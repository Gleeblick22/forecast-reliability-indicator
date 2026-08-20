"""
c3_36_investigate_band_dispatch.py
=====================================
Investigates why mean dispatch is non-monotonic across FRI
bands (LOW < HIGH < MEDIUM), addressing Minor review item #18.
Hypothesis: HIGH-band intervals may have lower average
available SoC at dispatch time (e.g., due to clustering /
recent prior discharges), even though the HIGH dispatch
factor (1.00) exceeds MEDIUM's (0.75).
"""
import sys
import pandas as pd
from config.settings import TABLES_DIR
from config.logging_config import get_logger

logger = get_logger("c3_36_investigate_band_dispatch")

df = pd.read_csv(TABLES_DIR / "c3_02_fri_agent_results.csv", parse_dates=["DATETIME"])

for band in ["LOW", "MEDIUM", "HIGH"]:
    sub = df[df["fri_band"] == band]
    dispatched = sub[sub["dispatch_mw"] > 0]
    logger.info(f"\n=== {band} band ===")
    logger.info(f"Total intervals: {len(sub):,}")
    logger.info(f"Dispatched intervals: {len(dispatched):,}")
    logger.info(f"Mean dispatch_mw (all): {sub['dispatch_mw'].mean():.2f}")
    logger.info(f"Mean dispatch_mw (dispatched only): {dispatched['dispatch_mw'].mean():.2f}")
    if "soc" in sub.columns:
        logger.info(f"Mean SoC at dispatch: {dispatched['soc'].mean():.4f}")

sys.exit(0)
