"""
c3_07_sensitivity_analysis.py
==============================
Sensitivity analysis for Component 3.
Tests H5 and H7 at alternative dispatch
thresholds per PDD protocol.

Alternative thresholds:
  $50/MWh  (lower threshold)
  $200/MWh (higher threshold)
Primary: $100/MWh (Decision 9)

Input:  data/processed/aemo_nem_all_2021_2022_processed.csv
        data/processed/features_all.csv
        results/models/fri_model_v1_tuned.pkl
Output: results/tables/c3_07_sensitivity_results.csv

Project: forecast-reliability-indicator (FRI)
OSF:     10.17605/OSF.IO/Z89HD
"""

import sys
import pickle
import pandas as pd
import numpy as np
from datetime import datetime
from pathlib import Path

from config.settings import (
    PROCESSED_DIR,
    TABLES_DIR,
    MODELS_DIR,
    TRAIN_TEST_SPLIT,
    BATTERY_CAPACITY_MWH,
    BATTERY_POWER_MW,
    BATTERY_SOC_MIN,
    BATTERY_SOC_MAX,
    BATTERY_SOC_INITIAL,
    BATTERY_DISCHARGE_EFF,
    BATTERY_MIN_DISPATCH_MW,
    BATTERY_SOC_RESET_DAILY,
    BATTERY_SOC_RESET_VALUE,
    FRI_THRESHOLD_HIGH,
    FRI_THRESHOLD_MEDIUM,
    H5_REDUCTION_THRESHOLD,
    H7_REVENUE_THRESHOLD,
)
from config.logging_config import get_logger

logger = get_logger("c3_07_sensitivity_analysis")

PROCESSED_FILE = PROCESSED_DIR / "aemo_nem_all_2021_2022_processed.csv"
FEATURES_FILE  = PROCESSED_DIR / "features_all.csv"
MODEL_FILE     = MODELS_DIR    / "fri_model_v1_tuned.pkl"
OUTPUT_FILE    = TABLES_DIR    / "c3_07_sensitivity_results.csv"

ALTERNATIVE_THRESHOLDS = [50.0, 200.0]
INTERVAL_HOURS         = 0.5
DISPATCH_FACTORS       = {"HIGH": 1.00, "MEDIUM": 0.75, "LOW": 0.25}


def load_inputs() -> tuple:
    """Load test data features and model."""
    processed = pd.read_csv(PROCESSED_FILE, parse_dates=["DATETIME"])
    features  = pd.read_csv(FEATURES_FILE,  parse_dates=["DATETIME"])

    split_date = pd.Timestamp(TRAIN_TEST_SPLIT)
    test_proc  = processed[processed["DATETIME"] >= split_date].copy()
    test_feat  = features[features["DATETIME"]  >= split_date].copy()

    with open(MODEL_FILE, "rb") as f:
        model = pickle.load(f)

    logger.info(f"Test intervals: {len(test_proc):,}")
    return test_proc, test_feat, model


def get_fri_scores(test_feat: pd.DataFrame, model) -> pd.DataFrame:
    """Get FRI scores for test intervals."""
    feature_cols = [c for c in test_feat.columns if c.startswith("f_")]
    scores       = model.predict_proba(test_feat[feature_cols].values)[:, 1]

    fri_df = test_feat[["DATETIME", "REGIONID"]].copy()
    fri_df["fri_score"] = scores
    fri_df["fri_band"]  = np.where(
        scores >= FRI_THRESHOLD_HIGH, "HIGH",
        np.where(scores >= FRI_THRESHOLD_MEDIUM, "MEDIUM", "LOW")
    )
    fri_df["dispatch_factor"] = fri_df["fri_band"].map(DISPATCH_FACTORS)
    return fri_df


def simulate_agents(
    test_proc: pd.DataFrame,
    fri_scores: pd.DataFrame,
    threshold: float
) -> tuple:
    """Simulate baseline and FRI agents at given threshold."""
    merged = test_proc.merge(
        fri_scores[["DATETIME", "REGIONID", "fri_score",
                    "fri_band", "dispatch_factor"]],
        on=["DATETIME", "REGIONID"], how="left"
    )
    merged["dispatch_factor"] = merged["dispatch_factor"].fillna(0.75)
    merged = merged.sort_values("DATETIME").reset_index(drop=True)

    baseline_results = []
    fri_results      = []
    soc_b = BATTERY_SOC_INITIAL
    soc_f = BATTERY_SOC_INITIAL
    current_date = None

    for _, row in merged.iterrows():
        interval_date = pd.Timestamp(row["DATETIME"]).date()
        if BATTERY_SOC_RESET_DAILY and interval_date != current_date:
            soc_b        = BATTERY_SOC_RESET_VALUE
            soc_f        = BATTERY_SOC_RESET_VALUE
            current_date = interval_date

        decision_price = row.get("first_forecast", 0)
        revenue_price  = row.get("last_forecast", 0)
        regime         = row.get("regime", "normal")
        forecast_err   = row.get("forecast_error", 0)
        dispatch_fac   = row["dispatch_factor"]

        should_dispatch = decision_price >= threshold

        # Baseline agent
        if should_dispatch and soc_b > BATTERY_SOC_MIN:
            max_d_b  = min(BATTERY_POWER_MW,
                          (soc_b - BATTERY_SOC_MIN) * BATTERY_CAPACITY_MWH / INTERVAL_HOURS)
            d_mw_b   = max(BATTERY_MIN_DISPATCH_MW, max_d_b)
            soc_b   -= d_mw_b * INTERVAL_HOURS / BATTERY_CAPACITY_MWH
        else:
            d_mw_b = 0.0
        soc_b = max(BATTERY_SOC_MIN, min(BATTERY_SOC_MAX, soc_b))
        rev_b = d_mw_b * BATTERY_DISCHARGE_EFF * revenue_price * INTERVAL_HOURS
        sf_b  = (should_dispatch and regime == "extreme" and
                 abs(forecast_err) > threshold)

        # FRI agent
        if should_dispatch and soc_f > BATTERY_SOC_MIN:
            max_d_f  = min(BATTERY_POWER_MW,
                          (soc_f - BATTERY_SOC_MIN) * BATTERY_CAPACITY_MWH / INTERVAL_HOURS)
            d_mw_f   = max(BATTERY_MIN_DISPATCH_MW, max_d_f * dispatch_fac)
            soc_f   -= d_mw_f * INTERVAL_HOURS / BATTERY_CAPACITY_MWH
        else:
            d_mw_f = 0.0
        soc_f = max(BATTERY_SOC_MIN, min(BATTERY_SOC_MAX, soc_f))
        rev_f = d_mw_f * BATTERY_DISCHARGE_EFF * revenue_price * INTERVAL_HOURS
        sf_f  = (should_dispatch and regime == "extreme" and
                 abs(forecast_err) > threshold and
                 row.get("fri_band", "LOW") == "LOW")

        baseline_results.append({"revenue": rev_b, "is_silent_failure": sf_b})
        fri_results.append({"revenue": rev_f,      "is_silent_failure": sf_f})

    return pd.DataFrame(baseline_results), pd.DataFrame(fri_results)


