"""
Generate all academic-style figures for REPORT.md.
One consistent style applied to every figure.
Output: outputs/report_figures/
"""

import json
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
from pathlib import Path
from scipy import stats

OUT   = Path("outputs/report_figures")
OUT.mkdir(parents=True, exist_ok=True)
BASE  = Path(".")

# ── Unified academic style ────────────────────────────────────────────────────
STYLE = {
    "font.family":          "serif",
    "axes.spines.top":      False,
    "axes.spines.right":    False,
    "axes.grid":            True,
    "grid.alpha":           0.30,
    "grid.color":           "#bbbbbb",
    "grid.linestyle":       "--",
    "axes.labelsize":       12,
    "axes.titlesize":       12,
    "axes.titleweight":     "bold",
    "xtick.labelsize":      11,
    "ytick.labelsize":      11,
    "legend.fontsize":      10,
    "legend.framealpha":    0.85,
    "legend.edgecolor":     "#cccccc",
    "figure.dpi":           150,
    "figure.facecolor":     "white",
    "axes.facecolor":       "white",
}

COND_COLORS = {
    "mut_off_plast_off": "#4C72B0",
    "mut_on_plast_off":  "#55A868",
    "mut_off_plast_on":  "#C44E52",
    "mut_on_plast_on":   "#8172B2",
}
COND_LABELS = {
    "mut_off_plast_off": "Mut OFF / Plast OFF",
    "mut_on_plast_off":  "Mut ON / Plast OFF",
    "mut_off_plast_on":  "Mut OFF / Plast ON",
    "mut_on_plast_on":   "Mut ON / Plast ON",
}

# Extinction ticks per condition (hardcoded from summary JSONs)
EXT_TICKS = {
    "mut_off_plast_off": [4161, 9059, 12226, 11287, 8822, 6866, 7002, 7439, 14178, 9131],
    "mut_on_plast_off":  [5670, 10720, 15410, 9691, 13594, 6382, 9905, 9840, 14828, 9504],
    "mut_off_plast_on":  [10814, 14111, 12860, 13000, 14974, 15057, 17208, 29732],
    "mut_on_plast_on":   [9658, 12423, 14653, 16696, 17199, 17135, 17240, 22182, 11553, 23003],
}

COND_DIRS = [
    ("mut_off_plast_off", "block2_main_mut_off_plast_off"),
    ("mut_on_plast_off",  "block2_main_mut_on_plast_off"),
    ("mut_off_plast_on",  "block2_main_mut_off_plast_on"),
    ("mut_on_plast_on",   "block2_main_mut_on_plast_on"),
]


def savefig(fig, name, **kw):
    fig.savefig(OUT / name, bbox_inches="tight", **kw)
    plt.close(fig)
    print(f"[ok] {name}")


def cliffs_delta(a, b):
    a, b = np.asarray(a), np.asarray(b)
    count = sum(1 if x > y else (-1 if x < y else 0) for x in a for y in b)
    return count / (len(a) * len(b))


# ─────────────────────────────────────────────────────────────────────────────
# FIGURE 2 ── Phase 2 Self-Survival Baseline (3 ecologies, data-driven)
# ─────────────────────────────────────────────────────────────────────────────
PH2_DIR = Path("outputs/phase2_survival_minimal/newmech_auto_1000_percept8")


def fig_ph2_baseline():
    ecologies = ["harsh", "balanced", "easy"]
    labels    = ["Harsh", "Balanced", "Easy"]
    colors    = ["#C44E52", "#4C72B0", "#55A868"]

    pop_data, energy_data, fail_data = [], [], []
    for eco in ecologies:
        df = pd.read_csv(PH2_DIR / f"validation_{eco}.csv")
        pop_data.append(df["final_pop"].values)
        energy_data.append(df["mean_energy"].values)
        forage_total = df["FORAGE"].replace(0, np.nan)
        fail_rate = df["FAILED_FORAGE"] / forage_total * 100
        fail_data.append(fail_rate.dropna().values)

    with plt.rc_context(STYLE):
        fig, axes = plt.subplots(1, 3, figsize=(13, 4.5))

        for ax, data, ylabel, title in [
            (axes[0], pop_data,    "Final population (alive mothers)", "(a) Population"),
            (axes[1], energy_data, "Mean agent energy (0–1)",          "(b) Agent Energy"),
            (axes[2], fail_data,   "Failed forage rate (%)",           "(c) Foraging Pressure"),
        ]:
            bp = ax.boxplot(data, patch_artist=True, widths=0.5,
                            medianprops=dict(color="black", linewidth=2),
                            whiskerprops=dict(linewidth=1.2),
                            capprops=dict(linewidth=1.2),
                            flierprops=dict(marker="o", markersize=4, alpha=0.55, linestyle="none"))
            for patch, col in zip(bp["boxes"], colors):
                patch.set_facecolor(col)
                patch.set_alpha(0.72)
            ax.set_xticks(range(1, 4))
            ax.set_xticklabels(labels)
            ax.set_ylabel(ylabel)
            ax.set_title(title)
            ax.set_ylim(bottom=0)

        fig.suptitle("Self-Survival Baseline Across Three Ecological Difficulty Levels",
                     fontsize=13, fontweight="bold", y=1.02)
        fig.tight_layout()
    savefig(fig, "fig02_ph2_baseline.png")


