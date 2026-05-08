# experiments/phase4_weight_sweep/plot.py
"""
Phase 4 Weight Sweep — clean academic figures.

  sweep_heatmap.png         — C_matr per (care_weight, forage_weight)
  sweep_mother_survival.png — M_surv per (care_weight, forage_weight)
  sweep_3d_surface.png      — 3D surface: care × forage → C_matr

Axes show raw weight inputs (self_weight = 1.0 fixed).
Effective share = w / (care_w + forage_w + 1.0).
"""

import os
import sys
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D  # noqa: F401

PROJECT_ROOT = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)
sys.path.insert(0, PROJECT_ROOT)

from experiments.phase4_weight_sweep.config import (
    CARE_WEIGHT_VALUES, FORAGE_WEIGHT_VALUES,
    VIABLE_LABEL, OPTIMAL_LABEL,
)

matplotlib.rcParams.update({
    "font.family":       "sans-serif",
    "font.sans-serif":   ["DejaVu Sans", "Arial", "Helvetica"],
    "axes.titlesize":    11,
    "axes.labelsize":    10,
    "xtick.labelsize":   9,
    "ytick.labelsize":   9,
    "xtick.direction":   "in",
    "ytick.direction":   "in",
    "figure.facecolor":  "white",
    "savefig.facecolor": "white",
})


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _build_grid(summary_rows: list, metric: str) -> np.ndarray:
    n_c = len(CARE_WEIGHT_VALUES)
    n_f = len(FORAGE_WEIGHT_VALUES)
    grid = np.full((n_c, n_f), np.nan)
    c_idx = {round(v, 4): i for i, v in enumerate(CARE_WEIGHT_VALUES)}
    f_idx = {round(v, 4): i for i, v in enumerate(FORAGE_WEIGHT_VALUES)}
    for row in summary_rows:
        ci = c_idx.get(round(row["care_weight"],   4))
        fi = f_idx.get(round(row["forage_weight"], 4))
        if ci is not None and fi is not None:
            grid[ci, fi] = row[metric]
    return grid


def _save(fig, path: str, dpi: int = 200) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    fig.savefig(path, dpi=dpi, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"  Saved: {os.path.basename(path)}")


def _style_ax(ax, xlabel="", ylabel="") -> None:
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color("#bbbbbb")
    ax.spines["bottom"].set_color("#bbbbbb")
    ax.tick_params(direction="in", colors="#444444", length=3)
    if xlabel:
        ax.set_xlabel(xlabel, labelpad=6)
    if ylabel:
        ax.set_ylabel(ylabel, labelpad=6)


def _set_ticks(ax) -> None:
    ax.set_xticks(range(len(FORAGE_WEIGHT_VALUES)))
    ax.set_yticks(range(len(CARE_WEIGHT_VALUES)))
    ax.set_xticklabels([f"{v:.1f}" for v in FORAGE_WEIGHT_VALUES])
    ax.set_yticklabels([f"{v:.1f}" for v in CARE_WEIGHT_VALUES])


# ─────────────────────────────────────────────────────────────────────────────
# Core heatmap
# ─────────────────────────────────────────────────────────────────────────────

def _heatmap(ax, grid: np.ndarray, vmin: float, vmax: float,
             cmap: str, fmt: str = ".2f") -> object:
    im = ax.imshow(
        grid, cmap=cmap, aspect="auto",
        vmin=vmin, vmax=vmax, origin="lower",
    )
    for ci in range(grid.shape[0]):
        for fi in range(grid.shape[1]):
            val = grid[ci, fi]
            if np.isnan(val):
                continue
            brightness = (val - vmin) / max(vmax - vmin, 1e-9)
            color = "white" if brightness > 0.6 else "#222222"
            ax.text(fi, ci, format(val, fmt),
                    ha="center", va="center",
                    fontsize=8.5, color=color)
    return im


# ─────────────────────────────────────────────────────────────────────────────
# Figure 1 — C_matr heatmap
# ─────────────────────────────────────────────────────────────────────────────

