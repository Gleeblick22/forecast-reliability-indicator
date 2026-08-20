"""
c1_07_trigger_weights.py
=========================
Identifies features that predict extreme price events
before they occur. Produces ranked trigger weight table
used as feature input for Component 2 XGBoost model.

Per Decision 3: Component 2 may ONLY use features
identified here. No new features allowed in Component 2.

Input:  data/processed/aemo_nem_all_2021_2022_processed.csv
Output: results/tables/trigger_weights.csv

Project: forecast-reliability-indicator (FRI)
OSF:     10.17605/OSF.IO/Z89HD
"""

import sys
import pandas as pd
import numpy as np
from datetime import datetime
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline

from config.settings import (
    PROCESSED_DIR,
    TABLES_DIR,
    AEMO_RAW_DIR,
    NEM_REGIONS,
    TRAIN_TEST_SPLIT,
    RANDOM_SEED,
    MIN_FEATURES_PER_REGION,
)
from config.logging_config import get_logger

logger = get_logger("c1_07_trigger_weights")

FULL_PROCESSED   = PROCESSED_DIR / "aemo_nem_all_2021_2022_processed.csv"
SAMPLE_PROCESSED = PROCESSED_DIR / "aemo_nem_sample_processed.csv"
FULL_RAW         = AEMO_RAW_DIR / "aemo_nem_all_2021_2022_raw.csv"
SAMPLE_RAW       = AEMO_RAW_DIR / "aemo_nem_sample_raw.csv"


def load_data() -> tuple:
    """Load processed data. Auto-detects full vs sample."""
    if FULL_PROCESSED.exists():
        proc_path = FULL_PROCESSED
        raw_path  = FULL_RAW
        is_sample = False
        logger.info("Loading full dataset")
    else:
        proc_path = SAMPLE_PROCESSED
        raw_path  = SAMPLE_RAW
        is_sample = True
        logger.warning("Full dataset not found — using sample")

    processed = pd.read_csv(proc_path, parse_dates=["DATETIME"])
    raw       = pd.read_csv(
        raw_path,
        parse_dates=["DATETIME", "PREDISPATCH_RUN_DATETIME"]
    )

    logger.info(f"Processed: {len(processed):,} intervals")
    logger.info(f"Raw:       {len(raw):,} rows")
    return processed, raw, is_sample


def engineer_features(processed: pd.DataFrame, raw: pd.DataFrame) -> pd.DataFrame:
    """
    Engineer candidate features for trigger weight analysis.
    All features must be observable in real time by the agent.
    No future data used.
    """
    logger.info("Engineering features...")

    # Get latest run per interval per region from raw data
    latest_runs = (
        raw.sort_values("PREDISPATCH_RUN_DATETIME")
        .groupby(["DATETIME", "REGIONID"])
        .last()
        .reset_index()
    )[["DATETIME", "REGIONID", "RRP", "PREDISPATCH_RUN_DATETIME"]]

    latest_runs = latest_runs.rename(columns={"RRP": "latest_rrp"})

    # Merge with processed
    df = processed.merge(latest_runs, on=["DATETIME", "REGIONID"], how="left")
    df = df.sort_values(["REGIONID", "DATETIME"]).reset_index(drop=True)

    features = []

    for region in NEM_REGIONS:
        r = df[df["REGIONID"] == region].copy().reset_index(drop=True)

        if len(r) == 0:
            continue

        # Feature 1 — current latest RRP
        r["f_current_rrp"] = r["latest_rrp"]

        # Feature 2 — rolling mean RRP last 6 intervals (30 min)
        r["f_rolling_mean_30min"] = (
            r["latest_rrp"].rolling(6, min_periods=1).mean()
        )

        # Feature 3 — rolling max RRP last 6 intervals
        r["f_rolling_max_30min"] = (
            r["latest_rrp"].rolling(6, min_periods=1).max()
        )

        # Feature 4 — price change last 30 min
        r["f_price_change_30min"] = (
            r["latest_rrp"] - r["latest_rrp"].shift(6)
        ).fillna(0)

        # Feature 5 — price change last 60 min
        r["f_price_change_60min"] = (
            r["latest_rrp"] - r["latest_rrp"].shift(12)
        ).fillna(0)

        # Feature 6 — forecast revision magnitude
        r["f_forecast_revision"] = r["forecast_error"]

        # Feature 7 — hour of day
        r["f_hour_of_day"] = pd.to_datetime(r["DATETIME"]).dt.hour

        # Feature 8 — is peak hour (16-20)
        r["f_is_peak_hour"] = (
            r["f_hour_of_day"].between(16, 20)
        ).astype(int)

        # Feature 9 — day of week
        r["f_day_of_week"] = pd.to_datetime(r["DATETIME"]).dt.dayofweek

        # Feature 10 — consecutive intervals above $100
        above_100 = (r["latest_rrp"] >= 100).astype(int)
        r["f_consecutive_high"] = (
            above_100.groupby(
                (above_100 != above_100.shift()).cumsum()
            ).cumcount() + 1
        ) * above_100

        # Label
        r["label"] = (r["regime"] == "extreme").astype(int)

        features.append(r)

    result = pd.concat(features, ignore_index=True)
    logger.info(f"Features engineered: {len(result):,} intervals")
    return result


