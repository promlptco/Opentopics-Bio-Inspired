"""
experiments/phase3_survival_full/escalation_sweep.py

Phase 3 -- Auto-Calibration Pipeline: Resource Escalation + MVE Detection.

Step 1 -- Escalation Loop:
  Iterates init_food = [50, 55, 60, 65, 70] (defaults; configurable via CLI).
  For each food level, runs the full 48-combo Motivation Sweep
  (care_weight x forage_weight x self_weight) with N=15 seeds per combination.

Step 2 -- Canonical Intersection (MVE Detection):
  After each food-level sweep, checks whether any genome configuration achieves BOTH:
    - Mother Survival Rate >= 0.80
    - Child Survival Rate  >= 0.80
  Stops at the FIRST food level satisfying this condition.
  That level becomes the "Phase 3 Balanced Baseline" (Minimum Viable Environment).

  Tie-breaker (among passing configs at the MVE level):
    1. Lowest care_weight.
    2. If tied: highest mean_mother_energy.

  The winning configuration is logged as the "Canonical Genome".

Usage:
  python experiments/phase3_survival_full/escalation_sweep.py
  python experiments/phase3_survival_full/escalation_sweep.py --seeds 15
  python experiments/phase3_survival_full/escalation_sweep.py --food_start 50 --food_end 70 --food_step 5
  python experiments/phase3_survival_full/escalation_sweep.py --duration 1000 --seeds 15

Outputs (under outputs/phase3_survival_full/escalation_sweep/<timestamp>/):
  food_<X>/sweep_results.csv
  food_<X>/motivation_sweep_raw.csv
  food_<X>/motivation_sweep_summary.csv
  food_<X>/anova_results.csv
  food_<X>/motivation_sweep_heatmap.png
  food_<X>/survival_zone_heatmap.png
  food_<X>/top5_candidates.png
  escalation_summary.csv              <- pass/fail record per food level
  phase3_balanced_baseline.json       <- Canonical Genome + MVE food level
"""

import sys
import os
import csv
import json
import argparse
from datetime import datetime
from itertools import product

import numpy as np

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, PROJECT_ROOT)

from experiments.phase3_survival_full.motivation_sweep import (
    CARE_WEIGHTS,
    FORAGE_WEIGHTS,
    SELF_WEIGHTS,
    SURVIVAL_THRESHOLD,
    CARE_RATE_MIN,
    run_one,
    summarize_combo,
    compute_and_save_anova,
    plot_heatmap,
    plot_survival_zone,
    plot_top5_candidates,
    _save_raw_csv,
    _save_summary_csv,
    _save_sweep_results_csv,
)
from experiments.phase3_survival_full.config import INIT_MOTHERS, PHASE3_BASELINE


# ============================================================
# MVE canonical selection  (survival-only, no care_rate gate)
# ============================================================

def select_mve_canonical(summaries):
    """
    From summaries at one food level, return the canonical genome for the MVE.

    Passing criteria (per spec):
      mother_survival_rate_mean >= SURVIVAL_THRESHOLD (0.80)
      child_survival_rate_mean  >= SURVIVAL_THRESHOLD (0.80)

    Tie-breaker:
      1. Lowest care_weight.
      2. Highest mean_mother_energy_mean.

    Returns the chosen summary dict, or None if no combo passes.
    """
    candidates = [
        s for s in summaries
        if s["mother_survival_rate_mean"] >= SURVIVAL_THRESHOLD
        and s["child_survival_rate_mean"] >= SURVIVAL_THRESHOLD
    ]

    if not candidates:
        return None

    min_care = min(s["care_weight"] for s in candidates)
    tied = [s for s in candidates if abs(s["care_weight"] - min_care) < 1e-9]
    return max(tied, key=lambda s: s["mean_mother_energy_mean"])


# ============================================================
# Per-food-level sweep
# ============================================================

