"""
c1_06b_h3_horizon_sweep.py
===========================
H3 Horizon Sweep -- post-hoc exploratory analysis.
Converts H3 null result into temporal characterisation
of forecast reliability degradation.

Computes amplification ratio at each horizon:
  30, 60, 120, 240, 360, 480, 720, 1440 minutes

Bootstrap 95% CIs per horizon per region.
Spearman monotonicity test.
Identifies failure onset horizon per region.

NOT pre-registered -- clearly labelled exploratory.
Deviation D-018 recorded in COMPLIANCE.md.

Input:  data/raw/aemo_nem/aemo_nem_all_2021_2022_raw.csv
        data/processed/aemo_nem_all_2021_2022_processed.csv
Output: results/tables/h3_horizon_sweep.csv
        results/tables/h3_horizon_onset.csv
Project: forecast-reliability-indicator (FRI)
OSF:     10.17605/OSF.IO/Z89HD
"""
import sys
import warnings
import numpy as np
import pandas as pd
from scipy import stats
from config.settings import RAW_DIR, PROCESSED_DIR, TABLES_DIR
from config.logging_config import get_logger

warnings.filterwarnings("ignore")
logger = get_logger("c1_06b_h3_horizon_sweep")

#  CONFIG 
HORIZONS      = [30, 60, 120, 240, 360, 480, 720, 1440]
HORIZON_LABELS = {
    30:   "P30",
    60:   "P60",
    120:  "P120",
    240:  "P240",
    360:  "P360",
    480:  "P480",
    720:  "P720",
    1440: "P1440"
}
REGIONS         = ["NSW1", "VIC1", "QLD1", "SA1", "TAS1"]
EXTREME_THRESH  = 300.0
RELIABLE_THRESH = 1.5   # amplification ratio below = reliable
N_BOOTSTRAP     = 10000
SEED            = 42
WINDOW_MIN      = 15    # +/- window to match horizon


def load_raw(path):
    logger.info("Loading raw data...")
    df = pd.read_csv(
        path,
        parse_dates=["DATETIME", "PREDISPATCH_RUN_DATETIME"],
        low_memory=False)
    df["horizon_min"] = (
        df["DATETIME"] - df["PREDISPATCH_RUN_DATETIME"]
    ).dt.total_seconds() / 60
    logger.info(f"Raw rows: {len(df):,}")
    return df


def get_intervals(processed_path):
    """Get all intervals with regime from processed."""
    logger.info("Loading processed data...")
    df = pd.read_csv(processed_path,
                     parse_dates=["DATETIME"])
    df = df[["DATETIME", "REGIONID",
             "last_forecast", "regime"]].copy()
    extreme = df[df["regime"] == "extreme"]
    normal  = df[df["regime"] == "normal"]
    logger.info(f"Extreme intervals: {len(extreme):,}")
    logger.info(f"Normal intervals:  {len(normal):,}")
    return df


def get_forecast_at_horizon(raw_df, all_df,
                             region, horizon_min):
    """
    Vectorised: compute forecast revision at horizon h.
    revision = |last_forecast - RRP_at_horizon|
    For both extreme and normal intervals.
    """
    reg_raw = raw_df[
        raw_df["REGIONID"] == region].copy()
    reg_all = all_df[
        all_df["REGIONID"] == region].copy()

    if reg_raw.empty or reg_all.empty:
        return pd.DataFrame()

    # Filter raw to rows near target horizon
    reg_raw = reg_raw[
        (reg_raw["horizon_min"] >= horizon_min - WINDOW_MIN) &
        (reg_raw["horizon_min"] <= horizon_min + WINDOW_MIN)
    ].copy()

    if reg_raw.empty:
        return pd.DataFrame()

    reg_raw["horizon_diff"] = abs(
        reg_raw["horizon_min"] - horizon_min)

    # Keep only closest run per DATETIME
    reg_raw = reg_raw.sort_values("horizon_diff")
    reg_raw = reg_raw.drop_duplicates(
        subset=["DATETIME"], keep="first")
    reg_raw = reg_raw[["DATETIME", "RRP", "horizon_diff"]]

    # Merge with all intervals
    merged = reg_all.merge(reg_raw, on="DATETIME",
                           how="inner")
    merged = merged.rename(columns={"RRP": "forecast_rrp"})
    merged["horizon_min"] = horizon_min

    # Compute revision = |last_forecast - forecast_at_horizon|
    merged["revision"] = abs(
        merged["last_forecast"] - merged["forecast_rrp"])

    return merged


def compute_amplification(df):
    """
    Compute amplification ratio:
    mean revision (extreme) / mean revision (normal)
    This matches H1 metric applied per horizon.
    """
    if df.empty or len(df) < 5:
        return None, None, None
    extreme = df[df["regime"] == "extreme"]
    normal  = df[df["regime"] == "normal"]
    if len(extreme) < 5 or len(normal) < 5:
        return None, None, None
    mean_extreme = extreme["revision"].mean()
    mean_normal  = normal["revision"].mean()
    if mean_normal <= 0:
        return None, None, None
    ratio = mean_extreme / mean_normal
    return mean_extreme, mean_normal, ratio


