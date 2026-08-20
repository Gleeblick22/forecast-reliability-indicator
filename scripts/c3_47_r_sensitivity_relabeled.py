"""
c3_47_r_sensitivity_relabeled.py
===================================
Priority 6: R-sensitivity check for the relabeled classifier's
complete net revenue (discharge + charging), at R=21M/42M/84M,
completing the data needed for Figure 10's rebuild.
"""
import sys
import pandas as pd
from config.settings import TABLES_DIR
from config.logging_config import get_logger

logger = get_logger("c3_47_r_sensitivity_relabeled")

ALPHA = 5.04e-4
BETA = 2.03

def recompute_degradation(depth_series, R):
    return (R * ALPHA * (depth_series ** BETA)).sum()

def main():
    logger.info("=" * 60)
    # Discharge-side: reuse the confirmed relabeled agents' dispatch patterns
    base = pd.read_csv(TABLES_DIR / "c3_40_p5_baseline_relabeled_match_results.csv")
    fri = pd.read_csv(TABLES_DIR / "c3_39_p5_fri_relabeled_results.csv")

    base["depth"] = (base["dispatch_mw"] * 0.5) / 100.0
    fri["depth"] = (fri["dispatch_mw"] * 0.5) / 100.0

    charging = pd.read_csv(TABLES_DIR / "c3_41_charging_economics_relabeled_results.csv")
    base_charge_net = charging.iloc[0]["charging_cost"] * -1 - charging.iloc[0]["charging_degradation"]
    fri_charge_net = charging.iloc[1]["charging_cost"] * -1 - charging.iloc[1]["charging_degradation"]
    base_charge_net = -charging.iloc[0]["net_charging_economics"]
    fri_charge_net = -charging.iloc[1]["net_charging_economics"]

    for R in [21_000_000, 42_000_000, 84_000_000]:
        base_deg = recompute_degradation(base["depth"], R)
        fri_deg = recompute_degradation(fri["depth"], R)

        base_gross = base["revenue"].sum()
        fri_gross = fri["revenue"].sum()

        base_net_complete = base_gross - base_deg + base_charge_net
        fri_net_complete = fri_gross - fri_deg + fri_charge_net

        adv_pct = (fri_net_complete - base_net_complete) / base_net_complete * 100
        logger.info(f"R={R:,}: baseline_net={base_net_complete:,.2f}  fri_net={fri_net_complete:,.2f}  advantage={adv_pct:.1f}%")

    logger.info("=" * 60)
    sys.exit(0)

if __name__ == "__main__":
    main()
