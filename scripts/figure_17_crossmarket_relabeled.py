"""
figure_16_crossmarket_relabeled.py
=====================================
Rebuild of Figure 16 (H8 cross-market) for the relabeled
classifier. Simplified to 5 contexts (NEM, SA1, NZ, GB-original,
GB-harmonized), since NZ North/South regional breakdown was not
recomputed for the relabeled classifier (Section 4.H reports
NZ overall only).

Verified data:
  NEM (reference): F1=0.8898, AUC=0.9666
  SA1: F1=0.8577, AUC=0.9673, PASS
  NZ: F1=0.0787, AUC=0.8399, FAIL
  GB original: F1=0.0778, AUC=0.9800, FAIL
  GB harmonized: F1=0.0206, AUC=0.8252, FAIL
  Tolerance: 0.15
"""
import os
import sys
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from config.settings import FIGURES_DIR
from config.logging_config import get_logger

logger = get_logger("figure_16_crossmarket_relabeled")

BLUE = "#0072B2"
GREEN = "#009E73"
VERMILLION = "#D55E00"
GREY_LIGHT = "#CCCCCC"
BLACK = "#222222"
MUTED = "#666666"
C_NEM = "#534AB7"

NEM_F1 = 0.8898
TOLERANCE = 0.15

CONTEXTS = ["SA1\n(cross-region)", "NZ EMI\n(cross-market)",
            "GB\n(original thr.)", "GB\n(harmonized thr.)"]
F1_VALUES = [0.8577, 0.0787, 0.0778, 0.0206]
AUC_VALUES = [0.9673, 0.8399, 0.9800, 0.8252]
STATUS = ["Pass", "Fail", "Fail", "Fail"]
COLORS = [GREEN, VERMILLION, VERMILLION, VERMILLION]

STYLE = {
    "font.family": "Latin Modern Roman", "font.size": 6,
    "axes.labelsize": 7.5, "xtick.labelsize": 6.5, "ytick.labelsize": 7,
    "legend.fontsize": 5.5, "figure.dpi": 1000, "savefig.dpi": 1000,
    "savefig.bbox": "tight", "savefig.pad_inches": 0.04,
    "axes.facecolor": "white", "figure.facecolor": "white",
    "axes.spines.top": False, "axes.spines.right": False,
    "axes.grid": True, "grid.color": "#E8E8E8", "grid.linestyle": "-",
    "grid.linewidth": 0.5, "axes.axisbelow": True, "axes.linewidth": 0.6,
}

def main():
    plt.rcParams.update(STYLE)
    fig, ax = plt.subplots(figsize=(7.60, 4.20))

    x = np.arange(len(CONTEXTS))
    ax.bar(x, F1_VALUES, width=0.55, color=COLORS, alpha=0.9,
           edgecolor="white", linewidth=0.3, zorder=3)

    for xi, f1, auc, s in zip(x, F1_VALUES, AUC_VALUES, STATUS):
        ax.text(xi, f1 + 0.02, f"F1={f1:.4f}\nAUC={auc:.4f}\n({s})",
                ha="center", va="bottom", fontsize=6.5, fontweight="bold",
                color=BLACK, zorder=5)

    ax.axhline(NEM_F1, color=C_NEM, ls="--", lw=1.0, alpha=0.8, zorder=4)
    ax.text(3.55, NEM_F1 + 0.015, f"NEM reference F1 = {NEM_F1:.4f}",
            fontsize=6, color=C_NEM, fontweight="bold", ha="right", va="bottom", zorder=5)

    ax.axhspan(max(0, NEM_F1 - TOLERANCE), min(1, NEM_F1 + TOLERANCE),
               color=C_NEM, alpha=0.06, zorder=1)
    ax.text(3.55, NEM_F1 - TOLERANCE - 0.03, "\u00b10.15 tolerance band",
            fontsize=5.5, color=C_NEM, style="italic", ha="right", va="top", zorder=2)

    ax.set_xticks(x)
    ax.set_xticklabels(CONTEXTS, fontsize=6.5, color=BLACK)
    ax.set_ylabel("Test F1 (relabeled classifier)", fontsize=7.5, color=BLACK)
    ax.set_ylim(0, 1.05)
    ax.grid(axis="x", visible=False)
    ax.set_title("Cross-market FRI performance, relabeled classifier",
                 fontsize=9, fontweight="bold", loc="left", color=BLACK, pad=10)

    os.makedirs(FIGURES_DIR, exist_ok=True)
    fig.savefig(FIGURES_DIR / "fig17_crossmarket.png", dpi=1000, bbox_inches="tight")
    fig.savefig(FIGURES_DIR / "fig17_crossmarket.pdf", dpi=1000, bbox_inches="tight")
    logger.info(f"Saved: {FIGURES_DIR}/fig17_crossmarket.png/.pdf")
    sys.exit(0)

if __name__ == "__main__":
    main()
