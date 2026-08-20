"""
c1_05_test_h2_masking.py
=========================
Tests H2: Aggregate metrics mask >= 50% of true
forecast error magnitude during extreme events.

Success criterion:
  masking percentage > 50% at overall NEM level

  masking = (extreme_MAE - aggregate_MAE)
            / extreme_MAE * 100

Input:  data/processed/aemo_nem_all_2021_2022_processed.csv
Output: results/tables/c1_05_h2_masking_results.csv

Project: forecast-reliability-indicator (FRI)
OSF:     10.17605/OSF.IO/Z89HD
"""

import sys
import pandas as pd
import numpy as np
from datetime import datetime

from config.settings import (
    PROCESSED_DIR,
    TABLES_DIR,
    NEM_REGIONS,
    H2_MASKING_THRESHOLD,
)
from config.logging_config import get_logger

logger = get_logger("c1_05_test_h2_masking")

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


def calculate_masking(df: pd.DataFrame, label: str) -> dict:
    """
    Calculate masking effect for a given subset of data.

    masking = what aggregate MAE hides about extreme MAE.
    masking % = (extreme_MAE - aggregate_MAE) / extreme_MAE * 100

    Args:
        df:    dataframe subset (all NEM or single region)
        label: label for logging
    """
    aggregate_mae = float(df["forecast_error"].mean())
    extreme_df    = df[df["regime"] == "extreme"]
    normal_df     = df[df["regime"] == "normal"]

    if len(extreme_df) == 0:
        logger.warning(f"{label}: no extreme events found")
        return {
            "label":          label,
            "total_intervals": len(df),
            "extreme_count":  0,
            "normal_count":   len(normal_df),
            "aggregate_mae":  round(aggregate_mae, 4),
            "extreme_mae":    None,
            "normal_mae":     round(float(normal_df["forecast_error"].mean()), 4),
            "masking_pct":    None,
            "passes_h2":      False,
            "note":           "no_extreme_events",
        }

    extreme_mae = float(extreme_df["forecast_error"].mean())
    normal_mae  = float(normal_df["forecast_error"].mean()) if len(normal_df) > 0 else 0

    masking_pct = (
        (extreme_mae - aggregate_mae) / extreme_mae * 100
        if extreme_mae > 0 else 0
    )

    passes = masking_pct > (H2_MASKING_THRESHOLD * 100)

    result = {
        "label":           label,
        "total_intervals": len(df),
        "extreme_count":   len(extreme_df),
        "normal_count":    len(normal_df),
        "aggregate_mae":   round(aggregate_mae, 4),
        "extreme_mae":     round(extreme_mae, 4),
        "normal_mae":      round(normal_mae, 4),
        "masking_pct":     round(masking_pct, 2),
        "passes_h2":       passes,
        "note":            "",
    }

    status = "PASS" if passes else "FAIL"
    logger.info(
        f"{label}: aggregate_MAE=${aggregate_mae:.2f} | "
        f"extreme_MAE=${extreme_mae:.2f} | "
        f"masking={masking_pct:.1f}% | {status}"
    )
    return result


def save_results(results: list, h2_passed: bool) -> object:
    """Save H2 results to results/tables/."""
    TABLES_DIR.mkdir(parents=True, exist_ok=True)
    output_path = TABLES_DIR / "c1_05_h2_masking_results.csv"

    df = pd.DataFrame(results)
    df["h2_overall_passed"] = h2_passed
    df.to_csv(output_path, index=False)
    logger.info(f"Results saved: {output_path}")
    return output_path


def main():
    logger.info("=" * 60)
    logger.info("c1_05_test_h2_masking.py started")
    logger.info(f"Timestamp: {datetime.now()}")
    logger.info(f"H2 threshold: masking > {H2_MASKING_THRESHOLD * 100:.0f}%")
    logger.info("=" * 60)

    df, is_sample = load_processed()

    results = []

    # Overall NEM level — primary H2 test
    logger.info("Testing H2 at overall NEM level...")
    overall = calculate_masking(df, "OVERALL_NEM")
    results.append(overall)

    # Per region — supplementary analysis
    logger.info("Testing H2 per region...")
    for region in NEM_REGIONS:
        region_df = df[df["REGIONID"] == region]
        result    = calculate_masking(region_df, region)
        results.append(result)

    # H2 passes on overall NEM result
    h2_passed = overall["passes_h2"]

    output_path = save_results(results, h2_passed)

    logger.info("=" * 60)
    logger.info(f"H2 RESULT: {'PASSED' if h2_passed else 'FAILED'}")

    if overall["masking_pct"] is not None:
        logger.info(f"Overall masking: {overall['masking_pct']:.1f}%")
        logger.info(f"Required:        > {H2_MASKING_THRESHOLD * 100:.0f}%")
    else:
        logger.warning("No extreme events in sample — H2 cannot be evaluated")

    if is_sample:
        logger.warning(
            "SAMPLE MODE: H2 result not meaningful — "
            "insufficient extreme events in 7-day sample. "
            "Re-run on full dataset after May 1 download."
        )

    if not h2_passed and not is_sample:
        logger.warning("H2 FAILED — initiate self-refine protocol")
        logger.warning("See PDD Section 4.2 for failure diagnosis")

    logger.info(f"Results: {output_path}")
    logger.info("Next: ./run.sh scripts/c1_06_test_h3_horizon.py")
    logger.info("=" * 60)
    sys.exit(0)


if __name__ == "__main__":
    main()
