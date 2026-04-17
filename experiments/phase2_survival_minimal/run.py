"""
experiments/phase2_survival_minimal/run.py

Phase 2 Survival-Minimal Baseline Calibration.

This version uses MotherAgent.choose_motivation() instead of defining
motivation logic directly inside run.py.

Decision logic:
  MotherAgent environmental cue × genome weight → softmax motivation

Phase 2:
  - Mother only
  - No child
  - No care
  - No reproduction
  - No mutation
  - No plasticity

Motivation:
  - FORAGE
  - SELF

Action:
  - MOVE
  - PICK
  - EAT
  - REST

Usage:
  python experiments/phase2_survival_minimal/run.py --mode sweep --duration 1000 --repeats 3
  python experiments/phase2_survival_minimal/run.py --mode single --duration 1000 --repeats 10
  python experiments/phase2_survival_minimal/run.py --mode sweep --duration 1000 --repeats 3 --tau 0.1 --perceptual_noise 0.1
"""

import sys
import os
import argparse
import random
from datetime import datetime

import numpy as np
from concurrent.futures import ProcessPoolExecutor

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
    BALANCED_BASELINE,
    SENSITIVITY_SWEEPS,
    TAIL_WINDOW,
    PLOT_SMOOTH_WINDOW,
    ENABLE_ACTION_SELECTION_PLOT,
    ENABLE_MOTIVATION_SELECTION_PLOT,
    ENABLE_FAILED_SELECTION_PLOT,
    ENABLE_STACKED_ACTION_FAILED_PLOT,
    ENABLE_FAILED_SELF_ENERGY_CORRELATION_PLOT,
    ENABLE_FAILED_FORAGE_ENERGY_CORRELATION_PLOT,
    ENABLE_RATE_SUM_CHECK_PLOT,
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
    plot_rate_sum_check,
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

        self.action_counts = {"MOVE": 0, "PICK": 0, "EAT": 0, "REST": 0}
        self.motivation_counts = {"FORAGE": 0, "SELF": 0}
        self.failed_counts = {"FAILED_FORAGE": 0, "FAILED_SELF": 0}

        self.action_history = []
        self.motivation_history = []
        self.failed_history = []
        self.food_history = []
        self.energy_flow_history = []

        self.spatial_heatmap = np.zeros((config.height, config.width), dtype=float)

    # ============================================================
    # Initialization
    # ============================================================

    def initialize(self):
        food_count = int(self.config.init_food * self.food_mult)

        for i in range(self.config.init_mothers):
            x, y = self._random_free_pos()

            genome = Genome(
                care_weight=0.0,
                forage_weight=getattr(self.config, "forage_weight", 1.0),
                self_weight=getattr(self.config, "self_weight", 1.0),
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

    def _perceived_nearest_food(self, mother):
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

        return nearest, dist_to_food

    def _choose_self_action(self, mother):
        eat_score = 0.0
        if mother.held_food > 0:
            eat_score = 1.5 * (1.0 - mother.energy)

        rest_score = 0.8 * mother.fatigue

        if eat_score <= 0.0 and rest_score <= 0.0:
            return "REST"

        probs = softmax_probs({"EAT": eat_score, "REST": rest_score}, tau=self.tau)
        return np.random.choice(list(probs.keys()), p=list(probs.values()))

    # ============================================================
    # Step
    # ============================================================

    def step(self):
        alive_mothers = [m for m in self.mothers if m.alive]
        random.shuffle(alive_mothers)
        processed_alive_count = len(alive_mothers)

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
            tick_energy_flow["hunger_loss"] += before_hunger - mother.energy

            nearest, dist_to_food = self._perceived_nearest_food(mother)
            perception_radius = getattr(self.config, "perception_radius", DEFAULT_PERCEPTION_RADIUS)

            motivation, _, _ = mother.choose_motivation(
                world=self.world,
                perception_radius=perception_radius,
                tau=self.tau,
                child=None,
                nearest_food=nearest,
                distance_to_food=dist_to_food,
                care_enabled=False,
            )

            if motivation not in tick_motivations:
                motivation = "SELF"

            tick_motivations[motivation] += 1
            self.motivation_counts[motivation] += 1

            executed_action = None

            # -------------------------
            # FORAGE motivation
            # -------------------------
            if motivation == "FORAGE":
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

                        tick_energy_flow["move_loss"] += before_move - mother.energy

                        mother.fatigue = min(1.0, mother.fatigue + self.config.fatigue_rate)

                        self.action_counts["MOVE"] += 1
                        tick_actions["MOVE"] += 1

                        executed_action = "MOVE"

            # -------------------------
            # SELF motivation
            # -------------------------
            elif motivation == "SELF":
                action = self._choose_self_action(mother)

                if action == "EAT" and mother.held_food > 0:
                    before_eat = mother.energy

                    variance = random.uniform(0.8, 1.2)
                    mother.energy = min(1.0, mother.energy + self.config.eat_gain * variance)
                    mother.held_food -= 1

                    tick_energy_flow["eat_gain"] += mother.energy - before_eat

                    self.action_counts["EAT"] += 1
                    tick_actions["EAT"] += 1
                    tick_food["EAT"] += 1

                    executed_action = "EAT"

                else:
                    mother.fatigue = max(0.0, mother.fatigue - self.config.rest_recovery)

                    self.action_counts["REST"] += 1
                    tick_actions["REST"] += 1

                    executed_action = "REST"

            # -------------------------
            # Failed realization
            # -------------------------
            if executed_action is None:
                failed_key = f"FAILED_{motivation}"

                if failed_key in tick_failed:
                    tick_failed[failed_key] += 1
                    self.failed_counts[failed_key] += 1

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

        tick_actions["alive"] = processed_alive_count
        tick_motivations["alive"] = processed_alive_count
        tick_failed["alive"] = processed_alive_count
        tick_food["alive"] = processed_alive_count
        tick_food["food_available"] = len(self.world.food_positions)
        tick_energy_flow["alive"] = processed_alive_count

        self.action_history.append(tick_actions)
        self.motivation_history.append(tick_motivations)
        self.failed_history.append(tick_failed)
        self.food_history.append(tick_food)
        self.energy_flow_history.append(tick_energy_flow)

    # ============================================================
    # Run
    # ============================================================

    def collect_result(self) -> dict:
        """Build and return the result dict from current simulation state.

        Called by run() after the loop, or by the live viewer after it drives
        the loop externally via step().
        """
        final_pop    = sum(1 for m in self.mothers if m.alive)
        mean_energy  = float(np.mean(self.energy_history))  if self.energy_history else 0.0
        final_energy = float(self.energy_history[-1])        if self.energy_history else 0.0

        return {
            "final_pop":          final_pop,
            "mean_energy":        mean_energy,
            "final_energy":       final_energy,
            "energy_history":     self.energy_history,
            "fatigue_history":    self.fatigue_history,
            "population_history": self.population_history,
            "actions":            self.action_counts,
            "motivations":        self.motivation_counts,
            "failed":             self.failed_counts,
            "action_history":     self.action_history,
            "motivation_history": self.motivation_history,
            "failed_history":     self.failed_history,
            "food_history":       self.food_history,
            "energy_flow_history":self.energy_flow_history,
            "spatial_heatmap":    self.spatial_heatmap,
        }

    def run(self):
        self.initialize()

        for t in range(self.config.max_ticks):
            self.tick = t
            self.step()

            if not any(m.alive for m in self.mothers):
                break

        return self.collect_result()


# ============================================================
# Experiment utilities
# ============================================================

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

    cfg.fatigue_rate = params.get("fatigue_rate", getattr(cfg, "fatigue_rate", 0.01))

    cfg.forage_weight = params.get("forage_weight", 1.0)
    cfg.self_weight = params.get("self_weight", 1.0)
    cfg.care_weight = 0.0

    cfg.children_enabled = False
    cfg.care_enabled = False
    cfg.plasticity_enabled = False
    cfg.reproduction_enabled = False

    return cfg


def run_one(params, seed, duration, tau, noise):
    set_seed(seed)
    cfg = make_config(params, duration)
    sim = SurvivalSimulation(cfg, tau=tau, perceptual_noise=noise)
    return sim.run()


def _run_task(task):
    """Top-level wrapper required for ProcessPoolExecutor pickling."""
    params, seed, duration, tau, noise = task
    return run_one(params, seed, duration, tau, noise)


def _n_workers(w: int) -> int:
    if w == 0:
        return os.cpu_count() or 1
    return max(1, w)


def validate_params(params, args, workers: int = 1):
    tasks = [
        (params, seed * 1000 + rep, args.duration, args.tau, args.perceptual_noise)
        for seed in VALIDATION_SEEDS
        for rep in range(args.repeats)
    ]

    if workers <= 1:
        raw = [_run_task(t) for t in tasks]
    else:
        with ProcessPoolExecutor(max_workers=workers) as pool:
            raw = list(pool.map(_run_task, tasks))

    results, labels = [], []
    for flat_idx, (task, r) in enumerate(zip(tasks, raw)):
        seed_idx  = flat_idx // args.repeats
        rep_idx   = flat_idx  % args.repeats
        base_seed = VALIDATION_SEEDS[seed_idx]
        r["base_seed"] = base_seed
        r["repeat"]    = rep_idx + 1
        r["run_seed"]  = task[1]
        results.append(r)
        labels.append(f"{base_seed}-r{rep_idx + 1}")

    return results, labels, summarize_repeats(results, args.duration)


# ============================================================
# Selection rules
# ============================================================

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


def select_condition_by_validation(name, sweep_records, args, workers: int = 1):
    pool = build_validation_pool(name, sweep_records)

    if not pool:
        raise RuntimeError(f"No candidates available for {name} validation.")

    print(f"\nSelecting {name.upper()} using validation-first rule.")

    best_fallback = None
    checked = []

    for idx, rec in enumerate(pool, start=1):
        params = dict(rec["params"])
        params["name"] = name

        results, labels, validation_summary = validate_params(params, args, workers=workers)

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


# ============================================================
# Output helpers
# ============================================================

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
    
    if ENABLE_RATE_SUM_CHECK_PLOT:
        plot_rate_sum_check(
            name=name,
            results=results,
            duration=args.duration,
            out_dir=out_dir,
        )

    if ENABLE_FAILED_SELF_ENERGY_CORRELATION_PLOT:
        plot_failed_self_energy_correlation(
            name=name,
            results=results,
            duration=args.duration,
            out_dir=out_dir,
            window=PLOT_SMOOTH_WINDOW,
        )

    if ENABLE_FAILED_FORAGE_ENERGY_CORRELATION_PLOT:
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


# ============================================================
# Pipeline helpers
# ============================================================

def _detect_cliff_edge_from_ovat(ovat_all, synthetic_baseline,
                                  surv_lo=0.80, surv_hi=0.95,
                                  energy_lo=0.65, energy_hi=0.75,
                                  min_surv_range=0.20):
    """
    Detect the cliff-edge balanced operating point from OVAT sweeps (N=50).

    For each parameter:
      CLEAR (surv range >= min_surv_range):
        Scan for the last stable point satisfying BOTH dual-metric conditions:
          - survival in [surv_lo, surv_hi]
          - tail energy in [energy_lo, energy_hi]
        Among those, pick the one where the NEXT adjacent x-step shows the
        steepest drop in survival (i.e., the point right at the cliff edge).
        Falls back to max-gradient boundary crossing if no dual-metric point exists.

      UNCLEAR (flat curve — surv range < min_surv_range):
        Retain the synthetic center value. Parameter becomes a secondary axis
        in the Step 4 multi-dimensional grid to expose hidden tipping points.

    Returns (detected_params dict, clarity dict keyed by set_id).
    """
    detected = dict(synthetic_baseline)
    clarity  = {}

    for set_id, data in ovat_all.items():
        key    = SENSITIVITY_SWEEPS[set_id]["key"]
        xs     = np.array([d["param_value"]        for d in data], dtype=float)
        surv   = np.array([d["survival_rate_mean"] for d in data], dtype=float)
        energy = np.array([d["tail_energy_mean"]   for d in data], dtype=float)

        surv_range = float(np.nanmax(surv) - np.nanmin(surv))
        is_clear   = surv_range >= min_surv_range

        if not is_clear:
            justification = f"Flat curve — Δsurvival={surv_range:.3f} < {min_surv_range}"
            # detected[key] already == synthetic_baseline[key] from dict(synthetic_baseline)
        else:
            gradients = np.diff(surv)  # length n-1

            # Find all candidate points satisfying dual-metric boundary conditions
            candidates = []
            for i in range(len(xs)):
                if (surv_lo <= surv[i] <= surv_hi) and (energy_lo <= energy[i] <= energy_hi):
                    drop_next = abs(gradients[i])     if i < len(gradients) else 0.0
                    drop_prev = abs(gradients[i - 1]) if i > 0              else 0.0
                    candidates.append((i, drop_next, drop_prev))

            if candidates:
                # Select candidate with steepest drop at the *next* adjacent step
                best     = max(candidates, key=lambda c: c[1])
                best_i   = best[0]
                edge_val = float(xs[best_i])
                justification = (
                    f"Sharp drop at next step — "
                    f"Δsurv_next={best[1]:.3f} | "
                    f"surv@edge={surv[best_i]:.2f}, energy@edge={energy[best_i]:.2f}"
                )
            else:
                # Fallback: largest absolute gradient — use stable side
                max_grad_i = int(np.argmax(np.abs(gradients)))
                if gradients[max_grad_i] < 0:
                    best_i = max_grad_i               # last stable before drop
                else:
                    best_i = min(max_grad_i + 1, len(xs) - 1)  # first stable after rise
                edge_val = float(xs[best_i])
                justification = (
                    f"Dual-metric band not met; max-gradient fallback — "
                    f"surv={surv[best_i]:.2f}, energy={energy[best_i]:.2f}"
                )

            detected[key] = (
                int(round(edge_val)) if key == "init_food" else round(edge_val, 6)
            )

        clarity[set_id] = {
            "key":           key,
            "is_clear":      is_clear,
            "surv_range":    round(surv_range, 3),
            "detected_val":  detected[key],
            "synthetic_val": float(synthetic_baseline.get(key, 0)),
            "justification": justification,
        }

    return detected, clarity


def _pipeline_multidim_configs(detected_params, clarity, synthetic_baseline):
    """
    Build the multi-dimensional Step 4 validation grid.

    Primary axis  : init_food ±4 steps around the detected cliff-edge center.
    Secondary axes: one axis per UNCLEAR parameter (5 evenly-spaced values from
                    SENSITIVITY_SWEEPS range) to expose hidden tipping points.
    CLEAR params  : locked to their detected cliff-edge values throughout.

    Returns (configs list, description string).
    """
    from itertools import product as iproduct

    unclear_keys = {c["key"] for c in clarity.values() if not c["is_clear"]}
    key_to_setid = {v["key"]: k for k, v in SENSITIVITY_SWEEPS.items()}

    # Base params: synthetic baseline.
    # Combining all CLEAR cliff-edge values simultaneously creates a super-harsh
    # operating point (e.g. high hunger + high move_cost + low eat_gain) that drives
    # total extinction across the whole food axis.  Individual cliff-edge values
    # are reported in Step 3 for reference but should not all be locked at once.
    base_params = dict(synthetic_baseline)

    # Primary axis: init_food — span from harsh to easy zone.
    # Anchor between min(detected, synthetic) and max(detected, synthetic) + buffer
    # so the grid covers all three operating zones.
    center     = int(detected_params.get("init_food", synthetic_baseline["init_food"]))
    synth_food = int(synthetic_baseline["init_food"])
    step       = max(3, max(center, synth_food) // 8)
    food_lo    = max(10, min(center, synth_food) - 4 * step)
    food_hi    = max(center, synth_food) + 4 * step
    food_raw   = np.linspace(food_lo, food_hi, 9)
    food_values = sorted({int(round(v)) for v in food_raw} | {center, synth_food})

    # Secondary axes for UNCLEAR params (excluding init_food — already on primary axis)
    extra_keys   = []
    extra_values = []
    for key in sorted(unclear_keys):
        if key == "init_food":
            continue
        set_id = key_to_setid.get(key)
        if set_id:
            vals    = SENSITIVITY_SWEEPS[set_id]["values"]
            indices = np.linspace(0, len(vals) - 1, min(5, len(vals)), dtype=int)
            extra_keys.append(key)
            extra_values.append([vals[i] for i in indices])

    all_keys   = ["init_food"] + extra_keys
    all_axes   = [food_values] + extra_values

    configs = []
    for combo in iproduct(*all_axes):
        params = dict(base_params)
        for k, v in zip(all_keys, combo):
            params[k] = int(v) if k == "init_food" else float(v)
        params["name"] = "candidate"
        configs.append(params)

    extra_desc = (
        " × ".join(f"{len(v)} {k}" for k, v in zip(extra_keys, extra_values))
        if extra_keys else "no UNCLEAR secondary axes"
    )
    desc = f"{len(food_values)} food × ({extra_desc}) = {len(configs)} configs"
    return configs, desc


def _penalty_score(name, result):
    """
    Penalty score for condition selection (lower = better).

    Hard constraint violations add +1000 per unit deviation.
    Soft terms penalize proportional distance from target.

    Balanced : target ~14/15 survival, energy ~0.70, flat energy slope.
    Easy     : target ~15/15 survival, energy ≥ 0.85.
    Harsh    : target ~2–5/15 survival, energy ≤ 0.40.
    """
    surv    = result["final_pop"] / INIT_MOTHERS
    energy  = safe(result["tail_mean_energy"])
    e_sd    = safe(result["tail_energy_sd"], nan=1.0)
    e_slope = abs(safe(result.get("tail_energy_slope", 0.0)))

    HARD  = 1000.0
    score = 0.0

    if name == "balanced":
        if surv < 10.5 / INIT_MOTHERS:
            score += HARD * (10.5 / INIT_MOTHERS - surv) * 15
        if energy < 0.55:
            score += HARD * (0.55 - energy) * 10
        elif energy > 0.82:
            score += HARD * (energy - 0.85) * 10
        score += abs(surv - 14.0 / INIT_MOTHERS) * 30.0
        score += abs(energy - 0.70) * 30.0
        score += e_slope * 10_000.0   # slope is heavily penalized
        score += e_sd * 10.0

    elif name == "easy":
        if surv < 13.5 / INIT_MOTHERS:
            score += HARD * (13.5 / INIT_MOTHERS - surv) * 15
        if energy < 0.75:
            score += HARD * (0.75 - energy) * 10
        score += abs(surv - 1.0) * 20.0
        score += max(0.0, 0.85 - energy) * 40.0
        score += e_sd * 5.0

    elif name == "harsh":
        if surv < 2.0 / INIT_MOTHERS:
            score += HARD * (2.0 / INIT_MOTHERS - surv) * 15
        elif surv > 5.0 / INIT_MOTHERS:
            score += HARD * (surv - 5.0 / INIT_MOTHERS) * 15
        if energy > 0.40:
            score += HARD * (energy - 0.40) * 10
        score += abs(surv - 3.5 / INIT_MOTHERS) * 30.0
        score += abs(energy - 0.35) * 30.0

    return score


def select_by_penalty_score(name, sweep_records):
    """
    Select the best configuration for `name` using penalty scoring.

    Returns (best_record, best_score, all_scored_list).
    all_scored_list is sorted best → worst: [(score, record), ...].
    """
    scored = [(  _penalty_score(name, rec["result"]), rec) for rec in sweep_records]
    scored.sort(key=lambda x: x[0])
    if not scored:
        raise RuntimeError(f"No candidates for {name}")
    best_score, best_rec = scored[0]
    return best_rec, best_score, scored


def _pipeline_validate(params, n_seeds, duration, tau, noise, workers):
    """Run N independent seeds for diagnostic validation. Returns (results, labels, summary)."""
    seeds = list(range(42, 42 + n_seeds))
    tasks = [(dict(params), seed, duration, tau, noise) for seed in seeds]

    if workers <= 1:
        raw = [_run_task(t) for t in tasks]
    else:
        with ProcessPoolExecutor(max_workers=workers) as pool:
            raw = list(pool.map(_run_task, tasks))

    results = []
    for seed, r in zip(seeds, raw):
        r["base_seed"] = seed
        r["repeat"]    = 1
        r["run_seed"]  = seed
        results.append(r)

    labels  = [str(s) for s in seeds]
    summary = summarize_repeats(results, duration)
    return results, labels, summary


def _run_pipeline(args, out_dir, n_workers):
    from experiments.phase2_survival_minimal.sensitivity_sweep import (
        run_set,
        plot_sensitivity_map,
        save_csv as save_sens_csv,
    )

    N_SEEDS       = 50
    pipeline_seeds = list(range(42, 42 + N_SEEDS))

    # ── Step 1: Synthetic baseline ────────────────────────────────────────────
    synthetic = dict(BALANCED_BASELINE)
    print("\n" + "=" * 70)
    print("PIPELINE Step 1 — Synthetic Starting Baseline (BALANCED_BASELINE)")
    print("=" * 70)
    eco_keys = ("hunger_rate", "move_cost", "eat_gain", "init_food", "rest_recovery")
    for k in eco_keys:
        print(f"  {k:<20} = {synthetic[k]}")

    # ── Step 2: OVAT (N=50 seeds per sweep point) ─────────────────────────────
    ovat_dir = os.path.join(out_dir, "sensitivity_ovat")
    os.makedirs(ovat_dir, exist_ok=True)

    print("\n" + "=" * 70)
    print(f"PIPELINE Step 2 — OVAT Sensitivity Sweep  (N={N_SEEDS} seeds per point)")
    print("=" * 70)
    print(f"  Duration={args.duration}  Workers={n_workers}")

    ovat_all = {}
    for set_id in "ABCDE":
        sweep_def = SENSITIVITY_SWEEPS[set_id]
        key       = sweep_def["key"]
        n_vals    = len(sweep_def["values"])
        print(f"\n── Set {set_id}: '{key}'  ({n_vals} values × {N_SEEDS} seeds = {n_vals * N_SEEDS} runs) ──")
        results = run_set(
            set_id=set_id,
            sweep=sweep_def,
            baseline=synthetic,
            seeds=pipeline_seeds,
            repeats=1,
            duration=args.duration,
            tau=args.tau,
            noise=args.perceptual_noise,
            tail_window=TAIL_WINDOW,
            workers=n_workers,
        )
        ovat_all[set_id] = results
        save_sens_csv(results, os.path.join(ovat_dir, f"set_{set_id}_{key}.csv"))

    plot_sensitivity_map(ovat_all, synthetic, ovat_dir, hide_keys=set())
    print(f"\n  OVAT plots saved → {ovat_dir}")

    # ── Step 3: Dual-metric cliff-edge detection ───────────────────────────────
    print("\n" + "=" * 70)
    print("PIPELINE Step 3 — Dual-Metric Cliff-Edge Detection")
    print("=" * 70)
    detected, clarity = _detect_cliff_edge_from_ovat(ovat_all, synthetic)

    hdr = f"  {'Parameter':<18}  {'Synthetic':>10}  {'Detected':>10}  {'Status':<8}  Justification"
    print(hdr)
    print("  " + "-" * (len(hdr) - 2))
    for set_id in "ABCDE":
        c      = clarity[set_id]
        status = "CLEAR" if c["is_clear"] else "UNCLEAR"
        print(
            f"  {c['key']:<18}  {c['synthetic_val']:>10g}  "
            f"{c['detected_val']:>10g}  {status:<8}  {c['justification']}"
        )

    unclear_keys_list = [c["key"] for c in clarity.values() if not c["is_clear"]]
    if unclear_keys_list:
        print(f"\n  NOTE: {unclear_keys_list} are UNCLEAR (flat curves).")
        print( "  Synthetic values retained for CLEAR locking.")
        print( "  These become secondary axes in Step 4 to expose hidden tipping points.")

    # ── Step 4: Multi-dimensional validation grid (N=50 per config) ───────────
    print("\n" + "=" * 70)
    print(f"PIPELINE Step 4 — Multi-Dimensional Validation Grid  (N={N_SEEDS} per config)")
    print("=" * 70)

    sweep_configs, grid_desc = _pipeline_multidim_configs(detected, clarity, synthetic)
    total_runs = len(sweep_configs) * N_SEEDS
    print(f"  Grid    : {grid_desc}")
    print(f"  Runs    : {total_runs}  ({len(sweep_configs)} configs × {N_SEEDS} seeds)")
    print(f"  CLEAR params locked to cliff-edge values; UNCLEAR varied across plausible range")

    sweep_tasks = [
        (dict(p), seed, args.duration, args.tau, args.perceptual_noise)
        for p in sweep_configs
        for seed in pipeline_seeds
    ]

    if n_workers <= 1:
        flat_results = [_run_task(t) for t in sweep_tasks]
    else:
        with ProcessPoolExecutor(max_workers=n_workers) as pool:
            flat_results = list(pool.map(_run_task, sweep_tasks))

    step4_records = []
    print(f"\n  {'#':>4}  {'food':>5}  {'surv':>6}  {'tailE':>7}  {'E±':>6}  {'slope':>9}")
    for idx, params in enumerate(sweep_configs):
        reps = flat_results[idx * N_SEEDS : (idx + 1) * N_SEEDS]
        sr   = summarize_repeats(reps, args.duration)
        step4_records.append({"params": dict(params), "result": sr})
        print(
            f"  {idx + 1:>4}  {params['init_food']:>5}  "
            f"{sr['final_pop'] / INIT_MOTHERS:>6.2f}  "
            f"{sr['tail_mean_energy']:>7.3f}  "
            f"{sr['tail_energy_sd']:>6.3f}  "
            f"{sr.get('tail_energy_slope', 0.0):>9.6f}"
        )

    # ── Step 5: Penalty scoring → final ecological baselines ──────────────────
    print("\n" + "=" * 70)
    print("PIPELINE Step 5 — Automated Selection via Penalty Scoring")
    print("=" * 70)
    print(f"  {'Condition':<12}  {'Score':>9}  {'Surv':>6}  {'TailE':>7}  {'E±':>6}  Config")
    print(f"  {'-'*12}  {'-'*9}  {'-'*6}  {'-'*7}  {'-'*6}  {'-'*40}")

    selected   = {}
    scored_all = {}
    for cond_name in ["balanced", "easy", "harsh"]:
        best_rec, best_score, all_scored = select_by_penalty_score(cond_name, step4_records)
        selected[cond_name]   = best_rec
        scored_all[cond_name] = all_scored
        r = best_rec["result"]
        p = best_rec["params"]
        cfg_str = "  ".join(
            f"{k}={p[k]:g}"
            for k in ("hunger_rate", "move_cost", "eat_gain", "init_food", "rest_recovery")
        )
        print(
            f"  {cond_name.upper():<12}  {best_score:>9.2f}  "
            f"{r['final_pop'] / INIT_MOTHERS:>6.2f}  "
            f"{r['tail_mean_energy']:>7.3f}  "
            f"{r['tail_energy_sd']:>6.3f}  {cfg_str}"
        )

    print("\n  ── Final Ecological Baselines (exact genome + environment) ──")
    for cond_name, rec in selected.items():
        print(f"\n  [{cond_name.upper()}]")
        for k, v in sorted(rec["params"].items()):
            if k != "name":
                print(f"    {k:<22} = {v}")

    # ── Step 6: Diagnostic report generation (N=50 validation seeds) ──────────
    print("\n" + "=" * 70)
    print(f"PIPELINE Step 6 — Diagnostic Report Generation  (N={N_SEEDS} validation seeds)")
    print("=" * 70)

    summary = {}
    for cond_name, rec in selected.items():
        params = dict(rec["params"])
        params["name"] = cond_name
        print(f"\n  Validating + plotting {cond_name.upper()} ...")

        val_results, val_labels, val_summary = _pipeline_validate(
            params, N_SEEDS, args.duration, args.tau, args.perceptual_noise, n_workers
        )

        print_validation_runs(cond_name, val_results)
        generate_diagnostic_plots(
            name=cond_name,
            results=val_results,
            params=params,
            labels=val_labels,
            args=args,
            out_dir=out_dir,
        )
        save_validation_csv(cond_name, val_results, out_dir)

        final_score = _penalty_score(cond_name, val_summary)
        summary[cond_name] = {
            "selected_config":    params,
            "penalty_score":      final_score,
            "sweep_summary":      rec["result"],
            "validation_summary": val_summary,
            "validation_runs":    build_validation_summary(val_results),
        }

    summary["_penalty_score_trace"] = {
        cond: [
            {"params": rec["params"], "score": score, "result": rec["result"]}
            for score, rec in all_scored[:20]
        ]
        for cond, all_scored in scored_all.items()
    }

    summary["_pipeline_meta"] = {
        "n_seeds":          N_SEEDS,
        "synthetic_baseline": {k: v for k, v in synthetic.items() if k != "name"},
        "detected_balanced":  {k: v for k, v in detected.items()  if k != "name"},
        "edge_clarity":       {c["key"]: c for c in clarity.values()},
        "ovat_dir":           ovat_dir,
        "step4_grid_desc":    grid_desc,
        "step4_n_configs":    len(sweep_configs),
    }

    save_summary_json(summary, out_dir)
    print(f"\nDone. All outputs saved to: {out_dir}")


# ============================================================
# Main experiment
# ============================================================

def run_experiment(args):
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir = os.path.join(
        PROJECT_ROOT,
        "outputs",
        "phase2_survival_minimal",
        f"{ts}_validation_selected_baselines",
    )
    os.makedirs(out_dir, exist_ok=True)

    n_workers = _n_workers(args.workers)

    print(f"Phase 2 Baseline Calibration - Mode: {args.mode}")
    print(f"Output dir: {out_dir}")
    print(f"Duration: {args.duration} | Tau: {args.tau}")
    print(f"Perceptual noise: {args.perceptual_noise}")
    print(f"Repeats: {args.repeats} | Workers: {n_workers}")

    if args.mode == "pipeline":
        _run_pipeline(args, out_dir, n_workers)
        return

    if args.mode == "single":
        name   = "single"
        params = candidate_configs(mode="single")[0]

        if args.live:
            from experiments.live_viewer import LiveViewer, Phase2LiveProvider

            run_seed = VALIDATION_SEEDS[0] * 1000
            print(f"\nLive mode: seed={VALIDATION_SEEDS[0]}  speed=×{args.speed}")
            set_seed(run_seed)
            cfg = make_config(params, args.duration)
            sim = SurvivalSimulation(cfg, tau=args.tau, perceptual_noise=args.perceptual_noise)
            sim.initialize()

            viewer   = LiveViewer(speed=args.speed, title="Phase 2")
            provider = Phase2LiveProvider(sim, total_ticks=args.duration)
            viewer.run_live(sim, provider)

            r = sim.collect_result()
            r.update(base_seed=VALIDATION_SEEDS[0], repeat=1, run_seed=run_seed)
            results    = [r]
            labels     = [f"{VALIDATION_SEEDS[0]}-r1"]
            val_summary = summarize_repeats(results, args.duration)
            print(f"Live run done: pop={r['final_pop']}/15 | energy={r['final_energy']:.3f}")
        else:
            results, labels, val_summary = validate_params(params, args, workers=n_workers)

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
                "selected_config":   params,
                "selection_status":  "live_mode" if args.live else "single_mode",
                "validation_summary": val_summary,
                "validation_runs":   build_validation_summary(results),
            }
        }

        save_summary_json(summary, out_dir)
        print(f"\nDone. Outputs saved to: {out_dir}")
        return

    configs = candidate_configs(mode="sweep")

    # ── parallel sweep ────────────────────────────────────────────────────────
    sweep_tasks = [
        (dict(params), DEFAULT_SWEEP_SEED_BASE + rep, args.duration, args.tau, args.perceptual_noise)
        for params in configs
        for rep in range(args.repeats)
    ]

    print(
        f"\nStep 1: Auto sweep | {len(configs)} configs × {args.repeats} reps"
        f" = {len(sweep_tasks)} tasks | workers={n_workers}"
    )

    if n_workers <= 1:
        flat_results = [_run_task(t) for t in sweep_tasks]
    else:
        with ProcessPoolExecutor(max_workers=n_workers) as pool:
            flat_results = list(pool.map(_run_task, sweep_tasks))

    sweep_records = []
    for idx, params in enumerate(configs):
        reps           = flat_results[idx * args.repeats : (idx + 1) * args.repeats]
        summary_result = summarize_repeats(reps, args.duration)
        sweep_records.append({"params": dict(params), "result": summary_result})

        if idx % 5 == 0 or idx == len(configs) - 1:
            print(
                f"  [{idx + 1:03d}/{len(configs)}] "
                f"avg_pop={summary_result['final_pop']:4.1f}/15 | "
                f"tailE={summary_result['tail_mean_energy']:.3f} ± "
                f"{summary_result['tail_energy_sd']:.3f}"
            )

    print("\nStep 2: Validation-first selection for all conditions")

    selected = {}
    traces = {}

    for name in ["balanced", "easy", "harsh"]:
        selected[name], traces[name] = select_condition_by_validation(name, sweep_records, args, workers=n_workers)

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


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--duration", type=int, default=1000)
    parser.add_argument("--tau", type=float, default=0.1)
    parser.add_argument("--perceptual_noise", type=float, default=0.1)
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--mode", type=str, choices=["sweep", "single", "pipeline"], default="sweep")
    parser.add_argument("--workers", type=int, default=1,
                        help="Parallel workers (0=auto/cpu_count, 1=sequential)")
    parser.add_argument("--live", action="store_true", default=False,
                        help="Open live viewer window (single mode only)")
    parser.add_argument("--speed", type=int, choices=[1, 2, 5], default=1,
                        help="Live viewer speed multiplier")
    args = parser.parse_args()

    run_experiment(args)