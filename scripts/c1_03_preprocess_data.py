"""
c1_03_preprocess_data.py
========================
Preprocesses raw AEMO NEM data into analysis-ready format.

For each interval and region:
  1. Removes duplicates per Decision 6
  2. Calculates forecast error (earliest vs latest run) per D1
  3. Classifies regime (extreme or normal) per D2
  4. Extracts P5 and P30 horizon errors separately per D7
  5. Validates and saves output

Input:  data/raw/aemo_nem/aemo_nem_all_2021_2022_raw.csv
Output: data/processed/aemo_nem_all_2021_2022_processed.csv

Decisions applied:
  D1: forecast_error = |earliest_forecast - latest_forecast|
  D2: extreme if last_forecast >= 300
  D6: keep latest LASTCHANGED for duplicates
  D7: P5 = final run, P30 = run in 25-35 min window

Project: forecast-reliability-indicator (FRI)
OSF:     10.17605/OSF.IO/Z89HD
"""

import sys
import pandas as pd
import numpy as np
from datetime import datetime

from config.settings import (
    AEMO_RAW_DIR,
    PROCESSED_DIR,
    NEM_REGIONS,
    PRICE_THRESHOLD_NEM,
    H3_P30_WINDOW_MIN,
    H3_P30_WINDOW_MAX,
)
from config.logging_config import get_logger

logger = get_logger("c1_03_preprocess_data")

FULL_PATH   = AEMO_RAW_DIR / "aemo_nem_all_2021_2022_raw.csv"
SAMPLE_PATH = AEMO_RAW_DIR / "aemo_nem_sample_raw.csv"


def load_data() -> tuple:
    """Load raw data. Auto-detects full vs sample."""
    if FULL_PATH.exists():
        path      = FULL_PATH
        is_sample = False
        logger.info("Loading full dataset")
    else:
        path      = SAMPLE_PATH
        is_sample = True
        logger.warning("Full dataset not found — using sample")

    df = pd.read_csv(
        path,
        parse_dates=["DATETIME", "PREDISPATCH_RUN_DATETIME", "LASTCHANGED"],
    )
    logger.info(f"Loaded {len(df):,} rows")
    return df, is_sample


def remove_duplicates(df: pd.DataFrame) -> pd.DataFrame:
    """Remove duplicates per Decision 6 — keep latest LASTCHANGED."""
    key_cols = ["DATETIME", "REGIONID", "PREDISPATCH_RUN_DATETIME"]
    before   = len(df)

    df = df.sort_values("LASTCHANGED", ascending=False)
    df = df.drop_duplicates(subset=key_cols, keep="first")
    df = df.sort_values(
        ["REGIONID", "DATETIME", "PREDISPATCH_RUN_DATETIME"]
    ).reset_index(drop=True)

    removed = before - len(df)
    if removed > 0:
        logger.warning(f"Removed {removed:,} duplicate rows")
    else:
        logger.info("No duplicates found")
    return df


def process_intervals(df: pd.DataFrame) -> pd.DataFrame:
    """
    For each interval and region:
    - Calculate forecast error (D1)
    - Classify regime (D2)
    - Extract P5 and P30 horizon errors (D7)

    All horizon work done on RAW runs before collapsing.
    """
    logger.info("Processing intervals...")
    results = []
    groups  = df.groupby(["DATETIME", "REGIONID"])
    total   = len(groups)

    for i, ((dt, region), group) in enumerate(groups):
        if i % 5000 == 0:
            logger.info(f"  Processing {i:,} of {total:,}...")

        group_sorted = group.sort_values("PREDISPATCH_RUN_DATETIME")
        dt_ts        = pd.Timestamp(dt)

        # D1 — Forecast error: earliest vs latest run
        first_run      = group_sorted.iloc[0]
        last_run       = group_sorted.iloc[-1]
        first_forecast = first_run["RRP"]
        last_forecast  = last_run["RRP"]
        forecast_error = abs(first_forecast - last_forecast)
        run_count      = len(group_sorted)

        # D2 — Regime classification
        regime = "extreme" if last_forecast >= PRICE_THRESHOLD_NEM else "normal"

        # D7 — P5 horizon: the final run before dispatch
        p5_rrp   = last_run["RRP"]
        p5_error = abs(first_forecast - p5_rrp)

        # D7 — P30 horizon: run closest to 25-35 min before dispatch
        p30_rrp   = None
        p30_error = None

        for _, run in group_sorted.iterrows():
            mins = (dt_ts - run["PREDISPATCH_RUN_DATETIME"]).total_seconds() / 60
            if H3_P30_WINDOW_MIN <= mins <= H3_P30_WINDOW_MAX:
                p30_rrp   = run["RRP"]
                p30_error = abs(first_forecast - p30_rrp)
                break

        results.append({
            "DATETIME":           dt,
            "REGIONID":           region,
            "first_forecast":     round(first_forecast, 4),
            "last_forecast":      round(last_forecast, 4),
            "forecast_error":     round(forecast_error, 4),
            "regime":             regime,
            "run_count":          run_count,
            "p5_rrp":             round(p5_rrp, 4),
            "p5_error":           round(p5_error, 4),
            "p30_rrp":            round(p30_rrp, 4) if p30_rrp is not None else None,
            "p30_error":          round(p30_error, 4) if p30_error is not None else None,
            "has_p30":            p30_rrp is not None,
            "first_run_datetime": first_run["PREDISPATCH_RUN_DATETIME"],
            "last_run_datetime":  last_run["PREDISPATCH_RUN_DATETIME"],
        })

    processed = pd.DataFrame(results)
    logger.info(f"Processed {len(processed):,} intervals")
    return processed


