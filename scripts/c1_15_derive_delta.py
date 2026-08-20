"""
c1_04g_derive_delta.py
========================
Derives an empirically-justified delta for the new
reliability label, based on the distribution of
|first_forecast - p_actual|. Reports the delta value
that yields a comparable base rate to the original
label's 0.94% extreme rate (test partition), for fair
before/after comparison under leakage control.

Input:  data/processed/aemo_nem_with_actual_price.csv
Output: results/tables/delta_derivation_analysis.csv
"""
import sys
import pandas as pd
import numpy as np
from config.settings import PROCESSED_DIR, TABLES_DIR
from config.logging_config import get_logger

logger = get_logger("c1_04g_derive_delta")

INPUT_FILE  = PROCESSED_DIR / "aemo_nem_with_actual_price.csv"
OUTPUT_FILE = TABLES_DIR / "delta_derivation_analysis.csv"

def main():
    logger.info("=" * 60)
    logger.info("c1_04g_derive_delta.py started")
    logger.info("=" * 60)

    df = pd.read_csv(INPUT_FILE)
    df = df.dropna(subset=["p_actual", "first_forecast"]).copy()
    logger.info(f"Rows with valid p_actual: {len(df):,}")

    df["new_error"] = (df["first_forecast"] - df["p_actual"]).abs()

    logger.info("New error (|first_forecast - p_actual|) distribution:")
    logger.info(f"\n{df['new_error'].describe()}")

    # Candidate delta values to inspect
    candidates = [50, 100, 150, 200, 300, 500, 750, 1000, 1500, 2000]
    logger.info("\nCandidate delta -> resulting 'extreme' (unreliable) rate:")
    rows = []
    for d in candidates:
        rate = (df["new_error"] > d).mean() * 100
        count = (df["new_error"] > d).sum()
        logger.info(f"  delta={d:>5}: rate={rate:.4f}%  count={count:,}")
        rows.append({"delta": d, "rate_pct": rate, "count": count})

    # Find delta that most closely matches original 0.94% base rate
    target_rate = 0.94
    percentile_needed = 100 - target_rate
    delta_at_target = np.percentile(df["new_error"], percentile_needed)
    rate_at_that_delta = (df["new_error"] > delta_at_target).mean() * 100

    logger.info(f"\nOriginal label base rate (test partition): {target_rate}%")
    logger.info(f"Delta at {percentile_needed:.2f}th percentile "
                f"(matches ~{target_rate}% rate): AUD {delta_at_target:.2f}")
    logger.info(f"Actual rate at this delta: {rate_at_that_delta:.4f}%")

    pd.DataFrame(rows).to_csv(OUTPUT_FILE, index=False)
    logger.info(f"Saved: {OUTPUT_FILE}")
    logger.info("=" * 60)
    sys.exit(0)

if __name__ == "__main__":
    main()
