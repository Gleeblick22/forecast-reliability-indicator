"""
c1_01_download_aemo_nem.py
==========================
Downloads AEMO NEM predispatch price data for
the full research period 2022 and combines with
existing Q4 2021 data into one master file.

Existing data:
  data/raw/aemo_nem/aemo_nem_q4_2021_raw.csv

Downloads:
  Full 2022 AEMO predispatch price data

Output:
  data/raw/aemo_nem/aemo_nem_all_2021_2022_raw.csv

Project: forecast-reliability-indicator (FRI)
OSF:     10.17605/OSF.IO/Z89HD
"""

import sys
import pandas as pd
from datetime import datetime

from nemseer import compile_data, download_raw_data
from config.settings import (
    AEMO_RAW_DIR,
    NEM_REGIONS,
    AEMO_START_DATE,
    AEMO_END_DATE,
)
from config.logging_config import get_logger

logger = get_logger("c1_01_download_aemo_nem")

MASTER_FILE  = AEMO_RAW_DIR / "aemo_nem_all_2021_2022_raw.csv"
Q4_2021_FILE = AEMO_RAW_DIR / "aemo_nem_q4_2021_raw.csv"
DATA_2022    = AEMO_RAW_DIR / "aemo_nem_2022_raw.csv"
CACHE_DIR    = AEMO_RAW_DIR / "cache"


def download_2022_data() -> None:
    """Download full 2022 AEMO predispatch price data."""
    if DATA_2022.exists():
        logger.info("2022 data already exists — skipping download")
        return

    logger.info("Downloading 2022 AEMO data...")
    logger.info("This may take 30 to 60 minutes")

    CACHE_DIR.mkdir(parents=True, exist_ok=True)

    download_raw_data(
        forecast_type="PREDISPATCH",
        tables="PRICE",
        raw_cache=str(CACHE_DIR),
        run_start="2022/01/01 00:00:00",
        run_end="2022/12/31 23:30:00",
    )

    logger.info("Compiling downloaded data...")
    df = compile_data(
        forecast_type="PREDISPATCH",
        tables="PRICE",
        raw_cache=str(CACHE_DIR),
        run_start="2022/01/01 00:00:00",
        run_end="2022/12/31 23:30:00",
    )

    df.to_csv(DATA_2022, index=False)
    logger.info(f"2022 data saved: {len(df):,} rows")


def combine_datasets() -> pd.DataFrame:
    """Combine Q4 2021 and 2022 data into master file."""
    if not Q4_2021_FILE.exists():
        raise FileNotFoundError(f"Q4 2021 file missing: {Q4_2021_FILE}")
    if not DATA_2022.exists():
        raise FileNotFoundError(f"2022 file missing: {DATA_2022}")

    logger.info("Loading Q4 2021 data...")
    df_q4 = pd.read_csv(Q4_2021_FILE, parse_dates=["DATETIME"])
    logger.info(f"Q4 2021 rows: {len(df_q4):,}")

    logger.info("Loading 2022 data...")
    df_2022 = pd.read_csv(DATA_2022, parse_dates=["DATETIME"])
    logger.info(f"2022 rows: {len(df_2022):,}")

    logger.info("Combining datasets...")
    df = pd.concat([df_q4, df_2022], ignore_index=True)
    df = df.sort_values("DATETIME").reset_index(drop=True)
    df = df.drop_duplicates(
        subset=["DATETIME", "REGIONID", "PREDISPATCH_RUN_DATETIME"],
        keep="first"
    )

    logger.info(f"Combined rows: {len(df):,}")
    logger.info(f"Date range: {df['DATETIME'].min()} to {df['DATETIME'].max()}")
    logger.info(f"Regions: {df['REGIONID'].unique().tolist()}")
    return df


def validate_master(df: pd.DataFrame) -> bool:
    """Validate master file meets research requirements."""
    errors = []

    regions_found = set(df["REGIONID"].unique())
    if regions_found != set(NEM_REGIONS):
        errors.append(f"Missing regions: {set(NEM_REGIONS) - regions_found}")

    if df["DATETIME"].min() > pd.Timestamp(AEMO_START_DATE):
        errors.append(f"Data starts too late: {df['DATETIME'].min()}")

    if df["DATETIME"].max() < pd.Timestamp(AEMO_END_DATE):
        errors.append(f"Data ends too early: {df['DATETIME'].max()}")

    required = ["DATETIME", "REGIONID", "RRP", "PREDISPATCH_RUN_DATETIME"]
    missing  = [c for c in required if c not in df.columns]
    if missing:
        errors.append(f"Missing columns: {missing}")

    if len(df) < 1000000:
        errors.append(f"Too few rows: {len(df):,} (expected 1M+)")

    if errors:
        for e in errors:
            logger.error(f"Validation failed: {e}")
        return False

    logger.info("Master file validation passed")
    logger.info(f"  Rows:    {len(df):,}")
    logger.info(f"  Regions: {df['REGIONID'].unique().tolist()}")
    logger.info(f"  Start:   {df['DATETIME'].min()}")
    logger.info(f"  End:     {df['DATETIME'].max()}")
    return True


def main():
    logger.info("=" * 60)
    logger.info("c1_01_download_aemo_nem.py started")
    logger.info(f"Timestamp: {datetime.now()}")
    logger.info("=" * 60)

    AEMO_RAW_DIR.mkdir(parents=True, exist_ok=True)

    if MASTER_FILE.exists():
        logger.info("Master file already exists — verifying...")
        df = pd.read_csv(MASTER_FILE, parse_dates=["DATETIME"])
        if validate_master(df):
            logger.info("Master file already valid — skipping download")
            logger.info("Next: ./run.sh scripts/c1_02_validate_data.py")
            sys.exit(0)
        else:
            logger.warning("Existing master file invalid — re-downloading")

    logger.info("Step 1: Downloading 2022 data...")
    download_2022_data()

    logger.info("Step 2: Combining datasets...")
    df = combine_datasets()

    logger.info("Step 3: Saving master file...")
    df.to_csv(MASTER_FILE, index=False)
    logger.info(f"Master file saved: {MASTER_FILE}")

    logger.info("Step 4: Validating master file...")
    if not validate_master(df):
        logger.error("c1_01 FAILED — master file validation failed")
        sys.exit(1)

    logger.info("=" * 60)
    logger.info("c1_01 COMPLETE")
    logger.info(f"Master file: {MASTER_FILE}")
    logger.info(f"Total rows: {len(df):,}")
    logger.info("Next: ./run.sh scripts/c1_02_validate_data.py")
    logger.info("=" * 60)
    sys.exit(0)


if __name__ == "__main__":
    main()
