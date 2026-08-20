"""
c3_03_test_h5_silent_failure.py
================================
Tests H5 hypothesis — silent failure reduction.

H5: FRI agent experiences >= 20% fewer silent
    failure windows vs baseline agent.

Silent failure window: period where agent dispatches
suboptimally due to undetected signal unreliability.

Input:  results/tables/c3_01_baseline_agent_results.csv
        results/tables/c3_02_fri_agent_results.csv
Output: results/tables/c3_03_h5_silent_failure_results.csv

Project: forecast-reliability-indicator (FRI)
OSF:     10.17605/OSF.IO/Z89HD
"""

import sys
import pandas as pd
import numpy as np
from datetime import datetime
from pathlib import Path
from scipy import stats

from config.settings import (
    TABLES_DIR,
    H5_REDUCTION_THRESHOLD,
)
from config.logging_config import get_logger

logger = get_logger("c3_03_test_h5_silent_failure")

BASELINE_FILE = TABLES_DIR / "c3_01_baseline_agent_results.csv"
FRI_FILE      = TABLES_DIR / "c3_02_fri_agent_results.csv"
OUTPUT_FILE   = TABLES_DIR / "c3_03_h5_silent_failure_results.csv"


def load_results() -> tuple:
    """Load baseline and FRI agent results."""
    for f in [BASELINE_FILE, FRI_FILE]:
        if not f.exists():
            logger.error(f"File not found: {f}")
            sys.exit(1)

    baseline = pd.read_csv(BASELINE_FILE, parse_dates=["DATETIME"])
    fri      = pd.read_csv(FRI_FILE,      parse_dates=["DATETIME"])

    logger.info(f"Baseline: {len(baseline):,} intervals")
    logger.info(f"FRI:      {len(fri):,} intervals")

    return baseline, fri


def calculate_silent_failures(df: pd.DataFrame, agent_type: str) -> dict:
    """Calculate silent failure statistics."""
    total_intervals    = len(df)
    dispatch_intervals = df["should_dispatch"].sum()
    silent_failures    = df["is_silent_failure"].sum()
    silent_rate        = silent_failures / total_intervals * 100

    logger.info(f"{agent_type}:")
    logger.info(f"  Total intervals:    {total_intervals:,}")
    logger.info(f"  Dispatch intervals: {dispatch_intervals:,}")
    logger.info(f"  Silent failures:    {silent_failures:,}")
    logger.info(f"  Silent failure rate: {silent_rate:.2f}%")

    return {
        "agent_type":        agent_type,
        "total_intervals":   total_intervals,
        "dispatch_intervals": int(dispatch_intervals),
        "silent_failures":   int(silent_failures),
        "silent_rate_pct":   round(silent_rate, 4),
    }


def test_h5(baseline_stats: dict, fri_stats: dict) -> dict:
    """
    Test H5 hypothesis.
    H5 passes if FRI reduces silent failures by >= 20%.
    """
    baseline_sf = baseline_stats["silent_failures"]
    fri_sf      = fri_stats["silent_failures"]

    if baseline_sf == 0:
        logger.warning("Baseline has zero silent failures — H5 cannot be tested")
        reduction_pct = 0.0
        passes_h5     = False
    else:
        reduction_pct = (baseline_sf - fri_sf) / baseline_sf * 100
        passes_h5     = reduction_pct >= H5_REDUCTION_THRESHOLD * 100

    logger.info(f"=== H5 FORMAL EVALUATION ===")
    logger.info(f"Baseline silent failures: {baseline_sf:,}")
    logger.info(f"FRI silent failures:      {fri_sf:,}")
    logger.info(f"Reduction:                {reduction_pct:.2f}%")
    logger.info(f"H5 threshold:             >= {H5_REDUCTION_THRESHOLD*100:.0f}%")
    logger.info(f"H5 RESULT:                {'PASSED' if passes_h5 else 'FAILED'}")

    return {
        "baseline_silent_failures": baseline_sf,
        "fri_silent_failures":      fri_sf,
        "reduction_pct":            round(reduction_pct, 4),
        "h5_threshold_pct":         H5_REDUCTION_THRESHOLD * 100,
        "passes_h5":                passes_h5,
        "baseline_silent_rate":     baseline_stats["silent_rate_pct"],
        "fri_silent_rate":          fri_stats["silent_rate_pct"],
    }


def main():
    logger.info("=" * 60)
    logger.info("c3_03_test_h5_silent_failure.py started")
    logger.info(f"Timestamp: {datetime.now()}")
    logger.info(f"H5 threshold: reduction >= {H5_REDUCTION_THRESHOLD*100:.0f}%")
    logger.info("=" * 60)

    baseline, fri = load_results()

    logger.info("Calculating baseline silent failures...")
    baseline_stats = calculate_silent_failures(baseline, "baseline")

    logger.info("Calculating FRI silent failures...")
    fri_stats = calculate_silent_failures(fri, "fri")

    logger.info("Testing H5...")
    h5_result = test_h5(baseline_stats, fri_stats)

    output = {**baseline_stats, **fri_stats, **h5_result}
    pd.DataFrame([output]).to_csv(OUTPUT_FILE, index=False)
    logger.info(f"Saved: {OUTPUT_FILE}")

    logger.info("=" * 60)
    logger.info(f"H5 RESULT: {'PASSED' if h5_result['passes_h5'] else 'FAILED'}")
    logger.info(f"Reduction: {h5_result['reduction_pct']:.2f}%")
    logger.info(f"Required:  >= {H5_REDUCTION_THRESHOLD*100:.0f}%")
    logger.info("Next: ./run.sh scripts/c3_04_test_h6_dispatch_correlation.py")
    logger.info("=" * 60)
    sys.exit(0)


if __name__ == "__main__":
    main()
