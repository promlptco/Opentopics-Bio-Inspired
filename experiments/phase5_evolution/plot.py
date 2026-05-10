"""Phase 5 — Baldwin trajectory visualization."""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib
import matplotlib.pyplot as plt
import pandas as pd

matplotlib.rcParams["font.family"]        = "sans-serif"
matplotlib.rcParams["axes.linewidth"]     = 0.5
matplotlib.rcParams["axes.spines.top"]   = False
matplotlib.rcParams["axes.spines.right"] = False
matplotlib.rcParams["xtick.direction"]   = "in"
matplotlib.rcParams["ytick.direction"]   = "in"


class EvolutionPlotter:
    """Reads snapshots.csv and produces Phase 5 Baldwin trajectory figures.

    Decoupled from simulation — always re-runnable on any saved CSV without
    re-running the simulation.

    Example:
        plotter = EvolutionPlotter("outputs/phase5_evolution/exp_001")
        plotter.plot()
    """

    def __init__(self, input_dir: Path | str) -> None:
        self._input_dir = Path(input_dir)

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def plot(self, output_file: Path | str | None = None) -> None:
        """Produce and save the 4-panel Baldwin trajectory figure.

        Panels:
            1. Genetic care weight vs tick (should rise above 1/3).
            2. Expressed (phenotypic) care weight vs tick.
            3. Innateness index (1 - plasticity) vs tick (should increase).
            4. Genome–behavior distance vs tick (should decrease).

        Args:
            output_file: Save path for the PNG. Defaults to
                ``<input_dir>/phase5_evolution_analysis.png``.

        Raises:
            FileNotFoundError: If snapshots.csv is absent in input_dir.
        """
        csv_path = self._input_dir / "snapshots.csv"
        if not csv_path.exists():
            raise FileNotFoundError(f"snapshots.csv not found at {csv_path}")

        df     = pd.read_csv(csv_path)
        seeds  = sorted(df["seed"].unique())
        colors = plt.cm.tab20(range(len(seeds)))

        fig, axes = plt.subplots(2, 2, figsize=(14, 10))
        fig.suptitle(
            "Phase 5: Baldwin Emergence Evolution",
            fontsize=14,
            fontweight="bold",
            y=0.995,
        )

        self._plot_genome_care(axes[0, 0], df, seeds, colors)
        self._plot_expressed_care(axes[0, 1], df, seeds, colors)
        self._plot_innateness(axes[1, 0], df, seeds, colors)
        self._plot_genome_behavior_distance(axes[1, 1], df, seeds, colors)

        plt.tight_layout()

        out = (
            Path(output_file)
            if output_file
            else self._input_dir / "phase5_evolution_analysis.png"
        )
        plt.savefig(out, dpi=150, bbox_inches="tight")
        print(f"✓ Plot saved to {out}")
        plt.close()

    # ------------------------------------------------------------------
    # Private — one method per subplot
    # ------------------------------------------------------------------

    def _plot_genome_care(
        self, ax, df: pd.DataFrame, seeds, colors
    ) -> None:
        """Genome care weight vs tick — success if it rises above 1/3."""
        self._draw_seed_lines(ax, df, seeds, colors, col="mean_genome_care")
        ax.axhline(
            y=1 / 3, color="red", linestyle="--", linewidth=2,
            label="Neutral (1/3)", zorder=5,
        )
        self._style_axes(ax)
        ax.set_xlabel("Tick", fontsize=11)
        ax.set_ylabel("Mean Genome Care Weight", fontsize=11)
        ax.set_title("Genetic Care Weight Evolution", fontsize=12, fontweight="bold")
        ax.set_ylim([0, 1])
        ax.legend(loc="best", fontsize=8, framealpha=0.9)

    def _plot_expressed_care(
        self, ax, df: pd.DataFrame, seeds, colors
    ) -> None:
        """Expressed (phenotypic) care weight vs tick."""
        self._draw_seed_lines(ax, df, seeds, colors, col="mean_expressed_care")
        ax.axhline(
            y=1 / 3, color="red", linestyle="--", linewidth=2,
            label="Neutral (1/3)", zorder=5,
        )
        self._style_axes(ax)
        ax.set_xlabel("Tick", fontsize=11)
        ax.set_ylabel("Mean Expressed Care", fontsize=11)
        ax.set_title("Phenotypic Care Expression", fontsize=12, fontweight="bold")
        ax.set_ylim([0, 1])
        ax.legend(loc="best", fontsize=8, framealpha=0.9)

    def _plot_innateness(
        self, ax, df: pd.DataFrame, seeds, colors
    ) -> None:
        """Innateness index (1 − plasticity) vs tick — should increase."""
        self._draw_seed_lines(ax, df, seeds, colors, col="innateness_index")
        self._style_axes(ax)
        ax.set_xlabel("Tick", fontsize=11)
        ax.set_ylabel("Innateness Index (1 − Plasticity)", fontsize=11)
        ax.set_title(
            "Genetic Assimilation (Learned → Innate)", fontsize=12, fontweight="bold"
        )
        ax.set_ylim([0, 1])
        ax.legend(loc="best", fontsize=8, framealpha=0.9)

    def _plot_genome_behavior_distance(
        self, ax, df: pd.DataFrame, seeds, colors
    ) -> None:
        """Genome–behavior distance vs tick — should decrease over time."""
        self._draw_seed_lines(ax, df, seeds, colors, col="genome_behavior_distance")
        self._style_axes(ax)
        ax.set_xlabel("Tick", fontsize=11)
        ax.set_ylabel("|Expressed − Genome|", fontsize=11)
        ax.set_title("Genome–Behavior Distance", fontsize=12, fontweight="bold")
        max_val = df["genome_behavior_distance"].max()
        ax.set_ylim([0, max(0.3, max_val * 1.1)])
        ax.legend(loc="best", fontsize=8, framealpha=0.9)

    def _draw_seed_lines(
        self, ax, df: pd.DataFrame, seeds, colors, col: str
    ) -> None:
        """Draw one trajectory line per seed on ax.

        Args:
            ax: Matplotlib axes to draw on.
            df: Full snapshots DataFrame.
            seeds: Ordered sequence of seed values.
            colors: Colour array aligned with seeds.
            col: Column name to plot on the y-axis.
        """
        for idx, seed in enumerate(seeds):
            seed_df = df[df["seed"] == seed].sort_values("tick")
            ax.plot(
                seed_df["tick"],
                seed_df[col],
                color=colors[idx],
                alpha=0.6,
                linewidth=1.5,
                label=f"seed={seed}",
            )

    @staticmethod
    def _style_axes(ax) -> None:
        """Apply consistent academic styling to an axes object.

        Args:
            ax: Matplotlib axes to style.
        """
        ax.set_facecolor("white")
        ax.grid(True, alpha=0.3, linestyle="--", linewidth=0.5)
        ax.set_axisbelow(True)
        ax.tick_params(labelsize=9)
        for spine in ax.spines.values():
            spine.set_linewidth(0.5)


# ===========================================================================
# CLI entry point
# ===========================================================================

def main() -> None:
    """CLI entry point for Phase 5 plot generation."""
    parser = argparse.ArgumentParser(
        description="Phase 5: Plot evolutionary trajectories"
    )
    parser.add_argument(
        "--input-dir",
        type=str,
        required=True,
        help="Directory containing snapshots.csv",
    )
    parser.add_argument(
        "--output-file",
        type=str,
        default=None,
        help="Output PNG path (default: <input-dir>/phase5_evolution_analysis.png)",
    )

    args = parser.parse_args()

    plotter = EvolutionPlotter(args.input_dir)
    plotter.plot(args.output_file)


if __name__ == "__main__":
    main()
