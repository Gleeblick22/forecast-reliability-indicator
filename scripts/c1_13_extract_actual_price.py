"""
c1_04e_extract_actual_price.py
================================
Extracts p_actual for each 30-minute interval: the P5MIN
price forecast from the run closest to (but not after)
that interval, i.e. the freshest available estimate.

Input:  data/raw/aemo_nem/aemo_nem_p5min_actual_2021_2022_raw.csv
Output: data/processed/p5min_actual_price_30min.csv
        (one row per REGIONID + 30-min DATETIME, with p_actual)
"""
import sys
import pandas as pd
from config.settings import AEMO_RAW_DIR, PROCESSED_DIR
from config.logging_config import get_logger

logger = get_logger("c1_04e_extract_actual_price")

INPUT_FILE  = AEMO_RAW_DIR / "aemo_nem_p5min_actual_2021_2022_raw.csv"
OUTPUT_FILE = PROCESSED_DIR / "p5min_actual_price_30min.csv"

def main():
    logger.info("=" * 60)
    logger.info("c1_04e_extract_actual_price.py started")
    logger.info("=" * 60)

    logger.info("Loading P5MIN raw data...")
    df = pd.read_csv(INPUT_FILE, parse_dates=["RUN_DATETIME", "INTERVAL_DATETIME"])
    logger.info(f"Loaded rows: {len(df):,}")

    # Only keep 30-minute-aligned target intervals (on the hour or half-hour)
    # since that's the resolution of your existing predispatch dataset
    is_30min_boundary = (df["INTERVAL_DATETIME"].dt.minute % 30 == 0)
    df_30 = df[is_30min_boundary].copy()
    logger.info(f"Rows at 30-min boundaries: {len(df_30):,}")

    # For each (REGIONID, INTERVAL_DATETIME), keep the row with the
    # LATEST RUN_DATETIME that is still <= INTERVAL_DATETIME
    # (i.e. the freshest available estimate before the interval occurred)
    df_30 = df_30[df_30["RUN_DATETIME"] <= df_30["INTERVAL_DATETIME"]]
    df_30 = df_30.sort_values(["REGIONID", "INTERVAL_DATETIME", "RUN_DATETIME"])
    df_actual = df_30.groupby(["REGIONID", "INTERVAL_DATETIME"], as_index=False).last()

    df_actual = df_actual.rename(columns={
        "INTERVAL_DATETIME": "DATETIME",
        "RRP": "p_actual",
    })[["DATETIME", "REGIONID", "p_actual", "RUN_DATETIME"]]
    df_actual = df_actual.rename(columns={"RUN_DATETIME": "p_actual_run_datetime"})

    logger.info(f"Final rows: {len(df_actual):,}")
    logger.info(f"Regions: {df_actual['REGIONID'].unique().tolist()}")
    logger.info(f"Date range: {df_actual['DATETIME'].min()} to {df_actual['DATETIME'].max()}")
    logger.info(f"p_actual stats:\n{df_actual['p_actual'].describe()}")

    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    df_actual.to_csv(OUTPUT_FILE, index=False)
    logger.info(f"Saved: {OUTPUT_FILE}")
    logger.info("=" * 60)
    sys.exit(0)

if __name__ == "__main__":
    main()
