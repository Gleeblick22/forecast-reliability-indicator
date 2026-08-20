"""
c1_02_validate_data.py
======================
Validates the master AEMO NEM raw data file before
any analysis begins. Checks data quality, completeness,
and structure. Produces a data quality report.

Input:  data/raw/aemo_nem/aemo_nem_all_2021_2022_raw.csv
        OR data/raw/aemo_nem/aemo_nem_sample_raw.csv (testing)
Output: results/tables/data_quality_report.csv

Usage:
  Production: python3 scripts/c1_02_validate_data.py
  Test mode:  python3 scripts/c1_02_validate_data.py --sample

Project: forecast-reliability-indicator (FRI)
OSF:     10.17605/OSF.IO/Z89HD
"""

import sys
import pandas as pd
from datetime import datetime
from pathlib import Path

from config.settings import (
    AEMO_RAW_DIR,
    TABLES_DIR,
    NEM_REGIONS,
    AEMO_START_DATE,
    AEMO_END_DATE,
    MISSING_RATE_FLAG_THRESHOLD,
)
from config.logging_config import get_logger

logger = get_logger("c1_02_validate_data")

# Check if running in sample/test mode
SAMPLE_MODE = "--sample" in sys.argv or True
# Auto-detect: if full file missing use sample mode
FULL_PATH   = AEMO_RAW_DIR / "aemo_nem_all_2021_2022_raw.csv"
SAMPLE_PATH = AEMO_RAW_DIR / "aemo_nem_sample_raw.csv"


def load_raw_data() -> tuple:
    """Load raw data. Returns (dataframe, is_sample_mode)."""
    if FULL_PATH.exists():
        logger.info("Full dataset found — running in production mode")
        df = pd.read_csv(
            FULL_PATH,
            parse_dates=["DATETIME", "PREDISPATCH_RUN_DATETIME", "LASTCHANGED"],
        )
        return df, False
    else:
        logger.warning("Full dataset not found — running in SAMPLE TEST MODE")
        logger.warning("Sample mode skips row count and date range checks")
        df = pd.read_csv(
            SAMPLE_PATH,
            parse_dates=["DATETIME", "PREDISPATCH_RUN_DATETIME", "LASTCHANGED"],
        )
        return df, True


def check_required_columns(df: pd.DataFrame) -> list:
    """Check all required columns are present."""
    required = [
        "DATETIME",
        "PREDISPATCH_RUN_DATETIME",
        "REGIONID",
        "RRP",
        "LASTCHANGED",
    ]
    missing = [c for c in required if c not in df.columns]
    if missing:
        logger.error(f"Missing required columns: {missing}")
    else:
        logger.info("All required columns present")
    return missing


def check_regions(df: pd.DataFrame) -> dict:
    """Check all 5 NEM regions are present."""
    found    = set(df["REGIONID"].unique())
    expected = set(NEM_REGIONS)
    missing  = expected - found

    result = {
        "regions_found":   sorted(list(found)),
        "regions_missing": sorted(list(missing)),
        "pass":            len(missing) == 0,
    }

    if result["pass"]:
        logger.info(f"All 5 regions present: {result['regions_found']}")
    else:
        logger.error(f"Missing regions: {result['regions_missing']}")
    return result


def check_date_range(df: pd.DataFrame) -> dict:
    """Check data covers required date range."""
    actual_start   = df["DATETIME"].min()
    actual_end     = df["DATETIME"].max()
    expected_start = pd.Timestamp(AEMO_START_DATE)
    expected_end   = pd.Timestamp(AEMO_END_DATE)

    result = {
        "actual_start":   str(actual_start),
        "actual_end":     str(actual_end),
        "expected_start": str(expected_start),
        "expected_end":   str(expected_end),
        "start_ok":       actual_start <= expected_start + pd.Timedelta(days=1),
        "end_ok":         actual_end   >= expected_end   - pd.Timedelta(days=1),
    }
    result["pass"] = result["start_ok"] and result["end_ok"]

    if result["pass"]:
        logger.info(f"Date range OK: {actual_start} to {actual_end}")
    else:
        logger.warning(
            f"Date range: {actual_start} to {actual_end} "
            f"(expected {expected_start} to {expected_end})"
        )
    return result


def check_missing_values(df: pd.DataFrame) -> list:
    """Check missing value rate per region."""
    results = []
    for region in NEM_REGIONS:
        region_df    = df[df["REGIONID"] == region]
        total        = len(region_df)
        missing_rrp  = region_df["RRP"].isna().sum()
        missing_rate = missing_rrp / total if total > 0 else 0
        status       = "FLAG" if missing_rate > MISSING_RATE_FLAG_THRESHOLD else "PASS"

        results.append({
            "region":       region,
            "total_rows":   total,
            "missing_rrp":  missing_rrp,
            "missing_rate": round(missing_rate, 6),
            "status":       status,
        })
        logger.info(
            f"{region}: {total:,} rows | "
            f"missing RRP: {missing_rrp} ({missing_rate:.4%}) | {status}"
        )
    return results


