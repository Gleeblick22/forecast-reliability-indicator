"""
c1_21_check_wilcoxon_ties.py
==============================
Checks whether the small Wilcoxon W statistics for NSW1/VIC1
(W=1.0, W=3.0) are explained by automatic tie-removal (zero-
difference pairs dropped by scipy before computing W), rather
than a pipeline bug, per Critical review item #7.
"""
import sys
import pandas as pd
import numpy as np
from scipy import stats
from config.settings import PROCESSED_DIR
from config.logging_config import get_logger

logger = get_logger("c1_21_check_wilcoxon_ties")

df = pd.read_csv(PROCESSED_DIR / "aemo_nem_all_2021_2022_processed.csv")

for region in ["NSW1", "VIC1", "QLD1", "SA1", "TAS1"]:
    sub = df[(df["REGIONID"] == region) & (df["regime"] == "extreme")]
    if "p5_error" not in sub.columns or "p30_error" not in sub.columns:
        logger.info(f"{region}: p5_error/p30_error columns not found, skipping")
        continue
    paired = sub[["p5_error", "p30_error"]].dropna()
    diffs = paired["p5_error"].abs() - paired["p30_error"].abs()
    n_total = len(diffs)
    n_zero = (diffs == 0).sum()
    n_nonzero = n_total - n_zero
    logger.info(f"{region}: total pairs={n_total}, exact ties (zero diff)={n_zero} "
                f"({100*n_zero/n_total:.1f}%), non-tied pairs={n_nonzero}")

sys.exit(0)
