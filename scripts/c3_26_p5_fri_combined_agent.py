"""
c3_13_p5_fri_combined_agent.py
=================================
The critical test agent: combines P5 decision timing
(fresh information, like c3_11) WITH FRI's graded band
scaling (like c3_02), to isolate whether the reliability
signal adds value ON TOP OF information freshness, once
freshness is no longer a confound (Critical #4, final test).

If this agent outperforms the P5-baseline alone (c3_11),
that is evidence the reliability signal has genuine
incremental value. If not, the signal's apparent value in
the original comparison was substantially attributable to
information timing, not reliability detection.

Input:  data/processed/aemo_nem_with_actual_price.csv
        results/tables/c3_02_fri_agent_results.csv (for fri_score, fri_band)
Output: results/tables/c3_13_p5_fri_combined_results.csv
"""
import sys
import pandas as pd
from config.settings import (
    PROCESSED_DIR, AEMO_RAW_DIR, TABLES_DIR, TRAIN_TEST_SPLIT,
    DISPATCH_THRESHOLD, BATTERY_CAPACITY_MWH, BATTERY_POWER_MW,
    BATTERY_SOC_MIN, BATTERY_SOC_MAX, BATTERY_SOC_INITIAL,
    BATTERY_DISCHARGE_EFF, BATTERY_MIN_DISPATCH_MW,
    BATTERY_SOC_RESET_DAILY, BATTERY_SOC_RESET_VALUE,
)
from config.logging_config import get_logger

logger = get_logger("c3_13_p5_fri_combined_agent")

MAIN_FILE     = PROCESSED_DIR / "aemo_nem_with_actual_price.csv"
P5MIN_FILE    = AEMO_RAW_DIR / "aemo_nem_p5min_actual_2021_2022_raw.csv"
FRI_FILE      = TABLES_DIR / "c3_02_fri_agent_results.csv"
OUTPUT_FILE   = TABLES_DIR / "c3_13_p5_fri_combined_results.csv"
INTERVAL_HOURS = 0.5

DISPATCH_FACTORS = {"HIGH": 1.00, "MEDIUM": 0.75, "LOW": 0.25}

def load_p5_decision_price():
    p5 = pd.read_csv(P5MIN_FILE, parse_dates=["RUN_DATETIME", "INTERVAL_DATETIME"])
    p5["lead_minutes"] = (p5["INTERVAL_DATETIME"] - p5["RUN_DATETIME"]).dt.total_seconds() / 60
    p5 = p5[(p5["lead_minutes"] >= 0) & (p5["lead_minutes"] <= 10)]
    p5["dist_from_5"] = (p5["lead_minutes"] - 5).abs()
    p5 = p5.sort_values("dist_from_5").groupby(
        ["REGIONID", "INTERVAL_DATETIME"], as_index=False).first()
    p5 = p5.rename(columns={"INTERVAL_DATETIME": "DATETIME", "RRP": "p5_decision_price"})
    return p5[["DATETIME", "REGIONID", "p5_decision_price"]]

def load_test_data():
    df = pd.read_csv(MAIN_FILE, parse_dates=["DATETIME"])
    split_date = pd.Timestamp(TRAIN_TEST_SPLIT)
    test = df[df["DATETIME"] >= split_date].copy()

    p5 = load_p5_decision_price()
    test = test.merge(p5, on=["DATETIME", "REGIONID"], how="left")

    fri = pd.read_csv(FRI_FILE, parse_dates=["DATETIME"])
    test = test.merge(fri[["DATETIME", "REGIONID", "fri_score", "fri_band"]],
                       on=["DATETIME", "REGIONID"], how="left")

    before = len(test)
    test = test.dropna(subset=["p5_decision_price", "p_actual", "fri_band"])
    logger.info(f"Rows before dropping unmatched: {before:,}")
    logger.info(f"Rows after: {len(test):,}")
    return test.sort_values("DATETIME").reset_index(drop=True)

def simulate(df):
    logger.info("Simulating P5-decision + FRI-band-scaling combined agent...")
    results = []
    soc = BATTERY_SOC_INITIAL
    current_date = None

    for _, row in df.iterrows():
        interval_date = pd.Timestamp(row["DATETIME"]).date()
        if BATTERY_SOC_RESET_DAILY and interval_date != current_date:
            soc = BATTERY_SOC_RESET_VALUE
            current_date = interval_date

        decision_price = row["p5_decision_price"]
        revenue_price  = row["p_actual"]
        regime         = row.get("regime", "normal")
        fri_band       = row["fri_band"]
        dispatch_factor = DISPATCH_FACTORS.get(fri_band, 0.75)

        should_dispatch = decision_price >= DISPATCH_THRESHOLD

        if should_dispatch and soc > BATTERY_SOC_MIN:
            max_dispatch = min(BATTERY_POWER_MW,
                                (soc - BATTERY_SOC_MIN) * BATTERY_CAPACITY_MWH / INTERVAL_HOURS)
            dispatch_mw = max(BATTERY_MIN_DISPATCH_MW, max_dispatch * dispatch_factor)
            energy_discharged = dispatch_mw * INTERVAL_HOURS
            soc -= energy_discharged / BATTERY_CAPACITY_MWH
        else:
            dispatch_mw = 0.0

        soc = max(BATTERY_SOC_MIN, min(BATTERY_SOC_MAX, soc))
        revenue = dispatch_mw * BATTERY_DISCHARGE_EFF * revenue_price * INTERVAL_HOURS
        genuine_error = abs(decision_price - revenue_price)
        is_silent_failure = should_dispatch and regime == "extreme" and genuine_error > 100

        results.append({
            "DATETIME": row["DATETIME"], "REGIONID": row["REGIONID"], "regime": regime,
            "p5_decision_price": decision_price, "p_actual": revenue_price,
            "fri_band": fri_band, "dispatch_factor": dispatch_factor,
            "should_dispatch": should_dispatch, "dispatch_mw": dispatch_mw,
            "revenue": round(revenue, 4), "is_silent_failure": is_silent_failure,
            "agent_type": "p5_fri_combined",
        })

    results_df = pd.DataFrame(results)
    logger.info(f"Total revenue: ${results_df['revenue'].sum():,.2f}")
    logger.info(f"Silent failures: {results_df['is_silent_failure'].sum():,}")
    return results_df

def main():
    logger.info("=" * 60)
    logger.info("c3_13_p5_fri_combined_agent.py started")
    logger.info("Testing whether FRI signal adds value beyond info freshness")
    logger.info("=" * 60)
    test_data = load_test_data()
    results = simulate(test_data)
    TABLES_DIR.mkdir(parents=True, exist_ok=True)
    results.to_csv(OUTPUT_FILE, index=False)
    logger.info(f"Saved: {OUTPUT_FILE}")
    logger.info("=" * 60)
    sys.exit(0)

if __name__ == "__main__":
    main()
