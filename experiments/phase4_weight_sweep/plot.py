# experiments/phase4_weight_sweep/plot.py
"""
Phase 4 Weight Sweep — 3 figures.

  sweep_3d_surface.png      — 3D surface: care × forage → C_matr
  sweep_heatmap.png         — Annotated 2D heatmap: C_matr per (care, forage)
  sweep_mother_survival.png — Annotated 2D heatmap: M_surv per (care, forage)
"""

import os
import sys
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
from mpl_toolkits.mplot3d import Axes3D  # noqa: F401 — registers 3D projection

PROJECT_ROOT = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)
sys.path.insert(0, PROJECT_ROOT)

from experiments.phase4_weight_sweep.config import (
    CARE_WEIGHT_VALUES, FORAGE_WEIGHT_VALUES, VIABLE_MIN_C_MATR,
    VIABLE_LABEL, OPTIMAL_LABEL,
)

# ─────────────────────────────────────────────────────────────────────────────
# Global rcParams
# ─────────────────────────────────────────────────────────────────────────────
matplotlib.rcParams.update({
    "font.family":       "sans-serif",
    "font.sans-serif":   ["DejaVu Sans", "Arial", "Helvetica"],
    "axes.titlesize":    12,
    "axes.labelsize":    11,
    "xtick.labelsize":   9,
    "ytick.labelsize":   9,
    "xtick.direction":   "in",
    "ytick.direction":   "in",
    "figure.facecolor":  "white",
    "savefig.facecolor": "white",
})

# Colour constants
C_CONTOUR  = "#2d2d2d"    # isocontour line colour
C_OPTIMAL  = "#8B0000"    # optimal marker colour (dark red)


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _build_grid(summary_rows: list, metric: str) -> np.ndarray:
    """Build a (n_care × n_forage) matrix for the given metric."""
    n_c = len(CARE_WEIGHT_VALUES)
    n_f = len(FORAGE_WEIGHT_VALUES)
    grid = np.full((n_c, n_f), np.nan)
    c_idx = {v: i for i, v in enumerate(CARE_WEIGHT_VALUES)}
    f_idx = {v: i for i, v in enumerate(FORAGE_WEIGHT_VALUES)}
    for row in summary_rows:
        ci = c_idx.get(row["care_weight"])
        fi = f_idx.get(row["forage_weight"])
        if ci is not None and fi is not None:
            grid[ci, fi] = row[metric]
    return grid


def _save(fig, path: str, dpi: int = 200) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    fig.savefig(path, dpi=dpi, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"  Saved: {os.path.basename(path)}")


def _style_ax(ax, xlabel="", ylabel="", title="") -> None:
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color("#cccccc")
    ax.spines["bottom"].set_color("#cccccc")
    ax.tick_params(direction="in", colors="#444444")
    if xlabel: ax.set_xlabel(xlabel)
    if ylabel: ax.set_ylabel(ylabel)
    if title:  ax.set_title(title, fontweight="bold")


# ─────────────────────────────────────────────────────────────────────────────
# Figure 1 — 3D surface: care × forage → C_matr
# ─────────────────────────────────────────────────────────────────────────────

def plot_sweep_3d_surface(summary_rows: list, selected: dict,
                           out_dir: str) -> None:
    grid = _build_grid(summary_rows, "c_matr_mean")

    C = np.array(CARE_WEIGHT_VALUES)
    F = np.array(FORAGE_WEIGHT_VALUES)
    F_mesh, C_mesh = np.meshgrid(F, C)   # shape (n_c, n_f)

    fig = plt.figure(figsize=(10, 7))
    ax  = fig.add_subplot(111, projection="3d")

    surf = ax.plot_surface(
        C_mesh, F_mesh, grid,
        cmap="Blues", alpha=0.88,
        linewidth=0.2, edgecolor="#aaaaaa",
        vmin=0, vmax=float(np.nanmax(grid)),
    )
    fig.colorbar(surf, ax=ax, shrink=0.5, aspect=10,
                 label=r"Mean $C_\mathrm{matr}$")

    # 2D shadow projected below
    zfloor = -0.02
    ax.contourf(
        C_mesh, F_mesh, grid,
        zdir="z", offset=zfloor,
        cmap="Blues", alpha=0.35,
        levels=20,
    )

    # OPTIMAL star
    opt = selected.get(OPTIMAL_LABEL, {})
    ax.scatter(
        [opt.get("care_weight", 1.0)],
        [opt.get("forage_weight", 1.0)],
        [opt.get("c_matr_mean", 0) + 0.01],
        color=C_OPTIMAL, s=120, marker="*", zorder=5,
    )

    ax.set_xlabel("care_weight", labelpad=8)
    ax.set_ylabel("forage_weight", labelpad=8)
    ax.set_zlabel("Mean C_matr")
    ax.set_title(
        "Phase 4 — Motivation weight sweep\n"
        "C_matr surface  (self_weight=1.0, 5 seeds)",
        fontweight="bold",
    )
    ax.set_zlim(zfloor, max(0.1, float(np.nanmax(grid))) + 0.05)
    _save(fig, os.path.join(out_dir, "sweep_3d_surface.png"))


