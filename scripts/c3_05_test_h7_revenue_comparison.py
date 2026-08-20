"""
c3_05_test_h7_revenue_comparison.py
=====================================
Tests H7 hypothesis — revenue improvement.

H7: FRI agent achieves >= 15% higher simulated
    revenue vs baseline agent.

Input:  results/tables/c3_01_baseline_agent_results.csv
        results/tables/c3_02_fri_agent_results.csv
Output: results/tables/c3_05_h7_revenue_comparison_results.csv

Project: forecast-reliability-indicator (FRI)
OSF:     10.17605/OSF.IO/Z89HD
"""

import sys
import pandas as pd
import numpy as np
from datetime import datetime
from pathlib import Path

from config.settings import (
    TABLES_DIR,
    H7_REVENUE_THRESHOLD,
)
from config.logging_config import get_logger

logger = get_logger("c3_05_test_h7_revenue_comparison")

BASELINE_FILE = TABLES_DIR / "c3_01_baseline_agent_results.csv"
FRI_FILE      = TABLES_DIR / "c3_02_fri_agent_results.csv"
OUTPUT_FILE   = TABLES_DIR / "c3_05_h7_revenue_comparison_results.csv"


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


def calculate_revenue_stats(df: pd.DataFrame, agent_type: str) -> dict:
    """Calculate revenue statistics."""
    total_revenue    = df["revenue"].sum()
    mean_revenue     = df["revenue"].mean()
    dispatch_revenue = df[df["dispatch_mw"] > 0]["revenue"].sum()
    dispatch_count   = (df["dispatch_mw"] > 0).sum()

    logger.info(f"{agent_type}:")
    logger.info(f"  Total revenue:    ${total_revenue:,.2f}")
    logger.info(f"  Mean per interval: ${mean_revenue:.4f}")
    logger.info(f"  Dispatch revenue: ${dispatch_revenue:,.2f}")
    logger.info(f"  Dispatch count:   {dispatch_count:,}")

    return {
        "agent_type":       agent_type,
        "total_revenue":    round(total_revenue, 2),
        "mean_revenue":     round(mean_revenue, 4),
        "dispatch_revenue": round(dispatch_revenue, 2),
        "dispatch_count":   int(dispatch_count),
    }


def test_h7(baseline_stats: dict, fri_stats: dict) -> dict:
    """
    Test H7 hypothesis.
    H7 passes if FRI revenue >= 15% higher than baseline.
    """
    baseline_rev = baseline_stats["total_revenue"]
    fri_rev      = fri_stats["total_revenue"]

    if baseline_rev == 0:
        logger.warning("Baseline revenue is zero — H7 cannot be tested")
        improvement_pct = 0.0
        passes_h7 = False
    elif baseline_rev < 0:
        logger.warning("Baseline revenue is negative")
        improvement_pct = (fri_rev - baseline_rev) / abs(baseline_rev) * 100
        passes_h7 = improvement_pct >= H7_REVENUE_THRESHOLD * 100
    else:
        improvement_pct = (fri_rev - baseline_rev) / baseline_rev * 100
        passes_h7 = improvement_pct >= H7_REVENUE_THRESHOLD * 100

    revenue_diff = fri_rev - baseline_rev

    logger.info(f"=== H7 FORMAL EVALUATION ===")
    logger.info(f"Baseline revenue:   ${baseline_rev:,.2f}")
    logger.info(f"FRI revenue:        ${fri_rev:,.2f}")
    logger.info(f"Difference:         ${revenue_diff:,.2f}")
    logger.info(f"Improvement:        {improvement_pct:.2f}%")
    logger.info(f"H7 threshold:       >= {H7_REVENUE_THRESHOLD*100:.0f}%")
    logger.info(f"H7 RESULT:          {'PASSED' if passes_h7 else 'FAILED'}")

    return {
        "baseline_revenue":    baseline_rev,
        "fri_revenue":         fri_rev,
        "revenue_difference":  round(revenue_diff, 2),
        "improvement_pct":     round(improvement_pct, 4),
        "h7_threshold_pct":    H7_REVENUE_THRESHOLD * 100,
        "passes_h7":           passes_h7,
    }


def revenue_by_regime(baseline: pd.DataFrame, fri: pd.DataFrame) -> dict:
    """Breakdown revenue by regime for manuscript."""
    results = {}
    for regime in ["extreme", "normal"]:
        b_rev = baseline[baseline["regime"]==regime]["revenue"].sum()
        f_rev = fri[fri["regime"]==regime]["revenue"].sum()
        if b_rev != 0:
            imp = (f_rev - b_rev) / abs(b_rev) * 100
        else:
            imp = 0.0
        results[f"{regime}_baseline_revenue"] = round(b_rev, 2)
        results[f"{regime}_fri_revenue"]      = round(f_rev, 2)
        results[f"{regime}_improvement_pct"]  = round(imp, 2)
        logger.info(
            f"  {regime}: baseline=${b_rev:,.2f} "
            f"fri=${f_rev:,.2f} improvement={imp:.2f}%"
        )
    return results


def main():
    logger.info("=" * 60)
    logger.info("c3_05_test_h7_revenue_comparison.py started")
    logger.info(f"Timestamp: {datetime.now()}")
    logger.info(f"H7 threshold: revenue improvement >= {H7_REVENUE_THRESHOLD*100:.0f}%")
    logger.info("=" * 60)

    baseline, fri = load_results()

    logger.info("Calculating baseline revenue...")
    baseline_stats = calculate_revenue_stats(baseline, "baseline")

    logger.info("Calculating FRI revenue...")
    fri_stats = calculate_revenue_stats(fri, "fri")

    logger.info("Testing H7...")
    h7_result = test_h7(baseline_stats, fri_stats)

    logger.info("Revenue breakdown by regime...")
    regime_breakdown = revenue_by_regime(baseline, fri)

    output = {**baseline_stats, **fri_stats, **h7_result, **regime_breakdown}
    TABLES_DIR.mkdir(parents=True, exist_ok=True)
    pd.DataFrame([output]).to_csv(OUTPUT_FILE, index=False)
    logger.info(f"Saved: {OUTPUT_FILE}")

    logger.info("=" * 60)
    logger.info(f"H7 RESULT: {'PASSED' if h7_result['passes_h7'] else 'FAILED'}")
    logger.info(f"Improvement: {h7_result['improvement_pct']:.2f}%")
    logger.info(f"Required:    >= {H7_REVENUE_THRESHOLD*100:.0f}%")
    logger.info("Next: ./run.sh scripts/c3_06_test_h8_ercot_validation.py")
    logger.info("=" * 60)
    sys.exit(0)


if __name__ == "__main__":
    main()
