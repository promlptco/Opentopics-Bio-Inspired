"""Phase 2 — Food Mechanism Comparison: Uniform (1:1) vs Shannon Entropy.

Compares four food_entropy_alpha levels at Phase 4b BEST_CALIBRATED ecology.
Mother-only simulation (no children, no reproduction, no mutation).

Alpha levels:
  F0: 0.00 — uniform 1:1 replacement (existing Phase 2 baseline)
  F1: 0.01 — mild Shannon patchy food
  F2: 0.05 — moderate Shannon patchy food
  F3: 0.10 — strong Shannon patchy food

Outputs (in outputs/phase2_food_comparison/exp_<ts>/):
  food_comparison_timeseries.png — 4-panel time-series overlay
  food_comparison_summary.png    — bar chart of tail-window metrics
  summary.json                   — scalar results per condition

Usage:
  python -m experiments.phase2_food_comparison.run
  python -m experiments.phase2_food_comparison.run --workers 4 --seeds 10 --ticks 3000
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
from utils.experiment import set_seed


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
}

TAIL_WINDOW = 200
SMOOTH_WINDOW = 50

CONDITION_COLORS = {
    "F0": "#1f4e79",  # dark blue
    "F1": "#2a9a3c",  # green
    "F2": "#e07b00",  # orange
    "F3": "#c0392b",  # red
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
            print(f"Warning: could not parse ecology JSON: {exc}")
    else:
        print(f"Warning: {_ECOLOGY_PATH} not found — using fallback ecology")
    return _FALLBACK_ECOLOGY.copy()


# ---------------------------------------------------------------------------
# Config builder
# ---------------------------------------------------------------------------

def make_comparison_config(alpha: float, seed: int, max_ticks: int, eco: dict) -> Config:
    """Build a mother-only Config at Phase 4b BEST_CALIBRATED + given alpha."""
    cfg = Config()
    cfg.max_ticks = max_ticks
    cfg.seed = seed
    cfg.width = 50
    cfg.height = 50

    cfg.init_mothers = 15
    cfg.initial_energy = 1.0

    # Phase 4b BEST_CALIBRATED ecology
    cfg.init_food = int(eco.get("init_food", 300))
    cfg.eat_gain = eco.get("eat_gain", 0.70)
    cfg.move_cost = eco.get("move_cost", 0.005)
    cfg.rest_recovery = eco.get("rest_recovery", 0.005)
    cfg.perception_radius = int(eco.get("perception_radius", 8))
    cfg.food_perception_radius = int(eco.get("food_perception_radius", 8))

    cfg.hunger_rate = 1.0 / 35.0
    cfg.feed_cost = 0.01
    cfg.fatigue_rate = 0.01

    # Shannon food mechanism
    cfg.food_entropy_alpha = alpha
    cfg.food_entropy_beta = 0.01
    cfg.food_entropy_gamma = 0.01
    # food_patch_prior sets equilibrium food density: 300 items on 50×50 = 0.12
    cfg.food_patch_prior = cfg.init_food / (cfg.width * cfg.height)

    # Genome weights: neutral FORAGE/SELF, no CARE
    cfg.forage_weight = 1.0
    cfg.self_weight = 1.0
    cfg.care_weight = 0.0

    # Consistent maturity age (no effect — mother-only, no children)
    cfg.maturity_age = 80

    # Mother-only mode — all other mechanisms off
    cfg.children_enabled = False
    cfg.care_enabled = False
    cfg.reproduction_enabled = False
    cfg.mutation_enabled = False
    cfg.plasticity_enabled = False

    cfg.softmax_tau = 0.1

    # Disable other ecological mechanisms
    cfg.cry_decay_radius = 0.0
    cfg.temperature_sensitivity = 0.0
    cfg.warmth_factor = 0.0

    return cfg


# ---------------------------------------------------------------------------
# Top-level worker (must be at module level for ProcessPoolExecutor pickling)
# ---------------------------------------------------------------------------

def _worker(args: tuple) -> dict:
    """Run one seed for one alpha level. Returns result dict."""
    alpha, seed, max_ticks, eco = args

    import sys
    from pathlib import Path as _Path
    sys.path.insert(0, str(_Path(__file__).resolve().parents[2]))

    from utils.experiment import set_seed as _set_seed
    from experiments.phase2_survival_minimal.new_run import SurvivalSimulation
    from experiments.phase2_food_comparison.run import make_comparison_config

    _set_seed(seed)
    cfg = make_comparison_config(alpha, seed, max_ticks, eco)
    sim = SurvivalSimulation(cfg, tau=0.1, food_mult=1.0, perceptual_noise=0.0)
    result = sim.run()
    result["alpha"] = alpha
    result["seed"] = seed
    # Remove large spatial heatmap from transfer payload
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


def _mean_series(seed_results: list[dict], key: str, length: int) -> np.ndarray:
    stacked = np.array([_pad(r[key], length) for r in seed_results])
    return np.nanmean(stacked, axis=0)


def _std_series(seed_results: list[dict], key: str, length: int) -> np.ndarray:
    stacked = np.array([_pad(r[key], length) for r in seed_results])
    return np.nanstd(stacked, axis=0)


def _mean_history_key(seed_results: list[dict], history_key: str, field: str, length: int) -> np.ndarray:
    series = [[t.get(field, 0.0) for t in r[history_key]] for r in seed_results]
    stacked = np.array([_pad(s, length) for s in series])
    return np.nanmean(stacked, axis=0)


def _action_rate_series(seed_results: list[dict], action: str, length: int) -> np.ndarray:
    series = []
    for r in seed_results:
        rates = []
        for tick in r["action_history"]:
            total = sum(tick.get(k, 0) for k in ("MOVE", "PICK", "EAT", "REST"))
            rates.append(tick.get(action, 0) / max(1, total))
        series.append(rates)
    stacked = np.array([_pad(s, length) for s in series])
    return np.nanmean(stacked, axis=0)


def aggregate(seed_results: list[dict], max_ticks: int) -> dict:
    """Average time-series and scalar metrics across seeds for one condition."""
    n = max_ticks
    energy_mean = _mean_series(seed_results, "energy_history", n)
    energy_std = _std_series(seed_results, "energy_history", n)
    pop_mean = _mean_series(seed_results, "population_history", n)
    pop_std = _std_series(seed_results, "population_history", n)

    return {
        "energy_mean": energy_mean,
        "energy_std": energy_std,
        "pop_mean": pop_mean,
        "pop_std": pop_std,
        "food_avail_mean": _mean_history_key(seed_results, "food_history", "food_available", n),
        "eat_gain_mean": _mean_history_key(seed_results, "energy_flow_history", "eat_gain", n),
        "hunger_loss_mean": _mean_history_key(seed_results, "energy_flow_history", "hunger_loss", n),
        "move_loss_mean": _mean_history_key(seed_results, "energy_flow_history", "move_loss", n),
        "pick_rate": _action_rate_series(seed_results, "PICK", n),
        "move_rate": _action_rate_series(seed_results, "MOVE", n),
        "eat_rate": _action_rate_series(seed_results, "EAT", n),
        "rest_rate": _action_rate_series(seed_results, "REST", n),
        # Scalar summaries (tail window)
        "tail_mean_energy": float(np.nanmean(energy_mean[-TAIL_WINDOW:])),
        "tail_mean_pop": float(np.nanmean(pop_mean[-TAIL_WINDOW:])),
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
    out = output_dir or (PROJECT_ROOT / "outputs" / "phase2_food_comparison" / f"exp_{ts}")
    out.mkdir(parents=True, exist_ok=True)

    print(f"[phase2_food_comparison]")
    print(f"  ecology : init_food={eco.get('init_food')}  eat_gain={eco.get('eat_gain')}  move_cost={eco.get('move_cost')}")
    print(f"  seeds={seeds}  ticks={max_ticks}  workers={workers}")
    print(f"  output  : {out}")

    seed_list = list(range(42, 42 + seeds))
    jobs = [(alpha, seed, max_ticks, eco) for alpha, _, _ in ALPHA_LEVELS for seed in seed_list]

    seed_results_by_alpha: dict[float, list[dict]] = {alpha: [] for alpha, _, _ in ALPHA_LEVELS}

    if workers <= 1:
        for job in jobs:
            r = _worker(job)
            seed_results_by_alpha[r["alpha"]].append(r)
            print(f"  [ok] alpha={r['alpha']}  seed={r['seed']}  pop={r['final_pop']}")
    else:
        with ProcessPoolExecutor(max_workers=workers) as pool:
            futures = {pool.submit(_worker, job): job for job in jobs}
            for future in as_completed(futures):
                job = futures[future]
                try:
                    r = future.result()
                    seed_results_by_alpha[r["alpha"]].append(r)
                    print(f"  [ok] alpha={r['alpha']}  seed={r['seed']}  pop={r['final_pop']}")
                except Exception as exc:
                    print(f"  [FAIL] alpha={job[0]}  seed={job[1]}: {exc}")

    # Aggregate per condition
    aggregates: dict[str, dict] = {}
    for alpha, label, desc in ALPHA_LEVELS:
        results = seed_results_by_alpha.get(alpha, [])
        if not results:
            print(f"  WARNING: no results for alpha={alpha} ({label})")
            continue
        agg = aggregate(results, max_ticks)
        aggregates[label] = {"alpha": alpha, "label": label, "desc": desc, **agg}
        print(
            "  %s (%-28s)  tail_energy=%.3f  tail_pop=%.1f/%d" % (
                label, desc,
                agg["tail_mean_energy"], agg["tail_mean_pop"],
                eco.get("init_mothers", 15),
            )
        )

    # Save scalar summary (arrays excluded — too large for JSON)
    scalar_summary = {
        "ecology": {k: eco.get(k) for k in ("init_food", "eat_gain", "move_cost", "rest_recovery")},
        "run_params": {"seeds": seeds, "max_ticks": max_ticks},
        "conditions": {
            label: {
                "alpha": v["alpha"],
                "desc": v["desc"],
                "tail_mean_energy": v["tail_mean_energy"],
                "tail_mean_pop": v["tail_mean_pop"],
                "final_pop_mean": v["final_pop_mean"],
                "final_pop_sd": v["final_pop_sd"],
                "n_seeds": v["n_seeds"],
            }
            for label, v in aggregates.items()
        },
    }
    (out / "summary.json").write_text(json.dumps(scalar_summary, indent=2))
    print(f"  Saved summary.json")

    # Plot
    from experiments.phase2_food_comparison.plot import plot_comparison
    plot_comparison(aggregates, ALPHA_LEVELS, max_ticks, out, smooth_w=SMOOTH_WINDOW)

    print(f"\n[ok] Phase 2 food comparison complete — {out}")
    return out


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Phase 2 Food Mechanism Comparison")
    parser.add_argument("--seeds", type=int, default=5, help="Number of seeds per condition")
    parser.add_argument("--ticks", type=int, default=2000, help="Simulation duration (ticks)")
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