# ─────────────────────────────────────────────────────────────────────────────
# FIGURE 2b ── Phase 2 OVAT Sensitivity Analysis (4 parameters)
# ─────────────────────────────────────────────────────────────────────────────
def fig_ph2_ovat():
    PH2_OVAT = PH2_DIR / "sensitivity_ovat"

    panels = [
        ("set_A_init_food.csv",          "param_value", "Initial food cells",      "(a) Food abundance (init_food)"),
        ("set_B_eat_gain.csv",           "param_value", "Energy gain per food",    "(b) Energy per food (eat_gain)"),
        ("set_C_move_cost.csv",          "param_value", "Energy cost per move",    "(c) Movement cost (move_cost)"),
        ("set_D_food_entropy_alpha.csv", "param_value", "Entropy parameter α",     "(d) Food patchiness (α)"),
    ]

    with plt.rc_context(STYLE):
        fig, axes = plt.subplots(2, 2, figsize=(11, 7), constrained_layout=True)

        for ax, (fname, xcol, xlabel, title) in zip(axes.flatten(), panels):
            df  = pd.read_csv(PH2_OVAT / fname)
            x   = df[xcol].values
            y   = df["tail_pop_mean"].values
            sd  = df["tail_pop_sd"].values

            ax.plot(x, y, "o-", color="#4C72B0", linewidth=1.8, markersize=6,
                    markerfacecolor="#4C72B0", markeredgecolor="white", markeredgewidth=0.8)
            ax.fill_between(x, np.maximum(0, y - sd), y + sd,
                            color="#4C72B0", alpha=0.18)
            ax.set_xlabel(xlabel)
            ax.set_ylabel("Tail-window population (mean ± SD)")
            ax.set_title(title)
            ax.set_ylim(bottom=0)

        fig.suptitle("OVAT Sensitivity: Parameter Effect on Population Stability",
                     fontsize=13, fontweight="bold")
    savefig(fig, "fig02b_ph2_ovat.png")


# ─────────────────────────────────────────────────────────────────────────────
# FIGURE 3 ── Food Mechanism: self-only pop + child maturation composite
# ─────────────────────────────────────────────────────────────────────────────
def fig_food_mechanism():
    alpha_labels = ["F0\n(a=0.00)", "F1\n(a=0.01)", "F2\n(a=0.05)", "F3\n(a=0.10)"]
    p2_pop  = [11.7, 8.8,  7.6,  6.8];  p2_sd  = [0.9,  1.66, 2.01, 1.99]
    p3_matr = [0.287, 0.493, 0.940, 0.960]; p3_sd = [0.108, 0.137, 0.063, 0.053]
    bar_col_matr = ["#4C72B0", "#55A868", "#DD8452", "#C44E52"]
    x = np.arange(4)

    with plt.rc_context(STYLE):
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 4.5))

        bars = ax1.bar(x, p2_pop, 0.6, yerr=p2_sd, color="#4C72B0", alpha=0.72,
                       capsize=4, error_kw=dict(elinewidth=1.2, ecolor="black"))
        for bar, v in zip(bars, p2_pop):
            ax1.text(bar.get_x()+bar.get_width()/2, v+0.3, f"{v:.1f}",
                     ha="center", va="bottom", fontsize=11)
        ax1.set_xticks(x); ax1.set_xticklabels(alpha_labels)
        ax1.set_ylabel("Mean alive mothers (tail window)")
        ax1.set_xlabel("Food distribution condition")
        ax1.set_title("(a) Self-only population")
        ax1.set_ylim(0, 15)

        bars2 = ax2.bar(x, p3_matr, 0.6, yerr=p3_sd, color=bar_col_matr, alpha=0.80,
                        capsize=4, error_kw=dict(elinewidth=1.2, ecolor="black"))
        for bar, v in zip(bars2, p3_matr):
            ax2.text(bar.get_x()+bar.get_width()/2, v+0.02, f"{v:.3f}",
                     ha="center", va="bottom", fontsize=11)
        ax2.set_xticks(x); ax2.set_xticklabels(alpha_labels)
        ax2.set_ylabel("Child maturation rate (fraction)")
        ax2.set_xlabel("Food distribution condition")
        ax2.set_title("(b) Child maturation rate")
        ax2.set_ylim(0, 1.20)
        ax2.axhline(1.0, color="#999999", linestyle="--", linewidth=0.9)

        fig.suptitle("Effect of Shannon Entropy Food Distribution on Survival and Child Maturation",
                     fontsize=13, fontweight="bold", y=1.02)
        fig.tight_layout()
    savefig(fig, "fig03_food_mechanism.png")


