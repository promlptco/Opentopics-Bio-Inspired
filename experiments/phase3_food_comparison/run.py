"""Phase 3 — Food Mechanism Comparison with Children: Uniform (1:1) vs Shannon Entropy.

Extends Phase 2 food comparison by adding children (care_enabled=True).
Uses unbiased genome weights (care=forage=self=1.0) — the Phase 3 research question
is whether any food mechanism allows unbiased mothers to rear children to maturity.

Alpha levels (same as Phase 2 food comparison):
  F0: 0.00 — uniform 1:1 replacement
  F1: 0.01 — mild Shannon patchy food
  F2: 0.05 — moderate Shannon patchy food
  F3: 0.10 — strong Shannon patchy food

Ecology: Phase 4b BEST_CALIBRATED (init_food=300, eat_gain=0.70, move_cost=0.005).
Children: 15 mother-child pairs, ISM=1.0, maturity_age=80.
Weights: unbiased (care=forage=self=1.0) — tests care-trap hypothesis.

Outputs (in outputs/phase3_food_comparison/exp_<ts>/):
  food_comparison_timeseries.png — 4-panel overlay (+ child panels)
  food_comparison_summary.png    — bar chart including child maturation rate
  summary.json                   — scalar results per condition

Usage:
  python -m experiments.phase3_food_comparison.run
  python -m experiments.phase3_food_comparison.run --workers 4 --seeds 10 --ticks 3000
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


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

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
_FALLBACK_ECOLOGY: dict = {
    "init_food": 300,
    "eat_gain": 0.70,
    "move_cost": 0.005,
    "rest_recovery": 0.005,
    "perception_radius": 8,
    "food_perception_radius": 8,
    "infant_starvation_multiplier": 1.0,
}

TAIL_WINDOW   = 200
ACTIVE_START  = 100  # skip warm-up
ACTIVE_END    = 350  # well before mother_max_age=400
SMOOTH_WINDOW = 50

CONDITION_COLORS = {
    "F0": "#1f4e79",
    "F1": "#2a9a3c",
    "F2": "#e07b00",
    "F3": "#c0392b",
}


# ---------------------------------------------------------------------------
# Ecology loader
# ---------------------------------------------------------------------------

def load_ecology() -> dict:
    if _ECOLOGY_PATH.exists():
        try:
            data = json.loads(_ECOLOGY_PATH.read_text())
            return data.get("BEST_CALIBRATED", data)
        except Exception as exc:
            print("Warning: could not parse ecology JSON: %s" % exc)
    else:
        print("Warning: %s not found — using fallback ecology" % _ECOLOGY_PATH)
    return _FALLBACK_ECOLOGY.copy()


# ---------------------------------------------------------------------------
# Config builder
# ---------------------------------------------------------------------------

def make_comparison_config(alpha: float, seed: int, max_ticks: int, eco: dict) -> Config:
    """Build a Phase 3 Config: Phase 4b ecology + children + unbiased weights + given alpha."""
    cfg = Config()
    cfg.max_ticks = max_ticks
    cfg.seed = seed
    cfg.width = 50
    cfg.height = 50

    # Population
    cfg.init_mothers = 15
    cfg.initial_energy = 1.0

    # Phase 4b BEST_CALIBRATED ecology
    cfg.init_food = int(eco.get("init_food", 300))
    cfg.eat_gain = eco.get("eat_gain", 0.70)
    cfg.move_cost = eco.get("move_cost", 0.005)
    cfg.rest_recovery = eco.get("rest_recovery", 0.005)
    cfg.perception_radius = int(eco.get("perception_radius", 8))
    cfg.food_perception_radius = int(eco.get("food_perception_radius", 8))

    # Energy dynamics
    cfg.hunger_rate = 1.0 / 35.0
    cfg.feed_cost = 0.01
    cfg.fatigue_rate = 0.01

    # Shannon food mechanism
    cfg.food_entropy_alpha = alpha
    cfg.food_entropy_beta = 0.01
    cfg.food_entropy_gamma = 0.01
    cfg.food_patch_prior = cfg.init_food / (cfg.width * cfg.height)  # 0.12

    # Unbiased genome weights (Phase 3 research question: can equal weights support care?)
    cfg.care_weight = 1.0
    cfg.forage_weight = 1.0
    cfg.self_weight = 1.0

    # Phase 3 mode: children + care, no evolution
    cfg.children_enabled = True
    cfg.care_enabled = True
    cfg.reproduction_enabled = False
    cfg.mutation_enabled = False
    cfg.plasticity_enabled = False
    cfg.allow_allomothering = False

    # Child parameters
    cfg.infant_starvation_multiplier = float(eco.get("infant_starvation_multiplier", 1.0))
    cfg.maturity_age = 80          # Phase 5 locked value
    cfg.starvation_threshold = 1.0

    # Mother lifetime
    cfg.mother_max_age = 400

    # Food replacement
    cfg.food_replace_on_pick = True         # 1:1 replacement when Shannon is OFF
    cfg.food_replenish_threshold_ratio = 0.0  # burst replenishment disabled

    # Reproduction parameters (must exist even though reproduction is off)
    cfg.reproduction_threshold = 0.85
    cfg.reproduction_cost = 0.20
    cfg.reproduction_cooldown = 120

    # Plasticity parameters (must exist even though plasticity is off)
    cfg.plastic_gain = 0.1
    cfg.plasticity_metabolic_alpha = 0.01
    cfg.plasticity_maintenance_beta = 0.001
    cfg.plasticity_kin_conditional = True
    cfg.init_learning_rate = 1.0
    cfg.init_plasticity_coefficient = 1.0
    cfg.phenotype_retention = 0.15

    # Other ecological mechanisms (disabled)
    cfg.softmax_tau = 0.1
    cfg.cry_decay_radius = 0.0
    cfg.temperature_sensitivity = 0.0
    cfg.warmth_factor = 0.0
    cfg.warmth_radius = 3
    cfg.temperature_period = 200
    cfg.birth_scatter_radius = 2

    # Mutation params (must exist even though mutation is off)
    cfg.mutation_rate = 0.5
    cfg.mutation_sigma = 0.02
    cfg.min_mutation_rate = 0.01

    return cfg


# ---------------------------------------------------------------------------
# Top-level worker (module-level for ProcessPoolExecutor pickling)
# ---------------------------------------------------------------------------

def _worker(args: tuple) -> dict:
    """Run one seed for one alpha level. Returns result dict."""
    alpha, seed, max_ticks, eco = args

    import sys
    from pathlib import Path as _Path
    sys.path.insert(0, str(_Path(__file__).resolve().parents[2]))

    import random
    import numpy as np
    random.seed(seed)
    np.random.seed(seed)

    from experiments.phase3_food_comparison.run import make_comparison_config
    from experiments.phase3_survival_full.run import Phase3Simulation

    cfg = make_comparison_config(alpha, seed, max_ticks, eco)
    sim = Phase3Simulation(cfg)
    result = sim.run()
    result["alpha"] = alpha
    result["seed"] = seed
    result.pop("spatial_heatmap", None)
    return result


# ---------------------------------------------------------------------------
# Aggregation helpers
# ---------------------------------------------------------------------------

def _pad(series: list, length: int) -> np.ndarray:
    arr = np.full(length, np.nan)
    s = np.asarray(series, dtype=float)
    n = min(length, len(s))
    arr[:n] = s[:n]
    return arr


def aggregate(seed_results: list[dict], max_ticks: int) -> dict:
    """Average time-series and scalar metrics across seeds for one condition."""
    n = max_ticks

    def _mean(key: str) -> np.ndarray:
        stacked = np.array([_pad(r[key], n) for r in seed_results])
        return np.nanmean(stacked, axis=0)

    def _std(key: str) -> np.ndarray:
        stacked = np.array([_pad(r[key], n) for r in seed_results])
        return np.nanstd(stacked, axis=0)

    def _mean_food_key(field: str) -> np.ndarray:
        series = [[t.get(field, 0.0) for t in r["food_history"]] for r in seed_results]
        stacked = np.array([_pad(s, n) for s in series])
        return np.nanmean(stacked, axis=0)

    energy_mean = _mean("energy_history")
    energy_std = _std("energy_history")
    pop_mean = _mean("population_history")
    pop_std = _std("population_history")
    child_energy_mean = _mean("child_energy_history")
    child_energy_std = _std("child_energy_history")
    child_pop_mean = _mean("child_population_history")
    child_pop_std = _std("child_population_history")

    return {
        # Mother time-series (Phase 2 compatible)
        "energy_mean": energy_mean,
        "energy_std": energy_std,
        "pop_mean": pop_mean,
        "pop_std": pop_std,
        # Child time-series
        "child_energy_mean": child_energy_mean,
        "child_energy_std": child_energy_std,
        "child_pop_mean": child_pop_mean,
        "child_pop_std": child_pop_std,
        # Food
        "food_avail_mean": _mean_food_key("food_available"),
        # Scalar summaries — active window avoids NaN from post-max_age population collapse
        "tail_mean_energy": float(np.nanmean(energy_mean[ACTIVE_START:ACTIVE_END])) if len(energy_mean) > ACTIVE_START else float("nan"),
        "tail_mean_pop":    float(np.nanmean(pop_mean[ACTIVE_START:ACTIVE_END]))    if len(pop_mean) > ACTIVE_START else float("nan"),
        "child_maturation_rate_mean": float(np.nanmean([r["child_maturation_rate"] for r in seed_results])),
        "child_maturation_rate_sd": float(np.nanstd([r["child_maturation_rate"] for r in seed_results])),
        "child_death_tick_mean": float(np.nanmean([r["child_death_tick_mean"] for r in seed_results])),
        "care_pct_mean": float(np.nanmean([r["care_pct"] for r in seed_results])),
        "final_pop_mean": float(np.nanmean([r["final_pop"] for r in seed_results])),
        "final_pop_sd": float(np.nanstd([r["final_pop"] for r in seed_results])),
        "n_seeds": len(seed_results),
    }


# ---------------------------------------------------------------------------
# Main runner
# ---------------------------------------------------------------------------

def run(
    seeds: int = 5,
    max_ticks: int = 2000,
    workers: int = 1,
    output_dir: Path | None = None,
) -> Path:
    eco = load_ecology()
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out = output_dir or (PROJECT_ROOT / "outputs" / "phase3_food_comparison" / f"exp_{ts}")
    out.mkdir(parents=True, exist_ok=True)

    print("[phase3_food_comparison]")
    print("  ecology : init_food=%d  eat_gain=%.2f  move_cost=%.4f  ISM=%.1f" % (
        eco.get("init_food", 300), eco.get("eat_gain", 0.7),
        eco.get("move_cost", 0.005), eco.get("infant_starvation_multiplier", 1.0),
    ))
    print("  weights : care=1.0  forage=1.0  self=1.0  (unbiased — tests care-trap)")
    print("  seeds=%d  ticks=%d  workers=%d" % (seeds, max_ticks, workers))
    print("  output  : %s" % out)

    seed_list = list(range(42, 42 + seeds))
    jobs = [(alpha, seed, max_ticks, eco) for alpha, _, _ in ALPHA_LEVELS for seed in seed_list]

    seed_results_by_alpha: dict[float, list[dict]] = {alpha: [] for alpha, _, _ in ALPHA_LEVELS}

    if workers <= 1:
        for job in jobs:
            r = _worker(job)
            seed_results_by_alpha[r["alpha"]].append(r)
            print("  [ok] alpha=%.2f  seed=%d  pop=%d  c_matr=%.2f" % (
                r["alpha"], r["seed"], r["final_pop"], r["child_maturation_rate"]))
    else:
        with ProcessPoolExecutor(max_workers=workers) as pool:
            futures = {pool.submit(_worker, job): job for job in jobs}
            for future in as_completed(futures):
                job = futures[future]
                try:
                    r = future.result()
                    seed_results_by_alpha[r["alpha"]].append(r)
                    print("  [ok] alpha=%.2f  seed=%d  pop=%d  c_matr=%.2f" % (
                        r["alpha"], r["seed"], r["final_pop"], r["child_maturation_rate"]))
                except Exception as exc:
                    print("  [FAIL] alpha=%.2f  seed=%d: %s" % (job[0], job[1], exc))

    # Aggregate per condition
    aggregates: dict[str, dict] = {}
    for alpha, label, desc in ALPHA_LEVELS:
        results = seed_results_by_alpha.get(alpha, [])
        if not results:
            print("  WARNING: no results for alpha=%.2f (%s)" % (alpha, label))
            continue
        agg = aggregate(results, max_ticks)
        aggregates[label] = {"alpha": alpha, "label": label, "desc": desc, **agg}
        print("  %s %-28s  tail_E=%.3f  tail_pop=%.1f  c_matr=%.2f  care_pct=%.2f" % (
            label, desc,
            agg["tail_mean_energy"], agg["tail_mean_pop"],
            agg["child_maturation_rate_mean"], agg["care_pct_mean"],
        ))

    # Save scalar summary
    scalar_summary = {
        "ecology": {k: eco.get(k) for k in ("init_food", "eat_gain", "move_cost", "rest_recovery", "infant_starvation_multiplier")},
        "run_params": {"seeds": seeds, "max_ticks": max_ticks},
        "genome": {"care_weight": 1.0, "forage_weight": 1.0, "self_weight": 1.0},
        "conditions": {
            label: {
                "alpha": v["alpha"],
                "desc": v["desc"],
                "tail_mean_energy": v["tail_mean_energy"],
                "tail_mean_pop": v["tail_mean_pop"],
                "child_maturation_rate_mean": v["child_maturation_rate_mean"],
                "child_maturation_rate_sd": v["child_maturation_rate_sd"],
                "child_death_tick_mean": v["child_death_tick_mean"],
                "care_pct_mean": v["care_pct_mean"],
                "final_pop_mean": v["final_pop_mean"],
                "final_pop_sd": v["final_pop_sd"],
                "n_seeds": v["n_seeds"],
            }
            for label, v in aggregates.items()
        },
    }
    (out / "summary.json").write_text(json.dumps(scalar_summary, indent=2))
    print("  Saved summary.json")

    # Plot
    from experiments.phase3_food_comparison.plot import plot_comparison
    plot_comparison(aggregates, ALPHA_LEVELS, max_ticks, out, smooth_w=SMOOTH_WINDOW)

    print("\n[ok] Phase 3 food comparison complete — %s" % out)
    return out


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Phase 3 Food Mechanism Comparison (with children)")
    parser.add_argument("--seeds", type=int, default=5)
    parser.add_argument("--ticks", type=int, default=2000)
    parser.add_argument("--workers", type=int, default=1, help="Parallel workers (0=cpu_count)")
    parser.add_argument("--output-dir", type=str, default=None)
    args = parser.parse_args()

    w = (
        __import__("os").cpu_count() or 1
        if args.workers == 0
        else max(1, args.workers)
    )
    run(
        seeds=args.seeds,
        max_ticks=args.ticks,
        workers=w,
        output_dir=Path(args.output_dir) if args.output_dir else None,
    )


if __name__ == "__main__":
    main()
