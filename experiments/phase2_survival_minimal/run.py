"""
experiments/phase2_survival_minimal/run.py

Phase 2 Survival-Minimal Baseline Calibration.

This script runs mother-only survival experiments to select baseline
environment settings for:
  - balanced
  - easy
  - harsh

Usage:
  # Full baseline sweep and validation
  python experiments/phase2_survival_minimal/run.py --mode sweep --duration 1000 --repeats 3

  # Same as above, because sweep is default mode
  python experiments/phase2_survival_minimal/run.py

  # Quick single-config validation
  python experiments/phase2_survival_minimal/run.py --mode single --duration 1000 --repeats 3

  # Custom stochasticity / perception noise
  python experiments/phase2_survival_minimal/run.py --mode sweep --duration 1000 --repeats 3 --tau 0.1 --perceptual_noise 0.1

Outputs:
  outputs/phase2_survival_minimal/<timestamp>_validation_selected_baselines/
    ├── validation_balanced.png
    ├── validation_easy.png
    ├── validation_harsh.png
    ├── validation_balanced.csv
    ├── validation_easy.csv
    ├── validation_harsh.csv
    └── auto_baseline_summary.json

Single mode outputs:
  outputs/phase2_survival_minimal/<timestamp>_validation_selected_baselines/
    ├── validation_single.png
    ├── validation_single.csv
    └── auto_baseline_summary.json
"""

import sys
import os
import argparse
import random
from datetime import datetime

import numpy as np

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, PROJECT_ROOT)

from config import Config
from simulation.world import GridWorld
from agents.mother import MotherAgent, softmax_probs
from evolution.genome import Genome
from utils.experiment import set_seed

from experiments.phase2_survival_minimal.config import (
    INIT_MOTHERS,
    INITIAL_ENERGY,
    VALIDATION_SEEDS,
    DEFAULT_SWEEP_SEED_BASE,
    DEFAULT_PERCEPTION_RADIUS,
    SELECTION_TARGETS,
    candidate_configs,
)

from experiments.phase2_survival_minimal.plot import (
    safe,
    summarize_repeats,
    plot_multiseed_condition,
    print_validation_runs,
    save_summary_json,
    save_validation_csv,
)


