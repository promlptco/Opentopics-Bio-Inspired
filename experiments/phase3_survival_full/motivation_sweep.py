"""
experiments/phase3_survival_full/motivation_sweep.py

Phase 3a -- Motivation Weight Sweep.

Grid-searches care x forage x self motivation weights to find the canonical
genome: lowest care_weight that produces reliable mother and child survival
with non-trivial caregiving.

Grid (48 combinations):
  care_weight  : 0.3  0.5  0.7  0.9
  forage_weight: 0.5  0.7  0.85 1.0
  self_weight  : 0.3  0.5  0.7

Selection rule:
  1. Keep combinations where mother survival >= SURVIVAL_THRESHOLD
     AND child survival >= SURVIVAL_THRESHOLD
     AND mean care selection rate > CARE_RATE_MIN.
  2. Among those, select the lowest care_weight.
  3. Tie-breaker: highest mean mother energy averaged across all seeds and ticks.

Usage:
  python experiments/phase3_survival_full/motivation_sweep.py
  python experiments/phase3_survival_full/motivation_sweep.py --seeds 30
  python experiments/phase3_survival_full/motivation_sweep.py --duration 1000 --seeds 15

Outputs:
  outputs/phase3_survival_full/motivation_sweep/<timestamp>/
    sweep_results.csv                 <- mandatory per-run results table
    motivation_sweep_raw.csv
    motivation_sweep_summary.csv
    motivation_sweep_canonical.json
    motivation_sweep_heatmap.png
    survival_zone_heatmap.png         <- joint survival by foragexcare (3 self_weight panels)
    top5_candidates.png               <- bar chart justifying canonical genome selection
    anova_results.csv                 <- one-way ANOVA p-values per metric across all combos
"""

import sys
import os
import csv
import json
import argparse
from datetime import datetime
from itertools import product

import numpy as np
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, PROJECT_ROOT)

from experiments.phase3_survival_full.run import MotherChildSurvivalSimulation, make_config
from experiments.phase3_survival_full.config import INIT_MOTHERS, PHASE3_BASELINE, TAIL_WINDOW
from utils.experiment import set_seed


# ============================================================
# Grid and selection thresholds
# ============================================================

CARE_WEIGHTS   = [0.3, 0.5, 0.7, 0.9]
FORAGE_WEIGHTS = [0.5, 0.7, 0.85, 1.0]
SELF_WEIGHTS   = [0.3, 0.5, 0.7]

SURVIVAL_THRESHOLD = 0.80
CARE_RATE_MIN      = 0.05


# ============================================================
# Simulation runner
# ============================================================

def run_one(params, seed, duration, tau=0.1, noise=0.1):
    set_seed(seed)
    cfg = make_config(params, duration)
    sim = MotherChildSurvivalSimulation(cfg, tau=tau, perceptual_noise=noise)
    return sim.run()


# ============================================================
# Per-combo summarize
# ============================================================

def _care_rate(result):
    m = result.get("motivations", {})
    total = sum(m.values())
    return m.get("CARE", 0) / total if total > 0 else 0.0


