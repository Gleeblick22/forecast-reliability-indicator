"""
c1_20_recompute_h1_h2_genuine_error.py
==========================================
Recomputes H1 (amplification) and H2 (masking) using
genuine forecast error (|first_forecast - p_actual|)
instead of revision (|last_forecast - first_forecast|),
directly addressing Critical review items #1 and #2.

Regime label also rebuilt from p_actual (>= $300) rather
than last_forecast, consistent with the new label logic
(c1_16_build_new_label.py).

Input:  data/processed/aemo_nem_with_actual_price.csv
Output: results/tables/h1_h2_genuine_error_results.csv
"""
import sys
import pandas as pd
from scipy import stats
from config.settings import PROCESSED_DIR, TABLES_DIR
from config.logging_config import get_logger

logger = get_logger("c1_20_recompute_h1_h2")

INPUT_FILE  = PROCESSED_DIR / "aemo_nem_with_actual_price.csv"
OUTPUT_FILE = TABLES_DIR / "h1_h2_genuine_error_results.csv"

def main():
    logger.info("=" * 60)
    logger.info("c1_20_recompute_h1_h2_genuine_error.py started")
    logger.info("=" * 60)

    df = pd.read_csv(INPUT_FILE)
    df = df.dropna(subset=["p_actual", "first_forecast"]).copy()
    logger.info(f"Valid rows: {len(df):,}")

    df["genuine_error"] = (df["first_forecast"] - df["p_actual"]).abs()
    df["regime_new"] = df["p_actual"].apply(lambda x: "extreme" if x >= 300 else "normal")

    logger.info("\n=== H1: Amplification (genuine error) ===")
    results = []
    for region in sorted(df["REGIONID"].unique()):
        sub = df[df["REGIONID"] == region]
        extreme = sub[sub["regime_new"] == "extreme"]["genuine_error"]
        normal  = sub[sub["regime_new"] == "normal"]["genuine_error"]
        if len(extreme) > 1 and len(normal) > 1:
            ratio = extreme.mean() / normal.mean()
            t_stat, p_val = stats.ttest_ind(extreme, normal, equal_var=False)
            logger.info(f"  {region}: ratio={ratio:.2f}x  "
                        f"extreme_n={len(extreme)}  normal_n={len(normal)}  p={p_val:.4g}")
            results.append({"region": region, "ratio": ratio, "p_value": p_val,
                             "extreme_n": len(extreme), "normal_n": len(normal)})

    logger.info("\n=== H2: Masking (genuine error) ===")
    extreme_all  = df[df["regime_new"] == "extreme"]["genuine_error"]
    all_intervals = df["genuine_error"]
    mae_extreme = extreme_all.mean()
    mae_aggregate = all_intervals.mean()
    masking = 1 - (mae_aggregate / mae_extreme)
    logger.info(f"  MAE extreme: {mae_extreme:.2f}")
    logger.info(f"  MAE aggregate: {mae_aggregate:.2f}")
    logger.info(f"  Masking rate: {masking*100:.2f}%")

    pd.DataFrame(results).to_csv(OUTPUT_FILE, index=False)
    logger.info(f"Saved: {OUTPUT_FILE}")
    logger.info("=" * 60)
    sys.exit(0)

if __name__ == "__main__":
    main()
