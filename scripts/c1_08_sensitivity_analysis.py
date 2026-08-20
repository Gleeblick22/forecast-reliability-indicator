"""
c1_08_sensitivity_analysis.py
==============================
Sensitivity analysis for H1 H2 H3 results.
Re-runs hypothesis tests at alternative price
thresholds to confirm robustness of findings.

Per Decision 2: SENSITIVITY_THRESHOLDS = [150.0, 500.0]

Success criterion:
  H1 H2 H3 results confirmed robust at both
  $150 and $500 per MWh thresholds

Input:  data/processed/aemo_nem_all_2021_2022_processed.csv
        data/raw/aemo_nem/aemo_nem_all_2021_2022_raw.csv
Output: results/tables/c1_08_sensitivity_results.csv

Project: forecast-reliability-indicator (FRI)
OSF:     10.17605/OSF.IO/Z89HD
"""

import sys
import pandas as pd
import numpy as np
from scipy import stats
from datetime import datetime

from config.settings import (
    PROCESSED_DIR,
    AEMO_RAW_DIR,
    TABLES_DIR,
    NEM_REGIONS,
    SENSITIVITY_THRESHOLDS,
    H1_AMPLIFICATION_THRESHOLD,
    H1_PVALUE_THRESHOLD,
    H1_MIN_REGIONS_PASSING,
    H2_MASKING_THRESHOLD,
    H3_PVALUE_THRESHOLD,
)
from config.logging_config import get_logger

logger = get_logger("c1_08_sensitivity_analysis")

FULL_PROCESSED   = PROCESSED_DIR / "aemo_nem_all_2021_2022_processed.csv"
SAMPLE_PROCESSED = PROCESSED_DIR / "aemo_nem_sample_processed.csv"
FULL_RAW         = AEMO_RAW_DIR / "aemo_nem_all_2021_2022_raw.csv"
SAMPLE_RAW       = AEMO_RAW_DIR / "aemo_nem_sample_raw.csv"


def load_data() -> tuple:
    """Load processed and raw data."""
    if FULL_PROCESSED.exists():
        proc_path = FULL_PROCESSED
        raw_path  = FULL_RAW
        is_sample = False
        logger.info("Loading full dataset")
    else:
        proc_path = SAMPLE_PROCESSED
        raw_path  = SAMPLE_RAW
        is_sample = True
        logger.warning("Full dataset not found — using sample")

    processed = pd.read_csv(proc_path, parse_dates=["DATETIME"])
    raw       = pd.read_csv(
        raw_path,
        parse_dates=["DATETIME", "PREDISPATCH_RUN_DATETIME"], dayfirst=True
    )
    logger.info(f"Loaded {len(processed):,} processed intervals")
    return processed, raw, is_sample


def reclassify_regime(
    processed: pd.DataFrame,
    raw: pd.DataFrame,
    threshold: float
) -> pd.DataFrame:
    """
    Reclassify extreme/normal regime using alternative threshold.
    Recalculates last_forecast from raw data for accuracy.
    """
    latest_runs = (
        raw.sort_values("PREDISPATCH_RUN_DATETIME")
        .groupby(["DATETIME", "REGIONID"])
        .last()
        .reset_index()
    )[["DATETIME", "REGIONID", "RRP"]]
    latest_runs = latest_runs.rename(columns={"RRP": "latest_rrp"})

    df = processed.merge(latest_runs, on=["DATETIME", "REGIONID"], how="left")
    df["regime_alt"] = np.where(
        df["latest_rrp"] >= threshold,
        "extreme",
        "normal"
    )

    extreme_count = (df["regime_alt"] == "extreme").sum()
    logger.info(
        f"Threshold ${threshold:.0f}: "
        f"extreme={extreme_count:,} ({extreme_count/len(df)*100:.2f}%)"
    )
    return df


def test_h1_sensitivity(df: pd.DataFrame, threshold: float) -> dict:
    """Test H1 at alternative threshold."""
    regions_passing = 0

    for region in NEM_REGIONS:
        r              = df[df["REGIONID"] == region]
        extreme_errors = r[r["regime_alt"] == "extreme"]["forecast_error"].values
        normal_errors  = r[r["regime_alt"] == "normal"]["forecast_error"].values

        if len(extreme_errors) < 2 or len(normal_errors) < 2:
            continue

        mae_extreme = np.mean(extreme_errors)
        mae_normal  = np.mean(normal_errors)
        ratio       = mae_extreme / mae_normal if mae_normal > 0 else 0
        _, p_value  = stats.ttest_ind(extreme_errors, normal_errors, equal_var=False)

        if ratio > H1_AMPLIFICATION_THRESHOLD and p_value < H1_PVALUE_THRESHOLD:
            regions_passing += 1

    passes = regions_passing >= H1_MIN_REGIONS_PASSING
    logger.info(
        f"H1 at ${threshold:.0f}: "
        f"{regions_passing}/5 regions pass | "
        f"{'ROBUST' if passes else 'NOT ROBUST'}"
    )
    return {
        "hypothesis":        "H1",
        "threshold":         threshold,
        "regions_passing":   regions_passing,
        "passes":            passes,
    }


