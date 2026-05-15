"""Phase 4c Mechanism Screen — plots.

Produces:
  mechanism_screen.png — 2x3 panel bar chart (SVR, CMR, PSC for cry and temp axes)
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

matplotlib.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": ["DejaVu Sans", "Arial", "Helvetica"],
    "axes.titlesize": 11,
    "axes.labelsize": 10,
    "xtick.labelsize": 8,
    "ytick.labelsize": 8,
    "xtick.direction": "in",
    "ytick.direction": "in",
    "legend.fontsize": 8,
    "figure.facecolor": "white",
    "savefig.facecolor": "white",
})

CRY_COLORS  = ["#1f4e79", "#2a9a3c", "#e07b00", "#c0392b"]
TEMP_COLORS = ["#4a4e69", "#9a8c98", "#c9ada7", "#f2e9e4"]


def plot_mechanism_screen(
    cry_aggs:  list[dict],
    cry_levels: list[tuple[float, str, str]],
    temp_aggs: list[dict],
    temp_levels: list[tuple[float, str, str]],
    best_cry_lbl: str,
    best_temp_lbl: str,
    out: Path,
) -> None:
    """2x3 panel: rows=cry/temp axes, columns=SVR/CMR/PSC."""
    fig, axes = plt.subplots(2, 3, figsize=(13, 7))
    fig.suptitle(
        "Phase 4c — Mechanism Screen: Cry Signal vs Temperature OVAT\n"
        "Phase 4b BEST_CALIBRATED ecology | OPTIMAL weights (care=0.5, forage=2.0, self=1.0)",
        fontsize=11, fontweight="bold",
    )

    metrics = [
        ("svr_mean", "svr_sd", "SVR — Mother Survival Rate",       0.0, 1.0),
        ("cmr_mean", "cmr_sd", "CMR — Child Maturation Rate",      0.0, 1.0),
        ("psc_mean", "psc_sd", "PSC — Population Stability (CV)",  0.0, None),
    ]

    for col, (mean_key, sd_key, title, ymin, ymax) in enumerate(metrics):
        # Row 0: cry axis
        ax = axes[0, col]
        labels_cry = [lbl for _, lbl, _ in cry_levels]
        vals  = [a[mean_key] for a in cry_aggs]
        sds   = [a[sd_key]   for a in cry_aggs]
        colors = [CRY_COLORS[i] for i in range(len(cry_levels))]
        edge_colors = ["gold" if lbl == best_cry_lbl else "white" for lbl in labels_cry]
        lw = [2.5 if lbl == best_cry_lbl else 0.8 for lbl in labels_cry]

        x = np.arange(len(labels_cry))
        bars = ax.bar(x, vals, yerr=sds, color=colors, edgecolor=edge_colors,
                      linewidth=lw, capsize=4, width=0.6)
        for bar, val in zip(bars, vals):
            ax.text(bar.get_x() + bar.get_width() / 2,
                    bar.get_height() + (max(vals) * 0.04 if vals else 0.02),
                    "%.3f" % val, ha="center", va="bottom", fontsize=7)
        ax.set_xticks(x)
        ax.set_xticklabels(labels_cry)
        ax.set_title("%s\n(cry axis)" % title)
        ax.set_ylabel(title.split(" — ")[0])
        if ymax is not None:
            ax.set_ylim(ymin, ymax * 1.15)
        else:
            ax.set_ylim(ymin, None)
        ax.axhline(0, color="gray", lw=0.5)

        # Threshold reference lines
        if mean_key == "svr_mean":
            ax.axhline(0.60, color="gray", lw=1.0, ls="--", label="SVR=0.60")
            ax.legend(fontsize=7)
        elif mean_key == "psc_mean":
            ax.axhline(0.50, color="gray", lw=1.0, ls="--", label="PSC=0.50")
            ax.legend(fontsize=7)

        # Row 1: temp axis
        ax = axes[1, col]
        labels_temp = [lbl for _, lbl, _ in temp_levels]
        vals  = [a[mean_key] for a in temp_aggs]
        sds   = [a[sd_key]   for a in temp_aggs]
        colors = [TEMP_COLORS[i] for i in range(len(temp_levels))]
        edge_colors = ["gold" if lbl == best_temp_lbl else "white" for lbl in labels_temp]
        lw = [2.5 if lbl == best_temp_lbl else 0.8 for lbl in labels_temp]

        x = np.arange(len(labels_temp))
        bars = ax.bar(x, vals, yerr=sds, color=colors, edgecolor=edge_colors,
                      linewidth=lw, capsize=4, width=0.6)
        for bar, val in zip(bars, vals):
            ax.text(bar.get_x() + bar.get_width() / 2,
                    bar.get_height() + (max(vals) * 0.04 if vals else 0.02),
                    "%.3f" % val, ha="center", va="bottom", fontsize=7)
        ax.set_xticks(x)
        ax.set_xticklabels(labels_temp)
        ax.set_title("%s\n(temperature axis)" % title)
        ax.set_ylabel(title.split(" — ")[0])
        if ymax is not None:
            ax.set_ylim(ymin, ymax * 1.15)
        else:
            ax.set_ylim(ymin, None)
        ax.axhline(0, color="gray", lw=0.5)

        if mean_key == "svr_mean":
            ax.axhline(0.60, color="gray", lw=1.0, ls="--", label="SVR=0.60")
            ax.legend(fontsize=7)
        elif mean_key == "psc_mean":
            ax.axhline(0.50, color="gray", lw=1.0, ls="--", label="PSC=0.50")
            ax.legend(fontsize=7)

    # Row labels
    for row, label in enumerate(["Cry axis (temperature_sensitivity=0)", "Temp axis (cry_decay_radius=0)"]):
        axes[row, 0].set_ylabel("%s\n%s" % (label, metrics[0][0].split("_")[0].upper()))

    # Legend: gold border = selected level
    from matplotlib.patches import Patch
    legend_patch = Patch(facecolor="white", edgecolor="gold", linewidth=2.5,
                         label="Selected level (lock rule)")
    fig.legend(handles=[legend_patch], loc="lower center", ncol=1, fontsize=9,
               bbox_to_anchor=(0.5, 0.0))

    plt.tight_layout(rect=[0, 0.03, 1, 1])
    path = out / "mechanism_screen.png"
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print("  Saved %s" % path.name)
