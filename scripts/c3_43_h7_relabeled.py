"""
c3_43_h7_relabeled.py
========================
Phase 3: recomputes H7 (revenue comparison against the original
~24h-lead baseline) using the relabeled classifier's scores to
drive the FRI-augmented agent's dispatch scaling, matching the
original H7 test's pre-registered comparison structure (both
agents on ~24h-lead decision timing, not the P5-timing variant).

Input:  data/processed/aemo_nem_with_actual_price.csv
        results/tables/c2_18_relabeled_full_scores.csv
Output: results/tables/c3_43_h7_relabeled_results.csv
"""
import sys
import pandas as pd
from config.settings import (
    PROCESSED_DIR, TABLES_DIR, TRAIN_TEST_SPLIT,
    DISPATCH_THRESHOLD, BATTERY_CAPACITY_MWH, BATTERY_POWER_MW,
    BATTERY_SOC_MIN, BATTERY_SOC_MAX, BATTERY_SOC_INITIAL,
    BATTERY_MIN_DISPATCH_MW, BATTERY_SOC_RESET_DAILY, BATTERY_SOC_RESET_VALUE,
)
from config.logging_config import get_logger

logger = get_logger("c3_43_h7_relabeled")

DISPATCH_FACTORS = {"HIGH": 1.00, "MEDIUM": 0.75, "LOW": 0.25}
DISCHARGE_EFF = 0.90
INTERVAL_HOURS = 0.5

def load_test_data():
    df = pd.read_csv(PROCESSED_DIR / "aemo_nem_with_actual_price.csv", parse_dates=["DATETIME"])
    split_date = pd.Timestamp(TRAIN_TEST_SPLIT)
    test = df[df["DATETIME"] >= split_date].copy()

    relabeled = pd.read_csv(TABLES_DIR / "c2_18_relabeled_full_scores.csv", parse_dates=["DATETIME"])
    test = test.merge(relabeled[["DATETIME", "REGIONID", "fri_band"]],
                       on=["DATETIME", "REGIONID"], how="inner")

    before = len(test)
    test = test.dropna(subset=["first_forecast", "p_actual", "fri_band"])
    logger.info(f"Rows before dropping unmatched: {before:,} -> after: {len(test):,}")
    return test.sort_values("DATETIME").reset_index(drop=True)

def simulate(df, use_fri):
    soc = BATTERY_SOC_INITIAL
    current_date = None
    total_revenue = 0.0
    extreme_revenue = 0.0
    normal_revenue = 0.0

    for _, row in df.iterrows():
        interval_date = pd.Timestamp(row["DATETIME"]).date()
        if BATTERY_SOC_RESET_DAILY and interval_date != current_date:
            soc = BATTERY_SOC_RESET_VALUE
            current_date = interval_date

        decision_price = row["first_forecast"]  # original ~24h-lead
        revenue_price  = row["p_actual"]
        regime         = row.get("regime", "normal")

        should_dispatch = decision_price >= DISPATCH_THRESHOLD
        dispatch_factor = DISPATCH_FACTORS.get(row["fri_band"], 0.75) if use_fri else 1.0

        if should_dispatch and soc > BATTERY_SOC_MIN:
            max_dispatch = min(BATTERY_POWER_MW,
                                (soc - BATTERY_SOC_MIN) * BATTERY_CAPACITY_MWH / INTERVAL_HOURS)
            dispatch_mw = max(BATTERY_MIN_DISPATCH_MW, max_dispatch * dispatch_factor)
            energy_discharged = dispatch_mw * INTERVAL_HOURS
            soc -= energy_discharged / BATTERY_CAPACITY_MWH
        else:
            dispatch_mw = 0.0

        soc = max(BATTERY_SOC_MIN, min(BATTERY_SOC_MAX, soc))
        revenue = dispatch_mw * DISCHARGE_EFF * revenue_price * INTERVAL_HOURS
        total_revenue += revenue
        if regime == "extreme":
            extreme_revenue += revenue
        else:
            normal_revenue += revenue

    return total_revenue, extreme_revenue, normal_revenue

def main():
    logger.info("=" * 60)
    logger.info("c3_43_h7_relabeled.py started")
    logger.info("=" * 60)

    test_data = load_test_data()

    base_total, base_extreme, base_normal = simulate(test_data, use_fri=False)
    fri_total, fri_extreme, fri_normal = simulate(test_data, use_fri=True)

    pct_change = (fri_total - base_total) / base_total * 100
    logger.info(f"Baseline total revenue: AUD {base_total:,.2f}")
    logger.info(f"FRI total revenue:      AUD {fri_total:,.2f}")
    logger.info(f"Revenue change:         {pct_change:+.2f}%")
    logger.info(f"Baseline extreme/normal: {base_extreme:,.2f} / {base_normal:,.2f}")
    logger.info(f"FRI extreme/normal:      {fri_extreme:,.2f} / {fri_normal:,.2f}")

    pd.DataFrame([{"baseline_total": base_total, "fri_total": fri_total,
                    "pct_change": pct_change, "baseline_extreme": base_extreme,
                    "baseline_normal": base_normal, "fri_extreme": fri_extreme,
                    "fri_normal": fri_normal}]).to_csv(
        TABLES_DIR / "c3_43_h7_relabeled_results.csv", index=False)
    logger.info(f"\nSaved: {TABLES_DIR}/c3_43_h7_relabeled_results.csv")
    logger.info("=" * 60)
    sys.exit(0)

if __name__ == "__main__":
    main()
