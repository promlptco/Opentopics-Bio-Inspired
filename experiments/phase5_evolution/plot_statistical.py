"""Statistical evolution plots — one figure per motivation, separate files.

For each motivation (CARE, FORAGE, SELF) produces:
  - genome_<motivation>.png    genome weight over ticks
  - expressed_<motivation>.png expressed weight over ticks

Each figure: mean line (bold) + ±1 SD shaded band + individual seed dots.
X-axis = simulation tick; Y-axis = weight [0, 1].

Usage:
  python -m experiments.phase5_evolution.plot_statistical
  python -m experiments.phase5_evolution.plot_statistical --input-dir outputs/phase5_evolution/block2_main_mut_on_plast_on --output-dir outputs/phase5_evolution/block2_main_mut_on_plast_on
"""
from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

matplotlib.rcParams.update({
    "font.family": "sans-serif",
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.linewidth": 0.8,
})

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_RUN  = PROJECT_ROOT / "outputs" / "phase5_evolution" / "block2_main_mut_on_plast_on"


MOTIVATIONS = [
    ("care",   "#2196F3", "Care"),
    ("forage", "#FF9800", "Forage"),
    ("self",   "#4CAF50", "Self"),
]

# Down-sample ticks for the scatter layer so dots don't completely fill the plot.
SCATTER_EVERY = 10   # plot seed dots every N ticks


def _load(run_dir: Path) -> pd.DataFrame:
    path = run_dir / "snapshots.csv"
    if not path.exists():
        raise FileNotFoundError(f"snapshots.csv not found in {run_dir}")
    return pd.read_csv(path)


def _style(ax: plt.Axes, title: str, ylabel: str = "Weight") -> None:
    ax.set_xlabel("Simulation tick", fontsize=12)
    ax.set_ylabel(ylabel, fontsize=12)
    ax.set_title(title, fontsize=13, fontweight="bold", pad=10)
    ax.set_ylim(-0.02, 1.02)
    ax.grid(True, linestyle="--", linewidth=0.5, alpha=0.4)
    ax.tick_params(labelsize=10)


def _plot_one(
    df: pd.DataFrame,
    col_mean: str,
    col_std: str,
    color: str,
    title: str,
    neutral_line: bool,
    output_path: Path,
) -> None:
    """One standalone statistical figure."""
    seeds = sorted(df["seed"].unique())

    # Aggregate across seeds at each tick
    agg = (
        df.groupby("tick")[col_mean]
        .agg(mean_val="mean", sd_val="std", n="count")
        .reset_index()
        .sort_values("tick")
    )
    agg["sd_val"] = agg["sd_val"].fillna(0.0)

    fig, ax = plt.subplots(figsize=(10, 5))

    # ── Seed scatter dots (sub-sampled) ──────────────────────────────────────
    tick_vals = sorted(df["tick"].unique())
    scatter_ticks = set(tick_vals[::SCATTER_EVERY])
    scatter_df = df[df["tick"].isin(scatter_ticks)]
    ax.scatter(
        scatter_df["tick"],
        scatter_df[col_mean],
        s=18,
        color=color,
        alpha=0.22,
        zorder=2,
        label="Individual seed",
        linewidths=0,
    )

    # ── ±1 SD band ───────────────────────────────────────────────────────────
    lo = (agg["mean_val"] - agg["sd_val"]).clip(0.0, 1.0)
    hi = (agg["mean_val"] + agg["sd_val"]).clip(0.0, 1.0)
    ax.fill_between(
        agg["tick"], lo, hi,
        color=color, alpha=0.18, zorder=3, label="±1 SD",
    )

    # ── Mean line ─────────────────────────────────────────────────────────────
    ax.plot(
        agg["tick"], agg["mean_val"],
        color=color, linewidth=2.4, zorder=4,
        label=f"Mean (n={len(seeds)} seeds)",
    )

    # ── Neutral reference ─────────────────────────────────────────────────────
    if neutral_line:
        ax.axhline(
            1 / 3, color="red", linestyle="--", linewidth=1.5,
            alpha=0.85, zorder=5, label="Neutral (1/3)",
        )

    _style(ax, title)
    ax.legend(loc="upper right", fontsize=9, framealpha=0.9)
    plt.tight_layout()
    fig.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved -> {output_path}")


def run(run_dir: Path, output_dir: Path) -> None:
    df = _load(run_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    for key, color, label in MOTIVATIONS:
        # Genome
        _plot_one(
            df,
            col_mean=f"mean_genome_{key}",
            col_std=f"std_genome_{key}",
            color=color,
            title=f"Genome {label} Weight — Evolution Over Time\n(mean ± 1 SD across seeds · dots = individual seeds)",
            neutral_line=True,
            output_path=output_dir / f"genome_{key}.png",
        )
        # Expressed
        _plot_one(
            df,
            col_mean=f"mean_expressed_{key}",
            col_std=f"std_expressed_{key}",
            color=color,
            title=f"Expressed {label} Weight — Phenotypic Expression Over Time\n(mean ± 1 SD across seeds · dots = individual seeds)",
            neutral_line=True,
            output_path=output_dir / f"expressed_{key}.png",
        )

    print(f"\n[ok] 6 plots saved to {output_dir}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Statistical per-motivation evolution plots")
    parser.add_argument(
        "--input-dir", type=str, default=str(DEFAULT_RUN),
        help="Run directory containing snapshots.csv",
    )
    parser.add_argument(
        "--output-dir", type=str, default=None,
        help="Output directory for PNG files (default: same as input-dir)",
    )
    args = parser.parse_args()
    in_dir  = Path(args.input_dir)
    out_dir = Path(args.output_dir) if args.output_dir else in_dir
    run(in_dir, out_dir)


if __name__ == "__main__":
    main()
