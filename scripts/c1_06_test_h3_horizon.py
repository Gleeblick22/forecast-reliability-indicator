"""
c1_06_test_h3_horizon.py
=========================
Tests H3: P5 predispatch forecast errors degrade
significantly more than P30 during extreme events.

Success criterion:
  P5 error > P30 error during extreme events
  p-value < 0.05 at overall NEM level

Input:  data/processed/aemo_nem_all_2021_2022_processed.csv
Output: results/tables/c1_06_h3_horizon_results.csv

Project: forecast-reliability-indicator (FRI)
OSF:     10.17605/OSF.IO/Z89HD
"""

import sys
import pandas as pd
import numpy as np
from scipy import stats  # uses wilcoxon signed-rank per D-011
from datetime import datetime

from config.settings import (
    PROCESSED_DIR,
    TABLES_DIR,
    NEM_REGIONS,
    H3_PVALUE_THRESHOLD,
)
from config.logging_config import get_logger

logger = get_logger("c1_06_test_h3_horizon")

FULL_PROCESSED   = PROCESSED_DIR / "aemo_nem_all_2021_2022_processed.csv"
SAMPLE_PROCESSED = PROCESSED_DIR / "aemo_nem_sample_processed.csv"


def load_processed() -> tuple:
    """Load processed data. Auto-detects full vs sample."""
    if FULL_PROCESSED.exists():
        path      = FULL_PROCESSED
        is_sample = False
        logger.info("Loading full processed dataset")
    else:
        path      = SAMPLE_PROCESSED
        is_sample = True
        logger.warning("Full processed data not found — using sample")

    df = pd.read_csv(path, parse_dates=["DATETIME"])
    logger.info(f"Loaded {len(df):,} intervals")
    return df, is_sample


def test_h3_region(df: pd.DataFrame, label: str) -> dict:
    """
    Test H3 for a given subset (region or overall NEM).

    Compares P5 errors vs P30 errors during extreme events.
    Uses independent samples t-test per Decision 7.

    P5 errors  = p5_error where regime == extreme
    P30 errors = p30_error where regime == extreme AND has_p30 == True
    """
    extreme = df[df["regime"] == "extreme"]

    if len(extreme) == 0:
        logger.warning(f"{label}: no extreme events found")
        return {
            "label":       label,
            "extreme_count": 0,
            "p5_count":    0,
            "p30_count":   0,
            "p5_mean":     None,
            "p30_mean":    None,
            "p_value":     None,
            "passes_h3":   False,
            "note":        "no_extreme_events",
        }

    # Extract PAIRED p5 and p30 errors from same intervals
    paired = extreme[extreme["has_p30"] == True].dropna(
        subset=["p5_error", "p30_error"]
    )
    p5_errors  = paired["p5_error"].values
    p30_errors = paired["p30_error"].values

    if len(p5_errors) < 2 or len(p30_errors) < 2:
        logger.warning(
            f"{label}: insufficient data "
            f"P5={len(p5_errors)} P30={len(p30_errors)}"
        )
        return {
            "label":         label,
            "extreme_count": len(extreme),
            "p5_count":      len(p5_errors),
            "p30_count":     len(p30_errors),
            "p5_mean":       None,
            "p30_mean":      None,
            "p_value":       None,
            "passes_h3":     False,
            "note":          "insufficient_data",
        }

    p5_mean  = float(np.mean(p5_errors))
    p30_mean = float(np.mean(p30_errors))

    # Wilcoxon signed-rank test used instead of t-test per D-011
    # Justification: forecast errors are highly skewed (skewness > 10)
    # Non-parametric paired test is more appropriate for this distribution
    # Reference: Conover 1999 Practical Nonparametric Statistics
    # Wilcoxon signed-rank on properly paired absolute errors
    # Both arrays must be same length and matched per interval
    df_paired  = pd.DataFrame({
        "p5":  p5_errors,
        "p30": p30_errors
    }).dropna()
    t_stat, p_value = stats.wilcoxon(
        df_paired["p5"].abs().values,
        df_paired["p30"].abs().values,
    )

    # Direction: P5 abs error > P30 abs error (P5 further from actual)
    p5_abs_mean  = float(df_paired["p5"].abs().mean())
    p30_abs_mean = float(df_paired["p30"].abs().mean())
    passes = p5_abs_mean > p30_abs_mean and p_value < H3_PVALUE_THRESHOLD

    result = {
        "label":         label,
        "extreme_count": len(extreme),
        "p5_count":      len(p5_errors),
        "p30_count":     len(p30_errors),
        "p5_mean":       round(p5_mean, 4),
        "p30_mean":      round(p30_mean, 4),
        "w_statistic":   round(float(t_stat), 4),
        "p_value":       round(float(p_value), 6),
        "passes_h3":     passes,
        "note":          "",
    }

    status = "PASS" if passes else "FAIL"
    logger.info(
        f"{label}: P5_mean=${p5_mean:.2f} | "
        f"P30_mean=${p30_mean:.2f} | "
        f"p={p_value:.4f} | {status}"
    )
    return result


def save_results(results: list, h3_passed: bool) -> object:
    """Save H3 results to results/tables/."""
    TABLES_DIR.mkdir(parents=True, exist_ok=True)
    output_path = TABLES_DIR / "c1_06_h3_horizon_results.csv"

    df = pd.DataFrame(results)
    df["h3_overall_passed"] = h3_passed
    df.to_csv(output_path, index=False)
    logger.info(f"Results saved: {output_path}")
    return output_path


def main():
    logger.info("=" * 60)
    logger.info("c1_06_test_h3_horizon.py started")
    logger.info(f"Timestamp: {datetime.now()}")
    logger.info(f"H3 threshold: p < {H3_PVALUE_THRESHOLD}")
    logger.info("H3 direction: P5 error must be > P30 error")
    logger.info("=" * 60)

    df, is_sample = load_processed()

    results = []

    # Overall NEM level — primary H3 test
    logger.info("Testing H3 at overall NEM level...")
    overall = test_h3_region(df, "OVERALL_NEM")
    results.append(overall)

    # Per region — supplementary analysis
    logger.info("Testing H3 per region...")
    for region in NEM_REGIONS:
        region_df = df[df["REGIONID"] == region]
        result    = test_h3_region(region_df, region)
        results.append(result)

    h3_passed = overall["passes_h3"]

    output_path = save_results(results, h3_passed)

    logger.info("=" * 60)
    logger.info(f"H3 RESULT: {'PASSED' if h3_passed else 'FAILED'}")

    if overall["p_value"] is not None:
        logger.info(f"Overall p-value: {overall['p_value']:.4f}")
        logger.info(f"P5 mean error:  ${overall['p5_mean']:.2f}")
        logger.info(f"P30 mean error: ${overall['p30_mean']:.2f}")
    else:
        logger.warning("H3 could not be evaluated — insufficient extreme events")

    if is_sample:
        logger.warning(
            "SAMPLE MODE: H3 result not meaningful — "
            "insufficient extreme events in 7-day sample. "
            "Re-run on full dataset after May 1 download."
        )

    if not h3_passed and not is_sample:
        logger.warning("H3 FAILED — initiate self-refine protocol")
        logger.warning("See PDD Section 4.2 for failure diagnosis")

    logger.info(f"Results: {output_path}")
    logger.info("Next: ./run.sh scripts/c1_07_trigger_weights.py")
    logger.info("=" * 60)
    sys.exit(0)


if __name__ == "__main__":
    main()
