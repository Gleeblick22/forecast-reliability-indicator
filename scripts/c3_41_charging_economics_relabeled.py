"""
c3_41_charging_economics_relabeled.py
========================================
Phase 3: charging economics for the relabeled-classifier
agents (c3_39, c3_40), using the confirmed, corrected spread-
charging methodology (c3_38: charge triggered at <=AUD 20/MWh,
spread evenly across available low-price intervals per day).

Input:  results/tables/c3_39_p5_fri_relabeled_results.csv
        results/tables/c3_40_p5_baseline_relabeled_match_results.csv
        data/processed/aemo_nem_with_actual_price.csv
Output: results/tables/c3_41_charging_economics_relabeled_results.csv
"""
import sys
import pandas as pd
from config.settings import PROCESSED_DIR, TABLES_DIR
from config.logging_config import get_logger

logger = get_logger("c3_41_charging_economics_relabeled")

ALPHA = 5.04e-4
BETA  = 2.03
R_REPLACEMENT = 42_000_000
CHARGE_EFF = 0.90
BATTERY_CAPACITY_MWH = 100.0
BATTERY_POWER_MW = 50.0
CHARGE_THRESHOLD = 20.0
INTERVAL_HOURS = 0.5

def degradation_cost(depth):
    return R_REPLACEMENT * ALPHA * (depth ** BETA)

def compute_charging_economics(agent_file, agent_name, actual_df):
    df = pd.read_csv(agent_file, parse_dates=["DATETIME"])
    df = df.merge(actual_df[["DATETIME", "REGIONID", "p_actual"]],
                  on=["DATETIME", "REGIONID"], how="left")
    df = df.dropna(subset=["p_actual"]).sort_values("DATETIME").reset_index(drop=True)
    df["date"] = df["DATETIME"].dt.date
    df["energy_discharged_mwh"] = df["dispatch_mw"] * INTERVAL_HOURS

    total_charging_cost = 0.0
    total_charging_degradation = 0.0
    total_charge_intervals = 0

    for (region, date), day_df in df.groupby(["REGIONID", "date"]):
        energy_needed_mwh = day_df["energy_discharged_mwh"].sum() / CHARGE_EFF
        if energy_needed_mwh <= 0:
            continue

        low_price_intervals = day_df[day_df["p_actual"] <= CHARGE_THRESHOLD]
        n_intervals = len(low_price_intervals)
        if n_intervals == 0:
            continue

        max_energy_per_interval = BATTERY_POWER_MW * INTERVAL_HOURS
        energy_per_interval = min(max_energy_per_interval, energy_needed_mwh / n_intervals)

        for _, row in low_price_intervals.iterrows():
            depth = energy_per_interval / BATTERY_CAPACITY_MWH
            cost = energy_per_interval * row["p_actual"]
            degradation = degradation_cost(depth)
            total_charging_cost += cost
            total_charging_degradation += degradation
            total_charge_intervals += 1

    logger.info(f"\n=== {agent_name} ===")
    logger.info(f"Charge intervals used: {total_charge_intervals:,}")
    logger.info(f"Total charging cost (energy purchase): AUD {total_charging_cost:,.2f}")
    logger.info(f"Total charging degradation:            AUD {total_charging_degradation:,.2f}")
    logger.info(f"Net charging economics:                AUD {total_charging_cost + total_charging_degradation:,.2f}")

    return {"agent": agent_name, "charge_intervals": total_charge_intervals,
            "charging_cost": round(total_charging_cost, 2),
            "charging_degradation": round(total_charging_degradation, 2),
            "net_charging_economics": round(total_charging_cost + total_charging_degradation, 2)}

def main():
    logger.info("=" * 60)
    logger.info("c3_41_charging_economics_relabeled.py started")
    logger.info("=" * 60)

    actual_df = pd.read_csv(PROCESSED_DIR / "aemo_nem_with_actual_price.csv", parse_dates=["DATETIME"])

    results = []
    results.append(compute_charging_economics(
        TABLES_DIR / "c3_40_p5_baseline_relabeled_match_results.csv",
        "P5-baseline (relabeled match)", actual_df))
    results.append(compute_charging_economics(
        TABLES_DIR / "c3_39_p5_fri_relabeled_results.csv",
        "P5+FRI (relabeled)", actual_df))

    summary = pd.DataFrame(results)
    logger.info(f"\n{summary.to_string(index=False)}")
    summary.to_csv(TABLES_DIR / "c3_41_charging_economics_relabeled_results.csv", index=False)
    logger.info(f"\nSaved: {TABLES_DIR}/c3_41_charging_economics_relabeled_results.csv")
    logger.info("=" * 60)
    sys.exit(0)

if __name__ == "__main__":
    main()
