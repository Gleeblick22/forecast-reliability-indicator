"""c4_03_test_R.py (Phase 4, P4.3/P4.5): registered tests R1-R6 on 2023-25 with the FROZEN model.
Run ONCE, as registered (OSF amendment; code tag R-prereg-2026-10-28-clean).
Frozen: params + theta from c2_31_best_params.json; fit partition 2021-10-01..2022-07-31;
features as c2_31 (earliest-run price features). The refit must reproduce c2_31 test scores.
Outputs: results/tables/c4_03_R_outcomes.csv, c4_03_R1_regions.csv, c4_03_R6.csv,
         c4_03_exploratory.csv, c4_03_scores.csv"""
import sys, json, importlib.util
import numpy as np
import pandas as pd
from scipy.stats import ttest_ind
from xgboost import XGBClassifier
from sklearn.metrics import roc_auc_score, average_precision_score, f1_score, precision_score, recall_score
from config.settings import PROCESSED_DIR, TABLES_DIR
from config.logging_config import get_logger

logger = get_logger("c4_03_test_R")
spec = importlib.util.spec_from_file_location("A", "scripts/c3_50_agents_v2.py")
A = importlib.util.module_from_spec(spec); spec.loader.exec_module(A)
KEYS = ["REGIONID", "DATETIME"]
OLD = ["f_current_rrp", "f_rolling_mean_30min", "f_rolling_max_30min", "f_consecutive_high",
       "f_price_change_30min", "f_price_change_60min", "f_hour_of_day", "f_day_of_week", "f_is_peak_hour"]
PATH = ["rev_abs", "rev_signed", "n_runs", "n_sign_flips", "max_abs_step", "run_std", "recent_std_3h"]
FULL = OLD + ["f_decision"] + PATH
Y, SEED, DT = "y_v2_d300", 42, 0.5
rng = np.random.default_rng(SEED)
INFO = json.load(open(TABLES_DIR / "c2_31_best_params.json"))
P, THETA = INFO["params"], INFO["theta_d300"]


def frozen_model():
    lab = pd.read_csv(PROCESSED_DIR / "aemo_nem_label_v2.csv", parse_dates=["DATETIME"])
    pf = pd.read_csv(PROCESSED_DIR / "price_features_earliest.csv", parse_dates=["DATETIME"])[KEYS + OLD]
    df = lab.merge(pf, on=KEYS)
    tr = df[df.partition == "train"]
    fit = tr[tr.DATETIME < "2022-08-01"]
    y = fit[Y]
    m = XGBClassifier(**P, scale_pos_weight=(y == 0).sum() / (y == 1).sum(), random_state=SEED,
                      eval_metric="logloss", verbosity=0, n_jobs=-1).fit(fit[FULL], y)
    ref = pd.read_csv(TABLES_DIR / "c2_31_test_scores.csv", parse_dates=["DATETIME"])
    test = df[df.partition == "test"].merge(ref[KEYS + ["fri_score"]], on=KEYS)
    diff = np.abs(m.predict_proba(test[FULL])[:, 1] - test.fri_score.values).max()
    logger.info(f"Frozen-model check vs c2_31 test scores ({len(test):,} rows): max |diff| = {diff:.2e}")
    if diff > 1e-5:
        logger.error("Refit does not reproduce the frozen model - STOP"); sys.exit(1)
    return m


def strat_idx(y):
    pos, neg = np.where(y == 1)[0], np.where(y == 0)[0]
    return np.concatenate([rng.choice(pos, len(pos)), rng.choice(neg, len(neg))])


def auc_ci(y, s, n=1000):
    reps = [roc_auc_score(y[i], s[i]) for i in (strat_idx(y) for _ in range(n))]
    return roc_auc_score(y, s), np.percentile(reps, 2.5), np.percentile(reps, 97.5)


def dap_ci(y, s1, s2, n=1000):
    reps = []
    for _ in range(n):
        i = strat_idx(y)
        reps.append(average_precision_score(y[i], s1[i]) - average_precision_score(y[i], s2[i]))
    obs = average_precision_score(y, s1) - average_precision_score(y, s2)
    return obs, np.percentile(reps, 2.5), np.percentile(reps, 97.5)


