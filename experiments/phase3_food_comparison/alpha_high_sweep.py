"""Phase 3 high-alpha sweep — test stronger Shannon dispersal at prior=0.37.

Runs alpha=[0.10, 0.20, 0.50, 1.00] with fixed perception=8 and prior=0.37
to see if stronger food dispersal breaks the spatial clustering.

Output:
  outputs/phase3_alpha_high_sweep/exp_<ts>/
    A10/ A20/ A50/ A100/
      validation_<label>.png
      spatial_heatmap_population_<label>.png
      motivation_selection_<label>.png
      ...

Usage:
  python -m experiments.phase3_food_comparison.alpha_high_sweep
  python -m experiments.phase3_food_comparison.alpha_high_sweep --seeds 5 --ticks 2000 --workers 4
"""
from __future__ import annotations

import argparse
import sys
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

ALPHA_LEVELS: list[tuple[float, str, str]] = [
    (0.10, "A10",  "Shannon alpha=0.10 (baseline)"),
    (0.20, "A20",  "Shannon alpha=0.20"),
    (0.50, "A50",  "Shannon alpha=0.50"),
    (1.00, "A100", "Shannon alpha=1.00 (strong dispersal)"),
]


def _worker(args: tuple) -> dict:
    alpha, seed, max_ticks, eco, prior, perception = args
    import sys as _sys
    from pathlib import Path as _Path
    _sys.path.insert(0, str(_Path(__file__).resolve().parents[2]))
    import random as _random
    import numpy as _np
    _random.seed(seed)
    _np.random.seed(seed)

    from experiments.phase3_food_comparison.diagnostic_run import make_config
    from experiments.phase3_survival_full.run import Phase3Simulation

    cfg = make_config(alpha, eco, max_ticks, prior, perception)
    cfg.seed = seed
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

    plot_stacked_action_failed_over_time(label, results, max_ticks, out_str)
    plot_rate_sum_check(label, results, max_ticks, out_str)
    plot_food_consumption_over_time(label, results, max_ticks, out_str)
    plot_spatial_heatmap_population(label, results, out_str)
    plot_homeostatic_balance(label, results, max_ticks, out_str)


def run(seeds: int = 5, max_ticks: int = 2000, workers: int = 1,
        output_dir: Path | None = None,
        prior: float = 0.37,
        perception: int = 8) -> Path:
    from experiments.phase3_food_comparison.diagnostic_run import load_ecology
    eco = load_ecology()
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out = output_dir or (PROJECT_ROOT / "outputs" / "phase3_alpha_high_sweep" / ("exp_%s" % ts))
    out.mkdir(parents=True, exist_ok=True)

    print("[phase3_alpha_high_sweep]")
    print("  prior=%.2f (food_equiv=%d)  perception=%d" % (prior, int(prior * 2500), perception))
    print("  seeds=%d  ticks=%d  workers=%d" % (seeds, max_ticks, workers))
    print("  output: %s" % out)

    seed_list = list(range(42, 42 + seeds))

    for alpha, label, desc in ALPHA_LEVELS:
        print("\n  [%s] %s" % (label, desc))
        jobs = [(alpha, s, max_ticks, eco, prior, perception) for s in seed_list]
        results: list[dict] = []

        if workers <= 1:
            for job in jobs:
                r = _worker(job)
                results.append(r)
                print("    seed=%d  final_pop=%d  cmr=%.3f  care_pct=%.3f" % (
                    r["base_seed"], r["final_pop"],
                    r.get("child_maturation_rate", 0.0),
                    r.get("care_pct", 0.0)))
        else:
            with ProcessPoolExecutor(max_workers=workers) as pool:
                futures = {pool.submit(_worker, job): job for job in jobs}
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

    print("\n[ok] Phase 3 high-alpha sweep complete -- %s" % out)
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description="Phase 3 high-alpha Shannon sweep")
    parser.add_argument("--seeds", type=int, default=5)
    parser.add_argument("--ticks", type=int, default=2000)
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument("--output-dir", type=str, default=None)
    parser.add_argument("--prior", type=float, default=0.37,
                        help="food_patch_prior (default: 0.37 = entropy max from sweep)")
    parser.add_argument("--perception", type=int, default=8,
                        help="perception_radius (default: 8)")
    args = parser.parse_args()

    run(
        seeds=args.seeds,
        max_ticks=args.ticks,
        workers=max(1, args.workers),
        output_dir=Path(args.output_dir) if args.output_dir else None,
        prior=args.prior,
        perception=args.perception,
    )


if __name__ == "__main__":
    main()
