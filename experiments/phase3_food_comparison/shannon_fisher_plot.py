"""Phase 3 Shannon Entropy + Fisher Information visualization.

Reads alpha_prior_sweep/summary.csv and generates a two-panel figure styled
after the information-theory population-distribution diagram:

  Panel A (top): High-Entropy vs Low-Entropy CMR distribution at extreme alpha values.
    Gradient coloring: red = high density (low surprise), blue = low density (high surprise).
    Individual prior-condition outcomes shown as colored ticks below the curve.

  Panel B (bottom): Likelihood-function mini-plots at each Shannon alpha, plus a
    Fisher Information bar chart showing where CMR is most sensitive to alpha.

Definitions used:
  Shannon Entropy  H(α)  = 0.5 * ln(2πe * Var(CMR | α))   — differential entropy
  Fisher Information I(α) = (∂E[CMR]/∂α)² / Var(CMR | α)  — mechanistic sensitivity

Usage:
  python -m experiments.phase3_food_comparison.shannon_fisher_plot
  python -m experiments.phase3_food_comparison.shannon_fisher_plot --csv path/summary.csv
  python -m experiments.phase3_food_comparison.shannon_fisher_plot --out outputs/mydir
"""
from __future__ import annotations

import argparse
import csv
import math
import sys
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from matplotlib.collections import LineCollection
from matplotlib.colors import LinearSegmentedColormap, Normalize
from scipy.stats import gaussian_kde

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

_DEFAULT_CSV = (
    PROJECT_ROOT
    / "outputs" / "phase3_alpha_prior_sweep" / "exp_20260516_164359" / "summary.csv"
)

