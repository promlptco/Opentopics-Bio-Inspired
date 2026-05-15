"""Phase 2 Food Comparison — overlay comparison plots.

Produces two figures:
  food_comparison_timeseries.png — 4-panel time-series (all conditions overlaid)
  food_comparison_summary.png    — bar chart of tail-window scalar metrics
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
    "legend.frameon": True,
    "legend.edgecolor": "#cccccc",
    "figure.facecolor": "white",
    "savefig.facecolor": "white",
})

CONDITION_COLORS = {
    "F0": "#1f4e79",  # dark blue   — uniform 1:1
    "F1": "#2a9a3c",  # green       — mild Shannon
    "F2": "#e07b00",  # orange      — moderate Shannon
    "F3": "#c0392b",  # red         — strong Shannon
}


# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------

def _smooth(x: np.ndarray, w: int) -> np.ndarray:
    if w <= 1 or len(x) < w:
        return x.copy()
    half = w // 2
    padded = np.pad(x, (half, half), mode="reflect")
    kernel = np.ones(w) / w
    smoothed = np.convolve(padded, kernel, mode="valid")
    return smoothed[: len(x)]


def _fill_nan(x: np.ndarray) -> np.ndarray:
    return np.where(np.isnan(x), 0.0, x)


# ---------------------------------------------------------------------------
# Time-series comparison figure
# ---------------------------------------------------------------------------

def plot_comparison(
    aggregates: dict[str, dict],
    alpha_levels: list[tuple[float, str, str]],
    max_ticks: int,
    out: Path,
    smooth_w: int = 50,
) -> None:
    """4-panel overlay: population, energy, food available, foraging success."""
    ticks = np.arange(max_ticks)
    labels_present = [lbl for _, lbl, _ in alpha_levels if lbl in aggregates]

    fig, axes = plt.subplots(2, 2, figsize=(12, 7))
    fig.suptitle(
        "Phase 2 — Food Mechanism Comparison: Uniform 1:1 vs Shannon Entropy\n"
        "(Phase 4b BEST_CALIBRATED ecology, mother-only, no evolution)",
        fontsize=11, fontweight="bold",
    )

    panels = [
        ("pop_mean",        "pop_std",   "Mother population (alive)",      "Mothers",          axes[0, 0]),
        ("energy_mean",     "energy_std","Mean energy (population-weighted)","Energy (0–1)",    axes[0, 1]),
        ("food_avail_mean", None,        "Food available in world",         "Food items",       axes[1, 0]),
        ("pick_rate",       None,        "Foraging success rate (PICK/total actions)", "Rate", axes[1, 1]),
    ]

    for mean_key, std_key, title, ylabel, ax in panels:
        for label in labels_present:
            agg = aggregates[label]
            color = CONDITION_COLORS.get(label, "gray")
            desc = agg["desc"]

            raw = _fill_nan(agg[mean_key])
            ys = _smooth(raw, smooth_w)

            ax.plot(ticks, ys, color=color, lw=1.6, label=f"{label}: {desc}")

            if std_key and std_key in agg:
                raw_std = _fill_nan(agg[std_key])
                ys_std = _smooth(raw_std, smooth_w)
                ax.fill_between(ticks, ys - ys_std, ys + ys_std,
                                color=color, alpha=0.12)

        ax.set_title(title)
        ax.set_xlabel("Tick")
        ax.set_ylabel(ylabel)
        ax.set_xlim(0, max_ticks)
        ax.legend(loc="upper right", fontsize=7)

    # Force energy axis to [0, 1]
    axes[0, 1].set_ylim(0, 1.05)
    axes[0, 0].set_ylim(0, None)
    axes[1, 1].set_ylim(0, 1.0)

    plt.tight_layout()
    path = out / "food_comparison_timeseries.png"
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved {path.name}")

    # ---- Summary bar chart -----------------------------------------------
    _plot_summary(aggregates, alpha_levels, out)


def _plot_summary(
    aggregates: dict[str, dict],
    alpha_levels: list[tuple[float, str, str]],
    out: Path,
) -> None:
    """Bar chart comparing tail-window metrics across conditions."""
    labels_present = [lbl for _, lbl, _ in alpha_levels if lbl in aggregates]
    descs = [aggregates[lbl]["desc"] for lbl in labels_present]
    colors = [CONDITION_COLORS.get(lbl, "gray") for lbl in labels_present]

    metrics = [
        ("tail_mean_energy", "Tail-window mean energy\n(population-weighted)", 0.0, 1.0),
        ("tail_mean_pop",    "Tail-window mean population\n(alive mothers)",   0.0, None),
        ("final_pop_mean",   "Final population\n(alive mothers at T_end)",     0.0, None),
    ]

    fig, axes = plt.subplots(1, 3, figsize=(11, 4))
    fig.suptitle(
        "Phase 2 Food Comparison — Tail-Window Summary Metrics",
        fontsize=11, fontweight="bold",
    )

    x = np.arange(len(labels_present))
    bar_w = 0.55

    for ax, (metric_key, ylabel, ymin, ymax) in zip(axes, metrics):
        vals = [aggregates[lbl][metric_key] for lbl in labels_present]
        bars = ax.bar(x, vals, width=bar_w, color=colors, edgecolor="white", linewidth=0.8)

        # Value labels on top of bars
        for bar, val in zip(bars, vals):
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                bar.get_height() + 0.01 * (ymax or max(vals) or 1),
                f"{val:.2f}",
                ha="center", va="bottom", fontsize=8,
            )

        ax.set_xticks(x)
        ax.set_xticklabels(labels_present)
        ax.set_ylabel(ylabel)
        ax.set_ylim(ymin, (ymax * 1.15) if ymax else None)

        # Secondary x-labels: short alpha description
        ax2 = ax.secondary_xaxis("top")
        ax2.set_xticks(x)
        ax2.set_xticklabels(
            [agg["alpha"] for agg in [aggregates[lbl] for lbl in labels_present]],
            fontsize=7,
        )
        ax2.set_xlabel("food_entropy_alpha (alpha)", fontsize=8)

    plt.tight_layout()
    path = out / "food_comparison_summary.png"
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved {path.name}")