def run_food_level_sweep(init_food, seeds, duration, tau, noise):
    """
    Run all 48 combos at a given init_food level.

    Returns (raw_rows, summaries).
    """
    combos = list(product(CARE_WEIGHTS, FORAGE_WEIGHTS, SELF_WEIGHTS))
    raw_rows = []
    summaries = []

    for idx, (care, forage, self_w) in enumerate(combos, start=1):
        params = {
            **PHASE3_BASELINE,
            "care_weight": care,
            "forage_weight": forage,
            "self_weight": self_w,
            "init_food": init_food,
        }

        run_results = []
        for seed in seeds:
            result = run_one(params, seed, duration, tau=tau, noise=noise)
            run_results.append(result)

            mots = result.get("motivations", {})
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

        mve_pass = (
            summary["mother_survival_rate_mean"] >= SURVIVAL_THRESHOLD
            and summary["child_survival_rate_mean"] >= SURVIVAL_THRESHOLD
        )
        status = "MVE+" if mve_pass else "----"

        print(
            f"  [{idx:03d}/{len(combos)}]"
            f" food={init_food} care={care} forage={forage} self={self_w}"
            f" | mother={summary['mother_survival_rate_mean']:.2f}"
            f" child={summary['child_survival_rate_mean']:.2f}"
            f" energy={summary['mean_mother_energy_mean']:.3f}"
            f" care_rate={summary['care_rate_mean']:.3f}"
            f" | {status}"
        )

    return raw_rows, summaries


# ============================================================
# Save per-level outputs
# ============================================================

def save_food_level_outputs(init_food, raw_rows, summaries, canonical, level_dir):
    os.makedirs(level_dir, exist_ok=True)

    for s in summaries:
        s["selected"] = int(
            abs(s["care_weight"]   - canonical["care_weight"])   < 1e-9
            and abs(s["forage_weight"] - canonical["forage_weight"]) < 1e-9
            and abs(s["self_weight"]   - canonical["self_weight"])   < 1e-9
        )

    _save_sweep_results_csv(raw_rows,  os.path.join(level_dir, "sweep_results.csv"))
    _save_raw_csv(raw_rows,            os.path.join(level_dir, "motivation_sweep_raw.csv"))
    _save_summary_csv(summaries,       os.path.join(level_dir, "motivation_sweep_summary.csv"))
    compute_and_save_anova(raw_rows,   level_dir)

    plot_heatmap(summaries,        canonical, level_dir)
    plot_survival_zone(summaries,  canonical, level_dir)
    plot_top5_candidates(summaries, canonical, level_dir)


# ============================================================
# Escalation summary CSV
# ============================================================

_ESC_FIELDS = [
    "init_food",
    "n_combos_mve_pass",
    "best_mother_surv",
    "best_child_surv",
    "min_care_weight_passing",
    "mve_found",
]


def _append_escalation_row(row, path):
    write_header = not os.path.exists(path)
    with open(path, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=_ESC_FIELDS)
        if write_header:
            writer.writeheader()
        writer.writerow(row)


# ============================================================
# Main
# ============================================================

