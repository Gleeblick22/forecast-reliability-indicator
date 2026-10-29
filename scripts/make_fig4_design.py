"""make_fig4_design.py (Step D): Fig. 4 study design: research questions, the hypotheses that test them, and the data each uses.
Redrawn from the v1.1 Fig. 4 (same gate structure and names); contains no results. PNG (300 dpi), SVG, PDF."""
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.patches import Polygon, FancyBboxPatch

try:
    from config.settings import TABLES_DIR
    FIG = TABLES_DIR.parent / "figures"
except ImportError:
    FIG = Path("figures")
FIG.mkdir(parents=True, exist_ok=True)
plt.rcParams.update({"font.family": "sans-serif", "font.sans-serif": ["Arial", "Liberation Sans", "Helvetica", "DejaVu Sans"],
                     "mathtext.fontset": "dejavusans", "savefig.dpi": 300, "pdf.fonttype": 42, "svg.fonttype": "none"})
print("Font used:", Path(font_manager.findfont(font_manager.FontProperties(family=["sans-serif"]))).name)

INK, MUTED, LINE, PANEL = "#1F2933", "#52606D", "#9AA5B1", "#F5F7FA"
HEAD, HEAD4 = "#1F3A5F", "#0F766E"
fig, ax = plt.subplots(figsize=(7.16, 4.8))
ax.set_xlim(0, 100); ax.set_ylim(-4, 66); ax.axis("off")
RH = 3.4


def rbox(x0, y0, x1, y1, fc, ec, lw=0.7, r=0.9, ls="-", z=2):
    ax.add_patch(FancyBboxPatch((x0, y0), x1 - x0, y1 - y0, boxstyle=f"round,pad=0,rounding_size={r}",
                                facecolor=fc, edgecolor=ec, lw=lw, ls=ls, zorder=z))


def rq(x0, x1, ytop, title, rows, head=HEAD):
    n = len(rows)
    rbox(x0, ytop - 4.2 - n * RH - 0.6, x1, ytop, "white", LINE, lw=0.7)
    rbox(x0, ytop - 4.2, x1, ytop, head, head, r=0.9, z=3)
    ax.text((x0 + x1) / 2, ytop - 2.1, title, ha="center", va="center", fontsize=7, color="white", fontweight="bold", zorder=4)
    y = ytop - 4.2 - 0.3
    for k, (lab, out) in enumerate(rows):
        yc = y - RH / 2
        if k:
            ax.plot([x0 + 0.8, x1 - 0.8], [y, y], color="#E4E7EB", lw=0.6, zorder=3)
        code, _, rest = lab.partition("  ")
        ax.text(x0 + 1.0, yc, code, ha="left", va="center", fontsize=6.3, color=head, fontweight="bold", zorder=4)
        ax.text(x0 + (4.6 if len(code) <= 2 else 8.2), yc, rest, ha="left", va="center", fontsize=6.1, color=INK, zorder=4)
        ax.text(x1 - 0.9, yc, out, ha="right", va="center", fontsize=5.6, color=MUTED, style="italic", zorder=4)
        y -= RH
    return dict(l=x0, r=x1, t=ytop, b=y - 0.3, cx=(x0 + x1) / 2)


def diamond(cx, cy, w, h, text):
    ax.add_patch(Polygon([(cx - w / 2, cy), (cx, cy + h / 2), (cx + w / 2, cy), (cx, cy - h / 2)], closed=True,
                         facecolor=PANEL, edgecolor=LINE, lw=0.8, joinstyle="round", zorder=2))
    ax.text(cx, cy, text, ha="center", va="center", fontsize=6.1, color=INK, linespacing=1.2, zorder=3)
    return dict(l=cx - w / 2, r=cx + w / 2, t=cy + h / 2, b=cy - h / 2, cx=cx, cy=cy)


def outbox(x0, x1, y0, y1, text, kind):
    fg, bg = {"good": ("#1E6B34", "#E3F2E7"), "rep": (HEAD4, "#E0F2F1"), "lim": ("#52606D", "#EEF1F4")}[kind]
    rbox(x0, y0, x1, y1, bg, fg, lw=0.8, ls=(0, (3, 2)) if kind == "lim" else "-")
    ax.text((x0 + x1) / 2, (y0 + y1) / 2, text, ha="center", va="center", fontsize=6.1, color=INK, linespacing=1.25, zorder=4)
    return dict(l=x0, r=x1, t=y1, b=y0, cx=(x0 + x1) / 2, cy=(y0 + y1) / 2)


def path(pts, head=True):
    xs, ys = zip(*pts)
    ax.plot(xs, ys, color="#7B8794", lw=0.9, solid_capstyle="round", zorder=1)
    if head:
        ax.annotate("", xy=pts[-1], xytext=pts[-2], arrowprops=dict(arrowstyle="-|>", lw=0.9, color="#7B8794", mutation_scale=7), zorder=4)


