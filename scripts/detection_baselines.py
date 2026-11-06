"""detection_baselines.py (revision B3-B5 + B8, EXPLORATORY; reviewer R2.2, R2.3, R2.4, R2.5, DA.1, Ed.2).
Test 1 and test 2, AP co-primary with day-block bootstrap CIs:
FRI; |f_decision|; logistic 17; logistic 8; additive (splines) 8; error-magnitude regressor;
quantile interval width (q90 - q10; split-conformal width ranks the same); one-sided model (B8).
New models fitted on the fitting partition only (2021-10-01 .. 2022-07-31).
Output: results/revision/b3_detection_baselines.csv"""
import json
import numpy as np
import pandas as pd
from xgboost import XGBClassifier, XGBRegressor
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler, SplineTransformer
from sklearn.impute import SimpleImputer
from sklearn.metrics import roc_auc_score, average_precision_score
from config.settings import PROCESSED_DIR, TABLES_DIR

KEYS, Y, SEED, NBOOT = ["REGIONID", "DATETIME"], "y_v2_d300", 42, 1000
OLD = ["f_current_rrp", "f_rolling_mean_30min", "f_rolling_max_30min", "f_consecutive_high",
       "f_price_change_30min", "f_price_change_60min", "f_hour_of_day", "f_day_of_week", "f_is_peak_hour"]
PATH = ["rev_abs", "rev_signed", "n_runs", "n_sign_flips", "max_abs_step", "run_std", "recent_std_3h"]
FULL = OLD + ["f_decision"] + PATH
EIGHT = ["f_decision"] + PATH
P = json.load(open(TABLES_DIR / "c2_31_best_params.json"))["params"]
OUT = TABLES_DIR.parent / "revision"; OUT.mkdir(parents=True, exist_ok=True)
rng = np.random.default_rng(SEED)

lab = pd.read_csv(PROCESSED_DIR / "aemo_nem_label_v2.csv", parse_dates=["DATETIME"])
pf = pd.read_csv(PROCESSED_DIR / "price_features_earliest.csv", parse_dates=["DATETIME"])[KEYS + OLD]
df = lab.merge(pf, on=KEYS)
fit = df[(df.partition == "train") & (df.DATETIME < "2022-08-01")].copy()
t1 = df[df.partition == "test"].merge(
    pd.read_csv(TABLES_DIR / "c2_31_test_scores.csv", parse_dates=["DATETIME"])[KEYS + ["fri_score"]], on=KEYS)
t2 = pd.read_csv(PROCESSED_DIR / "replication_2023_2025_lead30.csv", parse_dates=["DATETIME"]).merge(
    pd.read_csv(TABLES_DIR / "c4_03_scores.csv", parse_dates=["DATETIME"])[KEYS + ["fri_score"]], on=KEYS)
for name, d in (("fit", fit), ("test 1", t1), ("test 2", t2)):
    for c in FULL + [Y, "p_disp30", "f_decision"]:
        assert c in d.columns, f"{name}: missing {c}"
    d["err"] = (d.f_decision - d.p_disp30).abs()
    d["y_over"] = ((d.f_decision - d.p_disp30) > 300).astype(int)
print(f"fit {len(fit):,} rows ({fit[Y].sum():,} pos) | test 1 {len(t1):,} ({t1[Y].sum()}) | test 2 {len(t2):,} ({t2[Y].sum():,})")

y = fit[Y].values
lr = lambda: LogisticRegression(class_weight="balanced", max_iter=5000)
models = {}
models["logistic_17"] = (make_pipeline(SimpleImputer(strategy="median"), StandardScaler(), lr()).fit(fit[FULL], y), FULL, "p")
models["logistic_8"] = (make_pipeline(SimpleImputer(strategy="median"), StandardScaler(), lr()).fit(fit[EIGHT], y), EIGHT, "p")
models["additive_8"] = (make_pipeline(SimpleImputer(strategy="median"), StandardScaler(),
                                      SplineTransformer(n_knots=5, degree=3), lr()).fit(fit[EIGHT], y), EIGHT, "p")
