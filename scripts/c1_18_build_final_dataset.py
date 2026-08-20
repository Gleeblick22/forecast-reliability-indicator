"""
c1_04j_build_final_dataset.py
================================
Assembles the final leakage-controlled training dataset:
  - New label (y_new, delta=300, from p_actual)
  - New revision feature (30-60 min lead, leakage-controlled)
  - Original 8 remaining features (already leakage-safe,
    anchored to earliest run: current price, rolling mean/max,
    price change 3h/6h, consecutive-high, hour, day-of-week,
    peak indicator) -- unchanged from original feature set

Input:  data/processed/aemo_nem_new_label.csv
        data/processed/revision_feature_leakage_controlled.csv
        data/processed/features_all.csv (for the other 8 features)
Output: data/processed/final_leakage_controlled_dataset.csv
"""
import sys
import pandas as pd
from config.settings import PROCESSED_DIR
from config.logging_config import get_logger

logger = get_logger("c1_04j_build_final_dataset")

LABEL_FILE    = PROCESSED_DIR / "aemo_nem_new_label.csv"
REVISION_FILE = PROCESSED_DIR / "revision_feature_leakage_controlled.csv"
FEATURES_FILE = PROCESSED_DIR / "features_all.csv"
OUTPUT_FILE   = PROCESSED_DIR / "final_leakage_controlled_dataset.csv"

def main():
    logger.info("=" * 60)
    logger.info("c1_04j_build_final_dataset.py started")
    logger.info("=" * 60)

    logger.info("Loading label data...")
    label_df = pd.read_csv(LABEL_FILE, parse_dates=["DATETIME"])
    logger.info(f"Label rows: {len(label_df):,}")

    logger.info("Loading leakage-controlled revision feature...")
    rev_df = pd.read_csv(REVISION_FILE, parse_dates=["DATETIME"])
    logger.info(f"Revision rows: {len(rev_df):,}")

    logger.info("Loading original features (for the other 8)...")
    feat_df = pd.read_csv(FEATURES_FILE, parse_dates=["DATETIME"])
    logger.info(f"Original features rows: {len(feat_df):,}")

    other_features = [
        "f_current_rrp", "f_rolling_mean_30min", "f_rolling_max_30min",
        "f_consecutive_high", "f_price_change_30min", "f_price_change_60min",
        "f_hour_of_day", "f_day_of_week", "f_is_peak_hour",
    ]
    missing_cols = [c for c in other_features if c not in feat_df.columns]
    if missing_cols:
        logger.warning(f"Missing expected columns in features_all.csv: {missing_cols}")
    keep_cols = ["DATETIME", "REGIONID"] + [c for c in other_features if c in feat_df.columns]
    feat_subset = feat_df[keep_cols]

    logger.info("Merging label + revision...")
    merged = label_df[["DATETIME", "REGIONID", "y_new"]].merge(
        rev_df[["DATETIME", "REGIONID", "new_revision"]],
        on=["DATETIME", "REGIONID"], how="inner"
    )
    logger.info(f"After label+revision merge: {len(merged):,}")

    logger.info("Merging with other 8 features...")
    final = merged.merge(feat_subset, on=["DATETIME", "REGIONID"], how="inner")
    logger.info(f"Final merged rows: {len(final):,}")

    na_counts = final.isna().sum()
    logger.info(f"NA counts per column:\n{na_counts[na_counts > 0]}")
    final = final.dropna()
    logger.info(f"Rows after dropping any remaining NAs: {len(final):,}")

    logger.info(f"Final label positive rate: {final['y_new'].mean()*100:.4f}%")

    final.to_csv(OUTPUT_FILE, index=False)
    logger.info(f"Saved: {OUTPUT_FILE}")
    logger.info("=" * 60)
    sys.exit(0)

if __name__ == "__main__":
    main()
