"""
c2_30_label_v2_eval_and_leakage.py  (Roadmap P2.2)
Evaluates the FRI classifier on the redesigned label (c1_30) and runs leakage
and baseline checks.

Splits: fit = train before 2022-08-01; validation = Aug-Sep 2022 (threshold
        chosen here, max F1); test = held-out partition. No refit on validation.
Models: XGBoost with the registered fixed hyperparameters (200 / 9 / 0.3);
        logistic regression baseline.
Checks per delta (150/300/500):
  full        : old non-revision features + f_decision + revision-path features
  manuscript  : old non-revision features + rev_abs (closest to the paper's set)
  no_revision : drop all revision-path features (ablation)
  logreg_full : logistic regression, full features
  raw_*       : single-signal scores, no model (rev_abs, recent_std_3h, |f_decision|)
  permuted    : training labels shuffled (5 repeats, delta 300) -> AUC should be ~0.5
Output: results/tables/c2_30_label_v2_eval.csv
"""
import sys
import numpy as np
import pandas as pd
from xgboost import XGBClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import make_pipeline
from sklearn.metrics import (roc_auc_score, average_precision_score, f1_score,
                             precision_score, recall_score, precision_recall_curve)
from config.settings import PROCESSED_DIR, TABLES_DIR
from config.logging_config import get_logger

logger = get_logger("c2_30_label_v2_eval_and_leakage")

LABEL_FILE = PROCESSED_DIR / "aemo_nem_label_v2.csv"
FEAT_FILE = PROCESSED_DIR / "final_leakage_controlled_dataset.csv"
OUT_FILE = TABLES_DIR / "c2_30_label_v2_eval.csv"

KEYS = ["REGIONID", "DATETIME"]
OLD_KEEP = ["f_current_rrp", "f_rolling_mean_30min", "f_rolling_max_30min",
            "f_consecutive_high", "f_price_change_30min", "f_price_change_60min",
            "f_hour_of_day", "f_day_of_week", "f_is_peak_hour"]
PATH = ["rev_abs", "rev_signed", "n_runs", "n_sign_flips",
        "max_abs_step", "run_std", "recent_std_3h"]
FULL = OLD_KEEP + ["f_decision"] + PATH
MANUSCRIPT = OLD_KEEP + ["rev_abs"]
NO_REV = OLD_KEEP + ["f_decision"]
LABELS = ["y_v2_d150", "y_v2_d300", "y_v2_d500"]
VAL_START = pd.Timestamp("2022-08-01")
N_BOOT, N_PERM, SEED = 1000, 5, 42
rng = np.random.default_rng(SEED)


def load():
    lab = pd.read_csv(LABEL_FILE, parse_dates=["DATETIME"])
    old = pd.read_csv(FEAT_FILE, parse_dates=["DATETIME"])
    missing = [c for c in KEYS + OLD_KEEP if c not in old.columns]
    if missing:
        logger.error(f"Missing columns in {FEAT_FILE.name}: {missing}")
        sys.exit(1)
    old = old[KEYS + OLD_KEEP].drop_duplicates(KEYS)
    df = lab.merge(old, on=KEYS, how="inner")
    df["abs_f_decision"] = df["f_decision"].abs()
    logger.info(f"Label rows {len(lab):,}; after merge with old features {len(df):,}")
    return df


def split(df):
    tr = df[df["partition"] == "train"]
    return tr[tr["DATETIME"] < VAL_START], tr[tr["DATETIME"] >= VAL_START], df[df["partition"] == "test"]


def boot_ci(y, s):
    pos, neg = np.where(y == 1)[0], np.where(y == 0)[0]
    if len(pos) < 2:
        return np.nan, np.nan
    aucs = []
    for _ in range(N_BOOT):
        i = np.concatenate([rng.choice(pos, len(pos)), rng.choice(neg, len(neg))])
        aucs.append(roc_auc_score(y[i], s[i]))
    return np.percentile(aucs, [2.5, 97.5])


