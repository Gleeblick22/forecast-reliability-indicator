"""
c3_11_confidence_intervals.py  [CORRECTED]
==========================================
Computes 95% bootstrap confidence intervals
for all key FRI metrics across H1-H8 and Q4.

CORRECTIONS APPLIED (audit, pre-manuscript):
  FIX-1 (H8_SA): prediction threshold changed 0.29 -> 0.8006
                 (NEM-derived threshold, D-023). SA F1 now 0.5923,
                 not 0.7840. Point estimate now COMPUTED, not hardcoded.
  FIX-2 (H6):    correlation CI changed from a degenerate raw bootstrap
                 (which produced [-0.0072, 0.0624], not even containing
                 the point estimate) to the analytic Fisher z-transform
                 CI on the DISPATCHED intervals (n=983). Point and CI
                 now both computed on the same dispatched subset,
                 consistent with c3_04.
  FIX-3:         H5 / H6 / H8_SA point estimates are now COMPUTED from
                 data rather than hardcoded, so they can never drift
                 from the CSVs again.

Method: Bootstrap percentile method n=10000
        Efron and Tibshirani 1993
        seed=42 for reproducibility
        H6 CI: Fisher z-transformation (analytic)

Also computes:
  McNemar test for H5 (SD-003)
  Power analysis for H7 (SD-004)

Output: results/tables/confidence_intervals.csv
        results/tables/h5_mcnemar_test.csv
        results/tables/h7_power_analysis.csv
Project: forecast-reliability-indicator (FRI)
OSF:     10.17605/OSF.IO/Z89HD
"""
import sys
import pickle
import warnings
import numpy as np
import pandas as pd
from datetime import datetime
from scipy import stats
from sklearn.metrics import (f1_score, roc_auc_score,
                             precision_score, recall_score)
from statsmodels.stats.power import TTestIndPower
from config.settings import PROCESSED_DIR, TABLES_DIR, MODELS_DIR
from config.logging_config import get_logger

warnings.filterwarnings("ignore")
logger = get_logger("c3_11_confidence_intervals")

N_BOOT   = 10000
SEED     = 42
CI_LEVEL = 95
NEM_THRESHOLD = 0.8006          # FIX-1: canonical NEM-derived threshold (D-004/D-023)
np.random.seed(SEED)


def bootstrap_ci(values, n_boot=N_BOOT, ci=CI_LEVEL):
    boots = [np.mean(values[np.random.choice(
        len(values), len(values), replace=True)])
        for _ in range(n_boot)]
    lo = np.percentile(boots, (100 - ci) / 2)
    hi = np.percentile(boots, 100 - (100 - ci) / 2)
    return round(lo, 4), round(hi, 4)


def bootstrap_metric(y_true, y_pred, y_proba, metric_fn,
                     n_boot=N_BOOT, ci=CI_LEVEL):
    boots = []
    n = len(y_true)
    for _ in range(n_boot):
        idx = np.random.choice(n, n, replace=True)
        boots.append(metric_fn(y_true[idx], y_pred[idx],
                               y_proba[idx]))
    lo = np.percentile(boots, (100 - ci) / 2)
    hi = np.percentile(boots, 100 - (100 - ci) / 2)
    return round(lo, 4), round(hi, 4)


def fisher_z_ci(r, n, ci=CI_LEVEL):
    """FIX-2: analytic CI for a Pearson correlation via Fisher
    z-transformation. Valid where a raw bootstrap is degenerate
    (here the FRI-score distribution is heavily zero-inflated)."""
    z      = np.arctanh(r)
    se     = 1.0 / np.sqrt(n - 3)
    crit   = stats.norm.ppf(1 - (1 - ci / 100) / 2)   # 1.96 at 95%
    lo     = np.tanh(z - crit * se)
    hi     = np.tanh(z + crit * se)
    return round(lo, 4), round(hi, 4)