# ─────────────────────────────────────────────────────────────────────────────
# FIGURE 4 ── Phase 4 Weight Sweep: care_weight vs outcomes
# ─────────────────────────────────────────────────────────────────────────────
def fig_ph4_weight_sweep():
    df = pd.read_csv(BASE / "outputs/phase4_weight_sweep/sweep_ism1/sweep_summary.csv")

    with plt.rc_context(STYLE):
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 4.5))

        sc = ax1.scatter(df["care_weight"], df["c_matr_mean"],
                         c=df["forage_weight"], cmap="viridis_r",
                         s=55, alpha=0.85, edgecolors="white", linewidths=0.4)
        cb1 = fig.colorbar(sc, ax=ax1, shrink=0.85)
        cb1.set_label("Forage weight", fontsize=10)
        ax1.axvline(0.5, color="#C44E52", linestyle="--", linewidth=1.0, alpha=0.7,
                    label="Optimal (g_c = 0.5)")
        ax1.set_xlabel("Care weight (g_c)")
        ax1.set_ylabel("Child maturation rate")
        ax1.set_title("(a) Care weight vs. child maturation")
        ax1.legend(fontsize=9)

        sc2 = ax2.scatter(df["care_weight"], df["m_surv_mean"],
                          c=df["forage_weight"], cmap="viridis_r",
                          s=55, alpha=0.85, edgecolors="white", linewidths=0.4)
        cb2 = fig.colorbar(sc2, ax=ax2, shrink=0.85)
        cb2.set_label("Forage weight", fontsize=10)
        ax2.axvline(0.5, color="#C44E52", linestyle="--", linewidth=1.0, alpha=0.7,
                    label="Optimal (g_c = 0.5)")
        ax2.set_xlabel("Care weight (g_c)")
        ax2.set_ylabel("Mother survival rate")
        ax2.set_title("(b) Care weight vs. mother survival")
        ax2.legend(fontsize=9)

        fig.suptitle("Genome Weight Sweep: Care Allocation vs. Fitness Outcomes",
                     fontsize=13, fontweight="bold", y=1.02)
        fig.tight_layout()
    savefig(fig, "fig04_ph4_weight_sweep.png")


# ─────────────────────────────────────────────────────────────────────────────
# FIGURE 5 ── Phase 5 Extinction Timing Comparison (box + strip)
# ─────────────────────────────────────────────────────────────────────────────
def fig_ph5_extinction():
    keys   = list(EXT_TICKS.keys())
    data   = [np.array(EXT_TICKS[k]) / 1000 for k in keys]
    colors = [COND_COLORS[k] for k in keys]
    labels = [COND_LABELS[k].replace(" / ", "\n") for k in keys]
    rng    = np.random.default_rng(42)

    with plt.rc_context(STYLE):
        fig, ax = plt.subplots(figsize=(9, 5))
        bp = ax.boxplot(data, patch_artist=True, widths=0.45,
                        medianprops=dict(color="black", linewidth=2),
                        whiskerprops=dict(linewidth=1.2),
                        capprops=dict(linewidth=1.2),
                        flierprops=dict(marker="o", markersize=4, linestyle="none", alpha=0.6))
        for patch, col in zip(bp["boxes"], colors):
            patch.set_facecolor(col); patch.set_alpha(0.65)

        for i, (d, col) in enumerate(zip(data, colors), 1):
            jit = rng.uniform(-0.13, 0.13, size=len(d))
            ax.scatter(i + jit, d, color=col, s=30, zorder=4,
                       alpha=0.90, edgecolors="white", linewidths=0.5)
            med = np.median(d)
            ax.text(i + 0.30, med, f" {med:.1f}k", va="center", fontsize=9.5)

        ax.set_xticks(range(1, 5))
        ax.set_xticklabels(labels, fontsize=10)
        ax.set_ylabel("Extinction tick (x10^3)")
        ax.set_xlabel("Experimental condition")
        ax.set_ylim(0, max(max(d) for d in data) * 1.18)
        fig.suptitle("Lineage Survival Duration Across Experimental Conditions",
                     fontsize=13, fontweight="bold")
        fig.tight_layout()
    savefig(fig, "fig05_ph5_extinction.png")


