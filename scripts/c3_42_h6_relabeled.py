"""
c3_42_h6_relabeled.py
========================
Phase 3: recomputes H6 (dispatch correlation) using the
relabeled classifier's scores (c2_18) and the P5+FRI relabeled
agent's dispatch decisions (c3_39).

Input:  results/tables/c3_39_p5_fri_relabeled_results.csv
        results/tables/c2_18_relabeled_full_scores.csv
Output: results/tables/c3_42_h6_relabeled_results.csv
"""
import sys
import pandas as pd
import numpy as np
from scipy import stats
from config.settings import TABLES_DIR
from config.logging_config import get_logger

logger = get_logger("c3_42_h6_relabeled")

def main():
    logger.info("=" * 60)
    logger.info("c3_42_h6_relabeled.py started")
    logger.info("=" * 60)

    agent = pd.read_csv(TABLES_DIR / "c3_39_p5_fri_relabeled_results.csv", parse_dates=["DATETIME"])
    scores = pd.read_csv(TABLES_DIR / "c2_18_relabeled_full_scores.csv", parse_dates=["DATETIME"])

    df = agent.merge(scores[["DATETIME", "REGIONID", "fri_score"]],
                      on=["DATETIME", "REGIONID"], how="left")
    df = df.dropna(subset=["fri_score"])

    dispatched = df[df["dispatch_mw"] > 0]
    logger.info(f"Dispatched intervals: {len(dispatched):,}")

    r, p = stats.pearsonr(dispatched["fri_score"], dispatched["dispatch_mw"])

    # Fisher z-transformed CI
    n = len(dispatched)
    z = np.arctanh(r)
    se = 1 / np.sqrt(n - 3)
    ci_low = np.tanh(z - 1.96 * se)
    ci_high = np.tanh(z + 1.96 * se)

    logger.info(f"Pearson r = {r:.4f}, p = {p:.6f}")
    logger.info(f"95% CI [{ci_low:.4f}, {ci_high:.4f}]")
    logger.info(f"r-squared: {r**2:.4f}")

    # Band-level mean dispatch, for monotonicity check
    band_means = dispatched.groupby("fri_band")["dispatch_mw"].agg(["mean", "count"])
    logger.info(f"\nBand-level mean dispatch:\n{band_means}")

    pd.DataFrame([{"r": r, "p_value": p, "ci_low": ci_low, "ci_high": ci_high,
                    "n_dispatched": n}]).to_csv(
        TABLES_DIR / "c3_42_h6_relabeled_results.csv", index=False)
    logger.info(f"\nSaved: {TABLES_DIR}/c3_42_h6_relabeled_results.csv")
    logger.info("=" * 60)
    sys.exit(0)

if __name__ == "__main__":
    main()
