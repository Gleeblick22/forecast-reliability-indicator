"""c4_06 (exploratory, NOT registered): forecast-level-matched control agent.
Built exactly like the registered volatility-matched control (c4_03 agent_setup): the same number of x0.25 and
x0.75 intervals as FRI, assigned by highest decision forecast f_decision instead of recent_std_3h.
Runs on the 2022 test set and on 2023-25; first reproduces known results as a check.
Output: results/tables/c4_06_fdec_matched.csv, c4_06_fdec_matched_boot.csv"""
import sys, importlib.util
import numpy as np
import pandas as pd
from config.settings import PROCESSED_DIR, TABLES_DIR

spec = importlib.util.spec_from_file_location("M", "scripts/c4_03_test_R.py")
M = importlib.util.module_from_spec(spec); spec.loader.exec_module(M)
A, KEYS = M.A, M.KEYS
NEED = ["f_decision", "p_disp30", "recent_std_3h"]
KNOWN = {"2022 test": {"baseline": 65.0, "fri_3band": 20.5, "vol_matched": 45.2},
         "2023-25": {"baseline": 1800.0, "fri_3band": 954.0, "vol_matched": 1511.6}}


def run(period, d):
    miss = [c for c in NEED + ["fri_score"] if c not in d.columns]
    if miss:
        sys.exit(f"{period}: missing {miss}; columns: {list(d.columns)}")
    d = d.sort_values(KEYS).reset_index(drop=True)
    t, groups, scales = M.agent_setup(d, d.fri_score.values)
    fri3 = scales["fri_3band"]; n = len(t)
    n25, n75 = int((fri3 == 0.25).sum()), int((fri3 == 0.75).sum())
    order = np.argsort(-t.f_decision.fillna(-1e9).values, kind="stable")
    fm = np.ones(n); fm[order[:n25]] = 0.25; fm[order[n25:n25 + n75]] = 0.75
    scales["fdec_matched"] = fm
    over = ((t.f_decision - t.p_disp30) > 300).values
    rows, daily = [], {}
    for k, sc in scales.items():
        r = A.run_agent(t, sc, groups)
        rows.append({"period": period, **A.summarise(k, t, r)})
        daily[k] = pd.Series(r.disp.values * M.DT * over).groupby(t.day).sum()
    res = pd.DataFrame(rows)
    for k, v in KNOWN[period].items():
        got = float(res.loc[res.agent == k, "mwh_into_overforecast"].iloc[0])
        print(f"  check {period} {k}: {got:.1f} vs known {v:.1f} -> {'OK' if abs(got - v) < 0.15 else 'DIFFERENT'}")
    boot = []
    for other in ["fdec_matched", "vol_matched", "baseline"]:
        tot, lo, hi = A.boot_diff(daily[other], daily["fri_3band"])
        boot.append({"period": period, "comparison": f"{other} - fri_3band (MWh into over-forecast)",
                     "diff": round(tot, 1), "ci_lo": round(lo, 1), "ci_hi": round(hi, 1)})
    return res, pd.DataFrame(boot)


lab = pd.read_csv(PROCESSED_DIR / "aemo_nem_label_v2.csv", parse_dates=["DATETIME"])
t22 = lab[lab.partition == "test"]
s22 = pd.read_csv(TABLES_DIR / "c2_31_test_scores.csv", parse_dates=["DATETIME"])
sc = next((c for c in ["fri_score", "score", "y_score", "proba", "pred_proba", "p"] if c in s22.columns), None)
if sc is None or any(k not in s22.columns for k in KEYS):
    sys.exit(f"c2_31_test_scores columns: {list(s22.columns)}")
t22 = t22.merge(s22[KEYS + [sc]].rename(columns={sc: "fri_score"}), on=KEYS, how="inner")
rep = pd.read_csv(PROCESSED_DIR / "replication_2023_2025_lead30.csv", parse_dates=["DATETIME"])
s25 = pd.read_csv(TABLES_DIR / "c4_03_scores.csv", parse_dates=["DATETIME"])
rep = rep.merge(s25[KEYS + ["fri_score"]], on=KEYS, how="inner")
print(f"2022 test rows {len(t22):,}; 2023-25 rows {len(rep):,}")

R, Bt = zip(*[run("2022 test", t22), run("2023-25", rep)])
res, boot = pd.concat(R), pd.concat(Bt)
res.to_csv(TABLES_DIR / "c4_06_fdec_matched.csv", index=False)
boot.to_csv(TABLES_DIR / "c4_06_fdec_matched_boot.csv", index=False)
cols = ["period", "agent", "dispatch_intervals", "mwh_into_overforecast", "dispatched_into_overforecast", "silent_failures", "net_revenue"]
with pd.option_context("display.width", 220):
    print(res[cols].to_string(index=False)); print(boot.to_string(index=False))