def test_h2_sensitivity(df: pd.DataFrame, threshold: float) -> dict:
    """Test H2 at alternative threshold."""
    aggregate_mae = float(df["forecast_error"].mean())
    extreme_df    = df[df["regime_alt"] == "extreme"]

    if len(extreme_df) == 0:
        logger.warning(f"H2 at ${threshold:.0f}: no extreme events")
        return {
            "hypothesis": "H2",
            "threshold":  threshold,
            "masking_pct": None,
            "passes":     False,
        }

    extreme_mae = float(extreme_df["forecast_error"].mean())
    masking_pct = (
        (extreme_mae - aggregate_mae) / extreme_mae * 100
        if extreme_mae > 0 else 0
    )
    passes = masking_pct > (H2_MASKING_THRESHOLD * 100)

    logger.info(
        f"H2 at ${threshold:.0f}: "
        f"masking={masking_pct:.1f}% | "
        f"{'ROBUST' if passes else 'NOT ROBUST'}"
    )
    return {
        "hypothesis":  "H2",
        "threshold":   threshold,
        "masking_pct": round(masking_pct, 2),
        "passes":      passes,
    }


def test_h3_sensitivity(df: pd.DataFrame, threshold: float) -> dict:
    """Test H3 at alternative threshold."""
    extreme   = df[df["regime_alt"] == "extreme"]
    p5_errors = extreme["p5_error"].dropna().values

    if "p30_error" not in df.columns:
        logger.warning(f"H3 at ${threshold:.0f}: p30_error column not found")
        return {
            "hypothesis": "H3",
            "threshold":  threshold,
            "p_value":    None,
            "passes":     False,
        }

    p30_errors = extreme[extreme["has_p30"] == True]["p30_error"].dropna().values

    if len(p5_errors) < 2 or len(p30_errors) < 2:
        logger.warning(
            f"H3 at ${threshold:.0f}: insufficient data "
            f"P5={len(p5_errors)} P30={len(p30_errors)}"
        )
        return {
            "hypothesis": "H3",
            "threshold":  threshold,
            "p_value":    None,
            "passes":     False,
        }

    p5_mean         = float(np.mean(p5_errors))
    p30_mean        = float(np.mean(p30_errors))
    _, p_value      = stats.ttest_ind(p5_errors, p30_errors, equal_var=False)
    passes          = p5_mean > p30_mean and p_value < H3_PVALUE_THRESHOLD

    logger.info(
        f"H3 at ${threshold:.0f}: "
        f"P5=${p5_mean:.2f} P30=${p30_mean:.2f} "
        f"p={p_value:.4f} | "
        f"{'ROBUST' if passes else 'NOT ROBUST'}"
    )
    return {
        "hypothesis": "H3",
        "threshold":  threshold,
        "p5_mean":    round(p5_mean, 4),
        "p30_mean":   round(p30_mean, 4),
        "p_value":    round(float(p_value), 6),
        "passes":     passes,
    }


def save_results(results: list, all_robust: bool) -> object:
    """Save sensitivity results."""
    TABLES_DIR.mkdir(parents=True, exist_ok=True)
    output_path = TABLES_DIR / "c1_08_sensitivity_results.csv"

    df = pd.DataFrame(results)
    df["all_hypotheses_robust"] = all_robust
    df.to_csv(output_path, index=False)
    logger.info(f"Results saved: {output_path}")
    return output_path


def main():
    logger.info("=" * 60)
    logger.info("c1_08_sensitivity_analysis.py started")
    logger.info(f"Timestamp: {datetime.now()}")
    logger.info(f"Testing thresholds: {SENSITIVITY_THRESHOLDS}")
    logger.info("=" * 60)

    processed, raw, is_sample = load_data()

    all_results = []
    robust_count = 0
    total_tests  = len(SENSITIVITY_THRESHOLDS) * 3

    for threshold in SENSITIVITY_THRESHOLDS:
        logger.info(f"--- Testing at ${threshold:.0f}/MWh ---")

        df_alt = reclassify_regime(processed, raw, threshold)

        h1 = test_h1_sensitivity(df_alt, threshold)
        h2 = test_h2_sensitivity(df_alt, threshold)
        h3 = test_h3_sensitivity(df_alt, threshold)

        all_results.extend([h1, h2, h3])

        if h1["passes"]:
            robust_count += 1
        if h2["passes"]:
            robust_count += 1
        if h3["passes"]:
            robust_count += 1

    all_robust  = robust_count == total_tests
    output_path = save_results(all_results, all_robust)

    logger.info("=" * 60)
    logger.info(
        f"SENSITIVITY RESULT: "
        f"{'ALL ROBUST' if all_robust else 'NOT ALL ROBUST'}"
    )
    logger.info(f"Robust: {robust_count} of {total_tests} tests")

    if is_sample:
        logger.warning(
            "SAMPLE MODE: sensitivity results not meaningful. "
            "Re-run on full dataset after May 1 download."
        )

    if not all_robust and not is_sample:
        logger.warning("Some results not robust — review sensitivity report")
        logger.warning("See PDD Section 4.4 for sensitivity analysis protocol")

    logger.info(f"Results: {output_path}")
    logger.info("Next: ./run.sh scripts/c1_09_replication_check.py")
    logger.info("=" * 60)
    sys.exit(0)


if __name__ == "__main__":
    main()
