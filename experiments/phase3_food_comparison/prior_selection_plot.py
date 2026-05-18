"""Phase 3 -- Prior selection evidence plot.

Generates prior_selection_evidence.png showing why food_patch_prior = 0.12
was used in Phase 5. The prior is not selected by maximising CMR; it is
derived from the Phase 4b ecology lock:

    init_food = 300  on a 50x50 grid  -->  density = 300 / 2500 = 0.12

Two panels:
  A (left):  CMR heatmap (alpha x prior).
             Row prior=0.12 highlighted as Phase 4b ecology anchor.
             Column alpha=0.010 highlighted as Fisher peak zone.
             Intersection cell is the selected operating point.

  B (right): CMR profile at alpha=0.010 across all priors.
             prior=0.12 bar highlighted; annotation box shows the
             arithmetic derivation and explains why a higher prior
             would be ecologically inconsistent.

Usage:
  python -m experiments.phase3_food_comparison.prior_selection_plot
  python -m experiments.phase3_food_comparison.prior_selection_plot \\
      --csv <path/to/summary.csv> --out <output_dir>
"""
from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.gridspec as gridspec

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

_DEFAULT_CSV = (
    PROJECT_ROOT
    / "outputs/phase3_alpha_prior_sweep/exp_20260516_164359/summary.csv"
)

PHASE4B_INIT_FOOD = 300
GRID_CELLS        = 2500        # 50 x 50
PHASE4B_PRIOR     = round(PHASE4B_INIT_FOOD / GRID_CELLS, 4)  # 0.12
SELECTED_ALPHA    = 0.010


def _load(csv_path: Path) -> tuple[np.ndarray, list[float], list[float]]:
    data: dict[tuple[float, float], float] = {}
    with open(csv_path, newline="") as f:
        for row in csv.DictReader(f):
            a = round(float(row["alpha"]), 6)
            p = round(float(row["prior"]), 6)
            data[(a, p)] = float(row["cmr"])
    alphas = sorted({k[0] for k in data})
    priors = sorted({k[1] for k in data})
    mat = np.array([[data[(a, p)] for p in priors] for a in alphas])
    return mat, alphas, priors