def main():
    parser = argparse.ArgumentParser(
        description="Phase 3 Auto-Calibration: Escalation Loop + MVE Detection."
    )
    parser.add_argument("--food_start", type=int, default=50,
                        help="First init_food value to try (default: 50).")
    parser.add_argument("--food_end",   type=int, default=95,
                        help="Last init_food value to try, inclusive (default: 95).")
    parser.add_argument("--food_step",  type=int, default=5,
                        help="Increment between food levels (default: 5).")
    parser.add_argument("--seeds",      type=int, default=15,
                        help="Seeds per combination (default: 15).")
    parser.add_argument("--duration",   type=int, default=1000,
                        help="Ticks per simulation run (default: 1000).")
    parser.add_argument("--tau",        type=float, default=0.1)
    parser.add_argument("--perceptual_noise", type=float, default=0.1)
    args = parser.parse_args()

    food_levels = list(range(args.food_start, args.food_end + 1, args.food_step))
    seeds = list(range(42, 42 + args.seeds))
    combos = list(product(CARE_WEIGHTS, FORAGE_WEIGHTS, SELF_WEIGHTS))

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir = os.path.join(
        PROJECT_ROOT, "outputs", "phase3_survival_full", "escalation_sweep", ts
    )
    os.makedirs(out_dir, exist_ok=True)

    esc_csv_path = os.path.join(out_dir, "escalation_summary.csv")

    print("=" * 72)
    print("Phase 3 -- Auto-Calibration: Resource Escalation + MVE Detection")
    print(f"Food levels  : {food_levels}")
    print(f"Seeds        : {args.seeds}  ({seeds[0]}-{seeds[-1]})")
    print(f"Combinations : {len(combos)}  (care x {CARE_WEIGHTS}  forage x {FORAGE_WEIGHTS}  self x {SELF_WEIGHTS})")
    print(f"Duration     : {args.duration} ticks")
    print(f"MVE criteria : mother_surv>={SURVIVAL_THRESHOLD}  AND  child_surv>={SURVIVAL_THRESHOLD}")
    print(f"Tie-breaker  : lowest care_weight -> highest mean_mother_energy")
    print(f"Output root  : {out_dir}")
    print("=" * 72)

    mve_food = None
    mve_canonical = None
    mve_summaries = None

    for food in food_levels:
        print(f"\n{'-' * 72}")
        print(f"ESCALATION STEP  init_food = {food}")
        total_runs = len(combos) * args.seeds
        print(f"Running {len(combos)} combos x {args.seeds} seeds = {total_runs} simulations ...")
        print(f"{'-' * 72}")

        raw_rows, summaries = run_food_level_sweep(
            init_food=food,
            seeds=seeds,
            duration=args.duration,
            tau=args.tau,
            noise=args.perceptual_noise,
        )

        # --- MVE check ---
        passing = [
            s for s in summaries
            if s["mother_survival_rate_mean"] >= SURVIVAL_THRESHOLD
            and s["child_survival_rate_mean"]  >= SURVIVAL_THRESHOLD
        ]
        n_pass = len(passing)
        best_m = max((s["mother_survival_rate_mean"] for s in summaries), default=0.0)
        best_c = max((s["child_survival_rate_mean"]  for s in summaries), default=0.0)
        min_care_pass = min((s["care_weight"] for s in passing), default=float("nan"))

        mve_found = n_pass > 0
        _append_escalation_row({
            "init_food":              food,
            "n_combos_mve_pass":      n_pass,
            "best_mother_surv":       round(best_m, 4),
            "best_child_surv":        round(best_c, 4),
            "min_care_weight_passing": round(min_care_pass, 4) if not np.isnan(min_care_pass) else "",
            "mve_found":              int(mve_found),
        }, esc_csv_path)

        print(f"\n  food={food}  combos passing MVE: {n_pass}/{len(combos)}"
              f"  best_mother={best_m:.3f}  best_child={best_c:.3f}")

        # Pick canonical (fallback needed for plotting even when MVE not found)
        canonical = select_mve_canonical(summaries)
        if canonical is None:
            # Fallback for plotting: best combined survival score
            canonical = max(
                summaries,
                key=lambda s: s["mother_survival_rate_mean"] + s["child_survival_rate_mean"],
            )
            canonical["selection_status"] = "fallback_no_mve"
        else:
            canonical["selection_status"] = "mve_pass"

        # Save per-level outputs
        level_dir = os.path.join(out_dir, f"food_{food}")
        save_food_level_outputs(food, raw_rows, summaries, canonical, level_dir)
        print(f"  Saved outputs -> {level_dir}")

        if mve_found:
            if mve_food is None:
                # Record only the FIRST food level that passes -- that is the MVE.
                mve_food = food
                mve_canonical = canonical
                mve_summaries = summaries
                print(f"\n  *** FIRST MVE at init_food={food} -- continuing to complete all levels ***")
            else:
                print(f"\n  MVE also passes at food={food} (MVE already found at {mve_food})")
        else:
            print(f"  No combo passed MVE criteria at food={food}.")

    # -------------------------------------------------------
    # Progression summary across all food levels
    # -------------------------------------------------------

    print("\n" + "=" * 72)
    print("ESCALATION PROGRESSION SUMMARY")
    print(f"{'food':>6}  {'pass/48':>7}  {'best_mother':>11}  {'best_child':>10}  {'MVE':>4}")
    print("-" * 72)
    with open(esc_csv_path, newline="") as _f:
        import csv as _csv
        for row in _csv.DictReader(_f):
            marker = " <-- MVE" if int(row["mve_found"]) and row["init_food"] == str(mve_food) else ""
            print(
                f"  {row['init_food']:>4}  {row['n_combos_mve_pass']:>7}"
                f"  {row['best_mother_surv']:>11}  {row['best_child_surv']:>10}"
                f"  {'YES' if int(row['mve_found']) else 'no ':>4}{marker}"
            )
    print("=" * 72)

    # -------------------------------------------------------
    # Final output
    # -------------------------------------------------------

    if mve_food is None:
        print("\n" + "=" * 72)
        print("WARNING: No food level produced an MVE-passing configuration.")
        print(f"Tried: {food_levels}.  Consider extending --food_end beyond {args.food_end}.")
        print(f"Escalation summary  -> {esc_csv_path}")
        print("=" * 72)
        return

    baseline_out = {
        "phase": "Phase 3 Balanced Baseline (MVE)",
        "init_food": mve_food,
        "n_seeds": args.seeds,
        "duration": args.duration,
        "mve_criteria": {
            "mother_survival_rate_threshold": SURVIVAL_THRESHOLD,
            "child_survival_rate_threshold":  SURVIVAL_THRESHOLD,
        },
        "selection_rule": (
            "First init_food level where at least one genome achieves "
            f"mother_surv>={SURVIVAL_THRESHOLD} AND child_surv>={SURVIVAL_THRESHOLD}. "
            "Tie-breaker: lowest care_weight -> highest mean_mother_energy."
        ),
        "canonical_genome": {
            "care_weight":   mve_canonical["care_weight"],
            "forage_weight": mve_canonical["forage_weight"],
            "self_weight":   mve_canonical["self_weight"],
        },
        "canonical_stats": {
            "mother_survival_rate_mean": mve_canonical["mother_survival_rate_mean"],
            "mother_survival_rate_sd":   mve_canonical["mother_survival_rate_sd"],
            "child_survival_rate_mean":  mve_canonical["child_survival_rate_mean"],
            "child_survival_rate_sd":    mve_canonical["child_survival_rate_sd"],
            "mean_mother_energy_mean":   mve_canonical["mean_mother_energy_mean"],
            "mean_mother_energy_sd":     mve_canonical["mean_mother_energy_sd"],
            "care_rate_mean":            mve_canonical["care_rate_mean"],
            "care_rate_sd":              mve_canonical["care_rate_sd"],
            "passes_threshold":          mve_canonical["passes_threshold"],
            "selection_status":          mve_canonical["selection_status"],
        },
    }

    baseline_path = os.path.join(out_dir, "phase3_balanced_baseline.json")
    with open(baseline_path, "w") as f:
        json.dump(baseline_out, f, indent=2)

    print("\n" + "=" * 72)
    print("ESCALATION COMPLETE")
    print(f"Phase 3 Balanced Baseline (MVE) = init_food {mve_food}")
    print(f"Canonical Genome:")
    print(f"  care_weight   = {mve_canonical['care_weight']}")
    print(f"  forage_weight = {mve_canonical['forage_weight']}")
    print(f"  self_weight   = {mve_canonical['self_weight']}")
    print(f"Saved baseline  -> {baseline_path}")
    print(f"Escalation log  -> {esc_csv_path}")
    print(f"All outputs     -> {out_dir}")
    print("=" * 72)


if __name__ == "__main__":
    main()
