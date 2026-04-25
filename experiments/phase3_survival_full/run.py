"""
experiments/phase3_survival_full/run.py

Phase 3 Survival-Full: Mother + Child Baseline Validation.

Goal:
  Extend Phase 2 mother-only survival into mother-child survival.
  No reproduction, no mutation, no plasticity.

Motivation domains:
  - FORAGE
  - CARE
  - SELF

Actions:
  - MOVE_FOOD
  - PICK
  - EAT
  - MOVE_CHILD
  - FEED
  - REST

Usage:
  # Run full sweep and validation
  python experiments/phase3_survival_full/run.py --mode sweep --duration 1000 --repeats 3

  # Run one hand-picked config
  python experiments/phase3_survival_full/run.py --mode single --duration 1000 --repeats 10

  # Custom stochasticity / perceptual noise
  python experiments/phase3_survival_full/run.py --mode sweep --duration 1000 --repeats 3 --tau 0.1 --perceptual_noise 0.1

Outputs:
  outputs/phase3_survival_full/<timestamp>_validation_selected_baselines/
    ├── validation_<name>.png
    ├── action_selection_<name>.png
    ├── motivation_selection_<name>.png
    ├── failed_selection_<name>.png
    ├── mother_child_diagnostics_<name>.png
    ├── feed_rate_<name>.png
    ├── spatial_heatmap_<name>.png
    ├── validation_<name>.csv
    └── auto_phase3_summary.json
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
from agents.child import ChildAgent
from evolution.genome import Genome
from utils.experiment import set_seed

from experiments.phase3_survival_full.config import (
    INIT_MOTHERS,
    INITIAL_ENERGY,
    VALIDATION_SEEDS,
    DEFAULT_SWEEP_SEED_BASE,
    DEFAULT_PERCEPTION_RADIUS,
    TAIL_WINDOW,
    SELECTION_TARGETS,
    PLOT_SMOOTH_WINDOW,
    ENABLE_VALIDATION_PLOT,
    ENABLE_ACTION_SELECTION_PLOT,
    ENABLE_MOTIVATION_SELECTION_PLOT,
    ENABLE_FAILED_SELECTION_PLOT,
    ENABLE_MOTHER_CHILD_DIAGNOSTIC_PLOT,
    ENABLE_FEED_RATE_PLOT,
    ENABLE_SPATIAL_HEATMAP_PLOT,
    candidate_configs,
)

from experiments.phase3_survival_full.plot import (
    safe,
    summarize_repeats,
    plot_multiseed_condition,
    plot_action_selection_over_time,
    plot_motivation_selection_over_time,
    plot_failed_selection_over_time,
    plot_mother_child_diagnostics,
    plot_feed_rate_over_time,
    plot_spatial_heatmap,
    print_validation_runs,
    save_summary_json,
    save_validation_csv,
)


class MotherChildSurvivalSimulation:
    def __init__(self, config, tau=0.1, food_mult=1.0, perceptual_noise=0.1):
        self.config = config
        self.tau = tau
        self.food_mult = food_mult
        self.perceptual_noise = perceptual_noise

        self.world = GridWorld(config.width, config.height)

        self.mothers = []
        self.children = []

        self.tick = 0

        self.mother_energy_history = []
        self.mother_population_history = []

        self.child_hunger_history = []
        self.child_distress_history = []
        self.child_population_history = []
        self.mother_child_distance_history = []

        self.action_counts = {
            "MOVE_FOOD": 0,
            "PICK": 0,
            "EAT": 0,
            "MOVE_CHILD": 0,
            "FEED": 0,
            "REST": 0,
        }

        self.motivation_counts = {
            "FORAGE": 0,
            "CARE": 0,
            "SELF": 0,
        }

        self.failed_counts = {
            "FAILED_FORAGE": 0,
            "FAILED_CARE": 0,
            "FAILED_SELF": 0,
        }

        self.action_history = []
        self.motivation_history = []
        self.failed_history = []
        self.feed_history = []
        self.family_history = []

        # Per-agent tick-level log (disabled by default — only used for Phase 3b raster)
        self._agent_log_enabled = False
        self._agent_log = {}  # mother_id -> [action_at_t0, action_at_t1, ...]
        self._agent_order = []

        self.spatial_heatmap_mother = np.zeros((config.height, config.width), dtype=float)
        self.spatial_heatmap_child = np.zeros((config.height, config.width), dtype=float)

    # ============================================================
    # Initialization
    # ============================================================

    def initialize(self):
        food_count = int(self.config.init_food * self.food_mult)

        for i in range(self.config.init_mothers):
            mx, my = self._random_free_pos()

            genome = Genome(
                care_weight=getattr(self.config, "care_weight", 0.85),
                forage_weight=getattr(self.config, "forage_weight", 0.70),
                self_weight=getattr(self.config, "self_weight", 0.30),
                learning_rate=0.0,
                learning_cost=0.0,
            )

            mother = MotherAgent(mx, my, lineage_id=i, generation=0, genome=genome)
            mother.energy = self.config.initial_energy

            child_x, child_y = self._nearby_child_pos(mx, my)
            child = ChildAgent(
                child_x,
                child_y,
                lineage_id=i,
                generation=0,
                mother_id=mother.id,
            )

            mother.own_child_id = child.id

            self.mothers.append(mother)
            self.children.append(child)

            self.world.place_entity(mother)
            self.world.place_entity(child)

        self._spawn_food(food_count)

        if self._agent_log_enabled:
            self._agent_log = {m.id: [] for m in self.mothers}
            self._agent_order = [m.id for m in self.mothers]

    def _random_free_pos(self):
        for _ in range(300):
            x = random.randint(0, self.config.width - 1)
            y = random.randint(0, self.config.height - 1)
            if self.world.is_free((x, y)):
                return x, y
        return 0, 0

    def _nearby_child_pos(self, x, y):
        candidates = [
            (x + 1, y),
            (x - 1, y),
            (x, y + 1),
            (x, y - 1),
            (x + 1, y + 1),
            (x - 1, y - 1),
            (x + 1, y - 1),
            (x - 1, y + 1),
        ]

        random.shuffle(candidates)

        for cx, cy in candidates:
            if 0 <= cx < self.config.width and 0 <= cy < self.config.height:
                if self.world.is_free((cx, cy)):
                    return cx, cy

        return x, y

    def _spawn_food(self, count):
        spawned = 0

        for _ in range(count * 5):
            if spawned >= count:
                break

            x = random.randint(0, self.config.width - 1)
            y = random.randint(0, self.config.height - 1)

            # Do not place food on entity-occupied cells — food there is
            # unreachable by mothers and inflates the food count falsely.
            if (x, y) not in self.world.food_positions and (x, y) not in self.world.occupied:
                self.world.place_food(x, y)
                spawned += 1

    # ============================================================
    # Helpers
    # ============================================================

    def _nearest_food(self, pos):
        # Only consider food on cells not blocked by another entity.
        # Food under a child is unreachable — skipping it prevents mothers
        # from getting stuck in a permanent FAILED_FORAGE loop.
        accessible = [
            f for f in self.world.food_positions
            if f == pos or f not in self.world.occupied
        ]
        if not accessible:
            return None
        return min(accessible, key=lambda f: self.world.get_distance(pos, f))

    def _child_of(self, mother):
        for child in self.children:
            if child.mother_id == mother.id:
                return child
        return None

    def _alive_mothers(self):
        return [m for m in self.mothers if m.alive]

    def _alive_children(self):
        return [c for c in self.children if c.alive]

    # ============================================================
    # Decision utilities
    # ============================================================

    def _compute_motivation_scores(self, mother, child, nearest_food, dist_to_food):
        perception_radius = getattr(self.config, "perception_radius", DEFAULT_PERCEPTION_RADIUS)

        food_proximity = max(0.0, 1.0 - (dist_to_food / perception_radius))
        if mother.pos in self.world.food_positions:
            food_proximity = 1.5

        # Reduce foraging drive if mother already carries food.
        if mother.held_food > 0:
            food_proximity *= 0.25

        energy_deficit = 1.0 - mother.energy

        if child is not None and child.alive:
            child_dist = self.world.get_distance(mother.pos, child.pos)
            child_need = child.distress
            child_distance_pressure = min(1.0, child_dist / max(1.0, perception_radius))
            care_signal = 0.75 * child_need + 0.25 * child_distance_pressure

            # If mother has food and child is hungry, care becomes stronger.
            if mother.held_food > 0:
                care_signal += 0.35 * child.hunger
        else:
            care_signal = 0.0

        forage_score = (
            getattr(self.config, "forage_weight", 0.70)
            * (0.70 * food_proximity + 0.30 * energy_deficit)
        )

        care_score = getattr(self.config, "care_weight", 0.85) * care_signal

        self_score = getattr(self.config, "self_weight", 0.30) * (
            0.65 * energy_deficit + 0.35 * mother.fatigue
        )

        return {
            "FORAGE": max(0.0, forage_score),
            "CARE": max(0.0, care_score),
            "SELF": max(0.0, self_score),
        }

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
        alive_mothers = self._alive_mothers()
        random.shuffle(alive_mothers)

        tick_actions = {
            "MOVE_FOOD": 0,
            "PICK": 0,
            "EAT": 0,
            "MOVE_CHILD": 0,
            "FEED": 0,
            "REST": 0,
        }

        tick_motivations = {
            "FORAGE": 0,
            "CARE": 0,
            "SELF": 0,
        }

        tick_failed = {
            "FAILED_FORAGE": 0,
            "FAILED_CARE": 0,
            "FAILED_SELF": 0,
        }

        tick_feed = {
            "FEED": 0,
            "feed_success": 0,
            "hunger_reduced": 0.0,
        }

        # Update children first so mother reacts to current child state.
        for child in self._alive_children():
            child.tick_age()
            child.update_hunger(self.config.child_hunger_rate)

            mother = next((m for m in self.mothers if m.id == child.mother_id), None)
            if mother is not None and mother.alive:
                dist = self.world.get_distance(mother.pos, child.pos)
                child.update_separation(dist, getattr(self.config, "perception_radius", DEFAULT_PERCEPTION_RADIUS))
            else:
                child.separation = 1.0

            child.update_distress()
            child.check_death()
            if not child.alive:
                self.world.remove_entity(child.id)

        for mother in alive_mothers:
            mother.tick_age()

            before_hunger = mother.energy
            mother.energy = max(0.0, mother.energy - self.config.hunger_rate)
            hunger_loss = before_hunger - mother.energy

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

            child = self._child_of(mother)

            scores = self._compute_motivation_scores(
                mother=mother,
                child=child,
                nearest_food=nearest,
                dist_to_food=dist_to_food,
            )

            probs = softmax_probs(scores, tau=self.tau)
            motivation = np.random.choice(list(probs.keys()), p=list(probs.values()))

            tick_motivations[motivation] += 1
            self.motivation_counts[motivation] += 1

            executed_action = None

            # -------------------------
            # FORAGE
            # -------------------------
            if motivation == "FORAGE":
                if mother.held_food > 0:
                    # Eat held food immediately — mirrors Phase 2 mechanics so that
                    # CARE interruptions between PICK and SELF don't starve the mother.
                    variance = random.uniform(0.8, 1.2)
                    mother.energy = min(1.0, mother.energy + self.config.eat_gain * variance)
                    mother.held_food -= 1

                    tick_actions["EAT"] += 1
                    self.action_counts["EAT"] += 1
                    executed_action = "EAT"

                elif mother.pos in self.world.food_positions:
                    self.world.remove_food(*mother.pos)
                    mother.held_food += 1

                    tick_actions["PICK"] += 1
                    self.action_counts["PICK"] += 1
                    executed_action = "PICK"

                elif nearest is not None:
                    new_pos = self.world.get_step_toward(mother.pos, nearest)

                    if self.world.update_position(mother, new_pos):
                        mother.energy = max(0.0, mother.energy - self.config.move_cost)
                        mother.fatigue = min(1.0, mother.fatigue + self.config.fatigue_rate)

                        tick_actions["MOVE_FOOD"] += 1
                        self.action_counts["MOVE_FOOD"] += 1
                        executed_action = "MOVE_FOOD"

            # -------------------------
            # CARE
            # -------------------------
            elif motivation == "CARE":
                if child is not None and child.alive:
                    dist = self.world.get_distance(mother.pos, child.pos)

                    if dist <= self.config.feed_distance:
                        # Direct energy-donation feeding — no held_food required.
                        # Matches Phase 2: care is an energy cost, not a food-item transfer.
                        mother.energy = max(0.0, mother.energy - self.config.feed_cost)

                        hunger_reduced = child.receive_food(self.config.feed_amount)
                        child.update_distress()

                        tick_actions["FEED"] += 1
                        tick_feed["FEED"] += 1
                        tick_feed["feed_success"] += 1
                        tick_feed["hunger_reduced"] += hunger_reduced
                        self.action_counts["FEED"] += 1

                        executed_action = "FEED"

                    else:
                        new_pos = self.world.get_step_toward(mother.pos, child.pos)

                        if self.world.update_position(mother, new_pos):
                            mother.energy = max(0.0, mother.energy - self.config.move_cost)
                            mother.fatigue = min(1.0, mother.fatigue + self.config.fatigue_rate)

                            tick_actions["MOVE_CHILD"] += 1
                            self.action_counts["MOVE_CHILD"] += 1
                            executed_action = "MOVE_CHILD"

            # -------------------------
            # SELF
            # -------------------------
            elif motivation == "SELF":
                action = self._choose_self_action(mother)

                if action == "EAT" and mother.held_food > 0:
                    variance = random.uniform(0.8, 1.2)
                    mother.energy = min(1.0, mother.energy + self.config.eat_gain * variance)
                    mother.held_food -= 1

                    tick_actions["EAT"] += 1
                    self.action_counts["EAT"] += 1
                    executed_action = "EAT"

                else:
                    mother.fatigue = max(0.0, mother.fatigue - self.config.rest_recovery)

                    tick_actions["REST"] += 1
                    self.action_counts["REST"] += 1
                    executed_action = "REST"

            # -------------------------
            # Failed realization
            # -------------------------
            if executed_action is None:
                failed_key = f"FAILED_{motivation}"
                tick_failed[failed_key] += 1
                self.failed_counts[failed_key] += 1

            if self._agent_log_enabled:
                self._agent_log[mother.id].append(
                    executed_action if executed_action is not None else f"FAILED_{motivation}"
                )

            if mother.energy <= 0:
                mother.die()
                self.world.remove_entity(mother.id)

        target = int(self.config.init_food * self.food_mult)
        if len(self.world.food_positions) < target:
            self._spawn_food(self.config.food_respawn_per_tick)

        alive_mothers_now = self._alive_mothers()
        alive_children_now = self._alive_children()

        self.mother_population_history.append(len(alive_mothers_now))
        self.child_population_history.append(len(alive_children_now))

        avg_mother_energy = (
            sum(m.energy for m in alive_mothers_now) / len(alive_mothers_now)
            if alive_mothers_now
            else 0.0
        )

        avg_child_hunger = (
            sum(c.hunger for c in alive_children_now) / len(alive_children_now)
            if alive_children_now
            else 0.0
        )

        avg_child_distress = (
            sum(c.distress for c in alive_children_now) / len(alive_children_now)
            if alive_children_now
            else 0.0
        )

        distances = []
        for mother in alive_mothers_now:
            child = self._child_of(mother)
            if child is not None and child.alive:
                distances.append(self.world.get_distance(mother.pos, child.pos))

        avg_distance = float(np.mean(distances)) if distances else 0.0

        self.mother_energy_history.append(avg_mother_energy)
        self.child_hunger_history.append(avg_child_hunger)
        self.child_distress_history.append(avg_child_distress)
        self.mother_child_distance_history.append(avg_distance)

        for mother in alive_mothers_now:
            x, y = mother.pos
            if 0 <= x < self.config.width and 0 <= y < self.config.height:
                self.spatial_heatmap_mother[y, x] += 1.0

        for child in alive_children_now:
            x, y = child.pos
            if 0 <= x < self.config.width and 0 <= y < self.config.height:
                self.spatial_heatmap_child[y, x] += 1.0

        alive_mother_count = len(alive_mothers_now)
        alive_child_count = len(alive_children_now)

        tick_actions["alive"] = alive_mother_count
        tick_motivations["alive"] = alive_mother_count
        tick_failed["alive"] = alive_mother_count
        tick_feed["alive"] = alive_mother_count

        self.action_history.append(tick_actions)
        self.motivation_history.append(tick_motivations)
        self.failed_history.append(tick_failed)
        self.feed_history.append(tick_feed)

        self.family_history.append(
            {
                "alive_mothers": alive_mother_count,
                "alive_children": alive_child_count,
                "mother_energy": avg_mother_energy,
                "child_hunger": avg_child_hunger,
                "child_distress": avg_child_distress,
                "mother_child_distance": avg_distance,
                "food_available": len(self.world.food_positions),
            }
        )

    # ============================================================
    # Run
    # ============================================================

    def run(self):
        self.initialize()

        for t in range(self.config.max_ticks):
            self.tick = t
            self.step()

            if not any(m.alive for m in self.mothers) and not any(c.alive for c in self.children):
                break

        final_mothers = sum(1 for m in self.mothers if m.alive)
        final_children = sum(1 for c in self.children if c.alive)

        mean_mother_energy = (
            float(np.mean(self.mother_energy_history))
            if self.mother_energy_history
            else 0.0
        )

        final_mother_energy = (
            float(self.mother_energy_history[-1])
            if self.mother_energy_history
            else 0.0
        )

        mean_child_hunger = (
            float(np.mean(self.child_hunger_history))
            if self.child_hunger_history
            else 0.0
        )

        final_child_hunger = (
            float(self.child_hunger_history[-1])
            if self.child_hunger_history
            else 0.0
        )

        mean_child_distress = (
            float(np.mean(self.child_distress_history))
            if self.child_distress_history
            else 0.0
        )

        final_child_distress = (
            float(self.child_distress_history[-1])
            if self.child_distress_history
            else 0.0
        )

        return {
            "final_mothers": final_mothers,
            "final_children": final_children,
            "mean_mother_energy": mean_mother_energy,
            "final_mother_energy": final_mother_energy,
            "mean_child_hunger": mean_child_hunger,
            "final_child_hunger": final_child_hunger,
            "mean_child_distress": mean_child_distress,
            "final_child_distress": final_child_distress,
            "mother_energy_history": self.mother_energy_history,
            "mother_population_history": self.mother_population_history,
            "child_hunger_history": self.child_hunger_history,
            "child_distress_history": self.child_distress_history,
            "child_population_history": self.child_population_history,
            "mother_child_distance_history": self.mother_child_distance_history,
            "actions": self.action_counts,
            "motivations": self.motivation_counts,
            "failed": self.failed_counts,
            "action_history": self.action_history,
            "motivation_history": self.motivation_history,
            "failed_history": self.failed_history,
            "feed_history": self.feed_history,
            "family_history": self.family_history,
            "spatial_heatmap_mother": self.spatial_heatmap_mother,
            "spatial_heatmap_child": self.spatial_heatmap_child,
            "per_agent_log": dict(self._agent_log) if self._agent_log_enabled else None,
            "agent_order": list(self._agent_order) if self._agent_log_enabled else None,
        }


# ============================================================
# Experiment utilities
# ============================================================

def make_config(params, duration):
    cfg = Config()

    cfg.max_ticks = duration
    cfg.width = params.get("width", 30)
    cfg.height = params.get("height", 30)

    cfg.init_mothers = INIT_MOTHERS
    cfg.initial_energy = INITIAL_ENERGY

    cfg.perception_radius = params.get("perception_radius", DEFAULT_PERCEPTION_RADIUS)

    cfg.hunger_rate = params["hunger_rate"]
    cfg.move_cost = params["move_cost"]
    cfg.eat_gain = params["eat_gain"]
    cfg.init_food = params["init_food"]
    cfg.rest_recovery = params["rest_recovery"]

    cfg.fatigue_rate = params.get("fatigue_rate", getattr(cfg, "fatigue_rate", 0.01))

    cfg.child_hunger_rate = params["child_hunger_rate"]
    cfg.feed_amount = params["feed_amount"]
    cfg.feed_cost = params["feed_cost"]
    cfg.feed_distance = params["feed_distance"]
    cfg.food_respawn_per_tick = params.get("food_respawn_per_tick", 3)

    cfg.care_weight = params.get("care_weight", 0.85)
    cfg.forage_weight = params.get("forage_weight", 0.70)
    cfg.self_weight = params.get("self_weight", 0.30)

    cfg.children_enabled = True
    cfg.care_enabled = True
    cfg.plasticity_enabled = False
    cfg.reproduction_enabled = False

    return cfg


def run_one(params, seed, duration, tau, noise):
    set_seed(seed)
    cfg = make_config(params, duration)
    sim = MotherChildSurvivalSimulation(cfg, tau=tau, perceptual_noise=noise)
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


# ============================================================
# Selection rules
# ============================================================

def is_valid_condition(name, result):
    if name == "balanced":
        t = SELECTION_TARGETS["balanced"]
        return (
            result["final_mothers"] >= t["min_final_mothers"]
            and result["final_children"] >= t["min_final_children"]
            and t["mother_energy_low"] <= safe(result["tail_mother_energy"]) <= t["mother_energy_high"]
            and safe(result["tail_child_hunger"]) <= t["max_child_hunger"]
            and safe(result["tail_child_distress"]) <= t["max_child_distress"]
        )

    if name == "easy":
        t = SELECTION_TARGETS["easy"]
        return (
            result["final_mothers"] >= t["min_final_mothers"]
            and result["final_children"] >= t["min_final_children"]
            and safe(result["tail_mother_energy"]) >= t["min_mother_energy"]
            and safe(result["tail_child_hunger"]) <= t["max_child_hunger"]
            and safe(result["tail_child_distress"]) <= t["max_child_distress"]
        )

    if name == "harsh":
        t = SELECTION_TARGETS["harsh"]
        child_fail = result["final_children"] <= t["max_final_children"]
        mother_partial = result["final_mothers"] >= t["min_final_mothers"]
        return child_fail and mother_partial

    return False


def strict_sort_key(name, record):
    r = record["result"]
    p = record["params"]

    if name == "balanced":
        t = SELECTION_TARGETS["balanced"]
        return (
            p["init_food"],
            abs(safe(r["tail_mother_energy"]) - t["target_mother_energy"]),
            safe(r["tail_child_hunger"]),
            safe(r["tail_child_distress"]),
            abs(r["final_mothers"] - INIT_MOTHERS),
            abs(r["final_children"] - INIT_MOTHERS),
        )

    if name == "easy":
        return (
            -safe(r["tail_mother_energy"]),
            safe(r["tail_child_hunger"]),
            safe(r["tail_child_distress"]),
            -r["final_children"],
            -r["final_mothers"],
            -p["init_food"],
        )

    if name == "harsh":
        t = SELECTION_TARGETS["harsh"]
        return (
            abs(r["final_children"] - t["target_final_children"]),
            -r["final_mothers"],
            p["init_food"],
            safe(r["tail_child_hunger"]),
        )

    return (999,)


def fallback_sort_key(name, record):
    r = record["result"]
    p = record["params"]

    if name == "balanced":
        t = SELECTION_TARGETS["balanced"]
        mother_gap = max(0.0, t["min_final_mothers"] - r["final_mothers"])
        child_gap = max(0.0, t["min_final_children"] - r["final_children"])
        hunger_gap = max(0.0, safe(r["tail_child_hunger"]) - t["max_child_hunger"])
        distress_gap = max(0.0, safe(r["tail_child_distress"]) - t["max_child_distress"])

        return (
            mother_gap,
            child_gap,
            hunger_gap,
            distress_gap,
            p["init_food"],
            abs(safe(r["tail_mother_energy"]) - t["target_mother_energy"]),
        )

    if name == "easy":
        t = SELECTION_TARGETS["easy"]
        return (
            max(0.0, t["min_final_mothers"] - r["final_mothers"]),
            max(0.0, t["min_final_children"] - r["final_children"]),
            max(0.0, t["min_mother_energy"] - safe(r["tail_mother_energy"])),
            max(0.0, safe(r["tail_child_hunger"]) - t["max_child_hunger"]),
            p["init_food"],
        )

    if name == "harsh":
        t = SELECTION_TARGETS["harsh"]
        return (
            abs(r["final_children"] - t["target_final_children"]),
            max(0.0, t["min_final_mothers"] - r["final_mothers"]),
            p["init_food"],
        )

    return (999,)


def build_validation_pool(name, sweep_records):
    valid = [r for r in sweep_records if is_valid_condition(name, r["result"])]

    if valid:
        return sorted(valid, key=lambda r: strict_sort_key(name, r))

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
            f"food={params['init_food']} | "
            f"mothers={validation_summary['final_mothers']:.2f}/15 | "
            f"children={validation_summary['final_children']:.2f}/15 | "
            f"tailE={validation_summary['tail_mother_energy']:.3f} | "
            f"childH={validation_summary['tail_child_hunger']:.3f}"
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
            "final_mothers": r["final_mothers"],
            "final_children": r["final_children"],
            "mean_mother_energy": r["mean_mother_energy"],
            "final_mother_energy": r["final_mother_energy"],
            "mean_child_hunger": r["mean_child_hunger"],
            "final_child_hunger": r["final_child_hunger"],
            "mean_child_distress": r["mean_child_distress"],
            "final_child_distress": r["final_child_distress"],
            "actions": r.get("actions", {}),
            "motivations": r.get("motivations", {}),
            "failed": r.get("failed", {}),
        }
        for r in results
    ]


def generate_diagnostic_plots(name, results, params, labels, args, out_dir):
    if ENABLE_VALIDATION_PLOT:
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

    if ENABLE_MOTHER_CHILD_DIAGNOSTIC_PLOT:
        plot_mother_child_diagnostics(
            name=name,
            results=results,
            duration=args.duration,
            out_dir=out_dir,
            window=PLOT_SMOOTH_WINDOW,
        )

    if ENABLE_FEED_RATE_PLOT:
        plot_feed_rate_over_time(
            name=name,
            results=results,
            duration=args.duration,
            out_dir=out_dir,
            window=PLOT_SMOOTH_WINDOW,
        )

    if ENABLE_SPATIAL_HEATMAP_PLOT:
        plot_spatial_heatmap(
            name=name,
            results=results,
            out_dir=out_dir,
        )


# ============================================================
# Main experiment
# ============================================================

def run_experiment(args):
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir = os.path.join(
        PROJECT_ROOT,
        "outputs",
        "phase3_survival_full",
        f"{ts}_validation_selected_baselines",
    )
    os.makedirs(out_dir, exist_ok=True)

    print(f"Phase 3 Survival-Full Calibration - Mode: {args.mode}")
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

        if idx % 10 == 0 or idx == len(configs):
            print(
                f"  [{idx:03d}/{len(configs)}] "
                f"mothers={summary_result['final_mothers']:4.1f}/15 | "
                f"children={summary_result['final_children']:4.1f}/15 | "
                f"tailE={summary_result['tail_mother_energy']:.3f} | "
                f"childH={summary_result['tail_child_hunger']:.3f}"
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


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--duration", type=int, default=1000)
    parser.add_argument("--tau", type=float, default=0.1)
    parser.add_argument("--perceptual_noise", type=float, default=0.1)
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--mode", type=str, choices=["sweep", "single"], default="sweep")
    args = parser.parse_args()

    run_experiment(args)