"""
c1_04_test_h1_amplification.py
===============================
Tests H1: Forecast errors amplify >= 1.5x during
extreme price events vs normal conditions.

Success criterion:
  MAE ratio (extreme/normal) > 1.5
  p-value < 0.05
  In at least 4 of 5 NEM regions

Input:  data/processed/aemo_nem_all_2021_2022_processed.csv
Output: results/tables/c1_04_h1_amplification_results.csv

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
    TABLES_DIR,
    NEM_REGIONS,
    H1_AMPLIFICATION_THRESHOLD,
    H1_PVALUE_THRESHOLD,
    H1_MIN_REGIONS_PASSING,
)
from config.logging_config import get_logger

logger = get_logger("c1_04_test_h1_amplification")

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


def test_h1_region(df: pd.DataFrame, region: str) -> dict:
    """
    Test H1 for a single NEM region.

    Compares forecast_error distributions:
      extreme intervals vs normal intervals
    Using independent samples t-test.
    """
    r = df[df["REGIONID"] == region]

    extreme_errors = r[r["regime"] == "extreme"]["forecast_error"].values
    normal_errors  = r[r["regime"] == "normal"]["forecast_error"].values

    if len(extreme_errors) < 2:
        logger.warning(f"{region}: insufficient extreme events ({len(extreme_errors)})")
        return {
            "region":         region,
            "extreme_count":  len(extreme_errors),
            "normal_count":   len(normal_errors),
            "mae_extreme":    None,
            "mae_normal":     None,
            "ratio":          None,
            "p_value":        None,
            "passes_h1":      False,
            "note":           "insufficient_extreme_events",
        }

    mae_extreme = float(np.mean(extreme_errors))
    mae_normal  = float(np.mean(normal_errors))
    ratio       = mae_extreme / mae_normal if mae_normal > 0 else 0

    t_stat, p_value = stats.ttest_ind(
        extreme_errors,
        normal_errors,
        equal_var=False,
    )

    passes = (
        ratio > H1_AMPLIFICATION_THRESHOLD
        and p_value < H1_PVALUE_THRESHOLD
    )

    result = {
        "region":        region,
        "extreme_count": len(extreme_errors),
        "normal_count":  len(normal_errors),
        "mae_extreme":   round(mae_extreme, 4),
        "mae_normal":    round(mae_normal, 4),
        "ratio":         round(ratio, 4),
        "t_statistic":   round(float(t_stat), 4),
        "p_value":       round(float(p_value), 6),
        "passes_h1":     passes,
        "note":          "",
    }

    status = "PASS" if passes else "FAIL"
    logger.info(
        f"{region}: MAE_extreme=${mae_extreme:.2f} | "
        f"MAE_normal=${mae_normal:.2f} | "
        f"ratio={ratio:.2f}x | p={p_value:.4f} | {status}"
    )
    return result


def save_results(results: list, h1_passed: bool) -> object:
    """Save H1 results to results/tables/."""
    TABLES_DIR.mkdir(parents=True, exist_ok=True)
    output_path = TABLES_DIR / "c1_04_h1_amplification_results.csv"

    df = pd.DataFrame(results)
    df["h1_overall_passed"] = h1_passed
    df.to_csv(output_path, index=False)
    logger.info(f"Results saved: {output_path}")
    return output_path


def main():
    logger.info("=" * 60)
    logger.info("c1_04_test_h1_amplification.py started")
    logger.info(f"Timestamp: {datetime.now()}")
    logger.info(f"H1 threshold: ratio > {H1_AMPLIFICATION_THRESHOLD}x")
    logger.info(f"H1 p-value:   p < {H1_PVALUE_THRESHOLD}")
    logger.info(f"H1 regions:   >= {H1_MIN_REGIONS_PASSING} of 5 must pass")
    logger.info("=" * 60)

    df, is_sample = load_processed()

    results = []
    for region in NEM_REGIONS:
        result = test_h1_region(df, region)
        results.append(result)

    regions_passing = sum(1 for r in results if r["passes_h1"])
    h1_passed       = regions_passing >= H1_MIN_REGIONS_PASSING

    output_path = save_results(results, h1_passed)

    logger.info("=" * 60)
    logger.info(f"H1 RESULT: {'PASSED' if h1_passed else 'FAILED'}")
    logger.info(f"Regions passing: {regions_passing} of 5")
    logger.info(f"Required:        {H1_MIN_REGIONS_PASSING} of 5")

    if is_sample:
        logger.warning(
            "SAMPLE MODE: H1 result not meaningful — "
            "insufficient extreme events in 7-day sample. "
            "Re-run on full dataset after May 1 download."
        )

    if not h1_passed and not is_sample:
        logger.warning("H1 FAILED — initiate self-refine protocol")
        logger.warning("See PDD Section 4.2 for failure diagnosis")

    logger.info(f"Results: {output_path}")
    logger.info("Next: ./run.sh scripts/c1_05_test_h2_masking.py")
    logger.info("=" * 60)
    sys.exit(0)


if __name__ == "__main__":
    main()
