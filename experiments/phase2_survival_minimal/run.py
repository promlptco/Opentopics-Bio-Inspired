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
    ├── validation_<name>.png
    ├── action_selection_<name>.png
    ├── motivation_selection_<name>.png
    ├── failed_selection_<name>.png
    ├── stacked_action_failed_<name>.png
    ├── correlation_failed_self_energy_<name>.png
    ├── state_space_energy_action_<name>.png
    ├── food_consumption_rate_<name>.png
    ├── spatial_heatmap_population_<name>.png
    ├── energy_expenditure_breakdown_<name>.png
    ├── validation_<name>.csv
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
    PLOT_SMOOTH_WINDOW,
    ENABLE_ACTION_SELECTION_PLOT,
    ENABLE_MOTIVATION_SELECTION_PLOT,
    ENABLE_FAILED_SELECTION_PLOT,
    ENABLE_STACKED_ACTION_FAILED_PLOT,
    ENABLE_FAILED_SELF_ENERGY_CORRELATION_PLOT,
    ENABLE_STATE_SPACE_ENERGY_ACTION_PLOT,
    ENABLE_FOOD_CONSUMPTION_PLOT,
    ENABLE_SPATIAL_HEATMAP_PLOT,
    ENABLE_ENERGY_EXPENDITURE_PLOT,
    ENABLE_HOMEOSTATIC_BALANCE_PLOT,
    candidate_configs,
)

from experiments.phase2_survival_minimal.plot import (
    safe,
    summarize_repeats,
    plot_multiseed_condition,
    plot_action_selection_over_time,
    plot_motivation_selection_over_time,
    plot_failed_selection_over_time,
    plot_stacked_action_failed_over_time,
    plot_failed_self_energy_correlation,
    plot_failed_forage_energy_correlation,
    plot_state_space_energy_action,
    plot_food_consumption_over_time,
    plot_spatial_heatmap_population,
    plot_energy_expenditure_breakdown,
    plot_homeostatic_balance,
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
        self.fatigue_history = []
        self.population_history = []

        # Episode-level totals.
        self.action_counts = {"MOVE": 0, "PICK": 0, "EAT": 0, "REST": 0}
        self.motivation_counts = {"FORAGE": 0, "SELF": 0}
        self.failed_counts = {"FAILED_FORAGE": 0, "FAILED_SELF": 0}

        # Per-tick logs for over-time plots.
        self.action_history = []
        self.motivation_history = []
        self.failed_history = []
        self.food_history = []
        self.energy_flow_history = []

        # Spatial visit map. Shape is [height, width].
        # We accumulate visits at the end of each tick across all alive mothers.
        self.spatial_heatmap = np.zeros((config.height, config.width), dtype=float)

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

        tick_actions = {"MOVE": 0, "PICK": 0, "EAT": 0, "REST": 0}
        tick_motivations = {"FORAGE": 0, "SELF": 0}
        tick_failed = {"FAILED_FORAGE": 0, "FAILED_SELF": 0}

        tick_food = {
            "PICK": 0,
            "EAT": 0,
            "food_available": len(self.world.food_positions),
        }

        tick_energy_flow = {
            "hunger_loss": 0.0,
            "move_loss": 0.0,
            "eat_gain": 0.0,
            "net_energy_change": 0.0,
        }

        for mother in alive_mothers:
            energy_before_agent = mother.energy

            mother.tick_age()

            before_hunger = mother.energy
            mother.energy = max(0.0, mother.energy - self.config.hunger_rate)
            hunger_loss = before_hunger - mother.energy
            tick_energy_flow["hunger_loss"] += hunger_loss

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

            if selection == "FORAGE":
                selected_motivation = "FORAGE"
                tick_motivations["FORAGE"] += 1
                self.motivation_counts["FORAGE"] += 1
            else:
                selected_motivation = "SELF"
                tick_motivations["SELF"] += 1
                self.motivation_counts["SELF"] += 1

            executed_action = None

            if selection == "EAT" and mother.held_food > 0:
                before_eat = mother.energy
                variance = random.uniform(0.8, 1.2)
                mother.energy = min(1.0, mother.energy + self.config.eat_gain * variance)
                mother.held_food -= 1

                eat_gain = mother.energy - before_eat
                tick_energy_flow["eat_gain"] += eat_gain

                self.action_counts["EAT"] += 1
                tick_actions["EAT"] += 1
                tick_food["EAT"] += 1
                executed_action = "EAT"

            elif selection == "REST":
                mother.fatigue = max(0.0, mother.fatigue - self.config.rest_recovery)

                self.action_counts["REST"] += 1
                tick_actions["REST"] += 1
                executed_action = "REST"

            elif selection == "FORAGE":
                if mother.pos in self.world.food_positions:
                    self.world.remove_food(*mother.pos)
                    mother.held_food += 1

                    self.action_counts["PICK"] += 1
                    tick_actions["PICK"] += 1
                    tick_food["PICK"] += 1
                    executed_action = "PICK"

                elif nearest:
                    new_pos = self.world.get_step_toward(mother.pos, nearest)
                    if self.world.update_position(mother, new_pos):
                        before_move = mother.energy
                        mother.energy = max(0.0, mother.energy - self.config.move_cost)
                        move_loss = before_move - mother.energy
                        tick_energy_flow["move_loss"] += move_loss

                        mother.fatigue = min(1.0, mother.fatigue + self.config.fatigue_rate)

                        self.action_counts["MOVE"] += 1
                        tick_actions["MOVE"] += 1
                        executed_action = "MOVE"

            if executed_action is None:
                if selected_motivation == "FORAGE":
                    tick_failed["FAILED_FORAGE"] += 1
                    self.failed_counts["FAILED_FORAGE"] += 1
                else:
                    tick_failed["FAILED_SELF"] += 1
                    self.failed_counts["FAILED_SELF"] += 1

            if mother.energy <= 0:
                mother.die()
                self.world.remove_entity(mother.id)

            tick_energy_flow["net_energy_change"] += mother.energy - energy_before_agent

        target = int(self.config.init_food * self.food_mult)
        if len(self.world.food_positions) < max(1, target // 3):
            self._spawn_food(3)

        alive_now = [m for m in self.mothers if m.alive]
        self.population_history.append(len(alive_now))

        avg_energy = sum(m.energy for m in alive_now) / len(alive_now) if alive_now else 0.0
        avg_fatigue = sum(m.fatigue for m in alive_now) / len(alive_now) if alive_now else 0.0

        self.energy_history.append(avg_energy)
        self.fatigue_history.append(avg_fatigue)

        for mother in alive_now:
            x, y = mother.pos
            if 0 <= x < self.config.width and 0 <= y < self.config.height:
                self.spatial_heatmap[y, x] += 1.0

        alive_count = len(alive_now)

        tick_actions["alive"] = alive_count
        tick_motivations["alive"] = alive_count
        tick_failed["alive"] = alive_count
        tick_food["alive"] = alive_count
        tick_food["food_available"] = len(self.world.food_positions)
        tick_energy_flow["alive"] = alive_count

        self.action_history.append(tick_actions)
        self.motivation_history.append(tick_motivations)
        self.failed_history.append(tick_failed)
        self.food_history.append(tick_food)
        self.energy_flow_history.append(tick_energy_flow)

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
            "fatigue_history": self.fatigue_history,
            "population_history": self.population_history,
            "actions": self.action_counts,
            "motivations": self.motivation_counts,
            "failed": self.failed_counts,
            "action_history": self.action_history,
            "motivation_history": self.motivation_history,
            "failed_history": self.failed_history,
            "food_history": self.food_history,
            "energy_flow_history": self.energy_flow_history,
            "spatial_heatmap": self.spatial_heatmap,
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
            and abs(safe(result.get("tail_energy_slope", 0.0))) <= t.get("max_abs_energy_slope", float("inf"))
            and abs(safe(result.get("tail_pop_slope", 0.0))) <= t.get("max_abs_pop_slope", float("inf"))
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
            "actions": r.get("actions", {}),
            "motivations": r.get("motivations", {}),
            "failed": r.get("failed", {}),
        }
        for r in results
    ]


