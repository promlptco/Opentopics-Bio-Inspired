"""Academic re-plotter for all figures used in REPORT.md.

Generates publication-quality replacements for:
  Fig 2  — Phase 4 ISM sweep: child maturation vs infant starvation multiplier
  Fig 3  — Phase 4 weight sweep heatmap: care × forage → child maturation rate
  Fig 4  — Phase 4b scatter: mother survival vs child maturation across ecology
  Fig 6  — Block 2 main cohort: maturation fraction over generation
  Fig 7  — Block 2 main cohort: plasticity drift over generation
  Fig 8  — Block 2 main cohort: learning cost over generation
  Fig 9  — Block 2b cohort:    maturation fraction over generation
  Fig 10 — Block 2b cohort:    plasticity drift over generation
  Fig 11 — Block 2b cohort:    learning cost over generation

Style: Palatino serif, muted colour-blind palette (Wong 2011),
       mean ± 95 % CI (1.96 × SE), white background, outward ticks.

Usage:
  python -m experiments.plot_report_academic
"""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]

# ── Shared style ──────────────────────────────────────────────────────────────
_FONT = ["Palatino Linotype", "Palatino", "Georgia", "DejaVu Serif", "serif"]
plt.rcParams.update({
    "font.family": "serif",
    "font.serif": _FONT,
    "font.size": 11,
    "axes.titlesize": 13,
    "axes.labelsize": 11,
    "xtick.labelsize": 9,
    "ytick.labelsize": 9,
    "legend.fontsize": 9,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.linewidth": 0.9,
    "xtick.direction": "out",
    "ytick.direction": "out",
    "xtick.major.size": 4,
    "ytick.major.size": 4,
    "xtick.major.width": 0.8,
    "ytick.major.width": 0.8,
    "axes.grid": True,
    "grid.color": "#e5e5e5",
    "grid.linewidth": 0.6,
    "axes.facecolor": "white",
    "figure.facecolor": "white",
})

# Wong 2011 colour-blind palette
C = {
    "blue":   "#0072B2",
    "orange": "#E69F00",
    "green":  "#009E73",
    "red":    "#D55E00",
    "purple": "#CC79A7",
    "sky":    "#56B4E9",
    "gray":   "#888888",
}

FIGSIZE  = (7.5, 4.0)
FIGSIZE_SQ = (6.0, 5.5)
DPI      = 200
CI_Z     = 1.96

P4_ROOT  = PROJECT_ROOT / "outputs" / "phase4_weight_sweep"
P5_ROOT  = PROJECT_ROOT / "outputs" / "phase5_evolution"


# ── Helpers ───────────────────────────────────────────────────────────────────

def _save(fig: plt.Figure, path: Path) -> None:
    fig.savefig(path, dpi=DPI, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved -> {path.relative_to(PROJECT_ROOT)}")


def _style_ax(ax: plt.Axes, xlabel: str, ylabel: str) -> None:
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)


# ── Fig 2 — ISM sweep ─────────────────────────────────────────────────────────

def fig2_ism_sweep() -> None:
    ism_dirs = {
        1.00: P4_ROOT / "sweep_ism1",
        1.20: P4_ROOT / "sweep_ism1p2",
        2.33: P4_ROOT / "sweep_ism2p33",
    }
    ism_vals, cmr_means, cmr_sds = [], [], []
    for ism, d in sorted(ism_dirs.items()):
        df = pd.read_csv(d / "sweep_summary.csv")
        ism_vals.append(ism)
        cmr_means.append(float(df["c_matr_mean"].mean()))
        cmr_sds.append(float(df["c_matr_mean"].std()))

    fig, ax = plt.subplots(figsize=(5.5, 4.0))
    x = np.arange(len(ism_vals))
    colors = [C["green"], C["orange"], C["red"]]
    bars = ax.bar(x, cmr_means, yerr=cmr_sds, color=colors,
                  capsize=5, width=0.5, alpha=0.85,
                  error_kw=dict(elinewidth=1.2, ecolor="black", capthick=1.2))
    ax.set_xticks(x)
    ax.set_xticklabels([f"ISM = {v}" for v in ism_vals])
    ax.set_ylim(0, max(cmr_means) * 1.4)
    for i, (m, s) in enumerate(zip(cmr_means, cmr_sds)):
        ax.text(i, m + s + 0.01, f"{m:.3f}", ha="center", va="bottom",
                fontsize=9, fontweight="bold")
    _style_ax(ax, "Infant Starvation Multiplier (ISM)",
              "Child Maturation Rate (mean ± SD across weight combinations)")
    ax.set_title("Effect of Infant Starvation Multiplier on Child Maturation",
                 fontweight="bold", pad=8)
    fig.tight_layout()
    _save(fig, P4_ROOT / "ism_vs_child_survival.png")


