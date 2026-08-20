"""
figure_h7_revenue_c.py — Fig 10c: Power analysis full width.
Panel (c): Power % with vertical gap line
Panel (d): N comparison log scale, small annotation top right
"""

import os, sys
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import numpy as np
from config.settings import FIGURES_DIR
from config.logging_config import get_logger

logger = get_logger("figure_h7_revenue_c")

POWER_ACHIEVED = 5.27
POWER_REQUIRED = 80.0
N_ACTUAL       = 142
N_REQUIRED     = 47090
COHEN_D        = 0.0183
SF_BASE        = 54
SF_OVL         = 3
GAP_PCT        = POWER_REQUIRED - POWER_ACHIEVED

COLOR_NEG  = "#D55E00"
COLOR_POS  = "#009E73"
BLACK      = "#222222"
PURPLE     = "#534AB7"

STYLE = {
    "font.family":        "Latin Modern Roman",
    "font.size":          6,
    "axes.labelsize":     7.5,
    "xtick.labelsize":    6.5,
    "ytick.labelsize":    6.5,
    "figure.dpi":         1000,
    "savefig.dpi":        1000,
    "savefig.bbox":       "tight",
    "savefig.pad_inches": 0.04,
    "axes.facecolor":     "white",
    "figure.facecolor":   "white",
    "axes.spines.top":    False,
    "axes.spines.right":  False,
    "axes.grid":          True,
    "grid.color":         "#E8E8E8",
    "grid.linestyle":     "-",
    "grid.linewidth":     0.5,
    "axes.axisbelow":     True,
    "axes.linewidth":     0.6,
}


def build_panel_c(ax):
    cats   = ["Achieved\npower", "Required\npower"]
    vals   = [POWER_ACHIEVED, POWER_REQUIRED]
    colors = [COLOR_NEG, COLOR_POS]
    x      = np.arange(len(cats))

    ax.bar(x, vals, width=0.50,
           color=colors, alpha=0.9,
           edgecolor="white", linewidth=0.3, zorder=3)

    # Value labels
    for xi, v, col in zip(x, vals, colors):
        ax.text(xi, v + 1.0, f"{v:.2f}%",
                ha="center", va="bottom",
                fontsize=8, color=col,
                fontweight="bold", zorder=5)

    # Single vertical double-headed arrow between bars
    ax.annotate("",
                xy=(0.5, POWER_REQUIRED),
                xytext=(0.5, POWER_ACHIEVED),
                arrowprops=dict(arrowstyle="<->",
                                color=PURPLE, lw=1.2,
                                mutation_scale=10))

    # Gap label next to vertical line
    ax.text(0.62, (POWER_ACHIEVED + POWER_REQUIRED)/2,
            f"{GAP_PCT:.2f}%\ngap",
            ha="left", va="center",
            fontsize=6.5, color=PURPLE,
            fontweight="bold", zorder=6)

    ax.set_xticks(x)
    ax.set_xticklabels(cats, fontsize=7,
                       color=BLACK, fontweight="bold")
    ax.set_ylabel("Statistical power (%)",
                  fontsize=7.5, color=BLACK, fontweight="bold")
    ax.set_ylim(0, 95)
    ax.set_xlim(-0.6, 1.8)
    ax.grid(axis="x", visible=False)
    for label in ax.get_yticklabels():
        label.set_fontweight("bold")

    ax.set_title("(a)  Statistical power: achieved vs required",
                 fontsize=8, fontweight="bold",
                 loc="left", pad=7, color=BLACK)


def build_panel_d(ax):
    cats   = ["Actual N\n(extreme events)", "Required N\n(for 80% power)"]
    vals   = [N_ACTUAL, N_REQUIRED]
    colors = [COLOR_NEG, COLOR_POS]
    labels = [f"{N_ACTUAL:,}", f"{N_REQUIRED:,}"]
    x      = np.arange(len(cats))

    ax.bar(x, vals, width=0.50,
           color=colors, alpha=0.9,
           edgecolor="white", linewidth=0.3, zorder=3)

    # Value labels above bars
    for xi, v, col, lbl in zip(x, vals, colors, labels):
        ax.text(xi, v * 1.2, lbl,
                ha="center", va="bottom",
                fontsize=7.5, color=col,
                fontweight="bold", zorder=5)

    # Small annotation top right — key stats only
    ax.text(0.98, 0.98,
            f"Gap: {N_REQUIRED//N_ACTUAL}×  |  Cohen d = {COHEN_D}\n"
            f"SF: {SF_BASE}→{SF_OVL} (−94.44%)  |  Underpowered",
            transform=ax.transAxes,
            fontsize=5.5, ha="right", va="top",
            color=PURPLE, fontweight="bold",
            bbox=dict(boxstyle="round,pad=0.30",
                      facecolor="white",
                      edgecolor=PURPLE,
                      linewidth=0.8, alpha=0.95),
            zorder=10)

    ax.set_xticks(x)
    ax.set_xticklabels(cats, fontsize=7,
                       color=BLACK, fontweight="bold")
    ax.set_ylabel("Extreme events (count, log scale)",
                  fontsize=7.5, color=BLACK, fontweight="bold")
    ax.set_yscale("log")
    ax.set_ylim(10, 500000)
    ax.grid(axis="x", visible=False)
    for label in ax.get_yticklabels():
        label.set_fontweight("bold")

    ax.set_title("(b)  Sample size: actual vs required",
                 fontsize=8, fontweight="bold",
                 loc="left", pad=7, color=BLACK)


def build_figure():
    plt.rcParams.update(STYLE)
    fig = plt.figure(figsize=(6.90, 3.20))
    gs  = gridspec.GridSpec(1, 2, figure=fig, wspace=0.32,
                            left=0.09, right=0.97,
                            top=0.88, bottom=0.18)
    ax1 = fig.add_subplot(gs[0])
    ax2 = fig.add_subplot(gs[1])
    build_panel_c(ax1)
    build_panel_d(ax2)
    return fig


def save_figure(fig):
    os.makedirs(FIGURES_DIR, exist_ok=True)
    png = str(FIGURES_DIR / "fig14_h7_mcnemar_power.png")
    pdf = str(FIGURES_DIR / "fig14_h7_mcnemar_power.pdf")
    fig.savefig(png, dpi=1000, bbox_inches="tight")
    fig.savefig(pdf, dpi=1000, bbox_inches="tight", format="pdf")
    plt.close()


def main():
    fig = build_figure()
    save_figure(fig)
    sys.exit(0)


if __name__ == "__main__":
    main()
