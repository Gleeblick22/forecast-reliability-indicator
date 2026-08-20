"""
c3_45_h8_nz_relabeled_harmonized.py
======================================
Phase 3: H8 NZ transfer test, corrected with a harmonized delta
(NZD 98.84, matching NEM's 8.41% genuine-label positive rate),
addressing the base-rate mismatch found when applying NEM's raw
delta=300 to NZ's differently-scaled price/forecast distribution
(same principle as the GB percentile-harmonization fix).

Input:  data/processed/nz_emi_processed.csv
        results/models/fri_model_relabeled.pkl
Output: results/tables/c3_45_h8_nz_relabeled_harmonized_results.csv
"""
import sys
import pandas as pd
import joblib
from sklearn.metrics import f1_score, roc_auc_score
from config.settings import PROCESSED_DIR, TABLES_DIR, MODELS_DIR
from config.logging_config import get_logger

logger = get_logger("c3_45_h8_nz_relabeled_harmonized")

DELTA_HARMONIZED = 98.84
NEM_THRESHOLD = 0.856818

def main():
    logger.info("=" * 60)
    logger.info("c3_45_h8_nz_relabeled_harmonized.py started")
    logger.info(f"Harmonized delta: NZD {DELTA_HARMONIZED}")
    logger.info("=" * 60)

    nz = pd.read_csv(PROCESSED_DIR / "nz_emi_processed.csv", parse_dates=["DATETIME"])
    nz["y_new"] = ((nz["first_forecast"] - nz["actual_rrp"]).abs() > DELTA_HARMONIZED).astype(int)
    logger.info(f"NZ harmonized-label positive rate: {nz['y_new'].mean()*100:.2f}%")

    nz = nz.rename(columns={"f_forecast_revision": "new_revision"})
    FEATURES_NZ = ["f_current_rrp", "new_revision", "f_rolling_mean_30min",
                   "f_rolling_max_30min", "f_consecutive_high", "f_price_change_30min",
                   "f_price_change_60min", "f_hour_of_day", "f_day_of_week", "f_is_peak_hour"]
    X_nz = nz[FEATURES_NZ]
    y_nz = nz["y_new"]

    model = joblib.load(MODELS_DIR / "fri_model_relabeled.pkl")
    proba = model.predict_proba(X_nz)[:, 1]
    pred = (proba >= NEM_THRESHOLD).astype(int)

    f1 = f1_score(y_nz, pred, zero_division=0)
    auc = roc_auc_score(y_nz, proba)

    logger.info(f"NZ (harmonized, relabeled) F1={f1:.4f}  AUC={auc:.4f}")
    logger.info(f"F1 difference from NEM reference (0.8898): {abs(0.8898-f1):.4f}")
    logger.info(f"Passes 0.15 tolerance: {abs(0.8898-f1) <= 0.15}")

    pd.DataFrame([{"context": "NZ (harmonized, relabeled)", "f1": f1, "auc": auc,
                    "delta": DELTA_HARMONIZED, "positive_rate": nz["y_new"].mean()}]).to_csv(
        TABLES_DIR / "c3_45_h8_nz_relabeled_harmonized_results.csv", index=False)
    logger.info(f"Saved: {TABLES_DIR}/c3_45_h8_nz_relabeled_harmonized_results.csv")
    logger.info("=" * 60)
    sys.exit(0)

if __name__ == "__main__":
    main()
