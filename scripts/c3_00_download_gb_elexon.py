"""
c3_00_download_gb_elexon.py
============================
Downloads Great Britain electricity system
prices from Elexon BMRS API.

Source: Elexon Balancing Mechanism Reporting Service
URL:    https://data.elexon.co.uk/bmrs/api/v1/
Market: GB electricity balancing market
Price:  System Buy Price (GBP/MWh)
Period: 2021-01-01 to 2022-12-31
Freq:   30-minute settlement periods

Output: data/raw/gb_elexon/gb_elexon_2021_2022.csv

Project: forecast-reliability-indicator (FRI)
OSF:     10.17605/OSF.IO/Z89HD
"""

import sys
import requests
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path
import time

from config.settings import RAW_DIR
from config.logging_config import get_logger

logger = get_logger("c3_00_download_gb_elexon")

GB_RAW_DIR  = RAW_DIR / "gb_elexon"
OUTPUT_FILE = GB_RAW_DIR / "gb_elexon_2021_2022.csv"
BASE_URL    = "https://data.elexon.co.uk/bmrs/api/v1/balancing/settlement/system-prices"
START_DATE  = "2021-01-01"
END_DATE    = "2022-12-31"


def download_day(date_str: str) -> pd.DataFrame:
    """Download one day of GB system prices."""
    url = f"{BASE_URL}/{date_str}"
    try:
        r = requests.get(url, timeout=30)
        r.raise_for_status()
        data = r.json()
        rows = data.get("data", [])
        if not rows:
            return None
        df = pd.DataFrame(rows)
        return df
    except Exception as e:
        logger.warning(f"Failed {date_str}: {e}")
        return None


def main():
    logger.info("=" * 60)
    logger.info("c3_00_download_gb_elexon.py started")
    logger.info(f"Timestamp: {datetime.now()}")
    logger.info(f"Source: Elexon BMRS API")
    logger.info(f"Period: {START_DATE} to {END_DATE}")
    logger.info("=" * 60)

    GB_RAW_DIR.mkdir(parents=True, exist_ok=True)

    start = datetime.strptime(START_DATE, "%Y-%m-%d")
    end   = datetime.strptime(END_DATE,   "%Y-%m-%d")

    all_days = []
    current  = start
    total_days = (end - start).days + 1
    done = 0

    while current <= end:
        date_str = current.strftime("%Y-%m-%d")
        df = download_day(date_str)
        if df is not None:
            all_days.append(df)
        done += 1

        if done % 30 == 0:
            logger.info(f"Progress: {done}/{total_days} days downloaded")

        current += timedelta(days=1)
        time.sleep(0.1)  # Rate limiting

    if not all_days:
        logger.error("No data downloaded")
        sys.exit(1)

    combined = pd.concat(all_days, ignore_index=True)
    combined["DATETIME"] = pd.to_datetime(combined["startTime"])
    combined = combined.rename(columns={"systemBuyPrice": "PRICE"})
    combined = combined[["DATETIME", "PRICE",
                          "settlementDate", "settlementPeriod"]]
    combined = combined.sort_values("DATETIME").reset_index(drop=True)
    combined = combined.dropna(subset=["PRICE"])

    combined.to_csv(OUTPUT_FILE, index=False)

    logger.info("=" * 60)
    logger.info("c3_00 COMPLETE")
    logger.info(f"Total rows:    {len(combined):,}")
    logger.info(f"Date range:    {combined['DATETIME'].min()} to {combined['DATETIME'].max()}")
    logger.info(f"Mean price:    {combined['PRICE'].mean():.2f} GBP/MWh")
    logger.info(f"Max price:     {combined['PRICE'].max():.2f} GBP/MWh")
    logger.info(f"Saved:         {OUTPUT_FILE}")
    logger.info("Next: ./run.sh scripts/c3_06_test_h8_gb_validation.py")
    logger.info("=" * 60)
    sys.exit(0)


if __name__ == "__main__":
    main()
