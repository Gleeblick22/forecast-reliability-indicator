"""
c3_01_baseline_agent.py
========================
Simulates baseline battery dispatch agent
WITHOUT FRI signal. Pure forecast-following.

CORRECT MODEL (D-008 self-refine cycle 2):
  Decision price = first_forecast (earliest RRP)
  Revenue price  = last_forecast  (actual settlement RRP)
  This models real battery dispatch where agent
  decides based on forecast but earns actual price.

Agent dispatches when first_forecast >= $100/MWh.
No signal reliability detection.
SOC reset daily at 50% (Decision 13).

Input:  data/processed/aemo_nem_all_2021_2022_processed.csv
Output: results/tables/c3_01_baseline_agent_results.csv

Project: forecast-reliability-indicator (FRI)
OSF:     10.17605/OSF.IO/Z89HD
"""

import sys
import pandas as pd
import numpy as np
from datetime import datetime
from pathlib import Path

from config.settings import (
    PROCESSED_DIR,
    TABLES_DIR,
    TRAIN_TEST_SPLIT,
    DISPATCH_THRESHOLD,
    BATTERY_CAPACITY_MWH,
    BATTERY_POWER_MW,
    BATTERY_SOC_MIN,
    BATTERY_SOC_MAX,
    BATTERY_SOC_INITIAL,
    BATTERY_DISCHARGE_EFF,
    BATTERY_MIN_DISPATCH_MW,
    BATTERY_SOC_RESET_DAILY,
    BATTERY_SOC_RESET_VALUE,
)
from config.logging_config import get_logger

logger = get_logger("c3_01_baseline_agent")

PROCESSED_FILE = PROCESSED_DIR / "aemo_nem_all_2021_2022_processed.csv"
OUTPUT_FILE    = TABLES_DIR    / "c3_01_baseline_agent_results.csv"
INTERVAL_HOURS = 0.5


def load_test_data() -> pd.DataFrame:
    """Load test partition only (after split date)."""
    df = pd.read_csv(PROCESSED_FILE, parse_dates=["DATETIME"])
    split_date = pd.Timestamp(TRAIN_TEST_SPLIT)
    test = df[df["DATETIME"] >= split_date].copy()
    test = test.sort_values("DATETIME").reset_index(drop=True)

    logger.info(f"Test partition: {len(test):,} intervals")
    logger.info(f"Date range: {test['DATETIME'].min()} to {test['DATETIME'].max()}")
    logger.info(f"Extreme intervals: {test['regime'].eq('extreme').sum():,}")
    logger.info(f"Columns: {list(test.columns)}")
    return test


