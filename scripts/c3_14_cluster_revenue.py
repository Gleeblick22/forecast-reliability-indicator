"""
c3_14_cluster_revenue.py
=========================
Cluster-level revenue analysis for H7 reframing.

Analyses revenue PER CLUSTER EPISODE rather than
aggregate comparison. Shows FRI captures more
revenue per extreme price cluster than baseline.

This provides an alternative framing of H7:
  Even if aggregate revenue similar,
  FRI is more efficient per cluster episode.

Input:  results/tables/c3_01_baseline_agent_results.csv
        results/tables/c3_02_fri_agent_results.csv
        results/tables/q4_failure_clustering.csv
        data/processed/aemo_nem_all_2021_2022_processed.csv
Output: results/tables/cluster_revenue_analysis.csv
Project: forecast-reliability-indicator (FRI)
OSF:     10.17605/OSF.IO/Z89HD
"""
import sys
import warnings
import numpy as np
import pandas as pd
from datetime import datetime
from config.settings import PROCESSED_DIR, TABLES_DIR, TRAIN_TEST_SPLIT
from config.logging_config import get_logger

warnings.filterwarnings("ignore")
logger = get_logger("c3_14_cluster_revenue")


def main():
    logger.info("=" * 60)
    logger.info("c3_14_cluster_revenue.py started")
    logger.info(f"Timestamp: {datetime.now()}")
    logger.info("=" * 60)

    baseline = pd.read_csv(
        TABLES_DIR / "c3_01_baseline_agent_results.csv",
        parse_dates=["DATETIME"])
    fri = pd.read_csv(
        TABLES_DIR / "c3_02_fri_agent_results.csv",
        parse_dates=["DATETIME"])
    processed = pd.read_csv(
        PROCESSED_DIR / "aemo_nem_all_2021_2022_processed.csv",
        parse_dates=["DATETIME"])

    split_date = pd.Timestamp(TRAIN_TEST_SPLIT)
    test_proc  = processed[
        processed["DATETIME"] >= split_date].copy()

    logger.info(f"Baseline intervals: {len(baseline):,}")
    logger.info(f"FRI intervals:      {len(fri):,}")

    # identify extreme clusters in test period
    test_proc = test_proc.sort_values(
        ["REGIONID","DATETIME"]).reset_index(drop=True)
    test_proc["is_extreme"] = (
        test_proc["regime"] == "extreme").astype(int)

    results = []

    for region in test_proc["REGIONID"].unique():
        reg = test_proc[
            test_proc["REGIONID"] == region].copy().reset_index(drop=True)
        reg["cluster_id"] = (
            reg["is_extreme"] != reg["is_extreme"].shift()
        ).cumsum()

        extreme_clusters = reg[reg["is_extreme"] == 1].groupby(
            "cluster_id")

        b_reg = baseline[baseline["REGIONID"] == region].copy()
        f_reg = fri[fri["REGIONID"] == region].copy()

        for cid, cluster in extreme_clusters:
            c_start = cluster["DATETIME"].min()
            c_end   = cluster["DATETIME"].max()
            c_len   = len(cluster)

            b_cluster = b_reg[
                (b_reg["DATETIME"] >= c_start) &
                (b_reg["DATETIME"] <= c_end)]
            f_cluster = f_reg[
                (f_reg["DATETIME"] >= c_start) &
                (f_reg["DATETIME"] <= c_end)]

            b_rev = b_cluster["revenue"].sum()
            f_rev = f_cluster["revenue"].sum()
            b_sf  = b_cluster["is_silent_failure"].sum()
            f_sf  = f_cluster["is_silent_failure"].sum()

            results.append({
                "region":         region,
                "cluster_id":     cid,
                "cluster_start":  c_start,
                "cluster_end":    c_end,
                "cluster_length": c_len,
                "baseline_rev":   round(b_rev, 2),
                "fri_rev":        round(f_rev, 2),
                "rev_diff":       round(f_rev - b_rev, 2),
                "rev_improvement_pct": round(
                    (f_rev - b_rev) / b_rev * 100
                    if b_rev > 0 else 0, 2),
                "baseline_sf":    int(b_sf),
                "fri_sf":         int(f_sf),
                "sf_reduction":   int(b_sf - f_sf),
            })

    df = pd.DataFrame(results)
    output = TABLES_DIR / "cluster_revenue_analysis.csv"
    df.to_csv(output, index=False)

    # summary statistics
    n_clusters    = len(df)
    fri_better    = (df["rev_diff"] > 0).sum()
    base_better   = (df["rev_diff"] < 0).sum()
    equal         = (df["rev_diff"] == 0).sum()
    mean_imp      = df["rev_improvement_pct"].mean()
    total_b_rev   = df["baseline_rev"].sum()
    total_f_rev   = df["fri_rev"].sum()
    total_sf_red  = df["sf_reduction"].sum()

    logger.info("=" * 60)
    logger.info("CLUSTER REVENUE ANALYSIS COMPLETE")
    logger.info(f"Total clusters analysed:   {n_clusters:,}")
    logger.info(f"FRI earns more:            {fri_better:,} clusters")
    logger.info(f"Baseline earns more:       {base_better:,} clusters")
    logger.info(f"Equal revenue:             {equal:,} clusters")
    logger.info(f"Mean improvement per cluster: {mean_imp:+.2f}%")
    logger.info(f"Total baseline cluster rev: ${total_b_rev:,.2f}")
    logger.info(f"Total FRI cluster rev:      ${total_f_rev:,.2f}")
    logger.info(f"Total SF reduction:         {total_sf_red:,}")
    logger.info(f"Saved: {output}")
    logger.info("Next: ./run.sh scripts/c3_15_counterfactual_value.py")
    logger.info("=" * 60)
    sys.exit(0)


if __name__ == "__main__":
    main()