def r1(d):
    rows = []
    for reg, g in d.groupby("REGIONID"):
        ext, nor = g.error_v2[g.p_disp30 >= 300], g.error_v2[g.p_disp30 < 300]
        _, p = ttest_ind(ext, nor, equal_var=False)
        ratio = ext.mean() / nor.mean()
        rows.append(dict(region=reg, n_extreme=len(ext), mean_err_extreme=round(ext.mean(), 2),
                         mean_err_normal=round(nor.mean(), 2), ratio=round(ratio, 3), p=p,
                         pass_region=bool(ratio > 1.5 and p < 0.05)))
    t = pd.DataFrame(rows)
    return t, int(t.pass_region.sum())


def agent_setup(d, s):
    t = d.copy()
    t["day"] = t.DATETIME.dt.floor("D").factorize()[0]
    groups = [(g.index.values, g.day.tolist(), g.f_decision.tolist(), g.p_disp30.tolist())
              for _, g in t.groupby("REGIONID", sort=False)]
    n = len(t)
    fri3 = np.where(s >= THETA, 0.25, np.where(s >= 0.5, 0.75, 1.0))
    vol = t.recent_std_3h.fillna(0).values
    order = np.argsort(-vol, kind="stable")
    n25, n75 = int((fri3 == 0.25).sum()), int((fri3 == 0.75).sum())
    volm = np.ones(n); volm[order[:n25]] = 0.25; volm[order[n25:n25 + n75]] = 0.75
    scales = {"baseline": np.ones(n), "fri_3band": fri3, "vol_matched": volm, "const_0.25": np.full(n, 0.25)}
    return t, groups, scales