def simulate_baseline_agent(df: pd.DataFrame) -> pd.DataFrame:
    """
    Simulate baseline agent without FRI.
    Decision based on FIRST (earliest) forecast RRP.
    Revenue based on LAST (actual) forecast RRP.
    This is the correct real-world dispatch model.
    Reference: Krishnamurthy et al 2018 IEEE Trans Power Systems
    """
    logger.info("Simulating baseline agent...")
    logger.info("Decision price: first_forecast (earliest RRP)")
    logger.info("Revenue price:  last_forecast  (actual settlement RRP)")

    results      = []
    soc          = BATTERY_SOC_INITIAL
    current_date = None

    for _, row in df.iterrows():
        interval_date = pd.Timestamp(row["DATETIME"]).date()

        if BATTERY_SOC_RESET_DAILY and interval_date != current_date:
            soc          = BATTERY_SOC_RESET_VALUE
            current_date = interval_date

        # Decision price = earliest forecast (what agent knew)
        decision_price = row.get("first_forecast", 0)

        # Revenue price = latest forecast (actual settlement)
        revenue_price  = row.get("last_forecast", 0)

        regime         = row.get("regime", "normal")
        forecast_error = row.get("forecast_error", 0)

        # Baseline dispatches if DECISION price >= threshold
        should_dispatch = decision_price >= DISPATCH_THRESHOLD

        if should_dispatch and soc > BATTERY_SOC_MIN:
            max_dispatch = min(
                BATTERY_POWER_MW,
                (soc - BATTERY_SOC_MIN) * BATTERY_CAPACITY_MWH / INTERVAL_HOURS
            )
            dispatch_mw       = max(BATTERY_MIN_DISPATCH_MW, max_dispatch)
            energy_discharged = dispatch_mw * INTERVAL_HOURS
            soc              -= energy_discharged / BATTERY_CAPACITY_MWH
        else:
            dispatch_mw       = 0.0
            energy_discharged = 0.0

        soc = max(BATTERY_SOC_MIN, min(BATTERY_SOC_MAX, soc))

        # Revenue on ACTUAL price not decision price
        revenue = dispatch_mw * BATTERY_DISCHARGE_EFF * revenue_price * INTERVAL_HOURS

        # Revenue error = what agent expected vs what it got
        expected_revenue = dispatch_mw * BATTERY_DISCHARGE_EFF * decision_price * INTERVAL_HOURS
        revenue_error    = expected_revenue - revenue

        # Silent failure: dispatched on bad signal
        is_silent_failure = (
            should_dispatch and
            regime == "extreme" and
            abs(forecast_error) > DISPATCH_THRESHOLD
        )

        results.append({
            "DATETIME":        row["DATETIME"],
            "REGIONID":        row.get("REGIONID", "NSW1"),
            "regime":          regime,
            "first_forecast":  decision_price,
            "last_forecast":   revenue_price,
            "forecast_error":  forecast_error,
            "should_dispatch": should_dispatch,
            "dispatch_mw":     dispatch_mw,
            "soc":             round(soc, 4),
            "revenue":         round(revenue, 4),
            "expected_revenue": round(expected_revenue, 4),
            "revenue_error":   round(revenue_error, 4),
            "is_silent_failure": is_silent_failure,
            "fri_score":       None,
            "fri_band":        None,
            "agent_type":      "baseline",
        })

    results_df = pd.DataFrame(results)

    total_revenue   = results_df["revenue"].sum()
    total_error     = results_df["revenue_error"].sum()
    silent_failures = results_df["is_silent_failure"].sum()
    dispatch_count  = results_df["should_dispatch"].sum()

    logger.info(f"Total revenue:       ${total_revenue:,.2f}")
    logger.info(f"Total revenue error: ${total_error:,.2f}")
    logger.info(f"Dispatch intervals:  {dispatch_count:,}")
    logger.info(f"Silent failures:     {silent_failures:,}")

    return results_df


def main():
    logger.info("=" * 60)
    logger.info("c3_01_baseline_agent.py started")
    logger.info(f"Timestamp: {datetime.now()}")
    logger.info(f"Dispatch threshold: ${DISPATCH_THRESHOLD}/MWh")
    logger.info(f"Battery: {BATTERY_CAPACITY_MWH}MWh {BATTERY_POWER_MW}MW")
    logger.info("NO FRI — pure forecast following agent")
    logger.info("MODEL: forecast vs actual price (D-008)")
    logger.info("=" * 60)

    test_data = load_test_data()
    results   = simulate_baseline_agent(test_data)

    TABLES_DIR.mkdir(parents=True, exist_ok=True)
    results.to_csv(OUTPUT_FILE, index=False)
    logger.info(f"Saved: {OUTPUT_FILE}")

    logger.info("=" * 60)
    logger.info("c3_01 COMPLETE")
    logger.info(f"Total revenue:   ${results['revenue'].sum():,.2f}")
    logger.info(f"Revenue error:   ${results['revenue_error'].sum():,.2f}")
    logger.info(f"Silent failures: {results['is_silent_failure'].sum():,}")
    logger.info("Next: ./run.sh scripts/c3_02_fri_agent.py")
    logger.info("=" * 60)
    sys.exit(0)


if __name__ == "__main__":
    main()
