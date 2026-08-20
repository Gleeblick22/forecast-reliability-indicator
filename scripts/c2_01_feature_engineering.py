"""
c2_01_feature_engineering.py
=============================
Engineers features for FRI XGBoost model.

Uses ONLY features from trigger_weights.csv
per Decision 3. No new features allowed.

Input:  data/processed/aemo_nem_all_2021_2022_processed.csv
        results/tables/trigger_weights.csv
        data/raw/aemo_nem/aemo_nem_all_2021_2022_raw.csv
Output: data/processed/features_all.csv

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
    TABLES_DIR,
    AEMO_RAW_DIR,
    NEM_REGIONS,
    TRAIN_TEST_SPLIT,
    FEATURE_LOCK_RULE,
)
from config.logging_config import get_logger

logger = get_logger("c2_01_feature_engineering")

PROCESSED_FILE = PROCESSED_DIR / "aemo_nem_all_2021_2022_processed.csv"
SAMPLE_FILE    = PROCESSED_DIR / "aemo_nem_sample_processed.csv"
RAW_FILE       = AEMO_RAW_DIR  / "aemo_nem_all_2021_2022_raw.csv"
SAMPLE_RAW     = AEMO_RAW_DIR  / "aemo_nem_sample_raw.csv"
TRIGGER_FILE   = TABLES_DIR    / "trigger_weights.csv"
OUTPUT_FILE    = PROCESSED_DIR / "features_all.csv"


def load_inputs() -> tuple:
    """Load processed data raw data and trigger weights."""
    if PROCESSED_FILE.exists():
        proc_path = PROCESSED_FILE
        raw_path  = RAW_FILE
        is_sample = False
        logger.info("Loading full dataset")
    else:
        proc_path = SAMPLE_FILE
        raw_path  = SAMPLE_RAW
        is_sample = True
        logger.warning("Full dataset not found — using sample")

    processed = pd.read_csv(proc_path, parse_dates=["DATETIME"])
    logger.info(f"Processed: {len(processed):,} intervals")

    raw = pd.read_csv(
        raw_path,
        parse_dates=["DATETIME", "PREDISPATCH_RUN_DATETIME"],
        usecols=["DATETIME", "REGIONID", "RRP",
                 "PREDISPATCH_RUN_DATETIME"]
    )
    logger.info(f"Raw: {len(raw):,} rows")

    weights = pd.read_csv(TRIGGER_FILE)
    locked  = weights["feature"].unique().tolist()
    logger.info(f"Locked features from trigger_weights.csv: {locked}")
    logger.info(f"Feature lock rule: {FEATURE_LOCK_RULE}")

    return processed, raw, locked, is_sample


def engineer_features(
    processed: pd.DataFrame,
    raw: pd.DataFrame,
    locked_features: list
) -> pd.DataFrame:
    """
    Engineer all features per interval per region.
    Only features in locked_features used per Decision 3.
    All features observable in real time — no future data.
    """
    logger.info("Engineering features...")

    # Use EARLIEST forecast run per interval
    # This prevents circular logic where f_current_rrp
    # encodes the same information as the label (Decision 1)
    # Label = last_forecast >= $300
    # f_current_rrp = earliest_forecast RRP
    # So model predicts: does early signal predict final failure?
    latest_runs = (
        raw.sort_values("PREDISPATCH_RUN_DATETIME")
        .groupby(["DATETIME", "REGIONID"])
        .first()
        .reset_index()
    )[["DATETIME", "REGIONID", "RRP"]]
    latest_runs = latest_runs.rename(columns={"RRP": "latest_rrp"})

    df = processed.merge(latest_runs, on=["DATETIME", "REGIONID"], how="left")
    df = df.sort_values(["REGIONID", "DATETIME"]).reset_index(drop=True)

    all_regions = []

    for region in NEM_REGIONS:
        r = df[df["REGIONID"] == region].copy().reset_index(drop=True)
        if len(r) == 0:
            continue

        # f_current_rrp = EARLIEST forecast RRP (not latest)
        # Avoids circular logic with label definition
        r["f_current_rrp"]        = r["latest_rrp"].fillna(0)
        r["f_rolling_mean_30min"] = r["latest_rrp"].rolling(6, min_periods=1).mean()
        r["f_rolling_max_30min"]  = r["latest_rrp"].rolling(6, min_periods=1).max()
        r["f_price_change_30min"] = (r["latest_rrp"] - r["latest_rrp"].shift(6)).fillna(0)
        r["f_price_change_60min"] = (r["latest_rrp"] - r["latest_rrp"].shift(12)).fillna(0)
        r["f_forecast_revision"]  = r["forecast_error"].fillna(0)
        r["f_hour_of_day"]        = pd.to_datetime(r["DATETIME"]).dt.hour
        r["f_is_peak_hour"]       = r["f_hour_of_day"].between(16, 20).astype(int)
        r["f_day_of_week"]        = pd.to_datetime(r["DATETIME"]).dt.dayofweek

        above_100 = (r["latest_rrp"] >= 100).astype(int)
        r["f_consecutive_high"] = (
            above_100.groupby(
                (above_100 != above_100.shift()).cumsum()
            ).cumcount() + 1
        ) * above_100

        r["label"] = (r["regime"] == "extreme").astype(int)

        feature_cols = [f for f in locked_features if f in r.columns]
        keep_cols    = ["DATETIME", "REGIONID", "label", "regime"] + feature_cols
        all_regions.append(r[keep_cols])

    result = pd.concat(all_regions, ignore_index=True)
    logger.info(f"Features engineered: {len(result):,} intervals")

    extreme = result["label"].sum()
    normal  = len(result) - extreme
    ratio   = normal / extreme if extreme > 0 else 0
    logger.info(f"Class distribution: extreme={extreme:,} normal={normal:,}")
    logger.info(f"scale_pos_weight for XGBoost: {ratio:.2f}")

    return result


def validate_features(df: pd.DataFrame, locked_features: list) -> bool:
    """Validate feature matrix before saving."""
    feature_cols = [c for c in df.columns if c.startswith("f_")]

    missing = [f for f in locked_features if f not in df.columns]
    if missing:
        logger.error(f"Missing locked features: {missing}")
        return False

    null_counts = df[feature_cols].isnull().sum()
    if null_counts.any():
        logger.error(f"Null values found: {null_counts[null_counts > 0].to_dict()}")
        return False

    if set(df["label"].unique()) - {0, 1}:
        logger.error("Label is not binary")
        return False

    if set(df["REGIONID"].unique()) != set(NEM_REGIONS):
        logger.error(f"Missing regions")
        return False

    logger.info(f"Feature validation passed")
    logger.info(f"Feature columns: {feature_cols}")
    return True


def main():
    logger.info("=" * 60)
    logger.info("c2_01_feature_engineering.py started")
    logger.info(f"Timestamp: {datetime.now()}")
    logger.info(f"Feature lock rule: {FEATURE_LOCK_RULE}")
    logger.info("=" * 60)

    processed, raw, locked_features, is_sample = load_inputs()

    features = engineer_features(processed, raw, locked_features)

    logger.info("Validating feature matrix...")
    if not validate_features(features, locked_features):
        logger.error("c2_01 FAILED — validation failed")
        sys.exit(1)

    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    features.to_csv(OUTPUT_FILE, index=False)
    logger.info(f"Saved: {OUTPUT_FILE} ({len(features):,} rows)")

    if is_sample:
        logger.warning("SAMPLE MODE: results not final")

    logger.info("=" * 60)
    logger.info("c2_01 COMPLETE")
    logger.info(f"Total intervals: {len(features):,}")
    logger.info(f"Features: {len([c for c in features.columns if c.startswith('f_')])}")
    logger.info("Next: ./run.sh scripts/c2_02_train_test_split.py")
    logger.info("=" * 60)
    sys.exit(0)


if __name__ == "__main__":
    main()
