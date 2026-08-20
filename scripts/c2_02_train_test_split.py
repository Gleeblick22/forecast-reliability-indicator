"""
c2_02_train_test_split.py
==========================
Splits feature matrix into train and test sets.
Uses chronological split at October 1 2022.
No random split — prevents look-ahead bias.

Input:  data/processed/features_all.csv
Output: data/processed/X_train.csv
        data/processed/X_test.csv
        data/processed/y_train.csv
        data/processed/y_test.csv

Project: forecast-reliability-indicator (FRI)
OSF:     10.17605/OSF.IO/Z89HD
"""

import sys
import pandas as pd
import numpy as np
from datetime import datetime
from pathlib import Path

from config.settings import (
    PROCESSED_DIR,
    TRAIN_TEST_SPLIT,
    NEM_REGIONS,
)
from config.logging_config import get_logger

logger = get_logger("c2_02_train_test_split")

FEATURES_FILE = PROCESSED_DIR / "features_all.csv"
X_TRAIN_FILE  = PROCESSED_DIR / "X_train.csv"
X_TEST_FILE   = PROCESSED_DIR / "X_test.csv"
Y_TRAIN_FILE  = PROCESSED_DIR / "y_train.csv"
Y_TEST_FILE   = PROCESSED_DIR / "y_test.csv"


def load_features() -> pd.DataFrame:
    """Load feature matrix."""
    if not FEATURES_FILE.exists():
        logger.error(f"Features file not found: {FEATURES_FILE}")
        logger.error("Run c2_01_feature_engineering.py first")
        sys.exit(1)

    df = pd.read_csv(FEATURES_FILE, parse_dates=["DATETIME"])
    logger.info(f"Loaded: {len(df):,} intervals")
    return df


def split_data(df: pd.DataFrame) -> tuple:
    """
    Split chronologically at TRAIN_TEST_SPLIT date.
    Training: before October 1 2022
    Test:     November 1 2022 onwards (October 2022 absent)
    """
    split_date = pd.Timestamp(TRAIN_TEST_SPLIT)

    train = df[df["DATETIME"] < split_date].copy()
    test  = df[df["DATETIME"] >= split_date].copy()

    logger.info(f"Split date: {split_date}")
    logger.info(f"Training:   {len(train):,} intervals")
    logger.info(f"Test:       {len(test):,} intervals")

    # Verify no overlap
    train_max = train["DATETIME"].max()
    test_min  = test["DATETIME"].min()
    logger.info(f"Training ends:  {train_max}")
    logger.info(f"Test starts:    {test_min}")

    if train_max >= test_min:
        logger.error("OVERLAP DETECTED between train and test")
        sys.exit(1)

    logger.info("No overlap confirmed")
    return train, test


def prepare_xy(
    train: pd.DataFrame,
    test: pd.DataFrame
) -> tuple:
    """Separate features and labels."""
    feature_cols = [c for c in train.columns if c.startswith("f_")]
    logger.info(f"Feature columns: {feature_cols}")

    X_train = train[feature_cols].reset_index(drop=True)
    y_train = train[["label"]].reset_index(drop=True)
    X_test  = test[feature_cols].reset_index(drop=True)
    y_test  = test[["label"]].reset_index(drop=True)

    # Log class distribution
    train_extreme = y_train["label"].sum()
    train_normal  = len(y_train) - train_extreme
    test_extreme  = y_test["label"].sum()
    test_normal   = len(y_test) - test_extreme

    logger.info(f"Train: extreme={train_extreme:,} normal={train_normal:,}")
    logger.info(f"Test:  extreme={test_extreme:,}  normal={test_normal:,}")

    scale_pos_weight = train_normal / train_extreme if train_extreme > 0 else 1
    logger.info(f"scale_pos_weight: {scale_pos_weight:.2f}")

    return X_train, X_test, y_train, y_test


def save_splits(
    X_train: pd.DataFrame,
    X_test: pd.DataFrame,
    y_train: pd.DataFrame,
    y_test: pd.DataFrame
) -> None:
    """Save all four split files."""
    X_train.to_csv(X_TRAIN_FILE, index=False)
    X_test.to_csv(X_TEST_FILE,   index=False)
    y_train.to_csv(Y_TRAIN_FILE, index=False)
    y_test.to_csv(Y_TEST_FILE,   index=False)

    logger.info(f"Saved: {X_TRAIN_FILE} ({len(X_train):,} rows)")
    logger.info(f"Saved: {X_TEST_FILE}  ({len(X_test):,} rows)")
    logger.info(f"Saved: {Y_TRAIN_FILE} ({len(y_train):,} rows)")
    logger.info(f"Saved: {Y_TEST_FILE}  ({len(y_test):,} rows)")


def main():
    logger.info("=" * 60)
    logger.info("c2_02_train_test_split.py started")
    logger.info(f"Timestamp: {datetime.now()}")
    logger.info(f"Split date: {TRAIN_TEST_SPLIT}")
    logger.info("=" * 60)

    df = load_features()

    logger.info("Splitting data...")
    train, test = split_data(df)

    logger.info("Preparing X y matrices...")
    X_train, X_test, y_train, y_test = prepare_xy(train, test)

    logger.info("Saving splits...")
    save_splits(X_train, X_test, y_train, y_test)

    logger.info("=" * 60)
    logger.info("c2_02 COMPLETE")
    logger.info(f"Training rows: {len(X_train):,}")
    logger.info(f"Test rows:     {len(X_test):,}")
    logger.info(f"Features:      {len(X_train.columns)}")
    logger.info("Next: ./run.sh scripts/c2_03_train_baseline_model.py")
    logger.info("=" * 60)
    sys.exit(0)


if __name__ == "__main__":
    main()
