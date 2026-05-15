"""Phase 3 Food Shannon Diagnostic — detailed plots (auto_400_percept8 style) per Shannon alpha.

Runs the same 4 conditions as phase3_food_comparison/run.py (children + unbiased weights),
but uses Phase3Simulation's Phase2-compatible result dicts so new_plot.py diagnostics work.

Key difference from Phase 2: motivation_history contains FORAGE/SELF/CARE, so the
motivation-selection plot shows the care trap dynamics across conditions.

Output structure:
  outputs/phase3_food_shannon_diagnostic/exp_<ts>/
    F0/  F1/  F2/  F3/
      validation_<label>.png
      motivation_selection_<label>.png   ← shows FORAGE/SELF/CARE split
      action_selection_<label>.png       ← same data, labelled as action
      food_consumption_rate_<label>.png
      spatial_heatmap_population_<label>.png
      homeostatic_balance_<label>.png
      rate_sum_check_<label>.png
      stacked_action_failed_<label>.png

Usage:
  python -m experiments.phase3_food_comparison.diagnostic_run
  python -m experiments.phase3_food_comparison.diagnostic_run --seeds 5 --ticks 2000 --workers 4
"""
from __future__ import annotations

import argparse
import json
import sys
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from config import Config

ALPHA_LEVELS: list[tuple[float, str, str]] = [
    (0.00, "F0", "Uniform 1:1 (alpha=0)"),
    (0.01, "F1", "Shannon alpha=0.01"),
    (0.05, "F2", "Shannon alpha=0.05"),
    (0.10, "F3", "Shannon alpha=0.10"),
]

_ECOLOGY_PATH = (
    PROJECT_ROOT
    / "outputs/phase4_weight_sweep/phase4b_20260510_111325/selected_ecology.json"
)
_FALLBACK: dict = {
    "init_food": 300,
    "eat_gain": 0.70,
    "move_cost": 0.005,
    "rest_recovery": 0.005,
    "perception_radius": 8,
    "food_perception_radius": 8,
    "infant_starvation_multiplier": 1.0,
}


def load_ecology() -> dict:
    if _ECOLOGY_PATH.exists():
        try:
            data = json.loads(_ECOLOGY_PATH.read_text())
            return data.get("BEST_CALIBRATED", data)
        except Exception as exc:
            print("Warning: %s" % exc)
    return _FALLBACK.copy()


def make_config(alpha: float, eco: dict, max_ticks: int) -> Config:
    cfg = Config()
    cfg.width = 50
    cfg.height = 50
    cfg.init_mothers = 15
    cfg.initial_energy = 1.0
    cfg.max_ticks = max_ticks
    cfg.init_food = int(eco.get("init_food", 300))
    cfg.eat_gain = eco.get("eat_gain", 0.70)
    cfg.move_cost = eco.get("move_cost", 0.005)
    cfg.rest_recovery = eco.get("rest_recovery", 0.005)
    cfg.perception_radius = int(eco.get("perception_radius", 8))
    cfg.food_perception_radius = int(eco.get("food_perception_radius", 8))
    cfg.hunger_rate = 1.0 / 35.0
    cfg.fatigue_rate = 0.01
    cfg.feed_cost = 0.01
    cfg.food_entropy_alpha = alpha
    cfg.food_entropy_beta = 0.01
    cfg.food_entropy_gamma = 0.01
    cfg.food_patch_prior = cfg.init_food / (cfg.width * cfg.height)
    cfg.care_weight = 1.0
    cfg.forage_weight = 1.0
    cfg.self_weight = 1.0
    cfg.children_enabled = True
    cfg.care_enabled = True
    cfg.reproduction_enabled = False
    cfg.mutation_enabled = False
    cfg.plasticity_enabled = False
    cfg.allow_allomothering = False
    cfg.infant_starvation_multiplier = float(eco.get("infant_starvation_multiplier", 1.0))
    cfg.maturity_age = 80
    cfg.starvation_threshold = 1.0
    cfg.mother_max_age = 400
    cfg.reproduction_threshold = 0.85
    cfg.reproduction_cost = 0.20
    cfg.reproduction_cooldown = 120
    cfg.plastic_gain = 0.1
    cfg.plasticity_metabolic_alpha = 0.01
    cfg.plasticity_maintenance_beta = 0.001
    cfg.plasticity_kin_conditional = True
    cfg.init_learning_rate = 1.0
    cfg.init_plasticity_coefficient = 1.0
    cfg.phenotype_retention = 0.15
    cfg.softmax_tau = 0.1
    cfg.cry_decay_radius = 0.0
    cfg.temperature_sensitivity = 0.0
    cfg.warmth_factor = 0.0
    cfg.warmth_radius = 3
    cfg.temperature_period = 200
    cfg.birth_scatter_radius = 2
    cfg.mutation_rate = 0.5
    cfg.mutation_sigma = 0.02
    cfg.min_mutation_rate = 0.01
    cfg.max_population = 140
    return cfg


def _worker_fixed(args: tuple) -> dict:
    alpha, seed, max_ticks, eco = args
    import sys as _sys
    from pathlib import Path as _Path
    _sys.path.insert(0, str(_Path(__file__).resolve().parents[2]))

    import random as _random
    import numpy as _np
    _random.seed(seed)
    _np.random.seed(seed)

    from experiments.phase3_food_comparison.diagnostic_run import make_config
    from experiments.phase3_survival_full.run import Phase3Simulation

    cfg = make_config(alpha, eco, max_ticks)
    cfg.seed = seed  # Simulation.__init__ re-seeds from cfg.seed — must set per worker
    sim = Phase3Simulation(cfg)
    result = sim.run()
    result["base_seed"] = seed
    result["repeat"] = seed
    result["run_seed"] = seed
    return result


