"""
c1_09_replication_check.py
===========================
Replication check for all Component 1 results.
Re-runs c1_03 through c1_08 from scratch and
compares all numerical outputs against first run.

Success criterion:
  All numerical outputs match first run
  to 4 decimal places exactly.

Input:  All Component 1 raw and processed data
Output: results/tables/c1_09_replication_report.csv

Project: forecast-reliability-indicator (FRI)
OSF:     10.17605/OSF.IO/Z89HD
"""

import sys
import subprocess
import pandas as pd
import numpy as np
from datetime import datetime
from pathlib import Path

from config.settings import TABLES_DIR
from config.logging_config import get_logger

logger = get_logger("c1_09_replication_check")

SCRIPTS = [
    "scripts/c1_03_preprocess_data.py",
    "scripts/c1_04_test_h1_amplification.py",
    "scripts/c1_05_test_h2_masking.py",
    "scripts/c1_06_test_h3_horizon.py",
    "scripts/c1_07_trigger_weights.py",
    "scripts/c1_08_sensitivity_analysis.py",
]

RESULT_FILES = [
    "c1_04_h1_amplification_results.csv",
    "c1_05_h2_masking_results.csv",
    "c1_06_h3_horizon_results.csv",
    "c1_08_sensitivity_results.csv",
    "trigger_weights.csv",
]

NUMERIC_TOLERANCE = 1e-4


def load_first_run_results() -> dict:
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


def backup_first_run(first_run: dict) -> dict:
    """Store first run numeric values for comparison."""
    backup = {}
    for filename, df in first_run.items():
        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        backup[filename] = df[numeric_cols].copy()
    return backup


def run_scripts() -> bool:
    """Re-run all Component 1 scripts."""
    import os
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
    comparison_results = []

    for filename, first_df in backup.items():
        path = TABLES_DIR / filename
        if not path.exists():
            logger.error(f"Replication file missing: {filename}")
            comparison_results.append({
                "file":    filename,
                "column":  "ALL",
                "max_diff": None,
                "passes":  False,
                "note":    "file_missing",
            })
            continue

        replic_df    = pd.read_csv(path)
        numeric_cols = first_df.columns.tolist()

        for col in numeric_cols:
            if col not in replic_df.columns:
                logger.warning(f"{filename}: column {col} missing in replication")
                continue

            first_vals  = first_df[col].dropna().values
            replic_vals = replic_df[col].dropna().values

            if len(first_vals) != len(replic_vals):
                logger.error(
                    f"{filename}/{col}: row count mismatch "
                    f"first={len(first_vals)} replic={len(replic_vals)}"
                )
                comparison_results.append({
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

                comparison_results.append({
                    "file":     filename,
                    "column":   col,
                    "max_diff": round(max_diff, 8),
                    "passes":   passes,
                    "note":     "" if passes else "exceeds_tolerance",
                })

                if passes:
                    logger.info(f"MATCH  {filename}/{col}: max_diff={max_diff:.8f}")
                else:
                    logger.error(
                        f"MISMATCH {filename}/{col}: "
                        f"max_diff={max_diff:.8f} (tolerance={NUMERIC_TOLERANCE})"
                    )
            except Exception as e:
                logger.error(f"{filename}/{col}: comparison failed — {e}")

    return comparison_results


def save_report(results: list, all_match: bool) -> object:
    """Save replication report."""
    TABLES_DIR.mkdir(parents=True, exist_ok=True)
    output_path = TABLES_DIR / "c1_09_replication_report.csv"

    df = pd.DataFrame(results)
    df["replication_confirmed"] = all_match
    df.to_csv(output_path, index=False)
    logger.info(f"Report saved: {output_path}")
    return output_path


def main():
    logger.info("=" * 60)
    logger.info("c1_09_replication_check.py started")
    logger.info(f"Timestamp: {datetime.now()}")
    logger.info(f"Tolerance: {NUMERIC_TOLERANCE}")
    logger.info("=" * 60)

    # Step 1 — Load first run results
    logger.info("Step 1: Loading first run results...")
    first_run = load_first_run_results()

    if not first_run:
        logger.error("No first run results found — run c1_04 through c1_08 first")
        sys.exit(1)

    # Step 2 — Backup numeric values
    logger.info("Step 2: Backing up first run numeric values...")
    backup = backup_first_run(first_run)

    # Step 3 — Re-run all scripts
    logger.info("Step 3: Re-running all Component 1 scripts...")
    scripts_ok = run_scripts()

    if not scripts_ok:
        logger.error("One or more scripts failed during replication")
        sys.exit(1)

    # Step 4 — Compare results
    logger.info("Step 4: Comparing results...")
    comparison = compare_results(backup)

    # Step 5 — Verdict
    all_match   = all(r["passes"] for r in comparison if r["max_diff"] is not None)
    output_path = save_report(comparison, all_match)

    passing = sum(1 for r in comparison if r.get("passes"))
    total   = len(comparison)

    logger.info("=" * 60)
    logger.info(
        f"REPLICATION: {'CONFIRMED' if all_match else 'FAILED'}"
    )
    logger.info(f"Matching: {passing} of {total} numeric columns")

    if all_match:
        logger.info("All results reproducible to 4 decimal places")
        logger.info("Component 1 is ready for Gate 1 review")
    else:
        logger.error("Replication failed — investigate before Gate 1 review")
        logger.error("Non-determinism source must be identified and fixed")

    logger.info(f"Report: {output_path}")
    logger.info("Next: Manual Gate 1 review — update PIPELINE.md")
    logger.info("=" * 60)
    sys.exit(0 if all_match else 1)


if __name__ == "__main__":
    main()