# ── Fig 3 — Phase 4 weight sweep heatmap ─────────────────────────────────────

def fig3_weight_heatmap() -> None:
    df = pd.read_csv(P4_ROOT / "sweep_ism1" / "sweep_summary.csv")
    care_vals   = sorted(df["care_weight"].unique())
    forage_vals = sorted(df["forage_weight"].unique())

    grid = np.full((len(forage_vals), len(care_vals)), np.nan)
    for _, row in df.iterrows():
        ci = care_vals.index(row["care_weight"])
        fi = forage_vals.index(row["forage_weight"])
        grid[fi, ci] = row["c_matr_mean"]

    fig, ax = plt.subplots(figsize=FIGSIZE_SQ)
    im = ax.imshow(grid, aspect="auto", cmap="viridis", origin="lower",
                   vmin=0, vmax=1)

    ax.set_xticks(range(len(care_vals)))
    ax.set_xticklabels([f"{v:.1f}" for v in care_vals], fontsize=8)
    ax.set_yticks(range(len(forage_vals)))
    ax.set_yticklabels([f"{v:.1f}" for v in forage_vals], fontsize=8)
    ax.set_xlabel("Care weight")
    ax.set_ylabel("Forage weight")
    ax.set_title("Child Maturation Rate — Care × Forage Weight Sweep\n(ISM = 1.0, n = 5 seeds)",
                 fontweight="bold", pad=8)

    # Annotate cells
    vmin, vmax = np.nanmin(grid), np.nanmax(grid)
    span = max(vmax - vmin, 1e-6)
    for fi in range(len(forage_vals)):
        for ci in range(len(care_vals)):
            v = grid[fi, ci]
            if not np.isnan(v):
                brightness = (v - vmin) / span
                tc = "white" if brightness < 0.5 else "black"
                ax.text(ci, fi, f"{v:.2f}", ha="center", va="center",
                        fontsize=7, color=tc, fontweight="bold")

    # Mark best point (care=0.5, forage=2.0)
    best_ci = care_vals.index(0.5) if 0.5 in care_vals else None
    best_fi = forage_vals.index(2.0) if 2.0 in forage_vals else None
    if best_ci is not None and best_fi is not None:
        ax.add_patch(plt.Rectangle(
            (best_ci - 0.5, best_fi - 0.5), 1, 1,
            fill=False, edgecolor=C["red"], linewidth=2.5, linestyle="--",
        ))
        ax.text(best_ci, best_fi + 0.55, "selected",
                ha="center", va="bottom", fontsize=7, color=C["red"])

    cbar = plt.colorbar(im, ax=ax, shrink=0.85)
    cbar.set_label("Child Maturation Rate", fontsize=9)
    fig.tight_layout()
    _save(fig, P4_ROOT / "sweep_ism1" / "sweep_heatmap.png")


# ── Fig 4 — Phase 4b scatter ──────────────────────────────────────────────────

