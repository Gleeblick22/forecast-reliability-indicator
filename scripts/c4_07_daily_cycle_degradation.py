"""c4_07 (exploratory, NOT registered): degradation charged per daily cycle instead of per discharge interval.
In the agent model the SoC resets each day and charging does not refill it within the day, so each region-day is
one discharge cycle of depth (energy discharged that day)/capacity. Same agents, same dispatch; only the
degradation accounting changes. Output: results/tables/c4_07_daily_cycle.csv"""
import sys, importlib.util
import numpy as np
import pandas as pd
from config.settings import PROCESSED_DIR, TABLES_DIR, BATTERY_CAPACITY_MWH as CAP

spec = importlib.util.spec_from_file_location("M", "scripts/c4_03_test_R.py")
M = importlib.util.module_from_spec(spec); spec.loader.exec_module(M)
A, KEYS = M.A, M.KEYS
KNOWN_NET = {("2022 test", "baseline"): 307230, ("2022 test", "fri_3band"): 310287,
             ("2023-25", "baseline"): 14027569, ("2023-25", "fri_3band"): 13986806}


def run(period, d):
    d = d.sort_values(KEYS).reset_index(drop=True)
    t, groups, scales = M.agent_setup(d, d.fri_score.values)
    fri3 = scales["fri_3band"]; n = len(t)
    n25, n75 = int((fri3 == 0.25).sum()), int((fri3 == 0.75).sum())
    order = np.argsort(-t.f_decision.fillna(-1e9).values, kind="stable")
    fm = np.ones(n); fm[order[:n25]] = 0.25; fm[order[n25:n25 + n75]] = 0.75
    scales["fdec_matched"] = fm
    scales["const_0.75"] = np.full(n, 0.75)
    rows = []
    for k, sc in scales.items():
        r = A.run_agent(t, sc, groups)
        gross, chg, deg_int = r.rev.sum(), r.chg.sum(), r.deg.sum()
        e_day = (r.disp * A.DT).groupby([t.REGIONID, t.day]).sum()
        deg_day = float((A.R_REPL * A.ALPHA * (e_day / CAP) ** A.BETA).sum())
        net_int, net_day = gross - chg - deg_int, gross - chg - deg_day
        if (period, k) in KNOWN_NET:
            ok = abs(net_int - KNOWN_NET[(period, k)]) < 2
            print(f"  check {period} {k}: per-interval net {net_int:,.0f} vs known {KNOWN_NET[(period, k)]:,} -> {'OK' if ok else 'DIFFERENT'}")
        rows.append({"period": period, "agent": k, "gross": round(gross), "charging": round(chg),
                     "deg_per_interval": round(deg_int), "deg_daily_cycle": round(deg_day),
                     "net_per_interval": round(net_int), "net_daily_cycle": round(net_day)})
    return pd.DataFrame(rows)


lab = pd.read_csv(PROCESSED_DIR / "aemo_nem_label_v2.csv", parse_dates=["DATETIME"])
t22 = lab[lab.partition == "test"]
s22 = pd.read_csv(TABLES_DIR / "c2_31_test_scores.csv", parse_dates=["DATETIME"])
sc = next(c for c in ["fri_score", "score", "y_score", "proba", "pred_proba", "p"] if c in s22.columns)
t22 = t22.merge(s22[KEYS + [sc]].rename(columns={sc: "fri_score"}), on=KEYS, how="inner")
rep = pd.read_csv(PROCESSED_DIR / "replication_2023_2025_lead30.csv", parse_dates=["DATETIME"])
rep = rep.merge(pd.read_csv(TABLES_DIR / "c4_03_scores.csv", parse_dates=["DATETIME"])[KEYS + ["fri_score"]], on=KEYS, how="inner")
res = pd.concat([run("2022 test", t22), run("2023-25", rep)])
for per in res.period.unique():
    m = res.period == per
    fri = res.loc[m & (res.agent == "fri_3band")].iloc[0]
    res.loc[m, "const25_minus_fri_daily"] = None
    c25 = res.loc[m & (res.agent == "const_0.25")].iloc[0]
    print(f"{per}: const x0.25 - FRI net  per-interval {c25.net_per_interval - fri.net_per_interval:+,}  "
          f"daily-cycle {c25.net_daily_cycle - fri.net_daily_cycle:+,}")
res = res.drop(columns="const25_minus_fri_daily")
res.to_csv(TABLES_DIR / "c4_07_daily_cycle.csv", index=False)
with pd.option_context("display.width", 220):
    print(res.to_string(index=False))