def generate_diagnostic_plots(name, results, params, labels, args, out_dir):
    plot_multiseed_condition(
        name=name,
        results=results,
        params=params,
        run_labels=labels,
        duration=args.duration,
        out_dir=out_dir,
    )

    if ENABLE_ACTION_SELECTION_PLOT:
        plot_action_selection_over_time(
            name=name,
            results=results,
            duration=args.duration,
            out_dir=out_dir,
            window=PLOT_SMOOTH_WINDOW,
            as_rate=True,
        )

    if ENABLE_MOTIVATION_SELECTION_PLOT:
        plot_motivation_selection_over_time(
            name=name,
            results=results,
            duration=args.duration,
            out_dir=out_dir,
            window=PLOT_SMOOTH_WINDOW,
            as_rate=True,
        )

    if ENABLE_FAILED_SELECTION_PLOT:
        plot_failed_selection_over_time(
            name=name,
            results=results,
            duration=args.duration,
            out_dir=out_dir,
            window=PLOT_SMOOTH_WINDOW,
            as_rate=True,
        )

    if ENABLE_STACKED_ACTION_FAILED_PLOT:
        plot_stacked_action_failed_over_time(
            name=name,
            results=results,
            duration=args.duration,
            out_dir=out_dir,
            window=PLOT_SMOOTH_WINDOW,
            as_rate=True,
        )

    if ENABLE_FAILED_SELF_ENERGY_CORRELATION_PLOT:
        plot_failed_self_energy_correlation(
            name=name,
            results=results,
            duration=args.duration,
            out_dir=out_dir,
            window=PLOT_SMOOTH_WINDOW,
        )
        
        plot_failed_forage_energy_correlation(
            name=name,
            results=results,
            duration=args.duration,
            out_dir=out_dir,
            window=PLOT_SMOOTH_WINDOW,
        )

    if ENABLE_STATE_SPACE_ENERGY_ACTION_PLOT:
        plot_state_space_energy_action(
            name=name,
            results=results,
            duration=args.duration,
            out_dir=out_dir,
            window=PLOT_SMOOTH_WINDOW,
        )

    if ENABLE_FOOD_CONSUMPTION_PLOT:
        plot_food_consumption_over_time(
            name=name,
            results=results,
            duration=args.duration,
            out_dir=out_dir,
            window=PLOT_SMOOTH_WINDOW,
        )

    if ENABLE_SPATIAL_HEATMAP_PLOT:
        plot_spatial_heatmap_population(
            name=name,
            results=results,
            out_dir=out_dir,
        )

    if ENABLE_ENERGY_EXPENDITURE_PLOT:
        plot_energy_expenditure_breakdown(
            name=name,
            results=results,
            out_dir=out_dir,
        )
        
    if ENABLE_HOMEOSTATIC_BALANCE_PLOT:
        plot_homeostatic_balance(
            name=name,
            results=results,
            duration=args.duration,
            out_dir=out_dir,
            window=PLOT_SMOOTH_WINDOW,
        )


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

        generate_diagnostic_plots(
            name=name,
            results=results,
            params=params,
            labels=labels,
            args=args,
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

        generate_diagnostic_plots(
            name=name,
            results=results,
            params=params,
            labels=labels,
            args=args,
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