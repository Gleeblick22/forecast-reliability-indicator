"""
c1_23_extract_true_dispatchprice.py
======================================
Priority 1 (post-Round-2 meta-review): extracts the true,
genuine settled RRP from AEMO's MMSDM DISPATCHPRICE archive
for the test partition (Nov-Dec 2022), replacing the P5MIN
proxy used throughout Phase 3 for NEM's outcome measure.

Input:  data/raw/aemo_nem/dispatchprice/PUBLIC_DVD_DISPATCHPRICE_202211010000.CSV
        data/raw/aemo_nem/dispatchprice/PUBLIC_DVD_DISPATCHPRICE_202212010000.CSV
Output: data/processed/true_dispatchprice_test_partition.csv
"""
import sys
import pandas as pd
from config.settings import PROCESSED_DIR, AEMO_RAW_DIR
from config.logging_config import get_logger

logger = get_logger("c1_23_extract_true_dispatchprice")

FILES = [
    AEMO_RAW_DIR / "dispatchprice" / "PUBLIC_DVD_DISPATCHPRICE_202211010000.CSV",
    AEMO_RAW_DIR / "dispatchprice" / "PUBLIC_DVD_DISPATCHPRICE_202212010000.CSV",
]

def load_dispatchprice_file(path):
    logger.info(f"Loading {path.name}...")
    df = pd.read_csv(path, skiprows=1, header=0, low_memory=False)
    df = df[df.iloc[:, 0] == "D"].copy()
    df = df[["SETTLEMENTDATE", "REGIONID", "RRP"]].copy()
    df["SETTLEMENTDATE"] = pd.to_datetime(df["SETTLEMENTDATE"])
    df["RRP"] = pd.to_numeric(df["RRP"], errors="coerce")
    logger.info(f"  Loaded {len(df):,} rows")
    return df

def main():
    logger.info("=" * 60)
    logger.info("c1_23_extract_true_dispatchprice.py started")
    logger.info("=" * 60)

    dfs = [load_dispatchprice_file(f) for f in FILES]
    full = pd.concat(dfs, ignore_index=True)
    logger.info(f"Combined: {len(full):,} rows (5-min resolution)")

    # Filter to NEM regions used in this study
    regions = ["NSW1", "VIC1", "QLD1", "SA1", "TAS1"]
    full = full[full["REGIONID"].isin(regions)]

    # Align to 30-minute intervals: select the price AT each 30-min mark
    # (minute == 0 or 30), matching the study's interval resolution
    full["minute"] = full["SETTLEMENTDATE"].dt.minute
    thirty_min = full[full["minute"].isin([0, 30])].copy()
    thirty_min = thirty_min.rename(columns={"SETTLEMENTDATE": "DATETIME", "RRP": "true_dispatchprice"})
    thirty_min = thirty_min[["DATETIME", "REGIONID", "true_dispatchprice"]]

    logger.info(f"30-min aligned rows: {len(thirty_min):,}")
    logger.info(f"Date range: {thirty_min['DATETIME'].min()} to {thirty_min['DATETIME'].max()}")
    logger.info(f"Price stats:\n{thirty_min['true_dispatchprice'].describe()}")

    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    thirty_min.to_csv(PROCESSED_DIR / "true_dispatchprice_test_partition.csv", index=False)
    logger.info(f"Saved: {PROCESSED_DIR / 'true_dispatchprice_test_partition.csv'}")
    logger.info("=" * 60)
    sys.exit(0)

if __name__ == "__main__":
    main()