def fig4_phase4b_scatter() -> None:
    p4b_dir = P4_ROOT / "phase4b_20260510_111325"
    df = pd.read_csv(p4b_dir / "sweep_summary.csv")

    with open(p4b_dir / "selected_ecology.json") as f:
        eco = json.load(f)["BEST_CALIBRATED"]
    best_x = float(eco["c_matr_mean"])
    best_y = float(eco["m_surv_mean"])

    fig, ax = plt.subplots(figsize=FIGSIZE)

    sc = ax.scatter(
        df["c_matr_mean"], df["m_surv_mean"],
        c=df["eat_gain"], cmap="plasma",
        s=50, alpha=0.7, zorder=3,
        edgecolors="none",
    )
    ax.scatter(best_x, best_y, marker="*", s=250, color=C["red"],
               zorder=5, label="BEST_CALIBRATED", edgecolors="black", linewidths=0.8)
    ax.axvline(0.5, color=C["gray"], linestyle=":", linewidth=1.0, alpha=0.6)
    ax.axhline(1.0, color=C["gray"], linestyle=":", linewidth=1.0, alpha=0.6)

    cbar = plt.colorbar(sc, ax=ax, shrink=0.85)
    cbar.set_label("eat_gain", fontsize=9)
    _style_ax(ax, "Child Maturation Rate (c_matr_mean)",
              "Mother Survival Rate (m_surv_mean)")
    ax.set_title("Phase 4b Ecology Sweep: Mother Survival vs Child Maturation\n"
                 "(each point = one (init_food, eat_gain) combination)",
                 fontweight="bold", pad=8)
    ax.legend(fontsize=9, loc="upper left")
    fig.tight_layout()
    _save(fig, p4b_dir / "scatter_msurv_cmatr.png")


# ── Phase 5 cohort re-plotter (Figs 6–11) ────────────────────────────────────

def _tv_drift(g: pd.DataFrame) -> float:
    cols = {"final_genome_forage", "final_genome_self",
            "final_expressed_forage", "final_expressed_self"}
    if cols.issubset(g.columns):
        d = (
            (g["final_expressed_care"]   - g["final_genome_care"]).abs()
            + (g["final_expressed_forage"] - g["final_genome_forage"]).abs()
            + (g["final_expressed_self"]   - g["final_genome_self"]).abs()
        )
        return float((0.5 * d).mean())
    return float((g["final_expressed_care"] - g["final_genome_care"]).abs().mean())


