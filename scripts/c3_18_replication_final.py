"""
c3_18_replication_final.py  [CORRECTED]
========================================
Final replication check for all correction
block scripts. Verifies outputs match the
CANONICAL post-correction results.

CORRECTIONS APPLIED (audit, pre-manuscript):
  FIX-A: H8_SA_F1 expected target 0.7840 -> 0.5923
         (D-023 threshold correction; the 0.7840 target
         was stale and would have failed against the
         corrected confidence_intervals.csv).
  FIX-B: added explicit verification of the H6 Fisher-z
         CI bounds [0.2044, 0.3208], which the original
         c3_18 did not check (it only checked point
         estimates). This makes the "CONFIRMED" stamp
         cover the H6 interval correction too.

Scripts verified:
  c3_11 confidence intervals
  c3_12 algorithm comparison
  c3_13 SHAP analysis
  c3_14 cluster revenue
  c3_15 counterfactual value
  c3_06c 9-feature FRI GB
  c3_16 rolling retraining
  c3_17 quarterly retraining

Output: results/tables/replication_final.csv
Project: forecast-reliability-indicator (FRI)
OSF:     10.17605/OSF.IO/Z89HD
"""
import sys
import warnings
import numpy as np
import pandas as pd
import pickle
from datetime import datetime
from sklearn.metrics import f1_score, roc_auc_score
from config.settings import PROCESSED_DIR, TABLES_DIR, MODELS_DIR
from config.logging_config import get_logger

warnings.filterwarnings("ignore")
logger = get_logger("c3_18_replication_final")