def summarize_combo(care, forage, self_w, run_results):
    arr_mothers    = np.asarray([r["final_mothers"]      for r in run_results], dtype=float)
    arr_children   = np.asarray([r["final_children"]     for r in run_results], dtype=float)
    arr_m_energy   = np.asarray([r["mean_mother_energy"] for r in run_results], dtype=float)
    arr_fm_energy  = np.asarray([r["final_mother_energy"] for r in run_results], dtype=float)
    arr_c_hunger   = np.asarray([r["mean_child_hunger"]  for r in run_results], dtype=float)
    arr_c_distress = np.asarray([r["mean_child_distress"] for r in run_results], dtype=float)
    arr_care_rate  = np.asarray([_care_rate(r)           for r in run_results], dtype=float)

    mother_surv = float(np.mean(arr_mothers) / INIT_MOTHERS)
    child_surv  = float(np.mean(arr_children) / INIT_MOTHERS)
    care_rate   = float(np.mean(arr_care_rate))

    passes = int(
        mother_surv >= SURVIVAL_THRESHOLD
        and child_surv  >= SURVIVAL_THRESHOLD
        and care_rate   >  CARE_RATE_MIN
    )

    return {
        "care_weight":   care,
        "forage_weight": forage,
        "self_weight":   self_w,
        "num_runs":      len(run_results),

        "mother_survival_rate_mean": mother_surv,
        "mother_survival_rate_sd":   float(np.std(arr_mothers / INIT_MOTHERS)),
        "child_survival_rate_mean":  child_surv,
        "child_survival_rate_sd":    float(np.std(arr_children / INIT_MOTHERS)),

        "mean_mother_energy_mean": float(np.mean(arr_m_energy)),
        "mean_mother_energy_sd":   float(np.std(arr_m_energy)),
        "final_mother_energy_mean": float(np.mean(arr_fm_energy)),
        "final_mother_energy_sd":   float(np.std(arr_fm_energy)),

        "mean_child_hunger_mean":   float(np.mean(arr_c_hunger)),
        "mean_child_hunger_sd":     float(np.std(arr_c_hunger)),
        "mean_child_distress_mean": float(np.mean(arr_c_distress)),
        "mean_child_distress_sd":   float(np.std(arr_c_distress)),

        "care_rate_mean": care_rate,
        "care_rate_sd":   float(np.std(arr_care_rate)),

        "passes_threshold": passes,
    }


# ============================================================
# Canonical selection
# ============================================================

def select_canonical(summaries):
    """
    Phase 3a canonical genome selection.

    Primary: lowest care_weight that satisfies all survival + care thresholds.
    Tie-breaker: highest mean_mother_energy_mean among tied care_weight candidates.
    Fallback when no combo passes: best score by child_survival - 0.5 * care_weight.
    """
    candidates = [s for s in summaries if s["passes_threshold"]]

    if not candidates:
        fallback = max(
            summaries,
            key=lambda s: s["child_survival_rate_mean"] - 0.5 * s["care_weight"],
        )
        fallback["selection_status"] = "fallback_no_threshold_pass"
        return fallback

    min_care = min(s["care_weight"] for s in candidates)
    tied = [s for s in candidates if abs(s["care_weight"] - min_care) < 1e-9]
    chosen = max(tied, key=lambda s: s["mean_mother_energy_mean"])
    chosen["selection_status"] = "threshold_pass"
    return chosen


# ============================================================
# CSV output
# ============================================================

_RAW_FIELDS = [
    "care_weight", "forage_weight", "self_weight", "seed",
    "final_mothers", "final_children",
    "mother_survival_rate", "child_survival_rate",
    "mean_mother_energy", "final_mother_energy",
    "mean_child_hunger", "mean_child_distress",
    "care_total", "forage_total", "self_total", "care_rate",
]

_SUMMARY_FIELDS = [
    "care_weight", "forage_weight", "self_weight", "num_runs",
    "mother_survival_rate_mean", "mother_survival_rate_sd",
    "child_survival_rate_mean",  "child_survival_rate_sd",
    "mean_mother_energy_mean",   "mean_mother_energy_sd",
    "final_mother_energy_mean",  "final_mother_energy_sd",
    "mean_child_hunger_mean",    "mean_child_hunger_sd",
    "mean_child_distress_mean",  "mean_child_distress_sd",
    "care_rate_mean",            "care_rate_sd",
    "passes_threshold",          "selected",
]


def _save_raw_csv(rows, path):
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=_RAW_FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def _save_summary_csv(summaries, path):
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=_SUMMARY_FIELDS)
        writer.writeheader()
        for s in summaries:
            writer.writerow({k: s.get(k, "") for k in _SUMMARY_FIELDS})


# ============================================================
# sweep_results.csv  -- mandatory per-run table (6 columns)
# ============================================================

_SWEEP_RESULTS_FIELDS = [
    "care_weight", "forage_weight", "self_weight",
    "mother_survival_rate", "child_survival_rate", "mean_mother_energy",
]


def _save_sweep_results_csv(raw_rows, path):
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=_SWEEP_RESULTS_FIELDS)
        writer.writeheader()
        for row in raw_rows:
            writer.writerow({k: row[k] for k in _SWEEP_RESULTS_FIELDS})


# ============================================================
# Heatmap plot
# ============================================================

def _nearest_idx(vals, target):
    return min(range(len(vals)), key=lambda i: abs(vals[i] - target))