# ─────────────────────────────────────────────────────────────────────────────
# FIGURE 6 ── Phase 5: Population dynamics — all 4 conditions in 2×2 grid
# ─────────────────────────────────────────────────────────────────────────────
def fig_ph5_population_4cond():
    with plt.rc_context(STYLE):
        fig, axes = plt.subplots(2, 2, figsize=(13, 8), sharex=False, sharey=False)
        axes_flat = axes.flatten()

        for ax, (key, folder) in zip(axes_flat, COND_DIRS):
            df = pd.read_csv(BASE / f"outputs/phase5_evolution/{folder}/snapshots.csv")
            color = COND_COLORS[key]

            for seed, sdf in df.groupby("seed"):
                ax.plot(sdf["tick"] / 1000, sdf["n_mothers"], color=color,
                        alpha=0.22, linewidth=0.8)

            agg = df.groupby("tick")["n_mothers"].agg(["mean", "sem"]).reset_index()
            ax.plot(agg["tick"] / 1000, agg["mean"], color=color, linewidth=2.0,
                    label="Mean")
            ax.fill_between(agg["tick"] / 1000,
                            agg["mean"] - 1.96 * agg["sem"],
                            agg["mean"] + 1.96 * agg["sem"],
                            color=color, alpha=0.20)

            ax.set_title(COND_LABELS[key], fontsize=11)
            ax.set_xlabel("Tick (x10^3)", fontsize=10)
            ax.set_ylabel("Alive mothers", fontsize=10)
            ax.set_ylim(bottom=0)

        fig.suptitle("Mother Population Dynamics Across All Four Conditions",
                     fontsize=13, fontweight="bold", y=1.01)
        fig.tight_layout()
    savefig(fig, "fig06_ph5_population_4cond.png")


# ─────────────────────────────────────────────────────────────────────────────
# FIGURE 7 ── Phase 5: Genome care weight — all 4 conditions overlaid
# ─────────────────────────────────────────────────────────────────────────────
def fig_ph5_genome_care_4cond():
    with plt.rc_context(STYLE):
        fig, ax = plt.subplots(figsize=(10, 5))

        for key, folder in COND_DIRS:
            df = pd.read_csv(BASE / f"outputs/phase5_evolution/{folder}/snapshots.csv")
            df = df[df["n_mothers"] > 0]
            color = COND_COLORS[key]

            agg = df.groupby("tick")["mean_genome_care"].agg(["mean", "sem"]).reset_index()
            ax.plot(agg["tick"] / 1000, agg["mean"], color=color, linewidth=1.8,
                    label=COND_LABELS[key])
            ax.fill_between(agg["tick"] / 1000,
                            agg["mean"] - 1.96 * agg["sem"],
                            agg["mean"] + 1.96 * agg["sem"],
                            color=color, alpha=0.15)

        ax.axhline(1/3, color="#999999", linestyle="--", linewidth=1.0,
                   label="Neutral (1/3)")
        ax.set_xlabel("Tick (x10^3)")
        ax.set_ylabel("Mean genome care weight (g_c)")
        ax.set_ylim(0.25, 0.55)
        ax.legend(loc="upper left", fontsize=9)
        fig.suptitle("Genome Care Weight Evolution Across All Four Conditions",
                     fontsize=13, fontweight="bold")
        fig.tight_layout()
    savefig(fig, "fig07_ph5_genome_care_4cond.png")


# ─────────────────────────────────────────────────────────────────────────────
# FIGURE 8 ── Phase 5 (mut_on plast_on): Expressed vs Genome care
# ─────────────────────────────────────────────────────────────────────────────
def fig_ph5_expressed_vs_genome():
    df = pd.read_csv(BASE / "outputs/phase5_evolution/block2_main_mut_on_plast_on/snapshots.csv")
    df = df[df["n_mothers"] > 0]

    agg = df.groupby("tick")[["mean_genome_care", "mean_expressed_care"]].agg(
        ["mean", "sem"]).reset_index()
    agg.columns = ["tick", "gc_mean", "gc_sem", "ec_mean", "ec_sem"]

    with plt.rc_context(STYLE):
        fig, ax = plt.subplots(figsize=(10, 4.5))

        ax.plot(agg["tick"] / 1000, agg["gc_mean"],
                color="#2166ac", linewidth=2.0, label="Genome care weight (g_c)")
        ax.fill_between(agg["tick"] / 1000,
                        agg["gc_mean"] - 1.96 * agg["gc_sem"],
                        agg["gc_mean"] + 1.96 * agg["gc_sem"],
                        color="#2166ac", alpha=0.15)

        ax.plot(agg["tick"] / 1000, agg["ec_mean"],
                color="#d6604d", linewidth=2.0, linestyle="--",
                label="Expressed care weight (w_c)")
        ax.fill_between(agg["tick"] / 1000,
                        agg["ec_mean"] - 1.96 * agg["ec_sem"],
                        agg["ec_mean"] + 1.96 * agg["ec_sem"],
                        color="#d6604d", alpha=0.15)

        ax.axhline(1/3, color="#888888", linestyle=":", linewidth=1.0,
                   label="Neutral (1/3)")
        ax.set_xlabel("Tick (x10^3)")
        ax.set_ylabel("Weight (0-1)")
        ax.legend(loc="upper right", fontsize=9)
        ax.set_ylim(0.0, 0.55)
        fig.suptitle("Genome vs. Expressed Care Weight Over Time  (Mut ON / Plast ON)",
                     fontsize=13, fontweight="bold")
        fig.tight_layout()
    savefig(fig, "fig08_ph5_expressed_vs_genome.png")