models["error_regressor"] = (XGBRegressor(**P, random_state=SEED, verbosity=0, n_jobs=-1).fit(
    fit[FULL], np.log1p(fit.err.values)), FULL, "r")
models["quantile_width"] = (XGBRegressor(**P, objective="reg:quantileerror", quantile_alpha=np.array([0.1, 0.9]),
                                         random_state=SEED, verbosity=0, n_jobs=-1).fit(fit[FULL], fit.p_disp30.values), FULL, "w")
yo = fit.y_over.values
models["one_sided_xgb"] = (XGBClassifier(**P, scale_pos_weight=(yo == 0).sum() / max((yo == 1).sum(), 1),
                                         random_state=SEED, eval_metric="logloss", verbosity=0, n_jobs=-1).fit(fit[FULL], yo), FULL, "p")
print("models fitted", flush=True)


def score(d, m):
    mod, cols, kind = m
    if kind == "p":
        return mod.predict_proba(d[cols])[:, 1]
    if kind == "r":
        return mod.predict(d[cols])
    qq = mod.predict(d[cols]); return qq[:, 1] - qq[:, 0]


def day_boot(d, ycol, S, ref="FRI"):
    days = d.DATETIME.dt.floor("D").values; ud = np.unique(days)
    idx = {k: np.where(days == k)[0] for k in ud}
    yv = d[ycol].values
    reps = {k: [] for k in S}; dreps = {k: [] for k in S}
    for _ in range(NBOOT):
        pick = np.concatenate([idx[k] for k in rng.choice(ud, len(ud))])
        yy = yv[pick]
        if yy.sum() == 0:
            continue
        aps = {k: average_precision_score(yy, s[pick]) for k, s in S.items()}
        for k in S:
            reps[k].append(aps[k]); dreps[k].append(aps[k] - aps[ref])
    return reps, dreps


def rows_for(label, target, yv, S, reps, dreps):
    out = []
    for k, s in S.items():
        out.append(dict(test=label, target=target, model=k,
                        auc=round(roc_auc_score(yv, s), 3), ap=round(average_precision_score(yv, s), 3),
                        ap_lo=round(np.percentile(reps[k], 2.5), 3), ap_hi=round(np.percentile(reps[k], 97.5), 3),
                        dAP_vs_FRI=round(average_precision_score(yv, s) - average_precision_score(yv, S["FRI"]), 3),
                        dAP_lo=round(np.percentile(dreps[k], 2.5), 3), dAP_hi=round(np.percentile(dreps[k], 97.5), 3)))
    return out


rows = []
for label, d in (("test 1", t1), ("test 2", t2)):
    S = {"FRI": d.fri_score.values, "abs_f_decision": d.f_decision.abs().values}
    for k, m in models.items():
        if k != "one_sided_xgb":
            S[k] = score(d, m)
    reps, dreps = day_boot(d, Y, S)
    rows += rows_for(label, "two-sided (registered)", d[Y].values, S, reps, dreps)
    S1 = {"FRI": d.fri_score.values, "abs_f_decision": d.f_decision.abs().values,
          "one_sided_xgb": score(d, models["one_sided_xgb"])}
    reps, dreps = day_boot(d, "y_over", S1)
    rows += rows_for(label, "one-sided (over-forecast)", d.y_over.values, S1, reps, dreps)
    print(f"{label}: done", flush=True)

res = pd.DataFrame(rows)
res.to_csv(OUT / "b3_detection_baselines.csv", index=False)
pd.set_option("display.width", 250)
print("\n=== B3-B5, B8: detection baselines (AP with day-block 95% CI) ===")
print(res.to_string(index=False))
c = res[(res.target.str.startswith("two")) & (res.model.isin(["FRI", "abs_f_decision"]))]
print("\nCHECK (expected AP): FRI 0.355 / 0.643; |f_decision| 0.427 / 0.645")
print(c[["test", "model", "ap"]].to_string(index=False))
print("Saved:", OUT / "b3_detection_baselines.csv")
