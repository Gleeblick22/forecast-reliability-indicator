"""theta_sensitivity.py (revision B7, EXPLORATORY; reviewer R2.7).
1. Stability of theta: re-select theta (validation max-F1) on day-block resamples of the validation period.
2. F1 / precision / recall across theta on test 1 and test 2.
3. Dispatch across theta (bands <0.5 x1.00, 0.5-theta x0.75, >=theta x0.25): over-forecast MWh and net revenue.
Checks: refit reproduces c2_31 test scores; theta = 0.849089 gives F1 0.476 / 0.630 and Table VIII dispatch rows.
Outputs: results/revision/b7_theta_metrics.csv, b7_theta_dispatch.csv, b7_theta_bootstrap.csv"""
import importlib.util, json, sys
import numpy as np
import pandas as pd
from xgboost import XGBClassifier
from sklearn.metrics import precision_recall_curve, f1_score, precision_score, recall_score
from config.settings import PROCESSED_DIR, TABLES_DIR

spec = importlib.util.spec_from_file_location("A", "scripts/c3_50_agents_v2.py")
A = importlib.util.module_from_spec(spec); spec.loader.exec_module(A)

KEYS, Y, SEED, DT, OVER, NBOOT = ["REGIONID", "DATETIME"], "y_v2_d300", 42, 0.5, 300.0, 1000
OLD = ["f_current_rrp", "f_rolling_mean_30min", "f_rolling_max_30min", "f_consecutive_high",
       "f_price_change_30min", "f_price_change_60min", "f_hour_of_day", "f_day_of_week", "f_is_peak_hour"]
PATH = ["rev_abs", "rev_signed", "n_runs", "n_sign_flips", "max_abs_step", "run_std", "recent_std_3h"]
FULL = OLD + ["f_decision"] + PATH
INFO = json.load(open(TABLES_DIR / "c2_31_best_params.json"))
P, THETA = INFO["params"], INFO["theta_d300"]
GRID = sorted({0.50, 0.60, 0.70, 0.75, 0.80, round(THETA, 6), 0.90, 0.95, 0.98})
OUT = TABLES_DIR.parent / "revision"; OUT.mkdir(parents=True, exist_ok=True)
rng = np.random.default_rng(SEED)

# refit the frozen model exactly as c4_03 and verify
lab = pd.read_csv(PROCESSED_DIR / "aemo_nem_label_v2.csv", parse_dates=["DATETIME"])
pf = pd.read_csv(PROCESSED_DIR / "price_features_earliest.csv", parse_dates=["DATETIME"])[KEYS + OLD]
df = lab.merge(pf, on=KEYS)
tr = df[df.partition == "train"]
fit, val = tr[tr.DATETIME < "2022-08-01"], tr[tr.DATETIME >= "2022-08-01"]
y = fit[Y]
m = XGBClassifier(**P, scale_pos_weight=(y == 0).sum() / (y == 1).sum(), random_state=SEED,
                  eval_metric="logloss", verbosity=0, n_jobs=-1).fit(fit[FULL], y)
t1 = df[df.partition == "test"].merge(
    pd.read_csv(TABLES_DIR / "c2_31_test_scores.csv", parse_dates=["DATETIME"])[KEYS + ["fri_score"]], on=KEYS)
diff = np.abs(m.predict_proba(t1[FULL])[:, 1] - t1.fri_score.values).max()
print(f"CHECK refit vs registered test-1 scores: max |diff| = {diff:.2e} (must be < 1e-5)")
if diff > 1e-5:
    sys.exit("Refit does not reproduce the registered model - STOP")
t2 = pd.read_csv(PROCESSED_DIR / "replication_2023_2025_lead30.csv", parse_dates=["DATETIME"]).merge(
    pd.read_csv(TABLES_DIR / "c4_03_scores.csv", parse_dates=["DATETIME"])[KEYS + ["fri_score"]], on=KEYS)
s_val = m.predict_proba(val[FULL])[:, 1]


