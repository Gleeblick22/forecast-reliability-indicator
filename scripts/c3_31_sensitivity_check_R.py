"""
c3_18_sensitivity_check_R.py
===============================
Sensitivity check: re-runs the realistic-cost comparison
(c3_16 vs c3_17 logic) at half and double the baseline R
(AUD 42 million), to confirm the qualitative finding --
FRI's degradation-cost advantage over the P5-baseline --
is robust to the specific capex assumption, not an artifact
of the chosen value.

Reuses the exact same discharge patterns already computed
and saved by c3_16 and c3_17 (dispatch decisions don't change
with R; only the dollar cost of degradation scales linearly
with R). Recomputes net revenue at each R value directly from
the saved depth-of-discharge-implied degradation, without
re-simulating.

Input:  results/tables/c3_16_realistic_costs_isolated_results.csv
        results/tables/c3_17_realistic_costs_p5_baseline_results.csv
Output: results/tables/c3_18_R_sensitivity_results.csv
"""
import sys
import pandas as pd
from config.settings import TABLES_DIR
from config.logging_config import get_logger

logger = get_logger("c3_18_sensitivity_check_R")

FRI_FILE      = TABLES_DIR / "c3_16_realistic_costs_isolated_results.csv"
BASELINE_FILE = TABLES_DIR / "c3_17_realistic_costs_p5_baseline_results.csv"
OUTPUT_FILE   = TABLES_DIR / "c3_18_R_sensitivity_results.csv"

R_BASELINE = 42_000_000
R_VALUES = {"half (AUD 21M)": 0.5, "baseline (AUD 42M)": 1.0, "double (AUD 84M)": 2.0}

def main():
    logger.info("=" * 60)
    logger.info("c3_18_sensitivity_check_R.py started")
    logger.info("=" * 60)

    fri_df = pd.read_csv(FRI_FILE)
    base_df = pd.read_csv(BASELINE_FILE)

    # degradation_cost scales linearly with R, so we can rescale directly
    fri_gross = fri_df["revenue"].sum()
    fri_degradation_at_baseline_R = fri_df["degradation_cost"].sum()

    base_gross = base_df["revenue"].sum()
    base_degradation_at_baseline_R = base_df["degradation_cost"].sum()

    results = []
    for label, multiplier in R_VALUES.items():
        fri_deg = fri_degradation_at_baseline_R * multiplier
        base_deg = base_degradation_at_baseline_R * multiplier
        fri_net = fri_gross - fri_deg
        base_net = base_gross - base_deg
        advantage_pct = (fri_net - base_net) / base_net * 100

        logger.info(f"\n=== R = {label} ===")
        logger.info(f"  P5-baseline:  gross=${base_gross:,.2f}  degradation=${base_deg:,.2f}  net=${base_net:,.2f}")
        logger.info(f"  P5+FRI:       gross=${fri_gross:,.2f}  degradation=${fri_deg:,.2f}  net=${fri_net:,.2f}")
        logger.info(f"  FRI advantage: ${fri_net - base_net:,.2f} ({advantage_pct:.1f}%)")

        results.append({
            "R_scenario": label, "R_value": R_BASELINE * multiplier,
            "p5_baseline_net": round(base_net, 2), "p5_fri_net": round(fri_net, 2),
            "fri_advantage_aud": round(fri_net - base_net, 2),
            "fri_advantage_pct": round(advantage_pct, 1),
        })

    results_df = pd.DataFrame(results)
    results_df.to_csv(OUTPUT_FILE, index=False)
    logger.info(f"\nSaved: {OUTPUT_FILE}")
    logger.info("=" * 60)
    sys.exit(0)

if __name__ == "__main__":
    main()
