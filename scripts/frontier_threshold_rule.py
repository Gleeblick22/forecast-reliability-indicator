"""frontier_threshold_rule.py (revision B2, EXPLORATORY; reviewer R1.4, R1.7, R2.4, DA.4, DA.6, Ed.2, Ed.3).
Threshold rules (derate to x0.25 when f_decision >= X) plus all agents on a risk-revenue plane
(over-forecast MWh vs net revenue), test 1 and test 2; Pareto frontier; break-even exposure price vs FRI.
Same simulation (c3_50.run_agent), scores (c2_31, c4_03) and theta as the registered analysis.
Checks: baseline, FRI, volatility-matched rows must equal Table VIII.
Outputs: results/revision/b2_frontier.csv, results/figures/fig_frontier.png"""
import importlib.util, json, sys
import numpy as np
import pandas as pd
from config.settings import PROCESSED_DIR, TABLES_DIR

spec = importlib.util.spec_from_file_location("A", "scripts/c3_50_agents_v2.py")
A = importlib.util.module_from_spec(spec); spec.loader.exec_module(A)

KEYS, DT, OVER = ["REGIONID", "DATETIME"], 0.5, 300.0
THETA = json.load(open(TABLES_DIR / "c2_31_best_params.json"))["theta_d300"]
X_LEVELS = [300, 500, 1000, 2000, 5000]
OUT = TABLES_DIR.parent / "revision"; OUT.mkdir(parents=True, exist_ok=True)
FIG = TABLES_DIR.parent / "figures"; FIG.mkdir(parents=True, exist_ok=True)
TABLE_VIII = {
    "test 1": {"baseline": (65.0, 307230), "fri_3band": (20.5, 310287), "vol_matched": (45.2, 308758)},
    "test 2": {"baseline": (1800.0, 14027569), "fri_3band": (954.0, 13986806), "vol_matched": (1511.6, 14023851)},
}


def load_test1():
    lab = pd.read_csv(PROCESSED_DIR / "aemo_nem_label_v2.csv", parse_dates=["DATETIME"])
    sc = pd.read_csv(TABLES_DIR / "c2_31_test_scores.csv", parse_dates=["DATETIME"])[KEYS + ["fri_score"]]
    return lab[lab.partition == "test"].merge(sc, on=KEYS).sort_values(KEYS).reset_index(drop=True)


def load_test2():
    d = pd.read_csv(PROCESSED_DIR / "replication_2023_2025_lead30.csv", parse_dates=["DATETIME"])
    sc = pd.read_csv(TABLES_DIR / "c4_03_scores.csv", parse_dates=["DATETIME"])[KEYS + ["fri_score"]]
    return d.merge(sc, on=KEYS).sort_values(KEYS).reset_index(drop=True)


def matched(order, n25, n75, n):
    s = np.ones(n); s[order[:n25]] = 0.25; s[order[n25:n25 + n75]] = 0.75
    return s


def evaluate(d, label):
    for c in ("f_decision", "p_disp30", "recent_std_3h", "fri_score"):
        assert c in d.columns, f"{label}: missing column {c}"
    t = d.copy()
    t["day"] = t.DATETIME.dt.floor("D").factorize()[0]
    groups = [(g.index.values, g.day.tolist(), g.f_decision.tolist(), g.p_disp30.tolist())
              for _, g in t.groupby("REGIONID", sort=False)]
    n, s, f = len(t), t.fri_score.values, t.f_decision.values
    fri3 = np.where(s >= THETA, 0.25, np.where(s >= 0.5, 0.75, 1.0))
    n25, n75 = int((fri3 == 0.25).sum()), int((fri3 == 0.75).sum())
    scales = {"baseline": np.ones(n), "fri_3band": fri3,
              "vol_matched": matched(np.argsort(-t.recent_std_3h.fillna(0).values, kind="stable"), n25, n75, n),
              "forecast_level_matched": matched(np.argsort(-f, kind="stable"), n25, n75, n),
              "const_0.75": np.full(n, 0.75), "const_0.25": np.full(n, 0.25)}
    for X in X_LEVELS:
        scales[f"threshold_f>={X}_x0.25"] = np.where(f >= X, 0.25, 1.0)
    over = ((t.f_decision - t.p_disp30) > OVER).values
    rows = []
    for name, sc in scales.items():
        r = A.run_agent(t, sc, groups); disp = r.disp.values
        rows.append(dict(test=label, agent=name, over_mwh=round(float((disp * DT)[over].sum()), 1),
                         over_intervals=int(((disp > 0) & over).sum()), net=round(float(r.net.sum()))))
        print(f"  {label}: {name} done", flush=True)
    res = pd.DataFrame(rows)
    res["on_frontier"] = [not ((res.over_mwh <= a.over_mwh) & (res.net >= a.net) &
                               ((res.over_mwh < a.over_mwh) | (res.net > a.net))).any() for a in res.itertuples()]
    fri = res[res.agent == "fri_3band"].iloc[0]
    dm = res.over_mwh - fri.over_mwh
    res["breakeven_vs_fri_aud_per_mwh"] = np.where(dm.abs() > 1e-9, ((res.net - fri.net) / dm).round(0), np.nan)
    return res


all_res = []
for label, loader in (("test 1", load_test1), ("test 2", load_test2)):
    r = evaluate(loader(), label)
    for a, (mwh, net) in TABLE_VIII[label].items():
        row = r[r.agent == a].iloc[0]
        ok = abs(row.over_mwh - mwh) < 0.15 and abs(row.net - net) <= 2
        print(f"CHECK {label} {a}: over {row.over_mwh} vs {mwh}, net {row.net:,.0f} vs {net:,} -> {'OK' if ok else 'MISMATCH'}")
    all_res.append(r)
res = pd.concat(all_res, ignore_index=True)
res.to_csv(OUT / "b2_frontier.csv", index=False)
pd.set_option("display.width", 250)
print("\n=== B2: risk-revenue frontier ===")
print(res.to_string(index=False))
print("Saved:", OUT / "b2_frontier.csv")

try:
    import matplotlib; matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    try:
        sys.path.insert(0, "scripts"); import fri_style  # noqa: F401
    except Exception:
        pass
    fig, axes = plt.subplots(1, 2, figsize=(7.2, 3.2))
    marks = {"baseline": ("s", "Baseline"), "fri_3band": ("*", "FRI"), "vol_matched": ("^", "Volatility-matched"),
             "forecast_level_matched": ("D", "Forecast-level-matched"), "const_0.75": ("v", "Constant ×0.75"),
             "const_0.25": ("P", "Constant ×0.25")}
    for ax, (label, g) in zip(axes, res.groupby("test")):
        thr = g[g.agent.str.startswith("threshold")].sort_values("over_mwh")
        ax.plot(thr.over_mwh, thr.net / 1e6, "-o", ms=3, color="0.55", label="Threshold rule (f ≥ X)")
        for a, (m, lab) in marks.items():
            row = g[g.agent == a].iloc[0]
            ax.plot(row.over_mwh, row.net / 1e6, m, ms=9 if a == "fri_3band" else 6, label=lab)
        ax.set_title(label.capitalize()); ax.set_xlabel("Energy into over-forecast intervals (MWh)")
        ax.set_ylabel("Net revenue (AUD million)")
    axes[1].legend(fontsize=6, loc="best"); fig.tight_layout()
    fig.savefig(FIG / "fig_frontier.png", dpi=600); print("Saved:", FIG / "fig_frontier.png")
except Exception as e:
    print("Figure skipped:", e)
