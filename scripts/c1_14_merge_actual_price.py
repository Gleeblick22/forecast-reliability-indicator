"""
c1_04f_merge_actual_price.py
==============================
Merges P5MIN-derived actual price (p_actual) onto the
existing processed predispatch dataset, on (REGIONID, DATETIME).

Input:  data/processed/aemo_nem_all_2021_2022_processed.csv
        data/processed/p5min_actual_price_30min.csv
Output: data/processed/aemo_nem_with_actual_price.csv
"""
import sys
import pandas as pd
from config.settings import PROCESSED_DIR
from config.logging_config import get_logger

logger = get_logger("c1_04f_merge_actual_price")

MAIN_FILE    = PROCESSED_DIR / "aemo_nem_all_2021_2022_processed.csv"
ACTUAL_FILE  = PROCESSED_DIR / "p5min_actual_price_30min.csv"
OUTPUT_FILE  = PROCESSED_DIR / "aemo_nem_with_actual_price.csv"

def main():
    logger.info("=" * 60)
    logger.info("c1_04f_merge_actual_price.py started")
    logger.info("=" * 60)

    logger.info("Loading main processed dataset...")
    main_df = pd.read_csv(MAIN_FILE)
    main_df["DATETIME"] = pd.to_datetime(main_df["DATETIME"], dayfirst=True)
    logger.info(f"Main dataset rows: {len(main_df):,}")

    logger.info("Loading P5MIN actual-price data...")
    actual_df = pd.read_csv(ACTUAL_FILE, parse_dates=["DATETIME"])
    logger.info(f"Actual-price rows: {len(actual_df):,}")

    logger.info("Merging on (REGIONID, DATETIME)...")
    merged = main_df.merge(
        actual_df[["DATETIME", "REGIONID", "p_actual", "p_actual_run_datetime"]],
        on=["DATETIME", "REGIONID"],
        how="left",
    )

    logger.info(f"Merged rows: {len(merged):,}")
    missing = merged["p_actual"].isna().sum()
    logger.info(f"Rows with missing p_actual: {missing:,} ({100*missing/len(merged):.2f}%)")

    if missing > 0:
        logger.info("Sample of unmatched rows:")
        logger.info(merged[merged["p_actual"].isna()][["DATETIME", "REGIONID"]].head(10))

    logger.info(f"p_actual stats (matched rows only):\n{merged['p_actual'].describe()}")

    # Sanity check: compare p_actual vs existing last_forecast
    if "last_forecast" in merged.columns:
        diff = (merged["p_actual"] - merged["last_forecast"]).dropna()
        logger.info(f"p_actual vs last_forecast difference stats:\n{diff.describe()}")
        logger.info(f"Correlation (p_actual, last_forecast): {merged[['p_actual','last_forecast']].corr().iloc[0,1]:.4f}")

    merged.to_csv(OUTPUT_FILE, index=False)
    logger.info(f"Saved: {OUTPUT_FILE}")
    logger.info("=" * 60)
    sys.exit(0)

if __name__ == "__main__":
    main()
