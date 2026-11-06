"""block_inference.py (revision B6, EXPLORATORY; reviewer R2.8, Ed.7).
Day-block bootstrap versions of tests that assumed independent intervals:
  H5 (test 1): reduction in unreliable intervals without an FRI warning (registered: >= 20%; McNemar)
  H6 (test 1): Pearson r between confidence 1 - s and dispatched energy (registered: Fisher-z CI)
  R4 (test 2): dAP = AP(FRI) - AP(recent_std_3h) (registered: interval bootstrap)
R1 day-block CIs are in b1_r1_forecast_conditioned.csv. Whole days are resampled, all regions of a day together.
Checks: H5 94 -> 54 (-42.6%); H6 r 0.318, n 587; R4 dAP 0.363.
Output: results/revision/b6_block_inference.csv"""
import importlib.util, json
import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score
from config.settings import PROCESSED_DIR, TABLES_DIR

spec = importlib.util.spec_from_file_location("A", "scripts/c3_50_agents_v2.py")
A = importlib.util.module_from_spec(spec); spec.loader.exec_module(A)

KEYS, Y, SEED, NBOOT = ["REGIONID", "DATETIME"], "y_v2_d300", 42, 2000
THETA = json.load(open(TABLES_DIR / "c2_31_best_params.json"))["theta_d300"]
OUT = TABLES_DIR.parent / "revision"; OUT.mkdir(parents=True, exist_ok=True)
rng = np.random.default_rng(SEED)

lab = pd.read_csv(PROCESSED_DIR / "aemo_nem_label_v2.csv", parse_dates=["DATETIME"])
t1 = lab[lab.partition == "test"].merge(
    pd.read_csv(TABLES_DIR / "c2_31_test_scores.csv", parse_dates=["DATETIME"])[KEYS + ["fri_score"]], on=KEYS)
t1 = t1.sort_values(KEYS).reset_index(drop=True)
t2 = pd.read_csv(PROCESSED_DIR / "replication_2023_2025_lead30.csv", parse_dates=["DATETIME"]).merge(
    pd.read_csv(TABLES_DIR / "c4_03_scores.csv", parse_dates=["DATETIME"])[KEYS + ["fri_score"]], on=KEYS)
t2 = t2.sort_values(KEYS).reset_index(drop=True)


def day_index(d):
    days = d.DATETIME.dt.floor("D").values
    ud = np.unique(days)
    return ud, {k: np.where(days == k)[0] for k in ud}


def boot(d, stat):
    ud, idx = day_index(d)
    reps = []
    for _ in range(NBOOT):
        pick = np.concatenate([idx[k] for k in rng.choice(ud, len(ud))])
        v = stat(pick)
        if v is not None and np.isfinite(v):
            reps.append(v)
    return np.percentile(reps, 2.5), np.percentile(reps, 97.5), len(reps)


rows = []

# H5: unwarned unreliable intervals, baseline (no warnings) vs FRI (warning = score >= theta)
y1, warn = t1[Y].values.astype(bool), (t1.fri_score.values >= THETA)
base_n, fri_n = int(y1.sum()), int((y1 & ~warn).sum())
red = 1 - fri_n / base_n


def h5_stat(p):
    b = y1[p].sum()
    return None if b == 0 else 1 - (y1[p] & ~warn[p]).sum() / b


lo, hi, n = boot(t1, h5_stat)
rows.append(dict(test="H5 (test 1)", estimate=f"{base_n} -> {fri_n} ({-red*100:.1f}%)", stat=round(red, 3),
                 ci_lo=round(lo, 3), ci_hi=round(hi, 3), criterion="reduction >= 0.20", met_by_ci_lower=bool(lo >= 0.20),
                 n_boot=n))

# H6: run the FRI agent on test 1, correlate confidence (1 - s) with dispatched energy over dispatch intervals
t = t1.copy()
t["day"] = t.DATETIME.dt.floor("D").factorize()[0]
groups = [(g.index.values, g.day.tolist(), g.f_decision.tolist(), g.p_disp30.tolist())
          for _, g in t.groupby("REGIONID", sort=False)]
s1 = t.fri_score.values
fri3 = np.where(s1 >= THETA, 0.25, np.where(s1 >= 0.5, 0.75, 1.0))
disp = A.run_agent(t, fri3, groups).disp.values
mask = disp > 0
conf = 1 - s1
r_obs = float(np.corrcoef(conf[mask], disp[mask])[0, 1])


def h6_stat(p):
    m = mask[p]
    if m.sum() < 3:
        return None
    return float(np.corrcoef(conf[p][m], disp[p][m])[0, 1])


lo, hi, n = boot(t1, h6_stat)
rows.append(dict(test="H6 (test 1)", estimate=f"r = {r_obs:.3f}, n = {int(mask.sum())}", stat=round(r_obs, 3),
                 ci_lo=round(lo, 3), ci_hi=round(hi, 3), criterion="r > 0", met_by_ci_lower=bool(lo > 0), n_boot=n))

# R4: dAP FRI - recent_std_3h on test 2
y2, s2, v2 = t2[Y].values, t2.fri_score.values, t2.recent_std_3h.fillna(0).values
dap = average_precision_score(y2, s2) - average_precision_score(y2, v2)


def r4_stat(p):
    if y2[p].sum() == 0:
        return None
    return average_precision_score(y2[p], s2[p]) - average_precision_score(y2[p], v2[p])


lo, hi, n = boot(t2, r4_stat)
rows.append(dict(test="R4 (test 2)", estimate=f"dAP = {dap:.3f}", stat=round(dap, 3), ci_lo=round(lo, 3),
                 ci_hi=round(hi, 3), criterion="dAP > 0 and CI lower > 0", met_by_ci_lower=bool(lo > 0), n_boot=n))

res = pd.DataFrame(rows)
res.to_csv(OUT / "b6_block_inference.csv", index=False)
pd.set_option("display.width", 220)
print("\n=== B6: day-block bootstrap inference (95% CI) ===")
print(res.to_string(index=False))
print("\nCHECK expected: H5 94 -> 54 (-42.6%); H6 r 0.318, n 587; R4 dAP 0.363")
print("Saved:", OUT / "b6_block_inference.csv")
