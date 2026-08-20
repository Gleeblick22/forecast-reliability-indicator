"""
figure_h7_revenue_b.py
======================
Fig 10b: % change horizontal bar chart with +15% threshold line.
Three categories: Overall -3.17%, Extreme -13.58%, Normal -2.79%.
Threshold line at +15% (pre-registered H7 criterion).

Verified locked values from c3_05_h7_revenue_comparison_results.csv
"""

import os
import sys
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
from config.settings import FIGURES_DIR
from config.logging_config import get_logger

logger = get_logger("figure_h7_revenue_b")

# Verified locked values
DATA = [
    {"label": "Overall",        "change": -3.1696, "color": "#0072B2"},
    {"label": "Extreme\nregime","change": -13.58,  "color": "#D55E00"},
    {"label": "Normal\nregime", "change": -2.79,   "color": "#009E73"},
]

H7_THRESHOLD = 15.0   # +15% required improvement (pre-registered)

COLOR_NEG  = "#D55E00"
COLOR_POS  = "#009E73"
BLACK      = "#222222"
MUTED      = "#666666"
PURPLE     = "#534AB7"

STYLE = {
    "font.family":        "Latin Modern Roman",
    "font.size":          6,
    "figure.dpi":         1000,
    "savefig.dpi":        1000,
    "savefig.bbox":       "tight",
    "savefig.pad_inches": 0.04,
    "axes.facecolor":     "white",
    "figure.facecolor":   "white",
    "axes.spines.top":    False,
    "axes.spines.right":  False,
    "axes.spines.left":   False,
    "axes.grid":          True,
    "grid.color":         "#E8E8E8",
    "grid.linestyle":     "-",
    "grid.linewidth":     0.5,
    "axes.axisbelow":     True,
    "axes.linewidth":     0.6,
    "xtick.major.size":   3,
    "ytick.major.size":   0,
}


def build_figure():
    plt.rcParams.update(STYLE)

    fig, ax = plt.subplots(figsize=(6.50, 3.00))
    fig.subplots_adjust(left=0.18, right=0.85,
                        top=0.82, bottom=0.18)

    n     = len(DATA)
    y     = np.arange(n)
    bar_h = 0.40

    for i, d in enumerate(DATA):
        change = d["change"]
        col    = d["color"]
        sign   = "+" if change > 0 else ""

        # Horizontal bar from 0 to change %
        ax.barh(y[i], change, height=bar_h,
                color=col, alpha=0.85,
                edgecolor="white", linewidth=0.3,
                zorder=3)

        # Value label at bar end
        offset = -0.5 if change < 0 else 0.5
        ax.text(change + offset, y[i],
                f"{sign}{change:.2f}%",
                va="center",
                ha="right" if change < 0 else "left",
                fontsize=7, color=col,
                fontweight="bold", zorder=5,
                clip_on=False)

    # Zero reference line
    ax.axvline(0, color=BLACK, lw=0.8, zorder=4)

    # H7 threshold line at +15%
    ax.axvline(H7_THRESHOLD, color=PURPLE,
               ls="--", lw=1.2, alpha=0.9, zorder=5)
    ax.text(H7_THRESHOLD + 0.3, n - 0.45,
            f"+{H7_THRESHOLD:.0f}%\nH7 threshold\n(required)",
            va="top", ha="left",
            fontsize=5.5, color=PURPLE,
            fontweight="bold", zorder=6)

    # Gap annotation — how far short of threshold
    ax.annotate("",
                xy=(H7_THRESHOLD, 2),
                xytext=(-3.17, 2),
                arrowprops=dict(arrowstyle="<->",
                                color=PURPLE, lw=0.8))
    ax.text((H7_THRESHOLD + (-3.17))/2, 2.22,
            "Gap: 18.17%",
            ha="center", va="bottom",
            fontsize=5.5, color=PURPLE,
            fontweight="bold", zorder=6)

    # Y axis labels
    ax.set_yticks(y)
    ax.set_yticklabels([d["label"] for d in DATA],
                       fontsize=7.5, color=BLACK,
                       fontweight="bold")

    # X axis
    ax.set_xlabel("Revenue change vs baseline (%)",
                  fontsize=7.5, color=BLACK,
                  fontweight="bold", labelpad=4)
    ax.set_xlim(-20, 22)
    ax.tick_params(axis="x", colors=BLACK)
    for label in ax.get_xticklabels():
        label.set_fontweight("bold")
    ax.spines["bottom"].set_color("#CCCCCC")
    ax.grid(axis="y", visible=False)



    # Title
    ax.text(0.0, 1.20,
            "Revenue change by regime vs H7 threshold",
            transform=ax.transAxes, fontsize=8,
            fontweight="bold", va="bottom",
            ha="left", color=BLACK)

    # Legend single line below title
    handles = [
        mpatches.Patch(color="#0072B2", label="Overall"),
        mpatches.Patch(color="#D55E00", label="Extreme regime"),
        mpatches.Patch(color="#009E73", label="Normal regime"),
        mpatches.Patch(color=PURPLE,    label="H7 threshold (+15%)"),
    ]
    leg = ax.legend(handles=handles,
                    loc="upper left",
                    bbox_to_anchor=(0.0, 1.14),
                    ncol=4, fontsize=6,
                    frameon=True, framealpha=0.95,
                    edgecolor="#CCCCCC",
                    handlelength=0.8,
                    handletextpad=0.3,
                    borderpad=0.3,
                    columnspacing=0.8,
                    fancybox=False)
    leg.get_frame().set_linewidth(0.5)

    return fig


def save_figure(fig):
    os.makedirs(FIGURES_DIR, exist_ok=True)
    png = str(FIGURES_DIR / "fig13_h7_revenue_by_regime.png")
    pdf = str(FIGURES_DIR / "fig13_h7_revenue_by_regime.pdf")
    fig.savefig(png, dpi=1000, bbox_inches="tight")
    logger.info(f"Saved: {png}")
    fig.savefig(pdf, dpi=1000, bbox_inches="tight", format="pdf")
    plt.close()


def main():
    logger.info("=" * 60)
    logger.info("figure_h7_revenue_b.py -- % change + threshold")
    logger.info("=" * 60)
    fig = build_figure()
    save_figure(fig)
    logger.info("figure_h7_revenue_b.py complete")
    sys.exit(0)


if __name__ == "__main__":
    main()
