# experiments/phase3a_motivation_sweep/plot.py
"""Phase 3a heatmap plots. All plots share the same care_w × forage_w axes,
averaged over self_w."""
import os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker

matplotlib.rcParams.update({
    "font.family": "sans-serif",
    "axes.titlesize": 12,
    "axes.labelsize": 11,
    "xtick.labelsize": 9,
    "ytick.labelsize": 9,
    "figure.facecolor": "white",
    "xtick.direction": "in",
    "ytick.direction": "in",
})


# ── Shared helpers ────────────────────────────────────────────────────────────

def _build_grid(agg: list[dict], metric: str) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Return (care_vals, forage_vals, grid[forage, care]) averaged over self_w."""
    from collections import defaultdict
    care_vals = sorted(set(r["care_w"] for r in agg))
    forage_vals = sorted(set(r["forage_w"] for r in agg))
    ci = {v: i for i, v in enumerate(care_vals)}
    fi = {v: i for i, v in enumerate(forage_vals)}

    sums = np.zeros((len(forage_vals), len(care_vals)))
    counts = np.zeros_like(sums)

    for r in agg:
        row, col = fi[r["forage_w"]], ci[r["care_w"]]
        sums[row, col] += r[metric]
        counts[row, col] += 1

    grid = np.divide(sums, counts, where=counts > 0, out=np.full_like(sums, np.nan))
    return np.array(care_vals), np.array(forage_vals), grid


def _heatmap(
    care_vals, forage_vals, grid,
    title: str, label: str, path: str,
    cmap: str = "viridis",
    vmin: float | None = None,
    vmax: float | None = None,
    canonical: dict | None = None,
) -> None:
    fig, ax = plt.subplots(figsize=(6, 5))
    im = ax.imshow(
        grid, origin="lower", aspect="auto", cmap=cmap,
        vmin=vmin, vmax=vmax,
        extent=[
            care_vals[0] - 0.1, care_vals[-1] + 0.1,
            forage_vals[0] - 0.1, forage_vals[-1] + 0.1,
        ],
    )
    cbar = fig.colorbar(im, ax=ax)
    cbar.set_label(label, fontsize=10)

    ax.set_xlabel("care_w")
    ax.set_ylabel("forage_w")
    ax.set_title(title)
    ax.set_xticks(care_vals)
    ax.set_yticks(forage_vals)

    # Mark canonical genome
    if canonical:
        ax.plot(canonical["care_w"], canonical["forage_w"],
                marker="*", color="red", markersize=14, label="canonical", zorder=5)
        ax.legend(fontsize=8, loc="upper left")

    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


# ── Four heatmaps ─────────────────────────────────────────────────────────────

def plot_child_survival(agg, canonical, out_dir):
    c, f, g = _build_grid(agg, "child_survival_rate")
    _heatmap(c, f, g,
             title="Child survival rate  (averaged over self_w)",
             label="children matured / children born",
             path=os.path.join(out_dir, "heatmap_child_survival.png"),
             cmap="YlGn", vmin=0.0, vmax=1.0,
             canonical=canonical)


def plot_child_energy(agg, canonical, out_dir):
    c, f, g = _build_grid(agg, "mean_child_final_energy")
    _heatmap(c, f, g,
             title="Mean child final energy  (averaged over self_w)",
             label="energy at maturation or starvation",
             path=os.path.join(out_dir, "heatmap_child_energy.png"),
             cmap="plasma", vmin=0.0, vmax=1.0,
             canonical=canonical)


def plot_mother_survival(agg, canonical, out_dir):
    c, f, g = _build_grid(agg, "mother_survival_rate")
    _heatmap(c, f, g,
             title="Mother survival rate  (averaged over self_w)",
             label="mothers alive at tick 400 / 15",
             path=os.path.join(out_dir, "heatmap_mother_survival.png"),
             cmap="Blues", vmin=0.0, vmax=1.0,
             canonical=canonical)


def plot_mean_mother_energy(agg, canonical, out_dir):
    c, f, g = _build_grid(agg, "mean_mother_energy")
    _heatmap(c, f, g,
             title="Mean mother energy at tick 400  (averaged over self_w)",
             label="mean energy of alive mothers",
             path=os.path.join(out_dir, "heatmap_mean_mother_energy.png"),
             cmap="coolwarm", vmin=0.0, vmax=1.0,
             canonical=canonical)


def plot_all(agg: list[dict], canonical: dict | None, out_dir: str) -> None:
    plot_child_survival(agg, canonical, out_dir)
    plot_child_energy(agg, canonical, out_dir)
    plot_mother_survival(agg, canonical, out_dir)
    plot_mean_mother_energy(agg, canonical, out_dir)