# ─────────────────────────────────────────────────────────────────────────────
# Figure 2 — 2D annotated heatmap: C_matr
# ─────────────────────────────────────────────────────────────────────────────

def _annotated_heatmap(ax, grid: np.ndarray, vmax: float,
                        cmap: str, fmt: str = ".2f") -> object:
    im = ax.imshow(
        grid, cmap=cmap, aspect="auto",
        vmin=0, vmax=vmax, origin="lower",
    )
    for ci in range(grid.shape[0]):
        for fi in range(grid.shape[1]):
            val = grid[ci, fi]
            if np.isnan(val):
                continue
            brightness = val / max(vmax, 1e-6)
            txt_color  = "white" if brightness > 0.55 else "black"
            ax.text(fi, ci, format(val, fmt),
                    ha="center", va="center",
                    fontsize=8, color=txt_color)
    return im


def plot_sweep_heatmap(summary_rows: list, selected: dict,
                        out_dir: str) -> None:
    grid = _build_grid(summary_rows, "c_matr_mean")
    vmax = float(np.nanmax(grid))

    fig, ax = plt.subplots(figsize=(7, 6))
    im = _annotated_heatmap(ax, grid, vmax=vmax, cmap="Blues")
    fig.colorbar(im, ax=ax, label="Mean C_matr")

    opt = selected.get(OPTIMAL_LABEL, {})
    vm  = selected.get(VIABLE_LABEL, {})

    ax.set_xticks(range(len(FORAGE_WEIGHT_VALUES)))
    ax.set_yticks(range(len(CARE_WEIGHT_VALUES)))
    ax.set_xticklabels([f"{v:.1f}" for v in FORAGE_WEIGHT_VALUES])
    ax.set_yticklabels([f"{v:.1f}" for v in CARE_WEIGHT_VALUES])

    # Main title (bold) + smaller subtitle with selected values
    ax.set_title(
        "Phase 4 — C_matr heatmap  (self_weight=1.0, 5 seeds)",
        fontweight="bold", pad=28,
    )
    ax.text(
        0.5, 1.0,
        f"Optimal: C_matr={opt['c_matr_mean']:.3f}   "
        f"Viable-min: C_matr={vm['c_matr_mean']:.3f}",
        transform=ax.transAxes,
        ha="center", va="bottom",
        fontsize=8, color="#555555",
    )

    _style_ax(ax, xlabel="forage_weight", ylabel="care_weight")
    fig.tight_layout()
    _save(fig, os.path.join(out_dir, "sweep_heatmap.png"))


# ─────────────────────────────────────────────────────────────────────────────
# Figure 3 — 2D annotated heatmap: M_surv  + VIABLE_MIN contour overlay
# ─────────────────────────────────────────────────────────────────────────────

def plot_sweep_mother_survival(summary_rows: list, selected: dict,
                                out_dir: str) -> None:
    grid_msurv = _build_grid(summary_rows, "m_surv_mean")
    grid_cmatr = _build_grid(summary_rows, "c_matr_mean")
    vmax = float(np.nanmax(grid_msurv))

    fig, ax = plt.subplots(figsize=(7, 6))
    im = _annotated_heatmap(ax, grid_msurv, vmax=vmax, cmap="Oranges")
    fig.colorbar(im, ax=ax, label="Mean M_surv")

    opt = selected.get(OPTIMAL_LABEL, {})

    ax.set_xticks(range(len(FORAGE_WEIGHT_VALUES)))
    ax.set_yticks(range(len(CARE_WEIGHT_VALUES)))
    ax.set_xticklabels([f"{v:.1f}" for v in FORAGE_WEIGHT_VALUES])
    ax.set_yticklabels([f"{v:.1f}" for v in CARE_WEIGHT_VALUES])

    # Main title (bold) + smaller subtitle with selected value
    ax.set_title(
        "Phase 4 — Mother survival heatmap  (self_weight=1.0, 5 seeds)",
        fontweight="bold", pad=28,
    )
    ax.text(
        0.5, 1.0,
        f"Optimal: M_surv={opt['m_surv_mean']:.3f}",
        transform=ax.transAxes,
        ha="center", va="bottom",
        fontsize=8, color="#555555",
    )

    _style_ax(ax, xlabel="forage_weight", ylabel="care_weight")
    fig.tight_layout()
    _save(fig, os.path.join(out_dir, "sweep_mother_survival.png"))