def best_threshold(y, s):
    if y.sum() == 0:
        return 0.5
    p, r, t = precision_recall_curve(y, s)
    f = 2 * p * r / (p + r + 1e-12)
    return t[np.argmax(f[:-1])]


def metrics(name, ycol, yv, sv, yt, st):
    thr = best_threshold(yv, sv)
    pred = (st >= thr).astype(int)
    lo, hi = boot_ci(yt, st)
    return dict(check=name, label=ycol, n_val_pos=int(yv.sum()), n_test_pos=int(yt.sum()),
                test_prevalence=round(yt.mean(), 5),
                auc=round(roc_auc_score(yt, st), 4), auc_lo=round(lo, 4), auc_hi=round(hi, 4),
                ap=round(average_precision_score(yt, st), 4),
                f1=round(f1_score(yt, pred, zero_division=0), 4),
                precision=round(precision_score(yt, pred, zero_division=0), 4),
                recall=round(recall_score(yt, pred, zero_division=0), 4),
                threshold=round(float(thr), 6))


def model_check(name, feats, df, ycol, kind="xgb", y_fit=None):
    fit, val, test = split(df)
    yf = fit[ycol].values if y_fit is None else y_fit
    if kind == "xgb":
        spw = (yf == 0).sum() / max((yf == 1).sum(), 1)
        m = XGBClassifier(n_estimators=200, max_depth=9, learning_rate=0.3,
                          scale_pos_weight=spw, random_state=SEED,
                          eval_metric="logloss", verbosity=0)
    else:
        m = make_pipeline(SimpleImputer(strategy="median"), StandardScaler(),
                          LogisticRegression(max_iter=3000, class_weight="balanced"))
    m.fit(fit[feats], yf)
    return metrics(name, ycol,
                   val[ycol].values, m.predict_proba(val[feats])[:, 1],
                   test[ycol].values, m.predict_proba(test[feats])[:, 1])


def raw_check(name, col, df, ycol):
    _, val, test = split(df)
    return metrics(name, ycol, val[ycol].values, val[col].fillna(0).values,
                   test[ycol].values, test[col].fillna(0).values)


def main():
    logger.info("=" * 60)
    logger.info("c2_30_label_v2_eval_and_leakage.py started")
    df = load()
    fit, val, test = split(df)
    logger.info(f"fit {len(fit):,} | val {len(val):,} | test {len(test):,}")

    rows = []
    for ycol in LABELS:
        logger.info(f"--- {ycol} ---")
        rows.append(model_check("full", FULL, df, ycol))
        rows.append(model_check("manuscript", MANUSCRIPT, df, ycol))
        rows.append(model_check("no_revision", NO_REV, df, ycol))
        rows.append(model_check("logreg_full", FULL, df, ycol, kind="logreg"))
        rows.append(raw_check("raw_rev_abs", "rev_abs", df, ycol))
        rows.append(raw_check("raw_recent_std_3h", "recent_std_3h", df, ycol))
        rows.append(raw_check("raw_abs_f_decision", "abs_f_decision", df, ycol))

    ycol = "y_v2_d300"
    perm_aucs = []
    for k in range(N_PERM):
        y_perm = rng.permutation(fit[ycol].values)
        r = model_check(f"permuted_{k}", FULL, df, ycol, y_fit=y_perm)
        perm_aucs.append(r["auc"])
        rows.append(r)
    logger.info(f"Permuted-label test AUCs: {perm_aucs} (expect ~0.5)")

    res = pd.DataFrame(rows)
    TABLES_DIR.mkdir(parents=True, exist_ok=True)
    res.to_csv(OUT_FILE, index=False)
    with pd.option_context("display.width", 200, "display.max_columns", 20):
        logger.info(f"\n{res[['check', 'label', 'n_test_pos', 'auc', 'auc_lo', 'auc_hi', 'ap', 'f1', 'precision', 'recall']]}")
    logger.info(f"Saved: {OUT_FILE}")
    sys.exit(0)


if __name__ == "__main__":
    main()
