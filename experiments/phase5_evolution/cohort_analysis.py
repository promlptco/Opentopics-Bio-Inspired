"""
Phase 5 Cohort Analysis — generation-indexed metrics from lifecycle logs.

Generates 12 figures (some 4-panel) covering 6 metric families:
    1. Genome care weight per cohort  (PRIMARY Baldwin signal)
    2. Maturation rate per cohort     (LOW-level fitness: matured / born)
    3. Plasticity drift per cohort    (plast_on conditions only)
    4. Mother nRMST per cohort
    5. Child nRMST per cohort
    6. Population size over time      (HIGH-level fitness: n agents alive per tick)

Usage:
    python -m experiments.phase5_evolution.cohort_analysis
    python -m experiments.phase5_evolution.cohort_analysis --include-2b
    python -m experiments.phase5_evolution.cohort_analysis --output-dir custom/path
"""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

BASE = Path("outputs/phase5_evolution")

H_CHILD  = 80    # maturity_age used in actual Phase 5 runs
H_MOTHER = 1000  # mother_max_age used in actual Phase 5 runs

CONDITIONS: dict[str, tuple[str, bool, bool]] = {
    "mut_on / plast_on":  ("block2_main_mut_on_plast_on",  True,  True),
    "mut_on / plast_off": ("block2_main_mut_on_plast_off", True,  False),
    "mut_off / plast_on": ("block2_main_mut_off_plast_on", False, True),
    "mut_off / plast_off":("block2_main_mut_off_plast_off",False, False),
}

CONDITIONS_2B: dict[str, tuple[str, bool, bool]] = {
    "mut_on / plast_on (2b)": ("block2b_mut_on_plast_on_lr0p25_pc0p25",  True,  True),
    "mut_off / plast_on (2b)":("block2b_mut_off_plast_on_lr0p25_pc0p25", False, True),
}

COLORS: dict[str, str] = {
    "mut_on / plast_on":       "#e41a1c",
    "mut_on / plast_off":      "#377eb8",
    "mut_off / plast_on":      "#ff7f00",
    "mut_off / plast_off":     "#4daf4a",
    "mut_on / plast_on (2b)":  "#a65628",
    "mut_off / plast_on (2b)": "#984ea3",
}

# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def load_condition(folder: str) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    mpath = BASE / folder / "mother_lifecycle.csv"
    cpath = BASE / folder / "child_lifecycle.csv"
    spath = BASE / folder / "snapshots.csv"
    m = pd.read_csv(mpath) if mpath.exists() else pd.DataFrame()
    c = pd.read_csv(cpath) if cpath.exists() else pd.DataFrame()
    s = pd.read_csv(spath) if spath.exists() else pd.DataFrame()
    return m, c, s

# ---------------------------------------------------------------------------
# Metric computation  (all return DataFrame with columns: seed, generation, <metric>)
# ---------------------------------------------------------------------------

def compute_genome_care(mdf: pd.DataFrame) -> pd.DataFrame:
    return (
        mdf.groupby(["seed", "generation"])["final_genome_care"]
        .mean()
        .reset_index()
        .rename(columns={"final_genome_care": "value"})
    )


def compute_fitness(mdf: pd.DataFrame) -> pd.DataFrame:
    g = mdf.groupby(["seed", "generation"]).agg(
        matured=("matured_children", "sum"),
        total=("total_children", "sum"),
    ).reset_index()
    g["value"] = g["matured"] / g["total"].replace(0, np.nan)
    return g[["seed", "generation", "value"]]


def compute_plasticity_drift(mdf: pd.DataFrame) -> pd.DataFrame | None:
    if "final_expressed_care" not in mdf.columns:
        return None
    sub = mdf.dropna(subset=["final_expressed_care", "final_genome_care"]).copy()
    if sub.empty:
        return None
    sub["drift"] = (sub["final_expressed_care"] - sub["final_genome_care"]).abs()
    return (
        sub.groupby(["seed", "generation"])["drift"]
        .mean()
        .reset_index()
        .rename(columns={"drift": "value"})
    )


def compute_mother_nrmst(mdf: pd.DataFrame) -> pd.DataFrame:
    mdf = mdf.copy()
    mdf["capped"] = mdf["age_at_event"].clip(upper=H_MOTHER)
    return (
        mdf.groupby(["seed", "generation"])["capped"]
        .mean()
        .div(H_MOTHER)
        .reset_index()
        .rename(columns={"capped": "value"})
    )


