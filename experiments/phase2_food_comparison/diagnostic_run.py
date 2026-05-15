"""Phase 2 Food Shannon Diagnostic — detailed plots (auto_400_percept8 style) per Shannon alpha.

Runs the same 4 alpha conditions as phase2_food_comparison/run.py, but uses
SurvivalSimulation (which tracks per-tick action/motivation/food/energy-flow
histories) so every new_plot.py diagnostic can be generated per condition.

Output structure:
  outputs/phase2_food_shannon_diagnostic/exp_<ts>/
    F0/  F1/  F2/  F3/
      validation_<label>.png
      action_selection_<label>.png
      motivation_selection_<label>.png
      ...

Usage:
  python -m experiments.phase2_food_comparison.diagnostic_run
  python -m experiments.phase2_food_comparison.diagnostic_run --seeds 10 --ticks 2000 --workers 4
"""
from __future__ import annotations

import argparse
import json
import random
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
}


def load_ecology() -> dict:
    if _ECOLOGY_PATH.exists():
        try:
            data = json.loads(_ECOLOGY_PATH.read_text())
            return data.get("BEST_CALIBRATED", data)
        except Exception as exc:
            print("Warning: %s" % exc)
    return _FALLBACK.copy()


def make_config(alpha: float, eco: dict, max_ticks: int,
                prior: float | None = None) -> Config:
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
    if prior is not None:
        cfg.init_food = max(1, int(prior * cfg.width * cfg.height))
        cfg.food_patch_prior = prior
    else:
        cfg.food_patch_prior = cfg.init_food / (cfg.width * cfg.height)
    cfg.care_weight = 0.0
    cfg.forage_weight = 1.0
    cfg.self_weight = 1.0
    cfg.children_enabled = False
    cfg.care_enabled = False
    cfg.reproduction_enabled = False
    cfg.mutation_enabled = False
    cfg.plasticity_enabled = False
    return cfg


def _worker(args: tuple) -> dict:
    alpha, seed, max_ticks, eco, prior = args
    import sys as _sys
    from pathlib import Path as _Path
    _sys.path.insert(0, str(_Path(__file__).resolve().parents[2]))

    import random as _random
    import numpy as _np
    _random.seed(seed)
    _np.random.seed(seed)

    from experiments.phase2_food_comparison.diagnostic_run import make_config
    from experiments.phase2_survival_minimal.new_run import SurvivalSimulation

    cfg = make_config(alpha, eco, max_ticks, prior)
    sim = SurvivalSimulation(cfg)
    result = sim.run()
    result["base_seed"] = seed
    result["repeat"] = seed
    result["run_seed"] = seed
    return result


def _generate_plots(label: str, desc: str, results: list[dict], eco: dict,
                    max_ticks: int, out: Path) -> None:
    from experiments.phase2_survival_minimal.new_plot import (
        plot_multiseed_condition,
        plot_action_selection_over_time,
        plot_motivation_selection_over_time,
        plot_failed_selection_over_time,
        plot_stacked_action_failed_over_time,
        plot_motivation_action_count_bar,
        plot_failed_action_rate_bar,
        plot_failed_forage_energy_correlation,
        plot_rate_sum_check,
        plot_state_space_energy_action,
        plot_food_consumption_over_time,
        plot_spatial_heatmap_population,
        plot_energy_expenditure_breakdown,
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
        "care_weight": 0.0,
        "food_entropy_alpha": float(label[1:].replace("p", ".")) if label != "F0" else 0.0,
    }

    run_labels = ["seed%d" % r["base_seed"] for r in results]
    out_str = str(out)

    plot_multiseed_condition(label, results, params, run_labels, max_ticks, out_str)
    plot_action_selection_over_time(label, results, max_ticks, out_str)
    plot_motivation_selection_over_time(label, results, max_ticks, out_str)
    plot_failed_selection_over_time(label, results, max_ticks, out_str)
    plot_stacked_action_failed_over_time(label, results, max_ticks, out_str)
    plot_motivation_action_count_bar(label, results, out_str)
    plot_failed_action_rate_bar(label, results, out_str)
    plot_failed_forage_energy_correlation(label, results, max_ticks, out_str)
    plot_rate_sum_check(label, results, max_ticks, out_str)
    plot_state_space_energy_action(label, results, max_ticks, out_str)
    plot_food_consumption_over_time(label, results, max_ticks, out_str)
    plot_spatial_heatmap_population(label, results, out_str)
    plot_energy_expenditure_breakdown(label, results, out_str)
    plot_homeostatic_balance(label, results, max_ticks, out_str)


def run(seeds: int = 5, max_ticks: int = 2000, workers: int = 1,
        output_dir: Path | None = None,
        prior: float | None = None) -> Path:
    eco = load_ecology()
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out = output_dir or (PROJECT_ROOT / "outputs" / "phase2_food_shannon_diagnostic" / f"exp_{ts}")
    out.mkdir(parents=True, exist_ok=True)

    eff_prior = prior if prior is not None else eco.get("init_food", 300) / 2500
    print("[phase2_food_shannon_diagnostic]")
    print("  ecology: eat_gain=%.2f  move_cost=%.4f" % (
        eco.get("eat_gain", 0.7), eco.get("move_cost", 0.005)))
    print("  prior=%.2f (food_equiv=%d)  seeds=%d  ticks=%d  workers=%d" % (
        eff_prior, int(eff_prior * 2500), seeds, max_ticks, workers))
    print("  output: %s" % out)

    seed_list = list(range(42, 42 + seeds))

    for alpha, label, desc in ALPHA_LEVELS:
        print("\n  [%s] %s" % (label, desc))
        jobs = [(alpha, s, max_ticks, eco, prior) for s in seed_list]
        results: list[dict] = []

        if workers <= 1:
            for job in jobs:
                r = _worker(job)
                results.append(r)
                print("    seed=%d  final_pop=%d  mean_energy=%.3f" % (
                    r["base_seed"], r["final_pop"], r["mean_energy"]))
        else:
            with ProcessPoolExecutor(max_workers=workers) as pool:
                futures = {pool.submit(_worker, job): job for job in jobs}
                for future in as_completed(futures):
                    try:
                        r = future.result()
                        results.append(r)
                        print("    seed=%d  final_pop=%d  mean_energy=%.3f" % (
                            r["base_seed"], r["final_pop"], r["mean_energy"]))
                    except Exception as exc:
                        job = futures[future]
                        print("    [FAIL] seed=%d: %s" % (job[1], exc))

        if not results:
            print("    WARNING: no results for %s" % label)
            continue

        cond_out = out / label
        cond_out.mkdir(parents=True, exist_ok=True)
        _generate_plots(label, desc, results, eco, max_ticks, cond_out)
        print("    Plots saved -> %s" % cond_out)

    print("\n[ok] Phase 2 Shannon diagnostic complete — %s" % out)
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description="Phase 2 Food Shannon Diagnostic")
    parser.add_argument("--seeds", type=int, default=5)
    parser.add_argument("--ticks", type=int, default=2000)
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument("--output-dir", type=str, default=None)
    parser.add_argument("--prior", type=float, default=None,
                        help="Override food_patch_prior (and init_food). "
                             "Default: init_food/(W*H). Best from sweep: 0.37")
    args = parser.parse_args()

    run(
        seeds=args.seeds,
        max_ticks=args.ticks,
        workers=max(1, args.workers),
        output_dir=Path(args.output_dir) if args.output_dir else None,
        prior=args.prior,
    )


if __name__ == "__main__":
    main()
