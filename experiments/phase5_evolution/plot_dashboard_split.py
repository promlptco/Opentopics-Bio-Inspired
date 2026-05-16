"""Split the 9-panel dashboard into 9 separate academic-style PNG files.

Style: publication-quality, mean ± 95 % CI band, light per-seed traces,
no decorative scatter, serif-friendly font stack, muted colour palette.

Output files (in <run-dir>/):
  01_genome_care.png            07_child_survival.png
  02_expressed_care.png         08_generation_depth.png
  03_plasticity_innateness.png  09_learning_rate.png
  04_genome_behavior_distance.png
  05_population.png
  06_energy.png

Usage:
  python -m experiments.phase5_evolution.plot_dashboard_split
  python -m experiments.phase5_evolution.plot_dashboard_split \
      --input-dir outputs/phase5_evolution/block2_main_mut_on_plast_on
"""
from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_RUN  = (
    PROJECT_ROOT / "outputs" / "phase5_evolution" / "block2_main_mut_on_plast_on"
)

# ── Typography & layout ───────────────────────────────────────────────────────
_FONT = ["Palatino Linotype", "Palatino", "Georgia", "DejaVu Serif", "serif"]

plt.rcParams.update({
    # Font
    "font.family": "serif",
    "font.serif": _FONT,
    "font.size": 11,
    "axes.titlesize": 13,
    "axes.labelsize": 11,
    "xtick.labelsize": 9,
    "ytick.labelsize": 9,
    "legend.fontsize": 9,
    # Spines
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.linewidth": 0.9,
    # Ticks
    "xtick.direction": "out",
    "ytick.direction": "out",
    "xtick.major.size": 4,
    "ytick.major.size": 4,
    "xtick.major.width": 0.8,
    "ytick.major.width": 0.8,
    # Grid
    "axes.grid": True,
    "grid.color": "#e5e5e5",
    "grid.linewidth": 0.6,
    "axes.facecolor": "white",
    "figure.facecolor": "white",
})

# Muted, colour-blind-friendly palette (Wong 2011)
C = {
    "blue":   "#0072B2",
    "orange": "#E69F00",
    "green":  "#009E73",
    "red":    "#D55E00",
    "purple": "#CC79A7",
    "sky":    "#56B4E9",
    "yellow": "#F0E442",
    "black":  "#000000",
    "gray":   "#888888",
    "neutral":"#CC0000",   # 1/3 reference
}

FIGSIZE   = (7.5, 4.0)   # ~single-column wide for A4 / IEEE
DPI       = 200
CI_Z      = 1.96          # 95 % CI
SEED_ALPHA = 0.12         # per-seed trace opacity


# ── Data helpers ──────────────────────────────────────────────────────────────

def _load(run_dir: Path) -> pd.DataFrame:
    p = run_dir / "snapshots.csv"
    if not p.exists():
        raise FileNotFoundError(f"snapshots.csv not found in {run_dir}")
    df = pd.read_csv(p)
    if "child_survival_rate" not in df.columns and "c_matr_cum" in df.columns:
        df["child_survival_rate"] = df["c_matr_cum"]
    if "highest_generation" not in df.columns:
        df["highest_generation"] = df.get("mean_generation", 0.0)
    return df


def _ci(df: pd.DataFrame, col: str) -> pd.DataFrame:
    """Mean ± 95 % CI across seeds per tick."""
    agg = (
        df.groupby("tick")[col]
        .agg(mean="mean", std="std", n="count")
        .reset_index()
        .sort_values("tick")
    )
    agg["std"]  = agg["std"].fillna(0.0)
    agg["se"]   = agg["std"] / np.sqrt(agg["n"].clip(lower=1))
    agg["lo"]   = agg["mean"] - CI_Z * agg["se"]
    agg["hi"]   = agg["mean"] + CI_Z * agg["se"]
    return agg


# ── Drawing primitives ────────────────────────────────────────────────────────

def _seed_traces(ax: plt.Axes, df: pd.DataFrame, col: str, color: str) -> None:
    """Thin per-seed lines in the background."""
    for seed, g in df.groupby("seed"):
        g = g.sort_values("tick")
        ax.plot(g["tick"], g[col], color=color, linewidth=0.5,
                alpha=SEED_ALPHA, zorder=1)