def log_summary(df: pd.DataFrame) -> None:
    """Log summary statistics per region."""
    logger.info("=== PROCESSED DATA SUMMARY ===")

    extreme_total = (df["regime"] == "extreme").sum()
    normal_total  = (df["regime"] == "normal").sum()
    p30_total     = df["has_p30"].sum()
    logger.info(
        f"TOTAL: {len(df):,} intervals | "
        f"extreme={extreme_total:,} | normal={normal_total:,} | "
        f"intervals_with_P30={p30_total:,}"
    )

    for region in NEM_REGIONS:
        r        = df[df["REGIONID"] == region]
        extreme  = (r["regime"] == "extreme").sum()
        normal   = (r["regime"] == "normal").sum()
        mean_err = r["forecast_error"].mean()
        max_err  = r["forecast_error"].max()
        p30_cnt  = r["has_p30"].sum()
        logger.info(
            f"{region}: {len(r):,} intervals | "
            f"extreme={extreme:,} | normal={normal:,} | "
            f"mean_error=${mean_err:.2f} | max_error=${max_err:.2f} | "
            f"P30_runs={p30_cnt:,}"
        )


def validate_output(df: pd.DataFrame) -> bool:
    """Validate processed output before saving."""
    required = [
        "DATETIME", "REGIONID", "first_forecast",
        "last_forecast", "forecast_error", "regime",
        "p5_rrp", "p5_error", "has_p30"
    ]

    missing_cols = [c for c in required if c not in df.columns]
    if missing_cols:
        logger.error(f"Missing columns: {missing_cols}")
        return False

    null_critical = df[["DATETIME", "REGIONID", "forecast_error", "regime"]].isnull().sum()
    if null_critical.any():
        logger.error(f"Nulls in critical columns: {null_critical[null_critical > 0].to_dict()}")
        return False

    if set(df["REGIONID"].unique()) != set(NEM_REGIONS):
        logger.error(f"Region mismatch: {df['REGIONID'].unique()}")
        return False

    if not set(df["regime"].unique()).issubset({"extreme", "normal"}):
        logger.error("Invalid regime values")
        return False

    logger.info("Output validation passed")
    return True


def save_output(df: pd.DataFrame, is_sample: bool) -> object:
    """Save processed data to data/processed/."""
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    filename    = (
        "aemo_nem_sample_processed.csv"
        if is_sample
        else "aemo_nem_all_2021_2022_processed.csv"
    )
    output_path = PROCESSED_DIR / filename
    df.to_csv(output_path, index=False)
    logger.info(f"Saved: {output_path} ({len(df):,} rows)")
    return output_path


def main():
    logger.info("=" * 60)
    logger.info("c1_03_preprocess_data.py started")
    logger.info(f"Timestamp: {datetime.now()}")
    logger.info("=" * 60)

    df, is_sample = load_data()

    logger.info("Step 1: Removing duplicates...")
    df = remove_duplicates(df)

    logger.info("Step 2: Processing intervals...")
    processed = process_intervals(df)

    logger.info("Step 3: Validating output...")
    if not validate_output(processed):
        logger.error("c1_03 FAILED — validation failed")
        sys.exit(1)

    log_summary(processed)

    logger.info("Step 4: Saving output...")
    output_path = save_output(processed, is_sample)

    logger.info("=" * 60)
    logger.info("c1_03 COMPLETE")
    logger.info(f"Output: {output_path}")
    logger.info(f"Total intervals: {len(processed):,}")
    logger.info("Next: ./run.sh scripts/c1_04_test_h1_amplification.py")
    logger.info("=" * 60)
    sys.exit(0)


if __name__ == "__main__":
    main()