def compute_population_fitness(sdf: pd.DataFrame) -> pd.DataFrame | None:
    """Population size (n_mothers) over ticks — higher-level fitness proxy.

    Uses snapshots.csv (tick-indexed). Returns columns: seed, tick, value.
    """
    if sdf.empty or "n_mothers" not in sdf.columns:
        return None
    df = sdf[["seed", "tick", "n_mothers"]].copy()
    df = df.rename(columns={"n_mothers": "value"})
    return df


def compute_child_nrmst(cdf: pd.DataFrame) -> pd.DataFrame | None:
    if cdf.empty or "age_at_event" not in cdf.columns:
        return None
    cdf = cdf.copy()
    cdf["effective_age"] = cdf.apply(
        lambda r: H_CHILD if str(r.get("event_type", "")) == "matured"
                  else min(r["age_at_event"], H_CHILD),
        axis=1,
    )
    # children's generation = mother_generation + 1
    cdf["mother_gen"] = cdf["generation"] - 1
    result = (
        cdf.groupby(["seed", "mother_gen"])["effective_age"]
        .mean()
        .div(H_CHILD)
        .reset_index()
        .rename(columns={"mother_gen": "generation", "effective_age": "value"})
    )
    return result

# ---------------------------------------------------------------------------
# Plotting helpers
# ---------------------------------------------------------------------------

def _agg(df: pd.DataFrame, x_col: str = "generation") -> pd.DataFrame:
    """Per-x_col mean ± SE across seeds."""
    a = df.groupby(x_col)["value"].agg(["mean", "sem"]).reset_index()
    a.columns = [x_col, "mean", "se"]
    return a


def plot_per_condition(
    datasets: dict[str, pd.DataFrame],
    ylabel: str,
    title: str,
    outpath: Path,
    hline: float | None = None,
    x_col: str = "generation",
    x_label: str | None = None,
) -> None:
    """One panel per condition, per-seed traces + mean. 2×2 or 1×N layout."""
    n = len(datasets)
    if n == 0:
        return
    cols = 2 if n > 2 else n
    rows = (n + cols - 1) // cols
    fig, axes = plt.subplots(rows, cols, figsize=(7 * cols, 5 * rows), sharey=True)
    axes = np.array(axes).flatten()
    xlabel = x_label if x_label is not None else x_col.capitalize()

    for ax, (label, df) in zip(axes, datasets.items()):
        color = COLORS.get(label, "steelblue")
        for _, grp in df.groupby("seed"):
            ax.plot(grp[x_col], grp["value"], alpha=0.25, lw=0.7, color=color)
        agg = _agg(df, x_col)
        ax.plot(agg[x_col], agg["mean"], color=color, lw=2.2)
        ax.fill_between(
            agg[x_col],
            agg["mean"] - agg["se"],
            agg["mean"] + agg["se"],
            alpha=0.25, color=color,
        )
        if hline is not None:
            ax.axhline(hline, color="black", ls="--", lw=1, alpha=0.6)
        ax.set_title(label, fontsize=10)
        ax.set_xlabel(xlabel)
        ax.set_ylabel(ylabel)
        ax.grid(True, alpha=0.3)

    for ax in axes[n:]:
        ax.set_visible(False)

    fig.suptitle(title, fontsize=13, fontweight="bold", y=1.01)
    plt.tight_layout()
    plt.savefig(outpath, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"  Saved: {outpath.name}")