# ─────────────────────────────────────────────────────────────────────────────
# FIGURE 9 ── Phase 5: Child survival rate — all 4 conditions overlaid
# ─────────────────────────────────────────────────────────────────────────────
def fig_ph5_child_survival_4cond():
    with plt.rc_context(STYLE):
        fig, ax = plt.subplots(figsize=(10, 5))

        for key, folder in COND_DIRS:
            df = pd.read_csv(BASE / f"outputs/phase5_evolution/{folder}/snapshots.csv")
            df = df[(df["n_mothers"] > 0) & (df["tick"] > 0)]
            color = COND_COLORS[key]

            agg = df.groupby("tick")["child_survival_rate"].agg(["mean","sem"]).reset_index()
            agg["smoothed"] = agg["mean"].rolling(10, min_periods=1, center=True).mean()
            ax.plot(agg["tick"] / 1000, agg["smoothed"], color=color,
                    linewidth=1.8, label=COND_LABELS[key])
            ax.fill_between(agg["tick"] / 1000,
                            (agg["mean"] - 1.96 * agg["sem"]).clip(0),
                            (agg["mean"] + 1.96 * agg["sem"]).clip(1),
                            color=color, alpha=0.12)

        ax.set_xlabel("Tick (x10^3)")
        ax.set_ylabel("Child maturation rate (0-1)")
        ax.set_ylim(0, 1.0)
        ax.legend(loc="upper right", fontsize=9)
        fig.suptitle("Child Survival Rate Over Time — All Conditions",
                     fontsize=13, fontweight="bold")
        fig.tight_layout()
    savefig(fig, "fig09_ph5_child_survival_4cond.png")


# ─────────────────────────────────────────────────────────────────────────────
# FIGURE 10 ── Birth Scatter Radius Sensitivity
# ─────────────────────────────────────────────────────────────────────────────
def fig_birth_scatter_sensitivity():
    r2 = [9658,12423,14653,16696,17199,17135,17240,22182,11553,23003]
    r3 = [4824,4615,4681,3798,3295,3390,3643,3875,4168,3997]
    r5 = [4217,4583,5429,3994,4369,4374,4227,3765,3892,3266]
    data   = [np.array(d)/1000 for d in [r2, r3, r5]]
    labels = ["radius = 2\n(baseline)", "radius = 3", "radius = 5"]
    colors = ["#55A868", "#DD8452", "#C44E52"]
    rng    = np.random.default_rng(7)

    with plt.rc_context(STYLE):
        fig, ax = plt.subplots(figsize=(8, 5))
        bp = ax.boxplot(data, patch_artist=True, widths=0.45,
                        medianprops=dict(color="black", linewidth=2),
                        whiskerprops=dict(linewidth=1.2),
                        capprops=dict(linewidth=1.2),
                        flierprops=dict(marker="o", markersize=4, linestyle="none"))
        for patch, col in zip(bp["boxes"], colors):
            patch.set_facecolor(col); patch.set_alpha(0.65)
        for i, (d, col) in enumerate(zip(data, colors), 1):
            jit = rng.uniform(-0.12, 0.12, size=len(d))
            ax.scatter(i+jit, d, color=col, s=30, zorder=4,
                       alpha=0.90, edgecolors="white", linewidths=0.5)
            ax.text(i+0.28, np.median(d), f" {np.median(d):.1f}k",
                    va="center", fontsize=10)

        ax.annotate("", xy=(1.5, 6), xytext=(2.5, 6),
                    arrowprops=dict(arrowstyle="<->", color="#C44E52", lw=1.8))
        ax.text(2.0, 6.4, "Phase transition\n(radius 2->3: -60% survival)",
                ha="center", fontsize=9, color="#C44E52")

        ax.set_xticks(range(1, 4)); ax.set_xticklabels(labels, fontsize=11)
        ax.set_ylabel("Extinction tick (x10^3)")
        ax.set_xlabel("Birth scatter radius (cells)")
        fig.suptitle("Birth Scatter Radius Sensitivity Analysis",
                     fontsize=13, fontweight="bold")
        fig.tight_layout()
    savefig(fig, "fig10_birth_scatter_sensitivity.png")


