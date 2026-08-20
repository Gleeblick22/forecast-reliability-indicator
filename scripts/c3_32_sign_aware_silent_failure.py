"""
c3_19_sign_aware_silent_failure.py
=====================================
Recomputes silent-failure counts for the P5-baseline and
P5+FRI combined agents using a SIGN-AWARE definition,
addressing Major review item #9 (Reviewer 3): the original
definition used |error| > threshold, which counts profitable
under-forecasts as failures alongside genuine over-forecasts.
For a discharging battery, only over-forecasts (actual price
lower than expected) are true silent failures.

Re-merges agent output with the source dataset to recover
p_actual and p5_decision_price (not saved in the agent output
files), then reclassifies is_silent_failure with sign awareness.

Input:  results/tables/c3_16_realistic_costs_isolated_results.csv
        results/tables/c3_17_realistic_costs_p5_baseline_results.csv
        data/processed/aemo_nem_with_actual_price.csv
        data/raw/aemo_nem/aemo_nem_p5min_actual_2021_2022_raw.csv
Output: results/tables/c3_19_sign_aware_comparison.csv
"""
import sys
import pandas as pd
from config.settings import PROCESSED_DIR, AEMO_RAW_DIR, TABLES_DIR, DISPATCH_THRESHOLD
from config.logging_config import get_logger

logger = get_logger("c3_19_sign_aware_silent_failure")

def load_p5_decision_price():
    p5 = pd.read_csv(AEMO_RAW_DIR / "aemo_nem_p5min_actual_2021_2022_raw.csv",
                      parse_dates=["RUN_DATETIME", "INTERVAL_DATETIME"])
    p5["lead_minutes"] = (p5["INTERVAL_DATETIME"] - p5["RUN_DATETIME"]).dt.total_seconds() / 60
    p5 = p5[(p5["lead_minutes"] >= 0) & (p5["lead_minutes"] <= 10)]
    p5["dist_from_5"] = (p5["lead_minutes"] - 5).abs()
    p5 = p5.sort_values("dist_from_5").groupby(
        ["REGIONID", "INTERVAL_DATETIME"], as_index=False).first()
    p5 = p5.rename(columns={"INTERVAL_DATETIME": "DATETIME", "RRP": "p5_decision_price"})
    return p5[["DATETIME", "REGIONID", "p5_decision_price"]]

def recompute(agent_file, agent_name, p5_df, actual_df):
    df = pd.read_csv(agent_file, parse_dates=["DATETIME"])
    df = df.merge(p5_df, on=["DATETIME", "REGIONID"], how="left")
    df = df.merge(actual_df[["DATETIME", "REGIONID", "p_actual"]],
                  on=["DATETIME", "REGIONID"], how="left")
    before = len(df)
    df = df.dropna(subset=["p5_decision_price", "p_actual"])
    logger.info(f"{agent_name}: {before:,} -> {len(df):,} rows after merge")

    # signed_error = decision - actual (positive = over-forecast, real loss)
    df["signed_error"] = df["p5_decision_price"] - df["p_actual"]

    old_silent = (df["should_dispatch"] & (df["regime"] == "extreme") &
                  (df["signed_error"].abs() > DISPATCH_THRESHOLD)).sum()
    new_silent_overforecast = (df["should_dispatch"] & (df["regime"] == "extreme") &
                                (df["signed_error"] > DISPATCH_THRESHOLD)).sum()
    windfall_underforecast = (df["should_dispatch"] & (df["regime"] == "extreme") &
                               (df["signed_error"] < -DISPATCH_THRESHOLD)).sum()

    logger.info(f"\n=== {agent_name} ===")
    logger.info(f"OLD definition (|error| > threshold): {old_silent} silent failures")
    logger.info(f"NEW definition (over-forecast only):  {new_silent_overforecast} silent failures")
    logger.info(f"Previously miscounted as failures, actually windfalls: {windfall_underforecast}")

    return {"agent": agent_name, "old_silent_failures": int(old_silent),
            "new_silent_failures_sign_aware": int(new_silent_overforecast),
            "reclassified_as_windfall": int(windfall_underforecast)}

def main():
    logger.info("=" * 60)
    logger.info("c3_19_sign_aware_silent_failure.py started")
    logger.info("=" * 60)

    p5_df = load_p5_decision_price()
    actual_df = pd.read_csv(PROCESSED_DIR / "aemo_nem_with_actual_price.csv", parse_dates=["DATETIME"])

    results = []
    results.append(recompute(TABLES_DIR / "c3_16_realistic_costs_isolated_results.csv",
                              "P5+FRI combined", p5_df, actual_df))
    results.append(recompute(TABLES_DIR / "c3_17_realistic_costs_p5_baseline_results.csv",
                              "P5-baseline", p5_df, actual_df))

    pd.DataFrame(results).to_csv(TABLES_DIR / "c3_19_sign_aware_comparison.csv", index=False)
    logger.info(f"\nSaved: {TABLES_DIR / 'c3_19_sign_aware_comparison.csv'}")
    logger.info("=" * 60)
    sys.exit(0)

if __name__ == "__main__":
    main()
