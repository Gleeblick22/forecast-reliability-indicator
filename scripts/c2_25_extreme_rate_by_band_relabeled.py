"""
c2_25_extreme_rate_by_band_relabeled.py
==========================================
Priority 6: computes extreme-event rate by FRI band for the
relabeled classifier (all test intervals, not just dispatched),
needed for Figure 11 Panel (a), replacing the original
classifier's band-discrimination data (c2_07_decision_rules.csv).

Input:  results/tables/c2_18_relabeled_full_scores.csv
Output: results/tables/c2_25_extreme_rate_by_band_relabeled.csv
"""
import sys
import pandas as pd
from config.settings import TABLES_DIR
from config.logging_config import get_logger

logger = get_logger("c2_25_extreme_rate_by_band_relabeled")

def main():
    logger.info("=" * 60)
    df = pd.read_csv(TABLES_DIR / "c2_18_relabeled_full_scores.csv")

    summary = df.groupby("fri_band").agg(
        count=("y_new", "count"),
        extreme_count=("y_new", "sum"),
    ).reset_index()
    summary["extreme_rate_pct"] = 100 * summary["extreme_count"] / summary["count"]
    summary["pct_of_total"] = 100 * summary["count"] / len(df)

    band_order = ["LOW", "MEDIUM", "HIGH"]
    summary["band"] = pd.Categorical(summary["fri_band"], categories=band_order, ordered=True)
    summary = summary.sort_values("band")

    logger.info(f"\n{summary.to_string(index=False)}")
    summary.to_csv(TABLES_DIR / "c2_25_extreme_rate_by_band_relabeled.csv", index=False)
    logger.info(f"Saved: {TABLES_DIR}/c2_25_extreme_rate_by_band_relabeled.csv")
    logger.info("=" * 60)
    sys.exit(0)

if __name__ == "__main__":
    main()
