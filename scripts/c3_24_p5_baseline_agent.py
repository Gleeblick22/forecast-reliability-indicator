"""
c3_11_p5_baseline_agent.py
============================
Simulates a P5-dispatching baseline agent, addressing
Critical review item #4: the original baseline dispatches
on the earliest forecast (up to 24h old), while the FRI
agent implicitly benefits from fresher information via its
revision feature. This agent dispatches on the P5 forecast
(~5 min lead), giving it comparably fresh information to
FRI's implicit access, isolating whether FRI's advantage
reflects genuine reliability detection or just information
recency.

Identical battery mechanics, trigger logic, and revenue
accounting to c3_01_baseline_agent.py; only the decision
price source differs (P5 forecast instead of earliest run).
Revenue computed on p_actual (genuine P5MIN-derived outcome,
consistent with the leakage-controlled experiment), not
last_forecast (which is itself only the final predispatch
run, not independently verified -- see EXP-011).

Input:  data/processed/aemo_nem_with_actual_price.csv
        data/raw/aemo_nem/aemo_nem_p5min_actual_2021_2022_raw.csv
Output: results/tables/c3_11_p5_baseline_agent_results.csv
"""
import sys
import pandas as pd
import numpy as np
from datetime import datetime
from config.settings import (
    PROCESSED_DIR, AEMO_RAW_DIR, TABLES_DIR, TRAIN_TEST_SPLIT,
    DISPATCH_THRESHOLD, BATTERY_CAPACITY_MWH, BATTERY_POWER_MW,
    BATTERY_SOC_MIN, BATTERY_SOC_MAX, BATTERY_SOC_INITIAL,
    BATTERY_DISCHARGE_EFF, BATTERY_MIN_DISPATCH_MW,
    BATTERY_SOC_RESET_DAILY, BATTERY_SOC_RESET_VALUE,
)
from config.logging_config import get_logger

logger = get_logger("c3_11_p5_baseline_agent")

MAIN_FILE   = PROCESSED_DIR / "aemo_nem_with_actual_price.csv"
P5MIN_FILE  = AEMO_RAW_DIR / "aemo_nem_p5min_actual_2021_2022_raw.csv"
OUTPUT_FILE = TABLES_DIR / "c3_11_p5_baseline_agent_results.csv"
INTERVAL_HOURS = 0.5

def load_p5_decision_price() -> pd.DataFrame:
    """
    For each (REGIONID, DATETIME), find the P5MIN forecast
    with lead time closest to 5 minutes -- the decision price
    a real operator would actually have at dispatch time.
    """
    logger.info("Loading P5MIN data to derive ~5-min-lead decision price...")
    p5 = pd.read_csv(P5MIN_FILE, parse_dates=["RUN_DATETIME", "INTERVAL_DATETIME"])
    p5["lead_minutes"] = (p5["INTERVAL_DATETIME"] - p5["RUN_DATETIME"]).dt.total_seconds() / 60
    p5 = p5[(p5["lead_minutes"] >= 0) & (p5["lead_minutes"] <= 10)]  # near-5-min window
    p5["dist_from_5"] = (p5["lead_minutes"] - 5).abs()
    p5 = p5.sort_values("dist_from_5").groupby(
        ["REGIONID", "INTERVAL_DATETIME"], as_index=False).first()
    p5 = p5.rename(columns={"INTERVAL_DATETIME": "DATETIME", "RRP": "p5_decision_price"})
    p5 = p5[["DATETIME", "REGIONID", "p5_decision_price", "lead_minutes"]]
    logger.info(f"P5 decision-price rows: {len(p5):,}")
    logger.info(f"Actual lead time stats:\n{p5['lead_minutes'].describe()}")
    return p5

def load_test_data() -> pd.DataFrame:
    df = pd.read_csv(MAIN_FILE, parse_dates=["DATETIME"])
    split_date = pd.Timestamp(TRAIN_TEST_SPLIT)
    test = df[df["DATETIME"] >= split_date].copy()

    p5 = load_p5_decision_price()
    test = test.merge(p5[["DATETIME", "REGIONID", "p5_decision_price"]],
                       on=["DATETIME", "REGIONID"], how="left")
    before = len(test)
    test = test.dropna(subset=["p5_decision_price", "p_actual"])
    logger.info(f"Test rows before dropping unmatched P5/actual: {before:,}")
    logger.info(f"Test rows after: {len(test):,}")

    test = test.sort_values("DATETIME").reset_index(drop=True)
    logger.info(f"Date range: {test['DATETIME'].min()} to {test['DATETIME'].max()}")
    return test

def simulate_p5_baseline_agent(df: pd.DataFrame) -> pd.DataFrame:
    logger.info("Simulating P5-dispatching baseline agent...")
    logger.info("Decision price: p5_decision_price (~5 min lead)")
    logger.info("Revenue price:  p_actual (genuine P5MIN-derived outcome)")

    results      = []
    soc          = BATTERY_SOC_INITIAL
    current_date = None

    for _, row in df.iterrows():
        interval_date = pd.Timestamp(row["DATETIME"]).date()
        if BATTERY_SOC_RESET_DAILY and interval_date != current_date:
            soc          = BATTERY_SOC_RESET_VALUE
            current_date = interval_date

        decision_price = row["p5_decision_price"]
        revenue_price  = row["p_actual"]
        regime         = row.get("regime", "normal")

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

        revenue          = dispatch_mw * BATTERY_DISCHARGE_EFF * revenue_price * INTERVAL_HOURS
        expected_revenue = dispatch_mw * BATTERY_DISCHARGE_EFF * decision_price * INTERVAL_HOURS
        revenue_error    = expected_revenue - revenue

        forecast_error = abs(decision_price - revenue_price)
        is_silent_failure = (
            should_dispatch and regime == "extreme" and forecast_error > DISPATCH_THRESHOLD
        )

        results.append({
            "DATETIME": row["DATETIME"], "REGIONID": row.get("REGIONID", "NSW1"),
            "regime": regime, "p5_decision_price": decision_price,
            "p_actual": revenue_price, "forecast_error": forecast_error,
            "should_dispatch": should_dispatch, "dispatch_mw": dispatch_mw,
            "soc": round(soc, 4), "revenue": round(revenue, 4),
            "expected_revenue": round(expected_revenue, 4),
            "revenue_error": round(revenue_error, 4),
            "is_silent_failure": is_silent_failure, "agent_type": "p5_baseline",
        })

    results_df = pd.DataFrame(results)
    logger.info(f"Total revenue:   ${results_df['revenue'].sum():,.2f}")
    logger.info(f"Silent failures: {results_df['is_silent_failure'].sum():,}")
    logger.info(f"Dispatch intervals: {results_df['should_dispatch'].sum():,}")
    return results_df

def main():
    logger.info("=" * 60)
    logger.info("c3_11_p5_baseline_agent.py started")
    logger.info(f"Timestamp: {datetime.now()}")
    logger.info(f"Dispatch threshold: ${DISPATCH_THRESHOLD}/MWh")
    logger.info(f"Battery: {BATTERY_CAPACITY_MWH}MWh {BATTERY_POWER_MW}MW")
    logger.info("Addresses Critical review item #4 (baseline strawman)")
    logger.info("=" * 60)

    test_data = load_test_data()
    results   = simulate_p5_baseline_agent(test_data)

    TABLES_DIR.mkdir(parents=True, exist_ok=True)
    results.to_csv(OUTPUT_FILE, index=False)
    logger.info(f"Saved: {OUTPUT_FILE}")
    logger.info("=" * 60)
    sys.exit(0)

if __name__ == "__main__":
    main()
