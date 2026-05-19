"""Phase 4c — Mechanism Screen: Cry Signal vs Temperature OVAT.

Two independent one-at-a-time (OVAT) sweeps on top of Phase 4b BEST_CALIBRATED
ecology, using Phase 4b OPTIMAL weights (care=0.5, forage=2.0, self=1.0):

  Cry axis  : cry_decay_radius       = [0.0, 3.0, 6.0, 10.0]  (temperature_sensitivity=0.0)
  Temp axis : temperature_sensitivity = [0.0, 0.1, 0.3, 0.5]   (cry_decay_radius=0.0)

Metrics per condition (averaged across seeds):
  SVR — Seed Viability Rate: mean pop during active window [50,400] / init_mothers
  CMR — Child Maturation Rate: fraction of children reaching maturity_age=80
  PSC — Population Stability Coefficient: CV of population during active window [50,400]

Lock rule: highest CMR among levels with SVR >= 0.60 AND PSC < 0.50.
Fallback if no level qualifies: highest CMR overall.

Outputs (outputs/phase4c_mechanism_screen/exp_<ts>/):
  cry_ovat.csv                 — SVR/CMR/PSC per cry level
  temp_ovat.csv                — SVR/CMR/PSC per temperature level
  mechanism_screen.png         — 2x3 bar-chart panel
  best_mechanism_settings.json — selected cry_decay_radius + temperature_sensitivity

Usage:
  python -m experiments.phase4c_mechanism_screen.run
  python -m experiments.phase4c_mechanism_screen.run --seeds 10 --ticks 2000 --workers 4
"""

from __future__ import annotations

import argparse
import csv
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
# OVAT axes
# ---------------------------------------------------------------------------

CRY_LEVELS: list[tuple[float, str, str]] = [
    (0.0,  "C0", "Global cry (r=0)"),
    (3.0,  "C1", "Mild decay (r=3)"),
    (6.0,  "C2", "Moderate decay (r=6)"),
    (10.0, "C3", "Strong decay (r=10)"),
]

TEMP_LEVELS: list[tuple[float, str, str]] = [
    (0.0, "T0", "No temperature"),
    (0.1, "T1", "Mild temp (s=0.1)"),
    (0.3, "T2", "Moderate temp (s=0.3)"),
    (0.5, "T3", "Strong temp (s=0.5)"),
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
    "care_weight": 0.5,
    "forage_weight": 2.0,
    "self_weight": 1.0,
}

TAIL_WINDOW   = 200
ACTIVE_START  = 50   # skip system warm-up
ACTIVE_END    = 400  # mother_max_age — active care window ends here
INIT_MOTHERS  = 15

SVR_MIN = 0.60
PSC_MAX = 0.50


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

def make_config(cry: float, temp: float, seed: int, max_ticks: int, eco: dict) -> Config:
    """Phase 4b BEST_CALIBRATED ecology + OPTIMAL weights + given cry/temp."""
    cfg = Config()
    cfg.max_ticks = max_ticks
    cfg.seed = seed
    cfg.width = 50
    cfg.height = 50

    # Population
    cfg.init_mothers = INIT_MOTHERS
    cfg.initial_energy = 1.0

    # Phase 4b BEST_CALIBRATED ecology
    cfg.init_food = int(eco.get("init_food", 300))
    cfg.eat_gain = eco.get("eat_gain", 0.70)
    cfg.move_cost = eco.get("move_cost", 0.005)
    cfg.rest_recovery = eco.get("rest_recovery", 0.005)
    cfg.perception_radius = int(eco.get("perception_radius", 8))
    cfg.food_perception_radius = int(eco.get("food_perception_radius", 8))

    # Energy dynamics (Phase 3/4 locked)
    cfg.hunger_rate = 1.0 / 35.0
    cfg.feed_cost = 0.01
    cfg.fatigue_rate = 0.01

    # Phase 4b OPTIMAL weights
    cfg.care_weight = eco.get("care_weight", 0.5)
    cfg.forage_weight = eco.get("forage_weight", 2.0)
    cfg.self_weight = eco.get("self_weight", 1.0)

    # Mechanism params — OVAT axes
    cfg.cry_decay_radius = cry
    cfg.temperature_sensitivity = temp
    cfg.temperature_period = 200
    cfg.warmth_factor = 0.0
    cfg.warmth_radius = 3

    # Care energy floor (Phase 4 approach E)
    cfg.care_energy_floor = 0.3

    # Shannon food (uniform 1:1 replacement — Phase 4b baseline)
    cfg.food_entropy_alpha = 0.0
    cfg.food_entropy_beta = 0.01
    cfg.food_entropy_gamma = 0.01
    cfg.food_patch_prior = cfg.init_food / (cfg.width * cfg.height)

    # Phase 4c mode: children + care, no evolution
    cfg.children_enabled = True
    cfg.care_enabled = True
    cfg.reproduction_enabled = False
    cfg.mutation_enabled = False
    cfg.plasticity_enabled = False
    cfg.allow_allomothering = False

    # Child parameters
    cfg.infant_starvation_multiplier = float(eco.get("infant_starvation_multiplier", 1.0))
    cfg.maturity_age = 80
    cfg.starvation_threshold = 1.0

    # Mother lifetime
    cfg.mother_max_age = 400

    # Food replacement (1:1)
    cfg.food_replace_on_pick = True
    cfg.food_replenish_threshold_ratio = 0.0

    # Softmax
    cfg.softmax_tau = 0.1

    # Birth placement
    cfg.birth_scatter_radius = 2

    # Reproduction params (must exist even when off)
    cfg.reproduction_threshold = 0.85
    cfg.reproduction_cost = 0.20
    cfg.reproduction_cooldown = 120

    # Plasticity params (must exist even when off)
    cfg.plastic_gain = 0.1
    cfg.plasticity_metabolic_alpha = 0.01
    cfg.plasticity_maintenance_beta = 0.001
    cfg.plasticity_kin_conditional = True
    cfg.init_learning_rate = 1.0
    cfg.init_plasticity_coefficient = 1.0
    cfg.phenotype_retention = 0.15

    # Mutation params (must exist even when off)
    cfg.mutation_rate = 0.5
    cfg.mutation_sigma = 0.02
    cfg.min_mutation_rate = 0.01

    return cfg