def max_f1_theta(yv, s):
    pr, rc, th = precision_recall_curve(yv, s)
    f1 = 2 * pr[:-1] * rc[:-1] / np.clip(pr[:-1] + rc[:-1], 1e-12, None)
    return float(th[np.nanargmax(f1)])


theta_val = max_f1_theta(val[Y].values, s_val)
print(f"validation: {len(val):,} rows, {int(val[Y].sum())} positives; max-F1 theta = {theta_val:.6f} (registered {THETA:.6f})")

# 1. bootstrap stability of theta
days = val.DATETIME.dt.floor("D").values; ud = np.unique(days)
idx = {k: np.where(days == k)[0] for k in ud}
yv = val[Y].values
boots = []
for _ in range(NBOOT):
    pick = np.concatenate([idx[k] for k in rng.choice(ud, len(ud))])
    if yv[pick].sum() >= 2:
        boots.append(max_f1_theta(yv[pick], s_val[pick]))
boots = np.array(boots)
s2, y2 = t2.fri_score.values, t2[Y].values
f1_at = lambda th: f1_score(y2, (s2 >= th).astype(int))
bt = pd.DataFrame(dict(stat=["theta_p2.5", "theta_p25", "theta_median", "theta_p75", "theta_p97.5"],
                       theta=np.percentile(boots, [2.5, 25, 50, 75, 97.5]).round(4)))
bt["test2_F1_at_theta"] = [round(f1_at(t), 3) for t in bt.theta]
bt.to_csv(OUT / "b7_theta_bootstrap.csv", index=False)

# 2. F1 across theta
rows = []
for label, d in (("test 1", t1), ("test 2", t2)):
    yy, ss = d[Y].values, d.fri_score.values
    for th in GRID:
        p = (ss >= th).astype(int)
        rows.append(dict(test=label, theta=th, flagged=int(p.sum()), precision=round(precision_score(yy, p, zero_division=0), 3),
                         recall=round(recall_score(yy, p), 3), F1=round(f1_score(yy, p), 3)))
met = pd.DataFrame(rows); met.to_csv(OUT / "b7_theta_metrics.csv", index=False)

# 3. dispatch across theta
drows = []
for label, d in (("test 1", t1), ("test 2", t2)):
    t = d.sort_values(KEYS).reset_index(drop=True)
    t["day"] = t.DATETIME.dt.floor("D").factorize()[0]
    groups = [(g.index.values, g.day.tolist(), g.f_decision.tolist(), g.p_disp30.tolist())
              for _, g in t.groupby("REGIONID", sort=False)]
    over = ((t.f_decision - t.p_disp30) > OVER).values
    s = t.fri_score.values
    for th in GRID:
        sc = np.where(s >= th, 0.25, np.where(s >= 0.5, 0.75, 1.0))
        r = A.run_agent(t, sc, groups); disp = r.disp.values
        drows.append(dict(test=label, theta=th, over_mwh=round(float((disp * DT)[over].sum()), 1),
                          net=round(float(r.net.sum()))))
        print(f"  dispatch {label} theta={th}: done", flush=True)
dis = pd.DataFrame(drows); dis.to_csv(OUT / "b7_theta_dispatch.csv", index=False)

pd.set_option("display.width", 220)
print("\n=== B7.1 theta stability (validation day-block bootstrap, n =", len(boots), ") ===")
print(bt.to_string(index=False))
print("\n=== B7.2 F1 across theta ===")
print(met.to_string(index=False))
print("\n=== B7.3 dispatch across theta ===")
print(dis.to_string(index=False))
r = met[(met.theta == round(THETA, 6))]
print("\nCHECK F1 at registered theta (expected 0.476 / 0.630):", r[["test", "F1"]].values.tolist())
r = dis[(dis.theta == round(THETA, 6))]
print("CHECK dispatch at registered theta (expected 20.5 / 310,287 and 954.0 / 13,986,806):", r[["test", "over_mwh", "net"]].values.tolist())