def main():
    m = frozen_model()
    d30 = pd.read_csv(PROCESSED_DIR / "replication_2023_2025_lead30.csv", parse_dates=["DATETIME"]).sort_values(KEYS).reset_index(drop=True)
    d60 = pd.read_csv(PROCESSED_DIR / "replication_2023_2025_lead60.csv", parse_dates=["DATETIME"]).sort_values(KEYS).reset_index(drop=True)
    s30, s60 = m.predict_proba(d30[FULL])[:, 1], m.predict_proba(d60[FULL])[:, 1]
    y30, y60 = d30[Y].values, d60[Y].values
    logger.info(f"lead30: {len(d30):,} rows, {y30.sum():,} positives | lead60: {len(d60):,} rows, {y60.sum():,} positives")
    d30.assign(fri_score=s30)[KEYS + [Y, "f_decision", "p_disp30", "fri_score"]].to_csv(TABLES_DIR / "c4_03_scores.csv", index=False)
    out = []

    t1, npass = r1(d30); t1.to_csv(TABLES_DIR / "c4_03_R1_regions.csv", index=False)
    out.append(dict(R="R1", result=f"{npass}/5 regions ratio>1.5 & p<0.05", criterion=">= 4/5", passed=npass >= 4))

    auc, lo, hi = auc_ci(y30, s30)
    out.append(dict(R="R2", result=f"AUC {auc:.4f} [{lo:.4f}, {hi:.4f}]", criterion="AUC>=0.80 & lo>0.70",
                    passed=bool(auc >= 0.80 and lo > 0.70)))

    t, groups, scales = agent_setup(d30, s30)
    over = ((t.f_decision - t.p_disp30) > 300).values
    runs = {k: A.run_agent(t, sc, groups) for k, sc in scales.items()}
    mwh = {k: float((r.disp.values * DT)[over].sum()) for k, r in runs.items()}
    daily = {k: pd.Series(r.disp.values * DT * over).groupby(t.day).sum() for k, r in runs.items()}
    red = 1 - mwh["fri_3band"] / mwh["baseline"] if mwh["baseline"] > 0 else float("nan")
    tot, lo3, hi3 = A.boot_diff(daily["vol_matched"], daily["fri_3band"])
    out.append(dict(R="R3", result=f"MWh over-forecast: base {mwh['baseline']:.1f}, vol {mwh['vol_matched']:.1f}, "
                    f"FRI {mwh['fri_3band']:.1f}; reduction {red*100:.1f}%; vol-FRI {tot:.1f} [{lo3:.1f}, {hi3:.1f}]",
                    criterion="reduction>=30% & (vol-FRI) CI lo>0", passed=bool(red >= 0.30 and lo3 > 0)))

    dap, lo4, hi4 = dap_ci(y30, s30, t.recent_std_3h.fillna(0).values)
    out.append(dict(R="R4", result=f"dAP {dap:.4f} [{lo4:.4f}, {hi4:.4f}]", criterion="dAP>0 & lo>0",
                    passed=bool(dap > 0 and lo4 > 0)))

    auc5, lo5, hi5 = auc_ci(y60, s60)
    out.append(dict(R="R5", result=f"AUC (60-min lead) {auc5:.4f} [{lo5:.4f}, {hi5:.4f}]", criterion="AUC>=0.75",
                    passed=bool(auc5 >= 0.75)))

    r6, target = [], None
    for beta in [2.03, 1.5, 1.0]:
        A.deg_cost = lambda dd, b=beta: A.R_REPL * A.ALPHA * dd ** b
        k = 1.0 if target is None else target / A.run_agent(t, scales["baseline"], groups).deg.sum()
        A.deg_cost = lambda dd, b=beta, kk=k: A.R_REPL * A.ALPHA * kk * dd ** b
        rr = {a: A.run_agent(t, scales[a], groups) for a in ["baseline", "fri_3band", "const_0.25"]}
        if target is None:
            target = rr["baseline"].deg.sum()
        r6.append(dict(beta=beta, k=round(k, 4), net_baseline=round(rr["baseline"].net.sum()),
                       net_fri=round(rr["fri_3band"].net.sum()), net_const025=round(rr["const_0.25"].net.sum()),
                       const025_minus_fri=round(rr["const_0.25"].net.sum() - rr["fri_3band"].net.sum())))
    r6 = pd.DataFrame(r6); r6.to_csv(TABLES_DIR / "c4_03_R6.csv", index=False)
    out.append(dict(R="R6", result="; ".join(f"beta {r.beta}: {r.const025_minus_fri:,}" for r in r6.itertuples()),
                    criterion="descriptive (no pass/fail)", passed=None))

    res = pd.DataFrame(out); res.to_csv(TABLES_DIR / "c4_03_R_outcomes.csv", index=False)
    pred = (s30 >= THETA).astype(int)
    ex = [dict(item="F1/precision/recall at frozen theta (d300)",
               value=f"{f1_score(y30, pred):.4f} / {precision_score(y30, pred, zero_division=0):.4f} / {recall_score(y30, pred):.4f}"),
          dict(item="AP (d300)", value=f"{average_precision_score(y30, s30):.4f}")]
    for dl in ["y_v2_d150", "y_v2_d500"]:
        ex.append(dict(item=f"AUC {dl}", value=f"{roc_auc_score(d30[dl], s30):.4f}"))
    for reg, g in d30.assign(s=s30).groupby("REGIONID"):
        if g[Y].nunique() == 2:
            ex.append(dict(item=f"AUC d300 {reg} (positives {int(g[Y].sum())})", value=f"{roc_auc_score(g[Y], g.s):.4f}"))
    pd.DataFrame(ex).to_csv(TABLES_DIR / "c4_03_exploratory.csv", index=False)
    with pd.option_context("display.width", 250, "display.max_colwidth", 200):
        logger.info(f"\nREGISTERED OUTCOMES:\n{res}")
        logger.info(f"\nR1 by region:\n{t1}")
        logger.info(f"\nR6:\n{r6}")
        logger.info(f"\nEXPLORATORY (not hypothesis tests):\n{pd.DataFrame(ex)}")
    sys.exit(0)


if __name__ == "__main__":
    main()