# ---------------------------------------------------------------------------
# Worker (module-level for ProcessPoolExecutor pickling)
# ---------------------------------------------------------------------------

def _worker(args: tuple) -> dict:
    """Run one seed for one (cry, temp) combination."""
    cry, temp, seed, max_ticks, eco = args

    import sys
    from pathlib import Path as _Path
    sys.path.insert(0, str(_Path(__file__).resolve().parents[2]))

    import random
    import numpy as _np
    random.seed(seed)
    _np.random.seed(seed)

    from experiments.phase4c_mechanism_screen.run import make_config
    from experiments.phase3_survival_full.run import Phase3Simulation

    cfg = make_config(cry, temp, seed, max_ticks, eco)
    sim = Phase3Simulation(cfg)
    result = sim.run()
    result["cry"] = cry
    result["temp"] = temp
    result["seed"] = seed
    result.pop("spatial_heatmap", None)
    return result


# ---------------------------------------------------------------------------
# Aggregation
# ---------------------------------------------------------------------------

def _active_window(arr: np.ndarray) -> np.ndarray:
    """Slice [ACTIVE_START, ACTIVE_END] from a population array."""
    start = min(ACTIVE_START, len(arr))
    end   = min(ACTIVE_END,   len(arr))
    return arr[start:end] if end > start else arr


def _svr(r: dict) -> float:
    """Mean population during active care window / init_mothers."""
    hist   = np.asarray(r["population_history"], dtype=float)
    window = _active_window(hist)
    return float(np.mean(window)) / INIT_MOTHERS


def _psc(pop_history: list) -> float:
    """Population Stability Coefficient: CV during active care window."""
    arr    = np.asarray(pop_history, dtype=float)
    window = _active_window(arr)
    mu     = float(np.mean(window))
    return float(np.std(window) / max(1.0, mu))


def aggregate(seed_results: list[dict]) -> dict:
    svr_vals = [_svr(r) for r in seed_results]
    cmr_vals = [r["child_maturation_rate"] for r in seed_results]
    psc_vals = [_psc(r["population_history"]) for r in seed_results]
    care_vals = [r.get("care_pct", 0.0) for r in seed_results]

    return {
        "svr_mean": float(np.mean(svr_vals)),
        "svr_sd":   float(np.std(svr_vals)),
        "cmr_mean": float(np.mean(cmr_vals)),
        "cmr_sd":   float(np.std(cmr_vals)),
        "psc_mean": float(np.mean(psc_vals)),
        "psc_sd":   float(np.std(psc_vals)),
        "care_pct_mean": float(np.mean(care_vals)),
        "n_seeds":  len(seed_results),
    }


def _empty_agg() -> dict:
    return {k: 0.0 for k in ("svr_mean", "svr_sd", "cmr_mean", "cmr_sd",
                              "psc_mean", "psc_sd", "care_pct_mean")} | {"n_seeds": 0}


# ---------------------------------------------------------------------------
# Level selection
# ---------------------------------------------------------------------------

