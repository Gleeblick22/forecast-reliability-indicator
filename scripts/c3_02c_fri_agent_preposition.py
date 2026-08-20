"""
c3_02c_fri_agent_preposition.py
================================
FRI agent with pre-positioning strategy.

Uses FRI early warning signal
to conserve SOC before extreme price clusters.

Pre-positioning logic:
  If FRI score rising (>0.5) in current interval
  AND next interval score predicted HIGH:
    Skip dispatch -- conserve SOC
  At HIGH band: dispatch full available SOC

Input:  data/processed/aemo_nem_all_2021_2022_processed.csv
        data/processed/features_all.csv
        results/models/fri_model_v1_tuned.pkl
        results/tables/c3_01_baseline_agent_results.csv
Output: results/tables/c3_02c_preposition_results.csv
Project: forecast-reliability-indicator (FRI)
OSF:     10.17605/OSF.IO/Z89HD
"""
import sys
import pickle
import warnings
import numpy as np
import pandas as pd
from datetime import datetime
from config.settings import (
    PROCESSED_DIR, TABLES_DIR, MODELS_DIR,
    TRAIN_TEST_SPLIT, DISPATCH_THRESHOLD,
    BATTERY_CAPACITY_MWH, BATTERY_POWER_MW,
    BATTERY_SOC_MIN, BATTERY_SOC_MAX,
    BATTERY_SOC_INITIAL, BATTERY_DISCHARGE_EFF,
    BATTERY_MIN_DISPATCH_MW,
    FRI_THRESHOLD_HIGH, FRI_THRESHOLD_MEDIUM,
)
from config.logging_config import get_logger

warnings.filterwarnings("ignore")
logger = get_logger("c3_02c_fri_agent_preposition")

INTERVAL_HOURS   = 0.5
PREPOSITION_SCORE = 0.50