def plot_sweep_heatmap(summary_rows: list, selected: dict,
                       out_dir: str) -> None:
    grid = _build_grid(summary_rows, "c_matr_mean")
    vmax = float(np.nanmax(grid))

    fig, ax = plt.subplots(figsize=(5.5, 4.5))
    fig.subplots_adjust(left=0.14, right=0.88, top=0.88, bottom=0.14)

    im = _heatmap(ax, grid, vmin=0.0, vmax=vmax, cmap="Blues")

    cb = fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    cb.set_label("Mean C_matr", fontsize=9)
    cb.ax.tick_params(labelsize=8)

    _set_ticks(ax)
    _style_ax(ax,
              xlabel="forage_weight  (self = 1.0 fixed; eff. share = w / Σw)",
              ylabel="care_weight")
    ax.set_title("Phase 4 — Child maturation rate  (5 seeds)", pad=10)

    _save(fig, os.path.join(out_dir, "sweep_heatmap.png"))


# ─────────────────────────────────────────────────────────────────────────────
# Figure 2 — M_surv heatmap
# ─────────────────────────────────────────────────────────────────────────────

def plot_sweep_mother_survival(summary_rows: list, selected: dict,
                                out_dir: str) -> None:
    grid = _build_grid(summary_rows, "m_surv_mean")
    vmax = float(np.nanmax(grid))

    fig, ax = plt.subplots(figsize=(5.5, 4.5))
    fig.subplots_adjust(left=0.14, right=0.88, top=0.88, bottom=0.14)

    im = _heatmap(ax, grid, vmin=0.0, vmax=vmax, cmap="Oranges")

    cb = fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    cb.set_label("Mean M_surv", fontsize=9)
    cb.ax.tick_params(labelsize=8)

    _set_ticks(ax)
    _style_ax(ax,
              xlabel="forage_weight  (self = 1.0 fixed; eff. share = w / Σw)",
              ylabel="care_weight")
    ax.set_title("Phase 4 — Mother survival rate  (5 seeds)", pad=10)

    _save(fig, os.path.join(out_dir, "sweep_mother_survival.png"))


# ─────────────────────────────────────────────────────────────────────────────
# Figure 3 — 3D surface
# ─────────────────────────────────────────────────────────────────────────────

def plot_sweep_3d_surface(summary_rows: list, selected: dict,
                           out_dir: str) -> None:
    grid = _build_grid(summary_rows, "c_matr_mean")

    C = np.array(CARE_WEIGHT_VALUES)
    F = np.array(FORAGE_WEIGHT_VALUES)
    F_mesh, C_mesh = np.meshgrid(F, C)

    fig = plt.figure(figsize=(7, 5))
    fig.subplots_adjust(left=0.05, right=0.95, top=0.90, bottom=0.05)
    ax  = fig.add_subplot(111, projection="3d")

    surf = ax.plot_surface(
        C_mesh, F_mesh, np.where(np.isnan(grid), np.nan, grid),
        cmap="Blues", alpha=0.90,
        linewidth=0.3, edgecolor="#aaaaaa",
        vmin=0, vmax=float(np.nanmax(grid)),
    )
    fig.colorbar(surf, ax=ax, shrink=0.45, aspect=12,
                 label="Mean C_matr", pad=0.08)

    ax.contourf(
        C_mesh, F_mesh, np.where(np.isnan(grid), 0, grid),
        zdir="z", offset=-0.02,
        cmap="Blues", alpha=0.30, levels=15,
    )

    ax.set_xlabel("care_weight", labelpad=6)
    ax.set_ylabel("forage_weight", labelpad=6)
    ax.set_zlabel("C_matr", labelpad=4)
    ax.set_title("Phase 4 — C_matr surface  (self = 1.0, 5 seeds)",
                 fontweight="bold", pad=8)
    ax.set_zlim(-0.02, max(0.1, float(np.nanmax(grid))) + 0.04)

    _save(fig, os.path.join(out_dir, "sweep_3d_surface.png"))