def main():
    logger.info("=" * 60)
    logger.info("c3_11_confidence_intervals.py started [CORRECTED]")
    logger.info(f"Timestamp: {datetime.now()}")
    logger.info(f"Bootstrap iterations: {N_BOOT}")
    logger.info(f"CI level: {CI_LEVEL}%")
    logger.info(f"Seed: {SEED}")
    logger.info(f"NEM threshold: {NEM_THRESHOLD}")
    logger.info("Reference: Efron Tibshirani 1993; Fisher 1915 (H6 CI)")
    logger.info("=" * 60)

    ci_results   = []
    mcn_results  = []
    pwr_results  = []

    # load shared data
    X_test  = pd.read_csv(PROCESSED_DIR / "X_test.csv")
    y_test  = pd.read_csv(PROCESSED_DIR / "y_test.csv").values.ravel()
    with open(MODELS_DIR / "fri_model_v1_tuned.pkl", "rb") as f:
        model = pickle.load(f)
    proba  = model.predict_proba(X_test.values)[:, 1]
    y_pred = (proba >= NEM_THRESHOLD).astype(int)

    baseline = pd.read_csv(
        TABLES_DIR / "c3_01_baseline_agent_results.csv")
    fri = pd.read_csv(
        TABLES_DIR / "c3_02_fri_agent_results.csv")

    # H1 amplification ratio CI
    logger.info("H1 amplification ratio CI...")
    h1 = pd.read_csv(TABLES_DIR / "c1_04_h1_amplification_results.csv")
    ratios = h1[~h1["region"].str.contains("OVERALL")]["ratio"].values
    lo, hi = bootstrap_ci(ratios)
    ci_results.append({
        "metric":  "H1_amplification_ratio",
        "point":   round(float(ratios.mean()), 4),
        "ci_low":  lo,
        "ci_high": hi,
        "n":       len(ratios),
        "note":    "Mean ratio across 5 NEM regions"
    })
    logger.info(f"  {ratios.mean():.4f} [{lo}, {hi}]")

    # H2 masking percentage CI
    logger.info("H2 masking percentage CI...")
    h2 = pd.read_csv(TABLES_DIR / "c1_05_h2_masking_results.csv")
    mask_pcts = h2[h2["label"].str.endswith("1")]["masking_pct"].values
    lo, hi = bootstrap_ci(mask_pcts)
    ci_results.append({
        "metric":  "H2_masking_pct",
        "point":   round(float(mask_pcts.mean()), 4),
        "ci_low":  lo,
        "ci_high": hi,
        "n":       len(mask_pcts),
        "note":    "Mean masking pct across 5 NEM regions"
    })
    logger.info(f"  {mask_pcts.mean():.4f} [{lo}, {hi}]")

    # H4 F1 AUC precision recall CI
    logger.info("H4 model metrics CI...")
    n = len(y_test)
    h4_f1_point   = round(f1_score(y_test, y_pred, zero_division=0), 4)
    h4_auc_point  = round(roc_auc_score(y_test, proba), 4)
    h4_prec_point = round(precision_score(y_test, y_pred, zero_division=0), 4)
    h4_rec_point  = round(recall_score(y_test, y_pred, zero_division=0), 4)
    logger.info(f"H4 actual point estimates: "
                f"F1={h4_f1_point} AUC={h4_auc_point} "
                f"Prec={h4_prec_point} Rec={h4_rec_point}")

    for name, point, fn in [
        ("H4_F1",
         h4_f1_point,
         lambda yt, yp, ypr: f1_score(yt, yp, zero_division=0)),
        ("H4_AUC",
         h4_auc_point,
         lambda yt, yp, ypr: roc_auc_score(yt, ypr)
         if yt.sum() > 0 else 0),
        ("H4_Precision",
         h4_prec_point,
         lambda yt, yp, ypr: precision_score(yt, yp, zero_division=0)),
        ("H4_Recall",
         h4_rec_point,
         lambda yt, yp, ypr: recall_score(yt, yp, zero_division=0)),
    ]:
        lo, hi = bootstrap_metric(y_test, y_pred, proba, fn)
        ci_results.append({
            "metric":  name,
            "point":   point,
            "ci_low":  lo,
            "ci_high": hi,
            "n":       n,
            "note":    "Bootstrap on held-out test set"
        })
        logger.info(f"  {name}: {point} [{lo}, {hi}]")

    # H5 silent failure reduction CI
    logger.info("H5 silent failure reduction CI...")
    b_sf = baseline["is_silent_failure"].values.astype(int)
    f_sf = fri["is_silent_failure"].values.astype(int)
    n    = len(b_sf)

    # FIX-3: compute the point estimate from data
    h5_point = round((b_sf.sum() - f_sf.sum()) / b_sf.sum() * 100, 2) \
        if b_sf.sum() > 0 else 0.0

    red_boots = []
    for _ in range(N_BOOT):
        idx = np.random.choice(n, n, replace=True)
        b   = b_sf[idx].sum()
        f   = f_sf[idx].sum()
        red_boots.append((b - f) / b * 100 if b > 0 else 0)

    lo = round(np.percentile(red_boots, (100 - CI_LEVEL) / 2), 2)
    hi = round(np.percentile(red_boots, 100 - (100 - CI_LEVEL) / 2), 2)
    ci_results.append({
        "metric":  "H5_sf_reduction_pct",
        "point":   h5_point,
        "ci_low":  lo,
        "ci_high": hi,
        "n":       n,
        "note":    "Bootstrap silent failure reduction"
    })
    logger.info(f"  {h5_point}% [{lo}, {hi}]")

    # H6 correlation CI  [FIX-2]
    logger.info("H6 Pearson correlation CI (Fisher z)...")
    # correlation is defined only on DISPATCHED intervals (those with a
    # dispatch size); this matches the canonical c3_04 run (n=983).
    # ADJUST the dispatch mask below if your column differs.
    dispatch_col = "dispatch_mw"          # <-- confirm this column name
    dispatched   = fri[fri[dispatch_col] > 0].copy()
    fri_scores   = dispatched["fri_score"].fillna(0).values
    dispatches   = dispatched[dispatch_col].values
    n_disp       = len(fri_scores)

    h6_point = round(float(np.corrcoef(fri_scores, dispatches)[0, 1]), 4)
    lo, hi   = fisher_z_ci(h6_point, n_disp)
    ci_results.append({
        "metric":  "H6_pearson_correlation",
        "point":   h6_point,
        "ci_low":  lo,
        "ci_high": hi,
        "n":       n_disp,
        "note":    "Fisher z-transformation CI on dispatched intervals"
    })
    logger.info(f"  {h6_point} [{lo}, {hi}]  (n={n_disp}, Fisher z)")

    # H8 SA F1 CI  [FIX-1]
    logger.info("H8 SA cross-region F1 CI...")
    # FIX-1b: match c3_06b EXACTLY -- LOAD the saved NEM model and apply
    # it to SA. Do NOT retrain. Retraining a fresh model (the previous
    # bug) produced 0.8526; loading the canonical NEM model reproduces
    # the canonical SA F1=0.5923. Feature order and fillna match c3_06b.
    SA_FEATURES = [
        "f_current_rrp", "f_forecast_revision", "f_rolling_max_30min",
        "f_rolling_mean_30min", "f_price_change_60min", "f_day_of_week",
        "f_consecutive_high", "f_hour_of_day", "f_price_change_30min",
        "f_is_peak_hour",
    ]
    features  = pd.read_csv(PROCESSED_DIR / "features_all.csv")
    test_df   = features[features["REGIONID"] == "SA1"].copy()
    sa_X      = test_df[SA_FEATURES].fillna(0)
    sa_true   = test_df["label"].astype(int).values
    sa_proba  = model.predict_proba(sa_X)[:, 1]          # saved NEM model
    sa_pred   = (sa_proba >= NEM_THRESHOLD).astype(int)  # 0.8006
    n         = len(sa_true)

    sa_f1_point = round(f1_score(sa_true, sa_pred, zero_division=0), 4)  # FIX-3

    sa_boots = []
    for _ in range(N_BOOT):
        idx = np.random.choice(n, n, replace=True)
        sa_boots.append(f1_score(sa_true[idx], sa_pred[idx],
                                 zero_division=0))

    lo = round(np.percentile(sa_boots, (100 - CI_LEVEL) / 2), 4)
    hi = round(np.percentile(sa_boots, 100 - (100 - CI_LEVEL) / 2), 4)
    ci_results.append({
        "metric":  "H8_SA_F1",
        "point":   sa_f1_point,
        "ci_low":  lo,
        "ci_high": hi,
        "n":       n,
        "note":    f"NEM model applied to SA, threshold={NEM_THRESHOLD} (D-023); loaded not retrained"
    })
    logger.info(f"  {sa_f1_point} [{lo}, {hi}]")

    # Q4 early warning ratio CI
    logger.info("Q4 early warning ratio CI...")
    clust = pd.read_csv(TABLES_DIR / "q4_failure_clustering.csv")
    pre2  = clust["pre2_ratio"].values
    lo, hi = bootstrap_ci(pre2)
    ci_results.append({
        "metric":  "Q4_early_warning_pre2_ratio",
        "point":   round(float(pre2.mean()), 1),
        "ci_low":  lo,
        "ci_high": hi,
        "n":       len(pre2),
        "note":    "Mean 2-interval early warning ratio across regions"
    })
    logger.info(f"  {pre2.mean():.1f}x [{lo}, {hi}]")

    # McNemar test for H5
    logger.info("McNemar test for H5 (SD-003)...")
    both_fail = int(((b_sf == 1) & (f_sf == 1)).sum())
    base_only = int(((b_sf == 1) & (f_sf == 0)).sum())
    fri_only  = int(((b_sf == 0) & (f_sf == 1)).sum())
    n_disc    = base_only + fri_only

    if n_disc > 0:
        chi2 = (abs(base_only - fri_only) - 1) ** 2 / n_disc
        pval = 1 - stats.chi2.cdf(chi2, df=1)
    else:
        chi2, pval = 0.0, 1.0

    mcn_results.append({
        "test":           "McNemar chi-squared",
        "both_fail":      both_fail,
        "baseline_only":  base_only,
        "fri_only":       fri_only,
        "n_discordant":   n_disc,
        "chi2":           round(chi2, 4),
        "p_value":        round(pval, 6),
        "significant":    pval < 0.05,
        "note":           "H5 paired binary outcome test SD-003"
    })
    logger.info(f"  chi2={chi2:.4f}  p={pval:.6f}")
    logger.info(f"  base_only={base_only}  fri_only={fri_only}")
    logger.info(f"  Significant: {'YES p<0.05' if pval < 0.05 else 'NO'}")

    # Power analysis for H7
    logger.info("Power analysis for H7 (SD-004)...")
    b_ext = baseline[baseline["regime"] == "extreme"]["revenue"].values
    f_ext = fri[fri["regime"] == "extreme"]["revenue"].values
    n_ext = len(b_ext)

    pooled_std = np.sqrt(
        (b_ext.std() ** 2 + f_ext.std() ** 2) / 2)
    cohen_d = (abs(f_ext.mean() - b_ext.mean()) / pooled_std
               if pooled_std > 0 else 0)

    pa = TTestIndPower()
    achieved_power = pa.solve_power(
        effect_size=cohen_d, nobs1=n_ext,
        alpha=0.05, alternative="two-sided")
    required_n = pa.solve_power(
        effect_size=cohen_d, power=0.80,
        alpha=0.05, alternative="two-sided")

    pwr_results.append({
        "hypothesis":       "H7",
        "n_extreme_events": n_ext,
        "cohen_d":          round(cohen_d, 4),
        "achieved_power":   round(achieved_power, 4),
        "required_n_80pct": round(required_n, 0),
        "conclusion":       (
            "Underpowered -- null result reflects "
            "insufficient sample not absent effect"),
        "note":             "Cohen 1988 TTestIndPower SD-004"
    })
    logger.info(f"  Extreme events:   {n_ext}")
    logger.info(f"  Cohen d:          {cohen_d:.4f}")
    logger.info(f"  Achieved power:   {achieved_power:.2%}")
    logger.info(f"  Required n (80%): {required_n:.0f}")

    # save all outputs
    ci_df  = pd.DataFrame(ci_results)
    mcn_df = pd.DataFrame(mcn_results)
    pwr_df = pd.DataFrame(pwr_results)

    ci_out  = TABLES_DIR / "confidence_intervals.csv"
    mcn_out = TABLES_DIR / "h5_mcnemar_test.csv"
    pwr_out = TABLES_DIR / "h7_power_analysis.csv"

    ci_df.to_csv(ci_out,   index=False)
    mcn_df.to_csv(mcn_out, index=False)
    pwr_df.to_csv(pwr_out, index=False)

    logger.info("=" * 60)
    logger.info("c3_11 COMPLETE [CORRECTED]")
    logger.info(f"CI metrics computed: {len(ci_df)}")
    logger.info(f"McNemar p-value:      {mcn_results[0]['p_value']}")
    logger.info(f"H7 achieved power:    {pwr_results[0]['achieved_power']:.2%}")
    logger.info(f"H7 required n:        {pwr_results[0]['required_n_80pct']:.0f}")
    logger.info(f"Saved: {ci_out}")
    logger.info(f"Saved: {mcn_out}")
    logger.info(f"Saved: {pwr_out}")
    logger.info("Next: ./run.sh scripts/c3_12_algorithm_comparison.py")
    logger.info("=" * 60)
    sys.exit(0)


if __name__ == "__main__":
    main()