def select_level(
    level_aggs: list[dict],
    levels: list[tuple[float, str, str]],
) -> tuple[float, str, str, dict]:
    """Lock rule: highest CMR with SVR >= SVR_MIN and PSC < PSC_MAX.
    Fallback: highest CMR overall."""
    items = [(agg, val, lbl, desc) for agg, (val, lbl, desc) in zip(level_aggs, levels)]
    valid = [(agg, val, lbl, desc) for agg, val, lbl, desc in items
             if agg["svr_mean"] >= SVR_MIN and agg["psc_mean"] < PSC_MAX]

    if valid:
        best = max(valid, key=lambda x: x[0]["cmr_mean"])
    else:
        print("  WARNING: no level meets SVR>=%.2f and PSC<%.2f — fallback: highest CMR" % (
            SVR_MIN, PSC_MAX))
        best = max(items, key=lambda x: x[0]["cmr_mean"])

    agg, val, lbl, desc = best
    return val, lbl, desc, agg


# ---------------------------------------------------------------------------
# CSV helper
# ---------------------------------------------------------------------------

def _save_csv(aggs: list[dict], levels: list[tuple[float, str, str]], path: Path) -> None:
    fieldnames = ["label", "value", "desc", "n_seeds",
                  "svr_mean", "svr_sd", "cmr_mean", "cmr_sd",
                  "psc_mean", "psc_sd", "care_pct_mean"]
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for agg, (val, lbl, desc) in zip(aggs, levels):
            w.writerow({"label": lbl, "value": val, "desc": desc,
                        **{k: agg[k] for k in fieldnames[3:]}})
    print("  Saved %s" % path.name)


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
    out = output_dir or (PROJECT_ROOT / "outputs" / "phase4c_mechanism_screen" / ("exp_%s" % ts))
    out.mkdir(parents=True, exist_ok=True)

    print("[phase4c_mechanism_screen]")
    print("  ecology : init_food=%d  eat_gain=%.2f  move_cost=%.4f  ISM=%.1f" % (
        eco.get("init_food", 300), eco.get("eat_gain", 0.7),
        eco.get("move_cost", 0.005), eco.get("infant_starvation_multiplier", 1.0),
    ))
    print("  weights : care=%.1f  forage=%.1f  self=%.1f  (Phase 4b OPTIMAL)" % (
        eco.get("care_weight", 0.5), eco.get("forage_weight", 2.0), eco.get("self_weight", 1.0),
    ))
    print("  seeds=%d  ticks=%d  workers=%d  output=%s" % (seeds, max_ticks, workers, out))

    seed_list = list(range(42, 42 + seeds))

    cry_jobs = [(cry_val, 0.0, seed, max_ticks, eco)
                for cry_val, _, _ in CRY_LEVELS for seed in seed_list]
    temp_jobs = [(0.0, temp_val, seed, max_ticks, eco)
                 for temp_val, _, _ in TEMP_LEVELS for seed in seed_list]

    cry_results:  dict[float, list[dict]] = {v: [] for v, _, _ in CRY_LEVELS}
    temp_results: dict[float, list[dict]] = {v: [] for v, _, _ in TEMP_LEVELS}

    def _dispatch_sequential() -> None:
        print("\n  -- Cry OVAT (temperature_sensitivity=0.0) --")
        for job in cry_jobs:
            r = _worker(job)
            cry_results[r["cry"]].append(r)
            print("  [ok] cry=%.1f  seed=%d  svr=%.2f  cmr=%.2f" % (
                r["cry"], r["seed"], _svr(r), r["child_maturation_rate"]))
        print("  -- Temperature OVAT (cry_decay_radius=0.0) --")
        for job in temp_jobs:
            r = _worker(job)
            temp_results[r["temp"]].append(r)
            print("  [ok] temp=%.1f  seed=%d  svr=%.2f  cmr=%.2f" % (
                r["temp"], r["seed"], _svr(r), r["child_maturation_rate"]))

    def _dispatch_parallel() -> None:
        futures: dict = {}
        with ProcessPoolExecutor(max_workers=workers) as pool:
            for job in cry_jobs:
                futures[pool.submit(_worker, job)] = ("cry", job)
            for job in temp_jobs:
                futures[pool.submit(_worker, job)] = ("temp", job)
            for future in as_completed(futures):
                axis, job = futures[future]
                try:
                    r = future.result()
                    if axis == "cry":
                        cry_results[r["cry"]].append(r)
                    else:
                        temp_results[r["temp"]].append(r)
                    print("  [ok] %s=%.1f  seed=%d  svr=%.2f  cmr=%.2f" % (
                        axis, r["cry"] if axis == "cry" else r["temp"],
                        r["seed"], _svr(r), r["child_maturation_rate"]))
                except Exception as exc:
                    print("  [FAIL] job=%s: %s" % (str(job[:3]), exc))

    if workers <= 1:
        _dispatch_sequential()
    else:
        _dispatch_parallel()

    # Aggregate
    cry_aggs: list[dict] = []
    temp_aggs: list[dict] = []

    print("\n  CRY OVAT summary:")
    print("  %-6s  %-8s  %6s  %6s  %6s  %6s  %4s" % (
        "Label", "Value", "SVR", "CMR", "PSC", "care%", "n"))
    for val, lbl, desc in CRY_LEVELS:
        results = cry_results.get(val, [])
        agg = aggregate(results) if results else _empty_agg()
        cry_aggs.append(agg)
        print("  %-6s  %-8.1f  %.3f  %.3f  %.3f  %.3f  %4d" % (
            lbl, val, agg["svr_mean"], agg["cmr_mean"],
            agg["psc_mean"], agg["care_pct_mean"], agg["n_seeds"]))

    print("  TEMP OVAT summary:")
    print("  %-6s  %-8s  %6s  %6s  %6s  %6s  %4s" % (
        "Label", "Value", "SVR", "CMR", "PSC", "care%", "n"))
    for val, lbl, desc in TEMP_LEVELS:
        results = temp_results.get(val, [])
        agg = aggregate(results) if results else _empty_agg()
        temp_aggs.append(agg)
        print("  %-6s  %-8.1f  %.3f  %.3f  %.3f  %.3f  %4d" % (
            lbl, val, agg["svr_mean"], agg["cmr_mean"],
            agg["psc_mean"], agg["care_pct_mean"], agg["n_seeds"]))

    # Select best levels
    best_cry_val, best_cry_lbl, best_cry_desc, best_cry_agg = select_level(cry_aggs, CRY_LEVELS)
    best_temp_val, best_temp_lbl, best_temp_desc, best_temp_agg = select_level(temp_aggs, TEMP_LEVELS)

    print("\n  SELECTED:")
    print("    cry  : %s (%s) — SVR=%.2f  CMR=%.2f  PSC=%.2f" % (
        best_cry_lbl, best_cry_desc,
        best_cry_agg["svr_mean"], best_cry_agg["cmr_mean"], best_cry_agg["psc_mean"]))
    print("    temp : %s (%s) — SVR=%.2f  CMR=%.2f  PSC=%.2f" % (
        best_temp_lbl, best_temp_desc,
        best_temp_agg["svr_mean"], best_temp_agg["cmr_mean"], best_temp_agg["psc_mean"]))

    # Save CSVs
    _save_csv(cry_aggs, CRY_LEVELS, out / "cry_ovat.csv")
    _save_csv(temp_aggs, TEMP_LEVELS, out / "temp_ovat.csv")

    # Save best_mechanism_settings.json
    best_settings = {
        "ecology": {k: eco.get(k) for k in (
            "init_food", "eat_gain", "move_cost", "rest_recovery",
            "infant_starvation_multiplier", "care_weight", "forage_weight", "self_weight",
        )},
        "run_params": {"seeds": seeds, "max_ticks": max_ticks},
        "lock_rule": {
            "svr_min": SVR_MIN,
            "psc_max": PSC_MAX,
            "criterion": "highest CMR with SVR >= svr_min AND PSC < psc_max",
        },
        "cry_decay_radius": {
            "selected_value": best_cry_val,
            "selected_label": best_cry_lbl,
            "selected_desc":  best_cry_desc,
            "svr_mean": best_cry_agg["svr_mean"],
            "cmr_mean": best_cry_agg["cmr_mean"],
            "psc_mean": best_cry_agg["psc_mean"],
        },
        "temperature_sensitivity": {
            "selected_value": best_temp_val,
            "selected_label": best_temp_lbl,
            "selected_desc":  best_temp_desc,
            "svr_mean": best_temp_agg["svr_mean"],
            "cmr_mean": best_temp_agg["cmr_mean"],
            "psc_mean": best_temp_agg["psc_mean"],
        },
        "locked_settings": {
            "cry_decay_radius":        best_cry_val,
            "temperature_sensitivity": best_temp_val,
        },
    }
    (out / "best_mechanism_settings.json").write_text(json.dumps(best_settings, indent=2))
    print("  Saved best_mechanism_settings.json")

    # Plot
    from experiments.phase4c_mechanism_screen.plot import plot_mechanism_screen
    plot_mechanism_screen(
        cry_aggs, CRY_LEVELS, temp_aggs, TEMP_LEVELS,
        best_cry_lbl, best_temp_lbl, out,
    )

    print("\n[ok] Phase 4c mechanism screen complete — %s" % out)
    return out


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Phase 4c Mechanism Screen (Cry + Temperature OVAT)")
    parser.add_argument("--seeds",      type=int, default=5)
    parser.add_argument("--ticks",      type=int, default=2000)
    parser.add_argument("--workers",    type=int, default=1,
                        help="Parallel workers (0=cpu_count)")
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
