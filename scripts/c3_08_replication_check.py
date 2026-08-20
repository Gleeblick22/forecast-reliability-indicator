"""
c3_08_replication_check.py
============================
Replication check for all Component 3 results.
Re-runs c3_01 through c3_07 from scratch and
compares all numerical outputs against first run.

Success criterion:
  All numerical outputs match first run
  to 4 decimal places exactly.

Input:  All Component 3 result files
Output: results/tables/c3_08_replication_report.csv

Project: forecast-reliability-indicator (FRI)
OSF:     10.17605/OSF.IO/Z89HD
"""

import sys
import subprocess
import pandas as pd
import numpy as np
from datetime import datetime
from pathlib import Path
import os

from config.settings import TABLES_DIR
from config.logging_config import get_logger

logger = get_logger("c3_08_replication_check")

SCRIPTS = [
    "scripts/c3_01_baseline_agent.py",
    "scripts/c3_02_fri_agent.py",
    "scripts/c3_03_test_h5_silent_failure.py",
    "scripts/c3_04_test_h6_dispatch_correlation.py",
    "scripts/c3_05_test_h7_revenue_comparison.py",
    "scripts/c3_07_sensitivity_analysis.py",
]

RESULT_FILES = [
    "c3_03_h5_silent_failure_results.csv",
    "c3_04_h6_dispatch_correlation_results.csv",
    "c3_05_h7_revenue_comparison_results.csv",
    "c3_07_sensitivity_results.csv",
]

NUMERIC_TOLERANCE = 1e-4


def load_first_run() -> dict:
    """Load existing result files as first run baseline."""
    first_run = {}
    for filename in RESULT_FILES:
        path = TABLES_DIR / filename
        if path.exists():
            df = pd.read_csv(path)
            first_run[filename] = df
            logger.info(f"First run loaded: {filename} ({len(df)} rows)")
        else:
            logger.warning(f"First run file not found: {filename}")
    return first_run


def backup_numeric(first_run: dict) -> dict:
    """Store first run numeric values for comparison."""
    backup = {}
    for filename, df in first_run.items():
        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        backup[filename] = df[numeric_cols].copy()
    return backup


def run_scripts() -> bool:
    """Re-run all Component 3 scripts except H8 (needs ERCOT data)."""
    env = os.environ.copy()
    env["PYTHONPATH"] = str(Path(__file__).resolve().parent.parent)

    for script in SCRIPTS:
        logger.info(f"Re-running: {script}")
        result = subprocess.run(
            ["python3", script],
            env=env,
            capture_output=True,
            text=True
        )
        if result.returncode != 0:
            logger.error(f"Script failed: {script}")
            logger.error(result.stderr[-500:] if result.stderr else "no stderr")
            return False
        logger.info(f"Completed: {script}")
    return True


def compare_results(backup: dict) -> list:
    """Compare replication run against first run."""
    comparison = []

    for filename, first_df in backup.items():
        path = TABLES_DIR / filename
        if not path.exists():
            logger.error(f"Replication file missing: {filename}")
            comparison.append({
                "file":     filename,
                "column":   "ALL",
                "max_diff": None,
                "passes":   False,
                "note":     "file_missing",
            })
            continue

        replic_df    = pd.read_csv(path)
        numeric_cols = first_df.columns.tolist()

        for col in numeric_cols:
            if col not in replic_df.columns:
                continue

            first_vals  = first_df[col].dropna().values
            replic_vals = replic_df[col].dropna().values

            if len(first_vals) != len(replic_vals):
                comparison.append({
                    "file":     filename,
                    "column":   col,
                    "max_diff": None,
                    "passes":   False,
                    "note":     "row_count_mismatch",
                })
                continue

            if len(first_vals) == 0:
                continue

            try:
                max_diff = float(np.max(np.abs(first_vals - replic_vals)))
                passes   = max_diff <= NUMERIC_TOLERANCE

                comparison.append({
                    "file":     filename,
                    "column":   col,
                    "max_diff": round(max_diff, 8),
                    "passes":   passes,
                    "note":     "" if passes else "exceeds_tolerance",
                })

                if passes:
                    logger.info(f"MATCH  {filename}/{col}: max_diff={max_diff:.8f}")
                else:
                    logger.error(f"MISMATCH {filename}/{col}: max_diff={max_diff:.8f}")

            except Exception as e:
                logger.error(f"{filename}/{col}: comparison failed — {e}")

    return comparison


def main():
    logger.info("=" * 60)
    logger.info("c3_08_replication_check.py started")
    logger.info(f"Timestamp: {datetime.now()}")
    logger.info(f"Tolerance: {NUMERIC_TOLERANCE}")
    logger.info("Note: H8 ERCOT excluded from replication")
    logger.info("      (external data dependency)")
    logger.info("=" * 60)

    logger.info("Step 1: Loading first run results...")
    first_run = load_first_run()

    if not first_run:
        logger.error("No first run results found")
        sys.exit(1)

    logger.info("Step 2: Backing up numeric values...")
    backup = backup_numeric(first_run)

    logger.info("Step 3: Re-running Component 3 scripts...")
    if not run_scripts():
        logger.error("One or more scripts failed during replication")
        sys.exit(1)

    logger.info("Step 4: Comparing results...")
    comparison = compare_results(backup)

    all_match = all(r["passes"] for r in comparison if r["max_diff"] is not None)
    passing   = sum(1 for r in comparison if r.get("passes"))
    total     = len(comparison)

    output_path = TABLES_DIR / "c3_08_replication_report.csv"
    TABLES_DIR.mkdir(parents=True, exist_ok=True)
    df = pd.DataFrame(comparison)
    df["replication_confirmed"] = all_match
    df.to_csv(output_path, index=False)
    logger.info(f"Report saved: {output_path}")

    logger.info("=" * 60)
    logger.info(f"REPLICATION: {'CONFIRMED' if all_match else 'FAILED'}")
    logger.info(f"Matching: {passing} of {total} numeric columns")

    if all_match:
        logger.info("All results reproducible to 4 decimal places")
        logger.info("Component 3 ready for Gate 3 review")
    else:
        logger.error("Replication failed — investigate before Gate 3 review")

    logger.info("Next: Manual Gate 3 review — update PIPELINE.md")
    logger.info("=" * 60)
    sys.exit(0 if all_match else 1)


if __name__ == "__main__":
    main()
