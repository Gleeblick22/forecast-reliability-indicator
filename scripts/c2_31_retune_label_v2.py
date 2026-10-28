"""
c2_31_retune_label_v2.py  (Roadmap P2.2b)
Re-tunes XGBoost for the redesigned label (c1_30) on the VALIDATION period only.

Splits (same as c2_30): fit = before 2022-08-01; val = Aug-Sep 2022; test = held-out.
Step 1  Grid search on fit -> score on val (average precision), primary label d300.
Step 2  Refit best setting on fit; theta = max-F1 point on val; test used once.
Step 3  Same hyperparameters (fixed, not re-tuned) applied to d150 and d500.
Step 4  Feature attribution (mean |contribution|, XGBoost native) + drop-group ablation.
Outputs: results/tables/c2_31_grid.csv
         results/tables/c2_31_final_eval.csv
         results/tables/c2_31_feature_importance.csv
         results/tables/c2_31_best_params.json
         results/tables/c2_31_test_scores.csv   (FRI scores for the agent stage)
"""
import sys, json, itertools
import numpy as np
import pandas as pd
import xgboost as xgb
from xgboost import XGBClassifier
from sklearn.metrics import (roc_auc_score, average_precision_score, f1_score,
                             precision_score, recall_score, precision_recall_curve)
from config.settings import PROCESSED_DIR, TABLES_DIR
from config.logging_config import get_logger

logger = get_logger("c2_31_retune_label_v2")

LABEL_FILE = PROCESSED_DIR / "aemo_nem_label_v2.csv"
FEAT_FILE = PROCESSED_DIR / "final_leakage_controlled_dataset.csv"
KEYS = ["REGIONID", "DATETIME"]
OLD_KEEP = ["f_current_rrp", "f_rolling_mean_30min", "f_rolling_max_30min",
            "f_consecutive_high", "f_price_change_30min", "f_price_change_60min",
            "f_hour_of_day", "f_day_of_week", "f_is_peak_hour"]
PATH = ["rev_abs", "rev_signed", "n_runs", "n_sign_flips",
        "max_abs_step", "run_std", "recent_std_3h"]
FULL = OLD_KEEP + ["f_decision"] + PATH
PRIMARY = "y_v2_d300"
LABELS = ["y_v2_d150", "y_v2_d300", "y_v2_d500"]
VAL_START = pd.Timestamp("2022-08-01")
SEED, N_BOOT = 42, 1000
rng = np.random.default_rng(SEED)

GRID = dict(max_depth=[2, 3, 4, 5, 6],
            learning_rate=[0.03, 0.1, 0.3],
            n_estimators=[100, 300, 600],
            min_child_weight=[1, 5])


def load():
    lab = pd.read_csv(LABEL_FILE, parse_dates=["DATETIME"])
    old = pd.read_csv(FEAT_FILE, parse_dates=["DATETIME"])[KEYS + OLD_KEEP].drop_duplicates(KEYS)
    df = lab.merge(old, on=KEYS, how="inner")
    tr = df[df["partition"] == "train"]
    return df, tr[tr["DATETIME"] < VAL_START], tr[tr["DATETIME"] >= VAL_START], df[df["partition"] == "test"]


def make(params, y):
    spw = (y == 0).sum() / max((y == 1).sum(), 1)
    return XGBClassifier(**params, scale_pos_weight=spw, random_state=SEED,
                         eval_metric="logloss", verbosity=0, n_jobs=-1), spw


def boot_ci(y, s):
    pos, neg = np.where(y == 1)[0], np.where(y == 0)[0]
    a = [roc_auc_score(y[i], s[i]) for i in
         (np.concatenate([rng.choice(pos, len(pos)), rng.choice(neg, len(neg))]) for _ in range(N_BOOT))]
    return np.percentile(a, [2.5, 97.5])


def best_theta(y, s):
    p, r, t = precision_recall_curve(y, s)
    f = 2 * p * r / (p + r + 1e-12)
    return float(t[np.argmax(f[:-1])])


