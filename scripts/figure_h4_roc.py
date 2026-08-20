"""
figure_h4_roc.py
================
Publication figure for H4 hypothesis result (ROC curve).
PRODUCTION VERSION -- master theme compliant.

Verified data:
  h4_roc_curve.csv (385 points, fpr/tpr/threshold)
  h4_optimal_point.csv: operating point fpr=0.0029, tpr=0.6338 at thr=0.8462 row,
    but locked operating threshold is 0.8006 with TP=90 FP=58 FN=52 TN=14965
    -> plotted operating point computed from confusion matrix:
       FPR = 58/(58+14965) = 0.00386,  TPR = 90/(90+52) = 0.6338
  AUC = 0.9901, 95% CI [0.9855, 0.9927] (confidence_intervals.csv H4_AUC point
    differs slightly (0.9893) as bootstrap mean; manuscript uses 0.9901)

Single panel: ROC curve, chance diagonal, operating point annotation,
AUC annotation box.

Output:
  results/figures/fig08_h4_roc.png
  results/figures/fig08_h4_roc.pdf

Project: forecast-reliability-indicator (FRI)
OSF:     10.17605/OSF.IO/Z89HD
"""

import os
import sys
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
import pandas as pd
import numpy as np
from config.settings import FIGURES_DIR, TABLES_DIR
from config.logging_config import get_logger

logger = get_logger("figure_h4_roc")

BLUE       = "#0072B2"
VERMILLION = "#D55E00"
GREY_LIGHT = "#CCCCCC"
BLACK      = "#222222"
MUTED      = "#666666"

# Locked operating point (from h4_confusion_matrix.csv, threshold 0.8006)
OP_TP, OP_FP, OP_FN, OP_TN = 452, 17, 95, 14081
OP_FPR = OP_FP / (OP_FP + OP_TN)   # 0.00386
OP_TPR = OP_TP / (OP_TP + OP_FN)   # 0.6338
OP_THR = 0.856818
AUC      = 0.9666
AUC_CI   = (0.9557, 0.9765)
AP       = 0.8931   # Average precision (PR curve)
BASELINE = 0.0374   # Random classifier baseline = positive rate