# ─────────────────────────────────────────────────────────────────────────────
# FIGURE 11 ── Phase 5: Plasticity & Innateness — all 4 conditions
# ─────────────────────────────────────────────────────────────────────────────
def fig_ph5_plasticity_4cond():
    with plt.rc_context(STYLE):
        fig, axes = plt.subplots(2, 2, figsize=(13, 8))
        axes_flat = axes.flatten()

        for ax, (key, folder) in zip(axes_flat, COND_DIRS):
            df = pd.read_csv(BASE / f"outputs/phase5_evolution/{folder}/snapshots.csv")
            df = df[df["n_mothers"] > 0]
            color = COND_COLORS[key]

            agg = df.groupby("tick")[["mean_plasticity","innateness_index"]].agg(
                ["mean","sem"]).reset_index()
            agg.columns = ["tick","pl_m","pl_s","in_m","in_s"]

            ax.plot(agg["tick"]/1000, agg["pl_m"], color="#2166ac",
                    linewidth=1.8, label="Plasticity coeff.")
            ax.fill_between(agg["tick"]/1000,
                            agg["pl_m"]-1.96*agg["pl_s"],
                            agg["pl_m"]+1.96*agg["pl_s"],
                            color="#2166ac", alpha=0.15)
            ax.plot(agg["tick"]/1000, agg["in_m"], color="#d6a920",
                    linewidth=1.8, linestyle="--", label="Innateness index")
            ax.fill_between(agg["tick"]/1000,
                            agg["in_m"]-1.96*agg["in_s"],
                            agg["in_m"]+1.96*agg["in_s"],
                            color="#d6a920", alpha=0.15)

            ax.set_title(COND_LABELS[key], fontsize=11)
            ax.set_xlabel("Tick (x10^3)", fontsize=10)
            ax.set_ylabel("Coefficient (0-1)", fontsize=10)
            ax.set_ylim(-0.05, 1.15)
            ax.legend(fontsize=8, loc="center right")

        fig.suptitle("Plasticity Coefficient and Innateness Index Across All Four Conditions",
                     fontsize=13, fontweight="bold", y=1.01)
        fig.tight_layout()
    savefig(fig, "fig11_ph5_plasticity_4cond.png")


# ─────────────────────────────────────────────────────────────────────────────
# FIGURE 12 ── Phase 5: Generation depth — all 4 conditions overlaid
# ─────────────────────────────────────────────────────────────────────────────
def fig_ph5_generation_4cond():
    with plt.rc_context(STYLE):
        fig, ax = plt.subplots(figsize=(10, 5))

        for key, folder in COND_DIRS:
            df = pd.read_csv(BASE / f"outputs/phase5_evolution/{folder}/snapshots.csv")
            df = df[df["n_mothers"] > 0]
            color = COND_COLORS[key]

            agg = df.groupby("tick")["highest_generation"].agg(["mean","sem"]).reset_index()
            ax.plot(agg["tick"]/1000, agg["mean"], color=color,
                    linewidth=1.8, label=COND_LABELS[key])
            ax.fill_between(agg["tick"]/1000,
                            agg["mean"]-1.96*agg["sem"],
                            agg["mean"]+1.96*agg["sem"],
                            color=color, alpha=0.15)

        ax.set_xlabel("Tick (x10^3)")
        ax.set_ylabel("Highest generation reached")
        ax.legend(loc="upper left", fontsize=9)
        fig.suptitle("Generational Depth Over Time — All Conditions",
                     fontsize=13, fontweight="bold")
        fig.tight_layout()
    savefig(fig, "fig12_ph5_generation_4cond.png")


