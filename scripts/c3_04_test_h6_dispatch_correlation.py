"""
c3_04_test_h6_dispatch_correlation.py
=======================================
Tests H6 hypothesis — dispatch correlation.

H6: FRI confidence scores positively and
    significantly correlated with dispatch size.
    Success: Pearson correlation positive AND p < 0.05.

Input:  results/tables/c3_02_fri_agent_results.csv
Output: results/tables/c3_04_h6_dispatch_correlation_results.csv

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
    H6_PVALUE_THRESHOLD,
)
from config.logging_config import get_logger

logger = get_logger("c3_04_test_h6_dispatch_correlation")

FRI_FILE    = TABLES_DIR / "c3_02_fri_agent_results.csv"
OUTPUT_FILE = TABLES_DIR / "c3_04_h6_dispatch_correlation_results.csv"


def load_fri_results() -> pd.DataFrame:
    """Load FRI agent results."""
    if not FRI_FILE.exists():
        logger.error(f"File not found: {FRI_FILE}")
        sys.exit(1)

    df = pd.read_csv(FRI_FILE, parse_dates=["DATETIME"])
    logger.info(f"FRI results loaded: {len(df):,} intervals")
    return df


def test_h6(df: pd.DataFrame) -> dict:
    """
    Test H6 hypothesis.
    Pearson correlation between FRI score and dispatch size.
    Uses only intervals where dispatch > 0.
    """
    # Use only dispatched intervals
    dispatched = df[df["dispatch_mw"] > 0].copy()
    logger.info(f"Dispatched intervals: {len(dispatched):,}")

    if len(dispatched) < 10:
        logger.warning("Insufficient dispatched intervals for correlation")
        return {
            "n_intervals":   len(dispatched),
            "correlation":   None,
            "p_value":       None,
            "passes_h6":     False,
            "note":          "insufficient_data",
        }

    fri_scores  = dispatched["fri_score"].values
    dispatch_mw = dispatched["dispatch_mw"].values

    corr, p_value = stats.pearsonr(fri_scores, dispatch_mw)
    passes_h6 = (corr > 0) and (p_value < H6_PVALUE_THRESHOLD)

    logger.info(f"=== H6 FORMAL EVALUATION ===")
    logger.info(f"Dispatched intervals: {len(dispatched):,}")
    logger.info(f"Pearson correlation:  {corr:.4f}")
    logger.info(f"p-value:              {p_value:.4f}")
    logger.info(f"Direction positive:   {corr > 0}")
    logger.info(f"p < {H6_PVALUE_THRESHOLD}:              {p_value < H6_PVALUE_THRESHOLD}")
    logger.info(f"H6 RESULT:            {'PASSED' if passes_h6 else 'FAILED'}")

    # Per band analysis
    for band in ["HIGH", "MEDIUM", "LOW"]:
        band_data = dispatched[dispatched["fri_band"] == band]
        if len(band_data) > 0:
            logger.info(
                f"  {band}: n={len(band_data):,} "
                f"mean_dispatch={band_data['dispatch_mw'].mean():.2f}MW "
                f"mean_fri={band_data['fri_score'].mean():.4f}"
            )

    return {
        "n_intervals":        len(dispatched),
        "pearson_correlation": round(corr, 4),
        "p_value":            round(p_value, 6),
        "direction_positive": bool(corr > 0),
        "p_significant":      bool(p_value < H6_PVALUE_THRESHOLD),
        "h6_threshold":       H6_PVALUE_THRESHOLD,
        "passes_h6":          passes_h6,
        "high_mean_dispatch": round(dispatched[dispatched["fri_band"]=="HIGH"]["dispatch_mw"].mean(), 2) if len(dispatched[dispatched["fri_band"]=="HIGH"]) > 0 else 0,
        "med_mean_dispatch":  round(dispatched[dispatched["fri_band"]=="MEDIUM"]["dispatch_mw"].mean(), 2) if len(dispatched[dispatched["fri_band"]=="MEDIUM"]) > 0 else 0,
        "low_mean_dispatch":  round(dispatched[dispatched["fri_band"]=="LOW"]["dispatch_mw"].mean(), 2) if len(dispatched[dispatched["fri_band"]=="LOW"]) > 0 else 0,
    }


def main():
    logger.info("=" * 60)
    logger.info("c3_04_test_h6_dispatch_correlation.py started")
    logger.info(f"Timestamp: {datetime.now()}")
    logger.info(f"H6 threshold: correlation positive AND p < {H6_PVALUE_THRESHOLD}")
    logger.info("=" * 60)

    fri_results = load_fri_results()

    logger.info("Testing H6 dispatch correlation...")
    h6_result = test_h6(fri_results)

    TABLES_DIR.mkdir(parents=True, exist_ok=True)
    pd.DataFrame([h6_result]).to_csv(OUTPUT_FILE, index=False)
    logger.info(f"Saved: {OUTPUT_FILE}")

    logger.info("=" * 60)
    logger.info(f"H6 RESULT: {'PASSED' if h6_result['passes_h6'] else 'FAILED'}")
    logger.info(f"Correlation: {h6_result['pearson_correlation']}")
    logger.info(f"p-value:     {h6_result['p_value']}")
    logger.info("Next: ./run.sh scripts/c3_05_test_h7_revenue_comparison.py")
    logger.info("=" * 60)
    sys.exit(0)


if __name__ == "__main__":
    main()