STYLE = {
    "font.family":        "Latin Modern Roman",
    "font.size":          6,
    "axes.labelsize":     7.5,
    "xtick.labelsize":    6.5,
    "ytick.labelsize":    6.5,
    "legend.fontsize":    5.5,
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


def load_data():
    logger.info("Loading H4 ROC and PR curve data...")
    roc = pd.read_csv(TABLES_DIR / "c2_23_roc_curve_relabeled.csv")
    pr  = pd.read_csv(TABLES_DIR / "c2_23_pr_curve_relabeled.csv")
    logger.info(f"ROC points: {len(roc)}  PR points: {len(pr)}")
    logger.info(f"Operating point: FPR={OP_FPR:.5f} TPR={OP_TPR:.4f} thr={OP_THR}")
    return roc, pr


def build_figure(roc, pr):
    logger.info("Building figure (two panels: ROC + PR)...")
    plt.rcParams.update(STYLE)

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(6.90, 3.40))
    fig.subplots_adjust(left=0.09, right=0.97, top=0.97,
                        bottom=0.14, wspace=0.32)

    # ── PANEL (a) ROC curve ───────────────────────────────────────
    ax1.plot(roc["fpr"], roc["tpr"], color=BLUE, lw=1.2, zorder=4)

    # Chance diagonal
    ax1.plot([0, 1], [0, 1], color=MUTED, ls=":", lw=0.8,
             alpha=0.8, zorder=2)
    ax1.text(0.38, 0.46, "Chance (AUC=0.5)", fontsize=5.5,
             color=MUTED, style="italic", rotation=45,
             ha="left", va="bottom", zorder=3)

    # Operating point
    ax1.scatter([OP_FPR], [OP_TPR], s=40, color=VERMILLION,
                edgecolors="white", linewidth=0.5, zorder=6)
    ax1.annotate(
        f"Operating point\nFPR={OP_FPR:.4f}  TPR={OP_TPR:.3f}\n"
        f"TP=90  FP=58  FN=52",
        xy=(OP_FPR, OP_TPR),
        xytext=(0.04, 0.78),
        fontsize=5.5, color=VERMILLION,
        arrowprops=dict(arrowstyle="->", color=VERMILLION, lw=0.8,
                        connectionstyle="arc3,rad=-0.15"),
        bbox=dict(boxstyle="round,pad=0.30", facecolor="white",
                  edgecolor=VERMILLION, linewidth=0.5, alpha=0.95),
        zorder=10,
    )

    # AUC box
    ax1.text(
        0.97, 0.06,
        f"AUC = {AUC:.4f}\n95% CI [{AUC_CI[0]:.4f}, {AUC_CI[1]:.4f}]",
        transform=ax1.transAxes,
        fontsize=6, ha="right", va="bottom", color=BLUE,
        fontweight="bold",
        bbox=dict(boxstyle="round,pad=0.30", facecolor="white",
                  edgecolor=BLUE, linewidth=0.5, alpha=0.95),
        zorder=10,
    )

    ax1.set_xlim(0.0, 1.0)
    ax1.set_ylim(0.0, 1.0)
    ax1.set_xlabel("False positive rate", fontsize=7.5,
                   color=BLACK, fontweight="bold")
    ax1.set_ylabel("True positive rate", fontsize=7.5,
                   color=BLACK, fontweight="bold")
    ax1.text(0.0, 1.04, "(a)  ROC curve",
             transform=ax1.transAxes, fontsize=8,
             fontweight="bold", va="bottom", ha="left", color=BLACK)

    # ── PANEL (b) Precision-Recall curve ─────────────────────────
    ax2.plot(pr["recall"], pr["precision"], color=BLUE, lw=1.2, zorder=4)

    # Baseline (random classifier = positive rate)
    ax2.axhline(BASELINE, color=MUTED, ls=":", lw=0.8,
                alpha=0.8, zorder=2)
    ax2.text(0.02, BASELINE + 0.015, f"Baseline ({BASELINE:.3f})",
             fontsize=5.5, color=MUTED, style="italic",
             ha="left", va="bottom", zorder=3)

    # Operating point: precision=0.6081 recall=0.6338 at threshold 0.8006
    ax2.scatter([0.8263], [0.9638], s=40, color=VERMILLION,
                edgecolors="white", linewidth=0.5, zorder=6)
    ax2.annotate(
        f"Operating point\nPrec={0.9638:.3f}  Rec={0.8263:.3f}",
        xy=(0.8263, 0.9638),
        xytext=(0.15, 0.55),
        fontsize=5.5, color=VERMILLION,
        arrowprops=dict(arrowstyle="->", color=VERMILLION, lw=0.8,
                        connectionstyle="arc3,rad=0.2"),
        bbox=dict(boxstyle="round,pad=0.30", facecolor="white",
                  edgecolor=VERMILLION, linewidth=0.5, alpha=0.95),
        zorder=10,
    )

    # AP box
    ax2.text(
        0.97, 0.06,
        f"AP = {AP:.4f}",
        transform=ax2.transAxes,
        fontsize=6, ha="right", va="bottom", color=BLUE,
        fontweight="bold",
        bbox=dict(boxstyle="round,pad=0.30", facecolor="white",
                  edgecolor=BLUE, linewidth=0.5, alpha=0.95),
        zorder=10,
    )

    ax2.set_xlim(-0.02, 1.02)
    ax2.set_ylim(-0.02, 1.10)
    ax2.set_xlabel("Recall", fontsize=7.5,
                   color=BLACK, fontweight="bold")
    ax2.set_ylabel("Precision", fontsize=7.5,
                   color=BLACK, fontweight="bold")
    ax2.text(0.0, 1.04, "(b)  Precision-Recall curve",
             transform=ax2.transAxes, fontsize=8,
             fontweight="bold", va="bottom", ha="left", color=BLACK)

    logger.info("Figure complete")
    return fig


def save_figure(fig):
    os.makedirs(FIGURES_DIR, exist_ok=True)
    png = str(FIGURES_DIR / "fig08_h4_roc.png")
    pdf = str(FIGURES_DIR / "fig08_h4_roc.pdf")
    fig.savefig(png, dpi=1000, bbox_inches="tight")
    logger.info(f"Saved PNG: {png}")
    fig.savefig(pdf, dpi=1000, bbox_inches="tight", format="pdf")
    logger.info(f"Saved PDF: {pdf}")
    plt.close()


def main():
    logger.info("=" * 60)
    logger.info("figure_h4_roc.py -- PRODUCTION (master theme)")
    logger.info("=" * 60)
    roc, pr = load_data()
    fig = build_figure(roc, pr)
    save_figure(fig)
    logger.info("=" * 60)
    logger.info("figure_h4_roc.py complete")
    logger.info(f"Output: {FIGURES_DIR}/fig08_h4_roc.png/.pdf")
    logger.info("=" * 60)
    sys.exit(0)


if __name__ == "__main__":
    main()