def _mean_band(
    ax: plt.Axes,
    agg: pd.DataFrame,
    color: str,
    label: str,
    ylo: float = 0.0,
    yhi: float = 1.0,
) -> None:
    lo = agg["lo"].clip(ylo, yhi)
    hi = agg["hi"].clip(ylo, yhi)
    ax.fill_between(agg["tick"], lo, hi, color=color, alpha=0.18, zorder=2)
    ax.plot(agg["tick"], agg["mean"], color=color, linewidth=1.8,
            label=label, zorder=3)


def _neutral(ax: plt.Axes) -> None:
    ax.axhline(1/3, color=C["neutral"], linestyle=":", linewidth=1.2,
               alpha=0.9, label="Neutral (1/3)", zorder=4)


def _finalize(
    ax: plt.Axes,
    fig: plt.Figure,
    ylabel: str,
    ylim: tuple[float, float] | None = None,
    legend_loc: str = "best",
) -> None:
    ax.set_xlabel("Simulation tick")
    ax.set_ylabel(ylabel)
    ax.xaxis.set_major_formatter(mticker.FuncFormatter(
        lambda x, _: f"{int(x/1000)}k" if x >= 1000 else str(int(x))
    ))
    if ylim is not None:
        ax.set_ylim(*ylim)
    handles, labels = ax.get_legend_handles_labels()
    if handles:
        ax.legend(handles, labels, loc=legend_loc, frameon=True,
                  framealpha=0.9, edgecolor="#cccccc")
    fig.tight_layout()