def evaluate_threshold(
    test_proc: pd.DataFrame,
    fri_scores: pd.DataFrame,
    threshold: float
) -> dict:
    """Evaluate H5 and H7 at given threshold."""
    logger.info(f"Testing threshold: ${threshold}/MWh")

    baseline, fri = simulate_agents(test_proc, fri_scores, threshold)

    # H5 silent failure reduction
    b_sf = baseline["is_silent_failure"].sum()
    f_sf = fri["is_silent_failure"].sum()
    sf_reduction = (b_sf - f_sf) / b_sf * 100 if b_sf > 0 else 0
    passes_h5    = sf_reduction >= H5_REDUCTION_THRESHOLD * 100

    # H7 revenue improvement
    b_rev = baseline["revenue"].sum()
    f_rev = fri["revenue"].sum()
    rev_improvement = (f_rev - b_rev) / abs(b_rev) * 100 if b_rev != 0 else 0
    passes_h7       = rev_improvement >= H7_REVENUE_THRESHOLD * 100

    logger.info(
        f"  H5: baseline_sf={b_sf} fri_sf={f_sf} "
        f"reduction={sf_reduction:.1f}% {'ROBUST' if passes_h5 else 'NOT ROBUST'}"
    )
    logger.info(
        f"  H7: baseline_rev=${b_rev:,.0f} fri_rev=${f_rev:,.0f} "
        f"improvement={rev_improvement:.1f}% {'ROBUST' if passes_h7 else 'NOT ROBUST'}"
    )

    return {
        "threshold":            threshold,
        "baseline_sf":          int(b_sf),
        "fri_sf":               int(f_sf),
        "h5_reduction_pct":     round(sf_reduction, 2),
        "h5_passes":            passes_h5,
        "baseline_revenue":     round(b_rev, 2),
        "fri_revenue":          round(f_rev, 2),
        "h7_improvement_pct":   round(rev_improvement, 2),
        "h7_passes":            passes_h7,
    }


def main():
    logger.info("=" * 60)
    logger.info("c3_07_sensitivity_analysis.py started")
    logger.info(f"Timestamp: {datetime.now()}")
    logger.info(f"Alternative thresholds: {ALTERNATIVE_THRESHOLDS}")
    logger.info("=" * 60)

    test_proc, test_feat, model = load_inputs()
    fri_scores = get_fri_scores(test_feat, model)

    results = []
    for threshold in ALTERNATIVE_THRESHOLDS:
        result = evaluate_threshold(test_proc, fri_scores, threshold)
        results.append(result)

    all_h5_robust = all(r["h5_passes"] for r in results)
    all_h7_robust = all(r["h7_passes"] for r in results)

    TABLES_DIR.mkdir(parents=True, exist_ok=True)
    df = pd.DataFrame(results)
    df["all_h5_robust"] = all_h5_robust
    df["all_h7_robust"] = all_h7_robust
    df.to_csv(OUTPUT_FILE, index=False)
    logger.info(f"Saved: {OUTPUT_FILE}")

    logger.info("=" * 60)
    logger.info(f"H5 sensitivity: {'ALL ROBUST' if all_h5_robust else 'NOT ALL ROBUST'}")
    logger.info(f"H7 sensitivity: {'ALL ROBUST' if all_h7_robust else 'NOT ALL ROBUST'}")
    for r in results:
        logger.info(
            f"  ${r['threshold']}: "
            f"H5={'ROBUST' if r['h5_passes'] else 'NOT'} "
            f"H7={'ROBUST' if r['h7_passes'] else 'NOT'}"
        )
    logger.info("Next: ./run.sh scripts/c3_08_replication_check.py")
    logger.info("=" * 60)
    sys.exit(0)


if __name__ == "__main__":
    main()
