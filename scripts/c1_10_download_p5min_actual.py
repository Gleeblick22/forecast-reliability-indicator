"""
c1_04b_download_p5min_actual.py
====================================
Downloads AEMO NEM P5MIN price data (REGIONSOLUTION table),
the forecast issued 5 minutes before real time, used as a
practical proxy for the "actual" settled price for label
redefinition (reviewer-requested leakage/definition fix).

Output:
  data/raw/aemo_nem/aemo_nem_p5min_actual_2021_2022_raw.csv
Project: forecast-reliability-indicator (FRI)
OSF:     10.17605/OSF.IO/Z89HD
"""
import sys
import pandas as pd
from datetime import datetime
from nemseer import compile_data, download_raw_data
from config.settings import AEMO_RAW_DIR, AEMO_START_DATE, AEMO_END_DATE
from config.logging_config import get_logger

logger = get_logger("c1_04b_download_p5min_actual")

OUTPUT_FILE = AEMO_RAW_DIR / "aemo_nem_p5min_actual_2021_2022_raw.csv"
CACHE_DIR   = AEMO_RAW_DIR / "cache_p5min"

def main():
    logger.info("=" * 60)
    logger.info("c1_04b_download_p5min_actual.py started")
    logger.info(f"Timestamp: {datetime.now()}")
    logger.info("=" * 60)

    CACHE_DIR.mkdir(parents=True, exist_ok=True)

    start_str = str(AEMO_START_DATE).replace("-", "/") + " 00:00:00"
    end_str   = str(AEMO_END_DATE).replace("-", "/") + " 23:55:00"

    logger.info("Compiling already-downloaded P5MIN REGIONSOLUTION data...")
    logger.info(f"Run period: {start_str} to {end_str}")

    df = compile_data(
        forecast_type="P5MIN",
        tables="REGIONSOLUTION",
        raw_cache=str(CACHE_DIR),
        run_start=start_str,
        run_end=end_str,
        forecasted_start=start_str,
        forecasted_end=end_str,
    )

    logger.info(f"Downloaded rows: {len(df):,}")
    logger.info(f"Columns: {list(df.columns)}")
    df.to_csv(OUTPUT_FILE, index=False)
    logger.info(f"Saved: {OUTPUT_FILE}")
    logger.info("=" * 60)
    sys.exit(0)

if __name__ == "__main__":
    main()
