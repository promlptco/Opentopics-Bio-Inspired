"""Phase 5 - Baldwin trajectory visualization."""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib
import matplotlib.pyplot as plt
import pandas as pd

matplotlib.rcParams["font.family"] = "sans-serif"
matplotlib.rcParams["axes.linewidth"] = 0.5
matplotlib.rcParams["axes.spines.top"] = False
matplotlib.rcParams["axes.spines.right"] = False
matplotlib.rcParams["xtick.direction"] = "in"
matplotlib.rcParams["ytick.direction"] = "in"


class EvolutionPlotter:
    """Reads snapshots.csv and produces a Phase 5 dashboard figure."""

    def __init__(self, input_dir: Path | str) -> None:
        self._input_dir = Path(input_dir)

    def plot(
        self,
        output_file: Path | str | None = None,
        checkpoint: int | None = None,
    ) -> None:
        """Produce and save the Phase 5 dashboard figure.

        If checkpoint is provided, only rows at ticks divisible by that value
        are plotted. This is useful both for coarse-grained plotting of old
        runs and for matching the snapshot cadence used during a run.
        """
        csv_path = self._input_dir / "snapshots.csv"
        if not csv_path.exists():
            raise FileNotFoundError(f"snapshots.csv not found at {csv_path}")

        df = self._prepare_dataframe(pd.read_csv(csv_path))
        if checkpoint is not None:
            if checkpoint <= 0:
                raise ValueError("checkpoint must be a positive integer")
            df = df[df["tick"] % checkpoint == 0].copy()
            if df.empty:
                raise ValueError(
                    f"No snapshot rows matched checkpoint={checkpoint} in {csv_path}"
                )
        seeds = sorted(df["seed"].unique())
        colors = plt.cm.tab20(range(len(seeds)))

        fig, axes = plt.subplots(3, 3, figsize=(18, 13))
        fig.suptitle(
            "Phase 5: Baldwin Emergence Evolution",
            fontsize=14,
            fontweight="bold",
            y=0.995,
        )

        self._plot_genome_care(axes[0, 0], df, seeds, colors)
        self._plot_expressed_care(axes[0, 1], df, seeds, colors)
        self._plot_plasticity(axes[0, 2], df, seeds, colors)
        self._plot_genome_behavior_distance(axes[1, 0], df, seeds, colors)
        self._plot_population(axes[1, 1], df, seeds, colors)
        self._plot_energy(axes[1, 2], df, seeds, colors)
        self._plot_child_survival(axes[2, 0], df, seeds, colors)
        self._plot_generation(axes[2, 1], df, seeds, colors)
        self._plot_learning_rate(axes[2, 2], df, seeds, colors)

        plt.tight_layout()

        out = (
            Path(output_file)
            if output_file
            else self._input_dir / "phase5_evolution_analysis.png"
        )
        plt.savefig(out, dpi=150, bbox_inches="tight")
        print(f"Plot saved to {out}")
        plt.close()

    def _prepare_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        if "child_survival_rate" not in df.columns and "c_matr_cum" in df.columns:
            df["child_survival_rate"] = df["c_matr_cum"]
        if "highest_generation" not in df.columns:
            fallback = df["mean_generation"] if "mean_generation" in df.columns else 0.0
            df["highest_generation"] = fallback
        return df

    def _plot_genome_care(self, ax, df: pd.DataFrame, seeds, colors) -> None:
        self._draw_seed_lines(ax, df, seeds, colors, col="mean_genome_care", label="mean genome care")
        ax.axhline(
            y=1 / 3,
            color="red",
            linestyle="--",
            linewidth=2,
            label="neutral (1/3)",
            zorder=5,
        )
        self._style_axes(ax)
        ax.set_xlabel("Tick", fontsize=11)
        ax.set_ylabel("Weight", fontsize=11)
        ax.set_title("Genetic Care Weight", fontsize=12, fontweight="bold")
        ax.set_ylim([0, 1])
        ax.legend(loc="best", fontsize=8, framealpha=0.9)

    def _plot_expressed_care(self, ax, df: pd.DataFrame, seeds, colors) -> None:
        self._draw_seed_lines(
            ax,
            df,
            seeds,
            colors,
            col="mean_expressed_care",
            label="mean expressed care",
        )
        ax.axhline(
            y=1 / 3,
            color="red",
            linestyle="--",
            linewidth=2,
            label="neutral (1/3)",
            zorder=5,
        )
        self._style_axes(ax)
        ax.set_xlabel("Tick", fontsize=11)
        ax.set_ylabel("Weight", fontsize=11)
        ax.set_title("Phenotypic Care Expression", fontsize=12, fontweight="bold")
        ax.set_ylim([0, 1])
        ax.legend(loc="best", fontsize=8, framealpha=0.9)

    def _plot_plasticity(self, ax, df: pd.DataFrame, seeds, colors) -> None:
        self._draw_seed_lines(
            ax,
            df,
            seeds,
            colors,
            col="mean_plasticity",
            label="mean plasticity",
        )
        mean_df = df.groupby("tick", as_index=False)["innateness_index"].mean()
        ax.plot(
            mean_df["tick"],
            mean_df["innateness_index"],
            color="darkorange",
            linewidth=2.0,
            linestyle="--",
            label="mean innateness",
        )
        self._style_axes(ax)
        ax.set_xlabel("Tick", fontsize=11)
        ax.set_ylabel("Coefficient", fontsize=11)
        ax.set_title("Plasticity / Innateness", fontsize=12, fontweight="bold")
        ax.set_ylim([0, 1])
        ax.legend(loc="best", fontsize=8, framealpha=0.9)

    def _plot_genome_behavior_distance(self, ax, df: pd.DataFrame, seeds, colors) -> None:
        self._draw_seed_lines(
            ax,
            df,
            seeds,
            colors,
            col="genome_behavior_distance",
            label="mean distance",
        )
        self._style_axes(ax)
        ax.set_xlabel("Tick", fontsize=11)
        ax.set_ylabel("|Expressed - Genome|", fontsize=11)
        ax.set_title("Genome-Behavior Distance", fontsize=12, fontweight="bold")
        max_val = df["genome_behavior_distance"].max()
        ax.set_ylim([0, max(0.3, max_val * 1.1)])
        ax.legend(loc="best", fontsize=8, framealpha=0.9)

    def _plot_population(self, ax, df: pd.DataFrame, seeds, colors) -> None:
        self._draw_seed_lines(ax, df, seeds, colors, col="n_mothers", label="mean mothers")
        mean_children = df.groupby("tick", as_index=False)["n_children"].mean()
        ax.plot(
            mean_children["tick"],
            mean_children["n_children"],
            color="purple",
            linewidth=2.0,
            linestyle="--",
            label="mean children",
        )
        self._style_axes(ax)
        ax.set_xlabel("Tick", fontsize=11)
        ax.set_ylabel("Count", fontsize=11)
        ax.set_title("Population", fontsize=12, fontweight="bold")
        ax.legend(loc="best", fontsize=8, framealpha=0.9)

    def _plot_energy(self, ax, df: pd.DataFrame, seeds, colors) -> None:
        self._draw_seed_lines(
            ax,
            df,
            seeds,
            colors,
            col="mean_mother_energy",
            label="mean mother energy",
        )
        mean_child_energy = df.groupby("tick", as_index=False)["mean_child_energy"].mean()
        ax.plot(
            mean_child_energy["tick"],
            mean_child_energy["mean_child_energy"],
            color="teal",
            linewidth=2.0,
            linestyle="--",
            label="mean child energy",
        )
        self._style_axes(ax)
        ax.set_xlabel("Tick", fontsize=11)
        ax.set_ylabel("Mean energy", fontsize=11)
        ax.set_title("Energy", fontsize=12, fontweight="bold")
        ax.set_ylim([0, 1])
        ax.legend(loc="best", fontsize=8, framealpha=0.9)

    def _plot_child_survival(self, ax, df: pd.DataFrame, seeds, colors) -> None:
        self._draw_seed_lines(
            ax,
            df,
            seeds,
            colors,
            col="child_survival_rate",
            label="mean child survival",
        )
        self._style_axes(ax)
        ax.set_xlabel("Tick", fontsize=11)
        ax.set_ylabel("Rate", fontsize=11)
        ax.set_title("Child Survival / Maturation", fontsize=12, fontweight="bold")
        ax.set_ylim([0, 1])
        ax.legend(loc="best", fontsize=8, framealpha=0.9)

    def _plot_generation(self, ax, df: pd.DataFrame, seeds, colors) -> None:
        self._draw_seed_lines(
            ax,
            df,
            seeds,
            colors,
            col="mean_generation",
            label="mean generation",
        )
        highest = df.groupby("tick", as_index=False)["highest_generation"].mean()
        ax.plot(
            highest["tick"],
            highest["highest_generation"],
            color="goldenrod",
            linewidth=2.0,
            linestyle="--",
            label="mean highest generation",
        )
        self._style_axes(ax)
        ax.set_xlabel("Tick", fontsize=11)
        ax.set_ylabel("Generation", fontsize=11)
        ax.set_title("Generation Depth", fontsize=12, fontweight="bold")
        ax.legend(loc="best", fontsize=8, framealpha=0.9)

    def _plot_learning_rate(self, ax, df: pd.DataFrame, seeds, colors) -> None:
        self._draw_seed_lines(
            ax,
            df,
            seeds,
            colors,
            col="mean_learning_rate",
            label="mean learning rate",
        )
        self._style_axes(ax)
        ax.set_xlabel("Tick", fontsize=11)
        ax.set_ylabel("Learning rate", fontsize=11)
        ax.set_title("Learning Rate", fontsize=12, fontweight="bold")
        ax.legend(loc="best", fontsize=8, framealpha=0.9)

    def _draw_seed_lines(
        self,
        ax,
        df: pd.DataFrame,
        seeds,
        colors,
        col: str,
        label: str,
    ) -> None:
        """Draw one faint trajectory per seed plus a bold across-seed mean."""
        for idx, seed in enumerate(seeds):
            seed_df = df[df["seed"] == seed].sort_values("tick")
            ax.plot(
                seed_df["tick"],
                seed_df[col],
                color=colors[idx],
                alpha=0.22,
                linewidth=1.0,
            )
        mean_df = df.groupby("tick", as_index=False)[col].mean()
        ax.plot(
            mean_df["tick"],
            mean_df[col],
            color="black",
            linewidth=2.2,
            label=label,
        )

    @staticmethod
    def _style_axes(ax) -> None:
        ax.set_facecolor("white")
        ax.grid(True, alpha=0.3, linestyle="--", linewidth=0.5)
        ax.set_axisbelow(True)
        ax.tick_params(labelsize=9)
        for spine in ax.spines.values():
            spine.set_linewidth(0.5)


