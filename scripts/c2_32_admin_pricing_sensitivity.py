"""
c2_32_admin_pricing_sensitivity.py  (Roadmap P2.3 / E4)
Retrains the validation-selected model (c2_31_best_params.json) with and without
the June 2022 administered-pricing / market-suspension window in the FITTING data.
Validation and test partitions are unchanged; theta re-chosen on validation each time.
WINDOW is conservative (all regions). VERIFY dates against AEMO's June 2022
market suspension report before reporting.
Output: results/tables/c2_32_admin_pricing_sensitivity.csv
"""
import sys, json
import numpy as np
import pandas as pd
from xgboost import XGBClassifier
from sklearn.metrics import (roc_auc_score, average_precision_score, f1_score,
                             precision_score, recall_score, precision_recall_curve)
from config.settings import PROCESSED_DIR, TABLES_DIR
from config.logging_config import get_logger

logger = get_logger("c2_32_admin_pricing_sensitivity")
WINDOW = (pd.Timestamp("2022-06-12 00:00"), pd.Timestamp("2022-06-25 00:00"))
KEYS = ["REGIONID", "DATETIME"]
OLD = ["f_current_rrp", "f_rolling_mean_30min", "f_rolling_max_30min", "f_consecutive_high",
       "f_price_change_30min", "f_price_change_60min", "f_hour_of_day", "f_day_of_week", "f_is_peak_hour"]
PATH = ["rev_abs", "rev_signed", "n_runs", "n_sign_flips", "max_abs_step", "run_std", "recent_std_3h"]
F = OLD + ["f_decision"] + PATH
Y = "y_v2_d300"


def theta(y, s):
    p, r, t = precision_recall_curve(y, s); f = 2*p*r/(p+r+1e-12); return float(t[np.argmax(f[:-1])])


def run(name, fit, val, test, params):
    y = fit[Y]
    m = XGBClassifier(**params, scale_pos_weight=(y == 0).sum()/(y == 1).sum(), random_state=42,
                      eval_metric="logloss", verbosity=0).fit(fit[F], y)
    sv, st = m.predict_proba(val[F])[:, 1], m.predict_proba(test[F])[:, 1]
    th = theta(val[Y], sv); pred = (st >= th).astype(int)
    return dict(spec=name, n_fit=len(fit), fit_pos=int(y.sum()), fit_prev_pct=round(y.mean()*100, 3),
                val_ap=round(average_precision_score(val[Y], sv), 4),
                test_auc=round(roc_auc_score(test[Y], st), 4), test_ap=round(average_precision_score(test[Y], st), 4),
                test_f1=round(f1_score(test[Y], pred, zero_division=0), 4),
                precision=round(precision_score(test[Y], pred, zero_division=0), 4),
                recall=round(recall_score(test[Y], pred, zero_division=0), 4), theta=round(th, 6))


def main():
    params = json.load(open(TABLES_DIR / "c2_31_best_params.json"))["params"]
    lab = pd.read_csv(PROCESSED_DIR / "aemo_nem_label_v2.csv", parse_dates=["DATETIME"])
    old = pd.read_csv(PROCESSED_DIR / "final_leakage_controlled_dataset.csv", parse_dates=["DATETIME"])[KEYS + OLD].drop_duplicates(KEYS)
    df = lab.merge(old, on=KEYS); tr = df[df.partition == "train"]
    fit, val, test = tr[tr.DATETIME < "2022-08-01"], tr[tr.DATETIME >= "2022-08-01"], df[df.partition == "test"]
    inwin = (fit.DATETIME >= WINDOW[0]) & (fit.DATETIME < WINDOW[1])
    logger.info(f"Window {WINDOW[0]} to {WINDOW[1]}: {inwin.sum():,} fit rows, {int(fit.loc[inwin, Y].sum())} positives "
                f"({fit.loc[inwin, Y].sum()/max(fit[Y].sum(),1)*100:.1f}% of all fit positives)")
    logger.info(f"\nPositives in window by region:\n{fit.loc[inwin].groupby('REGIONID')[Y].sum()}")
    res = pd.DataFrame([run("with_window (primary)", fit, val, test, params),
                        run("without_window", fit[~inwin], val, test, params)])
    res.to_csv(TABLES_DIR / "c2_32_admin_pricing_sensitivity.csv", index=False)
    with pd.option_context("display.width", 220, "display.max_columns", 20):
        logger.info(f"\n{res}")
    d = res.test_auc.iloc[1] - res.test_auc.iloc[0]
    logger.info(f"Delta test AUC (without - with): {d:+.4f}  -> Gate A rule: |delta| > 0.03 makes exclusion primary")
    sys.exit(0)


if __name__ == "__main__":
    main()
