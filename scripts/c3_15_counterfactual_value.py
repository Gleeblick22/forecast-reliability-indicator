"""
c3_15_counterfactual_value.py
==============================
Counterfactual value-of-information analysis.

Calculates the economic value of FRI by
quantifying revenue losses avoided through
silent failure reduction.

For each silent failure avoided by FRI:
  Baseline dispatched on bad forecast signal
  and earned low/negative revenue
  FRI avoided this dispatch -- saved capital

Total FRI value = sum of counterfactual savings
from 34 avoided silent failures.

This is a value-of-information framing:
  FRI provides information that prevents
  costly dispatch decisions
  Economic value exists independently of
  aggregate revenue comparison

Input:  results/tables/c3_01_baseline_agent_results.csv
        results/tables/c3_02_fri_agent_results.csv
Output: results/tables/counterfactual_value.csv
Project: forecast-reliability-indicator (FRI)
OSF:     10.17605/OSF.IO/Z89HD
"""
import sys
import warnings
import numpy as np
import pandas as pd
from datetime import datetime
from config.settings import TABLES_DIR
from config.logging_config import get_logger

warnings.filterwarnings("ignore")
logger = get_logger("c3_15_counterfactual_value")


def main():
    logger.info("=" * 60)
    logger.info("c3_15_counterfactual_value.py started")
    logger.info(f"Timestamp: {datetime.now()}")
    logger.info("=" * 60)

    baseline = pd.read_csv(
        TABLES_DIR / "c3_01_baseline_agent_results.csv",
        parse_dates=["DATETIME"])
    fri = pd.read_csv(
        TABLES_DIR / "c3_02_fri_agent_results.csv",
        parse_dates=["DATETIME"])

    # merge on DATETIME and REGIONID
    merged = baseline[["DATETIME","REGIONID","revenue",
                        "is_silent_failure","dispatch_mw",
                        "last_forecast"]].merge(
        fri[["DATETIME","REGIONID","revenue",
             "is_silent_failure","fri_band","fri_score"]],
        on=["DATETIME","REGIONID"],
        suffixes=("_base","_fri"))

    logger.info(f"Total intervals:        {len(merged):,}")
    logger.info(f"Baseline silent failures: "
                f"{merged['is_silent_failure_base'].sum():,}")
    logger.info(f"FRI silent failures:     "
                f"{merged['is_silent_failure_fri'].sum():,}")

    # intervals where baseline failed but FRI avoided
    avoided = merged[
        (merged["is_silent_failure_base"] == True) &
        (merged["is_silent_failure_fri"] == False)].copy()

    logger.info(f"Silent failures avoided: {len(avoided):,}")

    # counterfactual value = revenue baseline earned
    # during its silent failures (bad dispatches)
    # This is the cost FRI would have saved
    avoided["counterfactual_value"] = avoided["revenue_base"]

    results = []
    for _, row in avoided.iterrows():
        results.append({
            "DATETIME":            row["DATETIME"],
            "REGIONID":            row["REGIONID"],
            "last_forecast":       row["last_forecast"],
            "baseline_revenue":    round(row["revenue_base"], 2),
            "fri_revenue":         round(row["revenue_fri"], 2),
            "counterfactual_value":round(row["revenue_base"], 2),
            "fri_band":            row["fri_band"],
            "fri_score":           round(row["fri_score"], 4),
        })

    df = pd.DataFrame(results)
    output = TABLES_DIR / "counterfactual_value.csv"
    df.to_csv(output, index=False)

    # summary
    total_cf_value  = df["counterfactual_value"].sum()
    mean_cf_value   = df["counterfactual_value"].mean()
    n_avoided       = len(df)
    b_total_rev     = baseline["revenue"].sum()
    cf_pct_of_total = total_cf_value / b_total_rev * 100

    # annualise (test period = 3 months)
    annual_value    = total_cf_value * 4

    logger.info("=" * 60)
    logger.info("COUNTERFACTUAL VALUE ANALYSIS COMPLETE")
    logger.info(f"Silent failures avoided:     {n_avoided:,}")
    logger.info(f"Total counterfactual value:  ${total_cf_value:,.2f}")
    logger.info(f"Mean value per avoided SF:   ${mean_cf_value:,.2f}")
    logger.info(f"As % of baseline revenue:    {cf_pct_of_total:.2f}%")
    logger.info(f"Annualised value (x4):       ${annual_value:,.2f}")
    logger.info(f"Saved: {output}")
    logger.info("Next: ./run.sh scripts/c3_16_rolling_retraining.py")
    logger.info("=" * 60)
    sys.exit(0)


if __name__ == "__main__":
    main()
