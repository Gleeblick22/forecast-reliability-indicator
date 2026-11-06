"""Fig. 8: risk-revenue trade-off of the battery agents and forecast-threshold rules (exploratory, B2).
Reads results/revision/b2_frontier.csv; writes results/figures/fig_8_frontier.{png,pdf,svg}."""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.legend_handler import HandlerTuple
import fri_style
from fri_style import C

AG = {"fri_3band": (C["fri"], "FRI", 8.5), "forecast_level_matched": (C["flevel"], "Forecast-level*", 6.5),
      "vol_matched": (C["vol"], "Volatility-matched", 6.5), "baseline": (C["baseline"], "Baseline", 6.5)}
TC = C["const25"]   # forecast-threshold rules
OC = C["axis"]      # constant derating (off scale)
YLO, YHI = -2.2, 1.6

res = pd.read_csv("results/revision/b2_frontier.csv")
fri_style.use()
fig, axes = plt.subplots(1, 2, figsize=(7.16, 3.45), sharex=True, sharey=True)
for k, (ax, (t, g)) in enumerate(zip(axes, res.groupby("test"))):
    t1 = t == "test 1"
    b = g[g.agent == "baseline"].iloc[0]
    g = g.assign(red=(1 - g.over_mwh / b.over_mwh) * 100, pct=(g.net / b.net - 1) * 100)
    print(f"\n{t}")
    for r in g.itertuples():
        print(f"  {r.agent:26s} avoided={r.red:6.1f}%  revenue={r.pct:+7.2f}%")
    ax.set_xlim(-4, 80); ax.set_ylim(YLO, YHI)
    ax.fill_between([0, 80], 0, YHI, color=C["fri_light"], alpha=0.5, lw=0, zorder=0)
    ax.axhline(0, color=C["axis"], lw=0.8, zorder=1); ax.axvline(0, color=C["axis"], lw=0.8, zorder=1)
    ax.text(78, YHI - 0.08, "Less risk, more revenue", ha="right", va="top", fontsize=7,
            color=C["fri_dark"], style="italic")
    th = g[g.agent.str.contains("thr")].copy()
    th["X"] = th.agent.str.extract(r"(\d{3,})")[0].astype(int)
    th = th.sort_values("X")
    ax.plot(th.red, th.pct, ls="--" if t1 else "-", lw=1.2, marker="o", ms=3.8, color=TC,
            mfc="white" if t1 else TC, mec=TC, mew=1.0, alpha=0.85, zorder=2)
    for r in g[g.agent.str.startswith("const")].itertuples():
        ax.plot(r.red, YHI - 0.13, "^", ms=6, color=OC, mfc="white" if t1 else OC, mec=OC, mew=1.2,
                clip_on=False, zorder=6)
    for a, (col, name, ms) in AG.items():
        r = g[g.agent == a].iloc[0]
        ax.plot(r.red, r.pct, "o", ms=ms, color=col, mfc="white" if t1 else col, mec=col,
                mew=1.5 if t1 else 0.5, zorder=4)
    ax.set_title("(a) Test 1 (Nov–Dec 2022)" if t1 else "(b) Test 2 (2023–25)", loc="left", pad=8)
    ax.set_xlabel("Risky energy avoided vs baseline (%)")
    ax.grid(True, color="#e6e6e3", lw=0.6)
    ax.set_axisbelow(True)
axes[0].set_ylabel("Revenue change vs baseline (%)")

H = [(Line2D([], [], ls="", marker="o", ms=ms, mfc="white", mec=col, mew=1.5),
      Line2D([], [], ls="", marker="o", ms=ms, color=col)) for col, name, ms in AG.values()]
thr1 = Line2D([], [], ls="--", lw=1.2, marker="o", ms=3.8, color=TC, mfc="white", mec=TC)
thr2 = Line2D([], [], ls="-", lw=1.2, marker="o", ms=3.8, color=TC)
tri1 = Line2D([], [], ls="", marker="^", ms=6, mfc="white", mec=OC, mew=1.2)
tri2 = Line2D([], [], ls="", marker="^", ms=6, color=OC)
H += [(thr1, thr2), (tri1, tri2),
      Line2D([], [], ls="", marker="o", ms=6, mfc="white", mec=C["ink2"], mew=1.3),
      Line2D([], [], ls="", marker="o", ms=6, color=C["ink2"])]
L = [name for _, name, _ in AG.values()] + ["Forecast-threshold rules", "Constant derating (revenue off scale)",
                                             "Test 1", "Test 2"]
fig.tight_layout(rect=(0, 0.14, 1, 1), w_pad=1.5)
x0 = axes[0].get_position().x0; x1 = axes[1].get_position().x1
leg = fig.legend(H, L, handler_map={tuple: HandlerTuple(ndivide=None, pad=0.6)}, loc="lower left",
                 bbox_to_anchor=(x0, 0.01, x1 - x0, 0.1), mode="expand", ncol=4, frameon=True, fontsize=7.5,
                 handlelength=3.0, handletextpad=0.6, borderpad=0.7, labelspacing=0.6, fancybox=False)
leg.get_frame().set_edgecolor(C["axis"]); leg.get_frame().set_linewidth(0.6)
pathlib.Path("results/figures").mkdir(parents=True, exist_ok=True)
for ext in ("png", "pdf", "svg"):
    fig.savefig(f"results/figures/fig_8_frontier.{ext}")
print("\nSaved results/figures/fig_8_frontier.{png,pdf,svg}")
