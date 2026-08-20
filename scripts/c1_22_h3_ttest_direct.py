"""
c1_22_h3_ttest_direct.py
==========================
Direct, minimal re-verification of H3's pre-registered
independent-samples t-test (P5 vs P30 absolute error on
extreme intervals), using the existing, already-verified
regime/p5_error/p30_error columns directly -- avoiding
c1_08's more complex (and currently broken) reclassification
logic.
"""
import sys
import pandas as pd
from scipy import stats
from config.settings import PROCESSED_DIR
from config.logging_config import get_logger

logger = get_logger("c1_22_h3_ttest_direct")

df = pd.read_csv(PROCESSED_DIR / "aemo_nem_all_2021_2022_processed.csv")
extreme = df[df["regime"] == "extreme"]
paired = extreme[["p5_error", "p30_error"]].dropna()

logger.info(f"Extreme intervals: {len(extreme)}")
logger.info(f"Paired P5/P30 (non-null): {len(paired)}")

p5 = paired["p5_error"].abs()
p30 = paired["p30_error"].abs()

t_stat, p_value = stats.ttest_ind(p5, p30, equal_var=False)
logger.info(f"P5 mean: {p5.mean():.2f}  P30 mean: {p30.mean():.2f}")
logger.info(f"Welch's t-test: t={t_stat:.4f}  p={p_value:.6f}")
logger.info(f"PASSES (p<0.05): {p_value < 0.05}")

sys.exit(0)