# ─────────────────────────────────────────────────────────────────────────────
# FIGURE 13 ── Pairwise Mann-Whitney U + Cliff's delta matrix
# ─────────────────────────────────────────────────────────────────────────────
def fig_stat_pairwise():
    keys   = list(EXT_TICKS.keys())
    labels = [COND_LABELS[k] for k in keys]
    n      = len(keys)

    # Compute Cliff's delta and p-values for all pairs
    delta_mat = np.zeros((n, n))
    pval_mat  = np.ones((n, n))
    for i in range(n):
        for j in range(n):
            if i != j:
                a, b = EXT_TICKS[keys[i]], EXT_TICKS[keys[j]]
                delta_mat[i, j] = cliffs_delta(a, b)
                _, pval_mat[i, j] = stats.mannwhitneyu(a, b, alternative="two-sided")

    def sig_stars(p):
        if p < 0.001: return "***"
        if p < 0.01:  return "**"
        if p < 0.05:  return "*"
        return "ns"

    with plt.rc_context(STYLE):
        fig, (ax_heat, ax_bar) = plt.subplots(1, 2, figsize=(13, 5),
                                               gridspec_kw={"width_ratios": [1.2, 1]})

        # Left: Cliff's delta heatmap (upper triangle only)
        mask = np.triu(np.ones((n, n), dtype=bool), k=0)
        delta_disp = np.ma.array(delta_mat, mask=~mask)
        im = ax_heat.imshow(delta_disp, cmap="RdBu_r", vmin=-1, vmax=1, aspect="auto")
        fig.colorbar(im, ax=ax_heat, shrink=0.80, label="Cliff's delta")

        for i in range(n):
            for j in range(i, n):
                if i == j:
                    ax_heat.text(j, i, labels[i].replace(" / ", "\n"),
                                 ha="center", va="center", fontsize=7.5,
                                 color="black", fontweight="bold")
                else:
                    d = delta_mat[i, j]
                    p = pval_mat[i, j]
                    ax_heat.text(j, i, f"d={d:+.2f}\n{sig_stars(p)}",
                                 ha="center", va="center", fontsize=9,
                                 color="white" if abs(d) > 0.5 else "black")

        ax_heat.set_xticks([]); ax_heat.set_yticks([])
        ax_heat.set_title("(a) Pairwise Cliff's delta (upper triangle)", fontsize=11)
        ax_heat.spines[:].set_visible(False)

        # Right: mean ± bootstrapped 95% CI per condition
        rng = np.random.default_rng(42)
        means, ci_lo, ci_hi = [], [], []
        for k in keys:
            d = np.array(EXT_TICKS[k]) / 1000
            boot = np.array([np.mean(rng.choice(d, len(d), replace=True)) for _ in range(10000)])
            means.append(np.mean(d))
            ci_lo.append(np.mean(d) - np.percentile(boot, 2.5))
            ci_hi.append(np.percentile(boot, 97.5) - np.mean(d))

        x = np.arange(n)
        colors = [COND_COLORS[k] for k in keys]
        short_labels = ["Mut-/Pl-", "Mut+/Pl-", "Mut-/Pl+", "Mut+/Pl+"]
        for i, (m, lo, hi, col) in enumerate(zip(means, ci_lo, ci_hi, colors)):
            ax_bar.barh(i, m, xerr=[[lo], [hi]], color=col, alpha=0.80,
                        capsize=5, error_kw=dict(elinewidth=1.5, ecolor="black"))
            ax_bar.text(m + hi + 0.3, i, f"{m:.1f}k", va="center", fontsize=10)

        ax_bar.set_yticks(x); ax_bar.set_yticklabels(short_labels, fontsize=10)
        ax_bar.set_xlabel("Extinction tick (x10^3)")
        ax_bar.set_title("(b) Mean with bootstrap 95% CI", fontsize=11)
        ax_bar.invert_yaxis()

        fig.suptitle("Pairwise Statistical Comparison — Extinction Tick by Condition",
                     fontsize=13, fontweight="bold", y=1.02)
        fig.tight_layout()
    savefig(fig, "fig13_stat_pairwise.png")


# ─────────────────────────────────────────────────────────────────────────────
# FIGURE 14 ── Regression: genome care at t=2000 vs extinction tick
# ─────────────────────────────────────────────────────────────────────────────
def fig_stat_regression():
    TARGET_TICK = 2000
    records = []

    for key, folder in COND_DIRS:
        df = pd.read_csv(BASE / f"outputs/phase5_evolution/{folder}/snapshots.csv")
        snap = df[df["tick"] == TARGET_TICK]
        for seed, sdf in snap.groupby("seed"):
            gc = sdf["mean_genome_care"].values[0]
            ext = EXT_TICKS[key]
            seeds_order = df["seed"].unique().tolist()
            seed_idx = seeds_order.index(seed) if seed in seeds_order else 0
            # extinction tick for this seed
            ext_tick = EXT_TICKS[key][seeds_order.index(seed)] if seed in seeds_order else np.nan
            records.append({"cond": key, "genome_care": gc, "ext_tick": ext_tick / 1000})

    rdf = pd.DataFrame(records).dropna()
    x = rdf["genome_care"].values
    y = rdf["ext_tick"].values

    slope, intercept, r, p, se = stats.linregress(x, y)
    n = len(x)
    t_crit = stats.t.ppf(0.975, df=n - 2)
    x_fit = np.linspace(x.min() - 0.005, x.max() + 0.005, 200)
    y_fit = intercept + slope * x_fit
    x_bar = x.mean()
    se_fit = se * np.sqrt(1/n + (x_fit - x_bar)**2 / np.sum((x - x_bar)**2))

    with plt.rc_context(STYLE):
        fig, ax = plt.subplots(figsize=(8, 5))

        for key in EXT_TICKS:
            sub = rdf[rdf["cond"] == key]
            ax.scatter(sub["genome_care"], sub["ext_tick"],
                       color=COND_COLORS[key], s=55, alpha=0.85,
                       edgecolors="white", linewidths=0.6,
                       label=COND_LABELS[key], zorder=4)

        ax.plot(x_fit, y_fit, color="#333333", linewidth=1.8, zorder=3)
        ax.fill_between(x_fit, y_fit - t_crit * se_fit, y_fit + t_crit * se_fit,
                        color="#888888", alpha=0.20, zorder=2)

        sign = "+" if slope >= 0 else "-"
        ax.text(0.97, 0.95,
                f"r = {r:.2f}   p = {p:.3f}\nslope = {slope:.1f}k / unit",
                ha="right", va="top", transform=ax.transAxes,
                fontsize=10, bbox=dict(facecolor="white", edgecolor="#cccccc", alpha=0.9))

        ax.set_xlabel("Genome care weight at t = 2000 (g_c)")
        ax.set_ylabel("Extinction tick (x10^3)")
        ax.legend(loc="upper left", fontsize=9)
        fig.suptitle("Early Genome Care vs. Lineage Survival Duration",
                     fontsize=13, fontweight="bold")
        fig.tight_layout()
    savefig(fig, "fig14_stat_regression.png")