def _build_matrix(summaries, value_key, care_vals, forage_vals, self_w):
    """4x4 matrix indexed [forage_idx, care_idx] for a single self_weight slice."""
    mat = np.full((len(forage_vals), len(care_vals)), np.nan)
    for s in summaries:
        if abs(s["self_weight"] - self_w) > 1e-9:
            continue
        ci = _nearest_idx(care_vals,   s["care_weight"])
        fi = _nearest_idx(forage_vals, s["forage_weight"])
        mat[fi, ci] = s[value_key]
    return mat


def plot_heatmap(summaries, canonical, out_dir):
    col_specs = [
        ("child_survival_rate_mean", "Child Survival Rate", "YlOrRd",  0.0, 1.0),
        ("mean_mother_energy_mean",  "Mean Mother Energy",  "YlGnBu",  0.3, 0.9),
    ]

    n_rows = len(SELF_WEIGHTS)
    n_cols = len(col_specs)

    fig, axes = plt.subplots(n_rows, n_cols, figsize=(11, 4 * n_rows), squeeze=False)

    can_c = canonical["care_weight"]
    can_f = canonical["forage_weight"]
    can_s = canonical["self_weight"]

    for ri, self_w in enumerate(SELF_WEIGHTS):
        for ci_col, (vkey, title, cmap, vmin, vmax) in enumerate(col_specs):
            ax = axes[ri][ci_col]
            mat = _build_matrix(summaries, vkey, CARE_WEIGHTS, FORAGE_WEIGHTS, self_w)

            im = ax.imshow(
                mat,
                aspect="auto",
                origin="lower",
                cmap=cmap,
                vmin=vmin,
                vmax=vmax,
                interpolation="nearest",
            )
            fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)

            ax.set_xticks(range(len(CARE_WEIGHTS)))
            ax.set_xticklabels([str(c) for c in CARE_WEIGHTS], fontsize=8)
            ax.set_yticks(range(len(FORAGE_WEIGHTS)))
            ax.set_yticklabels([str(f) for f in FORAGE_WEIGHTS], fontsize=8)
            ax.set_xlabel("care_weight", fontsize=8)
            ax.set_ylabel("forage_weight", fontsize=8)
            ax.set_title(f"{title}  |  self_weight={self_w}", fontsize=10, fontweight="bold")

            midpoint = (vmin + vmax) / 2
            for fi_ann in range(len(FORAGE_WEIGHTS)):
                for ci_ann in range(len(CARE_WEIGHTS)):
                    v = mat[fi_ann, ci_ann]
                    if not np.isnan(v):
                        txt_color = "white" if v > midpoint else "black"
                        ax.text(
                            ci_ann, fi_ann, f"{v:.2f}",
                            ha="center", va="center",
                            fontsize=7, color=txt_color,
                            bbox=dict(facecolor="none", edgecolor="none", pad=0),
                        )

            # Mark canonical genome on the self_weight slice that matches
            if abs(can_s - self_w) < 1e-9:
                cx = _nearest_idx(CARE_WEIGHTS,   can_c)
                fy = _nearest_idx(FORAGE_WEIGHTS, can_f)
                ax.add_patch(mpatches.Rectangle(
                    (cx - 0.48, fy - 0.48), 0.96, 0.96,
                    fill=False, edgecolor="#00FF00", linewidth=2.5,
                ))
                ax.text(
                    cx, fy + 0.38, "*",
                    ha="center", va="center",
                    fontsize=11, color="#00FF00", fontweight="bold",
                )

    fig.suptitle(
        "Phase 3a -- Motivation Weight Sweep\n"
        f"carex{CARE_WEIGHTS}  foragex{FORAGE_WEIGHTS}  selfx{SELF_WEIGHTS}\n"
        f"Canonical *  care={can_c}  forage={can_f}  self={can_s}"
        f"  [{canonical.get('selection_status', '')}]",
        fontsize=12,
        fontweight="bold",
        y=1.01,
    )

    plt.tight_layout()
    out_path = os.path.join(out_dir, "motivation_sweep_heatmap.png")
    fig.savefig(out_path, dpi=200, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved heatmap -> {out_path}")


# ============================================================
# Survival Zone heatmap  (X=forage, Y=care, colour=joint survival)
# ============================================================

def _build_survival_matrix(summaries, care_vals, forage_vals, self_w):
    """Matrix[care_idx, forage_idx] = min(mother_surv, child_surv) for one self_weight slice."""
    mat = np.full((len(care_vals), len(forage_vals)), np.nan)
    for s in summaries:
        if abs(s["self_weight"] - self_w) > 1e-9:
            continue
        ci = _nearest_idx(care_vals,   s["care_weight"])
        fi = _nearest_idx(forage_vals, s["forage_weight"])
        mat[ci, fi] = min(
            s["mother_survival_rate_mean"],
            s["child_survival_rate_mean"],
        )
    return mat


def plot_survival_zone(summaries, canonical, out_dir):
    n_cols = len(SELF_WEIGHTS)
    fig, axes = plt.subplots(1, n_cols, figsize=(5 * n_cols, 5), squeeze=False)

    can_c = canonical["care_weight"]
    can_f = canonical["forage_weight"]
    can_s = canonical["self_weight"]

    for col_idx, self_w in enumerate(SELF_WEIGHTS):
        ax  = axes[0][col_idx]
        mat = _build_survival_matrix(summaries, CARE_WEIGHTS, FORAGE_WEIGHTS, self_w)

        im = ax.imshow(
            mat,
            aspect="auto",
            origin="lower",
            cmap="RdYlGn",
            vmin=0.0,
            vmax=1.0,
            interpolation="nearest",
        )
        fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04, label="Joint Survival Rate")

        ax.set_xticks(range(len(FORAGE_WEIGHTS)))
        ax.set_xticklabels([str(f) for f in FORAGE_WEIGHTS], fontsize=8)
        ax.set_yticks(range(len(CARE_WEIGHTS)))
        ax.set_yticklabels([str(c) for c in CARE_WEIGHTS], fontsize=8)
        ax.set_xlabel("forage_weight", fontsize=9)
        ax.set_ylabel("care_weight",   fontsize=9)
        ax.set_title(f"self_weight = {self_w}", fontsize=11, fontweight="bold")

        # Cell annotations
        for ci_ann in range(len(CARE_WEIGHTS)):
            for fi_ann in range(len(FORAGE_WEIGHTS)):
                v = mat[ci_ann, fi_ann]
                if not np.isnan(v):
                    txt_color = "white" if v < 0.5 else "black"
                    ax.text(
                        fi_ann, ci_ann, f"{v:.2f}",
                        ha="center", va="center",
                        fontsize=7.5, color=txt_color,
                    )

        # Dashed border on all threshold-passing cells
        for s in summaries:
            if abs(s["self_weight"] - self_w) > 1e-9:
                continue
            if s["passes_threshold"]:
                ci_ann = _nearest_idx(CARE_WEIGHTS,   s["care_weight"])
                fi_ann = _nearest_idx(FORAGE_WEIGHTS, s["forage_weight"])
                ax.add_patch(mpatches.Rectangle(
                    (fi_ann - 0.48, ci_ann - 0.48), 0.96, 0.96,
                    fill=False, edgecolor="#1A6E1A", linewidth=1.5, linestyle="--",
                ))

        # Solid orange border + star on canonical cell
        if abs(can_s - self_w) < 1e-9:
            cy = _nearest_idx(CARE_WEIGHTS,   can_c)
            fx = _nearest_idx(FORAGE_WEIGHTS, can_f)
            ax.add_patch(mpatches.Rectangle(
                (fx - 0.48, cy - 0.48), 0.96, 0.96,
                fill=False, edgecolor="#FF6600", linewidth=2.5,
            ))
            ax.text(
                fx, cy + 0.35, "*",
                ha="center", va="center",
                fontsize=12, color="#FF6600", fontweight="bold",
            )

    fig.suptitle(
        "Phase 3a -- Survival Zone  |  colour = min(mother_surv, child_surv)\n"
        f"Dashed border: passes all thresholds "
        f"(surv>={SURVIVAL_THRESHOLD}, care_rate>{CARE_RATE_MIN})   "
        f"* canonical: care={can_c}  forage={can_f}  self={can_s}",
        fontsize=11,
        fontweight="bold",
        y=1.04,
    )

    plt.tight_layout()
    out_path = os.path.join(out_dir, "survival_zone_heatmap.png")
    fig.savefig(out_path, dpi=200, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved survival zone  -> {out_path}")


# ============================================================
# Top-5 Candidates bar chart
# ============================================================

def plot_top5_candidates(summaries, canonical, out_dir):
    candidates = [s for s in summaries if s["passes_threshold"]]
    candidates.sort(key=lambda s: s["mean_mother_energy_mean"], reverse=True)
    top5 = candidates[:5]

    if not top5:
        ranked = sorted(
            summaries,
            key=lambda s: s["child_survival_rate_mean"] - 0.5 * s["care_weight"],
            reverse=True,
        )
        top5 = ranked[:5]

    can_key = (canonical["care_weight"], canonical["forage_weight"], canonical["self_weight"])

    labels     = [f"c={s['care_weight']}\nf={s['forage_weight']}\ns={s['self_weight']}" for s in top5]
    energies   = [s["mean_mother_energy_mean"] for s in top5]
    energy_sds = [s["mean_mother_energy_sd"]   for s in top5]
    colors     = [
        "#D08770" if (s["care_weight"], s["forage_weight"], s["self_weight"]) == can_key
        else "#5E81AC"
        for s in top5
    ]

    fig, ax = plt.subplots(figsize=(max(7, len(top5) * 1.9), 5), facecolor="#FFFFFF")
    ax.set_facecolor("#FAFAFA")

    bars = ax.bar(
        range(len(top5)),
        energies,
        yerr=energy_sds,
        capsize=5,
        color=colors,
        edgecolor="white",
        linewidth=0.8,
        error_kw={"elinewidth": 1.5, "ecolor": "#333333"},
    )

    for i, (bar, val, sd) in enumerate(zip(bars, energies, energy_sds)):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            val + sd + 0.005,
            f"{val:.3f}",
            ha="center", va="bottom",
            fontsize=8.5, color="#1A1A1A",
        )
        if colors[i] == "#D08770":
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                val * 0.5,
                "* canonical",
                ha="center", va="center",
                fontsize=7.5, color="white", fontweight="bold",
            )

    ax.set_xticks(range(len(top5)))
    ax.set_xticklabels(labels, fontsize=8.5)
    ax.set_ylabel("Mean Mother Energy", fontsize=10)
    ax.set_xlabel("Configuration  (care / forage / self weights)", fontsize=9)
    ax.set_title(
        "Phase 3a -- Top Candidates by Mean Mother Energy\n"
        f"(all pass: surv>={SURVIVAL_THRESHOLD:.0%}, care_rate>{CARE_RATE_MIN:.0%}; "
        f"ranked by mean_mother_energy; canonical = lowest care_weight -> highest energy)",
        fontsize=10,
        fontweight="bold",
    )

    ax.set_ylim(0, max(energies) * 1.30)
    ax.yaxis.grid(True, color="#E0E0E0", linewidth=0.7, linestyle="--")
    ax.set_axisbelow(True)
    for spine in ax.spines.values():
        spine.set_edgecolor("#CCCCCC")

    ax.legend(
        handles=[
            mpatches.Patch(facecolor="#D08770", label="Canonical (selected)"),
            mpatches.Patch(facecolor="#5E81AC", label="Other candidates"),
        ],
        loc="upper right",
        fontsize=8.5,
        facecolor="#FFFFFF",
        edgecolor="#CCCCCC",
    )

    plt.tight_layout()
    out_path = os.path.join(out_dir, "top5_candidates.png")
    fig.savefig(out_path, dpi=200, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved top-5 chart    -> {out_path}")


# ============================================================
# ANOVA -- one-way across all combos, per metric, per seed
# ============================================================

_ANOVA_METRICS = [
    "mother_survival_rate",
    "child_survival_rate",
    "mean_mother_energy",
    "care_rate",
]

_ANOVA_FIELDS = [
    "metric", "f_statistic", "p_value",
    "n_groups", "n_per_group", "significant_p05",
]


def compute_and_save_anova(raw_rows, out_dir):
    """
    One-way ANOVA across all (care, forage, self) combinations.

    For each metric the observations are the per-seed values within each combo.
    Tests whether motivation-weight combination has a statistically significant
    effect on that metric (F-test across 48 groups).

    Requires scipy -- already a project dependency (used in phase1 tests).
    """
    from scipy import stats as scipy_stats

    # Group per-seed values by combo key
    groups: dict[tuple, dict[str, list]] = {}
    for row in raw_rows:
        key = (row["care_weight"], row["forage_weight"], row["self_weight"])
        if key not in groups:
            groups[key] = {m: [] for m in _ANOVA_METRICS}
        for m in _ANOVA_METRICS:
            groups[key][m].append(float(row[m]))

    print("\nANOVA (one-way, across all combos):")
    results = []
    for metric in _ANOVA_METRICS:
        metric_groups = [groups[k][metric] for k in groups]
        f_stat, p_val = scipy_stats.f_oneway(*metric_groups)
        sig = int(p_val < 0.05)
        results.append({
            "metric":          metric,
            "f_statistic":     round(float(f_stat), 4),
            "p_value":         round(float(p_val),  6),
            "n_groups":        len(metric_groups),
            "n_per_group":     len(metric_groups[0]),
            "significant_p05": sig,
        })
        flag = "  *significant*" if sig else ""
        print(
            f"  {metric:<25s}  F={f_stat:8.3f}  p={p_val:.6f}{flag}"
        )

    anova_path = os.path.join(out_dir, "anova_results.csv")
    with open(anova_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=_ANOVA_FIELDS)
        writer.writeheader()
        writer.writerows(results)
    print(f"Saved ANOVA results  -> {anova_path}")
    return results


# ============================================================
# Main
# ============================================================

def main():
    parser = argparse.ArgumentParser(
        description="Phase 3a: Motivation Weight Sweep -- find canonical genome."
    )
    parser.add_argument("--duration", type=int, default=1000)
    parser.add_argument("--seeds",    type=int, default=15,
                        help="Seeds per combination (15-30 per EXPERIMENT_DESIGN).")
    parser.add_argument("--tau",      type=float, default=0.1)
    parser.add_argument("--perceptual_noise", type=float, default=0.1)
    args = parser.parse_args()

    seeds  = list(range(42, 42 + args.seeds))
    combos = list(product(CARE_WEIGHTS, FORAGE_WEIGHTS, SELF_WEIGHTS))

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir = os.path.join(
        PROJECT_ROOT, "outputs", "phase3_survival_full", "motivation_sweep", ts
    )
    os.makedirs(out_dir, exist_ok=True)

    print("=" * 70)
    print("Phase 3a * Motivation Weight Sweep")
    print(f"Duration     : {args.duration} ticks")
    print(f"Seeds        : {args.seeds}  ({seeds[0]}-{seeds[-1]})")
    print(f"Combinations : {len(combos)}")
    print(f"Total runs   : {len(combos) * args.seeds}")
    print(f"Tau          : {args.tau}")
    print(f"Noise        : {args.perceptual_noise}")
    print(f"Thresholds   : survival>={SURVIVAL_THRESHOLD}  care_rate>{CARE_RATE_MIN}")
    print(f"Output       : {out_dir}")
    print("=" * 70)

    raw_rows  = []
    summaries = []

    for idx, (care, forage, self_w) in enumerate(combos, start=1):
        params = {
            **PHASE3_BASELINE,
            "care_weight":   care,
            "forage_weight": forage,
            "self_weight":   self_w,
        }

        run_results = []
        for seed in seeds:
            result = run_one(
                params, seed, args.duration,
                tau=args.tau, noise=args.perceptual_noise,
            )
            run_results.append(result)

            mots  = result.get("motivations", {})
            total = sum(mots.values())
            care_rate_run = mots.get("CARE", 0) / total if total > 0 else 0.0

            raw_rows.append({
                "care_weight":          care,
                "forage_weight":        forage,
                "self_weight":          self_w,
                "seed":                 seed,
                "final_mothers":        result["final_mothers"],
                "final_children":       result["final_children"],
                "mother_survival_rate": result["final_mothers"] / INIT_MOTHERS,
                "child_survival_rate":  result["final_children"] / INIT_MOTHERS,
                "mean_mother_energy":   result["mean_mother_energy"],
                "final_mother_energy":  result["final_mother_energy"],
                "mean_child_hunger":    result["mean_child_hunger"],
                "mean_child_distress":  result["mean_child_distress"],
                "care_total":           mots.get("CARE",   0),
                "forage_total":         mots.get("FORAGE", 0),
                "self_total":           mots.get("SELF",   0),
                "care_rate":            care_rate_run,
            })

        summary = summarize_combo(care, forage, self_w, run_results)
        summaries.append(summary)

        status = "PASS" if summary["passes_threshold"] else "----"
        print(
            f"[{idx:03d}/{len(combos)}]"
            f" care={care} forage={forage} self={self_w}"
            f" | mother={summary['mother_survival_rate_mean']:.2f}+-{summary['mother_survival_rate_sd']:.2f}"
            f" child={summary['child_survival_rate_mean']:.2f}+-{summary['child_survival_rate_sd']:.2f}"
            f" energy={summary['mean_mother_energy_mean']:.3f}"
            f" care_rate={summary['care_rate_mean']:.3f}+-{summary['care_rate_sd']:.3f}"
            f" | {status}"
        )

    canonical = select_canonical(summaries)

    for s in summaries:
        s["selected"] = int(
            abs(s["care_weight"]   - canonical["care_weight"])   < 1e-9
            and abs(s["forage_weight"] - canonical["forage_weight"]) < 1e-9
            and abs(s["self_weight"]   - canonical["self_weight"])   < 1e-9
        )

    _save_sweep_results_csv(raw_rows, os.path.join(out_dir, "sweep_results.csv"))
    _save_raw_csv(raw_rows,  os.path.join(out_dir, "motivation_sweep_raw.csv"))
    _save_summary_csv(summaries, os.path.join(out_dir, "motivation_sweep_summary.csv"))
    print(f"\nSaved sweep_results -> {os.path.join(out_dir, 'sweep_results.csv')}")
    print(f"Saved raw CSV       -> {os.path.join(out_dir, 'motivation_sweep_raw.csv')}")
    print(f"Saved summary CSV   -> {os.path.join(out_dir, 'motivation_sweep_summary.csv')}")

    canonical_out = {
        **canonical,
        "selection_rule": (
            f"Lowest care_weight with mother_surv>={SURVIVAL_THRESHOLD} "
            f"AND child_surv>={SURVIVAL_THRESHOLD} "
            f"AND care_rate>{CARE_RATE_MIN}; "
            f"tie-break: highest mean_mother_energy."
        ),
    }
    compute_and_save_anova(raw_rows, out_dir)

    json_path = os.path.join(out_dir, "motivation_sweep_canonical.json")
    with open(json_path, "w") as f:
        json.dump(canonical_out, f, indent=2)
    print(f"Saved canonical   -> {json_path}")

    plot_heatmap(summaries, canonical, out_dir)
    plot_survival_zone(summaries, canonical, out_dir)
    plot_top5_candidates(summaries, canonical, out_dir)

    pass_count = sum(1 for s in summaries if s["passes_threshold"])
    print("\n" + "=" * 70)
    print(f"Combinations passing threshold: {pass_count}/{len(combos)}")
    print("Canonical genome selected:")
    print(f"  care_weight   = {canonical['care_weight']}")
    print(f"  forage_weight = {canonical['forage_weight']}")
    print(f"  self_weight   = {canonical['self_weight']}")
    print(f"  status        = {canonical.get('selection_status', '')}")
    print(f"  mother_surv   = {canonical['mother_survival_rate_mean']:.3f} "
          f"+- {canonical['mother_survival_rate_sd']:.3f}")
    print(f"  child_surv    = {canonical['child_survival_rate_mean']:.3f} "
          f"+- {canonical['child_survival_rate_sd']:.3f}")
    print(f"  mean_energy   = {canonical['mean_mother_energy_mean']:.3f} "
          f"+- {canonical['mean_mother_energy_sd']:.3f}")
    print(f"  care_rate     = {canonical['care_rate_mean']:.3f} "
          f"+- {canonical['care_rate_sd']:.3f}")
    print(f"\nOutputs: {out_dir}")
    print("=" * 70)


if __name__ == "__main__":
    main()
