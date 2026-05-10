# experiments/phase4_weight_sweep/phase4b_plot.py
"""
Phase 4b ecology calibration — publication-quality figures.

Three figures:
  1. cmatr_heatmap.png       — C_matr over init_food x eat_gain
  2. msurv_heatmap.png       — M_surv over init_food x eat_gain
  3. scatter_msurv_cmatr.png — C_matr vs M_surv for all 28 combos
"""

import os
import csv
import json
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker

from experiments.phase4_weight_sweep.phase4b_config import (
    INIT_FOOD_VALUES, EAT_GAIN_VALUES,
    MOTHER_SURVIVAL_MIN, CMATR_MIN, BEST_CALIBRATED_LABEL,
)

matplotlib.rcParams.update({
    "font.family":          "sans-serif",
    "font.size":            9,
    "axes.titlesize":       10,
    "axes.labelsize":       9,
    "xtick.labelsize":      8,
    "ytick.labelsize":      8,
    "xtick.direction":      "out",
    "ytick.direction":      "out",
    "xtick.major.size":     3,
    "ytick.major.size":     3,
    "xtick.major.width":    0.6,
    "ytick.major.width":    0.6,
    "axes.linewidth":       0.6,
    "figure.facecolor":     "white",
    "axes.facecolor":       "white",
    "axes.spines.top":      False,
    "axes.spines.right":    False,
    "legend.frameon":       False,
    "legend.fontsize":      8,
    "legend.handlelength":  1.2,
    "figure.dpi":           150,
})


# ─────────────────────────────────────────────────────────────────────────────

def _build_grid(summary: list, metric: str) -> np.ndarray:
    grid     = np.zeros((len(INIT_FOOD_VALUES), len(EAT_GAIN_VALUES)))
    food_idx = {f: i for i, f in enumerate(INIT_FOOD_VALUES)}
    eat_idx  = {e: j for j, e in enumerate(EAT_GAIN_VALUES)}
    for r in summary:
        i = food_idx.get(int(r["init_food"]) if isinstance(r["init_food"], str) else r["init_food"])
        j = eat_idx.get(round(float(r["eat_gain"]), 2))
        if i is not None and j is not None:
            grid[i, j] = float(r[metric])
    return grid


def _annotate_cells(ax, grid: np.ndarray, fmt: str = "{:.2f}",
                    threshold: float = None) -> None:
    vmax = grid.max()
    for i in range(grid.shape[0]):
        for j in range(grid.shape[1]):
            val = grid[i, j]
            color = "white" if (threshold and val > threshold * 0.6) else "0.15"
            ax.text(j, i, fmt.format(val),
                    ha="center", va="center", fontsize=7,
                    color=color, fontweight="normal")




def _finish_heatmap_axes(ax):
    ax.set_xticks(range(len(EAT_GAIN_VALUES)))
    ax.set_xticklabels([f"{e:.2f}" for e in EAT_GAIN_VALUES])
    ax.set_yticks(range(len(INIT_FOOD_VALUES)))
    ax.set_yticklabels([str(f) for f in INIT_FOOD_VALUES])
    ax.set_xlabel("Energy gain per food item")
    ax.set_ylabel("Initial food count")
    ax.tick_params(length=3)


# ─────────────────────────────────────────────────────────────────────────────

def plot_cmatr_heatmap(summary: list, selected: dict, out_dir: str) -> None:
    grid = _build_grid(summary, "c_matr_mean")
    vmax = max(0.10, float(grid.max()) * 1.05)

    fig, ax = plt.subplots(figsize=(5.0, 3.8))
    im = ax.imshow(grid, cmap="Blues", aspect="auto", vmin=0.0, vmax=vmax)

    _finish_heatmap_axes(ax)
    _annotate_cells(ax, grid, threshold=vmax * 0.5)

    cbar = fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    cbar.set_label("Mean child maturation rate", fontsize=8)
    cbar.ax.tick_params(labelsize=7)
    cbar.outline.set_linewidth(0.4)

    ax.set_title("Child Maturation Rate ($C_{matr}$)", pad=6)

    path = os.path.join(out_dir, "cmatr_heatmap.png")
    fig.tight_layout()
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved: {os.path.basename(path)}")


