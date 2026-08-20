"""
figure_11_h6_correlation_relabeled.py
========================================
Rebuild of Figure 11 (H6) for the relabeled classifier.
Panel (a): extreme-price rate by FRI band (all test intervals).
Panel (b): mean dispatch by FRI band, dispatched intervals only,
  with Pearson r annotated. Relabeled classifier has no MEDIUM-
  band intervals among dispatched decisions (only 15 MEDIUM
  intervals total in test set, none dispatched).

Verified data:
  Panel (a) (c2_25_extreme_rate_by_band_relabeled.csv):
    LOW: rate=0.59%, n=14,149
    MEDIUM: rate=53.33%, n=15
    HIGH: rate=94.80%, n=481
  Panel (b) (c3_42_h6_relabeled_results.csv + band means):
    r=0.3223, p<0.001, CI[0.2639,0.3783]
    LOW: mean=5.15 MW, n=936
    HIGH: mean=23.25 MW, n=8
    (no MEDIUM among dispatched)

Output:
  results/figures/fig11_h6_correlation.png
  results/figures/fig11_h6_correlation.pdf
"""
import os
import sys
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import numpy as np
import pandas as pd
from config.settings import FIGURES_DIR, TABLES_DIR
from config.logging_config import get_logger

logger = get_logger("figure_11_h6_correlation_relabeled")

BAND_COLORS = {"LOW": "#0072B2", "MEDIUM": "#E69F00", "HIGH": "#D55E00"}
BLACK = "#222222"
MUTED = "#666666"

R_PEARSON = 0.3223
R_CI = (0.2639, 0.3783)

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

def build_panel_a(ax):
    dec = pd.read_csv(TABLES_DIR / "c2_25_extreme_rate_by_band_relabeled.csv")
    band_order = ["LOW", "MEDIUM", "HIGH"]
    dec["band"] = pd.Categorical(dec["fri_band"], categories=band_order, ordered=True)
    dec = dec.sort_values("band")

    x = np.arange(len(dec))
    vals = dec["extreme_rate_pct"].values
    cols = [BAND_COLORS[b] for b in dec["fri_band"]]

    ax.bar(x, vals, width=0.55, color=cols, alpha=0.9,
           edgecolor="white", linewidth=0.3, zorder=3)
    for xi, v, n, pct in zip(x, vals, dec["count"], dec["pct_of_total"]):
        ax.text(xi, v + 2, f"{v:.2f}%", ha="center", va="bottom",
                fontsize=7, color=BLACK, fontweight="bold", zorder=5)
        ax.text(xi, -7, f"n={n:,}\n({pct:.2f}%)", ha="center", va="top",
                fontsize=5.5, color=MUTED, zorder=5)

    ax.text(0.03, 0.96,
            "Extreme event rate rises ~160-fold\nfrom LOW (0.59%) to HIGH (94.80%)",
            transform=ax.transAxes, fontsize=6, ha="left", va="top",
            color="#534AB7",
            bbox=dict(boxstyle="round,pad=0.35", facecolor="white",
                      edgecolor="#534AB7", linewidth=0.8, alpha=0.95), zorder=10)

    ax.set_xticks(x)
    ax.set_xticklabels(dec["fri_band"], fontsize=7, color=BLACK)
    ax.tick_params(axis="x", pad=22)
    ax.set_ylabel("Extreme price interval rate (%)", fontsize=7.5, color=BLACK)
    ax.set_ylim(0, 108)
    ax.grid(axis="x", visible=False)
    ax.set_title("(a)  Extreme rate by FRI band", fontsize=8, fontweight="bold",
                 loc="left", pad=7, color=BLACK)

def build_panel_b(ax):
    bands = ["LOW", "MEDIUM", "HIGH"]
    vals = [5.15, 0, 23.25]
    ns = [936, 0, 8]
    cols = [BAND_COLORS[b] for b in bands]

    x = np.arange(len(bands))
    bar_vals = [5.15, 0.01, 23.25]  # tiny sliver for MEDIUM to show "no data" marker
    ax.bar(x, bar_vals, width=0.5, color=cols, alpha=0.9,
           edgecolor="white", linewidth=0.3, zorder=3)
    for xi, v, n, label in zip(x, vals, ns, bands):
        if label == "MEDIUM":
            ax.text(xi, 1.2, "no dispatched\nintervals\n(n=0)", ha="center", va="bottom",
                    fontsize=6, color=MUTED, style="italic", zorder=5)
        else:
            ax.text(xi, v + 0.8, f"{v:.2f} MW\n(n={n})", ha="center", va="bottom",
                    fontsize=6.5, color=BLACK, fontweight="bold", zorder=5)

    ax.text(0.03, 0.96,
            f"Pearson r = {R_PEARSON:.4f}\n95% CI [{R_CI[0]:.4f}, {R_CI[1]:.4f}]\n"
            f"p < 0.001",
            transform=ax.transAxes, fontsize=6, ha="left", va="top", color=BLACK,
            bbox=dict(boxstyle="round,pad=0.35", facecolor="white",
                      edgecolor="#009E73", linewidth=0.8, alpha=0.95), zorder=10)

    ax.set_xticks(x)
    ax.set_xticklabels(bands, fontsize=7, color=BLACK)
    ax.set_ylabel("Mean dispatch (MW)", fontsize=7.5, color=BLACK)
    ax.set_ylim(0, 30)
    ax.grid(axis="x", visible=False)
    ax.set_title("(b)  Mean dispatch by FRI band", fontsize=8, fontweight="bold",
                 loc="left", pad=7, color=BLACK)

def main():
    plt.rcParams.update(STYLE)
    fig = plt.figure(figsize=(7.20, 3.40))
    gs = gridspec.GridSpec(1, 2, figure=fig, wspace=0.30,
                            left=0.08, right=0.98, top=0.90, bottom=0.18)
    ax1 = fig.add_subplot(gs[0])
    ax2 = fig.add_subplot(gs[1])
    build_panel_a(ax1)
    build_panel_b(ax2)

    os.makedirs(FIGURES_DIR, exist_ok=True)
    fig.savefig(FIGURES_DIR / "fig11_h6_correlation.png", dpi=1000, bbox_inches="tight")
    fig.savefig(FIGURES_DIR / "fig11_h6_correlation.pdf", dpi=1000, bbox_inches="tight")
    logger.info(f"Saved: {FIGURES_DIR}/fig11_h6_correlation.png/.pdf")
    sys.exit(0)

if __name__ == "__main__":
    main()