def evaluate(name, ycol, feats, params, fit, val, test, keep_scores=False):
    m, spw = make(params, fit[ycol].values)
    m.fit(fit[feats], fit[ycol])
    sv, st = m.predict_proba(val[feats])[:, 1], m.predict_proba(test[feats])[:, 1]
    yv, yt = val[ycol].values, test[ycol].values
    th = best_theta(yv, sv)
    pred = (st >= th).astype(int)
    lo, hi = boot_ci(yt, st)
    row = dict(check=name, label=ycol, n_val_pos=int(yv.sum()), n_test_pos=int(yt.sum()),
               val_ap=round(average_precision_score(yv, sv), 4),
               auc=round(roc_auc_score(yt, st), 4), auc_lo=round(lo, 4), auc_hi=round(hi, 4),
               ap=round(average_precision_score(yt, st), 4),
               f1=round(f1_score(yt, pred, zero_division=0), 4),
               precision=round(precision_score(yt, pred, zero_division=0), 4),
               recall=round(recall_score(yt, pred, zero_division=0), 4),
               theta=round(th, 6), scale_pos_weight=round(spw, 4))
    return (row, m, st) if keep_scores else (row, m, None)


def main():
    logger.info("=" * 60)
    logger.info("c2_31_retune_label_v2.py started")
    df, fit, val, test = load()
    logger.info(f"fit {len(fit):,} | val {len(val):,} | test {len(test):,}")

    # Step 1: grid on validation (test never touched)
    rows = []
    keys = list(GRID)
    for combo in itertools.product(*GRID.values()):
        p = dict(zip(keys, combo))
        m, _ = make(p, fit[PRIMARY].values)
        m.fit(fit[FULL], fit[PRIMARY])
        sv = m.predict_proba(val[FULL])[:, 1]
        rows.append({**p, "val_ap": average_precision_score(val[PRIMARY], sv),
                     "val_auc": roc_auc_score(val[PRIMARY], sv)})
    grid = pd.DataFrame(rows).sort_values("val_ap", ascending=False)
    grid.to_csv(TABLES_DIR / "c2_31_grid.csv", index=False)
    best = {k: (int(v) if k != "learning_rate" else float(v)) for k, v in grid.iloc[0][keys].items()}
    logger.info(f"\nTop 5 settings by validation AP:\n{grid.head(5).round(4)}")
    logger.info(f"Selected: {best}")

    # Step 2-3: final evaluation (test used once per label)
    out, scores = [], None
    for ycol in LABELS:
        r, m, st = evaluate("full_tuned", ycol, FULL, best, fit, val, test, keep_scores=(ycol == PRIMARY))
        out.append(r)
        if ycol == PRIMARY:
            final_model, scores = m, st
            theta_primary = r["theta"]
    for name, feats in [("no_revision_path", OLD_KEEP + ["f_decision"]),
                        ("path_only", ["f_decision"] + PATH),
                        ("no_recent_std", [f for f in FULL if f != "recent_std_3h"])]:
        out.append(evaluate(name, PRIMARY, feats, best, fit, val, test)[0])
    res = pd.DataFrame(out)
    res.to_csv(TABLES_DIR / "c2_31_final_eval.csv", index=False)
    with pd.option_context("display.width", 220, "display.max_columns", 20):
        logger.info(f"\n{res}")

    # Step 4: attribution on test (mean |contribution|, share %)
    contrib = final_model.get_booster().predict(xgb.DMatrix(test[FULL]), pred_contribs=True)[:, :-1]
    imp = pd.Series(np.abs(contrib).mean(axis=0), index=FULL)
    imp = (imp / imp.sum() * 100).sort_values(ascending=False).round(2)
    imp.rename("share_pct").to_csv(TABLES_DIR / "c2_31_feature_importance.csv")
    logger.info(f"\nFeature attribution share (%):\n{imp}")
    logger.info(f"Revision-path group share: {imp[PATH].sum():.2f}%")

    sc = test[KEYS + [PRIMARY, "f_decision", "p_disp30"]].copy()
    sc["fri_score"] = scores
    sc.to_csv(TABLES_DIR / "c2_31_test_scores.csv", index=False)
    json.dump({"params": best, "theta_d300": theta_primary,
               "scale_pos_weight_d300": res.loc[res.label == PRIMARY, "scale_pos_weight"].iloc[0],
               "grid": GRID, "selection": "validation average precision, label d300"},
              open(TABLES_DIR / "c2_31_best_params.json", "w"), indent=2)
    logger.info("Saved grid, final eval, importance, best params, test scores.")
    sys.exit(0)


if __name__ == "__main__":
    main()
