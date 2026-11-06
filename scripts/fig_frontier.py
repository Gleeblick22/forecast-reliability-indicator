"""fig_frontier.py: Fig. 8 (revision) - risk-revenue frontier from results/revision/b2_frontier.csv (exploratory).
Uses the shared style (fri_style): same palette and agent colours as Figs 1-9.
Periods: test 2 (2023-25) filled markers / solid line, test 1 (2022) open markers / dashed line.
y = net revenue change vs baseline (%); constant derating is above the plotted range and shown as arrows.
Outputs: results/figures/fig_8_frontier.png / .pdf / .svg"""
import sys
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from config.settings import TABLES_DIR

sys.path.insert(0, "scripts")
import fri_style
from fri_style import C

fri_style.use()
res = pd.read_csv(TABLES_DIR.parent / "revision" / "b2_frontier.csv")

AG = {
    "baseline": ("s", C["baseline"], 6, "Baseline"),
    "fri_3band": ("*", C["fri"], 12, "FRI three-band"),
    "vol_matched": ("^", C["vol"], 7, "Volatility-matched"),
    "forecast_level_matched": ("D", C["flevel"], 6, "Forecast-level-matched*"),
}
OFF = {"const_0.75": ("Constant ×0.75", C["const75"]), "const_0.25": ("Constant ×0.25", C["const25"])}
THR = C["axis"]

fig, axes = plt.subplots(1, 2, figsize=(7.16, 3.1))
for k, (ax, (label, g)) in enumerate(zip(axes, res.groupby("test"))):
    test1 = label == "test 1"
    base = g[g.agent == "baseline"].net.iloc[0]
    g = g.assign(pct=(g.net / base - 1) * 100)
    thr = g[g.agent.str.startswith("threshold")].sort_values("over_mwh").copy()
    thr["X"] = thr.agent.str.extract(r">=(\d+)_")[0].astype(int)
    ax.plot(thr.over_mwh, thr.pct, ls="--" if test1 else "-", marker="o", ms=3.5, lw=1.0, color=THR,
            mfc="white" if test1 else THR, mec=THR, zorder=2)
    for a, (m, col, ms, _) in AG.items():
        r = g[g.agent == a].iloc[0]
        ax.plot(r.over_mwh, r.pct, m, ms=ms, color=col, mfc="white" if test1 else col, mec=col,
                mew=1.2 if test1 else 0.6, zorder=4)
    ymin = min(g.pct[~g.agent.isin(OFF)].min(), -0.5) - 0.6
    ymax = max(g.pct[~g.agent.isin(OFF)].max(), 0.5) + 1.1
    ax.set_ylim(ymin, ymax)
    yr = ymax - ymin
    xlo, xhi = ax.get_xlim()
    pts = (thr.groupby([thr.over_mwh.round(1), thr.pct.round(3)]).X.agg(["min", "max"])
           .reset_index().sort_values("over_mwh").reset_index(drop=True))
    for i, p in pts.iterrows():
        lo, hi = int(p["min"]), int(p["max"])
        txt = f"{lo}" if lo == hi else f"{lo}–{hi}"
        near_right = p.over_mwh > xlo + 0.85 * (xhi - xlo) and p.pct <= 0.2
        dy = -9 if i % 2 == 0 else 6
        ax.annotate(txt, (p.over_mwh, p.pct), textcoords="offset points", xytext=(-4 if near_right else 0, dy),
                    ha="right" if near_right else "center", va="top" if dy < 0 else "bottom",
                    fontsize=7, color=C["ink2"])
    off = g[g.agent.isin(OFF)].sort_values("over_mwh", ascending=False).reset_index(drop=True)
    for i, r in off.iterrows():
        name, col = OFF[r.agent]
        ax.annotate("", xy=(r.over_mwh, ymax), xytext=(r.over_mwh, ymax - 0.07 * yr),
                    arrowprops=dict(arrowstyle="->", color=col, lw=1.0))
        ax.text(r.over_mwh - 0.01 * (xhi - xlo), ymax - (0.10 + 0.075 * i) * yr,
                f"{name}: {r.pct:+.0f}% (off scale)", ha="right", va="top", fontsize=7, color=C["ink2"])
    ax.axhline(0, color=C["axis"], lw=0.8, zorder=1)
    ax.set_title(("(a) Test 1 (Nov–Dec 2022)" if test1 else "(b) Test 2 (2023–25)"), loc="left")
    ax.set_xlabel("Energy into over-forecast intervals (MWh)")
    ax.set_ylabel("Net revenue vs baseline (%)" if k == 0 else "")

handles = [Line2D([], [], color=THR, marker="o", ms=3.5, lw=1.0, label="Forecast threshold f ≥ X AUD/MWh (×0.25)*")]
handles += [Line2D([], [], ls="", marker=m, ms=min(ms, 9), color=col, label=lab) for m, col, ms, lab in AG.values()]
handles += [Line2D([], [], ls="", marker="o", ms=5, color=C["ink2"], label="Test 2: filled, solid"),
            Line2D([], [], ls="", marker="o", ms=5, mfc="white", mec=C["ink2"], label="Test 1: open, dashed")]
fig.legend(handles=handles, loc="lower center", ncol=4, frameon=False, bbox_to_anchor=(0.5, -0.06))
fig.tight_layout(rect=(0, 0.1, 1, 1))
out = TABLES_DIR.parent / "figures" / "fig_8_frontier"
for ext in ("png", "pdf", "svg"):
    fig.savefig(f"{out}.{ext}")
print("Saved:", f"{out}.png / .pdf / .svg")