# ─────────────────────────────────────────────────────────────────────────────
# FIGURE 15 ── Spearman correlation heatmap across outcome variables
# ─────────────────────────────────────────────────────────────────────────────
def fig_stat_correlation():
    records = []

    for key, folder in COND_DIRS:
        df = pd.read_csv(BASE / f"outputs/phase5_evolution/{folder}/snapshots.csv")
        seeds_order = df["seed"].unique().tolist()
        ext_ticks   = EXT_TICKS[key]

        for i, seed in enumerate(seeds_order):
            if i >= len(ext_ticks):
                continue
            sdf = df[(df["seed"] == seed) & (df["n_mothers"] > 0)]
            if sdf.empty:
                continue
            snap_2000 = df[(df["seed"] == seed) & (df["tick"] == 2000)]
            gc_2000   = snap_2000["mean_genome_care"].values[0] if len(snap_2000) else np.nan

            records.append({
                "extinction_tick":       ext_ticks[i] / 1000,
                "genome_care_t2000":     gc_2000,
                "mean_child_survival":   sdf["child_survival_rate"].mean(),
                "genome_behav_distance": sdf["genome_behavior_distance"].mean(),
                "max_generation":        sdf["highest_generation"].max(),
            })

    rdf = pd.DataFrame(records).dropna()
    var_labels = [
        "Extinction\ntick",
        "Genome care\n(t=2000)",
        "Mean child\nsurvival",
        "Genome-behav\ndistance",
        "Max\ngeneration",
    ]
    cols = list(rdf.columns)

    n_vars = len(cols)
    rho_mat = np.zeros((n_vars, n_vars))
    p_mat   = np.ones((n_vars, n_vars))
    for i in range(n_vars):
        for j in range(n_vars):
            r, p = stats.spearmanr(rdf.iloc[:, i], rdf.iloc[:, j])
            rho_mat[i, j] = r
            p_mat[i, j]   = p

    def sig_stars(p):
        if p < 0.001: return "***"
        if p < 0.01:  return "**"
        if p < 0.05:  return "*"
        return "ns"

    # Show lower triangle only
    mask = np.tril(np.ones((n_vars, n_vars), dtype=bool), k=0)

    with plt.rc_context(STYLE):
        fig, ax = plt.subplots(figsize=(8, 7))

        rho_disp = np.ma.array(rho_mat, mask=~mask)
        im = ax.imshow(rho_disp, cmap="RdBu_r", vmin=-1, vmax=1, aspect="auto")
        fig.colorbar(im, ax=ax, shrink=0.80, label="Spearman rho")

        for i in range(n_vars):
            for j in range(i + 1):
                rho = rho_mat[i, j]
                p   = p_mat[i, j]
                txt_color = "white" if abs(rho) > 0.6 else "black"
                if i == j:
                    ax.text(j, i, var_labels[i], ha="center", va="center",
                            fontsize=9, fontweight="bold", color="black")
                else:
                    ax.text(j, i, f"{rho:+.2f}\n{sig_stars(p)}",
                            ha="center", va="center", fontsize=9.5, color=txt_color)

        ax.set_xticks(range(n_vars)); ax.set_yticks(range(n_vars))
        ax.set_xticklabels(var_labels, fontsize=9)
        ax.set_yticklabels(var_labels, fontsize=9)
        ax.spines[:].set_visible(False)

        fig.suptitle("Spearman Correlation Matrix — Phase 5 Outcome Variables",
                     fontsize=13, fontweight="bold", y=1.01)
        fig.tight_layout()
    savefig(fig, "fig15_stat_correlation.png")


# ─────────────────────────────────────────────────────────────────────────────
# RUN ALL
# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    fig_ph2_baseline()
    fig_ph2_ovat()
    fig_food_mechanism()
    fig_ph4_weight_sweep()
    fig_ph5_extinction()
    fig_ph5_population_4cond()
    fig_ph5_genome_care_4cond()
    fig_ph5_expressed_vs_genome()
    fig_ph5_child_survival_4cond()
    fig_birth_scatter_sensitivity()
    fig_ph5_plasticity_4cond()
    fig_ph5_generation_4cond()
    fig_stat_pairwise()
    fig_stat_regression()
    fig_stat_correlation()
    print("All 14 figures saved to outputs/report_figures/")
