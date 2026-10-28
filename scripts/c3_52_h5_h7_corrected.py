"""c3_52 (Roadmap v3, A1-A2): registered H5-H7 re-evaluated with the CORRECTED agent
(c3_50: high s_hat -> scale down; per-region batteries; ex-ante charging) on the 2022 test set.
H5: silent failures (dispatched, settled >= 300, decision - settled > 100), >= 20% reduction.
H6: Pearson r(dispatch MW, confidence = 1 - s_hat) over FRI-dispatched intervals, p < 0.05, r > 0.
H7: gross revenue FRI vs baseline >= +15% (registered measure); net shown for reference.
A2: MWh into over-forecast (> 300) intervals, FRI vs baseline, daily bootstrap 95% CI.
Output: results/tables/c3_52_h5_h7.csv"""
import sys, json, importlib.util
import numpy as np
import pandas as pd
from scipy.stats import pearsonr
from config.settings import PROCESSED_DIR, TABLES_DIR
from config.logging_config import get_logger

logger = get_logger("c3_52_h5_h7_corrected")
spec = importlib.util.spec_from_file_location("A", "scripts/c3_50_agents_v2.py")
A = importlib.util.module_from_spec(spec); spec.loader.exec_module(A)
KEYS, DT = ["REGIONID", "DATETIME"], 0.5
theta = json.load(open(TABLES_DIR / "c2_31_best_params.json"))["theta_d300"]

t = pd.read_csv(TABLES_DIR / "c2_31_test_scores.csv", parse_dates=["DATETIME"])
t = t.sort_values(KEYS).reset_index(drop=True)
t["day"] = t.DATETIME.dt.floor("D").factorize()[0]
groups = [(g.index.values, g.day.tolist(), g.f_decision.tolist(), g.p_disp30.tolist())
          for _, g in t.groupby("REGIONID", sort=False)]
s = t.fri_score.values
fri = np.where(s >= theta, 0.25, np.where(s >= 0.5, 0.75, 1.0))
rb, rf = A.run_agent(t, np.ones(len(t)), groups), A.run_agent(t, fri, groups)

over = (t.f_decision - t.p_disp30).values
def sf(r): return int(((r.disp.values > 0) & (t.p_disp30.values >= 300) & (over > 100)).sum())
sf_b, sf_f = sf(rb), sf(rf)
h5 = "not testable (0 baseline events)" if sf_b == 0 else f"{(1 - sf_f / sf_b) * 100:.1f}% reduction"

d = rf.disp.values > 0
r6, p6 = pearsonr(rf.disp.values[d], 1 - s[d])
z, se = np.arctanh(r6), 1 / np.sqrt(d.sum() - 3)
lo6, hi6 = np.tanh(z - 1.96 * se), np.tanh(z + 1.96 * se)

g_b, g_f = rb.rev.sum(), rf.rev.sum()
n_b, n_f = rb.net.sum(), rf.net.sum()
gt, glo, ghi = A.boot_diff(rf.rev.groupby(t.day).sum(), rb.rev.groupby(t.day).sum())

bad = over > 300
mb, mf = (rb.disp.values * DT)[bad].sum(), (rf.disp.values * DT)[bad].sum()
eb = pd.Series(rb.disp.values * DT * bad).groupby(t.day).sum()
ef = pd.Series(rf.disp.values * DT * bad).groupby(t.day).sum()
et, elo, ehi = A.boot_diff(eb, ef)

rows = [
    dict(H="H5", criterion=">= 20% fewer silent failures", result=f"baseline {sf_b}, FRI {sf_f}; {h5}",
         outcome="not testable" if sf_b == 0 else ("supported" if sf_b and (1 - sf_f / sf_b) >= 0.20 else "not supported")),
    dict(H="H6", criterion="r > 0, p < 0.05", result=f"r = {r6:.4f} [{lo6:.4f}, {hi6:.4f}], p = {p6:.3g}, n = {int(d.sum())}",
         outcome="supported" if (r6 > 0 and p6 < 0.05) else "not supported"),
    dict(H="H7", criterion="gross revenue >= +15%", result=f"gross {g_b:,.0f} -> {g_f:,.0f} ({(g_f / g_b - 1) * 100:+.2f}%), "
         f"daily-bootstrap diff {gt:,.0f} [{glo:,.0f}, {ghi:,.0f}]; net {n_b:,.0f} -> {n_f:,.0f} ({(n_f / n_b - 1) * 100:+.2f}%)",
         outcome="supported" if (g_f / g_b - 1) >= 0.15 else "not supported"),
    dict(H="A2 exposure 2022", criterion="descriptive", result=f"MWh into over-forecast: baseline {mb:.1f}, FRI {mf:.1f} "
         f"({(1 - mf / mb) * 100:.1f}% less); baseline - FRI {et:.1f} [{elo:.1f}, {ehi:.1f}]", outcome="—"),
]
res = pd.DataFrame(rows)
res.to_csv(TABLES_DIR / "c3_52_h5_h7.csv", index=False)
with pd.option_context("display.width", 250, "display.max_colwidth", 200):
    logger.info(f"\n{res}")
sys.exit(0)
