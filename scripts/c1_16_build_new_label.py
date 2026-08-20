"""
c1_04h_build_new_label.py
============================
Constructs the new, leakage-controlled reliability label:
  y_new = 1 if |first_forecast - p_actual| > delta, else 0

delta = AUD 300, chosen as an economically meaningful,
previously-established reference point (matches the
original extreme-price threshold, the AEMO Administered
Price Cap), now applied to forecast-outcome divergence
rather than settled price level. See delta_derivation_analysis.csv
for the empirical distribution supporting this choice.

Input:  data/processed/aemo_nem_with_actual_price.csv
Output: data/processed/aemo_nem_new_label.csv
"""
import sys
import pandas as pd
from config.settings import PROCESSED_DIR
from config.logging_config import get_logger

logger = get_logger("c1_04h_build_new_label")

INPUT_FILE  = PROCESSED_DIR / "aemo_nem_with_actual_price.csv"
OUTPUT_FILE = PROCESSED_DIR / "aemo_nem_new_label.csv"

DELTA = 300.0

def main():
    logger.info("=" * 60)
    logger.info("c1_04h_build_new_label.py started")
    logger.info(f"delta = AUD {DELTA}")
    logger.info("=" * 60)

    df = pd.read_csv(INPUT_FILE)
    df["DATETIME"] = pd.to_datetime(df["DATETIME"])

    before = len(df)
    df = df.dropna(subset=["p_actual", "first_forecast"]).copy()
    logger.info(f"Rows before dropping unmatched: {before:,}")
    logger.info(f"Rows after dropping unmatched (p_actual/first_forecast NaN): {len(df):,}")

    df["new_error"] = (df["first_forecast"] - df["p_actual"]).abs()
    df["y_new"] = (df["new_error"] > DELTA).astype(int)

    overall_rate = df["y_new"].mean() * 100
    logger.info(f"Overall new-label positive rate: {overall_rate:.4f}%")
    logger.info(f"Positive count: {df['y_new'].sum():,} of {len(df):,}")

    logger.info("\nBy region:")
    logger.info(df.groupby("REGIONID")["y_new"].agg(["mean", "sum", "count"]))

    logger.info("\nComparison with original label ('regime' column, if present):")
    if "regime" in df.columns:
        df["y_old"] = (df["regime"] == "extreme").astype(int)
        agreement = (df["y_new"] == df["y_old"]).mean() * 100
        logger.info(f"Agreement between old and new label: {agreement:.2f}%")
        cross = pd.crosstab(df["y_old"], df["y_new"], margins=True)
        logger.info(f"\nCross-tabulation (rows=old, cols=new):\n{cross}")

    # Chronological split, matching original methodology
    split_date = pd.Timestamp("2022-10-01")
    train = df[df["DATETIME"] < split_date]
    test  = df[df["DATETIME"] >= split_date]
    logger.info(f"\nTrain rows: {len(train):,}  (positive rate: {train['y_new'].mean()*100:.4f}%)")
    logger.info(f"Test rows:  {len(test):,}  (positive rate: {test['y_new'].mean()*100:.4f}%)")

    df.to_csv(OUTPUT_FILE, index=False)
    logger.info(f"Saved: {OUTPUT_FILE}")
    logger.info("=" * 60)
    sys.exit(0)

if __name__ == "__main__":
    main()
