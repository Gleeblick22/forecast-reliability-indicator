"""
c1_04i_rebuild_revision_feature.py
=====================================
Rebuilds f_forecast_revision using only pre-dispatch runs
issued 30-60 minutes before the target interval, removing
the near-final-run leakage identified by Reviewer 4.

For each (REGIONID, DATETIME), selects:
  - earliest_run_price: the earliest available run's RRP (unchanged, already leakage-safe)
  - lead30_60_price: the RRP from the run with lead time closest to 30-60 min
  - new_revision = |lead30_60_price - earliest_run_price|

Input:  data/raw/aemo_nem/aemo_nem_all_2021_2022_raw.csv
Output: data/processed/revision_feature_leakage_controlled.csv
"""
import sys
import pandas as pd
from config.settings import AEMO_RAW_DIR, PROCESSED_DIR
from config.logging_config import get_logger

logger = get_logger("c1_04i_rebuild_revision_feature")

INPUT_FILE  = AEMO_RAW_DIR / "aemo_nem_all_2021_2022_raw.csv"
OUTPUT_FILE = PROCESSED_DIR / "revision_feature_leakage_controlled.csv"

def main():
    logger.info("=" * 60)
    logger.info("c1_04i_rebuild_revision_feature.py started")
    logger.info("=" * 60)

    logger.info("Loading raw predispatch run data (this may take a while)...")
    df = pd.read_csv(INPUT_FILE, usecols=["REGIONID", "RRP", "DATETIME", "PREDISPATCH_RUN_DATETIME"])
    df["DATETIME"] = pd.to_datetime(df["DATETIME"])
    df["PREDISPATCH_RUN_DATETIME"] = pd.to_datetime(df["PREDISPATCH_RUN_DATETIME"])
    logger.info(f"Loaded rows: {len(df):,}")

    df["lead_minutes"] = (df["DATETIME"] - df["PREDISPATCH_RUN_DATETIME"]).dt.total_seconds() / 60
    df = df[df["lead_minutes"] >= 0]

    # Earliest run per target interval (unchanged, leakage-safe baseline)
    earliest = df.sort_values("lead_minutes", ascending=False) \
                 .groupby(["REGIONID", "DATETIME"], as_index=False).first()
    earliest = earliest.rename(columns={"RRP": "earliest_run_price", "lead_minutes": "earliest_lead_min"})
    earliest = earliest[["REGIONID", "DATETIME", "earliest_run_price", "earliest_lead_min"]]
    logger.info(f"Earliest-run rows: {len(earliest):,}")
    logger.info(f"Earliest lead time stats:\n{earliest['earliest_lead_min'].describe()}")

    # Run closest to 30-60 min lead window (target midpoint = 45 min)
    window = df[(df["lead_minutes"] >= 30) & (df["lead_minutes"] <= 60)].copy()
    window["dist_from_45"] = (window["lead_minutes"] - 45).abs()
    window = window.sort_values("dist_from_45").groupby(["REGIONID", "DATETIME"], as_index=False).first()
    window = window.rename(columns={"RRP": "lead30_60_price", "lead_minutes": "lead30_60_actual_min"})
    window = window[["REGIONID", "DATETIME", "lead30_60_price", "lead30_60_actual_min"]]
    logger.info(f"30-60min-window rows: {len(window):,}")
    logger.info(f"Actual lead time stats (within window):\n{window['lead30_60_actual_min'].describe()}")

    merged = earliest.merge(window, on=["REGIONID", "DATETIME"], how="inner")
    logger.info(f"Merged rows (both available): {len(merged):,}")

    merged["new_revision"] = (merged["lead30_60_price"] - merged["earliest_run_price"]).abs()
    logger.info(f"New revision feature stats:\n{merged['new_revision'].describe()}")

    merged.to_csv(OUTPUT_FILE, index=False)
    logger.info(f"Saved: {OUTPUT_FILE}")
    logger.info("=" * 60)
    sys.exit(0)

if __name__ == "__main__":
    main()