def plot_msurv_heatmap(summary: list, selected: dict, out_dir: str) -> None:
    grid = _build_grid(summary, "m_surv_mean")
    vmax = max(1.0, float(grid.max()) * 1.05)

    fig, ax = plt.subplots(figsize=(5.0, 3.8))
    im = ax.imshow(grid, cmap="RdYlGn", aspect="auto", vmin=0.0, vmax=vmax)

    _finish_heatmap_axes(ax)
    _annotate_cells(ax, grid, threshold=vmax * 0.5)

    cbar = fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    cbar.set_label("Mean mother survival rate", fontsize=8)
    cbar.ax.tick_params(labelsize=7)
    cbar.outline.set_linewidth(0.4)

    ax.set_title("Mother Survival Rate ($M_{surv}$)", pad=6)

    path = os.path.join(out_dir, "msurv_heatmap.png")
    fig.tight_layout()
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved: {os.path.basename(path)}")


def plot_scatter(summary: list, selected: dict, out_dir: str) -> None:
    _EAT_COLORS = {
        0.20: "#4e79a7",
        0.30: "#f28e2b",
        0.50: "#59a14f",
        0.70: "#e15759",
    }

    fig, ax = plt.subplots(figsize=(4.5, 3.8))

    for r in summary:
        eat   = round(float(r["eat_gain"]), 2)
        color = _EAT_COLORS.get(eat, "#888888")
        ax.scatter(float(r["m_surv_mean"]), float(r["c_matr_mean"]),
                   color=color, s=40, linewidths=0.4,
                   edgecolors="white", zorder=3)
        ax.annotate(str(int(float(r["init_food"]))),
                    (float(r["m_surv_mean"]), float(r["c_matr_mean"])),
                    textcoords="offset points", xytext=(3, 2),
                    fontsize=6, color="0.3")

    for eat, color in _EAT_COLORS.items():
        ax.scatter([], [], color=color, s=30, label=f"Gain = {eat:.2f}")

    c_vals  = [float(r["c_matr_mean"]) for r in summary]
    ax.set_xlim(-0.02, 1.35)
    ax.set_ylim(-0.02, max(0.12, max(c_vals) + 0.04))
    ax.set_xlabel("Mother survival rate ($M_{surv}$)")
    ax.set_ylabel("Child maturation rate ($C_{matr}$)")
    ax.set_title("Ecology Calibration: Phase 4b", pad=6)
    ax.legend(loc="upper left", ncol=2, columnspacing=0.8,
              handletextpad=0.4, borderpad=0.3)

    ax.xaxis.set_major_formatter(ticker.FuncFormatter(lambda x, _: f"{x:.1f}"))
    ax.yaxis.set_major_formatter(ticker.FuncFormatter(lambda x, _: f"{x:.2f}"))

    path = os.path.join(out_dir, "scatter_msurv_cmatr.png")
    fig.tight_layout()
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved: {os.path.basename(path)}")


# ─────────────────────────────────────────────────────────────────────────────
# Standalone re-plot from existing output directory
# ─────────────────────────────────────────────────────────────────────────────

def _load_summary_csv(path: str) -> list:
    with open(path, newline="") as f:
        reader = csv.DictReader(f)
        return list(reader)


def _load_selected_json(path: str) -> dict:
    with open(path) as f:
        return json.load(f)


if __name__ == "__main__":
    import argparse, glob as _glob, sys

    PROJECT_ROOT = os.path.dirname(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    )
    sys.path.insert(0, PROJECT_ROOT)

    parser = argparse.ArgumentParser(description="Re-generate Phase 4b plots from existing output.")
    parser.add_argument("--out_dir", type=str, default=None,
                        help="Path to phase4b_* output directory. "
                             "Defaults to the most recent one.")
    args = parser.parse_args()

    if args.out_dir:
        out_dir = args.out_dir
    else:
        pattern = os.path.join(PROJECT_ROOT, "outputs", "phase4_weight_sweep", "phase4b_*")
        candidates = sorted(_glob.glob(pattern))
        if not candidates:
            print("No phase4b_* output directories found.")
            sys.exit(1)
        out_dir = candidates[-1]

    summary_path  = os.path.join(out_dir, "sweep_summary.csv")
    selected_path = os.path.join(out_dir, "selected_ecology.json")

    print(f"Re-plotting from: {out_dir}")
    summary  = _load_summary_csv(summary_path)
    selected = _load_selected_json(selected_path)

    plot_cmatr_heatmap(summary, selected, out_dir)
    plot_msurv_heatmap(summary, selected, out_dir)
    plot_scatter(summary, selected, out_dir)
    print("Done.")
