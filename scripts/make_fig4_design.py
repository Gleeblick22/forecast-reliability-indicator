"""make_fig4_design.py: Fig. 4 study design: the research questions and the hypotheses that test them.
Contains no results; every label matches Table III; the data parts are named in the caption (Table I). PNG (300 dpi), SVG, PDF."""
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.patches import Polygon, FancyBboxPatch

FIG = Path(__file__).resolve().parents[1] / "results" / "figures"   # always the repo results/figures folder
FIG.mkdir(parents=True, exist_ok=True)
import sys; sys.path.insert(0, str(Path(__file__).resolve().parent))
import fri_style as FS
FS.use()
print("Font used:", Path(font_manager.findfont(font_manager.FontProperties(family=["serif"]))).name)

INK, MUTED, LINE, PANEL = FS.C["ink"], FS.C["ink2"], FS.C["box_line"], FS.C["box_fill"]
HEAD, HEAD4 = FS.C["box_head"], FS.C["box_head_rep"]                 # RQ1-3 header; RQ4 (prospective) header
STATUS = {"supported": ("#1E6B34", "#E3F2E7"), "not supported": ("#A61B1B", "#FBE7E7"),
          "not testable": ("#52606D", "#EEF1F4"), "descriptive": ("#52606D", "#EEF1F4"), "": (MUTED, "white")}

fig, ax = plt.subplots(figsize=(7.16, 4.55))
ax.set_xlim(0, 100); ax.set_ylim(-4.5, 66); ax.axis("off")
RH = 3.4


def rbox(x0, y0, x1, y1, fc, ec, lw=0.7, r=0.9, ls="-", z=2):
    ax.add_patch(FancyBboxPatch((x0, y0), x1 - x0, y1 - y0, boxstyle=f"round,pad=0,rounding_size={r}",
                                facecolor=fc, edgecolor=ec, lw=lw, ls=ls, zorder=z))


def badge(x_right, y, text):
    fg, bg = STATUS[text]
    if not text:
        return
    ax.text(x_right, y, text, ha="right", va="center", fontsize=5.4, color=fg, fontweight="bold", zorder=5,
            bbox=dict(boxstyle="round,pad=0.25,rounding_size=0.5", fc=bg, ec="none"))


def rq(x0, x1, ytop, title, rows, head=HEAD, extra=None):
    n = len(rows)
    rbox(x0, ytop - 4.2 - n * RH - 0.6, x1, ytop, "white", LINE, lw=0.7)
    rbox(x0, ytop - 4.2, x1, ytop, head, head, r=0.9, z=3)
    ax.text((x0 + x1) / 2, ytop - 2.1, title, ha="center", va="center", fontsize=6.4, color="white", fontweight="bold", zorder=4)
    y = ytop - 4.2 - 0.3
    off = 8.2 if any(len(l.partition("  ")[0]) > 2 for l, _ in rows) else 4.6   # one text column per box
    for k, (lab, out) in enumerate(rows):
        yc = y - RH / 2
        if k:
            ax.plot([x0 + 0.8, x1 - 0.8], [y, y], color="#E4E7EB", lw=0.6, zorder=3)
        code, _, rest = lab.partition("  ")
        ax.text(x0 + 1.0, yc, code, ha="left", va="center", fontsize=6.3, color=head, fontweight="bold", zorder=4)
        ax.text(x0 + off, yc, rest, ha="left", va="center", fontsize=6.1, color=INK, zorder=4)
        if out in STATUS:
            badge(x1 - 0.9, yc, out)
        else:
            ax.text(x1 - 0.9, yc, out, ha="right", va="center", fontsize=5.6, color=MUTED, style="italic", zorder=4)
        y -= RH
    return dict(l=x0, r=x1, t=ytop, b=y - 0.3, cx=(x0 + x1) / 2)


def diamond(cx, cy, w, h, text):
    ax.add_patch(Polygon([(cx - w / 2, cy), (cx, cy + h / 2), (cx + w / 2, cy), (cx, cy - h / 2)], closed=True,
                         facecolor=PANEL, edgecolor=LINE, lw=0.8, joinstyle="round", zorder=2))
    ax.text(cx, cy, text, ha="center", va="center", fontsize=6.1, color=INK, linespacing=1.2, zorder=3)
    return dict(l=cx - w / 2, r=cx + w / 2, t=cy + h / 2, b=cy - h / 2, cx=cx, cy=cy)