def _build_cohort(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (seed, gen), grp in df.groupby(["seed", "generation"], sort=True):
        if (grp["event_type"] == "censored").any():
            continue
        tot  = float(grp["total_children"].sum())
        matd = float(grp["matured_children"].sum())
        rows.append({
            "seed":       int(seed),
            "generation": int(gen),
            "maturation_fraction": matd / tot if tot > 0 else np.nan,
            "plasticity_drift":    _tv_drift(grp),
            "learning_cost": float(grp["lifetime_learning_cost"].mean())
                             if "lifetime_learning_cost" in grp.columns else np.nan,
        })
    return pd.DataFrame(rows)


def _ci_band(df: pd.DataFrame, col: str, min_seeds: int = 3) -> pd.DataFrame:
    agg = (
        df.groupby("generation")[col]
        .agg(mean="mean", std="std", n="count")
        .reset_index()
        .sort_values("generation")
    )
    agg = agg[agg["n"] >= min_seeds].copy()
    agg["std"]  = agg["std"].fillna(0.0)
    agg["se"]   = agg["std"] / np.sqrt(agg["n"].clip(lower=1))
    agg["lo"]   = agg["mean"] - CI_Z * agg["se"]
    agg["hi"]   = agg["mean"] + CI_Z * agg["se"]
    return agg


def _cohort_plot(
    cohort: pd.DataFrame,
    col: str,
    color: str,
    title: str,
    ylabel: str,
    out_path: Path,
    ylim: tuple[float, float] | None = None,
    neutral: float | None = None,
) -> None:
    agg = _ci_band(cohort, col)
    if agg.empty:
        print(f"  [skip] {out_path.name}: no data after CI filter")
        return

    fig, ax = plt.subplots(figsize=FIGSIZE)

    # Per-seed light traces
    for seed, g in cohort.groupby("seed"):
        g = g.sort_values("generation")
        ax.plot(g["generation"], g[col], color=color, linewidth=0.6,
                alpha=0.15, zorder=1)

    # CI band
    lo = agg["lo"].clip(*(ylim if ylim else (-np.inf, np.inf)))
    hi = agg["hi"].clip(*(ylim if ylim else (-np.inf, np.inf)))
    ax.fill_between(agg["generation"], lo, hi, color=color, alpha=0.18, zorder=2)
    ax.plot(agg["generation"], agg["mean"], color=color, linewidth=1.8,
            label="Mean ± 95% CI", zorder=3)

    if neutral is not None:
        ax.axhline(neutral, color=C["red"], linestyle=":", linewidth=1.2,
                   alpha=0.8, label=f"Neutral ({neutral:.2f})")

    ax.set_title(title, fontweight="bold", pad=8)
    ax.set_xlabel("Generation")
    ax.set_ylabel(ylabel)
    if ylim:
        ax.set_ylim(*ylim)
    handles, labels = ax.get_legend_handles_labels()
    if handles:
        ax.legend(handles, labels, loc="best", frameon=True,
                  framealpha=0.9, edgecolor="#cccccc")
    fig.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    _save(fig, out_path)


def _run_cohort_block(run_dir: Path, label: str, out_dir: Path) -> None:
    lp = run_dir / "mother_lifecycle.csv"
    if not lp.exists():
        print(f"  [skip] No mother_lifecycle.csv in {run_dir.name}")
        return
    df     = pd.read_csv(lp)
    cohort = _build_cohort(df)
    if cohort.empty:
        print(f"  [skip] No completed cohort generations in {run_dir.name}")
        return

    _cohort_plot(
        cohort, "maturation_fraction", C["green"],
        f"Offspring Maturation Fraction — {label}\n(completed cohorts only, mean ± 95% CI)",
        "Matured offspring / born",
        out_dir / "maturation_fraction_overall.png",
        ylim=(0.0, 1.05),
    )
    _cohort_plot(
        cohort, "plasticity_drift", C["blue"],
        f"Plasticity Drift — {label}\n(TV(expressed, genome), mean ± 95% CI)",
        "Total variation distance",
        out_dir / "plasticity_drift_overall.png",
        ylim=(0.0, 0.6),
    )
    if cohort["learning_cost"].notna().any():
        _cohort_plot(
            cohort, "learning_cost", C["red"],
            f"Lifetime Learning Cost — {label}\n(mean metabolic cost of plasticity per mother, ± 95% CI)",
            "Lifetime learning cost",
            out_dir / "learning_cost_overall.png",
        )
    else:
        print(f"  [skip] learning_cost: no data in {run_dir.name}")


def figs6_11_cohort() -> None:
    pairs = [
        (
            P5_ROOT / "block2_main_mut_on_plast_on",
            "Block 2 Main (mut+/plast+, lr=1.0)",
            P5_ROOT / "block2_main_mut_on_plast_on" / "cohort_plots",
        ),
        (
            P5_ROOT / "block2b_mut_on_plast_on_lr0p25_pc0p25",
            "Block 2b (mut+/plast+, lr=0.25)",
            P5_ROOT / "block2b_mut_on_plast_on_lr0p25_pc0p25" / "cohort_plots",
        ),
    ]
    for run_dir, label, out_dir in pairs:
        print(f"\n[cohort] {label}")
        _run_cohort_block(run_dir, label, out_dir)


# ── Entry point ───────────────────────────────────────────────────────────────

def main() -> None:
    print("=== Academic report figure re-generation ===\n")

    print("[Phase 4] Fig 2 — ISM sweep bar chart")
    fig2_ism_sweep()

    print("\n[Phase 4] Fig 3 — Weight sweep heatmap")
    fig3_weight_heatmap()

    print("\n[Phase 4b] Fig 4 — Ecology scatter")
    fig4_phase4b_scatter()

    print("\n[Phase 5 cohort] Figs 6–11")
    figs6_11_cohort()

    print("\n[ok] All report figures regenerated in academic style.")


if __name__ == "__main__":
    main()