def main():
    logger.info("=" * 60)
    logger.info("c3_02c_fri_agent_preposition.py started")
    logger.info(f"Timestamp: {datetime.now()}")
    logger.info("Strategy: pre-positioning using early warning signal")
    logger.info(f"Pre-position trigger score: {PREPOSITION_SCORE}")
    logger.info("=" * 60)

    processed = pd.read_csv(
        PROCESSED_DIR / "aemo_nem_all_2021_2022_processed.csv",
        parse_dates=["DATETIME"])
    features = pd.read_csv(
        PROCESSED_DIR / "features_all.csv",
        parse_dates=["DATETIME"])

    split_date  = pd.Timestamp(TRAIN_TEST_SPLIT)
    test_proc   = processed[processed["DATETIME"] >= split_date].copy()
    test_feat   = features[features["DATETIME"] >= split_date].copy()
    test_proc   = test_proc.sort_values(
        ["DATETIME","REGIONID"]).reset_index(drop=True)
    test_feat   = test_feat.sort_values(
        ["DATETIME","REGIONID"]).reset_index(drop=True)

    with open(MODELS_DIR / "fri_model_v1_tuned.pkl", "rb") as f:
        model = pickle.load(f)

    feat_cols = [c for c in test_feat.columns if c.startswith("f_")]
    scores    = model.predict_proba(test_feat[feat_cols].values)[:, 1]
    test_feat["fri_score"] = scores
    test_feat["fri_band"]  = np.where(
        scores >= FRI_THRESHOLD_HIGH,   "HIGH",
        np.where(scores >= FRI_THRESHOLD_MEDIUM, "MEDIUM", "LOW"))

    # look-ahead: flag intervals where NEXT interval is HIGH
    test_feat = test_feat.sort_values(
        ["REGIONID","DATETIME"]).reset_index(drop=True)
    test_feat["next_score"] = test_feat.groupby(
        "REGIONID")["fri_score"].shift(-1).fillna(0)
    test_feat["is_preposition"] = (
        (test_feat["fri_score"] >= PREPOSITION_SCORE) &
        (test_feat["next_score"] >= FRI_THRESHOLD_HIGH) &
        (test_feat["fri_band"] != "HIGH"))

    merged = test_proc.merge(
        test_feat[["DATETIME","REGIONID","fri_score",
                   "fri_band","is_preposition"]],
        on=["DATETIME","REGIONID"], how="left")
    merged["fri_score"]     = merged["fri_score"].fillna(0)
    merged["fri_band"]      = merged["fri_band"].fillna("LOW")
    merged["is_preposition"]= merged["is_preposition"].fillna(False)
    merged = merged.sort_values(
        ["DATETIME","REGIONID"]).reset_index(drop=True)

    logger.info(f"Test intervals:    {len(merged):,}")
    logger.info(f"Pre-position flags:{merged['is_preposition'].sum():,}")
    logger.info(f"HIGH band:         "
                f"{(merged['fri_band']=='HIGH').sum():,}")

    results  = []
    soc      = BATTERY_SOC_INITIAL
    cur_date = None

    for _, row in merged.iterrows():
        interval_date = pd.Timestamp(row["DATETIME"]).date()
        if interval_date != cur_date:
            soc      = BATTERY_SOC_INITIAL
            cur_date = interval_date

        decision_price  = row.get("first_forecast", 0)
        revenue_price   = row.get("last_forecast", 0)
        regime          = row.get("regime", "normal")
        forecast_error  = row.get("forecast_error", 0)
        fri_band        = row["fri_band"]
        fri_score       = row["fri_score"]
        is_preposition  = row["is_preposition"]

        if is_preposition:
            # conserve SOC -- skip dispatch
            dispatch_mw      = 0.0
            should_dispatch  = False
            revenue          = 0.0
            expected_revenue = 0.0
            revenue_error    = 0.0
        else:
            # MEDIUM or HIGH -- dispatch proportionally
            should_dispatch = decision_price >= DISPATCH_THRESHOLD
            if fri_band == "HIGH":
                dispatch_factor = 1.00
            elif fri_band == "MEDIUM":
                dispatch_factor = 0.75
            else:
                dispatch_factor = 0.25

            if should_dispatch and soc > BATTERY_SOC_MIN:
                max_dispatch = min(
                    BATTERY_POWER_MW * dispatch_factor,
                    (soc - BATTERY_SOC_MIN) *
                    BATTERY_CAPACITY_MWH / INTERVAL_HOURS)
                dispatch_mw = (max(BATTERY_MIN_DISPATCH_MW, max_dispatch)
                               if max_dispatch > BATTERY_MIN_DISPATCH_MW
                               else max_dispatch)
                soc -= (dispatch_mw * INTERVAL_HOURS) / BATTERY_CAPACITY_MWH
            else:
                dispatch_mw = 0.0

            soc = max(BATTERY_SOC_MIN, min(BATTERY_SOC_MAX, soc))
            revenue = (dispatch_mw * BATTERY_DISCHARGE_EFF *
                       revenue_price * INTERVAL_HOURS)
            expected_revenue = (dispatch_mw * BATTERY_DISCHARGE_EFF *
                                decision_price * INTERVAL_HOURS)
            revenue_error = expected_revenue - revenue

        is_silent_failure = (
            should_dispatch and
            regime == "extreme" and
            abs(forecast_error) > DISPATCH_THRESHOLD)

        results.append({
            "DATETIME":         row["DATETIME"],
            "REGIONID":         row.get("REGIONID", "NSW1"),
            "regime":           regime,
            "first_forecast":   decision_price,
            "last_forecast":    revenue_price,
            "forecast_error":   forecast_error,
            "fri_score":        fri_score,
            "fri_band":         fri_band,
            "is_preposition":   is_preposition,
            "should_dispatch":  should_dispatch,
            "dispatch_mw":      dispatch_mw,
            "soc":              round(soc, 4),
            "revenue":          round(revenue, 4),
            "expected_revenue": round(expected_revenue, 4),
            "revenue_error":    round(revenue_error, 4),
            "is_silent_failure":is_silent_failure,
            "agent_type":       "fri_preposition",
        })

    results_df = pd.DataFrame(results)
    output     = TABLES_DIR / "c3_02c_preposition_results.csv"
    results_df.to_csv(output, index=False)

    baseline = pd.read_csv(
        TABLES_DIR / "c3_01_baseline_agent_results.csv")
    b_rev    = baseline["revenue"].sum()
    f_rev    = results_df["revenue"].sum()
    imp      = (f_rev - b_rev) / b_rev * 100
    b_sf     = baseline["is_silent_failure"].sum()
    f_sf     = results_df["is_silent_failure"].sum()
    sf_red   = (b_sf - f_sf) / b_sf * 100 if b_sf > 0 else 0

    logger.info("=" * 60)
    logger.info("PRE-POSITIONING RESULTS")
    logger.info(f"Baseline revenue:    ${b_rev:,.2f}")
    logger.info(f"Preposition revenue: ${f_rev:,.2f}")
    logger.info(f"Improvement:         {imp:+.2f}%")
    logger.info(f"H7 threshold:        +15.00%")
    logger.info(f"H7 status:           "
                f"{'PASS' if imp >= 15 else 'FAIL'}")
    logger.info(f"Silent failures:     "
                f"baseline={b_sf} FRI={f_sf}")
    logger.info(f"SF reduction:        {sf_red:.2f}%")
    logger.info(f"Saved: {output}")
    logger.info("Next: ./run.sh scripts/c3_14_cluster_revenue.py")
    logger.info("=" * 60)
    sys.exit(0)


if __name__ == "__main__":
    main()
