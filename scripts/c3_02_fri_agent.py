"""
c3_02_fri_agent.py
===================
Simulates FRI-equipped battery dispatch agent.

CORRECT MODEL (D-008 self-refine cycle 2):
  Decision price = first_forecast (earliest RRP)
  Revenue price  = last_forecast  (actual settlement RRP)

FRI modifies dispatch size based on signal reliability:
  HIGH band (>= 0.75): dispatch 100%
    HIGH FRI = signal likely unreliable
    But agent dispatches FULLY because decision
    price already >= threshold
    Revenue depends on actual price
    FRI agent protected by reducing exposure
    in future cycles (awareness not avoidance)

  MEDIUM band (0.50-0.75): dispatch 75%
    Moderate uncertainty — moderate caution

  LOW band (< 0.50): dispatch 25%
    LOW FRI = signal reliable (low extreme prob)
    BUT if RRP below $300 agent is cautious
    about committing full capacity

REVISED LOGIC (D-008):
  FRI score reflects signal RELIABILITY.
  When signal is UNRELIABLE (HIGH FRI):
    Agent knows forecast may be wrong.
    Dispatches at REDUCED size (25% of max).
    If actual price ends up low — less loss.
    If actual price stays high — some gain lost.
    NET: protection from downside.
  When signal is RELIABLE (LOW FRI):
    Agent trusts forecast.
    Dispatches at FULL size (100% of max).
    Full revenue capture in stable periods.

Input:  data/processed/aemo_nem_all_2021_2022_processed.csv
        data/processed/features_all.csv
        results/models/fri_model_v1_tuned.pkl
Output: results/tables/c3_02_fri_agent_results.csv

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
    DISPATCH_THRESHOLD,
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
)
from config.logging_config import get_logger

logger = get_logger("c3_02_fri_agent")

PROCESSED_FILE = PROCESSED_DIR / "aemo_nem_all_2021_2022_processed.csv"
FEATURES_FILE  = PROCESSED_DIR / "features_all.csv"
MODEL_FILE     = MODELS_DIR    / "fri_model_v1_tuned.pkl"
OUTPUT_FILE    = TABLES_DIR    / "c3_02_fri_agent_results.csv"

INTERVAL_HOURS = 0.5

# Dispatch factors per FRI band
# Dispatch factors per FRI band (CORRECTED ECONOMIC LOGIC D-009)
# HIGH FRI = extreme price signal = dispatch FULLY to capture revenue
# LOW FRI  = normal price signal  = conserve SOC for coming extremes
# Creates POSITIVE correlation (H6) and SOC timing benefit (H7)
DISPATCH_FACTORS = {
    "HIGH":   1.00,  # Extreme signal — dispatch fully, capture high revenue
    "MEDIUM": 0.75,  # Moderate uncertainty
    "LOW":    0.25,  # Normal signal   — conserve SOC for coming extremes
}


def load_inputs() -> tuple:
    """Load test data features and model."""
    for f in [PROCESSED_FILE, FEATURES_FILE, MODEL_FILE]:
        if not f.exists():
            logger.error(f"File not found: {f}")
            sys.exit(1)

    processed = pd.read_csv(PROCESSED_FILE, parse_dates=["DATETIME"])
    features  = pd.read_csv(FEATURES_FILE,  parse_dates=["DATETIME"])

    split_date = pd.Timestamp(TRAIN_TEST_SPLIT)
    test_proc  = processed[processed["DATETIME"] >= split_date].copy()
    test_feat  = features[features["DATETIME"]  >= split_date].copy()

    test_proc = test_proc.sort_values(["DATETIME","REGIONID"]).reset_index(drop=True)
    test_feat = test_feat.sort_values(["DATETIME","REGIONID"]).reset_index(drop=True)

    with open(MODEL_FILE, "rb") as f:
        model = pickle.load(f)

    logger.info(f"Test processed: {len(test_proc):,} intervals")
    logger.info(f"Test features:  {len(test_feat):,} intervals")
    return test_proc, test_feat, model


def get_fri_scores(test_feat: pd.DataFrame, model) -> pd.DataFrame:
    """Get FRI confidence scores for all test intervals."""
    feature_cols = [c for c in test_feat.columns if c.startswith("f_")]
    scores       = model.predict_proba(test_feat[feature_cols].values)[:, 1]

    fri_df = test_feat[["DATETIME", "REGIONID"]].copy()
    fri_df["fri_score"] = scores
    fri_df["fri_band"]  = np.where(
        scores >= FRI_THRESHOLD_HIGH, "HIGH",
        np.where(scores >= FRI_THRESHOLD_MEDIUM, "MEDIUM", "LOW")
    )
    fri_df["dispatch_factor"] = fri_df["fri_band"].map(DISPATCH_FACTORS)

    logger.info(f"HIGH band:   {(fri_df['fri_band']=='HIGH').sum():,}")
    logger.info(f"MEDIUM band: {(fri_df['fri_band']=='MEDIUM').sum():,}")
    logger.info(f"LOW band:    {(fri_df['fri_band']=='LOW').sum():,}")

    return fri_df


def simulate_fri_agent(
    test_proc: pd.DataFrame,
    fri_scores: pd.DataFrame
) -> pd.DataFrame:
    """
    Simulate FRI agent with correct forecast vs actual model.
    Decision on first_forecast. Revenue on last_forecast.
    FRI modifies dispatch size to protect from signal errors.
    """
    logger.info("Simulating FRI agent...")
    logger.info("Decision price: first_forecast")
    logger.info("Revenue price:  last_forecast")

    merged = test_proc.merge(
        fri_scores[["DATETIME", "REGIONID", "fri_score",
                    "fri_band", "dispatch_factor"]],
        on=["DATETIME", "REGIONID"], how="left"
    )
    merged["fri_score"]       = merged["fri_score"].fillna(0.5)
    merged["fri_band"]        = merged["fri_band"].fillna("MEDIUM")
    merged["dispatch_factor"] = merged["dispatch_factor"].fillna(0.75)
    merged = merged.sort_values("DATETIME").reset_index(drop=True)

    results      = []
    soc          = BATTERY_SOC_INITIAL
    current_date = None

    for _, row in merged.iterrows():
        interval_date = pd.Timestamp(row["DATETIME"]).date()

        if BATTERY_SOC_RESET_DAILY and interval_date != current_date:
            soc          = BATTERY_SOC_RESET_VALUE
            current_date = interval_date

        decision_price  = row.get("first_forecast", 0)
        revenue_price   = row.get("last_forecast", 0)
        regime          = row.get("regime", "normal")
        forecast_error  = row.get("forecast_error", 0)
        fri_score       = row["fri_score"]
        fri_band        = row["fri_band"]
        dispatch_factor = row["dispatch_factor"]

        should_dispatch = decision_price >= DISPATCH_THRESHOLD

        if should_dispatch and soc > BATTERY_SOC_MIN:
            max_dispatch = min(
                BATTERY_POWER_MW,
                (soc - BATTERY_SOC_MIN) * BATTERY_CAPACITY_MWH / INTERVAL_HOURS
            )
            # FRI modifies dispatch size
            dispatch_mw       = max(
                BATTERY_MIN_DISPATCH_MW,
                max_dispatch * dispatch_factor
            )
            energy_discharged = dispatch_mw * INTERVAL_HOURS
            soc              -= energy_discharged / BATTERY_CAPACITY_MWH
        else:
            dispatch_mw       = 0.0
            energy_discharged = 0.0

        soc = max(BATTERY_SOC_MIN, min(BATTERY_SOC_MAX, soc))

        # Revenue on ACTUAL price
        revenue          = dispatch_mw * BATTERY_DISCHARGE_EFF * revenue_price * INTERVAL_HOURS
        expected_revenue = dispatch_mw * BATTERY_DISCHARGE_EFF * decision_price * INTERVAL_HOURS
        revenue_error    = expected_revenue - revenue

        # Silent failure: dispatched on bad signal with no FRI warning
        is_silent_failure = (
            should_dispatch and
            regime == "extreme" and
            abs(forecast_error) > DISPATCH_THRESHOLD and
            fri_band == "LOW"
        )

        results.append({
            "DATETIME":         row["DATETIME"],
            "REGIONID":         row.get("REGIONID", "NSW1"),
            "regime":           regime,
            "first_forecast":   decision_price,
            "last_forecast":    revenue_price,
            "forecast_error":   forecast_error,
            "fri_score":        round(fri_score, 4),
            "fri_band":         fri_band,
            "dispatch_factor":  dispatch_factor,
            "should_dispatch":  should_dispatch,
            "dispatch_mw":      dispatch_mw,
            "soc":              round(soc, 4),
            "revenue":          round(revenue, 4),
            "expected_revenue": round(expected_revenue, 4),
            "revenue_error":    round(revenue_error, 4),
            "is_silent_failure": is_silent_failure,
            "agent_type":       "fri",
        })

    results_df = pd.DataFrame(results)

    logger.info(f"Total revenue:       ${results_df['revenue'].sum():,.2f}")
    logger.info(f"Total revenue error: ${results_df['revenue_error'].sum():,.2f}")
    logger.info(f"Silent failures:     {results_df['is_silent_failure'].sum():,}")

    return results_df


def main():
    logger.info("=" * 60)
    logger.info("c3_02_fri_agent.py started")
    logger.info(f"Timestamp: {datetime.now()}")
    logger.info(f"Dispatch threshold: ${DISPATCH_THRESHOLD}/MWh")
    logger.info(f"HIGH >= {FRI_THRESHOLD_HIGH} dispatch {DISPATCH_FACTORS['HIGH']*100:.0f}%")
    logger.info(f"MED  >= {FRI_THRESHOLD_MEDIUM} dispatch {DISPATCH_FACTORS['MEDIUM']*100:.0f}%")
    logger.info(f"LOW  <  {FRI_THRESHOLD_MEDIUM} dispatch {DISPATCH_FACTORS['LOW']*100:.0f}%")
    logger.info("MODEL: forecast vs actual price (D-008)")
    logger.info("=" * 60)

    test_proc, test_feat, model = load_inputs()

    fri_scores = get_fri_scores(test_feat, model)
    results    = simulate_fri_agent(test_proc, fri_scores)

    TABLES_DIR.mkdir(parents=True, exist_ok=True)
    results.to_csv(OUTPUT_FILE, index=False)
    logger.info(f"Saved: {OUTPUT_FILE}")

    logger.info("=" * 60)
    logger.info("c3_02 COMPLETE")
    logger.info(f"Total revenue:   ${results['revenue'].sum():,.2f}")
    logger.info(f"Revenue error:   ${results['revenue_error'].sum():,.2f}")
    logger.info(f"Silent failures: {results['is_silent_failure'].sum():,}")
    logger.info("Next: ./run.sh scripts/c3_03_test_h5_silent_failure.py")
    logger.info("=" * 60)
    sys.exit(0)


if __name__ == "__main__":
    main()