class SurvivalSimulation:
    def __init__(self, config, tau=0.1, food_mult=1.0, perceptual_noise=0.1):
        self.config = config
        self.tau = tau
        self.food_mult = food_mult
        self.perceptual_noise = perceptual_noise
        self.world = GridWorld(config.width, config.height)
        self.mothers = []
        self.tick = 0
        self.energy_history = []
        self.population_history = []
        self.action_counts = {"MOVE": 0, "EAT": 0, "REST": 0, "PICK": 0}

    def initialize(self):
        food_count = int(self.config.init_food * self.food_mult)

        for i in range(self.config.init_mothers):
            x, y = self._random_free_pos()
            genome = Genome(
                care_weight=0.0,
                forage_weight=0.85,
                self_weight=0.15,
                learning_rate=0.0,
                learning_cost=0.0,
            )
            mother = MotherAgent(x, y, lineage_id=i, generation=0, genome=genome)
            mother.energy = self.config.initial_energy
            self.mothers.append(mother)
            self.world.place_entity(mother)

        self._spawn_food(food_count)

    def _random_free_pos(self):
        for _ in range(200):
            x = random.randint(0, self.config.width - 1)
            y = random.randint(0, self.config.height - 1)
            if self.world.is_free((x, y)):
                return x, y
        return 0, 0

    def _spawn_food(self, count):
        spawned = 0
        for _ in range(count * 5):
            if spawned >= count:
                break
            x = random.randint(0, self.config.width - 1)
            y = random.randint(0, self.config.height - 1)
            if (x, y) not in self.world.food_positions:
                self.world.place_food(x, y)
                spawned += 1

    def _nearest_food(self, pos):
        if not self.world.food_positions:
            return None
        return min(self.world.food_positions, key=lambda f: self.world.get_distance(pos, f))

    def step(self):
        alive_mothers = [m for m in self.mothers if m.alive]
        random.shuffle(alive_mothers)

        for mother in alive_mothers:
            mother.tick_age()
            mother.energy = max(0.0, mother.energy - self.config.hunger_rate)

            perception_radius = getattr(self.config, "perception_radius", DEFAULT_PERCEPTION_RADIUS)

            nearest = self._nearest_food(mother.pos)
            dist_to_food = perception_radius

            if nearest:
                true_dist = self.world.get_distance(mother.pos, nearest)
                noisy_dist = max(0.0, true_dist + random.gauss(0.0, self.perceptual_noise))

                if noisy_dist <= perception_radius:
                    dist_to_food = noisy_dist
                else:
                    nearest = None

            u_forage = max(0.0, 1.0 - (dist_to_food / perception_radius))

            if mother.pos in self.world.food_positions:
                u_forage = 1.5

            if mother.held_food > 0:
                u_forage *= 0.1

            u_eat = 0.0
            if mother.held_food > 0:
                u_eat = 1.5 * (1.0 - mother.energy)

            u_rest = 0.8 * mother.fatigue

            scores = {"FORAGE": u_forage, "REST": u_rest, "EAT": u_eat}
            probs = softmax_probs(scores, tau=self.tau)
            selection = np.random.choice(list(probs.keys()), p=list(probs.values()))

            if selection == "EAT" and mother.held_food > 0:
                variance = random.uniform(0.8, 1.2)
                mother.energy = min(1.0, mother.energy + self.config.eat_gain * variance)
                mother.held_food -= 1
                self.action_counts["EAT"] += 1

            elif selection == "REST":
                mother.fatigue = max(0.0, mother.fatigue - self.config.rest_recovery)
                self.action_counts["REST"] += 1

            elif selection == "FORAGE":
                if mother.pos in self.world.food_positions:
                    self.world.remove_food(*mother.pos)
                    mother.held_food += 1
                    self.action_counts["PICK"] += 1
                elif nearest:
                    new_pos = self.world.get_step_toward(mother.pos, nearest)
                    if self.world.update_position(mother, new_pos):
                        mother.energy = max(0.0, mother.energy - self.config.move_cost)
                        mother.fatigue = min(1.0, mother.fatigue + self.config.fatigue_rate)
                        self.action_counts["MOVE"] += 1

            if mother.energy <= 0:
                mother.die()
                self.world.remove_entity(mother.id)

        target = int(self.config.init_food * self.food_mult)
        if len(self.world.food_positions) < max(1, target // 3):
            self._spawn_food(3)

        alive_now = [m for m in self.mothers if m.alive]
        self.population_history.append(len(alive_now))

        avg_energy = sum(m.energy for m in alive_now) / len(alive_now) if alive_now else 0.0
        self.energy_history.append(avg_energy)

    def run(self):
        self.initialize()

        for t in range(self.config.max_ticks):
            self.tick = t
            self.step()
            if not any(m.alive for m in self.mothers):
                break

        final_pop = sum(1 for m in self.mothers if m.alive)
        mean_energy = float(np.mean(self.energy_history)) if self.energy_history else 0.0
        final_energy = float(self.energy_history[-1]) if self.energy_history else 0.0

        return {
            "final_pop": final_pop,
            "mean_energy": mean_energy,
            "final_energy": final_energy,
            "energy_history": self.energy_history,
            "population_history": self.population_history,
            "actions": self.action_counts,
        }


def make_config(params, duration):
    cfg = Config()
    cfg.max_ticks = duration
    cfg.init_mothers = INIT_MOTHERS
    cfg.initial_energy = INITIAL_ENERGY

    cfg.perception_radius = params.get("perception_radius", DEFAULT_PERCEPTION_RADIUS)
    cfg.hunger_rate = params["hunger_rate"]
    cfg.move_cost = params["move_cost"]
    cfg.eat_gain = params["eat_gain"]
    cfg.init_food = params["init_food"]
    cfg.rest_recovery = params["rest_recovery"]

    # Used when FORAGE movement increases fatigue.
    cfg.fatigue_rate = params.get("fatigue_rate", getattr(cfg, "fatigue_rate", 0.01))

    return cfg


def run_one(params, seed, duration, tau, noise):
    set_seed(seed)
    cfg = make_config(params, duration)
    sim = SurvivalSimulation(cfg, tau=tau, perceptual_noise=noise)
    return sim.run()


def validate_params(params, args):
    results = []
    labels = []

    for seed in VALIDATION_SEEDS:
        for rep in range(args.repeats):
            run_seed = seed * 1000 + rep

            result = run_one(
                params=params,
                seed=run_seed,
                duration=args.duration,
                tau=args.tau,
                noise=args.perceptual_noise,
            )

            result["base_seed"] = seed
            result["repeat"] = rep + 1
            result["run_seed"] = run_seed

            results.append(result)
            labels.append(f"{seed}-r{rep + 1}")

    return results, labels, summarize_repeats(results, args.duration)


def is_valid_condition(name, result):
    if name == "balanced":
        t = SELECTION_TARGETS["balanced"]
        return (
            result["final_pop"] >= t["min_final_pop"]
            and t["energy_low"] <= safe(result["tail_mean_energy"]) <= t["energy_high"]
            and safe(result["tail_energy_sd"], nan=1.0) <= t["max_tail_sd"]
            and abs(safe(result["tail_energy_slope"])) <= t["max_abs_energy_slope"]
            and abs(safe(result["tail_pop_slope"])) <= t["max_abs_pop_slope"]
        )

    if name == "easy":
        t = SELECTION_TARGETS["easy"]
        return (
            result["final_pop"] >= t["min_final_pop"]
            and safe(result["tail_mean_energy"]) >= t["min_energy"]
            and safe(result["tail_energy_sd"], nan=1.0) <= t["max_tail_sd"]
        )

    if name == "harsh":
        t = SELECTION_TARGETS["harsh"]
        return (
            t["min_final_pop"] <= result["final_pop"] <= t["max_final_pop"]
            and t["energy_low"] <= safe(result["tail_mean_energy"]) <= t["energy_high"]
        )

    return False


def strict_sort_key(name, record):
    r = record["result"]
    p = record["params"]

    if name == "balanced":
        t = SELECTION_TARGETS["balanced"]
        return (
            p["init_food"],
            abs(safe(r["tail_mean_energy"]) - t["target_energy"]),
            safe(r["tail_energy_sd"], nan=1.0),
            abs(r["final_pop"] - INIT_MOTHERS),
            p["rest_recovery"],
        )

    if name == "easy":
        return (
            -safe(r["tail_mean_energy"]),
            safe(r["tail_energy_sd"], nan=1.0),
            -r["final_pop"],
            -p["init_food"],
            p["rest_recovery"],
        )

    if name == "harsh":
        t = SELECTION_TARGETS["harsh"]
        return (
            abs(r["final_pop"] - t["target_pop"]),
            abs(safe(r["tail_mean_energy"]) - t["target_energy"]),
            p["init_food"],
            safe(r["tail_energy_sd"], nan=1.0),
            p["rest_recovery"],
        )

    return (999,)


def fallback_sort_key(name, record):
    r = record["result"]
    p = record["params"]

    if name == "balanced":
        t = SELECTION_TARGETS["balanced"]
        return (
            max(0.0, t["min_final_pop"] - r["final_pop"]),
            p["init_food"],
            abs(safe(r["tail_mean_energy"]) - t["target_energy"]),
            safe(r["tail_energy_sd"], nan=1.0),
        )

    if name == "easy":
        t = SELECTION_TARGETS["easy"]
        return (
            max(0.0, t["min_final_pop"] - r["final_pop"]),
            max(0.0, t["min_energy"] - safe(r["tail_mean_energy"])),
            safe(r["tail_energy_sd"], nan=1.0),
            -p["init_food"],
        )

    if name == "harsh":
        t = SELECTION_TARGETS["harsh"]

        if r["final_pop"] < t["min_final_pop"]:
            pop_gap = t["min_final_pop"] - r["final_pop"]
        elif r["final_pop"] > t["max_final_pop"]:
            pop_gap = r["final_pop"] - t["max_final_pop"]
        else:
            pop_gap = 0.0

        return (
            pop_gap,
            abs(r["final_pop"] - t["target_pop"]),
            abs(safe(r["tail_mean_energy"]) - t["target_energy"]),
            p["init_food"],
        )

    return (999,)


def build_validation_pool(name, sweep_records):
    valid = [r for r in sweep_records if is_valid_condition(name, r["result"])]

    if valid:
        return sorted(valid, key=lambda r: strict_sort_key(name, r))

    if name == "balanced":
        t = SELECTION_TARGETS["balanced"]
        relaxed = [
            r for r in sweep_records
            if r["result"]["final_pop"] >= t["min_final_pop"] - 1.0
            and t["energy_low"] - 0.05
            <= safe(r["result"]["tail_mean_energy"])
            <= t["energy_high"] + 0.05
        ]

    elif name == "easy":
        t = SELECTION_TARGETS["easy"]
        relaxed = [
            r for r in sweep_records
            if r["result"]["final_pop"] >= t["min_final_pop"] - 1.0
            and safe(r["result"]["tail_mean_energy"]) >= t["min_energy"] - 0.05
        ]

    elif name == "harsh":
        t = SELECTION_TARGETS["harsh"]
        relaxed = [
            r for r in sweep_records
            if t["min_final_pop"] - 1.0
            <= r["result"]["final_pop"]
            <= t["max_final_pop"] + 3.0
        ]

    else:
        relaxed = []

    if relaxed:
        return sorted(relaxed, key=lambda r: fallback_sort_key(name, r))

    return sorted(sweep_records, key=lambda r: fallback_sort_key(name, r))


def select_condition_by_validation(name, sweep_records, args):
    pool = build_validation_pool(name, sweep_records)

    if not pool:
        raise RuntimeError(f"No candidates available for {name} validation.")

    print(f"\nSelecting {name.upper()} using validation-first rule.")

    best_fallback = None
    checked = []

    for idx, rec in enumerate(pool, start=1):
        params = dict(rec["params"])
        params["name"] = name

        results, labels, validation_summary = validate_params(params, args)

        candidate = {
            "params": params,
            "result": validation_summary,
            "sweep_summary": rec["result"],
            "validation_results": results,
            "validation_labels": labels,
            "selection_status": (
                "validated_pass"
                if is_valid_condition(name, validation_summary)
                else "validated_fail"
            ),
        }

        checked.append(candidate)

        print(
            f"  {name.upper()} candidate {idx:03d}/{len(pool)} | "
            f"food={params['init_food']} | rest={params['rest_recovery']} | "
            f"val_pop={validation_summary['final_pop']:.2f}/15 | "
            f"tailE={validation_summary['tail_mean_energy']:.3f} ± "
            f"{validation_summary['tail_energy_sd']:.3f}"
        )

        if best_fallback is None or fallback_sort_key(name, candidate) < fallback_sort_key(name, best_fallback):
            best_fallback = candidate

        if is_valid_condition(name, validation_summary):
            print(f"  -> {name.upper()} selected from validation PASS.")
            return candidate, checked

    if best_fallback is None:
        raise RuntimeError(f"{name.upper()} validation failed before creating fallback.")

    print(f"\nWARNING: No {name.upper()} candidate passed strict validation.")
    print("Fallback selected by closest validation result. Check JSON before reporting.")

    best_fallback["selection_status"] = "fallback_no_strict_validation_pass"
    best_fallback["params"]["name"] = name

    return best_fallback, checked


def build_validation_summary(results):
    return [
        {
            "seed": r["base_seed"],
            "repeat": r["repeat"],
            "run_seed": r["run_seed"],
            "final_pop": r["final_pop"],
            "mean_energy": r["mean_energy"],
            "final_energy": r["final_energy"],
        }
        for r in results
    ]


def run_experiment(args):
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir = os.path.join(
        PROJECT_ROOT,
        "outputs",
        "phase2_survival_minimal",
        f"{ts}_validation_selected_baselines",
    )
    os.makedirs(out_dir, exist_ok=True)

    print(f"Phase 2 Baseline Calibration - Mode: {args.mode}")
    print(f"Output dir: {out_dir}")
    print(f"Duration: {args.duration} | Tau: {args.tau}")
    print(f"Perceptual noise: {args.perceptual_noise}")
    print(f"Repeats: {args.repeats}")

    if args.mode == "single":
        name = "single"
        params = candidate_configs(mode="single")[0]
        results, labels, val_summary = validate_params(params, args)

        plot_multiseed_condition(
            name=name,
            results=results,
            params=params,
            run_labels=labels,
            duration=args.duration,
            out_dir=out_dir,
        )
        save_validation_csv(name, results, out_dir)

        summary = {
            name: {
                "selected_config": params,
                "selection_status": "single_mode",
                "validation_summary": val_summary,
                "validation_runs": build_validation_summary(results),
            }
        }

        save_summary_json(summary, out_dir)

        print(f"\nDone. Outputs saved to: {out_dir}")
        print("Generated plots:")
        print("  - validation_single.png")
        print("Generated logs:")
        print("  - validation_single.csv")
        print("  - auto_baseline_summary.json")
        return

    configs = candidate_configs(mode="sweep")
    sweep_records = []

    print(f"\nStep 1: Auto sweep | Total configs: {len(configs)}")
    print(f"Total sweep runs: {len(configs) * args.repeats}")

    for idx, params in enumerate(configs, start=1):
        repeat_results = []

        for rep in range(args.repeats):
            sweep_run_seed = DEFAULT_SWEEP_SEED_BASE + rep
            res = run_one(
                params=params,
                seed=sweep_run_seed,
                duration=args.duration,
                tau=args.tau,
                noise=args.perceptual_noise,
            )
            repeat_results.append(res)

        summary_result = summarize_repeats(repeat_results, args.duration)

        sweep_records.append(
            {
                "params": dict(params),
                "result": summary_result,
            }
        )

        if idx % 20 == 0 or idx == len(configs):
            print(
                f"  [{idx:03d}/{len(configs)}] "
                f"avg_pop={summary_result['final_pop']:4.1f}/15 | "
                f"tailE={summary_result['tail_mean_energy']:.3f} ± "
                f"{summary_result['tail_energy_sd']:.3f}"
            )

    print("\nStep 2: Validation-first selection for all conditions")

    selected = {}
    traces = {}

    for name in ["balanced", "easy", "harsh"]:
        selected[name], traces[name] = select_condition_by_validation(name, sweep_records, args)

    print("\nFinal selected conditions:")
    for name, rec in selected.items():
        print(
            f"{name.upper()}: {rec['result']} | "
            f"config={rec['params']} | "
            f"status={rec['selection_status']}"
        )

    print("\nStep 3: Plot and save validation outputs")

    summary = {}

    for name, rec in selected.items():
        results = rec["validation_results"]
        labels = rec["validation_labels"]
        params = rec["params"]

        print_validation_runs(name, results)

        plot_multiseed_condition(
            name=name,
            results=results,
            params=params,
            run_labels=labels,
            duration=args.duration,
            out_dir=out_dir,
        )
        save_validation_csv(name, results, out_dir)

        summary[name] = {
            "selected_config": params,
            "selection_status": rec["selection_status"],
            "sweep_summary": rec["sweep_summary"],
            "validation_summary": rec["result"],
            "validation_runs": build_validation_summary(results),
        }

    summary["_candidate_validation_trace"] = {
        name: [
            {
                "selected_config": r["params"],
                "selection_status": r["selection_status"],
                "sweep_summary": r["sweep_summary"],
                "validation_summary": r["result"],
            }
            for r in trace
        ]
        for name, trace in traces.items()
    }

    save_summary_json(summary, out_dir)

    print(f"\nDone. Outputs saved to: {out_dir}")
    print("Generated plots:")
    print("  - validation_balanced.png")
    print("  - validation_easy.png")
    print("  - validation_harsh.png")
    print("Generated logs:")
    print("  - validation_balanced.csv")
    print("  - validation_easy.csv")
    print("  - validation_harsh.csv")
    print("  - auto_baseline_summary.json")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--duration", type=int, default=1000)
    parser.add_argument("--tau", type=float, default=0.1)
    parser.add_argument("--perceptual_noise", type=float, default=0.1)
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--mode", type=str, choices=["sweep", "single"], default="sweep")
    args = parser.parse_args()

    run_experiment(args)