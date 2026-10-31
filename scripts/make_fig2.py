"""make_fig2.py (Roadmap v3, B4): Fig. 2 FRI pipeline in colour (shared style fri_style.py; PNG 300 dpi, SVG, PDF).
Solid arrows: information available at decision time. Dashed arrows: settled prices, used only for the
label (training) and for evaluation. theta and the feature count come from results/numbers.json."""
import json
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

try:
    from config.settings import TABLES_DIR
    R = TABLES_DIR.parent
except ImportError:                      # preview outside the repository
    R = Path(".")
FIG = R / "figures"; FIG.mkdir(exist_ok=True)
try:
    N = json.load(open(R / "numbers.json"))
    THETA = N["headline"]["det2022"]["theta"]
    NFEAT = len(N["sources"]["importance"])
except FileNotFoundError:
    print("numbers.json not found: preview values used")
    THETA, NFEAT = 0.849089, 17
assert NFEAT == 17, NFEAT
print(f"  check Fig.2: theta = {THETA:.6f}, features = {NFEAT}")

import fri_style as FS
FS.use(); PAL = FS.C
plt.rcParams.update({"font.size": 7, "axes.grid": False})
fig, ax = plt.subplots(figsize=(7.2, 3.7))
ax.set_xlim(0, 100); ax.set_ylim(0, 57); ax.axis("off")


ROLE = {"pre": ("white", PAL["fri"], PAL["fri_dark"]), "model": (PAL["fri_light"], PAL["fri"], PAL["fri_dark"]),
        "set": (PAL["part_fit"], PAL["axis"], PAL["ink"]), "label": ("#fdeeee", PAL["extreme"], "#a32d2d")}


def box(x0, y0, x1, y1, title, body, role="pre"):
    fc, ec, tc = ROLE[role]
    ax.add_patch(FancyBboxPatch((x0, y0), x1 - x0, y1 - y0, boxstyle="round,pad=0,rounding_size=1.2",
                                facecolor=fc, edgecolor=ec, lw=0.9, zorder=2))
    ax.text((x0 + x1) / 2, y1 - 1.6, title, ha="center", va="top", fontsize=7.6, fontweight="bold", color=tc, zorder=3)
    ax.text((x0 + x1) / 2, y1 - 5.2, body, ha="center", va="top", fontsize=6.8, linespacing=1.3, color=PAL["ink"], zorder=3)
    return dict(l=x0, r=x1, b=y0, t=y1, cx=(x0 + x1) / 2, cy=(y0 + y1) / 2)


def arrow(p, q, dashed=False, rad=0.0):
    ax.add_patch(FancyArrowPatch(p, q, arrowstyle="-|>", mutation_scale=8, lw=0.9, color=(PAL["axis"] if dashed else PAL["ink"]),
                                 linestyle=(0, (4, 2.5)) if dashed else "-", connectionstyle=f"arc3,rad={rad}",
                                 shrinkA=0, shrinkB=0, zorder=4))


# ---- band divider ----
DIV = 23.0
ax.plot([0, 100], [DIV, DIV], color=PAL["axis"], lw=0.7, ls=(0, (1.5, 2)), zorder=1)
ax.text(0.3, DIV + 0.8, "Available at decision time", ha="left", va="bottom",
        fontsize=7, style="italic", color=PAL["fri_dark"])
ax.text(0.3, DIV - 0.8, "After settlement: label and evaluation only", ha="left", va="top",
        fontsize=7, style="italic", color=PAL["ink2"])

# ---- decision-time boxes ----
A = box(0.3, 36, 17, 56, "Pre-dispatch", "AEMO\nPREDISPATCHPRICE\nhalf-hourly runs,\nfive NEM regions")
C = box(19.5, 36, 35, 56, "Decision run", "run closest to a\n45-min lead, within\n[30, 60] min\n" + r"$\rightarrow f(w_t)$")
D = box(37.5, 30, 56.5, 56, f"Features, " + r"$x_t \in \mathbb{R}^{17}$",
        "decision forecast\n" + r"$f(w_t)$ (1)" + "\n\nrevision path, earliest\nrun to decision run (7)\n\n"
        "earliest-run price and\ncalendar (9)")
M = box(59, 36, 75, 56, "FRI model", "XGBoost, depth 2,\n300 trees, rate 0.1;\nfitted Oct 2021 –\nJul 2022, then\n"
        + r"frozen $\rightarrow$ score $\hat{s}_t$", role="model")
P = box(78, 43.5, 99.5, 56, "Dispatch scaling",
        r"$\hat{s}_t < 0.5$: $\times$1.00" + "\n" + r"$0.5 \leq \hat{s}_t < \theta$: $\times$0.75" + "\n"
        + r"$\hat{s}_t \geq \theta$: $\times$0.25" + f"  (θ = {THETA:.3f})")
Bt = box(78, 24.5, 99.5, 41, "Battery agent", "one per region;\n100 MWh / 50 MW;\n" + r"discharge if $f(w_t) \geq 100$;"
         + "\n" + r"ex-ante charging if $f \leq 20$" + "\n(AUD/MWh)")

# ---- after-settlement boxes ----
B = box(0.3, 2, 17, 19, "Settlement", "AEMO\nDISPATCHPRICE\n5-min settled prices,\nINTERVENTION = 0", role="set")
L = box(37.5, 2, 56.5, 19, "Reliability label", r"$\bar{p}_t$ = mean of the six" + "\n5-min settled prices\n"
        + r"$Y_t = 1[\,|f(w_t) - \bar{p}_t| > 300\,]$" + "\n(AUD/MWh)", role="label")
E = box(78, 2, 99.5, 19, "Evaluation", "AUC, AP (detection);\nMWh into over-forecast\nintervals (exposure);\nnet revenue after\ncharging and degradation", role="set")

# ---- solid arrows (decision time) ----
arrow((A["r"], 46), (C["l"], 46))
arrow((C["r"], 46), (D["l"], 46))
arrow((D["r"], 46), (M["l"], 46))
arrow((M["r"], 48.5), (P["l"], 48.5))
arrow((P["cx"], P["b"]), (P["cx"], Bt["t"]))

# ---- dashed arrows (after settlement) ----
arrow((B["r"], 10.5), (L["l"], 10.5), dashed=True)
arrow((C["cx"], C["b"]), (L["l"] + 3, L["t"]), dashed=True)
arrow((L["r"] - 2, L["t"]), (M["cx"], M["b"]), dashed=True)
ax.text(66.5, 29.0, "training only\n(fit period)", ha="left", va="center", fontsize=6.8, style="italic", color=PAL["ink2"])
arrow((L["r"], 10.5), (E["l"], 10.5), dashed=True)
arrow((Bt["cx"], Bt["b"]), (Bt["cx"], E["t"]), dashed=True)

for ext in ("png", "svg", "pdf"):
    fig.savefig(FIG / f"fig_2.{ext}", bbox_inches="tight", facecolor="white")
cap = ("Fig. 2. FRI pipeline, run separately for each of the five NEM regions. Solid arrows carry information available "
       "at decision time; dashed arrows carry settled prices, used only to build the label for model fitting and to "
       f"evaluate the agent. θ = {THETA:.6f} was chosen on the validation period.")
(FIG / "fig_2_caption.txt").write_text(cap + "\n")
print("Saved fig_2.png/.svg/.pdf and fig_2_caption.txt to", FIG)
