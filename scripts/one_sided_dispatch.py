"""one_sided_dispatch.py (revision B2b, EXPLORATORY; reviewer R2.5, DA end note).
Does a score trained on the one-sided label (over-forecast > AUD 300/MWh only) reduce exposure further in dispatch?
One-sided XGBoost: same 17 features and hyperparameters as FRI, fitted on the fitting partition only.
  one_sided_3band   : own theta (validation max-F1, as FRI); bands <0.5 x1.00, 0.5-theta x0.75, >=theta x0.25
  one_sided_matched : same band counts as FRI, assigned by highest one-sided score (equal derating budget)
Checks: baseline and FRI rows must equal Table VIII. Output: results/revision/b2b_one_sided_dispatch.csv"""
import importlib.util, json
import numpy as np
import pandas as pd
from xgboost import XGBClassifier
from sklearn.metrics import precision_recall_curve
from config.settings import PROCESSED_DIR, TABLES_DIR

spec = importlib.util.spec_from_file_location("A", "scripts/c3_50_agents_v2.py")
A = importlib.util.module_from_spec(spec); spec.loader.exec_module(A)

KEYS, SEED, DT, OVER = ["REGIONID", "DATETIME"], 42, 0.5, 300.0
OLD = ["f_current_rrp", "f_rolling_mean_30min", "f_rolling_max_30min", "f_consecutive_high",
       "f_price_change_30min", "f_price_change_60min", "f_hour_of_day", "f_day_of_week", "f_is_peak_hour"]
PATH = ["rev_abs", "rev_signed", "n_runs", "n_sign_flips", "max_abs_step", "run_std", "recent_std_3h"]
FULL = OLD + ["f_decision"] + PATH
INFO = json.load(open(TABLES_DIR / "c2_31_best_params.json"))
P, THETA = INFO["params"], INFO["theta_d300"]
OUT = TABLES_DIR.parent / "revision"; OUT.mkdir(parents=True, exist_ok=True)
TABLE_VIII = {"test 1": {"baseline": (65.0, 307230), "fri_3band": (20.5, 310287)},
              "test 2": {"baseline": (1800.0, 14027569), "fri_3band": (954.0, 13986806)}}

lab = pd.read_csv(PROCESSED_DIR / "aemo_nem_label_v2.csv", parse_dates=["DATETIME"])
pf = pd.read_csv(PROCESSED_DIR / "price_features_earliest.csv", parse_dates=["DATETIME"])[KEYS + OLD]
df = lab.merge(pf, on=KEYS)
df["y_over"] = ((df.f_decision - df.p_disp30) > OVER).astype(int)
fit = df[(df.partition == "train") & (df.DATETIME < "2022-08-01")]
val = df[(df.partition == "train") & (df.DATETIME >= "2022-08-01")]
yo = fit.y_over.values
m = XGBClassifier(**P, scale_pos_weight=(yo == 0).sum() / (yo == 1).sum(), random_state=SEED,
                  eval_metric="logloss", verbosity=0, n_jobs=-1).fit(fit[FULL], yo)
pr, rc, th = precision_recall_curve(val.y_over.values, m.predict_proba(val[FULL])[:, 1])
f1 = 2 * pr[:-1] * rc[:-1] / np.clip(pr[:-1] + rc[:-1], 1e-12, None)
THETA_1S = float(th[np.nanargmax(f1)])
print(f"one-sided model: fit positives {yo.sum():,} of {len(yo):,}; validation positives {val.y_over.sum()}; "
      f"theta_1s (validation max-F1) = {THETA_1S:.6f}; FRI theta = {THETA:.6f}")

t1 = df[df.partition == "test"].merge(
    pd.read_csv(TABLES_DIR / "c2_31_test_scores.csv", parse_dates=["DATETIME"])[KEYS + ["fri_score"]], on=KEYS)
t2 = pd.read_csv(PROCESSED_DIR / "replication_2023_2025_lead30.csv", parse_dates=["DATETIME"]).merge(
    pd.read_csv(TABLES_DIR / "c4_03_scores.csv", parse_dates=["DATETIME"])[KEYS + ["fri_score"]], on=KEYS)


def bands(s, theta):
    return np.where(s >= theta, 0.25, np.where(s >= 0.5, 0.75, 1.0))


rows = []
for label, d in (("test 1", t1), ("test 2", t2)):
    t = d.sort_values(KEYS).reset_index(drop=True)
    t["day"] = t.DATETIME.dt.floor("D").factorize()[0]
    groups = [(g.index.values, g.day.tolist(), g.f_decision.tolist(), g.p_disp30.tolist())
              for _, g in t.groupby("REGIONID", sort=False)]
    n = len(t)
    s_fri, s_1s = t.fri_score.values, m.predict_proba(t[FULL])[:, 1]
    fri3 = bands(s_fri, THETA)
    n25, n75 = int((fri3 == 0.25).sum()), int((fri3 == 0.75).sum())
    order = np.argsort(-s_1s, kind="stable")
    matched = np.ones(n); matched[order[:n25]] = 0.25; matched[order[n25:n25 + n75]] = 0.75
    scales = {"baseline": np.ones(n), "fri_3band": fri3,
              "one_sided_3band": bands(s_1s, THETA_1S), "one_sided_matched": matched}
    over = ((t.f_decision - t.p_disp30) > OVER).values
    for name, sc in scales.items():
        r = A.run_agent(t, sc, groups); disp = r.disp.values
        rows.append(dict(test=label, agent=name, n_x025=int((sc == 0.25).sum()), n_x075=int((sc == 0.75).sum()),
                         over_mwh=round(float((disp * DT)[over].sum()), 1),
                         over_intervals=int(((disp > 0) & over).sum()), net=round(float(r.net.sum()))))
    for a, (mwh, net) in TABLE_VIII[label].items():
        row = [x for x in rows if x["test"] == label and x["agent"] == a][0]
        ok = abs(row["over_mwh"] - mwh) < 0.15 and abs(row["net"] - net) <= 2
        print(f"CHECK {label} {a}: over {row['over_mwh']} vs {mwh}, net {row['net']:,} vs {net:,} -> {'OK' if ok else 'MISMATCH'}")

res = pd.DataFrame(rows)
base = res[res.agent == "baseline"].set_index("test")
res["over_change_vs_base_pct"] = [round((r.over_mwh / base.loc[r.test, "over_mwh"] - 1) * 100, 1) for r in res.itertuples()]
res["net_change_vs_base_pct"] = [round((r.net / base.loc[r.test, "net"] - 1) * 100, 2) for r in res.itertuples()]
res.to_csv(OUT / "b2b_one_sided_dispatch.csv", index=False)
pd.set_option("display.width", 250)
print("\n=== B2b: one-sided score in dispatch ===")
print(res.to_string(index=False))
print("Saved:", OUT / "b2b_one_sided_dispatch.csv")
