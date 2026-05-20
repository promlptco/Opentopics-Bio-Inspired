"""Phase 3 Food Comparison — academic-style figures.

Produces:
  food_comparison_timeseries.png  — 6-panel overlay (mother + child), x-axis 0–400
  food_comparison_motivation.png  — 3-panel bar chart: forage / care / self %
  food_comparison_summary.png     — 3-panel bar chart: orig survival / orig energy / child maturity
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

# ── Unified academic style (matches generate_report_figures.py) ───────────────
STYLE = {
    "font.family":         "serif",
    "font.serif":          ["Times New Roman", "Times", "DejaVu Serif"],
    "axes.spines.top":     False,
    "axes.spines.right":   False,
    "axes.grid":           True,
    "grid.alpha":          0.30,
    "grid.color":          "#bbbbbb",
    "grid.linestyle":      "--",
    "axes.labelsize":      12,
    "axes.titlesize":      12,
    "axes.titleweight":    "bold",
    "xtick.labelsize":     11,
    "ytick.labelsize":     11,
    "legend.fontsize":     10,
    "legend.framealpha":   0.85,
    "legend.edgecolor":    "#cccccc",
    "figure.dpi":          150,
    "figure.facecolor":    "white",
    "axes.facecolor":      "white",
}

# F0–F3 condition colours (matches generate_report_figures.py fig_food_mechanism)
COND_COLORS = ["#4C72B0", "#55A868", "#DD8452", "#C44E52"]
COND_KEYS   = ["F0", "F1", "F2", "F3"]

# Motivation domain colours
MOTIV_COLORS = {
    "forage": "#DD8452",   # amber/orange
    "care":   "#55A868",   # green
    "self":   "#8172B2",   # purple
}

# Standard error-bar style
EKW = dict(capsize=4, error_kw=dict(elinewidth=1.2, ecolor="black"))
BAR_W   = 0.60
BAR_A   = 0.85

# One mother lifetime — no evolution, so x-axis is capped here
MOTHER_LIFESPAN = 400


# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------

def _smooth(x: np.ndarray, w: int) -> np.ndarray:
    if w <= 1 or len(x) < w:
        return x.copy()
    half = w // 2
    padded = np.pad(x, (half, half), mode="reflect")
    kernel = np.ones(w) / w
    return np.convolve(padded, kernel, mode="valid")[: len(x)]


def _fill_nan(x: np.ndarray) -> np.ndarray:
    return np.where(np.isnan(x), 0.0, x)


def _alpha_label(lbl: str, agg: dict) -> str:
    return "%s\n(α=%.2f)" % (lbl, agg["alpha"])


def _color_for(lbl: str) -> str:
    idx = COND_KEYS.index(lbl) if lbl in COND_KEYS else 0
    return COND_COLORS[idx]


def savefig(fig: plt.Figure, path: Path) -> None:
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)
    print("  Saved %s" % path.name)


# ---------------------------------------------------------------------------
# Time-series comparison (6 panels, x-axis capped at MOTHER_LIFESPAN=400)
# ---------------------------------------------------------------------------

def plot_comparison(
    aggregates: dict[str, dict],
    alpha_levels: list[tuple[float, str, str]],
    max_ticks: int,
    out: Path,
    smooth_w: int = 20,
) -> None:
    labels = [lbl for _, lbl, _ in alpha_levels if lbl in aggregates]
    ticks  = np.arange(max_ticks)
    xlim   = MOTHER_LIFESPAN  # cap at one mother lifetime (no evolution)

    with plt.rc_context(STYLE):
        fig, axes = plt.subplots(2, 3, figsize=(15, 8), constrained_layout=True)
        fig.suptitle(
            "Phase 3 — Food Mechanism Comparison: Uniform 1:1 vs Shannon Entropy\n"
            "Unbiased genome (care=forage=self=1.0) · Phase 2 BALANCED ecology"
            " (init_food=40, eat_gain=0.50, move_cost=0.02) · x-axis = one mother lifetime",
            fontsize=11,
        )

        panels = [
            ("pop_mean",          "pop_std",         "Mother population (all alive)", "Mothers",      axes[0, 0]),
            ("energy_mean",       "energy_std",       "Mother mean energy",            "Energy (0–1)", axes[0, 1]),
            ("food_avail_mean",   None,               "Food available in world",       "Food items",   axes[0, 2]),
            ("child_pop_mean",    "child_pop_std",    "Child population alive",        "Children",     axes[1, 0]),
            ("child_energy_mean", "child_energy_std", "Child mean energy",             "Energy (0–1)", axes[1, 1]),
        ]

        for mean_key, std_key, title, ylabel, ax in panels:
            for lbl in labels:
                agg   = aggregates[lbl]
                color = _color_for(lbl)
                if mean_key not in agg:
                    continue
                ys = _smooth(_fill_nan(agg[mean_key]), smooth_w)
                ax.plot(ticks[:xlim], ys[:xlim], color=color, lw=1.8,
                        label="%s (α=%.2f)" % (lbl, agg["alpha"]))
                if std_key and std_key in agg:
                    ys_sd = _smooth(_fill_nan(agg[std_key]), smooth_w)
                    ax.fill_between(ticks[:xlim], ys[:xlim] - ys_sd[:xlim],
                                    ys[:xlim] + ys_sd[:xlim], color=color, alpha=0.12)
            ax.set_title(title)
            ax.set_xlabel("Tick")
            ax.set_ylabel(ylabel)
            ax.set_xlim(0, xlim)
            ax.legend(loc="upper right", fontsize=9)

        axes[0, 1].set_ylim(0, 1.05)
        axes[1, 1].set_ylim(0, 1.05)
        axes[0, 0].axhline(15, color="#888888", lw=0.9, ls="--", alpha=0.6, label="15 mothers")
        axes[0, 0].set_ylim(0, None)
        axes[1, 0].set_ylim(0, None)

        # Add mother_max_age reference line on population panel
        for ax in (axes[0, 0], axes[1, 0]):
            ax.axvline(MOTHER_LIFESPAN, color="#999999", lw=0.9, ls=":", alpha=0.7)

        # Panel 6: child maturation rate bar chart
        ax_c   = axes[1, 2]
        c_matr = [aggregates[lbl]["child_maturation_rate_mean"] for lbl in labels]
        c_sd   = [aggregates[lbl]["child_maturation_rate_sd"]   for lbl in labels]
        colors = [_color_for(lbl) for lbl in labels]
        x_bar  = np.arange(len(labels))
        bars   = ax_c.bar(x_bar, c_matr, yerr=c_sd, width=BAR_W,
                          color=colors, alpha=BAR_A, edgecolor="white", **EKW)
        for bar, val, sd in zip(bars, c_matr, c_sd):
            ax_c.text(bar.get_x() + bar.get_width() / 2, val + sd + 0.02,
                      "%.3f" % val, ha="center", va="bottom", fontsize=10)
        ax_c.axhline(1.0, color="#888888", lw=0.9, ls="--", alpha=0.6)
        ax_c.set_xticks(x_bar)
        ax_c.set_xticklabels([_alpha_label(lbl, aggregates[lbl]) for lbl in labels])
        ax_c.set_ylabel("Child maturation rate (fraction)")
        ax_c.set_title("(c) Child maturation rate\n(fraction reaching maturity_age=80)")
        ax_c.set_ylim(0, 1.25)
        ax_c.set_xlabel("Food distribution condition")

    savefig(fig, out / "food_comparison_timeseries.png")
    _plot_motivation(aggregates, alpha_levels, out)
    _plot_summary(aggregates, alpha_levels, out)


# ---------------------------------------------------------------------------
# Motivation bar chart (3 panels: forage / care / self)
# ---------------------------------------------------------------------------

def _plot_motivation(
    aggregates: dict[str, dict],
    alpha_levels: list[tuple[float, str, str]],
    out: Path,
) -> None:
    labels   = [lbl for _, lbl, _ in alpha_levels if lbl in aggregates]
    x        = np.arange(len(labels))
    x_labels = [_alpha_label(lbl, aggregates[lbl]) for lbl in labels]

    panels = [
        ("forage_pct_mean", "forage_pct_sd", "(a) Forage motivation",
         "Fraction of decisions won by FORAGE", "forage"),
        ("care_pct_mean",   "care_pct_sd",   "(b) Care motivation",
         "Fraction of decisions won by CARE",   "care"),
        ("self_pct_mean",   "self_pct_sd",   "(c) Self motivation",
         "Fraction of decisions won by SELF",   "self"),
    ]

    with plt.rc_context(STYLE):
        fig, axes = plt.subplots(1, 3, figsize=(13, 4.8), constrained_layout=True)
        fig.suptitle(
            "Effect of Food Replenishment Rate (α): Motivation Domain Winner\n"
            "Phase 2 BALANCED ecology · Unbiased genome (care=forage=self=1.0)",
            fontsize=12,
        )

        for ax, (mean_key, sd_key, title, ylabel, domain) in zip(axes, panels):
            vals = [aggregates[lbl][mean_key] for lbl in labels]
            sds  = [aggregates[lbl][sd_key]   for lbl in labels]
            color = MOTIV_COLORS[domain]

            bars = ax.bar(x, vals, width=BAR_W, color=color, alpha=BAR_A,
                          edgecolor="white", yerr=sds, **EKW)

            top = max(vals) * 1.25 if max(vals) > 0 else 0.5
            for bar, val, sd in zip(bars, vals, sds):
                ax.text(bar.get_x() + bar.get_width() / 2, val + sd + top * 0.025,
                        "%.3f" % val, ha="center", va="bottom", fontsize=10, fontweight="bold")

            ax.axhline(1 / 3, color="#888888", lw=1.0, ls="--", alpha=0.7,
                       label="Equal share (1/3)")
            ax.set_title(title)
            ax.set_ylabel(ylabel)
            ax.set_xlabel("Food distribution condition")
            ax.set_xticks(x)
            ax.set_xticklabels(x_labels)
            ax.set_ylim(0, min(1.0, top * 1.15))
            ax.legend(fontsize=9)

    savefig(fig, out / "food_comparison_motivation.png")


# ---------------------------------------------------------------------------
# Outcome summary (3 panels: orig survival / orig energy / child maturity)
# ---------------------------------------------------------------------------

def _plot_summary(
    aggregates: dict[str, dict],
    alpha_levels: list[tuple[float, str, str]],
    out: Path,
) -> None:
    labels   = [lbl for _, lbl, _ in alpha_levels if lbl in aggregates]
    colors   = [_color_for(lbl) for lbl in labels]
    x        = np.arange(len(labels))
    x_labels = [_alpha_label(lbl, aggregates[lbl]) for lbl in labels]

    panels = [
        ("orig_tail_pop",    "orig_tail_pop_sd",
         "(a) Original mother survival",
         "Mean alive original mothers\n(active window t=100–350)",
         15.0, "Initial 15 mothers"),
        ("orig_tail_energy", "orig_tail_energy_sd",
         "(b) Original mother energy",
         "Mean energy of original mothers\n(active window t=100–350)",
         1.0,  "Max energy"),
        ("child_maturation_rate_mean", "child_maturation_rate_sd",
         "(c) Child maturation rate",
         "Child maturation rate (fraction)",
         1.0,  "Full maturation"),
    ]

    with plt.rc_context(STYLE):
        fig, axes = plt.subplots(1, 3, figsize=(15, 5), constrained_layout=True)
        fig.suptitle(
            "Effect of Food Replenishment Rate (α): Original Mother Survival, Energy, and Child Maturation",
            fontsize=12,
        )

        for ax, (mean_key, sd_key, title, ylabel, ref_val, ref_label) in zip(axes, panels):
            vals = [aggregates[lbl][mean_key] for lbl in labels]
            sds  = [aggregates[lbl][sd_key]   for lbl in labels]

            bars = ax.bar(x, vals, width=BAR_W, yerr=sds, color=colors,
                          alpha=BAR_A, edgecolor="white", **EKW)

            top = max(ref_val, max(vals) * 1.05) if vals else ref_val
            for bar, val, sd in zip(bars, vals, sds):
                ax.text(bar.get_x() + bar.get_width() / 2, val + sd + top * 0.02,
                        "%.3f" % val, ha="center", va="bottom", fontsize=10)

            ax.axhline(ref_val, color="#888888", lw=1.0, ls="--", alpha=0.7,
                       label=ref_label)
            ax.set_title(title)
            ax.set_ylabel(ylabel)
            ax.set_xlabel("Food distribution condition")
            ax.set_xticks(x)
            ax.set_xticklabels(x_labels)
            ax.set_ylim(0, top * 1.20)
            ax.legend(fontsize=9, loc="lower right")

    savefig(fig, out / "food_comparison_summary.png")