def outbox(x0, x1, y0, y1, text, kind):
    fg, bg = {"good": ("#1E6B34", "#E3F2E7"), "bad": ("#A61B1B", "#FBE7E7"), "rep": (HEAD4, "#E0F2F1"), "lim": ("#52606D", "#EEF1F4")}[kind]
    rbox(x0, y0, x1, y1, bg, fg, lw=0.8, ls=(0, (3, 2)) if kind in ("bad", "lim") else "-")
    ax.text((x0 + x1) / 2, (y0 + y1) / 2, text, ha="center", va="center", fontsize=6.1, color=INK, linespacing=1.25, zorder=4)
    return dict(l=x0, r=x1, t=y1, b=y0, cx=(x0 + x1) / 2, cy=(y0 + y1) / 2)


def path(pts, head=True):
    xs, ys = zip(*pts)
    ax.plot(xs, ys, color="#7B8794", lw=0.9, solid_capstyle="round", zorder=1)
    if head:
        ax.annotate("", xy=pts[-1], xytext=pts[-2], arrowprops=dict(arrowstyle="-|>", lw=0.9, color="#7B8794", mutation_scale=7), zorder=4)


def tag(x, y, text, kind="yes"):
    fg, bg = {"yes": ("white", "#1E6B34"), "no": ("white", "#A61B1B"), "lim": ("white", "#52606D")}[kind]
    ax.text(x, y, text, ha="center", va="center", fontsize=5.4, fontweight="bold", color=fg, zorder=6,
            bbox=dict(boxstyle="round,pad=0.3,rounding_size=0.6", fc=bg, ec="none"))


# ---------- row 1 ----------
A = rq(1, 29, 65, "NEM Signal Failures (RQ1)",
       [("H1  Error amplification", ""), ("H2  Error masking", ""), ("H3  Horizon difference", ""),
        ("R1  Against settled price", "")])
B = rq(36, 64, 65, "FRI Detection (RQ2)",
       [("H4  Classifier accuracy", ""), ("R2  Detection on new data", ""),
        ("R4  Versus raw volatility", ""), ("R5  60-min decision lead", "")])
C = rq(71, 99, 65, "Battery Dispatch Value (RQ3)",
       [("H5  Silent failures", ""), ("H6  Dispatch vs. score", ""), ("H7  Revenue", ""),
        ("R3  Energy at risk", ""), ("R6  Degradation curve", "")])
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

# ---------- row 2 ----------
D = rq(33, 67, 21.5, "Replication and Transfer (RQ4)",
       [("R1–R6  replication of RQ1–RQ3 on test 2", ""), ("Fixed  model, θ and code before test 2", ""), ("H8  Transfer (SA1, NZ, GB)", "")], head=HEAD4)
path([(oY["cx"], oY["b"]), (oY["cx"], 19.4), (D["r"], 19.4)])
path([(oN["cx"], oN["b"]), (oN["cx"], 19.4), (oY["cx"], 19.4)], head=False)

# ---------- registration timeline (mirrors Section III.G, parts 1-3) ----------
ax.plot([1, 99], [3.6, 3.6], color="#E4E7EB", lw=0.6)
steps = [(1, 24, "1. 28 April 2026", "H1–H8 registered", HEAD, "#E3EDFA"),
         (27, 50, "2. 2021–22 analysis", "errors corrected", MUTED, "#EEF1F4"),
         (53, 76, "3. 28 October 2026", "R1–R6 registered", HEAD4, "#E0F2F1"),
         (79, 99, "4. Test 2", "2023–25 data downloaded", "#1E6B34", "#E3F2E7")]
for k, (x0, x1, top, bot, col, fill) in enumerate(steps):
    rbox(x0, -3.8, x1, 2.4, fill, col, lw=0.8)
    ax.text((x0 + x1) / 2, 0.7, top, ha="center", va="center", fontsize=6.1, color=col, fontweight="bold")
    ax.text((x0 + x1) / 2, -1.9, bot, ha="center", va="center", fontsize=5.8, color=INK)
    if k: path([(steps[k - 1][1], -0.7), (x0, -0.7)])

for ext in ("png", "svg", "pdf"):
    fig.savefig(FIG / f"fig_4_design.{ext}", bbox_inches="tight", facecolor="white", dpi=600)
cap = ("Fig. 4. Study design: the four research questions and the hypotheses that test each one. H1–H3 use the NEM error "
       "dataset, H4–H7 test 1 (2022), R1–R6 test 2 (2023–25) and H8 the transfer data (Table I). R1–R6 were registered, with "
       "the model, threshold and code fixed, before the 2023–25 data were downloaded. The lower strip shows the order of registration (Section III.G). Outcomes are reported in Section IV.")
(FIG / "fig_4_design_caption.txt").write_text(cap + "\n")
print("Saved fig_4_design.png/.svg/.pdf and caption to", FIG)
