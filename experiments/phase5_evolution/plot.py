"""Phase 5 plotting: exploratory dashboard + lifecycle cohort statistics."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

matplotlib.rcParams["font.family"] = "sans-serif"
matplotlib.rcParams["axes.linewidth"] = 0.5
matplotlib.rcParams["axes.spines.top"] = False
matplotlib.rcParams["axes.spines.right"] = False
matplotlib.rcParams["xtick.direction"] = "in"
matplotlib.rcParams["ytick.direction"] = "in"

CI_Z = 1.96


def _rolling_mean(series: pd.Series, window: int) -> pd.Series:
    if window <= 1:
        return series
    return series.rolling(window=window, min_periods=1).mean()


def _restricted_mean_survival_time(
    durations: np.ndarray,
    death_observed: np.ndarray,
    horizon: float,
) -> float:
    """Kaplan-Meier restricted mean survival time with right censoring."""
    if horizon <= 0 or len(durations) == 0:
        return float("nan")

    times = np.minimum(np.asarray(durations, dtype=float), horizon)
    events = np.asarray(death_observed, dtype=bool)

    order = np.argsort(times, kind="mergesort")
    times = times[order]
    events = events[order]

    at_risk = len(times)
    survival = 1.0
    rmst = 0.0
    prev_time = 0.0
    idx = 0

    while idx < len(times):
        time = min(times[idx], horizon)
        if time > prev_time:
            rmst += survival * (time - prev_time)

        deaths = 0
        censored = 0
        while idx < len(times) and times[idx] == time:
            if events[idx]:
                deaths += 1
            else:
                censored += 1
            idx += 1

        if deaths > 0 and at_risk > 0:
            survival *= 1.0 - (deaths / at_risk)
        at_risk -= deaths + censored
        prev_time = time

        if prev_time >= horizon:
            break

    if prev_time < horizon:
        rmst += survival * (horizon - prev_time)

    return float(rmst)


class SnapshotDashboardPlotter:
    """Reads snapshots.csv and produces the exploratory Phase 5 dashboard."""

    def __init__(self, input_dir: Path | str) -> None:
        self._input_dir = Path(input_dir)
        self._metric_skip_reasons: dict[str, str] = {}

    def plot(
        self,
        output_file: Path | str | None = None,
        checkpoint: int | None = None,
        snapshot: int | None = None,
    ) -> None:
        """Produce and save the exploratory dashboard figure."""
        csv_path = self._input_dir / "snapshots.csv"
        if not csv_path.exists():
            raise FileNotFoundError(f"snapshots.csv not found at {csv_path}")

        df = self._prepare_dataframe(pd.read_csv(csv_path))
        if snapshot is not None:
            if snapshot < 0:
                raise ValueError("snapshot must be zero or a positive integer")
            df = df[df["tick"] <= snapshot].copy()
            if df.empty:
                raise ValueError(
                    f"No snapshot rows matched snapshot={snapshot} in {csv_path}"
                )
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
            "Phase 5: Exploratory Snapshot Dashboard",
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
        print(f"Dashboard saved to {out}")
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
        ax.set_ylabel("TV(Expressed, Genome)", fontsize=11)
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


EvolutionPlotter = SnapshotDashboardPlotter


class CohortStatisticsPlotter:
    """Reads lifecycle CSVs and emits one standalone plot per metric family."""

    FAMILY_SPECS = {
        "fitness": {
            "title": "Reproductive Success Over Generation",
            "ylabel": "Matured offspring / mother",
            "color": "tab:green",
            "overall_name": "fitness_overall.png",
        },
        "maturation_fraction": {
            "title": "Offspring Maturation Fraction Over Generation",
            "ylabel": "Matured / born",
            "color": "tab:olive",
            "overall_name": "maturation_fraction_overall.png",
        },
        "plasticity_drift": {
            "title": "Plasticity Reliance Over Generation",
            "ylabel": "TV(expressed, genome)",
            "color": "tab:blue",
            "overall_name": "plasticity_drift_overall.png",
        },
        "learning_cost": {
            "title": "Learning Cost Over Generation",
            "ylabel": "Mean lifetime learning cost",
            "color": "tab:red",
            "overall_name": "learning_cost_overall.png",
        },
        "child_ttd": {
            "title": "Mean Child TTD (normalized RMST)",
            "ylabel": "Normalized RMST",
            "color": "tab:pink",
            "overall_name": "child_ttd_overall.png",
        },
        "mother_ttd": {
            "title": "Mean Mother TTD (normalized RMST)",
            "ylabel": "Normalized RMST",
            "color": "tab:purple",
            "overall_name": "mother_ttd_overall.png",
        },
        "genome_care": {
            "title": "Genome Care Share Over Generation",
            "ylabel": "Genome care weight",
            "color": "tab:orange",
            "overall_name": "genome_care_overall.png",
        },
    }

    def __init__(self, input_dir: Path | str) -> None:
        self._input_dir = Path(input_dir)

    def plot_all(
        self,
        output_dir: Path | str | None = None,
        ma_window: int = 25,
        min_seeds: int = 3,
    ) -> None:
        output_root = Path(output_dir) if output_dir else self._input_dir / "cohort_plots"
        output_root.mkdir(parents=True, exist_ok=True)
        self._metric_skip_reasons = {}

        mother_csv = self._input_dir / "mother_lifecycle.csv"
        child_csv = self._input_dir / "child_lifecycle.csv"
        if not mother_csv.exists() or not child_csv.exists():
            raise FileNotFoundError(
                "lifecycle CSVs not found. This run predates lifecycle export; "
                "rerun Phase 5 with the updated runner for cohort plots."
            )

        params = self._load_summary_params()
        mother_df = pd.read_csv(mother_csv)
        child_df = pd.read_csv(child_csv)

        metric_frames = self._build_metric_frames(mother_df, child_df, params)
        plot_count = 0
        for family, frame in metric_frames.items():
            if frame.empty:
                reason = self._metric_skip_reasons.get(
                    family,
                    "no completed cohort rows yet.",
                )
                print(f"[cohort] Skipping {family}: {reason}")
                continue
            spec = self.FAMILY_SPECS[family]
            for seed in sorted(frame["seed"].unique()):
                seed_df = frame[frame["seed"] == seed].sort_values("generation")
                if self._plot_seed_metric(
                    seed_df=seed_df,
                    family=family,
                    spec=spec,
                    output_path=output_root / f"{family}_seed_{seed}.png",
                    ma_window=ma_window,
                ):
                    plot_count += 1
            if self._plot_overall_metric(
                metric_df=frame,
                family=family,
                spec=spec,
                output_path=output_root / spec["overall_name"],
                min_seeds=min_seeds,
            ):
                plot_count += 1

        print(f"Cohort plots saved to {output_root} ({plot_count} files)")

    def _load_summary_params(self) -> dict:
        summary_path = self._input_dir / "summary.json"
        if not summary_path.exists():
            raise FileNotFoundError(f"summary.json not found at {summary_path}")
        with open(summary_path, "r", encoding="utf-8") as f:
            summary = json.load(f)
        params = summary.get("params", {})
        if "maturity_age" not in params:
            raise KeyError(
                "summary.json params missing maturity_age. This looks like a legacy run "
                "created before cohort metadata was added."
            )
        if "mother_max_age" not in params or params["mother_max_age"] is None:
            raise KeyError(
                "summary.json params missing mother_max_age. This looks like a legacy run "
                "created before cohort metadata was added."
            )
        return params

    def _build_metric_frames(
        self,
        mother_df: pd.DataFrame,
        child_df: pd.DataFrame,
        params: dict,
    ) -> dict[str, pd.DataFrame]:
        mother_df = mother_df.copy()
        child_df = child_df.copy()
        mother_df["death_observed"] = mother_df["death_observed"].astype(int)
        child_df["death_observed"] = child_df["death_observed"].astype(int)

        metrics = {
            "fitness": self._mother_completed_metric(
                mother_df,
                lambda g: float(g["matured_children"].sum()) / len(g),
            ),
            "maturation_fraction": self._mother_completed_metric(
                mother_df,
                lambda g: (
                    float(g["matured_children"].sum()) / float(g["total_children"].sum())
                    if float(g["total_children"].sum()) > 0.0
                    else float("nan")
                ),
            ),
            "plasticity_drift": self._mother_completed_metric(
                mother_df,
                self._plasticity_drift_value,
            ),
            "child_ttd": self._survival_metric(
                child_df,
                horizon=float(params["maturity_age"]),
            ),
            "mother_ttd": self._survival_metric(
                mother_df,
                horizon=float(params["mother_max_age"]),
            ),
            "genome_care": self._mother_all_metric(
                mother_df,
                lambda g: float(g["final_genome_care"].mean()),
            ),
        }
        if "lifetime_learning_cost" in mother_df.columns:
            metrics["learning_cost"] = self._mother_completed_metric(
                mother_df,
                lambda g: float(g["lifetime_learning_cost"].mean()),
            )
        else:
            self._metric_skip_reasons["learning_cost"] = (
                "legacy run missing lifetime_learning_cost; rerun Phase 5 to assess learning cost."
            )
            metrics["learning_cost"] = pd.DataFrame(columns=["seed", "generation", "value"])

        return {
            key: frame.dropna(subset=["value"]).sort_values(["seed", "generation"]).reset_index(drop=True)
            for key, frame in metrics.items()
        }

    def _plasticity_drift_value(self, group: pd.DataFrame) -> float:
        vector_cols = {
            "final_genome_forage",
            "final_genome_self",
            "final_expressed_forage",
            "final_expressed_self",
        }
        if vector_cols.issubset(group.columns):
            diffs = (
                (group["final_expressed_care"] - group["final_genome_care"]).abs()
                + (group["final_expressed_forage"] - group["final_genome_forage"]).abs()
                + (group["final_expressed_self"] - group["final_genome_self"]).abs()
            )
            return float((0.5 * diffs).mean())
        return float((group["final_expressed_care"] - group["final_genome_care"]).abs().mean())

    def _mother_completed_metric(self, mother_df: pd.DataFrame, func) -> pd.DataFrame:
        rows: list[dict[str, float | int]] = []
        for (seed, generation), group in mother_df.groupby(["seed", "generation"], sort=True):
            if (group["event_type"] == "censored").any():
                continue
            rows.append(
                {
                    "seed": int(seed),
                    "generation": int(generation),
                    "value": func(group),
                }
            )
        return pd.DataFrame(rows, columns=["seed", "generation", "value"])

    def _mother_all_metric(self, mother_df: pd.DataFrame, func) -> pd.DataFrame:
        rows: list[dict[str, float | int]] = []
        for (seed, generation), group in mother_df.groupby(["seed", "generation"], sort=True):
            rows.append(
                {
                    "seed": int(seed),
                    "generation": int(generation),
                    "value": func(group),
                }
            )
        return pd.DataFrame(rows, columns=["seed", "generation", "value"])

    def _survival_metric(self, df: pd.DataFrame, horizon: float) -> pd.DataFrame:
        rows: list[dict[str, float | int]] = []
        for (seed, generation), group in df.groupby(["seed", "generation"], sort=True):
            rmst = _restricted_mean_survival_time(
                durations=group["age_at_event"].to_numpy(dtype=float),
                death_observed=group["death_observed"].to_numpy(dtype=int),
                horizon=horizon,
            )
            rows.append(
                {
                    "seed": int(seed),
                    "generation": int(generation),
                    "value": rmst / horizon if horizon > 0 else float("nan"),
                }
            )
        return pd.DataFrame(rows, columns=["seed", "generation", "value"])

    def _plot_seed_metric(
        self,
        seed_df: pd.DataFrame,
        family: str,
        spec: dict,
        output_path: Path,
        ma_window: int,
    ) -> bool:
        if seed_df.empty:
            return False

        color = spec["color"]
        fig, ax = plt.subplots(figsize=(9, 5))
        ax.plot(
            seed_df["generation"],
            seed_df["value"],
            color=color,
            alpha=0.22,
            linewidth=1.1,
            label=f"{family} (raw)",
        )
        ax.plot(
            seed_df["generation"],
            _rolling_mean(seed_df["value"], ma_window),
            color=color,
            linewidth=2.2,
            label=f"MA (w={ma_window})",
        )
        if family == "genome_care":
            ax.axhline(1 / 3, color="red", linestyle="--", linewidth=1.5, label="neutral (1/3)")

        ax.set_title(f"{spec['title']} - Seed {int(seed_df['seed'].iloc[0])}", fontsize=12, fontweight="bold")
        ax.set_xlabel("Generation")
        ax.set_ylabel(spec["ylabel"])
        if family in {"child_ttd", "mother_ttd", "genome_care", "maturation_fraction", "plasticity_drift"}:
            ax.set_ylim(0, 1)
        ax.grid(True, alpha=0.3, linestyle="--", linewidth=0.5)
        ax.legend(loc="best", fontsize=8, framealpha=0.9)
        plt.tight_layout()
        plt.savefig(output_path, dpi=150, bbox_inches="tight")
        plt.close(fig)
        return True

    def _plot_overall_metric(
        self,
        metric_df: pd.DataFrame,
        family: str,
        spec: dict,
        output_path: Path,
        min_seeds: int,
    ) -> bool:
        if metric_df.empty:
            return False

        summary = (
            metric_df.groupby("generation")["value"]
            .agg(n="count", mean="mean", sd="std")
            .reset_index()
            .sort_values("generation")
        )
        summary = summary[summary["n"] >= min_seeds].copy()
        if summary.empty:
            return False

        summary["sd"] = summary["sd"].fillna(0.0)
        summary["se"] = summary["sd"] / np.sqrt(summary["n"])
        summary["lower"] = summary["mean"] - (CI_Z * summary["se"])
        summary["upper"] = summary["mean"] + (CI_Z * summary["se"])
        if family in {"child_ttd", "mother_ttd", "genome_care", "maturation_fraction", "plasticity_drift"}:
            summary["lower"] = summary["lower"].clip(lower=0.0, upper=1.0)
            summary["upper"] = summary["upper"].clip(lower=0.0, upper=1.0)

        fig, ax = plt.subplots(figsize=(9, 5))
        for seed, seed_df in metric_df.groupby("seed"):
            ax.plot(
                seed_df["generation"],
                seed_df["value"],
                color=spec["color"],
                alpha=0.12,
                linewidth=0.9,
            )

        ax.fill_between(
            summary["generation"],
            summary["lower"],
            summary["upper"],
            color=spec["color"],
            alpha=0.18,
            label="95% CI",
        )
        ax.plot(
            summary["generation"],
            summary["mean"],
            color=spec["color"],
            linewidth=2.4,
            label="mean across seeds",
        )
        if family == "genome_care":
            ax.axhline(1 / 3, color="red", linestyle="--", linewidth=1.5, label="neutral (1/3)")

        ax.set_title(
            f"{spec['title']} (mean ± 95% CI, n_seed >= {min_seeds})",
            fontsize=12,
            fontweight="bold",
        )
        ax.set_xlabel("Generation")
        ax.set_ylabel(spec["ylabel"])
        if family in {"child_ttd", "mother_ttd", "genome_care", "maturation_fraction", "plasticity_drift"}:
            ax.set_ylim(0, 1)
        ax.grid(True, alpha=0.3, linestyle="--", linewidth=0.5)
        ax.legend(loc="best", fontsize=8, framealpha=0.9)
        plt.tight_layout()
        plt.savefig(output_path, dpi=150, bbox_inches="tight")
        plt.close(fig)
        return True


def main() -> None:
    """CLI entry point for Phase 5 plot generation."""
    parser = argparse.ArgumentParser(
        description="Phase 5: exploratory dashboard and lifecycle cohort plots"
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
        help="Dashboard PNG path (default: <run-dir>/phase5_evolution_analysis.png)",
    )
    parser.add_argument(
        "--plots-dir",
        type=str,
        default=None,
        help="Directory for lifecycle cohort plots (default: <run-dir>/cohort_plots)",
    )
    parser.add_argument(
        "--mode",
        choices=("dashboard", "cohort", "all"),
        default="all",
        help="What to generate: the exploratory dashboard, lifecycle cohort plots, or both.",
    )
    parser.add_argument(
        "--checkpoint",
        type=int,
        default=None,
        help="Only plot dashboard rows at ticks divisible by this checkpoint.",
    )
    parser.add_argument(
        "--snapshot",
        type=int,
        default=None,
        help="Only plot dashboard rows from tick 0 through this cutoff.",
    )
    parser.add_argument(
        "--ma-window",
        type=int,
        default=25,
        help="Rolling-mean window for individual cohort seed plots.",
    )
    parser.add_argument(
        "--min-seeds",
        type=int,
        default=3,
        help="Minimum contributing seeds required for each overall cohort generation point.",
    )

    args = parser.parse_args()

    run_dir = args.run_dir_flag or args.run_dir
    if not run_dir:
        parser.error("provide the run directory as a positional path or via --output-dir")
    if args.checkpoint is not None and args.checkpoint <= 0:
        parser.error("--checkpoint must be a positive integer")
    if args.snapshot is not None and args.snapshot < 0:
        parser.error("--snapshot must be zero or a positive integer")
    if args.ma_window <= 0:
        parser.error("--ma-window must be a positive integer")
    if args.min_seeds <= 0:
        parser.error("--min-seeds must be a positive integer")

    if args.mode in {"dashboard", "all"}:
        dashboard = SnapshotDashboardPlotter(run_dir)
        dashboard.plot(
            args.output_file,
            checkpoint=args.checkpoint,
            snapshot=args.snapshot,
        )

    if args.mode in {"cohort", "all"}:
        cohort = CohortStatisticsPlotter(run_dir)
        try:
            cohort.plot_all(
                output_dir=args.plots_dir,
                ma_window=args.ma_window,
                min_seeds=args.min_seeds,
            )
        except (FileNotFoundError, KeyError) as exc:
            if args.mode == "cohort":
                raise
            print(f"[cohort] Skipped: {exc}")


if __name__ == "__main__":
    main()
