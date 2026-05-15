"""Phase 3 Food Comparison — overlay comparison plots (mother + child panels).

Same format as Phase 2 food comparison but adds child-specific panels.

Produces:
  food_comparison_timeseries.png — 6-panel overlay (mother + child time-series)
  food_comparison_summary.png    — bar chart: tail energy, population, child maturation
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
    "F0": "#1f4e79",
    "F1": "#2a9a3c",
    "F2": "#e07b00",
    "F3": "#c0392b",
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
# Time-series comparison figure (6 panels: 3 mother + 3 child)
# ---------------------------------------------------------------------------

def plot_comparison(
    aggregates: dict[str, dict],
    alpha_levels: list[tuple[float, str, str]],
    max_ticks: int,
    out: Path,
    smooth_w: int = 50,
) -> None:
    """6-panel overlay: 3 mother panels + 3 child panels."""
    ticks = np.arange(max_ticks)
    labels_present = [lbl for _, lbl, _ in alpha_levels if lbl in aggregates]

    fig, axes = plt.subplots(2, 3, figsize=(15, 8))
    fig.suptitle(
        "Phase 3 — Food Mechanism Comparison: Uniform 1:1 vs Shannon Entropy (with children)\n"
        "Unbiased genome weights (care=forage=self=1.0) — Phase 4b BEST_CALIBRATED ecology",
        fontsize=11, fontweight="bold",
    )

    panels = [
        # (mean_key, std_key, title, ylabel, ax)
        ("pop_mean",          "pop_std",         "Mother population (alive)",        "Mothers",     axes[0, 0]),
        ("energy_mean",       "energy_std",       "Mother energy (population-weighted)", "Energy (0-1)", axes[0, 1]),
        ("food_avail_mean",   None,               "Food available in world",          "Food items",  axes[0, 2]),
        ("child_pop_mean",    "child_pop_std",    "Child population alive",           "Children",    axes[1, 0]),
        ("child_energy_mean", "child_energy_std", "Child mean energy",                "Energy (0-1)", axes[1, 1]),
    ]

    for mean_key, std_key, title, ylabel, ax in panels:
        for label in labels_present:
            agg = aggregates[label]
            if mean_key not in agg:
                continue
            color = CONDITION_COLORS.get(label, "gray")
            desc = agg["desc"]

            raw = _fill_nan(agg[mean_key])
            ys = _smooth(raw, smooth_w)
            ax.plot(ticks, ys, color=color, lw=1.6, label="%s: %s" % (label, desc))

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

    axes[0, 1].set_ylim(0, 1.05)
    axes[1, 1].set_ylim(0, 1.05)
    axes[0, 0].set_ylim(0, None)
    axes[1, 0].set_ylim(0, None)

    # Panel 6 (axes[1, 2]): child maturation rate bar chart per condition
    ax_c = axes[1, 2]
    labels_p = [lbl for lbl in labels_present if lbl in aggregates]
    c_matr = [aggregates[lbl]["child_maturation_rate_mean"] for lbl in labels_p]
    c_sd = [aggregates[lbl]["child_maturation_rate_sd"] for lbl in labels_p]
    colors_p = [CONDITION_COLORS.get(lbl, "gray") for lbl in labels_p]
    x = np.arange(len(labels_p))
    bars = ax_c.bar(x, c_matr, yerr=c_sd, color=colors_p, edgecolor="white",
                    capsize=4, linewidth=0.8)
    for bar, val in zip(bars, c_matr):
        ax_c.text(bar.get_x() + bar.get_width() / 2,
                  bar.get_height() + 0.01,
                  "%.3f" % val, ha="center", va="bottom", fontsize=8)
    ax_c.set_xticks(x)
    ax_c.set_xticklabels(labels_p)
    ax_c.set_ylabel("Child maturation rate")
    ax_c.set_title("Child maturation rate by food mechanism\n(fraction reaching maturity_age=80)")
    ax_c.set_ylim(0, max(1.0, max(c_matr) * 1.3) if c_matr else 1.0)
    ax_c.axhline(0, color="gray", lw=0.5)

    plt.tight_layout()
    path = out / "food_comparison_timeseries.png"
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print("  Saved %s" % path.name)

    _plot_summary(aggregates, alpha_levels, out)


def _plot_summary(
    aggregates: dict[str, dict],
    alpha_levels: list[tuple[float, str, str]],
    out: Path,
) -> None:
    """Bar chart: tail energy, tail population, child maturation rate."""
    labels_present = [lbl for _, lbl, _ in alpha_levels if lbl in aggregates]
    descs = [aggregates[lbl]["desc"] for lbl in labels_present]
    colors = [CONDITION_COLORS.get(lbl, "gray") for lbl in labels_present]
    x = np.arange(len(labels_present))
    bar_w = 0.55

    metrics = [
        ("tail_mean_energy",            "Mother active-window\nmean energy [t=100–350]",  0.0, None, None),
        ("tail_mean_pop",               "Mother active-window\nmean population [t=100–350]", 0.0, None, None),
        ("child_maturation_rate_mean",  "Child maturation rate\n(fraction reaching age=80)", 0.0, 1.0, "child_maturation_rate_sd"),
    ]

    fig, axes = plt.subplots(1, 3, figsize=(12, 4.5))
    fig.suptitle(
        "Phase 3 Food Comparison — Summary Metrics (active window t=100–350 or final)",
        fontsize=11, fontweight="bold",
    )

    for ax, (metric_key, ylabel, ymin, ymax, sd_key) in zip(axes, metrics):
        vals = [aggregates[lbl][metric_key] for lbl in labels_present]
        sds = ([aggregates[lbl][sd_key] for lbl in labels_present] if sd_key else None)
        bars = ax.bar(x, vals, width=bar_w, color=colors, edgecolor="white",
                      yerr=sds, capsize=4, linewidth=0.8)

        top = ymax or (max(vals) * 1.25 if max(vals) > 0 else 1.0)
        for bar, val in zip(bars, vals):
            ax.text(bar.get_x() + bar.get_width() / 2,
                    bar.get_height() + top * 0.02,
                    "%.3f" % val, ha="center", va="bottom", fontsize=8)

        ax.set_xticks(x)
        ax.set_xticklabels(labels_present)
        ax.set_ylabel(ylabel)
        ax.set_ylim(ymin, top * 1.15)

        ax2 = ax.secondary_xaxis("top")
        ax2.set_xticks(x)
        ax2.set_xticklabels(
            ["%.2f" % aggregates[lbl]["alpha"] for lbl in labels_present],
            fontsize=7,
        )
        ax2.set_xlabel("food_entropy_alpha", fontsize=8)

    plt.tight_layout()
    path = out / "food_comparison_summary.png"
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print("  Saved %s" % path.name)