def plot(csv_path: Path, out_dir: Path) -> Path:
    mat, alpha_vals, prior_vals = _load(csv_path)

    ai = min(range(len(alpha_vals)), key=lambda i: abs(alpha_vals[i] - SELECTED_ALPHA))
    pi = min(range(len(prior_vals)), key=lambda i: abs(prior_vals[i] - PHASE4B_PRIOR))

    matplotlib.rcParams.update({
        "font.family":       "sans-serif",
        "font.sans-serif":   ["DejaVu Sans", "Arial", "Helvetica"],
        "axes.spines.top":   False,
        "axes.spines.right": False,
    })

    fig = plt.figure(figsize=(15, 6.5))
    fig.patch.set_facecolor("white")
    fig.suptitle(
        "Phase 3  --  Evidence for food_patch_prior = 0.12  (Phase 4b Ecology Anchor)",
        fontsize=13, fontweight="bold", y=1.02,
    )

    gs = gridspec.GridSpec(1, 2, figure=fig, wspace=0.40, left=0.06, right=0.97)

    # ── Panel A: CMR heatmap ──────────────────────────────────────────────────
    ax = fig.add_subplot(gs[0, 0])

    im = ax.imshow(
        mat.T,          # shape (n_prior, n_alpha)
        aspect="auto", cmap="viridis", origin="lower",
        vmin=0.0, vmax=1.0,
    )

    for j in range(len(prior_vals)):
        for i in range(len(alpha_vals)):
            val = mat[i, j]
            color  = "white" if val < 0.55 else "black"
            weight = "bold"  if (i == ai and j == pi) else "normal"
            ax.text(i, j, f"{val:.2f}",
                    ha="center", va="center", fontsize=8.5,
                    color=color, fontweight=weight)

    # Pink fill + border: prior=0.12 row (Phase 4b anchor)
    ax.add_patch(mpatches.FancyBboxPatch(
        (-0.5, pi - 0.5), len(alpha_vals), 1.0,
        boxstyle="square,pad=0",
        linewidth=3.0, edgecolor="#E91E63", facecolor="#E91E63", alpha=0.09,
        zorder=5,
    ))
    # Blue column: alpha=0.010 (Fisher peak)
    ax.add_patch(mpatches.FancyBboxPatch(
        (ai - 0.5, -0.5), 1.0, len(prior_vals),
        boxstyle="square,pad=0",
        linewidth=2.5, edgecolor="#1565C0", facecolor="#1565C0", alpha=0.08,
        zorder=4,
    ))
    # Orange border: intersection (selected operating point)
    ax.add_patch(mpatches.FancyBboxPatch(
        (ai - 0.5, pi - 0.5), 1.0, 1.0,
        boxstyle="square,pad=0",
        linewidth=3.5, edgecolor="#FF6F00", facecolor="none",
        zorder=6,
    ))

    ax.set_xticks(range(len(alpha_vals)))
    ax.set_xticklabels([f"a={a:.3f}" for a in alpha_vals], fontsize=9)
    ax.set_yticks(range(len(prior_vals)))
    ax.set_yticklabels(
        [f"prior={p:.2f}  (food={int(p * GRID_CELLS)})" for p in prior_vals],
        fontsize=9,
    )
    ax.set_xlabel("Shannon alpha  (food spawn rate)", fontsize=10)
    ax.set_title(
        "A   CMR Heatmap -- all alpha x prior combinations\n"
        "(n = 5 seeds per cell)",
        fontsize=10, fontweight="bold", pad=8,
    )

    legend_handles = [
        mpatches.Patch(
            facecolor="#E91E63", alpha=0.25, edgecolor="#E91E63", linewidth=2.5,
            label=f"Phase 4b ecology anchor  (prior={PHASE4B_PRIOR:.2f},  init_food={PHASE4B_INIT_FOOD})",
        ),
        mpatches.Patch(
            facecolor="#1565C0", alpha=0.18, edgecolor="#1565C0", linewidth=2.0,
            label=f"Fisher peak zone  (alpha={SELECTED_ALPHA:.3f})",
        ),
        mpatches.Patch(
            facecolor="none", edgecolor="#FF6F00", linewidth=3.0,
            label="Selected operating point  (alpha=0.010,  prior=0.12)",
        ),
    ]
    ax.legend(
        handles=legend_handles, loc="upper left", fontsize=7.5,
        framealpha=0.9, edgecolor="#ccc",
        bbox_to_anchor=(0.0, -0.14), borderpad=0.6, ncol=1,
    )
    plt.colorbar(im, ax=ax, label="CMR", shrink=0.85, pad=0.02)

    # ── Panel B: CMR at alpha=0.010 across priors ────────────────────────────
    ax2 = fig.add_subplot(gs[0, 1])

    cmr_slice = mat[ai, :]
    bar_colors = [
        "#E91E63" if abs(p - PHASE4B_PRIOR) < 1e-6 else "#90A4AE"
        for p in prior_vals
    ]
    bars = ax2.barh(
        range(len(prior_vals)), cmr_slice,
        color=bar_colors, edgecolor="white", linewidth=0.8, height=0.6,
    )

    for i, (bar, val) in enumerate(zip(bars, cmr_slice)):
        anchor = abs(prior_vals[i] - PHASE4B_PRIOR) < 1e-6
        ax2.text(
            val + 0.012, bar.get_y() + bar.get_height() / 2,
            f"{val:.3f}", va="center", fontsize=9.5,
            fontweight="bold" if anchor else "normal",
            color="#C2185B" if anchor else "#333",
        )

    ax2.set_yticks(range(len(prior_vals)))
    ax2.set_yticklabels(
        [f"prior={p:.2f}  (food={int(p * GRID_CELLS)})" for p in prior_vals],
        fontsize=9,
    )
    ax2.set_xlabel(f"CMR  at  alpha={SELECTED_ALPHA:.3f}  (Fisher peak)", fontsize=10)
    ax2.set_title(
        f"B   CMR Profile at alpha={SELECTED_ALPHA:.3f}\n"
        "Prior selected by ecology lock, not CMR maximisation",
        fontsize=10, fontweight="bold", pad=8,
    )
    ax2.set_xlim(0.0, 1.20)

    # Dashed reference line at CMR of the anchor
    anchor_cmr = float(cmr_slice[pi])
    ax2.axvline(x=anchor_cmr, color="#E91E63", linewidth=1.2,
                linestyle="--", alpha=0.55, zorder=2)

    # Derivation annotation box
    deriv = (
        "Derivation (not a CMR maximum):\n\n"
        f"  Phase 4b lock:  init_food = {PHASE4B_INIT_FOOD}\n"
        f"  Grid size:      50 x 50 = {GRID_CELLS} cells\n"
        f"\n"
        f"  food_patch_prior\n"
        f"    = {PHASE4B_INIT_FOOD} / {GRID_CELLS} = {PHASE4B_PRIOR:.2f}\n"
        f"\n"
        "Note: prior=0.75 gives higher raw CMR\n"
        "(0.867 vs 0.840), but requires\n"
        "init_food=1875 -- inconsistent\n"
        "with Phase 4b ecology (300)."
    )
    ax2.text(
        0.97, 0.03, deriv,
        transform=ax2.transAxes, ha="right", va="bottom",
        fontsize=8, color="#333", family="monospace",
        bbox=dict(
            boxstyle="round,pad=0.5", facecolor="#FFF8E1",
            edgecolor="#FFB300", linewidth=1.2, alpha=0.95,
        ),
    )

    # Arrow to prior=0.12 bar
    ax2.annotate(
        "Phase 4b anchor\n(CMR = 0.840  viable)",
        xy=(anchor_cmr, pi),
        xytext=(anchor_cmr - 0.30, pi + 1.15),
        fontsize=8.5, color="#C2185B", fontweight="bold", ha="center",
        arrowprops=dict(arrowstyle="->", color="#C2185B", lw=1.5),
    )

    plt.tight_layout(pad=1.5)
    out_path = out_dir / "prior_selection_evidence.png"
    fig.savefig(str(out_path), dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved -> {out_path}")
    return out_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Phase 3 prior selection evidence plot")
    parser.add_argument("--csv", default=None, help="Path to summary.csv")
    parser.add_argument("--out", default=None, help="Output directory")
    args = parser.parse_args()
    csv_path = Path(args.csv) if args.csv else _DEFAULT_CSV
    out_dir  = Path(args.out) if args.out  else csv_path.parent
    out_dir.mkdir(parents=True, exist_ok=True)
    plot(csv_path, out_dir)


if __name__ == "__main__":
    main()
