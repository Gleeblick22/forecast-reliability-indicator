"""
c3_12_reconcile_revenue_basis.py
===================================
Recomputes revenue for the original baseline and FRI agents
using p_actual (genuine P5MIN-derived outcome) instead of
last_forecast, for a fully like-for-like comparison against
the P5-baseline agent (c3_11), which already uses p_actual.

Dispatch decisions (should_dispatch, dispatch_mw) are NOT
changed -- only the revenue calculation is recomputed against
the more defensible outcome measure.

Input:  results/tables/c3_01_baseline_agent_results.csv
        results/tables/c3_02_fri_agent_results.csv
        data/processed/aemo_nem_with_actual_price.csv
Output: results/tables/c3_12_revenue_reconciled_comparison.csv
"""
import sys
import pandas as pd
from config.settings import PROCESSED_DIR, TABLES_DIR
from config.logging_config import get_logger

logger = get_logger("c3_12_reconcile_revenue_basis")

BASELINE_FILE = TABLES_DIR / "c3_01_baseline_agent_results.csv"
FRI_FILE      = TABLES_DIR / "c3_02_fri_agent_results.csv"
ACTUAL_FILE   = PROCESSED_DIR / "aemo_nem_with_actual_price.csv"
P5_BASELINE_FILE = TABLES_DIR / "c3_11_p5_baseline_agent_results.csv"
OUTPUT_FILE   = TABLES_DIR / "c3_12_revenue_reconciled_comparison.csv"

INTERVAL_HOURS = 0.5
DISCHARGE_EFF  = 0.90  # matching BATTERY_DISCHARGE_EFF

def recompute_revenue(agent_file, agent_name, actual_df):
    df = pd.read_csv(agent_file, parse_dates=["DATETIME"])
    df = df.merge(actual_df[["DATETIME", "REGIONID", "p_actual"]],
                  on=["DATETIME", "REGIONID"], how="left")
    before = len(df)
    df = df.dropna(subset=["p_actual"])
    logger.info(f"{agent_name}: {before:,} rows -> {len(df):,} after p_actual match")

    df["revenue_reconciled"] = df["dispatch_mw"] * DISCHARGE_EFF * df["p_actual"] * INTERVAL_HOURS

    # Recompute silent failure using genuine error against p_actual
    decision_col = "first_forecast" if "first_forecast" in df.columns else "p5_decision_price"
    df["genuine_error"] = (df[decision_col] - df["p_actual"]).abs()
    df["silent_failure_reconciled"] = (
        df["should_dispatch"] & (df["regime"] == "extreme") & (df["genuine_error"] > 100)
    )

    total_revenue = df["revenue_reconciled"].sum()
    silent_failures = df["silent_failure_reconciled"].sum()
    logger.info(f"{agent_name} RECONCILED -- Revenue: ${total_revenue:,.2f}  "
                f"Silent failures: {silent_failures:,}")
    return {"agent": agent_name, "revenue_reconciled": total_revenue,
            "silent_failures_reconciled": silent_failures, "n_rows": len(df)}

def main():
    logger.info("=" * 60)
    logger.info("c3_12_reconcile_revenue_basis.py started")
    logger.info("=" * 60)

    actual_df = pd.read_csv(ACTUAL_FILE, parse_dates=["DATETIME"])

    results = []
    results.append(recompute_revenue(BASELINE_FILE, "original_baseline", actual_df))
    results.append(recompute_revenue(FRI_FILE, "fri_agent", actual_df))

    # P5-baseline already uses p_actual; just read its existing totals for comparison
    p5_df = pd.read_csv(P5_BASELINE_FILE)
    results.append({
        "agent": "p5_baseline",
        "revenue_reconciled": p5_df["revenue"].sum(),
        "silent_failures_reconciled": p5_df["is_silent_failure"].sum(),
        "n_rows": len(p5_df),
    })

    summary = pd.DataFrame(results)
    logger.info("\n=== FULLY RECONCILED COMPARISON (all on p_actual) ===")
    logger.info(f"\n{summary.to_string(index=False)}")

    summary.to_csv(OUTPUT_FILE, index=False)
    logger.info(f"Saved: {OUTPUT_FILE}")
    logger.info("=" * 60)
    sys.exit(0)

if __name__ == "__main__":
    main()
