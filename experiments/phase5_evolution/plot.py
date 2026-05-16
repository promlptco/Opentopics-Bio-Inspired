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


# ---------------------------------------------------------------------------
# Cross-condition comparison plotter  (--mode compare)
# ---------------------------------------------------------------------------

_CONDITION_COLORS: dict[str, str] = {
    "mut+/plast+": "#1f77b4",
    "mut+/plast−": "#ff7f0e",
    "mut−/plast+": "#2ca02c",
    "mut−/plast−": "#d62728",
}
_CONDITION_ORDER: list[str] = [
    "mut+/plast+",
    "mut+/plast−",
    "mut−/plast+",
    "mut−/plast−",
]
_DIR_SUFFIX_TO_LABEL: dict[str, str] = {
    "mut_on_plast_on":  "mut+/plast+",
    "mut_on_plast_off": "mut+/plast−",
    "mut_off_plast_on": "mut−/plast+",
    "mut_off_plast_off":"mut−/plast−",
}


class Block2EvoPlotter:
    """Cross-condition comparison plotter for Phase 5 Block 2 evolution.

    Auto-discovers all subdirectories under *block_dir* whose names start with
    *block_prefix*, loads their lifecycle and snapshot CSVs, and produces seven
    statistical comparison figures.

    Usage::

        python -m experiments.phase5_evolution.plot \\
            --mode compare \\
            --block-dir outputs/phase5_evolution/ \\
            --block-prefix block2_main \\
            --plots-dir outputs/phase5_evolution/block2_extended/
    """

    CONDITION_COLORS = _CONDITION_COLORS
    CONDITION_ORDER  = _CONDITION_ORDER

    def __init__(self, block_dir: Path | str, block_prefix: str = "block2_main") -> None:
        self._block_dir    = Path(block_dir)
        self._block_prefix = block_prefix
        self._life, self._snap = self._load_all_conditions()
        self._cohort = self._build_cohort_frame()

    # ------------------------------------------------------------------
    # Data loading
    # ------------------------------------------------------------------

    def _discover_dirs(self) -> list[Path]:
        dirs = sorted(
            d for d in self._block_dir.iterdir()
            if d.is_dir() and d.name.startswith(self._block_prefix)
        )
        if not dirs:
            raise FileNotFoundError(
                f"No subdirs matching '{self._block_prefix}*' under {self._block_dir}"
            )
        return dirs

    def _dir_to_label(self, dirname: str) -> str:
        suffix = dirname[len(self._block_prefix):].lstrip("_")
        return _DIR_SUFFIX_TO_LABEL.get(suffix, suffix)

    def _load_all_conditions(self) -> tuple[pd.DataFrame, pd.DataFrame]:
        life_frames: list[pd.DataFrame] = []
        snap_frames: list[pd.DataFrame] = []
        for d in self._discover_dirs():
            label = self._dir_to_label(d.name)
            lp = d / "mother_lifecycle.csv"
            sp = d / "snapshots.csv"
            if lp.exists():
                df = pd.read_csv(lp)
                df["condition"] = label
                life_frames.append(df)
                print(f"[compare] Loaded {d.name}/mother_lifecycle.csv ({len(df)} rows) -> '{label}'")
            if sp.exists():
                df = pd.read_csv(sp)
                df["condition"] = label
                snap_frames.append(df)
        life = pd.concat(life_frames, ignore_index=True) if life_frames else pd.DataFrame()
        snap = pd.concat(snap_frames, ignore_index=True) if snap_frames else pd.DataFrame()
        return life, snap

    def _build_cohort_frame(self) -> pd.DataFrame:
        """One row per (condition, seed, generation) with per-group aggregates."""
        df = self._life
        if df.empty:
            return pd.DataFrame()
        rows: list[dict] = []
        for (cond, seed, gen), grp in df.groupby(
            ["condition", "seed", "generation"], sort=True
        ):
            gc = float(grp["final_genome_care"].mean())
            gf = float(grp["final_genome_forage"].mean())
            gs = float(grp["final_genome_self"].mean())
            ec = float(grp["final_expressed_care"].mean())   if "final_expressed_care"   in grp.columns else np.nan
            ef = float(grp["final_expressed_forage"].mean()) if "final_expressed_forage" in grp.columns else np.nan
            es = float(grp["final_expressed_self"].mean())   if "final_expressed_self"   in grp.columns else np.nan
            tot  = float(grp["total_children"].sum())   if "total_children"   in grp.columns else 0.0
            matd = float(grp["matured_children"].sum()) if "matured_children" in grp.columns else 0.0
            cmr  = matd / tot if tot > 0.0 else np.nan
            if all(
                c in grp.columns
                for c in ["final_expressed_care", "final_expressed_forage", "final_expressed_self"]
            ):
                drift = float(
                    0.5
                    * (
                        (grp["final_expressed_care"]   - grp["final_genome_care"]).abs()
                        + (grp["final_expressed_forage"] - grp["final_genome_forage"]).abs()
                        + (grp["final_expressed_self"]   - grp["final_genome_self"]).abs()
                    ).mean()
                )
            else:
                drift = np.nan
            rows.append(
                {
                    "condition":        cond,
                    "seed":             int(seed),
                    "generation":       int(gen),
                    "genome_care":      gc,
                    "genome_forage":    gf,
                    "genome_self":      gs,
                    "expressed_care":   ec,
                    "expressed_forage": ef,
                    "expressed_self":   es,
                    "cohort_size":      len(grp),
                    "cmr":              cmr,
                    "plasticity_drift": drift,
                }
            )
        return pd.DataFrame(rows)

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    def plot_all(self, output_dir: Path | str) -> None:
        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)
        self.plot_genome_simplex(out)
        self.plot_distribution_shift(out)
        self.plot_population_fitness(out)
        self.plot_cmr_propagation(out)
        self.plot_population_over_time(out)
        self.plot_ternary_trajectory(out)
        self.plot_expressed_vs_genome_gap(out)
        print(f"[compare] All 7 figures saved to {out}")

    # ------------------------------------------------------------------
    # Fig 1 — All 3 genome weights by generation (mean ± SEM)
    # ------------------------------------------------------------------

    def plot_genome_simplex(self, output_dir: Path) -> None:
        """Line + SEM band for all 3 genome weights, all 4 conditions."""
        cohort = self._cohort
        genes  = ["genome_care",   "genome_forage",   "genome_self"]
        titles = ["Care Genome Weight", "Forage Genome Weight", "Self Genome Weight"]

        fig, axes = plt.subplots(1, 3, figsize=(15, 5))
        for ax, gene, title in zip(axes, genes, titles):
            for cond in self.CONDITION_ORDER:
                sub   = cohort[cohort["condition"] == cond]
                color = self.CONDITION_COLORS[cond]
                if sub.empty:
                    continue
                agg = (
                    sub.groupby("generation")[gene]
                    .agg(mean_val="mean", std_val="std", n="count")
                    .reset_index()
                    .sort_values("generation")
                )
                agg["sem"] = agg["std_val"] / np.sqrt(agg["n"].clip(lower=1))
                ax.fill_between(
                    agg["generation"],
                    (agg["mean_val"] - agg["sem"]).clip(0.0, 1.0),
                    (agg["mean_val"] + agg["sem"]).clip(0.0, 1.0),
                    alpha=0.15, color=color,
                )
                ax.plot(
                    agg["generation"], agg["mean_val"],
                    color=color, linewidth=2.0, label=cond,
                )
            ax.axhline(
                1 / 3, color="red", linestyle="--", linewidth=1.5,
                alpha=0.8, label="neutral 1/3",
            )
            ax.set_title(title, fontsize=12, fontweight="bold")
            ax.set_xlabel("Generation")
            ax.set_ylabel("Mean Genome Weight")
            ax.set_ylim(0.25, 0.50)
            SnapshotDashboardPlotter._style_axes(ax)
        axes[0].legend(loc="upper left", fontsize=8, framealpha=0.9)
        plt.suptitle(
            "All 3 Genome Weights by Generation — 4-Condition Comparison\n"
            "(shaded = ±1 SEM across seeds · simplex constraint: care + forage + self = 1)",
            fontsize=12, fontweight="bold",
        )
        plt.tight_layout()
        out = output_dir / "genome_all3_by_generation.png"
        plt.savefig(out, dpi=150, bbox_inches="tight")
        plt.close()
        print(f"[compare] Saved: {out.name}")

    # ------------------------------------------------------------------
    # Fig 2 — Genome distribution shift: early vs late (violin)
    # ------------------------------------------------------------------

    def plot_distribution_shift(self, output_dir: Path) -> None:
        """Violin plots comparing genome weight distributions early vs late."""
        try:
            from scipy.stats import mannwhitneyu as _mwu
            _has_scipy = True
        except ImportError:
            _has_scipy = False

        mut_on_conds = [c for c in self.CONDITION_ORDER if "mut+" in c]
        genes  = ["genome_care", "genome_forage", "genome_self"]
        g_lbls = ["Genome Care",  "Genome Forage",  "Genome Self"]
        cohort = self._cohort
        rng    = np.random.default_rng(42)

        fig, axes = plt.subplots(len(genes), len(mut_on_conds), figsize=(10, 12), squeeze=False)
        for ri, (gene, glbl) in enumerate(zip(genes, g_lbls)):
            for ci, cond in enumerate(mut_on_conds):
                ax    = axes[ri][ci]
                sub   = cohort[cohort["condition"] == cond]
                early = sub[sub["generation"] <= 5][gene].dropna().values
                late  = sub[sub["generation"] >= 40][gene].dropna().values
                color = self.CONDITION_COLORS[cond]

                parts = ax.violinplot(
                    [early, late], positions=[0, 1],
                    showmedians=True, showextrema=True,
                )
                for body in parts["bodies"]:
                    body.set_facecolor(color)
                    body.set_alpha(0.55)
                for key in ("cmedians", "cmins", "cmaxes", "cbars"):
                    parts[key].set_color(color)
                    parts[key].set_linewidth(1.5)

                for pos, vals in [(0, early), (1, late)]:
                    jitter = rng.uniform(-0.06, 0.06, size=len(vals))
                    ax.scatter(pos + jitter, vals, alpha=0.35, s=12, color=color, zorder=3)

                if _has_scipy and len(early) >= 2 and len(late) >= 2:
                    _, pval = _mwu(early, late, alternative="two-sided")
                    ptxt = f"MW p={pval:.3f}" if pval >= 0.001 else "MW p<0.001"
                else:
                    ptxt = f"n_early={len(early)}, n_late={len(late)}"

                ax.axhline(1 / 3, color="red", linestyle="--", linewidth=1.0, alpha=0.7)
                ax.set_xticks([0, 1])
                ax.set_xticklabels(["Early\n(gen 0–5)", "Late\n(gen 40+)"], fontsize=8)
                ax.set_ylim(0.22, 0.58)
                ax.set_ylabel("Weight" if ci == 0 else "")
                ax.set_title(f"{glbl}\n{cond}\n{ptxt}", fontsize=8, fontweight="bold")
                ax.grid(True, alpha=0.3, axis="y", linestyle="--")
                SnapshotDashboardPlotter._style_axes(ax)

        plt.suptitle(
            "Genome Distribution Shift — Early (gen 0–5) vs Late (gen 40+)\n"
            "(mut+ conditions only · Mann-Whitney U two-sided)",
            fontsize=12, fontweight="bold",
        )
        plt.tight_layout()
        out = output_dir / "genome_distribution_shift.png"
        plt.savefig(out, dpi=150, bbox_inches="tight")
        plt.close()
        print(f"[compare] Saved: {out.name}")

    # ------------------------------------------------------------------
    # Fig 3 — Population as fitness proxy (cohort-size boxplot)
    # ------------------------------------------------------------------

    def plot_population_fitness(self, output_dir: Path) -> None:
        """Boxplot of cohort size (mothers per generation per seed) by gen window."""
        cohort = self._cohort.copy()
        bins   = [0,  10,    20,    30,    40,   200]
        blbls  = ["0–9", "10–19", "20–29", "30–39", "40+"]
        cohort["gen_bin"] = pd.cut(
            cohort["generation"], bins=bins, labels=blbls, right=False
        )
        n_c   = len(self.CONDITION_ORDER)
        xpos  = np.arange(len(blbls), dtype=float)
        width = 0.18
        offs  = np.linspace(-(n_c - 1) / 2, (n_c - 1) / 2, n_c) * width

        fig, ax = plt.subplots(figsize=(14, 6))
        for i, cond in enumerate(self.CONDITION_ORDER):
            color = self.CONDITION_COLORS[cond]
            sub   = cohort[cohort["condition"] == cond]
            bdata = [
                sub[sub["gen_bin"] == lb]["cohort_size"].dropna().values
                for lb in blbls
            ]
            ax.boxplot(
                bdata,
                positions=xpos + offs[i],
                widths=width * 0.85,
                patch_artist=True,
                medianprops=dict(color="black", linewidth=1.5),
                boxprops=dict(facecolor=color, alpha=0.70),
                whiskerprops=dict(linewidth=1.0),
                capprops=dict(linewidth=1.0),
                flierprops=dict(marker=".", markersize=3, alpha=0.4, color=color),
            )
            ax.plot([], [], color=color, linewidth=7, alpha=0.7, label=cond)
            for j, vals in enumerate(bdata):
                if len(vals) > 0:
                    ax.text(
                        xpos[j] + offs[i], float(np.nanmax(vals)) + 0.3,
                        f"n={len(vals)}", ha="center", va="bottom",
                        fontsize=5, color="gray",
                    )
        ax.set_xticks(xpos)
        ax.set_xticklabels(blbls, fontsize=10)
        ax.set_xlabel("Generation Window", fontsize=11)
        ax.set_ylabel("Cohort Size (mothers per generation per seed)", fontsize=11)
        ax.set_title(
            "Population as Fitness Proxy — Cohort Size by Generation Window\n"
            "(larger cohorts in late generations = more gene copies surviving)",
            fontsize=12, fontweight="bold",
        )
        ax.legend(fontsize=9, loc="upper right")
        ax.grid(True, alpha=0.3, axis="y", linestyle="--")
        SnapshotDashboardPlotter._style_axes(ax)
        plt.tight_layout()
        out = output_dir / "cohort_population_fitness.png"
        plt.savefig(out, dpi=150, bbox_inches="tight")
        plt.close()
        print(f"[compare] Saved: {out.name}")

    # ------------------------------------------------------------------
    # Fig 4 — CMR as gene propagation rate (bootstrap CI)
    # ------------------------------------------------------------------

    def plot_cmr_propagation(self, output_dir: Path) -> None:
        """CMR by generation with 95% bootstrap CI across seeds."""
        cohort = self._cohort.dropna(subset=["cmr"])
        rng    = np.random.default_rng(0)
        n_boot = 1000

        fig, ax = plt.subplots(figsize=(12, 6))
        for cond in self.CONDITION_ORDER:
            sub   = cohort[cohort["condition"] == cond]
            color = self.CONDITION_COLORS[cond]
            if sub.empty:
                continue
            gens_sorted = sorted(sub["generation"].unique())
            means, lo, hi = [], [], []
            for g in gens_sorted:
                vals = sub[sub["generation"] == g]["cmr"].values
                means.append(float(vals.mean()))
                if len(vals) >= 2:
                    boots = [
                        rng.choice(vals, size=len(vals), replace=True).mean()
                        for _ in range(n_boot)
                    ]
                    lo.append(float(np.percentile(boots, 2.5)))
                    hi.append(float(np.percentile(boots, 97.5)))
                else:
                    lo.append(float(vals[0]))
                    hi.append(float(vals[0]))
            g_arr = np.array(gens_sorted, dtype=float)
            m_arr = np.array(means)
            l_arr = np.array(lo)
            h_arr = np.array(hi)
            valid = ~np.isnan(m_arr) & ~np.isnan(l_arr)
            ax.fill_between(
                g_arr[valid], l_arr[valid], h_arr[valid], alpha=0.15, color=color
            )
            ax.plot(g_arr, m_arr, color=color, linewidth=2.2, label=cond)

        ax.axhline(
            1 / 3, color="gray", linestyle=":", linewidth=1.0, alpha=0.6,
            label="neutral 1/3",
        )
        ax.set_xlabel("Generation", fontsize=11)
        ax.set_ylabel("Child Maturation Rate (CMR)", fontsize=11)
        ax.set_ylim(0.0, 1.05)
        ax.set_title(
            "Gene Propagation Rate (CMR) by Generation — 95% Bootstrap CI\n"
            "(fraction of gene copies successfully entering next generation)",
            fontsize=12, fontweight="bold",
        )
        ax.legend(fontsize=9)
        SnapshotDashboardPlotter._style_axes(ax)
        plt.tight_layout()
        out = output_dir / "cmr_gene_propagation.png"
        plt.savefig(out, dpi=150, bbox_inches="tight")
        plt.close()
        print(f"[compare] Saved: {out.name}")

    # ------------------------------------------------------------------
    # Fig 5 — Live population over simulation time (snapshot boxplot)
    # ------------------------------------------------------------------

    def plot_population_over_time(self, output_dir: Path) -> None:
        """Boxplot of n_mothers per tick window, all conditions."""
        snap = self._snap.copy()
        if snap.empty or "n_mothers" not in snap.columns:
            print("[compare] Skipping population_over_time: no snapshot data.")
            return
        bins  = [0, 5_000, 10_000, 15_000, 20_000, 100_000]
        blbls = ["0–5k", "5–10k", "10–15k", "15–20k", "20k+"]
        snap["tick_bin"] = pd.cut(snap["tick"], bins=bins, labels=blbls, right=False)

        n_c   = len(self.CONDITION_ORDER)
        xpos  = np.arange(len(blbls), dtype=float)
        width = 0.18
        offs  = np.linspace(-(n_c - 1) / 2, (n_c - 1) / 2, n_c) * width

        fig, ax = plt.subplots(figsize=(14, 6))
        for i, cond in enumerate(self.CONDITION_ORDER):
            color = self.CONDITION_COLORS[cond]
            sub   = snap[snap["condition"] == cond]
            bdata = [
                sub[sub["tick_bin"] == lb]["n_mothers"].dropna().values
                for lb in blbls
            ]
            ax.boxplot(
                bdata,
                positions=xpos + offs[i],
                widths=width * 0.85,
                patch_artist=True,
                medianprops=dict(color="black", linewidth=1.5),
                boxprops=dict(facecolor=color, alpha=0.70),
                whiskerprops=dict(linewidth=1.0),
                capprops=dict(linewidth=1.0),
                flierprops=dict(marker=".", markersize=3, alpha=0.4, color=color),
            )
            ax.plot([], [], color=color, linewidth=7, alpha=0.7, label=cond)
            for j, (lb, vals) in enumerate(zip(blbls, bdata)):
                n_s = int(sub[sub["tick_bin"] == lb]["seed"].nunique()) if len(vals) > 0 else 0
                if n_s > 0:
                    ax.text(
                        xpos[j] + offs[i], float(np.nanmax(vals)) + 0.3,
                        f"s={n_s}", ha="center", va="bottom",
                        fontsize=5, color="gray",
                    )
        ax.set_xticks(xpos)
        ax.set_xticklabels(blbls, fontsize=10)
        ax.set_xlabel("Simulation Tick Window", fontsize=11)
        ax.set_ylabel("Number of Live Mothers", fontsize=11)
        ax.set_title(
            "Live Population Over Time — Cross-Condition Comparison\n"
            "(s = seeds still alive in that tick range)",
            fontsize=12, fontweight="bold",
        )
        ax.legend(fontsize=9, loc="upper right")
        ax.grid(True, alpha=0.3, axis="y", linestyle="--")
        SnapshotDashboardPlotter._style_axes(ax)
        plt.tight_layout()
        out = output_dir / "population_over_time.png"
        plt.savefig(out, dpi=150, bbox_inches="tight")
        plt.close()
        print(f"[compare] Saved: {out.name}")

    # ------------------------------------------------------------------
    # Fig 6 — Genome simplex trajectory (ternary, manual barycentric)
    # ------------------------------------------------------------------

    @staticmethod
    def _to_cartesian(
        care: np.ndarray,
        forage: np.ndarray,
        self_: np.ndarray,
    ) -> tuple[np.ndarray, np.ndarray]:
        """Barycentric → 2-D. Vertices: CARE=top, FORAGE=bottom-left, SELF=bottom-right."""
        x = 0.5 * care + self_
        y = (np.sqrt(3) / 2) * care
        return x, y

    def plot_ternary_trajectory(self, output_dir: Path) -> None:
        """2×2 ternary scatter showing evolutionary drift in genome space."""
        cohort = self._cohort
        sqrt3  = np.sqrt(3)
        v_care   = np.array([0.5, sqrt3 / 2])
        v_forage = np.array([0.0, 0.0])
        v_self   = np.array([1.0, 0.0])
        cx, cy = self._to_cartesian(
            np.array([1 / 3]), np.array([1 / 3]), np.array([1 / 3])
        )

        fig, axes = plt.subplots(2, 2, figsize=(12, 11))
        for idx, cond in enumerate(self.CONDITION_ORDER):
            ax    = axes.flat[idx]
            color = self.CONDITION_COLORS[cond]

            # Triangle border
            ax.add_patch(
                plt.Polygon(
                    [v_forage, v_self, v_care],
                    fill=False, edgecolor="gray", linewidth=1.5, zorder=1,
                )
            )

            # Dashed grid at 1/3 and 2/3
            for frac in (1 / 3, 2 / 3):
                r = 1.0 - frac
                pts = [
                    self._to_cartesian(
                        np.array([frac]), np.array([r / 2]), np.array([r / 2])
                    ),
                    self._to_cartesian(
                        np.array([r / 2]), np.array([frac]), np.array([r / 2])
                    ),
                    self._to_cartesian(
                        np.array([r / 2]), np.array([r / 2]), np.array([frac])
                    ),
                ]
                for a_i, b_i in [(0, 1), (1, 2), (0, 2)]:
                    ax.plot(
                        [pts[a_i][0][0], pts[b_i][0][0]],
                        [pts[a_i][1][0], pts[b_i][1][0]],
                        color="lightgray", linewidth=0.6, linestyle="--", zorder=1,
                    )

            # Vertex labels
            ax.text(v_care[0],        v_care[1]   + 0.04, "CARE",
                    ha="center", va="bottom", fontsize=10, fontweight="bold")
            ax.text(v_forage[0] - 0.05, v_forage[1] - 0.04, "FORAGE",
                    ha="right",  va="top",    fontsize=10, fontweight="bold")
            ax.text(v_self[0]   + 0.05, v_self[1]   - 0.04, "SELF",
                    ha="left",   va="top",    fontsize=10, fontweight="bold")

            # Neutral centre
            ax.scatter(cx, cy, color="red", s=70, marker="x", linewidths=2.5, zorder=5)

            sub = cohort[cohort["condition"] == cond].sort_values("generation")
            if not sub.empty:
                traj = (
                    sub.groupby("generation")[
                        ["genome_care", "genome_forage", "genome_self"]
                    ]
                    .mean()
                    .reset_index()
                    .sort_values("generation")
                )
                xs, ys = self._to_cartesian(
                    traj["genome_care"].values,
                    traj["genome_forage"].values,
                    traj["genome_self"].values,
                )
                sc = ax.scatter(
                    xs, ys, c=traj["generation"].values,
                    cmap="viridis", s=35, zorder=4, alpha=0.85,
                )
                ax.plot(xs, ys, color="gray", linewidth=0.7, alpha=0.5, zorder=3)
                if len(xs) >= 2:
                    ax.annotate(
                        "", xy=(xs[-1], ys[-1]), xytext=(xs[-2], ys[-2]),
                        arrowprops=dict(arrowstyle="->", color=color, lw=2.0),
                        zorder=6,
                    )
                plt.colorbar(sc, ax=ax, shrink=0.65, label="Generation", pad=0.01)

            ax.set_xlim(-0.12, 1.12)
            ax.set_ylim(-0.12, sqrt3 / 2 + 0.12)
            ax.set_aspect("equal")
            ax.axis("off")
            ax.set_title(cond, fontsize=11, fontweight="bold", color=color)

        plt.suptitle(
            "Genome Simplex Trajectory — Evolutionary Direction in Gene Space\n"
            "(red × = neutral 1/3 centre · arrow = direction of final drift · colour = generation)",
            fontsize=12, fontweight="bold",
        )
        plt.tight_layout()
        out = output_dir / "simplex_trajectory.png"
        plt.savefig(out, dpi=150, bbox_inches="tight")
        plt.close()
        print(f"[compare] Saved: {out.name}")

    # ------------------------------------------------------------------
    # Fig 7 — Expressed vs genome care gap (plasticity signal)
    # ------------------------------------------------------------------

    def plot_expressed_vs_genome_gap(self, output_dir: Path) -> None:
        """Boxplot of (expressed_care − genome_care) by gen window, plast+ only."""
        try:
            from scipy.stats import wilcoxon as _wilcoxon
            _has_scipy = True
        except ImportError:
            _has_scipy = False

        plast_conds = [c for c in self.CONDITION_ORDER if "plast+" in c]
        cohort      = self._cohort.copy()
        cohort["gap"] = cohort["expressed_care"] - cohort["genome_care"]
        cohort = cohort[cohort["condition"].isin(plast_conds)].dropna(subset=["gap"])

        bins  = [0,  10,    20,    30,    40,   200]
        blbls = ["0–9", "10–19", "20–29", "30–39", "40+"]
        cohort["gen_bin"] = pd.cut(
            cohort["generation"], bins=bins, labels=blbls, right=False
        )

        fig, axes = plt.subplots(1, len(plast_conds), figsize=(12, 5), sharey=True)
        if len(plast_conds) == 1:
            axes = [axes]

        for ax, cond in zip(axes, plast_conds):
            color = self.CONDITION_COLORS[cond]
            sub   = cohort[cohort["condition"] == cond]
            bdata = [
                sub[sub["gen_bin"] == lb]["gap"].dropna().values
                for lb in blbls
            ]
            ax.boxplot(
                bdata,
                patch_artist=True,
                medianprops=dict(color="black", linewidth=2.0),
                boxprops=dict(facecolor=color, alpha=0.65),
                whiskerprops=dict(linewidth=1.0),
                capprops=dict(linewidth=1.0),
                flierprops=dict(marker=".", markersize=4, alpha=0.5, color=color),
            )
            for j, vals in enumerate(bdata):
                if _has_scipy and len(vals) >= 4:
                    try:
                        _, pval = _wilcoxon(vals)
                        ptxt = f"p={pval:.3f}" if pval >= 0.001 else "p<0.001"
                        ax.text(
                            j + 1, float(np.nanmax(vals)) + 0.003,
                            ptxt, ha="center", va="bottom", fontsize=7,
                        )
                    except Exception:
                        pass
            ax.axhline(
                0, color="red", linestyle="--", linewidth=1.5, alpha=0.8, label="zero gap"
            )
            ax.set_xticks(range(1, len(blbls) + 1))
            ax.set_xticklabels(blbls, fontsize=9)
            ax.set_xlabel("Generation Window", fontsize=10)
            ax.set_title(cond, fontsize=11, fontweight="bold", color=color)
            ax.grid(True, alpha=0.3, axis="y", linestyle="--")
            SnapshotDashboardPlotter._style_axes(ax)

        axes[0].set_ylabel("Expressed Care − Genome Care", fontsize=10)
        axes[0].legend(fontsize=9)
        plt.suptitle(
            "Phenotypic Plasticity Gap: Expressed vs Genome Care\n"
            "(plast+ conditions only · red line = no gap · Wilcoxon H₀: gap = 0)",
            fontsize=12, fontweight="bold",
        )
        plt.tight_layout()
        out = output_dir / "expressed_vs_genome_gap.png"
        plt.savefig(out, dpi=150, bbox_inches="tight")
        plt.close()
        print(f"[compare] Saved: {out.name}")


def main() -> None:
    """CLI entry point for Phase 5 plot generation."""
    import sys
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
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
        choices=("dashboard", "cohort", "all", "compare"),
        default="all",
        help=(
            "What to generate: dashboard, cohort plots, both (all), "
            "or cross-condition comparison (compare)."
        ),
    )
    parser.add_argument(
        "--block-dir",
        type=str,
        default=None,
        help="[compare mode] Parent directory containing condition subdirs (e.g. outputs/phase5_evolution/).",
    )
    parser.add_argument(
        "--block-prefix",
        type=str,
        default="block2_main",
        help="[compare mode] Subdir name prefix to auto-discover conditions (default: block2_main).",
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

    # ------------------------------------------------------------------
    # compare mode: multi-condition cross-run analysis
    # ------------------------------------------------------------------
    if args.mode == "compare":
        if not args.block_dir:
            parser.error("--mode compare requires --block-dir")
        plotter = Block2EvoPlotter(
            block_dir=args.block_dir,
            block_prefix=args.block_prefix,
        )
        out_dir = args.plots_dir or str(Path(args.block_dir) / "block2_extended")
        plotter.plot_all(out_dir)
        return

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
