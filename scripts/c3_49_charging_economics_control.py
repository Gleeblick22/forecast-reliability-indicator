"""
c3_49_charging_economics_control.py
======================================
M2: charging economics for the depth-matched control agent,
using the confirmed spread-charging methodology (c3_38/c3_41),
completing the control's full, complete-economics net revenue
for consistency with the 59.7% headline's basis.

Input:  results/tables/c3_48_depth_matched_control_results.csv
        data/processed/aemo_nem_with_actual_price.csv
Output: results/tables/c3_49_charging_economics_control_results.csv
"""
import sys
import pandas as pd
from config.settings import PROCESSED_DIR, TABLES_DIR
from config.logging_config import get_logger

logger = get_logger("c3_49_charging_economics_control")

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

def main():
    logger.info("=" * 60)
    df = pd.read_csv(TABLES_DIR / "c3_48_depth_matched_control_results.csv", parse_dates=["DATETIME"])
    actual_df = pd.read_csv(PROCESSED_DIR / "aemo_nem_with_actual_price.csv", parse_dates=["DATETIME"])
    df = df.merge(actual_df[["DATETIME", "REGIONID", "p_actual"]], on=["DATETIME", "REGIONID"], how="left")
    df = df.dropna(subset=["p_actual"]).sort_values("DATETIME").reset_index(drop=True)
    df["date"] = df["DATETIME"].dt.date
    df["energy_discharged_mwh"] = df["dispatch_mw"] * INTERVAL_HOURS

    total_cost = 0.0
    total_deg = 0.0
    for (region, date), day_df in df.groupby(["REGIONID", "date"]):
        energy_needed = day_df["energy_discharged_mwh"].sum() / CHARGE_EFF
        if energy_needed <= 0:
            continue
        low_price = day_df[day_df["p_actual"] <= CHARGE_THRESHOLD]
        n = len(low_price)
        if n == 0:
            continue
        max_e = BATTERY_POWER_MW * INTERVAL_HOURS
        e_per = min(max_e, energy_needed / n)
        for _, row in low_price.iterrows():
            depth = e_per / BATTERY_CAPACITY_MWH
            total_cost += e_per * row["p_actual"]
            total_deg += degradation_cost(depth)

    logger.info(f"Charging cost: AUD {total_cost:,.2f}")
    logger.info(f"Charging degradation: AUD {total_deg:,.2f}")
    logger.info(f"Net charging economics: AUD {-(total_cost + total_deg):,.2f}")

    discharge_net = 202957.44
    complete_net = discharge_net - total_cost - total_deg
    logger.info(f"Control complete net revenue (discharge+charging): AUD {complete_net:,.2f}")

    pd.DataFrame([{"charging_cost": total_cost, "charging_degradation": total_deg,
                    "discharge_net": discharge_net, "complete_net": complete_net}]).to_csv(
        TABLES_DIR / "c3_49_charging_economics_control_results.csv", index=False)
    logger.info("=" * 60)
    sys.exit(0)

if __name__ == "__main__":
    main()
