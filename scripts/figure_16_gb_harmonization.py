"""
figure_16_gb_harmonization.py
================================
Fig 17: GB transfer performance before and after label
harmonization, full and nine-feature models, with NEM
reference line.
PRODUCTION VERSION -- master theme compliant.

Verified data (c3_34/c3_35 harmonization results, Table 11):
  Full model:       original F1=0.2119, harmonized F1=0.6658
  9-feature model:  original F1=0.3849, harmonized F1=0.3162
  NEM reference:    F1=0.6207

Output:
  results/figures/fig16_gb_harmonization.png
  results/figures/fig16_gb_harmonization.pdf

Project: forecast-reliability-indicator (FRI)
OSF:      10.17605/OSF.IO/Z89HD
"""

import os
import sys
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np
from config.settings import FIGURES_DIR
from config.logging_config import get_logger

logger = get_logger("figure_16_gb_harmonization")

BLUE       = "#0072B2"
GREEN      = "#009E73"
VERMILLION = "#D55E00"
GREY_LIGHT = "#CCCCCC"
BLACK      = "#222222"
MUTED      = "#666666"
C_NEM      = "#534AB7"

NEM_F1 = 0.8898

MODELS = ["Original threshold\n(99.06th pct)",
          "Harmonized threshold\n(87.44th pct)"]
F1_VALUES = [0.0778, 0.0206]
AUC_VALUES = [0.9800, 0.8252]
STATUS    = ["Fail", "Fail"]
COLORS    = [VERMILLION, VERMILLION]

STYLE = {
    "font.family":        "Latin Modern Roman",
    "font.size":          6,
    "axes.labelsize":     7.5,
    "xtick.labelsize":    6.5,
    "ytick.labelsize":    7,
    "legend.fontsize":    5.5,
    "figure.dpi":         1200,
    "savefig.dpi":        1200,
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


def build_figure():
    logger.info("Building figure...")
    plt.rcParams.update(STYLE)
    fig, ax = plt.subplots(figsize=(7.20, 4.20))

    x = np.arange(len(MODELS))
    bars = ax.bar(x, F1_VALUES, width=0.55, color=COLORS, alpha=0.9,
                  edgecolor="white", linewidth=0.3, zorder=3)

    for xi, v, a, s in zip(x, F1_VALUES, AUC_VALUES, STATUS):
        ax.text(xi, v + 0.02, f"F1={v:.4f}\nAUC={a:.4f}\n({s})", ha="center",
                va="bottom", fontsize=6.5, fontweight="bold",
                color=BLACK, zorder=5)

    # NEM reference line
    ax.axhline(NEM_F1, color=C_NEM, ls="--", lw=1.0, alpha=0.8, zorder=4)
    ax.text(1.4, NEM_F1 + 0.015, f"NEM reference F1 = {NEM_F1:.4f}",
            fontsize=6, color=C_NEM, fontweight="bold",
            ha="right", va="bottom", zorder=5)

    # Tolerance band (+/- 0.15)
    ax.axhspan(NEM_F1 - 0.15, NEM_F1 + 0.15, color=C_NEM, alpha=0.06, zorder=1)
    ax.text(1.4, NEM_F1 - 0.15 - 0.025, "\u00b10.15 tolerance band",
            fontsize=5.5, color=C_NEM, style="italic",
            ha="right", va="top", zorder=2)


    ax.text(0.5, 0.30, "Harmonization does not rescue GB\nunder the relabeled classifier", fontsize=6.5, color=BLACK, fontweight="bold", ha="center", va="bottom", zorder=5)
    ax.set_xticks(x)
    ax.set_xticklabels(MODELS, fontsize=6.5, color=BLACK)
    ax.set_ylabel("GB test F1", fontsize=7.5, color=BLACK)
    ax.set_ylim(0, 0.85)
    ax.grid(axis="x", visible=False)

    ax.set_title("GB transfer performance: original vs. harmonized label",
                fontsize=9, fontweight="bold", loc="left",
                color=BLACK, pad=10)

    return fig


def save_figure(fig):
    os.makedirs(FIGURES_DIR, exist_ok=True)
    png = str(FIGURES_DIR / "fig16_gb_harmonization.png")
    pdf = str(FIGURES_DIR / "fig16_gb_harmonization.pdf")
    fig.savefig(png, dpi=1200, bbox_inches="tight")
    logger.info(f"Saved PNG: {png}")
    fig.savefig(pdf, dpi=1200, bbox_inches="tight", format="pdf")
    logger.info(f"Saved PDF: {pdf}")
    plt.close()


def main():
    logger.info("=" * 60)
    logger.info("figure_16_gb_harmonization.py -- PRODUCTION")
    logger.info("=" * 60)
    fig = build_figure()
    save_figure(fig)
    logger.info("figure_16_gb_harmonization.py complete")
    sys.exit(0)


if __name__ == "__main__":
    main()