def main():
    logger.info("=" * 60)
    logger.info("c3_18_replication_final.py started [CORRECTED]")
    logger.info(f"Timestamp: {datetime.now()}")
    logger.info("Verifying all correction block outputs")
    logger.info("=" * 60)

    results = []
    passed  = 0
    failed  = 0
    not_found = 0

    def check(label, actual, expected, tol=0.001):
        if isinstance(expected, bool):
            ok = bool(actual) == expected
        elif isinstance(expected, str):
            ok = str(actual) == expected
        else:
            ok = abs(float(actual) - float(expected)) <= tol
        status = "PASS" if ok else "FAIL"
        logger.info(f"  {status}: {label} = {actual}")
        return ok, status, actual

    def record(file, label, actual, expected, tol=0.001):
        ok, status, val = check(label, actual, expected, tol)
        results.append({"file":file,"check":label,
                        "status":status,"actual":val})
        return ok

    # 1. confidence_intervals.csv
    f = "confidence_intervals.csv"
    try:
        df = pd.read_csv(TABLES_DIR / f)
        h4 = df[df["metric"]=="H4_F1"]["point"].values[0]
        h5 = df[df["metric"]=="H5_sf_reduction_pct"]["point"].values[0]
        h6 = df[df["metric"]=="H6_pearson_correlation"]["point"].values[0]
        h8 = df[df["metric"]=="H8_SA_F1"]["point"].values[0]
        for lbl, val, exp in [
            ("H4_F1", h4, 0.6207),
            ("H5_reduction", h5, 61.82),
            ("H6_correlation", h6, 0.2636),
            ("H8_SA_F1", h8, 0.5923),      # FIX-A: 0.7840 -> 0.5923
        ]:
            ok = record(f, lbl, val, exp, 0.01)
            if ok: passed += 1
            else:  failed += 1

        # FIX-B: verify the H6 Fisher-z CI bounds too
        h6_row = df[df["metric"]=="H6_pearson_correlation"].iloc[0]
        for lbl, col, exp in [
            ("H6_ci_low",  "ci_low",  0.2044),
            ("H6_ci_high", "ci_high", 0.3208),
        ]:
            ok = record(f, lbl, h6_row[col], exp, 0.01)
            if ok: passed += 1
            else:  failed += 1
    except FileNotFoundError:
        not_found += 1

    # 2. h5_mcnemar_test.csv
    f = "h5_mcnemar_test.csv"
    try:
        df = pd.read_csv(TABLES_DIR / f)
        for lbl, col, exp, tol in [
            ("chi2",         "chi2",         32.0294, 0.01),
            ("significant",  "significant",  True,    0),
            ("baseline_only","baseline_only", 34,     0),
            ("fri_only",     "fri_only",     0,       0),
        ]:
            ok = record(f, lbl, df[col].iloc[0], exp, tol)
            if ok: passed += 1
            else:  failed += 1
    except FileNotFoundError:
        not_found += 1

    # 3. h7_power_analysis.csv
    f = "h7_power_analysis.csv"
    try:
        df = pd.read_csv(TABLES_DIR / f)
        for lbl, col, exp, tol in [
            ("hypothesis",       "hypothesis",       "H7", 0),
            ("n_extreme_events", "n_extreme_events",  142, 0),
        ]:
            ok = record(f, lbl, df[col].iloc[0], exp, tol)
            if ok: passed += 1
            else:  failed += 1
    except FileNotFoundError:
        not_found += 1

    # 4. algorithm_comparison.csv -- check XGBoost row
    f = "algorithm_comparison.csv"
    try:
        df  = pd.read_csv(TABLES_DIR / f)
        xgb = df[df["algorithm"]=="XGBoost"]
        ok  = record(f, "XGBoost_f1",
                     xgb["f1"].values[0], 0.6207, 0.001)
        if ok: passed += 1
        else:  failed += 1
        ok = record(f, "XGBoost_selected",
                    xgb["selected"].values[0], True, 0)
        if ok: passed += 1
        else:  failed += 1
    except FileNotFoundError:
        not_found += 1

    # 5. shap_importance.csv -- check top feature
    f = "shap_importance.csv"
    try:
        df  = pd.read_csv(TABLES_DIR / f)
        top = df.sort_values("shap_rank").iloc[0]
        ok  = record(f, "top_shap_pct",
                     top["shap_pct"], 34.94, 0.5)
        if ok: passed += 1
        else:  failed += 1
        ok = record(f, "top_feature",
                    top["feature"], "f_current_rrp", 0)
        if ok: passed += 1
        else:  failed += 1
    except FileNotFoundError:
        not_found += 1

    # 6. cluster_revenue_analysis.csv -- check total
    f = "cluster_revenue_analysis.csv"
    try:
        df    = pd.read_csv(TABLES_DIR / f)
        total = df["baseline_rev"].sum()
        ok    = record(f, "total_baseline_rev",
                       total, 11211.16, 5.0)
        if ok: passed += 1
        else:  failed += 1
        n_clusters = len(df)
        ok = record(f, "n_clusters", n_clusters, 83, 0)
        if ok: passed += 1
        else:  failed += 1
    except FileNotFoundError:
        not_found += 1

    # 7. counterfactual_value.csv -- check mean
    f = "counterfactual_value.csv"
    try:
        df   = pd.read_csv(TABLES_DIR / f)
        mean = df["counterfactual_value"].mean()
        ok   = record(f, "mean_counterfactual",
                      mean, 207.28, 10.0)
        if ok: passed += 1
        else:  failed += 1
        total = df["counterfactual_value"].sum()
        ok = record(f, "total_counterfactual",
                    total, 7047.55, 10.0)
        if ok: passed += 1
        else:  failed += 1
    except FileNotFoundError:
        not_found += 1

    # 8. c3_06c results
    f = "c3_06c_h8_frilite_results.csv"
    try:
        df = pd.read_csv(TABLES_DIR / f)
        for lbl, col, exp, tol in [
            ("nem_f1",       "nem_f1",       0.0641, 0.001),
            ("gb_f1",        "gb_f1",        0.3849, 0.001),
            ("passes_h8",    "passes_h8",    False,  0),
            ("data_leakage", "data_leakage", False,  0),
        ]:
            ok = record(f, lbl, df[col].iloc[0], exp, tol)
            if ok: passed += 1
            else:  failed += 1
    except FileNotFoundError:
        not_found += 1

    # 9. rolling_retraining_results.csv
    f = "rolling_retraining_results.csv"
    try:
        df = pd.read_csv(TABLES_DIR / f)
        ok = record(f, "first_month_f1",
                    df["f1_rolling"].iloc[0], 0.5170, 0.01)
        if ok: passed += 1
        else:  failed += 1
        mean_f1 = df["f1_rolling"].mean()
        ok = record(f, "mean_f1_rolling",
                    mean_f1, 0.7472, 0.01)
        if ok: passed += 1
        else:  failed += 1
    except FileNotFoundError:
        not_found += 1

    # 10. cluster_retraining_results.csv
    f = "cluster_retraining_results.csv"
    try:
        df = pd.read_csv(TABLES_DIR / f)
        ok = record(f, "Q1_f1",
                    df["f1"].iloc[0], 0.5179, 0.001)
        if ok: passed += 1
        else:  failed += 1
        ok = record(f, "Q4_f1",
                    df["f1"].iloc[-1], 0.6207, 0.001)
        if ok: passed += 1
        else:  failed += 1
        ok = record(f, "data_leakage",
                    df["data_leakage"].iloc[0], False, 0)
        if ok: passed += 1
        else:  failed += 1
    except FileNotFoundError:
        not_found += 1

    df = pd.DataFrame(results)
    output = TABLES_DIR / "replication_final.csv"
    df.to_csv(output, index=False)

    logger.info("=" * 60)
    logger.info("REPLICATION CHECK COMPLETE [CORRECTED]")
    logger.info(f"Checks passed:    {passed}")
    logger.info(f"Checks failed:    {failed}")
    logger.info(f"Files not found:  {not_found}")
    logger.info(f"Total checks:     {passed + failed}")
    logger.info(f"Status:           "
                f"{'CONFIRMED' if failed == 0 and not_found == 0 else 'ISSUES FOUND'}")
    logger.info(f"Saved: {output}")
    logger.info("=" * 60)
    sys.exit(0)


if __name__ == "__main__":
    main()