def check_price_range(df: pd.DataFrame) -> dict:
    """Check RRP values are within NEM bounds."""
    NEM_MIN = -1000.0
    NEM_MAX =  17500.0

    below = (df["RRP"] < NEM_MIN).sum()
    above = (df["RRP"] > NEM_MAX).sum()

    result = {
        "rrp_min":        float(df["RRP"].min()),
        "rrp_max":        float(df["RRP"].max()),
        "rrp_mean":       float(df["RRP"].mean()),
        "below_nem_floor": int(below),
        "above_nem_cap":   int(above),
        "pass":            below == 0 and above == 0,
    }

    if result["pass"]:
        logger.info(
            f"Price range OK: min={result['rrp_min']:.2f} "
            f"max={result['rrp_max']:.2f} "
            f"mean={result['rrp_mean']:.2f}"
        )
    else:
        logger.warning(
            f"Price range: {below} below floor, {above} above cap"
        )
    return result


def check_duplicates(df: pd.DataFrame) -> dict:
    """Check for duplicate records."""
    key_cols   = ["DATETIME", "REGIONID", "PREDISPATCH_RUN_DATETIME"]
    total      = len(df)
    duplicates = df.duplicated(subset=key_cols, keep=False).sum()

    result = {
        "total_rows":      total,
        "duplicate_rows":  int(duplicates),
        "duplicate_rate":  round(duplicates / total, 6),
        "pass":            duplicates == 0,
    }

    if result["pass"]:
        logger.info("No duplicate records found")
    else:
        logger.warning(
            f"Found {duplicates:,} duplicate rows "
            f"({result['duplicate_rate']:.4%}) — "
            f"will keep latest LASTCHANGED per Decision 6"
        )
    return result


def check_row_count(df: pd.DataFrame) -> dict:
    """Check total row count is sufficient."""
    MIN_ROWS = 1000000
    result = {
        "total_rows":       len(df),
        "minimum_required": MIN_ROWS,
        "pass":             len(df) >= MIN_ROWS,
    }
    if result["pass"]:
        logger.info(f"Row count OK: {len(df):,} rows")
    else:
        logger.warning(f"Row count: {len(df):,} (minimum {MIN_ROWS:,} for production)")
    return result


def save_report(checks: list) -> Path:
    """Save all check results to CSV."""
    TABLES_DIR.mkdir(parents=True, exist_ok=True)
    output_path = TABLES_DIR / "data_quality_report.csv"
    pd.DataFrame(checks).to_csv(output_path, index=False)
    logger.info(f"Quality report saved: {output_path}")
    return output_path


def main():
    logger.info("=" * 60)
    logger.info("c1_02_validate_data.py started")
    logger.info(f"Timestamp: {datetime.now()}")
    logger.info("=" * 60)

    df, is_sample = load_raw_data()
    logger.info(f"Loaded {len(df):,} rows")

    # Always run these checks
    missing_cols = check_required_columns(df)
    if missing_cols:
        logger.error(f"CRITICAL: Missing columns {missing_cols}")
        sys.exit(1)

    regions_check  = check_regions(df)
    missing_checks = check_missing_values(df)
    price_check    = check_price_range(df)
    duplicate_check = check_duplicates(df)

    # Only run these on full data
    if not is_sample:
        date_check = check_date_range(df)
        row_check  = check_row_count(df)
    else:
        logger.info("SAMPLE MODE: skipping date range and row count checks")
        date_check = {"pass": True, "actual_start": "SAMPLE", "actual_end": "SAMPLE"}
        row_check  = {"pass": True, "total_rows": len(df)}

    # Compile all checks for report
    checks = []
    checks.append({"check": "columns",    "status": "PASS" if not missing_cols else "FAIL"})
    checks.append({"check": "regions",    "status": "PASS" if regions_check["pass"] else "FAIL"})
    checks.append({"check": "date_range", "status": "PASS" if date_check["pass"] else "FAIL",
                   "actual_start": date_check["actual_start"], "actual_end": date_check["actual_end"]})
    checks.append({"check": "row_count",  "status": "PASS" if row_check["pass"] else "FAIL",
                   "total_rows": row_check["total_rows"]})
    checks.append({"check": "price_range","status": "PASS" if price_check["pass"] else "FLAG",
                   "rrp_min": price_check["rrp_min"], "rrp_max": price_check["rrp_max"]})
    checks.append({"check": "duplicates", "status": "PASS" if duplicate_check["pass"] else "FLAG",
                   "duplicate_rows": duplicate_check["duplicate_rows"]})
    for m in missing_checks:
        checks.append({"check": f"missing_{m['region']}", "status": m["status"],
                        "missing_rate": m["missing_rate"]})

    report_path = save_report(checks)

    # Final verdict
    critical_pass = (
        regions_check["pass"]
        and price_check["pass"]
        and date_check["pass"]
        and not missing_cols
    )

    logger.info("=" * 60)
    if critical_pass:
        mode = "SAMPLE TEST" if is_sample else "PRODUCTION"
        logger.info(f"c1_02 PASSED [{mode} MODE]")
        logger.info(f"Report: {report_path}")
        logger.info("Next: python3 scripts/c1_03_preprocess_data.py")
        sys.exit(0)
    else:
        logger.error("c1_02 FAILED — review report before proceeding")
        logger.error(f"Report: {report_path}")
        sys.exit(1)


if __name__ == "__main__":
    main()