def tag(x, y, text, kind="yes"):
    bg = {"yes": "#1E6B34", "lim": "#52606D"}[kind]
    ax.text(x, y, text, ha="center", va="center", fontsize=5.4, fontweight="bold", color="white", zorder=6,
            bbox=dict(boxstyle="round,pad=0.3,rounding_size=0.6", fc=bg, ec="none"))


A = rq(1, 29, 65, "NEM Signal Failures (RQ1)",
       [("H1  Error amplification", "error data"), ("H2  Error masking", "error data"), ("H3  Horizon difference", "error data"),
        ("R1  Against settled price", "test 2")])
B = rq(36, 64, 65, "FRI Detection (RQ2)",
       [("H4  Classifier accuracy", "test 1"), ("R2  Detection on new data", "test 2"),
        ("R4  Versus raw volatility", "test 2"), ("R5  60-min decision lead", "test 2")])
C = rq(71, 99, 65, "Battery Dispatch Value (RQ3)",
       [("H5  Silent failures", "test 1"), ("H6  Dispatch vs. score", "test 1"), ("H7  Revenue", "test 1"),
        ("R3  Energy at risk", "test 2"), ("R6  Degradation curve", "test 2")])
dA = diamond(A["cx"], 40, 22, 11, "Is the problem real\nand learnable?")
dB = diamond(B["cx"], 40, 22, 11, "Can FRI detect it\nbefore dispatch?")
dC = diamond(C["cx"], 38, 22, 9, "Does it add value\nin dispatch?")
for X, d in ((A, dA), (B, dB), (C, dC)):
    path([(X["cx"], X["b"]), (X["cx"], d["t"])])
path([(dA["r"], dA["cy"]), (32.5, dA["cy"]), (32.5, 62.9), (B["l"], 62.9)]); tag(32.5, 50, "YES")
path([(dB["r"], dB["cy"]), (67.5, dB["cy"]), (67.5, 62.9), (C["l"], 62.9)]); tag(67.5, 50, "YES")
oY = outbox(68.5, 84, 21.8, 27.8, "Energy committed\nto over-forecasts", "good")
oN = outbox(85.5, 99.7, 21.8, 27.8, "Revenue and\ndegradation cost", "lim")
path([(C["cx"], dC["b"]), (C["cx"], 32.2)], head=False)
path([(C["cx"], 32.2), (oY["cx"], 32.2), (oY["cx"], oY["t"])]); tag(oY["cx"], 30.0, "RISK")
path([(C["cx"], 32.2), (oN["cx"], 32.2), (oN["cx"], oN["t"])]); tag(oN["cx"], 30.0, "REVENUE", "lim")

D = rq(35, 65, 21.5, "Replication and Transfer (RQ4)",
       [("R1–R6  registered before 2023–25 data", ""), ("Code  model, θ and code frozen", ""),
        ("H8  Transfer (SA1, NZ, GB)", "transfer data")], head=HEAD4)
path([(oY["cx"], oY["b"]), (oY["cx"], 19.4), (D["r"], 19.4)])
path([(oN["cx"], oN["b"]), (oN["cx"], 19.4), (oY["cx"], 19.4)], head=False)
dD = diamond(D["cx"], 0.3, 22, 8.4, "Do results hold\non new data?")
path([(D["cx"], D["b"]), (D["cx"], dD["t"])])
oD1 = outbox(6, 26, -2.4, 3.6, "Main results:\nSections IV.A–IV.C", "rep")
oD2 = outbox(74, 99.5, -2.4, 3.6, "Tests not supported or\nnot re-run: Section IV.D", "lim")
path([(dD["l"], dD["cy"]), (oD1["r"], dD["cy"])]); tag((dD["l"] + oD1["r"]) / 2, dD["cy"] + 2.0, "YES")
path([(dD["r"], dD["cy"]), (oD2["l"], dD["cy"])]); tag((dD["r"] + oD2["l"]) / 2, dD["cy"] + 2.0, "LIMITS", "lim")

for ext in ("png", "svg", "pdf"):
    fig.savefig(FIG / f"fig_4_design.{ext}", bbox_inches="tight", facecolor="white")
cap = ("Fig. 4. Study design: the four research questions, the hypotheses that test each one and the part of the data each "
       "uses (Table I). H1–H8 were registered before the original analysis; R1–R6 were registered, with the model, threshold and "
       "code frozen, before the test-2 data (2023–2025) were downloaded. Outcomes are reported in Table III and Section IV.")
(FIG / "fig_4_design_caption.txt").write_text(cap + "\n")
print("Saved fig_4_design.png/.svg/.pdf and caption to", FIG)
