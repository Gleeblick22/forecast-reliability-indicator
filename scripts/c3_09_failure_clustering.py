"""
c3_09_failure_clustering.py
============================
Post-hoc exploratory analysis (EXP-035)
Analyses extreme price event clustering patterns
and FRI early warning capability.

NOT pre-registered — clearly labelled exploratory.
OSF amendment D-013 documents this addition.

Key findings:
  Extreme events cluster in multi-hour episodes
  FRI provides 1 hour advance warning all regions
  FRI score 22-78x above normal before onset

Input:  data/processed/features_all.csv
        data/processed/aemo_nem_all_2021_2022_processed.csv
        results/models/fri_model_v1_tuned.pkl
Output: results/tables/q4_failure_clustering.csv
Project: forecast-reliability-indicator (FRI)
OSF:     10.17605/OSF.IO/Z89HD
"""
import sys
import pickle
import pandas as pd
import numpy as np
from datetime import datetime
from config.settings import PROCESSED_DIR, TABLES_DIR, MODELS_DIR
from config.logging_config import get_logger

logger = get_logger("c3_09_failure_clustering")

def main():
    logger.info("=" * 60)
    logger.info("c3_09_failure_clustering.py started")
    logger.info(f"Timestamp: {datetime.now()}")
    logger.info("POST-HOC EXPLORATORY -- not pre-registered")
    logger.info("=" * 60)

    processed = pd.read_csv(
        PROCESSED_DIR / "aemo_nem_all_2021_2022_processed.csv",
        parse_dates=["DATETIME"])
    features = pd.read_csv(
        PROCESSED_DIR / "features_all.csv",
        parse_dates=["DATETIME"])

    feature_cols = [c for c in features.columns if c.startswith("f_")]

    with open(MODELS_DIR / "fri_model_v1_tuned.pkl", "rb") as f:
        model = pickle.load(f)

    features["fri_score"] = model.predict_proba(
        features[feature_cols].values)[:, 1]
    features["is_extreme"] = features["label"]

    results = []

    for region in ["NSW1", "VIC1", "QLD1", "SA1", "TAS1"]:
        reg = features[features["REGIONID"] == region].copy()
        reg = reg.sort_values("DATETIME").reset_index(drop=True)

        # Clustering
        reg["cluster_id"] = (
            reg["is_extreme"] != reg["is_extreme"].shift()
        ).cumsum()
        extreme_clusters = reg[reg["is_extreme"] == 1].groupby(
            "cluster_id").size()

        # Early warning
        reg["prev_extreme"] = reg["is_extreme"].shift(1).fillna(0)
        onsets = reg[(reg["is_extreme"] == 1) & (reg["prev_extreme"] == 0)]

        pre1 = []
        pre2 = []
        for idx in onsets.index:
            if idx >= 1:
                pre1.append(reg.loc[idx-1, "fri_score"])
            if idx >= 2:
                pre2.append(reg.loc[idx-2, "fri_score"])

        normal_score = reg[reg["is_extreme"] == 0]["fri_score"].mean()
        onset_score  = reg.loc[onsets.index, "fri_score"].mean()
        pre1_mean    = float(np.mean(pre1)) if pre1 else 0
        pre2_mean    = float(np.mean(pre2)) if pre2 else 0

        results.append({
            "region":              region,
            "total_extreme":       int(reg["is_extreme"].sum()),
            "n_clusters":          len(extreme_clusters),
            "avg_cluster_length":  round(float(extreme_clusters.mean()), 2),
            "max_cluster_length":  int(extreme_clusters.max()),
            "single_interval":     int((extreme_clusters == 1).sum()),
            "multi_interval":      int((extreme_clusters > 1).sum()),
            "normal_fri_score":    round(normal_score, 4),
            "pre2_fri_score":      round(pre2_mean, 4),
            "pre1_fri_score":      round(pre1_mean, 4),
            "onset_fri_score":     round(float(onset_score), 4),
            "pre2_ratio":          round(pre2_mean/normal_score, 1)
                                   if normal_score > 0 else 0,
            "pre1_ratio":          round(pre1_mean/normal_score, 1)
                                   if normal_score > 0 else 0,
            "early_warning":       pre1_mean > normal_score * 1.5,
        })

        logger.info(f"{region}: clusters={len(extreme_clusters)} "
                    f"avg={extreme_clusters.mean():.1f} "
                    f"pre1={pre1_mean:.4f} "
                    f"({pre1_mean/normal_score:.1f}x normal)")

    df = pd.DataFrame(results)
    output = TABLES_DIR / "q4_failure_clustering.csv"
    df.to_csv(output, index=False)

    logger.info("=" * 60)
    logger.info("EXPLORATORY RESULTS")
    logger.info(f"All regions show early warning: "
                f"{df['early_warning'].all()}")
    logger.info(f"Avg cluster length range: "
                f"{df['avg_cluster_length'].min():.1f} to "
                f"{df['avg_cluster_length'].max():.1f} intervals")
    logger.info(f"Pre2 ratio range: "
                f"{df['pre2_ratio'].min():.1f}x to "
                f"{df['pre2_ratio'].max():.1f}x normal")
    logger.info(f"Saved: {output}")
    logger.info("=" * 60)
    sys.exit(0)

if __name__ == "__main__":
    main()