def _generate_plots(label: str, results: list[dict], eco: dict,
                    max_ticks: int, out: Path) -> None:
    from experiments.phase2_survival_minimal.new_plot import (
        plot_multiseed_condition,
        plot_event_selection_over_time,
        plot_stacked_action_failed_over_time,
        plot_rate_sum_check,
        plot_food_consumption_over_time,
        plot_spatial_heatmap_population,
        plot_homeostatic_balance,
    )

    params = {
        "perception_radius": eco.get("perception_radius", 8),
        "hunger_rate": 1.0 / 35.0,
        "move_cost": eco.get("move_cost", 0.005),
        "eat_gain": eco.get("eat_gain", 0.70),
        "init_food": eco.get("init_food", 300),
        "rest_recovery": eco.get("rest_recovery", 0.005),
        "forage_weight": 1.0,
        "self_weight": 1.0,
        "care_weight": 1.0,
    }
    run_labels = ["seed%d" % r["base_seed"] for r in results]
    out_str = str(out)

    plot_multiseed_condition(label, results, params, run_labels, max_ticks, out_str)

    # Motivation selection: show FORAGE/SELF/CARE (Phase 3 has all 3 domains)
    plot_event_selection_over_time(
        name=label,
        results=results,
        duration=max_ticks,
        out_dir=out_str,
        history_key="motivation_history",
        event_keys=["FORAGE", "SELF", "CARE"],
        filename_prefix="motivation_selection",
        title_prefix="Motivation Selection (FORAGE/SELF/CARE)",
    )

    # Action selection: same data (action_history == motivation_history in Phase3Simulation)
    plot_event_selection_over_time(
        name=label,
        results=results,
        duration=max_ticks,
        out_dir=out_str,
        history_key="action_history",
        event_keys=["FORAGE", "SELF", "CARE"],
        filename_prefix="action_selection",
        title_prefix="Action Selection (Phase 3 motivation proxy)",
    )

    plot_stacked_action_failed_over_time(label, results, max_ticks, out_str)
    plot_rate_sum_check(label, results, max_ticks, out_str)
    plot_food_consumption_over_time(label, results, max_ticks, out_str)
    plot_spatial_heatmap_population(label, results, out_str)
    plot_homeostatic_balance(label, results, max_ticks, out_str)


def run(seeds: int = 5, max_ticks: int = 2000, workers: int = 1,
        output_dir: Path | None = None) -> Path:
    eco = load_ecology()
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out = output_dir or (PROJECT_ROOT / "outputs" / "phase3_food_shannon_diagnostic" / f"exp_{ts}")
    out.mkdir(parents=True, exist_ok=True)

    print("[phase3_food_shannon_diagnostic]")
    print("  ecology: init_food=%d  eat_gain=%.2f  ISM=%.1f" % (
        eco.get("init_food", 300), eco.get("eat_gain", 0.7),
        eco.get("infant_starvation_multiplier", 1.0)))
    print("  weights: care=1.0  forage=1.0  self=1.0 (unbiased)")
    print("  seeds=%d  ticks=%d  workers=%d" % (seeds, max_ticks, workers))
    print("  output: %s" % out)

    seed_list = list(range(42, 42 + seeds))

    for alpha, label, desc in ALPHA_LEVELS:
        print("\n  [%s] %s" % (label, desc))
        jobs = [(alpha, s, max_ticks, eco) for s in seed_list]
        results: list[dict] = []

        if workers <= 1:
            for job in jobs:
                r = _worker_fixed(job)
                results.append(r)
                print("    seed=%d  final_pop=%d  cmr=%.3f  care_pct=%.3f" % (
                    r["base_seed"], r["final_pop"],
                    r.get("child_maturation_rate", 0.0),
                    r.get("care_pct", 0.0)))
        else:
            with ProcessPoolExecutor(max_workers=workers) as pool:
                futures = {pool.submit(_worker_fixed, job): job for job in jobs}
                for future in as_completed(futures):
                    try:
                        r = future.result()
                        results.append(r)
                        print("    seed=%d  final_pop=%d  cmr=%.3f  care_pct=%.3f" % (
                            r["base_seed"], r["final_pop"],
                            r.get("child_maturation_rate", 0.0),
                            r.get("care_pct", 0.0)))
                    except Exception as exc:
                        job = futures[future]
                        print("    [FAIL] seed=%d: %s" % (job[1], exc))

        if not results:
            print("    WARNING: no results for %s" % label)
            continue

        cond_out = out / label
        cond_out.mkdir(parents=True, exist_ok=True)
        _generate_plots(label, results, eco, max_ticks, cond_out)
        print("    Plots saved -> %s" % cond_out)

    print("\n[ok] Phase 3 Shannon diagnostic complete — %s" % out)
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description="Phase 3 Food Shannon Diagnostic")
    parser.add_argument("--seeds", type=int, default=5)
    parser.add_argument("--ticks", type=int, default=2000)
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument("--output-dir", type=str, default=None)
    args = parser.parse_args()

    run(
        seeds=args.seeds,
        max_ticks=args.ticks,
        workers=max(1, args.workers),
        output_dir=Path(args.output_dir) if args.output_dir else None,
    )


if __name__ == "__main__":
    main()
