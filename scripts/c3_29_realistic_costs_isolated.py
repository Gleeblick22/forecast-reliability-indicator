"""
c3_16_realistic_costs_isolated.py
====================================
Corrected version of c3_14: isolates ONLY the addition of
realistic battery economics (degradation cost, discharge
efficiency loss) applied to the EXACT SAME strategy as the
validated P5+FRI combined agent (c3_13) -- same discharge-only
trigger logic, same daily SoC reset, same dispatch behavior.
No charging logic, no continuous arbitrage introduced, to
correctly isolate "what does realism cost the existing,
validated strategy" from "what if the strategy itself changes."

Input:  data/processed/aemo_nem_with_actual_price.csv
        results/tables/c3_02_fri_agent_results.csv (fri_band)
        data/raw/aemo_nem/aemo_nem_p5min_actual_2021_2022_raw.csv
Output: results/tables/c3_16_realistic_costs_isolated_results.csv
"""
import sys
import pandas as pd
from config.settings import (
    PROCESSED_DIR, AEMO_RAW_DIR, TABLES_DIR, TRAIN_TEST_SPLIT,
    DISPATCH_THRESHOLD, BATTERY_CAPACITY_MWH, BATTERY_POWER_MW,
    BATTERY_SOC_MIN, BATTERY_SOC_MAX, BATTERY_SOC_INITIAL,
    BATTERY_MIN_DISPATCH_MW, BATTERY_SOC_RESET_DAILY, BATTERY_SOC_RESET_VALUE,
)
from config.logging_config import get_logger

logger = get_logger("c3_16_realistic_costs_isolated")

MAIN_FILE   = PROCESSED_DIR / "aemo_nem_with_actual_price.csv"
P5MIN_FILE  = AEMO_RAW_DIR / "aemo_nem_p5min_actual_2021_2022_raw.csv"
FRI_FILE    = TABLES_DIR / "c3_02_fri_agent_results.csv"
OUTPUT_FILE = TABLES_DIR / "c3_16_realistic_costs_isolated_results.csv"
INTERVAL_HOURS = 0.5

DISPATCH_FACTORS = {"HIGH": 1.00, "MEDIUM": 0.75, "LOW": 0.25}

ALPHA = 5.04e-4
BETA  = 2.03
R_REPLACEMENT = 42_000_000  # AUD, illustrative (Modo Energy Australian capex midpoint)
DISCHARGE_EFF = 0.90  # unchanged from all other agents today

def degradation_cost(depth_of_discharge_fraction):
    life_loss = ALPHA * (depth_of_discharge_fraction ** BETA)
    return R_REPLACEMENT * life_loss

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
    test = test.merge(fri[["DATETIME", "REGIONID", "fri_band"]],
                       on=["DATETIME", "REGIONID"], how="left")
    before = len(test)
    test = test.dropna(subset=["p5_decision_price", "p_actual", "fri_band"])
    logger.info(f"Rows before dropping unmatched: {before:,} -> after: {len(test):,}")
    return test.sort_values("DATETIME").reset_index(drop=True)

def simulate(df):
    logger.info("Simulating P5+FRI agent (c3_13 strategy, unchanged) "
                "with degradation cost added...")
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
        degradation = 0.0

        if should_dispatch and soc > BATTERY_SOC_MIN:
            max_dispatch = min(BATTERY_POWER_MW,
                                (soc - BATTERY_SOC_MIN) * BATTERY_CAPACITY_MWH / INTERVAL_HOURS)
            dispatch_mw = max(BATTERY_MIN_DISPATCH_MW, max_dispatch * dispatch_factor)
            energy_discharged = dispatch_mw * INTERVAL_HOURS
            depth = energy_discharged / BATTERY_CAPACITY_MWH
            soc -= depth
            degradation = degradation_cost(depth)
        else:
            dispatch_mw = 0.0

        soc = max(BATTERY_SOC_MIN, min(BATTERY_SOC_MAX, soc))
        revenue = dispatch_mw * DISCHARGE_EFF * revenue_price * INTERVAL_HOURS
        net_revenue = revenue - degradation

        genuine_error = abs(decision_price - revenue_price)
        is_silent_failure = should_dispatch and regime == "extreme" and genuine_error > 100

        results.append({
            "DATETIME": row["DATETIME"], "REGIONID": row["REGIONID"], "regime": regime,
            "should_dispatch": should_dispatch, "dispatch_mw": dispatch_mw,
            "revenue": round(revenue, 4), "degradation_cost": round(degradation, 4),
            "net_revenue": round(net_revenue, 4), "is_silent_failure": is_silent_failure,
        })

    results_df = pd.DataFrame(results)
    logger.info(f"Gross revenue:       AUD {results_df['revenue'].sum():,.2f}")
    logger.info(f"Degradation cost:    AUD {results_df['degradation_cost'].sum():,.2f}")
    logger.info(f"NET revenue:         AUD {results_df['net_revenue'].sum():,.2f}")
    logger.info(f"Discharge intervals: {results_df['should_dispatch'].sum():,}")
    logger.info(f"Silent failures:     {results_df['is_silent_failure'].sum():,}")
    return results_df

def main():
    logger.info("=" * 60)
    logger.info("c3_16_realistic_costs_isolated.py started")
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