# Gradient: blue = high surprise (low density) → red = low surprise (high density)
_CMAP = LinearSegmentedColormap.from_list("surprise", ["#2196F3", "#F44336"])


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def load_cmr_matrix(csv_path: Path) -> tuple[np.ndarray, list[float], list[float]]:
    """Return (matrix[n_alpha, n_prior], alpha_vals, prior_vals) from summary.csv."""
    data: dict[tuple, float] = {}
    with open(csv_path, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            data[(round(float(row["alpha"]), 6), round(float(row["prior"]), 6))] = float(row["cmr"])

    alphas = sorted({k[0] for k in data})
    priors = sorted({k[1] for k in data})
    mat = np.array([[data.get((a, p), np.nan) for p in priors] for a in alphas])
    return mat, alphas, priors


# ---------------------------------------------------------------------------
# Statistics
# ---------------------------------------------------------------------------

def shannon_entropy(cmr_matrix: np.ndarray) -> np.ndarray:
    """Differential Shannon entropy H(α) = 0.5*ln(2πe*σ²) for each alpha row."""
    sigma2 = np.nanvar(cmr_matrix, axis=1, ddof=1)
    sigma2 = np.maximum(sigma2, 1e-9)
    return 0.5 * np.log(2.0 * math.pi * math.e * sigma2)


def fisher_information(cmr_matrix: np.ndarray, alpha_vals: list[float]) -> np.ndarray:
    """Fisher Information I(α) = (∂E[CMR]/∂α)² / Var(CMR|α) for each alpha."""
    mu = np.nanmean(cmr_matrix, axis=1)
    sigma2 = np.nanvar(cmr_matrix, axis=1, ddof=1)
    sigma2 = np.maximum(sigma2, 1e-8)

    a = np.array(alpha_vals, dtype=float)
    n = len(a)
    grad = np.empty(n)
    for i in range(n):
        if i == 0:
            grad[i] = (mu[1] - mu[0]) / max(a[1] - a[0], 1e-12)
        elif i == n - 1:
            grad[i] = (mu[-1] - mu[-2]) / max(a[-1] - a[-2], 1e-12)
        else:
            grad[i] = (mu[i + 1] - mu[i - 1]) / max(a[i + 1] - a[i - 1], 1e-12)

    return grad ** 2 / sigma2


# ---------------------------------------------------------------------------
# Drawing helpers
# ---------------------------------------------------------------------------

def _kde_gradient(ax: plt.Axes, data: np.ndarray,
                  bw: float = 0.22,
                  x_lo: float = 0.0, x_hi: float = 1.05,
                  alpha_fill: float = 0.72,
                  show_ticks: bool = False) -> float:
    """Draw gradient-coloured KDE: red=peak(low surprise), blue=tail(high surprise).
    Returns the KDE peak density value."""
    kde = gaussian_kde(data, bw_method=bw)

    margin = 0.08
    xs = np.linspace(max(x_lo, data.min() - margin),
                     min(x_hi, data.max() + margin), 300)
    ys = kde(xs)
    peak = ys.max()
    norm = Normalize(vmin=0, vmax=peak)

    # Fill: 160 thin vertical slices, each coloured by its local density
    n_sl = 160
    xs_sl = np.linspace(xs[0], xs[-1], n_sl)
    ys_sl = kde(xs_sl)
    dx = (xs_sl[-1] - xs_sl[0]) / n_sl
    for xi, yi in zip(xs_sl, ys_sl):
        c = _CMAP(norm(yi))
        ax.fill_between([xi - dx / 2, xi + dx / 2], 0, yi,
                        color=c, alpha=alpha_fill, linewidth=0)

    # Gradient outline using LineCollection
    pts = np.array([xs, ys]).T.reshape(-1, 1, 2)
    segs = np.concatenate([pts[:-1], pts[1:]], axis=1)
    lc = LineCollection(segs, cmap=_CMAP, norm=norm, linewidth=2.0, zorder=5)
    lc.set_array(ys[:-1])
    ax.add_collection(lc)

    ax.set_xlim(xs[0] - 0.04, xs[-1] + 0.04)
    ax.set_ylim(0, peak * 1.38)

    if show_ticks:
        # Individual condition ticks below x-axis, coloured by their surprise
        density_at_pts = kde(data)
        for xi, di in zip(data, density_at_pts):
            c = _CMAP(norm(di))
            ax.plot([xi, xi], [0, -peak * 0.08], color=c,
                    linewidth=2.5, clip_on=False, solid_capstyle="butt", zorder=6)

    return peak


def _style(ax: plt.Axes) -> None:
    for spine in ["top", "right"]:
        ax.spines[spine].set_visible(False)
    ax.tick_params(labelsize=7)


# ---------------------------------------------------------------------------
# Main figure
# ---------------------------------------------------------------------------

def plot(csv_path: Path, out: Path) -> Path:
    mat, alpha_vals, prior_vals = load_cmr_matrix(csv_path)
    H = shannon_entropy(mat)
    FI = fisher_information(mat, alpha_vals)
    FI_norm = FI / FI.max() if FI.max() > 0 else FI
    n = len(alpha_vals)

    # ── global rcParams for this figure ──────────────────────────────────────
    matplotlib.rcParams.update({
        "font.family":       "sans-serif",
        "font.sans-serif":   ["DejaVu Sans", "Arial", "Helvetica"],
        "axes.titlesize":    10,
        "axes.labelsize":    9,
        "xtick.labelsize":   8,
        "ytick.labelsize":   8,
        "axes.spines.top":   False,
        "axes.spines.right": False,
    })

    fig = plt.figure(figsize=(15, 14))
    fig.patch.set_facecolor("white")

    # ── GridSpec: three independent grids with explicit y-coordinates ─────────
    #
    #   y=0.975 ──── suptitle (fig.suptitle)
    #   y=0.935 ──── "A  Population Distribution"  (fig.text)
    #   y=0.575–0.895 ── Panel A  (two distributions)
    #
    #   y=0.560 ──── "B  Likelihood Function"  (fig.text)
    #   y=0.355–0.540 ── Panel B  (five mini distributions)
    #   y=0.338 ──── "W →" axis label  (fig.text)
    #
    #   y=0.065–0.305 ── Fisher Information bar chart
    #
    gs_A = gridspec.GridSpec(
        1, 2, figure=fig,
        left=0.07, right=0.96, top=0.862, bottom=0.548,
        wspace=0.30,
    )
    gs_B = gridspec.GridSpec(
        1, n, figure=fig,
        left=0.07, right=0.96, top=0.515, bottom=0.330,
        wspace=0.25,
    )
    gs_C = gridspec.GridSpec(
        1, 1, figure=fig,
        left=0.07, right=0.96, top=0.270, bottom=0.055,
    )

    # ── suptitle — single line, enough gap to Panel A ─────────────────────────
    fig.suptitle(
        "Phase 3 — Shannon Entropy & Fisher Information  |  CMR w.r.t. Food Mechanism α",
        fontsize=13, fontweight="bold", y=0.980, color="#111",
    )

    # ── Panel A row header (between suptitle and the subplots) ────────────────
    fig.text(0.035, 0.944, "A", fontsize=22, fontweight="bold", va="top", color="#111")
    fig.text(0.515, 0.944, "Population Distribution",
             ha="center", va="top", fontsize=12, fontweight="bold", color="#222")

    # ── Panel A: High Entropy ─────────────────────────────────────────────────
    ax_hi = fig.add_subplot(gs_A[0, 0])
    _kde_gradient(ax_hi, mat[0, :], bw=0.22, show_ticks=False, alpha_fill=0.76)
    ax_hi.set_title(
        "High Entropy  (α = %.3f)\nSpread CMR — uncertain outcomes" % alpha_vals[0],
        fontsize=10, fontweight="bold", pad=6, color="#222",
    )
    ax_hi.set_xlabel("CMR value", fontsize=9)
    ax_hi.set_ylabel("Density", fontsize=9)
    ax_hi.text(0.03, 0.97, "H = %.2f nats" % H[0],
               transform=ax_hi.transAxes, fontsize=8.5, va="top",
               color="#444", style="italic",
               bbox=dict(boxstyle="round,pad=0.3", facecolor="white",
                         edgecolor="#bbb", linewidth=0.8, alpha=0.9))
    _style(ax_hi)

    # ── Panel A: Low Entropy ──────────────────────────────────────────────────
    ax_lo = fig.add_subplot(gs_A[0, 1])
    _kde_gradient(ax_lo, mat[-1, :], bw=0.10, show_ticks=False, alpha_fill=0.76)
    ax_lo.set_title(
        "Low Entropy  (α = %.3f)\nPeaked CMR — predictable outcomes" % alpha_vals[-1],
        fontsize=10, fontweight="bold", pad=6, color="#222",
    )
    ax_lo.set_xlabel("CMR value", fontsize=9)
    ax_lo.set_ylabel("Density", fontsize=9)
    ax_lo.text(0.03, 0.97, "H = %.2f nats" % H[-1],
               transform=ax_lo.transAxes, fontsize=8.5, va="top",
               color="#444", style="italic",
               bbox=dict(boxstyle="round,pad=0.3", facecolor="white",
                         edgecolor="#bbb", linewidth=0.8, alpha=0.9))
    _style(ax_lo)
    from matplotlib.patches import Patch
    ax_lo.legend(
        handles=[
            Patch(facecolor="#F44336", alpha=0.78, label="red  = low surprise  (high density)"),
            Patch(facecolor="#2196F3", alpha=0.78, label="blue = high surprise (low density)"),
        ],
        loc="upper right", fontsize=8, framealpha=0.90,
        edgecolor="#ccc", borderpad=0.5, handlelength=1.2,
    )

    # ── Panel B row header ────────────────────────────────────────────────────
    # "B" label left of Panel B; "Likelihood Function" right of Panel B (mirroring reference image)
    fig.text(0.035, 0.527, "B", fontsize=22, fontweight="bold", va="top", color="#111")
    fig.text(0.968, 0.423, "Likelihood\nFunction",
             ha="right", va="center", fontsize=9, color="#444", style="italic")

    # ── Panel B: mini likelihood distributions ───────────────────────────────
    for k in range(n):
        ax_m = fig.add_subplot(gs_B[0, k])
        _kde_gradient(ax_m, mat[k, :], bw=0.24, alpha_fill=0.65)
        ax_m.set_title("α = %.3f" % alpha_vals[k],
                       fontsize=9, fontweight="bold", pad=4, color="#222")
        ax_m.set_xlabel("CMR", fontsize=8)
        ax_m.set_xlim(0.0, 1.1)
        # Negative H is expected for differential entropy when σ < 1/√(2πe) ≈ 0.24
        # Use bold + box so the minus sign is clearly readable
        h_color = "#1565C0" if H[k] < 0 else "#444"
        ax_m.text(0.97, 0.97, "H=%+.2f" % H[k],
                  transform=ax_m.transAxes, ha="right", va="top",
                  fontsize=9, fontweight="bold", color=h_color,
                  bbox=dict(boxstyle="round,pad=0.2", facecolor="white",
                            edgecolor="#ccc", linewidth=0.5, alpha=0.90))
        _style(ax_m)
        ax_m.tick_params(labelsize=7)
        if k == 0:
            ax_m.set_ylabel("Density", fontsize=8)

    # ── Fisher Information ────────────────────────────────────────────────────
    ax_fi = fig.add_subplot(gs_C[0, 0])
    bar_colors = plt.cm.RdYlGn(FI_norm)
    bars = ax_fi.bar(range(n), FI_norm, color=bar_colors,
                     edgecolor="white", linewidth=0.8, width=0.55)

    for bar, fi_n in zip(bars, FI_norm):
        ax_fi.text(bar.get_x() + bar.get_width() / 2,
                   bar.get_height() + 0.025,
                   "%.3f" % fi_n,
                   ha="center", va="bottom", fontsize=10,
                   fontweight="bold", color="#222")

    ax_fi.set_xticks(range(n))
    ax_fi.set_xticklabels(["α = %.3f" % a for a in alpha_vals], fontsize=9)
    ax_fi.set_ylabel("Fisher Information  (normalised)", fontsize=10)
    # Single-line title above axes; explanation text placed inside axes to avoid overlap
    ax_fi.set_title(
        "Fisher Information   I(α) = (∂E[CMR]/∂α)²  /  Var(CMR | α)",
        fontsize=10, fontweight="bold", pad=5, color="#222",
    )
    ax_fi.text(0.5, 0.93,
               "High I  →  CMR is most sensitive to the food mechanism at this α",
               transform=ax_fi.transAxes, ha="center", va="top",
               fontsize=8.5, color="#555", style="italic")
    # Note: negative H (blue labels above) is correct differential entropy for σ < 1/√(2πe)≈0.24
    # H decreases left→right (α=0.000: +0.05 → α=0.010: −2.02); slight rise at α=0.020 is real data
    ax_fi.text(0.99, 0.93,
               "H<0 (blue) = very low variance (correct for Gaussian differential entropy)",
               transform=ax_fi.transAxes, ha="right", va="top",
               fontsize=7.5, color="#1565C0", style="italic")
    ax_fi.set_ylim(0, 1.30)
    ax_fi.set_xlabel("Shannon α  (food spawn rate)    →    W", fontsize=10)
    _style(ax_fi)

    out_path = out / "shannon_fisher_analysis.png"
    fig.savefig(str(out_path), dpi=150, bbox_inches="tight")
    plt.close(fig)
    print("Saved -> %s" % out_path)
    return out_path


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Phase 3 Shannon Entropy + Fisher Info plot")
    parser.add_argument("--csv", type=str, default=None,
                        help="Path to alpha_prior_sweep summary.csv")
    parser.add_argument("--out", type=str, default=None,
                        help="Output directory (default: same directory as csv)")
    args = parser.parse_args()

    csv_path = Path(args.csv) if args.csv else _DEFAULT_CSV
    if not csv_path.exists():
        print("Error: CSV not found: %s" % csv_path)
        print("Run:  python -m experiments.phase3_food_comparison.alpha_prior_sweep  first.")
        sys.exit(1)

    out = Path(args.out) if args.out else csv_path.parent
    out.mkdir(parents=True, exist_ok=True)
    plot(csv_path, out)


if __name__ == "__main__":
    main()