def main() -> None:
    """CLI entry point for Phase 5 plot generation."""
    parser = argparse.ArgumentParser(
        description="Phase 5: Plot evolutionary trajectories"
    )
    parser.add_argument(
        "run_dir",
        nargs="?",
        default=None,
        help="Phase 5 run directory containing snapshots.csv",
    )
    parser.add_argument(
        "--input-dir",
        "--output-dir",
        "--output_dir",
        dest="run_dir_flag",
        type=str,
        default=None,
        help="Phase 5 run directory containing snapshots.csv",
    )
    parser.add_argument(
        "--output-file",
        type=str,
        default=None,
        help="Output PNG path (default: <run-dir>/phase5_evolution_analysis.png)",
    )
    parser.add_argument(
        "--checkpoint",
        type=int,
        default=None,
        help="Only plot rows at ticks divisible by this checkpoint.",
    )

    args = parser.parse_args()

    run_dir = args.run_dir_flag or args.run_dir
    if not run_dir:
        parser.error("provide the run directory as a positional path or via --output-dir")
    if args.checkpoint is not None and args.checkpoint <= 0:
        parser.error("--checkpoint must be a positive integer")

    plotter = EvolutionPlotter(run_dir)
    plotter.plot(args.output_file, checkpoint=args.checkpoint)


if __name__ == "__main__":
    main()
