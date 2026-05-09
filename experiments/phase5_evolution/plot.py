# experiments/phase5_evolution/plot.py
"""
Phase 5 Block 2 plot functions.

plot_care_evolution   — mean genome care_weight over time, 4 conditions
plot_final_distribution — boxplot of final care_weight per condition
"""

import os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker

from experiments.phase5_evolution.config import SUCCESS_CARE_THRESHOLD, CONDITIONS

# ── Style ──────────────────────────────────────────────────────────────────
plt.rcParams.update({
    "font.family":       "sans-serif",
    "axes.spines.top":   False,
    "axes.spines.right": False,
    "xtick.direction":   "in",
    "ytick.direction":   "in",
    "figure.facecolor":  "white",
    "axes.facecolor":    "white",
})

_COLORS = {
    "mut_on_plast_off":  "#1f77b4",   # steel blue  — primary result
    "mut_on_plast_on":   "#2ca02c",   # forest green
    "mut_off_plast_on":  "#ff7f0e",   # orange
    "mut_off_plast_off": "#888888",   # grey — null baseline
}
_LABELS = {
    "mut_on_plast_off":  "Mut ON  / Plast OFF  (primary)",
    "mut_on_plast_on":   "Mut ON  / Plast ON",
    "mut_off_plast_on":  "Mut OFF / Plast ON",
    "mut_off_plast_off": "Mut OFF / Plast OFF  (null)",
}


def plot_care_evolution(summary: dict, out_dir: str) -> None:
    """Mean genome care_weight over simulation ticks, ±1 SD band, 4 conditions."""
    fig, ax = plt.subplots(figsize=(10, 5))

    for cond in CONDITIONS:
        s = summary.get(cond)
        if s is None:
            continue
        ticks = np.array(s["trajectory_ticks"])
        mean  = np.array(s["trajectory_mean_care"], dtype=float)
        sd    = np.array(s["trajectory_sd_care"],   dtype=float)
        color = _COLORS[cond]
        ax.plot(ticks, mean, color=color, linewidth=1.6, label=_LABELS[cond])
        ax.fill_between(ticks, mean - sd, mean + sd, alpha=0.15, color=color)

    ax.axhline(SUCCESS_CARE_THRESHOLD, color="black", linestyle="--",
               linewidth=1.2, label=f"neutral baseline ({SUCCESS_CARE_THRESHOLD:.3f})")

    ax.set_xlabel("Simulation tick", fontsize=11)
    ax.set_ylabel("Mean genome care share", fontsize=11)
    ax.set_title("Block 2 — Baldwin Care Emergence\n"
                 "genome care_weight over time (mean ± 1 SD across 10 seeds)",
                 fontsize=12)
    ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{int(x):,}"))
    ax.set_ylim(bottom=0)
    ax.legend(fontsize=9, frameon=False)
    fig.tight_layout()

    path = os.path.join(out_dir, "care_evolution.png")
    fig.savefig(path, dpi=150)
    plt.close(fig)
    print(f"  Saved: {os.path.basename(path)}")


def plot_final_distribution(summary: dict, out_dir: str) -> None:
    """Boxplot of final mean_genome_care_weight per condition."""
    fig, ax = plt.subplots(figsize=(8, 4))

    cond_list  = list(CONDITIONS.keys())
    means      = [summary[c]["mean_final_care"] if c in summary else float("nan")
                  for c in cond_list]
    sds        = [summary[c]["sd_final_care"]   if c in summary else 0.0
                  for c in cond_list]
    colors     = [_COLORS[c] for c in cond_list]
    x          = np.arange(len(cond_list))

    bars = ax.bar(x, means, yerr=sds, color=colors, alpha=0.8,
                  capsize=5, error_kw={"linewidth": 1.2})

    ax.axhline(SUCCESS_CARE_THRESHOLD, color="black", linestyle="--",
               linewidth=1.2, label=f"neutral ({SUCCESS_CARE_THRESHOLD:.3f})")

    ax.set_xticks(x)
    ax.set_xticklabels([_LABELS[c] for c in cond_list], rotation=15,
                       ha="right", fontsize=8)
    ax.set_ylabel("Final mean genome care share", fontsize=11)
    ax.set_title("Block 2 — Final Genome Care Distribution\n"
                 "(mean ± SD across 10 seeds, last sampled tick)",
                 fontsize=12)
    ax.set_ylim(bottom=0)
    ax.legend(fontsize=9, frameon=False)
    fig.tight_layout()

    path = os.path.join(out_dir, "care_final_distribution.png")
    fig.savefig(path, dpi=150)
    plt.close(fig)
    print(f"  Saved: {os.path.basename(path)}")


def plot_population_over_time(summary: dict, out_dir: str) -> None:
    """Mean alive_mothers over time, 4 conditions. Useful for extinction check."""
    fig, ax = plt.subplots(figsize=(10, 4))

    for cond in CONDITIONS:
        s = summary.get(cond)
        if s is None or "trajectory_mean_pop" not in s:
            continue
        ticks = np.array(s["trajectory_ticks"])
        pop   = np.array(s["trajectory_mean_pop"], dtype=float)
        ax.plot(ticks, pop, color=_COLORS[cond], linewidth=1.4, label=_LABELS[cond])

    ax.set_xlabel("Simulation tick", fontsize=11)
    ax.set_ylabel("Mean alive mothers", fontsize=11)
    ax.set_title("Block 2 — Population Dynamics", fontsize=12)
    ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{int(x):,}"))
    ax.set_ylim(bottom=0)
    ax.legend(fontsize=9, frameon=False)
    fig.tight_layout()

    path = os.path.join(out_dir, "population_over_time.png")
    fig.savefig(path, dpi=150)
    plt.close(fig)
    print(f"  Saved: {os.path.basename(path)}")