def bootstrap_ratio(df, n=N_BOOTSTRAP, seed=SEED):
    """Bootstrap 95% CI for amplification ratio."""
    rng = np.random.default_rng(seed)
    ratios = []
    extreme = df[df["regime"] == "extreme"]
    normal  = df[df["regime"] == "normal"]
    n_ext = len(extreme)
    n_nrm = len(normal)
    for _ in range(n):
        s_ext = extreme.sample(n_ext, replace=True,
                    random_state=int(rng.integers(1e9)))
        s_nrm = normal.sample(n_nrm, replace=True,
                    random_state=int(rng.integers(1e9)))
        mean_ext = s_ext["revision"].mean()
        mean_nrm = s_nrm["revision"].mean()
        if mean_nrm > 0:
            ratios.append(mean_ext / mean_nrm)
    ratios = np.array(ratios)
    return (float(np.percentile(ratios, 2.5)),
            float(np.percentile(ratios, 97.5)))


def main():
    logger.info("=" * 60)
    logger.info("c1_06b_h3_horizon_sweep.py started")
    logger.info("POST-HOC EXPLORATORY ANALYSIS -- D-018")
    logger.info("=" * 60)

    rng = np.random.default_rng(SEED)

    # Load data
    raw_df = load_raw(
        RAW_DIR / "aemo_nem" / "aemo_nem_all_2021_2022_raw.csv")
    all_df = get_intervals(
        PROCESSED_DIR / "aemo_nem_all_2021_2022_processed.csv")

    results = []
    onset   = []

    for region in REGIONS:
        logger.info(f"\n{'='*40}")
        logger.info(f"Region: {region}")
        region_ratios = []

        for h in HORIZONS:
            label = HORIZON_LABELS[h]
            logger.info(f"  Computing {label} ({h} min)...")

            df_h = get_forecast_at_horizon(
                raw_df, all_df, region, h)

            if df_h.empty or len(df_h) < 10:
                logger.warning(
                    f"  {label}: insufficient data "
                    f"({len(df_h)} rows)")
                continue

            mae_actual, mae_forecast, ratio = \
                compute_amplification(df_h)

            if ratio is None:
                continue

            ci_low, ci_high = bootstrap_ratio(df_h)

            n_ext = len(df_h[df_h["regime"]=="extreme"])
            n_nrm = len(df_h[df_h["regime"]=="normal"])
            logger.info(
                f"  {label}: ext={n_ext} nrm={n_nrm} "
                f"ratio={ratio:.3f} "
                f"CI=[{ci_low:.3f}, {ci_high:.3f}]")

            n_ext = len(df_h[df_h["regime"]=="extreme"])
            n_nrm = len(df_h[df_h["regime"]=="normal"])
            results.append({
                "region":              region,
                "horizon_min":         h,
                "horizon_label":       label,
                "n_extreme":           n_ext,
                "n_normal":            n_nrm,
                "mean_revision_extreme": round(mae_actual, 4),
                "mean_revision_normal":  round(mae_forecast, 4),
                "amplification_ratio": round(ratio, 4),
                "ci_lower":            round(ci_low, 4),
                "ci_upper":            round(ci_high, 4),
            })
            region_ratios.append((h, ratio))

        # Spearman monotonicity test
        if len(region_ratios) >= 4:
            h_vals = [x[0] for x in region_ratios]
            r_vals = [x[1] for x in region_ratios]
            spearman_r, spearman_p = stats.spearmanr(
                h_vals, r_vals)
            logger.info(
                f"  Spearman rho={spearman_r:.4f} "
                f"p={spearman_p:.4f}")

            # Find failure onset -- first horizon where
            # ratio exceeds RELIABLE_THRESH
            onset_horizon = None
            for h, r in sorted(region_ratios):
                if r > RELIABLE_THRESH:
                    onset_horizon = h
                    break

            onset.append({
                "region":        region,
                "spearman_rho":  round(spearman_r, 4),
                "spearman_p":    round(spearman_p, 4),
                "monotonic":     spearman_r > 0 and
                                 spearman_p < 0.05,
                "onset_horizon_min": onset_horizon,
                "onset_label":   HORIZON_LABELS.get(
                    onset_horizon, str(onset_horizon))
                                 if onset_horizon else "all",
            })

    # Save results
    df_results = pd.DataFrame(results)
    df_onset   = pd.DataFrame(onset)

    out1 = TABLES_DIR / "h3_horizon_sweep.csv"
    out2 = TABLES_DIR / "h3_horizon_onset.csv"

    df_results.to_csv(out1, index=False)
    df_onset.to_csv(out2, index=False)

    logger.info("\n" + "=" * 60)
    logger.info("H3 HORIZON SWEEP COMPLETE")
    logger.info(f"Results: {out1}")
    logger.info(f"Onset:   {out2}")
    logger.info("\nSUMMARY:")
    logger.info(df_results.to_string())
    logger.info("\nONSET TABLE:")
    logger.info(df_onset.to_string())
    logger.info("=" * 60)
    sys.exit(0)


if __name__ == "__main__":
    main()