def plot_overall(
    datasets: dict[str, pd.DataFrame],
    ylabel: str,
    title: str,
    outpath: Path,
    hline: float | None = None,
    x_col: str = "generation",
    x_label: str | None = None,
) -> None:
    """All conditions on one axis, mean ± 95% CI."""
    fig, ax = plt.subplots(figsize=(10, 6))
    xlabel = x_label if x_label is not None else x_col.capitalize()
    for label, df in datasets.items():
        color = COLORS.get(label, "steelblue")
        agg = _agg(df, x_col)
        ci = 1.96 * agg["se"]
        ax.plot(agg[x_col], agg["mean"], color=color, lw=2, label=label)
        ax.fill_between(
            agg[x_col],
            agg["mean"] - ci,
            agg["mean"] + ci,
            alpha=0.15, color=color,
        )
    if hline is not None:
        ax.axhline(hline, color="black", ls="--", lw=1.2, alpha=0.7,
                   label=f"neutral = {hline:.3f}")
    ax.set_xlabel(xlabel, fontsize=12)
    ax.set_ylabel(ylabel, fontsize=12)
    ax.set_title(title, fontsize=13, fontweight="bold")
    ax.legend(fontsize=9)
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(outpath, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"  Saved: {outpath.name}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", default="outputs/phase5_evolution/cohort_plots")
    parser.add_argument("--include-2b", action="store_true",
                        help="Also include Block 2b conditions (lr=0.25, pc=0.25)")
    args = parser.parse_args()

    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)

    # Build condition map
    cond_map = dict(CONDITIONS)
    if args.include_2b:
        cond_map.update(CONDITIONS_2B)

    # Load raw data
    raw: dict[str, dict] = {}
    for label, (folder, mut, plast) in cond_map.items():
        m, c, s = load_condition(folder)
        raw[label] = {"m": m, "c": c, "s": s, "plast": plast}
        print(f"Loaded '{label}': {len(m)} mothers, {len(c)} children, {len(s)} snapshots")

    print()

    # ── 1. Genome care (PRIMARY Baldwin signal) ──────────────────────────────
    print("[1/5] Genome care weight")
    gcare = {lbl: compute_genome_care(d["m"]) for lbl, d in raw.items()}
    plot_per_condition(gcare, "Mean genome care weight", "Genome Care Weight per Cohort",
                       out / "genome_care_per_condition.png", hline=1/3)
    plot_overall(gcare, "Mean genome care weight", "Genome Care Weight — All Conditions",
                 out / "genome_care_overall.png", hline=1/3)

    # ── 2. Maturation rate — LOW-level fitness ───────────────────────────────
    print("[2/5] Maturation rate (low-level fitness)")
    fit = {lbl: compute_fitness(d["m"]) for lbl, d in raw.items()}
    plot_per_condition(fit, "Maturation rate (matured / total born)",
                       "Low-Level Fitness: Maturation Rate per Cohort",
                       out / "fitness_per_condition.png")
    plot_overall(fit, "Maturation rate (matured / total born)",
                 "Low-Level Fitness: Maturation Rate — All Conditions",
                 out / "fitness_overall.png")

    # ── 3. Plasticity drift (plast_on only) ──────────────────────────────────
    print("[3/5] Plasticity drift")
    drift = {}
    for lbl, d in raw.items():
        if not d["plast"]:
            continue
        dd = compute_plasticity_drift(d["m"])
        if dd is not None:
            drift[lbl] = dd

    if drift:
        plot_per_condition(drift, "|expressed_care − genome_care|",
                           "Plasticity Drift per Cohort (plast_on only)",
                           out / "drift_per_condition.png")
        plot_overall(drift, "|expressed_care − genome_care|",
                     "Plasticity Drift — plast_on Conditions",
                     out / "drift_overall.png")
    else:
        print("  No plasticity drift data available (expressed weights missing).")

    # ── 4. Mother nRMST ──────────────────────────────────────────────────────
    print("[4/5] Mother nRMST")
    mnrmst = {lbl: compute_mother_nrmst(d["m"]) for lbl, d in raw.items()}
    plot_per_condition(mnrmst, f"nRMST (horizon H={H_MOTHER})",
                       "Mother Longevity (nRMST) per Cohort",
                       out / "mother_nrmst_per_condition.png")
    plot_overall(mnrmst, f"nRMST (horizon H={H_MOTHER})",
                 "Mother Longevity — All Conditions",
                 out / "mother_nrmst_overall.png")

    # ── 5. Child nRMST ───────────────────────────────────────────────────────
    print("[5/5] Child nRMST")
    cnrmst = {}
    for lbl, d in raw.items():
        cd = compute_child_nrmst(d["c"])
        if cd is not None:
            cnrmst[lbl] = cd

    if cnrmst:
        plot_per_condition(cnrmst, f"nRMST (horizon H={H_CHILD})",
                           "Child Survival (nRMST) per Cohort",
                           out / "child_nrmst_per_condition.png")
        plot_overall(cnrmst, f"nRMST (horizon H={H_CHILD})",
                     "Child Survival — All Conditions",
                     out / "child_nrmst_overall.png")

    # ── 6. Population size — HIGH-level fitness ──────────────────────────────
    print("[6/6] Population size (high-level fitness)")
    pop: dict[str, pd.DataFrame] = {}
    for lbl, d in raw.items():
        pd_pop = compute_population_fitness(d["s"])
        if pd_pop is not None:
            pop[lbl] = pd_pop

    if pop:
        plot_per_condition(pop, "Alive mothers (population size)",
                           "High-Level Fitness: Population Size per Condition",
                           out / "population_per_condition.png",
                           x_col="tick", x_label="Tick")
        plot_overall(pop, "Alive mothers (population size)",
                     "High-Level Fitness: Population Size — All Conditions",
                     out / "population_overall.png",
                     x_col="tick", x_label="Tick")
    else:
        print("  No snapshot data available for population fitness.")

    total = len(list(out.glob("*.png")))
    print(f"\nDone. {total} figures saved to: {out}")


if __name__ == "__main__":
    main()