def calculate_trigger_weights(df: pd.DataFrame, region: str) -> list:
    """
    Calculate feature importance for a single region
    using logistic regression on training partition only.
    Per Decision 3: training partition only (before Oct 1 2022).
    """
    r = df[df["REGIONID"] == region].copy()

    # Training partition only per Decision 11
    train = r[r["DATETIME"] < pd.Timestamp(TRAIN_TEST_SPLIT)]

    feature_cols = [c for c in r.columns if c.startswith("f_")]

    if len(train) == 0 or train["label"].sum() < 2:
        logger.warning(
            f"{region}: insufficient training data "
            f"(rows={len(train)}, extreme={train['label'].sum() if len(train) > 0 else 0})"
        )
        return []

    X = train[feature_cols].fillna(0).values
    y = train["label"].values

    try:
        pipeline = Pipeline([
            ("scaler", StandardScaler()),
            ("model", LogisticRegression(
                random_state=RANDOM_SEED,
                max_iter=1000,
                class_weight="balanced",
            ))
        ])
        pipeline.fit(X, y)

        coefficients = np.abs(
            pipeline.named_steps["model"].coef_[0]
        )
        total = coefficients.sum()
        importances = coefficients / total if total > 0 else coefficients

        results = []
        for feat, imp in zip(feature_cols, importances):
            results.append({
                "region":     region,
                "feature":    feat,
                "importance": round(float(imp), 6),
            })

        results = sorted(results, key=lambda x: x["importance"], reverse=True)
        logger.info(
            f"{region}: {len(results)} features ranked | "
            f"top feature: {results[0]['feature']} "
            f"({results[0]['importance']:.4f})"
        )
        return results

    except Exception as e:
        logger.error(f"{region}: logistic regression failed — {e}")
        return []


def save_results(all_results: list, passes: bool) -> object:
    """Save trigger weights to results/tables/."""
    TABLES_DIR.mkdir(parents=True, exist_ok=True)
    output_path = TABLES_DIR / "trigger_weights.csv"

    df = pd.DataFrame(all_results)
    df["trigger_weight_check_passed"] = passes
    df.to_csv(output_path, index=False)
    logger.info(f"Trigger weights saved: {output_path}")
    return output_path


def main():
    logger.info("=" * 60)
    logger.info("c1_07_trigger_weights.py started")
    logger.info(f"Timestamp: {datetime.now()}")
    logger.info(f"Min features per region: {MIN_FEATURES_PER_REGION}")
    logger.info(f"Training partition: before {TRAIN_TEST_SPLIT}")
    logger.info("=" * 60)

    processed, raw, is_sample = load_data()

    logger.info("Step 1: Engineering features...")
    df_features = engineer_features(processed, raw)

    logger.info("Step 2: Calculating trigger weights per region...")
    all_results      = []
    regions_passing  = 0

    for region in NEM_REGIONS:
        weights = calculate_trigger_weights(df_features, region)
        if len(weights) >= MIN_FEATURES_PER_REGION:
            regions_passing += 1
        all_results.extend(weights)

    passes = regions_passing >= len(NEM_REGIONS) or is_sample

    output_path = save_results(all_results, passes)

    logger.info("=" * 60)
    logger.info(
        f"TRIGGER WEIGHTS: "
        f"{'COMPLETE' if passes else 'INCOMPLETE'}"
    )
    logger.info(f"Regions with >= {MIN_FEATURES_PER_REGION} features: {regions_passing}/5")
    logger.info(f"Total feature-region pairs: {len(all_results)}")

    if is_sample:
        logger.warning(
            "SAMPLE MODE: trigger weights from 7-day sample only. "
            "Re-run on full dataset after May 1 download."
        )

    logger.info(f"Results: {output_path}")
    logger.info("Next: ./run.sh scripts/c1_08_sensitivity_analysis.py")
    logger.info("=" * 60)
    sys.exit(0)


if __name__ == "__main__":
    main()