def _save(fig: plt.Figure, path: Path) -> None:
    fig.savefig(path, dpi=DPI, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved -> {path.name}")


def _fig(title: str) -> tuple[plt.Figure, plt.Axes]:
    fig, ax = plt.subplots(figsize=FIGSIZE)
    ax.set_title(title, fontweight="bold", pad=6)
    return fig, ax


# ── 9 panels ──────────────────────────────────────────────────────────────────

def p01(df: pd.DataFrame, out: Path) -> None:
    fig, ax = _fig("Genome Care Weight")
    _seed_traces(ax, df, "mean_genome_care", C["blue"])
    _mean_band(ax, _ci(df, "mean_genome_care"), C["blue"], "Mean ± 95% CI")
    _neutral(ax)
    _finalize(ax, fig, "Genome weight", ylim=(0.2, 0.55), legend_loc="upper left")
    _save(fig, out / "01_genome_care.png")


def p02(df: pd.DataFrame, out: Path) -> None:
    fig, ax = _fig("Expressed (Phenotypic) Care Weight")
    _seed_traces(ax, df, "mean_expressed_care", C["blue"])
    _mean_band(ax, _ci(df, "mean_expressed_care"), C["blue"], "Mean ± 95% CI")
    _neutral(ax)
    _finalize(ax, fig, "Expressed weight", ylim=(0, 0.7), legend_loc="upper right")
    _save(fig, out / "02_expressed_care.png")


def p03(df: pd.DataFrame, out: Path) -> None:
    fig, ax = _fig("Plasticity Coefficient and Innateness Index")
    _seed_traces(ax, df, "mean_plasticity", C["blue"])
    _mean_band(ax, _ci(df, "mean_plasticity"), C["blue"], "Plasticity (mean ± 95% CI)")

    agg_i = _ci(df, "innateness_index")
    ax.fill_between(agg_i["tick"], agg_i["lo"].clip(0, 1),
                    agg_i["hi"].clip(0, 1), color=C["orange"], alpha=0.18, zorder=2)
    ax.plot(agg_i["tick"], agg_i["mean"], color=C["orange"], linewidth=1.6,
            linestyle="--", label="Innateness (mean ± 95% CI)", zorder=3)

    _finalize(ax, fig, "Coefficient", ylim=(0, 1.05), legend_loc="lower left")
    _save(fig, out / "03_plasticity_innateness.png")


def p04(df: pd.DataFrame, out: Path) -> None:
    fig, ax = _fig("Genome–Behaviour Distance  [TV(expressed, genome)]")
    _seed_traces(ax, df, "genome_behavior_distance", C["purple"])
    _mean_band(ax, _ci(df, "genome_behavior_distance"), C["purple"],
               "Mean ± 95% CI", ylo=0, yhi=1)
    ymax = max(0.35, float(df["genome_behavior_distance"].quantile(0.99)) * 1.1)
    _finalize(ax, fig, "Total variation distance", ylim=(0, ymax),
              legend_loc="upper right")
    _save(fig, out / "04_genome_behavior_distance.png")


def p05(df: pd.DataFrame, out: Path) -> None:
    fig, ax = _fig("Population Size Over Time")
    _seed_traces(ax, df, "n_mothers", C["blue"])
    _mean_band(ax, _ci(df, "n_mothers"), C["blue"], "Mothers (mean ± 95% CI)",
               ylo=0, yhi=9999)
    for seed, g in df.groupby("seed"):
        g = g.sort_values("tick")
        ax.plot(g["tick"], g["n_children"], color=C["purple"], linewidth=0.5,
                alpha=SEED_ALPHA, zorder=1)
    agg_c = _ci(df, "n_children")
    ax.fill_between(agg_c["tick"], agg_c["lo"].clip(0),
                    agg_c["hi"], color=C["purple"], alpha=0.18, zorder=2)
    ax.plot(agg_c["tick"], agg_c["mean"], color=C["purple"], linewidth=1.6,
            linestyle="--", label="Children (mean ± 95% CI)", zorder=3)
    _finalize(ax, fig, "Count", legend_loc="upper right")
    _save(fig, out / "05_population.png")


def p06(df: pd.DataFrame, out: Path) -> None:
    fig, ax = _fig("Mean Energy — Mothers and Children")
    _seed_traces(ax, df, "mean_mother_energy", C["blue"])
    _mean_band(ax, _ci(df, "mean_mother_energy"), C["blue"],
               "Mother energy (mean ± 95% CI)")
    for seed, g in df.groupby("seed"):
        g = g.sort_values("tick")
        ax.plot(g["tick"], g["mean_child_energy"], color=C["green"], linewidth=0.5,
                alpha=SEED_ALPHA, zorder=1)
    agg_c = _ci(df, "mean_child_energy")
    ax.fill_between(agg_c["tick"], agg_c["lo"].clip(0, 1),
                    agg_c["hi"].clip(0, 1), color=C["green"], alpha=0.18, zorder=2)
    ax.plot(agg_c["tick"], agg_c["mean"], color=C["green"], linewidth=1.6,
            linestyle="--", label="Child energy (mean ± 95% CI)", zorder=3)
    _finalize(ax, fig, "Mean energy (0–1)", ylim=(0, 1.05), legend_loc="lower left")
    _save(fig, out / "06_energy.png")


def p07(df: pd.DataFrame, out: Path) -> None:
    col = "child_survival_rate"
    fig, ax = _fig("Child Survival / Maturation Rate")
    _seed_traces(ax, df, col, C["green"])
    _mean_band(ax, _ci(df, col), C["green"], "Mean ± 95% CI")
    _finalize(ax, fig, "Survival rate (0–1)", ylim=(0, 1.05), legend_loc="upper left")
    _save(fig, out / "07_child_survival.png")


def p08(df: pd.DataFrame, out: Path) -> None:
    fig, ax = _fig("Generational Depth")
    _seed_traces(ax, df, "mean_generation", C["blue"])
    _mean_band(ax, _ci(df, "mean_generation"), C["blue"],
               "Mean generation (mean ± 95% CI)", ylo=0, yhi=9999)
    agg_h = _ci(df, "highest_generation")
    ax.plot(agg_h["tick"], agg_h["mean"], color=C["orange"], linewidth=1.6,
            linestyle="--", label="Highest generation (mean)", zorder=3)
    _finalize(ax, fig, "Generation", legend_loc="upper left")
    _save(fig, out / "08_generation_depth.png")


def p09(df: pd.DataFrame, out: Path) -> None:
    fig, ax = _fig("Mean Learning Rate")
    _seed_traces(ax, df, "mean_learning_rate", C["red"])
    _mean_band(ax, _ci(df, "mean_learning_rate"), C["red"],
               "Mean ± 95% CI", ylo=0, yhi=1)
    _finalize(ax, fig, "Learning rate", legend_loc="lower left")
    _save(fig, out / "09_learning_rate.png")


# ── Entry point ───────────────────────────────────────────────────────────────

def run(run_dir: Path, output_dir: Path) -> None:
    df = _load(run_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    for fn in [p01, p02, p03, p04, p05, p06, p07, p08, p09]:
        fn(df, output_dir)
    print(f"\n[ok] 9 academic plots saved to {output_dir}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-dir",  type=str, default=str(DEFAULT_RUN))
    parser.add_argument("--output-dir", type=str, default=None)
    args    = parser.parse_args()
    in_dir  = Path(args.input_dir)
    out_dir = Path(args.output_dir) if args.output_dir else in_dir
    run(in_dir, out_dir)


if __name__ == "__main__":
    main()
