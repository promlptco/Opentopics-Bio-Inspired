# experiments/phase3_survival_full/run.py
"""
Phase 3 Ecological Calibration — 8-step OVAT pipeline (same as Phase 2).

Extends Phase 2's pipeline with children enabled.  The simulation engine is
simulation.simulation.Simulation (with children_enabled=True) wrapped in
Phase3Simulation to produce Phase-2-compatible result dicts + child metrics.

Modes:
  pipeline  — full 8-step automated run (Steps 1–8, recommended)
  sweep     — Steps 6–8 only (skip anchor + OVAT; faster for reruns)
  single    — single config diagnostic (Steps 1–2 + Step 8 plots)

Usage:
  python -m experiments.phase3_survival_full.run --mode pipeline --workers 4
  python -m experiments.phase3_survival_full.run --mode sweep   --workers 4
  python -m experiments.phase3_survival_full.run --mode single
"""

import sys
import os
import argparse
import csv
import json
import random
from datetime import datetime
from concurrent.futures import ProcessPoolExecutor

import numpy as np

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, PROJECT_ROOT)

from experiments.phase3_survival_full.config import (
    INIT_MOTHERS, INITIAL_ENERGY, VALIDATION_SEEDS, DEFAULT_SWEEP_SEED_BASE,
    DEFAULT_PERCEPTION_RADIUS, TAIL_WINDOW, PLOT_SMOOTH_WINDOW,
    BALANCED_BASELINE, SENSITIVITY_SWEEPS, SENSITIVITY_SUBPLOT_CONFIG,
    HIDE_BASELINE_FOR, SWEEP_GRID, SELECTION_TARGETS, CHILD_SELECTION_TARGETS,
    MAX_TICKS, ISM, make_config, candidate_configs,
)


# ─────────────────────────────────────────────────────────────────────────────
# Utility helpers
# ─────────────────────────────────────────────────────────────────────────────

def safe(value, nan: float = 0.0) -> float:
    return float(np.nan_to_num(value, nan=nan))


def pad(x, duration: int) -> np.ndarray:
    arr = np.full(duration, np.nan)
    x = np.asarray(x, dtype=float)
    arr[: min(duration, len(x))] = x[:duration]
    return arr


def tail_slope(series, duration: int, tail_window: int = TAIL_WINDOW) -> float:
    y = np.nan_to_num(pad(series, duration), nan=0.0)[-tail_window:]
    x = np.arange(len(y), dtype=float)
    return float(np.polyfit(x, y, 1)[0]) if len(y) >= 2 else 0.0


def _n_workers(w: int) -> int:
    return (os.cpu_count() or 1) if w == 0 else max(1, w)


# ─────────────────────────────────────────────────────────────────────────────
# Phase3Simulation — wraps simulation.simulation.Simulation
# ─────────────────────────────────────────────────────────────────────────────

class Phase3Simulation:
    """
    Wrapper that drives simulation.simulation.Simulation manually per-tick,
    collecting per-tick data compatible with Phase 2's result dict format
    plus Phase 3-specific child metrics.

    Phase 2 SurvivalSimulation had perceptual_noise because it used a custom
    step loop.  Phase 3 uses the canonical Simulation engine whose perception
    is governed by food_perception_radius — no additive noise needed.
    """

    def __init__(self, config, food_mult: float = 1.0):
        self.config    = config
        self.food_mult = food_mult

        # Per-tick histories (Phase 2 compatible)
        self.energy_history       = []
        self.fatigue_history      = []
        self.population_history   = []
        self.food_history         = []
        self.motivation_history   = []  # per-tick FORAGE/SELF/CARE counts (from logged choices)

        # Phase 3 additional
        self.child_energy_history     = []
        self.child_population_history = []

        # Spatial heatmap (mother positions accumulated)
        self.spatial_heatmap = np.zeros(
            (config.height, config.width), dtype=float
        )

    # ── Run ───────────────────────────────────────────────────────────────────

    def run(self) -> dict:
        from simulation.simulation import Simulation

        # Override init_food with food_mult scaling (matches Phase 2 behaviour)
        cfg = self.config
        if self.food_mult != 1.0:
            cfg.init_food = max(1, int(cfg.init_food * self.food_mult))

        sim = Simulation(cfg)
        sim.initialize()

        prev_choice_len = 0

        for t in range(cfg.max_ticks):
            alive_m = [m for m in sim.mothers if m.alive]
            alive_c = [c for c in sim.children if c.alive]

            # Mother energy: population-weighted (dead = 0, same as Phase 2)
            mom_energy  = sum(m.energy  for m in alive_m) / cfg.init_mothers
            mom_fatigue = np.mean([m.fatigue for m in alive_m]) if alive_m else 0.0
            child_energy = float(np.nanmean([c.energy for c in alive_c])) if alive_c else float("nan")

            self.energy_history.append(mom_energy)
            self.fatigue_history.append(mom_fatigue)
            self.population_history.append(len(alive_m))
            self.child_energy_history.append(child_energy)
            self.child_population_history.append(len(alive_c))
            self.food_history.append({
                "food_available": len(sim.world.food_positions),
                "alive": len(alive_m),
            })

            # Per-tick motivation tally from new choice_records since last tick.
            # Note: Simulation logs choices only when a distressed child is visible
            # (distress >= 0.3), so rates are conditional on care-pressure events.
            new_choices = sim.logger.choice_records[prev_choice_len:]
            prev_choice_len = len(sim.logger.choice_records)
            tick_m = {"FORAGE": 0, "SELF": 0, "CARE": 0, "alive": len(alive_m)}
            for r in new_choices:
                d = r.winner_domain.upper()
                if d in tick_m:
                    tick_m[d] += 1
            self.motivation_history.append(tick_m)

            # Spatial heatmap
            for m in alive_m:
                x, y = m.pos
                if 0 <= x < cfg.width and 0 <= y < cfg.height:
                    self.spatial_heatmap[y, x] += 1.0

            sim.step()
            sim.tick += 1

            if not any(m.alive for m in sim.mothers):
                break

        return self.collect_result(sim)

    # ── Diagnostic run (single seed, per-tick per-agent logging) ─────────────

    def run_diagnostic(self) -> dict:
        """
        Run one seed and collect per-tick per-agent data for care trap plots.

        Returns arrays shaped (T, n_agents):
          score_forage, score_care, score_self  — motivation scores before softmax
          domain_idx    — -1=dead, 0=FORAGE, 1=CARE, 2=SELF
          held_food     — -1=dead, else 0 or 1 (before action this tick)
          failed_care   — bool: domain==CARE and held_food==0
          child_energy  — NaN when dead
          child_death_tick — tick index when each child died (NaN = survived)
        """
        from simulation.simulation import Simulation

        cfg = self.config
        sim = Simulation(cfg)
        sim.initialize()

        all_mothers  = list(sim.mothers)
        all_children = list(sim.children)
        n_m, n_c     = len(all_mothers), len(all_children)
        T            = cfg.max_ticks

        DOMAIN_MAP = {"FORAGE": 0, "CARE": 1, "SELF": 2}

        score_forage     = np.full((T, n_m), np.nan)
        score_care       = np.full((T, n_m), np.nan)
        score_self       = np.full((T, n_m), np.nan)
        domain_idx       = np.full((T, n_m), -1, dtype=int)
        held_food_arr    = np.full((T, n_m), -1, dtype=int)
        failed_care_arr  = np.zeros((T, n_m), dtype=bool)
        child_energy_arr = np.full((T, n_c), np.nan)
        child_death_tick = np.full(n_c, np.nan)

        for t in range(T):
            # ── child state before step ───────────────────────────────────────
            for ci, c in enumerate(all_children):
                if c.alive:
                    child_energy_arr[t, ci] = c.energy

            # ── mother motivation scores & domain before step ─────────────────
            for mi, m in enumerate(all_mothers):
                if not m.alive:
                    continue

                hf = m.held_food
                held_food_arr[t, mi] = hf

                if m.has_commitment():
                    # Committed → will choose CARE this tick
                    scores      = {"FORAGE": 0.0, "SELF": 0.0, "CARE": 1.0}
                    pre_domain  = "CARE"
                else:
                    nearest_food = sim._nearest_food_in_radius(
                        m.pos, cfg.food_perception_radius
                    )
                    if hf >= 1:
                        nearest_food = None   # Fix B: suppress forage cue when provisioned
                    dist = (
                        float(sim.world.get_distance(m.pos, nearest_food))
                        if nearest_food is not None else None
                    )
                    care_child = None
                    if m.own_child_id is not None:
                        _own = sim._get_child_by_id(m.own_child_id)
                        care_child = _own if (_own and _own.alive) else None

                    scores     = m.compute_motivation_scores(
                        perception_radius=cfg.food_perception_radius,
                        child=care_child,
                        nearest_food=nearest_food,
                        distance_to_food=dist,
                        care_enabled=True,
                    )
                    pre_domain = max(scores, key=scores.get)

                score_forage[t, mi]    = scores.get("FORAGE", 0.0)
                score_care[t, mi]      = scores.get("CARE",   0.0)
                score_self[t, mi]      = scores.get("SELF",   0.0)
                domain_idx[t, mi]      = DOMAIN_MAP.get(pre_domain, 0)
                failed_care_arr[t, mi] = (pre_domain == "CARE" and hf == 0)

            # ── advance simulation ────────────────────────────────────────────
            sim.step()
            sim.tick += 1

            # ── detect child deaths this tick ─────────────────────────────────
            for ci, c in enumerate(all_children):
                if not c.alive and np.isnan(child_death_tick[ci]):
                    child_death_tick[ci] = float(t)

            if not any(m.alive for m in all_mothers):
                break

        return {
            "score_forage":    score_forage,
            "score_care":      score_care,
            "score_self":      score_self,
            "domain_idx":      domain_idx,
            "held_food":       held_food_arr,
            "failed_care":     failed_care_arr,
            "child_energy":    child_energy_arr,
            "child_death_tick": child_death_tick,
            "n_mothers":       n_m,
            "n_children":      n_c,
            "duration":        T,
        }

    def collect_result(self, sim) -> dict:
        alive_m = [m for m in sim.mothers if m.alive]

        matured = sum(
            1 for r in sim.logger.death_records
            if r.agent_type == "child" and r.cause == "matured"
        )
        hunger_deaths = [
            r for r in sim.logger.death_records
            if r.agent_type == "child" and r.cause == "hunger"
        ]
        death_ticks = [r.tick for r in hunger_deaths]
        child_death_mu = (
            float(sum(death_ticks) / len(death_ticks)) if death_ticks
            else float(self.config.max_ticks)
        )

        choices   = sim.logger.choice_records
        n_ch      = len(choices)
        care_pct   = sum(1 for r in choices if r.winner_domain == "care")   / n_ch if n_ch else 0.0
        forage_pct = sum(1 for r in choices if r.winner_domain == "forage") / n_ch if n_ch else 0.0
        self_pct   = sum(1 for r in choices if r.winner_domain == "self")   / n_ch if n_ch else 0.0

        # Cumulative motivation counts for compatibility with Phase 2's "actions" field
        motiv_counts = {"FORAGE": 0, "SELF": 0, "CARE": 0}
        for r in choices:
            d = r.winner_domain.upper()
            if d in motiv_counts:
                motiv_counts[d] += 1

        return {
            # Phase 2-compatible fields
            "final_pop":          len(alive_m),
            "mean_energy":        float(np.mean(self.energy_history)) if self.energy_history else 0.0,
            "final_energy":       float(self.energy_history[-1])       if self.energy_history else 0.0,
            "energy_history":     self.energy_history,
            "fatigue_history":    self.fatigue_history,
            "population_history": self.population_history,
            "actions":            motiv_counts,
            "motivations":        motiv_counts,
            "failed":             {},
            "action_history":     self.motivation_history,
            "motivation_history": self.motivation_history,
            "failed_history":     [{"alive": p} for p in self.population_history],
            "food_history":       self.food_history,
            "energy_flow_history": [{"alive": 1} for _ in self.energy_history],
            "spatial_heatmap":    self.spatial_heatmap,

            # Phase 3 extensions
            "child_maturation_rate":  matured / self.config.init_mothers,
            "child_death_tick_mean":  child_death_mu,
            "care_pct":               care_pct,
            "forage_pct":             forage_pct,
            "self_pct":               self_pct,
            "child_energy_history":    self.child_energy_history,
            "child_population_history": self.child_population_history,
        }


# ─────────────────────────────────────────────────────────────────────────────
# Run helpers
# ─────────────────────────────────────────────────────────────────────────────

def run_one(params: dict, seed: int, duration: int) -> dict:
    """Single run — full result dict (energy/population histories + child metrics)."""
    import random as _random
    _random.seed(seed)
    np.random.seed(seed)
    cfg        = make_config(params, duration)
    cfg.seed   = seed
    sim        = Phase3Simulation(cfg)
    return sim.run()


def _run_task(task):
    """Top-level wrapper for ProcessPoolExecutor pickling."""
    params, seed, duration = task
    return run_one(params, seed, duration)


# ─────────────────────────────────────────────────────────────────────────────
# Summary statistics
# ─────────────────────────────────────────────────────────────────────────────

def summarize_repeats(repeat_results: list, duration: int,
                      tail_window: int = TAIL_WINDOW) -> dict:
    """
    Aggregate multiple-seed results into a summary dict.
    Extends Phase 2's summarize_repeats with Phase 3 child metrics.
    """
    final_pops  = np.array([r["final_pop"]    for r in repeat_results], dtype=float)
    mean_es     = np.array([r["mean_energy"]   for r in repeat_results], dtype=float)
    final_es    = np.array([r["final_energy"]  for r in repeat_results], dtype=float)

    tail_means, e_slopes, pop_slopes = [], [], []
    for r in repeat_results:
        e = np.nan_to_num(pad(r["energy_history"], duration), nan=0.0)
        tail_means.append(np.mean(e[-tail_window:]))
        e_slopes.append(tail_slope(r["energy_history"], duration, tail_window))
        pop_slopes.append(tail_slope(r["population_history"], duration, tail_window))

    tail_means = np.array(tail_means, dtype=float)

    # Phase 3 child metrics
    c_matr_vals      = np.array([r.get("child_maturation_rate", 0.0) for r in repeat_results], dtype=float)
    child_death_vals = np.array([r.get("child_death_tick_mean", float(duration)) for r in repeat_results], dtype=float)
    care_pct_vals    = np.array([r.get("care_pct", 0.0)  for r in repeat_results], dtype=float)
    forage_pct_vals  = np.array([r.get("forage_pct", 0.0) for r in repeat_results], dtype=float)
    self_pct_vals    = np.array([r.get("self_pct", 0.0)   for r in repeat_results], dtype=float)

    # Child mean energy (PRIMARY selection metric): mean over alive-child ticks per run
    child_mean_e_vals = []
    for r in repeat_results:
        hist = r.get("child_energy_history", [])
        if hist:
            arr = np.asarray(hist, dtype=float)
            mu = float(np.nanmean(arr)) if not np.all(np.isnan(arr)) else 0.0
        else:
            mu = 0.0
        child_mean_e_vals.append(mu)
    child_mean_e_vals = np.array(child_mean_e_vals, dtype=float)

    # SELF-rate analogous to Phase 2's rest_action_rate (for selection sanity check)
    self_rates = []
    for r in repeat_results:
        m = r.get("motivations", r.get("actions", {}))
        total = sum(m.get(k, 0) for k in ["FORAGE", "SELF", "CARE"])
        self_rates.append(m.get("SELF", 0) / total if total > 0 else 0.0)

    return {
        "final_pop":                 float(np.mean(final_pops)),
        "final_pop_sd":              float(np.std(final_pops)),
        "mean_energy":               float(np.mean(mean_es)),
        "final_energy":              float(np.mean(final_es)),
        "tail_mean_energy":          float(np.mean(tail_means)),
        "tail_energy_sd":            float(np.std(tail_means)),
        "tail_energy_slope":         float(np.mean(e_slopes)),
        "tail_pop_slope":            float(np.mean(pop_slopes)),
        "rest_action_rate":          float(np.mean(self_rates)),   # SELF rate (Phase 2 compat name)
        # Phase 3 child metrics (priority: energy > longevity > maturation)
        "child_mean_energy_mean":      float(np.mean(child_mean_e_vals)),
        "child_mean_energy_sd":        float(np.std(child_mean_e_vals)),
        "child_maturation_rate_mean":  float(np.mean(c_matr_vals)),
        "child_maturation_rate_sd":    float(np.std(c_matr_vals)),
        "child_death_tick_mean_mean":  float(np.mean(child_death_vals)),
        "child_death_tick_mean_sd":    float(np.std(child_death_vals)),
        "care_pct_mean":               float(np.mean(care_pct_vals)),
        "forage_pct_mean":             float(np.mean(forage_pct_vals)),
        "self_pct_mean":               float(np.mean(self_pct_vals)),
    }


# ─────────────────────────────────────────────────────────────────────────────
# Regime selection
# ─────────────────────────────────────────────────────────────────────────────

def _survival_rate(result: dict) -> float:
    return result["final_pop"] / INIT_MOTHERS


def is_valid_condition(name: str, result: dict) -> bool:
    """
    Return True if result satisfies Phase 3 selection criteria for `name`.

    Priority order (checked top-to-bottom — a violation at any level fails):
      1. Child energy        (PRIMARY)
      2. Child longevity     (SECONDARY)
      3. Mother energy       (TERTIARY)
      4. Mother population   (QUATERNARY)
    """
    child_t = CHILD_SELECTION_TARGETS[name]
    t       = SELECTION_TARGETS[name]

    # ── Priority 1: child energy ──────────────────────────────────────────────
    child_mean_e = safe(result.get("child_mean_energy_mean", 0.0))
    if child_mean_e < child_t["min_child_energy"]:
        return False

    # ── Priority 2: child longevity (population proxy) ───────────────────────
    death_mu = safe(result.get("child_death_tick_mean_mean", 0.0))
    if death_mu < child_t["min_child_death_mu"]:
        return False

    # ── Priority 3: mother energy ─────────────────────────────────────────────
    energy = safe(result["tail_mean_energy"])
    if name in ("balanced", "harsh"):
        if not (t["energy_low"] <= energy <= t["energy_high"]):
            return False
    elif name == "easy":
        if energy < t["min_energy"]:
            return False

    # ── Priority 4: mother population ────────────────────────────────────────
    surv = _survival_rate(result)
    if name in ("balanced", "harsh"):
        if not (t["min_survival_rate"] <= surv <= t["max_survival_rate"]):
            return False
    elif name == "easy":
        if surv < t["min_survival_rate"]:
            return False

    return True


def _penalty_score(name: str, result: dict) -> float:
    """
    Lower = better.  Penalty weights follow the priority order:
      1. Child energy   — highest weight (PRIMARY)
      2. Child longevity — high weight  (SECONDARY)
      3. Mother energy   — medium weight (TERTIARY)
      4. Mother survival — lowest weight (QUATERNARY)
    """
    child_t = CHILD_SELECTION_TARGETS[name]
    t       = SELECTION_TARGETS[name]
    score   = 0.0

    # ── Priority 1: child energy (PRIMARY) ───────────────────────────────────
    child_mean_e = safe(result.get("child_mean_energy_mean", 0.0))
    if child_mean_e < child_t["min_child_energy"]:
        score += 3000.0 * (child_t["min_child_energy"] - child_mean_e)
    score += abs(child_mean_e - child_t["target_child_energy"]) * 200.0

    # ── Priority 2: child longevity (SECONDARY) ───────────────────────────────
    death_mu = safe(result.get("child_death_tick_mean_mean", 0.0))
    if death_mu < child_t["min_child_death_mu"]:
        score += 30.0 * (child_t["min_child_death_mu"] - death_mu)
    score += abs(death_mu - child_t["target_child_death_mu"]) * 10.0

    # ── Priority 3: mother energy (TERTIARY) ──────────────────────────────────
    energy = safe(result["tail_mean_energy"])
    e_sd   = safe(result["tail_energy_sd"], nan=1.0)
    if name in ("balanced", "harsh"):
        if energy < t["energy_low"]:
            score += 500.0 * (t["energy_low"] - energy)
        elif energy > t["energy_high"]:
            score += 500.0 * (energy - t["energy_high"])
        score += abs(energy - t["target_energy"]) * 30.0
    elif name == "easy":
        if energy < t["min_energy"]:
            score += 500.0 * (t["min_energy"] - energy)
        score += max(0.0, t["target_energy"] - energy) * 30.0
    score += e_sd * 5.0

    # ── Priority 4: mother survival (QUATERNARY) ──────────────────────────────
    surv = _survival_rate(result)
    if name in ("balanced", "harsh"):
        if surv < t["min_survival_rate"]:
            score += 200.0 * (t["min_survival_rate"] - surv)
        elif surv > t["max_survival_rate"]:
            score += 200.0 * (surv - t["max_survival_rate"])
        score += abs(surv - t["target_survival_rate"]) * 10.0
    elif name == "easy":
        if surv < t["min_survival_rate"]:
            score += 200.0 * (t["min_survival_rate"] - surv)
        score += abs(surv - t["target_survival_rate"]) * 10.0

    return score


def select_by_penalty_score(name: str, sweep_records: list):
    scored = [(_penalty_score(name, r["result"]), r) for r in sweep_records]
    scored.sort(key=lambda x: x[0])
    if not scored:
        raise RuntimeError(f"No candidates for {name}")
    best_score, best_rec = scored[0]
    return best_rec, best_score, scored


# ─────────────────────────────────────────────────────────────────────────────
# OVAT sweep helpers
# ─────────────────────────────────────────────────────────────────────────────

def _summarize_ovat_runs(run_results: list, duration: int,
                         tail_window: int = TAIL_WINDOW) -> dict:
    """Lightweight aggregate for OVAT rows (no full history needed)."""
    final_pops    = np.array([r["final_pop"]   for r in run_results], dtype=float)
    tail_means    = []
    c_matr_vals   = np.array([r.get("child_maturation_rate", 0.0) for r in run_results], dtype=float)
    child_death   = np.array([r.get("child_death_tick_mean", float(duration)) for r in run_results], dtype=float)
    care_pct_vals = np.array([r.get("care_pct", 0.0) for r in run_results], dtype=float)

    # Child mean energy (PRIMARY metric) — computed per run then averaged
    child_mean_e_list = []
    for r in run_results:
        e = np.nan_to_num(pad(r["energy_history"], duration), nan=0.0)
        tail_means.append(np.mean(e[-tail_window:]))
        hist = r.get("child_energy_history", [])
        if hist:
            arr = np.asarray(hist, dtype=float)
            mu = float(np.nanmean(arr)) if not np.all(np.isnan(arr)) else 0.0
        else:
            mu = 0.0
        child_mean_e_list.append(mu)

    tail_means       = np.array(tail_means,       dtype=float)
    child_mean_e_arr = np.array(child_mean_e_list, dtype=float)

    return {
        "num_runs":                    len(run_results),
        "survival_rate_mean":          float(np.mean(final_pops) / INIT_MOTHERS),
        "survival_rate_sd":            float(np.std(final_pops)  / INIT_MOTHERS),
        "final_pop_mean":              float(np.mean(final_pops)),
        "tail_energy_mean":            float(np.mean(tail_means)),
        "tail_energy_sd":              float(np.std(tail_means)),
        "child_mean_energy_mean":      float(np.mean(child_mean_e_arr)),
        "child_mean_energy_sd":        float(np.std(child_mean_e_arr)),
        "child_maturation_rate_mean":  float(np.mean(c_matr_vals)),
        "child_maturation_rate_sd":    float(np.std(c_matr_vals)),
        "child_death_tick_mean_mean":  float(np.mean(child_death)),
        "child_death_tick_mean_sd":    float(np.std(child_death)),
        "care_pct_mean":               float(np.mean(care_pct_vals)),
    }


def find_food_anchor(seeds: list, duration: int, workers: int = 1,
                     target_survival: float = 0.50,
                     food_step: int = 50, food_max: int = 3000,
                     repeats: int = 1) -> tuple:
    """
    Scan init_food upward (all other params from BALANCED_BASELINE) until
    mean mother survival >= target_survival.  Returns (anchor_food, summary).

    Phase 3 needs a larger search range than Phase 2 because children add
    indirect resource pressure on mothers.
    """
    base = {k: v for k, v in BALANCED_BASELINE.items() if k != "init_food"}
    food_range = range(
        max(10, BALANCED_BASELINE.get("init_food", 40)),
        food_max + food_step,
        food_step,
    )

    print(f"\n-- Phase 3 Step 3: Food anchor scan "
          f"(target mother survival >= {target_survival:.0%}) --")

    best_food, best_surv, best_sum = None, -1.0, None
    anchor_food, anchor_sum = None, None

    for food in food_range:
        params = {**base, "init_food": int(food)}
        tasks  = [(dict(params), seed * 1000 + rep, duration)
                  for seed in seeds for rep in range(repeats)]

        if workers <= 1:
            raws = [_run_task(t) for t in tasks]
        else:
            with ProcessPoolExecutor(max_workers=workers) as pool:
                raws = list(pool.map(_run_task, tasks))

        s = _summarize_ovat_runs(raws, duration)
        surv = s["survival_rate_mean"]
        print(f"  init_food={food:5d}  m_surv={surv:.2f}  "
              f"tailE={s['tail_energy_mean']:.3f}  "
              f"C_matr={s['child_maturation_rate_mean']:.3f}")

        if surv > best_surv:
            best_surv, best_food, best_sum = surv, int(food), s

        if anchor_food is None and surv >= target_survival:
            anchor_food, anchor_sum = int(food), s
            print(f"\n  Anchor found: init_food={anchor_food} (m_surv={surv:.2f})")
            break

    if anchor_food is None:
        anchor_food = best_food if best_food else int(list(food_range)[-1])
        anchor_sum  = best_sum
        print(f"\n  WARNING: no anchor found up to init_food={int(list(food_range)[-1])}. "
              f"Using argmax: init_food={anchor_food} (m_surv={best_surv:.2f})")

    return anchor_food, anchor_sum


def run_set(set_id: str, sweep: dict, baseline: dict, seeds: list,
            duration: int, tail_window: int, workers: int = 1,
            repeats: int = 1) -> list:
    """Run OVAT sweep for one parameter set.  Returns list of summary dicts."""
    key     = sweep["key"]
    results = []

    for val in sweep["values"]:
        params = dict(baseline)
        params[key] = int(val) if key == "init_food" else float(val)

        tasks = [(dict(params), seed * 1000 + rep, duration)
                 for seed in seeds for rep in range(repeats)]

        if workers <= 1:
            raws = [_run_task(t) for t in tasks]
        else:
            with ProcessPoolExecutor(max_workers=workers) as pool:
                raws = list(pool.map(_run_task, tasks))

        s = _summarize_ovat_runs(raws, duration, tail_window)
        s["param_value"] = params[key]
        results.append(s)

        print(
            f"  Set {set_id} [{key}={params[key]}]  "
            f"runs={s['num_runs']}  "
            f"child_E={s['child_mean_energy_mean']:.3f}  "
            f"child_mu={s['child_death_tick_mean_mean']:.1f}  "
            f"m_surv={s['survival_rate_mean']:.2f}  "
            f"tailE={s['tail_energy_mean']:.3f}  "
            f"C_matr={s['child_maturation_rate_mean']:.3f}"
        )

    return results


def save_csv_ovat(results: list, path: str) -> None:
    if not results:
        return
    fieldnames = [
        "param_value", "num_runs",
        "child_mean_energy_mean", "child_mean_energy_sd",
        "child_death_tick_mean_mean", "child_death_tick_mean_sd",
        "child_maturation_rate_mean", "child_maturation_rate_sd",
        "survival_rate_mean", "survival_rate_sd",
        "tail_energy_mean", "tail_energy_sd",
        "care_pct_mean",
    ]
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in results:
            writer.writerow({k: row.get(k, "") for k in fieldnames})


# ─────────────────────────────────────────────────────────────────────────────
# Validation helpers
# ─────────────────────────────────────────────────────────────────────────────

def validate_params(params: dict, duration: int, n_seeds: int = None,
                    n_repeats: int = 1, workers: int = 1) -> tuple:
    """Run VALIDATION_SEEDS (or n_seeds) x n_repeats for diagnostic validation."""
    seeds = VALIDATION_SEEDS if n_seeds is None else list(range(42, 42 + n_seeds))
    tasks = [(dict(params), seed * 1000 + rep, duration)
             for seed in seeds for rep in range(n_repeats)]

    if workers <= 1:
        raw = [_run_task(t) for t in tasks]
    else:
        with ProcessPoolExecutor(max_workers=workers) as pool:
            raw = list(pool.map(_run_task, tasks))

    for idx, r in enumerate(raw):
        seed_idx = idx // n_repeats
        rep_idx  = idx % n_repeats
        r["base_seed"] = seeds[seed_idx]
        r["repeat"]    = rep_idx + 1
        r["run_seed"]  = seeds[seed_idx] * 1000 + rep_idx

    labels  = [f"{seeds[i // n_repeats]}-r{(i % n_repeats) + 1}" for i in range(len(raw))]
    summary = summarize_repeats(raw, duration)
    return raw, labels, summary


# ─────────────────────────────────────────────────────────────────────────────
# Pipeline helpers (Steps 1–8)
# ─────────────────────────────────────────────────────────────────────────────

def _detect_cliff_edge_from_ovat(ovat_all: dict, synthetic_baseline: dict,
                                  min_surv_range: float = 0.20) -> tuple:
    """Classify OVAT results into HARSH / BALANCED / EASY zones (same as Phase 2)."""
    detected = dict(synthetic_baseline)
    clarity  = {}
    balanced_target = SELECTION_TARGETS["balanced"]["target_survival_rate"]

    for set_id, data in ovat_all.items():
        key  = SENSITIVITY_SWEEPS[set_id]["key"]
        xs   = np.array([d["param_value"]        for d in data], dtype=float)
        surv = np.array([d["survival_rate_mean"]  for d in data], dtype=float)

        surv_range = float(np.nanmax(surv) - np.nanmin(surv))
        is_clear   = surv_range >= min_surv_range

        zone_map = {}
        for x, s in zip(xs, surv):
            zone = ("DEAD" if s < 0.10 else "HARSH" if s <= 0.45
                    else "BALANCED" if s <= 0.75 else "EASY")
            zone_map[f"{x:g}"] = zone

        if is_clear:
            best_i   = int(np.argmin(np.abs(surv - balanced_target)))
            edge_val = float(xs[best_i])
            detected[key] = int(round(edge_val)) if key == "init_food" else round(edge_val, 6)
            justification = (f"BALANCED-closest={edge_val:g} "
                             f"(surv={surv[best_i]:.2f}); zones: {zone_map}")
        else:
            justification = (f"Flat — Δsurvival={surv_range:.3f} < {min_surv_range}; "
                             f"zones: {zone_map}")

        clarity[set_id] = {
            "key":           key,
            "is_clear":      is_clear,
            "surv_range":    round(surv_range, 3),
            "detected_val":  detected[key],
            "synthetic_val": float(synthetic_baseline.get(key, 0)),
            "justification": justification,
        }

    return detected, clarity


def _pipeline_multidim_configs(detected: dict, baseline: dict) -> tuple:
    """Build the full init_food × eat_gain × move_cost validation grid."""
    from itertools import product as iproduct

    food_values = SENSITIVITY_SWEEPS["A"]["values"]
    eat_values  = SENSITIVITY_SWEEPS["B"]["values"]
    cost_values = SENSITIVITY_SWEEPS["C"]["values"]

    base_params = dict(baseline)
    configs = []
    for food, eat, cost in iproduct(food_values, eat_values, cost_values):
        p = dict(base_params)
        p["init_food"] = int(food)
        p["eat_gain"]  = float(eat)
        p["move_cost"] = float(cost)
        p["name"]      = "candidate"
        configs.append(p)

    desc = (f"{len(food_values)} init_food × {len(eat_values)} eat_gain × "
            f"{len(cost_values)} move_cost = {len(configs)} configs")
    return configs, desc


# ─────────────────────────────────────────────────────────────────────────────
# JSON / CSV output helpers
# ─────────────────────────────────────────────────────────────────────────────

def save_summary_json(summary: dict, out_dir: str) -> None:
    path = os.path.join(out_dir, "auto_baseline_summary.json")
    with open(path, "w") as f:
        json.dump(summary, f, indent=2, default=str)
    print(f"  Saved summary JSON -> {path}")


def save_selected_ecologies_json(summary: dict, out_dir: str) -> None:
    selected = {}
    for name in ["harsh", "balanced", "easy"]:
        if name in summary:
            selected[name] = {
                "selected_config":    summary[name].get("selected_config", {}),
                "selection_status":   summary[name].get("selection_status", "unknown"),
                "validation_summary": summary[name].get("validation_summary", {}),
            }
    path = os.path.join(out_dir, "selected_ecologies.json")
    with open(path, "w") as f:
        json.dump(selected, f, indent=2)
    print(f"  Saved selected ecologies -> {path}")


def save_validation_csv(name: str, results: list, out_dir: str) -> None:
    path = os.path.join(out_dir, f"{name}_validation.csv")
    fieldnames = [
        "base_seed", "repeat", "run_seed", "final_pop", "mean_energy", "final_energy",
        "child_maturation_rate", "child_death_tick_mean", "care_pct", "forage_pct", "self_pct",
    ]
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(results)
    print(f"  Saved validation CSV -> {path}")


def print_validation_runs(name: str, results: list) -> None:
    print(f"\n  {name.upper()} validation runs:")
    print(f"  {'seed':>6}  {'pop':>5}  {'energy':>8}  {'C_matr':>8}  {'child_mu':>10}  {'care%':>6}")
    for r in results:
        print(
            f"  {r.get('base_seed', '?'):>6}  {r['final_pop']:>5}  "
            f"{r['final_energy']:>8.3f}  "
            f"{r.get('child_maturation_rate', 0.0):>8.3f}  "
            f"{r.get('child_death_tick_mean', 0.0):>10.1f}  "
            f"{r.get('care_pct', 0.0):>6.2%}"
        )


def build_validation_summary(results: list) -> list:
    return [
        {
            "seed":                  r.get("base_seed"),
            "repeat":                r.get("repeat"),
            "run_seed":              r.get("run_seed"),
            "final_pop":             r["final_pop"],
            "mean_energy":           r["mean_energy"],
            "final_energy":          r["final_energy"],
            "child_maturation_rate": r.get("child_maturation_rate", 0.0),
            "child_death_tick_mean": r.get("child_death_tick_mean", 0.0),
            "care_pct":              r.get("care_pct", 0.0),
        }
        for r in results
    ]


# ─────────────────────────────────────────────────────────────────────────────
# Care-trap diagnostic (Workstream 1)
# ─────────────────────────────────────────────────────────────────────────────

def run_caretrap_diagnostic(out_dir: str, seed: int = 42,
                             duration: int = MAX_TICKS) -> None:
    """
    Run one seed under BALANCED_BASELINE (unbiased weights) and produce the
    5 care-trap diagnostic plots.  No long sweep needed.
    """
    params = dict(BALANCED_BASELINE)
    params["name"] = "caretrap"
    cfg        = make_config(params, duration)
    cfg.seed   = seed

    print(f"\n-- Phase 3 Care-Trap Diagnostic (seed={seed}, duration={duration}) --")
    for k in ("move_cost", "eat_gain", "init_food", "care_weight",
              "forage_weight", "self_weight"):
        print(f"  {k:<20} = {params.get(k, getattr(cfg, k, '?'))}")

    sim  = Phase3Simulation(cfg)
    diag = sim.run_diagnostic()

    os.makedirs(out_dir, exist_ok=True)
    np.savez(
        os.path.join(out_dir, "caretrap_diag.npz"),
        **{k: v for k, v in diag.items() if isinstance(v, np.ndarray)},
    )
    print(f"  Diagnostic data saved -> caretrap_diag.npz")

    try:
        from experiments.phase3_survival_full.plot import (
            plot_caretrap_motivation_scores,
            plot_caretrap_action_strip,
            plot_caretrap_held_food,
            plot_caretrap_child_energy,
            plot_caretrap_failed_care_bar,
        )
        plot_caretrap_motivation_scores(diag, out_dir)
        plot_caretrap_action_strip(diag, out_dir)
        plot_caretrap_held_food(diag, out_dir, mother_idx=0)
        plot_caretrap_child_energy(diag, out_dir)
        plot_caretrap_failed_care_bar(diag, out_dir)
    except Exception as exc:
        print(f"  [warn] Care-trap plot failed: {exc}")
        import traceback
        traceback.print_exc()

    print(f"\nDone.  Care-trap plots saved to: {out_dir}")


# ─────────────────────────────────────────────────────────────────────────────
# Diagnostic plots (delegates to plot.py)
# ─────────────────────────────────────────────────────────────────────────────

def generate_diagnostic_plots(name: str, results: list, params: dict,
                               labels: list, duration: int, out_dir: str) -> None:
    try:
        from experiments.phase3_survival_full.plot import (
            plot_multiseed_condition_phase3,
            plot_motivation_split,
            plot_validation_p3,
            plot_motivation_selection_over_time_p3,
            plot_action_selection_over_time_p3,
            plot_stacked_motivation_p3,
            plot_care_child_energy_correlation_p3,
            plot_forage_energy_correlation_p3,
            plot_rate_sum_check_p3,
            plot_state_space_energy_motivation_p3,
            plot_food_consumption_p3,
            plot_spatial_heatmap_p3,
            plot_energy_expenditure_breakdown_p3,
            plot_homeostatic_balance_p3,
            plot_child_metrics_p3,
        )
        # Original Phase 3 overview plots
        plot_multiseed_condition_phase3(
            name=name, results=results, params=params,
            run_labels=labels, duration=duration, out_dir=out_dir,
        )
        plot_motivation_split(name=name, results=results, out_dir=out_dir)

        # Phase 2-style extended suite
        plot_validation_p3(name=name, results=results, params=params,
                           duration=duration, out_dir=out_dir)
        plot_motivation_selection_over_time_p3(name=name, results=results,
                                               duration=duration, out_dir=out_dir)
        plot_action_selection_over_time_p3(name=name, results=results,
                                           duration=duration, out_dir=out_dir)
        plot_stacked_motivation_p3(name=name, results=results,
                                   duration=duration, out_dir=out_dir)
        plot_care_child_energy_correlation_p3(name=name, results=results,
                                              duration=duration, out_dir=out_dir)
        plot_forage_energy_correlation_p3(name=name, results=results,
                                          duration=duration, out_dir=out_dir)
        plot_rate_sum_check_p3(name=name, results=results,
                               duration=duration, out_dir=out_dir)
        plot_state_space_energy_motivation_p3(name=name, results=results,
                                              duration=duration, out_dir=out_dir)
        plot_food_consumption_p3(name=name, results=results,
                                 duration=duration, out_dir=out_dir)
        plot_spatial_heatmap_p3(name=name, results=results, out_dir=out_dir)
        plot_energy_expenditure_breakdown_p3(name=name, results=results, out_dir=out_dir)
        plot_homeostatic_balance_p3(name=name, results=results,
                                    duration=duration, out_dir=out_dir)
        plot_child_metrics_p3(name=name, results=results,
                              duration=duration, out_dir=out_dir)
    except Exception as exc:
        print(f"  [warn] Diagnostic plots failed: {exc}")
        import traceback
        traceback.print_exc()


# ─────────────────────────────────────────────────────────────────────────────
# 8-step pipeline
# ─────────────────────────────────────────────────────────────────────────────

def _run_pipeline(args, out_dir: str, n_workers: int) -> None:
    N_SEEDS           = 10
    N_REPEATS         = 3
    N_RUNS_PER_CONFIG = N_SEEDS * N_REPEATS
    pipeline_seeds    = list(range(42, 42 + N_SEEDS))
    duration      = args.duration

    # Step 1 — Mechanics lock confirmation
    print("\n" + "=" * 70)
    print("PHASE 3 Step 1 — Mechanics Lock")
    print("=" * 70)
    print("  grid            = 50 x 50")
    print("  initial_energy  = 1.0")
    print("  hunger_rate     = 1/35 (locked)")
    print("  ISM             =", round(ISM, 3), "(locked)")
    print("  softmax_tau     = 0.1")
    print("  care_weight     = forage_weight = self_weight = 1.0 (unbiased)")
    print("  mutation        = OFF")
    print("  reproduction    = OFF")
    print("  children        = ON  (15 mother–child pairs)")
    print("  plasticity      = OFF")

    # Step 2 — Provisional baseline
    synthetic = dict(BALANCED_BASELINE)
    print("\n" + "=" * 70)
    print("PHASE 3 Step 2 — Provisional Baseline (loaded from Phase 2 BALANCED)")
    print("=" * 70)
    for k in ("hunger_rate", "move_cost", "eat_gain", "init_food", "rest_recovery"):
        print(f"  {k:<22} = {synthetic[k]}")

    # Step 3 — Food anchor scan
    print("\n" + "=" * 70)
    print("PHASE 3 Step 3 — Food Anchor Scan")
    print("=" * 70)
    anchor_food, _ = find_food_anchor(
        seeds=pipeline_seeds, duration=duration, workers=n_workers,
        target_survival=0.50, food_step=50, food_max=3000,
        repeats=N_REPEATS,
    )
    anchored_baseline = {**synthetic, "init_food": anchor_food}
    print(f"\n  Anchor init_food = {anchor_food}")

    # Step 4 — OVAT
    ovat_dir = os.path.join(out_dir, "sensitivity_ovat")
    os.makedirs(ovat_dir, exist_ok=True)
    print("\n" + "=" * 70)
    print(f"PHASE 3 Step 4 — OVAT Sensitivity ({N_SEEDS} seeds x {N_REPEATS} repeats = {N_RUNS_PER_CONFIG} runs per point)")
    print("=" * 70)

    ovat_all = {}
    for set_id in SENSITIVITY_SWEEPS:
        sw = SENSITIVITY_SWEEPS[set_id]
        n_vals = len(sw["values"])
        print(f"\n-- Set {set_id}: '{sw['key']}'  ({n_vals} values x {N_SEEDS} seeds x {N_REPEATS} repeats = {n_vals * N_RUNS_PER_CONFIG} runs) --")
        results = run_set(
            set_id=set_id, sweep=sw, baseline=anchored_baseline,
            seeds=pipeline_seeds, duration=duration,
            tail_window=TAIL_WINDOW, workers=n_workers,
            repeats=N_REPEATS,
        )
        ovat_all[set_id] = results
        save_csv_ovat(results, os.path.join(ovat_dir, f"set_{set_id}_{sw['key']}.csv"))

    # OVAT sensitivity map plot
    try:
        from experiments.phase3_survival_full.plot import plot_ovat_sensitivity_map
        plot_ovat_sensitivity_map(ovat_all, anchored_baseline, ovat_dir)
    except Exception as exc:
        print(f"  [warn] OVAT plot failed: {exc}")

    # Step 5 — Zone classification
    print("\n" + "=" * 70)
    print("PHASE 3 Step 5 — OVAT Zone Classification")
    print("=" * 70)
    detected, clarity = _detect_cliff_edge_from_ovat(ovat_all, anchored_baseline)
    for set_id in SENSITIVITY_SWEEPS:
        c = clarity[set_id]
        status = "CLEAR" if c["is_clear"] else "FLAT"
        print(f"  {c['key']:<18}  {c['detected_val']:>10g}  {status:<6}  {c['justification'][:60]}")

    # Step 6 — Multi-parameter validation grid
    print("\n" + "=" * 70)
    print(f"PHASE 3 Step 6 — Validation Grid ({N_SEEDS} seeds x {N_REPEATS} repeats = {N_RUNS_PER_CONFIG} runs per config)")
    print("=" * 70)
    sweep_configs, grid_desc = _pipeline_multidim_configs(detected, anchored_baseline)
    total_runs = len(sweep_configs) * N_RUNS_PER_CONFIG
    print(f"  Grid  : {grid_desc}")
    print(f"  Runs  : {total_runs}  ({len(sweep_configs)} configs x {N_SEEDS} seeds x {N_REPEATS} repeats)")

    sweep_tasks = [(dict(p), seed * 1000 + rep, duration)
                   for p in sweep_configs for seed in pipeline_seeds for rep in range(N_REPEATS)]

    if n_workers <= 1:
        flat_results = [_run_task(t) for t in sweep_tasks]
    else:
        with ProcessPoolExecutor(max_workers=n_workers) as pool:
            flat_results = list(pool.map(_run_task, sweep_tasks))

    sweep_records = []
    print(f"\n  {'#':>4}  {'food':>5}  {'eat':>6}  {'cost':>7}  "
          f"{'child_E':>8}  {'child_mu':>9}  {'m_surv':>7}  {'tailE':>7}")
    for idx, p in enumerate(sweep_configs):
        reps = flat_results[idx * N_RUNS_PER_CONFIG: (idx + 1) * N_RUNS_PER_CONFIG]
        sr   = summarize_repeats(reps, duration)
        sweep_records.append({"params": dict(p), "result": sr})
        if idx % 5 == 0 or idx == len(sweep_configs) - 1:
            print(
                f"  {idx + 1:>4}  {p['init_food']:>5}  {p['eat_gain']:>6.3f}  "
                f"{p['move_cost']:>7.4f}  "
                f"{sr['child_mean_energy_mean']:>8.3f}  "
                f"{sr['child_death_tick_mean_mean']:>9.1f}  "
                f"{sr['final_pop'] / INIT_MOTHERS:>7.2f}  "
                f"{sr['tail_mean_energy']:>7.3f}"
            )

    # Step 7 — Select regimes
    print("\n" + "=" * 70)
    print("PHASE 3 Step 7 — Select HARSH / BALANCED / EASY Regimes")
    print("=" * 70)
    print(f"  {'Condition':<12}  {'Score':>9}  {'child_E':>8}  {'child_mu':>9}  "
          f"{'tailE':>7}  {'m_surv':>7}  Config")
    print("  " + "-" * 85)

    selected_recs  = {}
    scored_all_map = {}
    for cond_name in ["harsh", "balanced", "easy"]:
        best_rec, best_score, all_scored = select_by_penalty_score(cond_name, sweep_records)
        selected_recs[cond_name]   = best_rec
        scored_all_map[cond_name]  = all_scored
        r  = best_rec["result"]
        p  = best_rec["params"]
        print(
            f"  {cond_name.upper():<12}  {best_score:>9.2f}  "
            f"{r['child_mean_energy_mean']:>8.3f}  "
            f"{r['child_death_tick_mean_mean']:>9.1f}  "
            f"{r['tail_mean_energy']:>7.3f}  "
            f"{r['final_pop'] / INIT_MOTHERS:>7.2f}  "
            f"food={p['init_food']} eat={p['eat_gain']:.2f} cost={p['move_cost']:.4f}"
        )

    # Step 8 — Final plots + validation
    print("\n" + "=" * 70)
    print(f"PHASE 3 Step 8 — Final Plots & Validation (N={N_SEEDS} seeds)")
    print("=" * 70)

    final_summary = {}
    for cond_name, rec in selected_recs.items():
        params = dict(rec["params"])
        params["name"] = cond_name
        print(f"\n  Validating + plotting {cond_name.upper()} ...")

        val_results, val_labels, val_summary = validate_params(
            params, duration, n_seeds=N_SEEDS, workers=n_workers,
        )

        print_validation_runs(cond_name, val_results)
        generate_diagnostic_plots(
            name=cond_name, results=val_results, params=params,
            labels=val_labels, duration=duration, out_dir=out_dir,
        )
        save_validation_csv(cond_name, val_results, out_dir)

        final_score = _penalty_score(cond_name, val_summary)
        final_summary[cond_name] = {
            "selected_config":    params,
            "selection_status":   (
                "validated_pass" if is_valid_condition(cond_name, val_summary)
                else "fallback_penalty_score"
            ),
            "penalty_score":      final_score,
            "sweep_summary":      rec["result"],
            "validation_summary": val_summary,
            "validation_runs":    build_validation_summary(val_results),
        }

    final_summary["_pipeline_meta"] = {
        "n_seeds":           N_SEEDS,
        "anchor_food":       anchor_food,
        "anchored_baseline": {k: v for k, v in anchored_baseline.items() if k != "name"},
        "ovat_dir":          ovat_dir,
        "grid_desc":         grid_desc,
        "n_grid_configs":    len(sweep_configs),
        "phase2_anchor":     {k: v for k, v in BALANCED_BASELINE.items() if k != "name"},
    }

    save_summary_json(final_summary, out_dir)
    save_selected_ecologies_json(final_summary, out_dir)
    print(f"\nDone. All outputs saved to: {out_dir}")


# ─────────────────────────────────────────────────────────────────────────────
# Sweep-only mode (Steps 6–8)
# ─────────────────────────────────────────────────────────────────────────────

def _run_sweep(args, out_dir: str, n_workers: int) -> None:
    """Runs Steps 6–8 directly using the SENSITIVITY_SWEEPS grid."""
    from itertools import product as iproduct
    duration = args.duration

    food_values = SENSITIVITY_SWEEPS["A"]["values"]
    eat_values  = SENSITIVITY_SWEEPS["B"]["values"]
    cost_values = SENSITIVITY_SWEEPS["C"]["values"]

    sweep_configs = []
    base = dict(BALANCED_BASELINE)
    for food, eat, cost in iproduct(food_values, eat_values, cost_values):
        p = dict(base)
        p.update({"init_food": int(food), "eat_gain": float(eat), "move_cost": float(cost),
                  "name": "candidate"})
        sweep_configs.append(p)

    _N_SWEEP_SEEDS    = 10
    _N_SWEEP_REPEATS  = 3
    _N_RUNS_PER_CFG   = _N_SWEEP_SEEDS * _N_SWEEP_REPEATS
    sweep_seeds       = list(range(42, 42 + _N_SWEEP_SEEDS))

    print(f"\nPhase 3 sweep mode: {len(sweep_configs)} configs x {_N_SWEEP_SEEDS} seeds x {_N_SWEEP_REPEATS} repeats = "
          f"{len(sweep_configs) * _N_RUNS_PER_CFG} runs  workers={n_workers}")

    sweep_tasks = [
        (dict(p), seed * 1000 + rep, duration)
        for p in sweep_configs
        for seed in sweep_seeds
        for rep in range(_N_SWEEP_REPEATS)
    ]

    if n_workers <= 1:
        flat_results = [_run_task(t) for t in sweep_tasks]
    else:
        with ProcessPoolExecutor(max_workers=n_workers) as pool:
            flat_results = list(pool.map(_run_task, sweep_tasks))

    sweep_records = []
    for idx, p in enumerate(sweep_configs):
        reps = flat_results[idx * _N_RUNS_PER_CFG: (idx + 1) * _N_RUNS_PER_CFG]
        sr   = summarize_repeats(reps, duration)
        sweep_records.append({"params": dict(p), "result": sr})

    summary = {}
    for cond_name in ["harsh", "balanced", "easy"]:
        best_rec, _, _ = select_by_penalty_score(cond_name, sweep_records)
        params = dict(best_rec["params"])
        params["name"] = cond_name

        val_results, val_labels, val_summary = validate_params(
            params, duration, n_repeats=3, workers=n_workers,
        )
        print_validation_runs(cond_name, val_results)
        generate_diagnostic_plots(
            name=cond_name, results=val_results, params=params,
            labels=val_labels, duration=duration, out_dir=out_dir,
        )
        save_validation_csv(cond_name, val_results, out_dir)

        summary[cond_name] = {
            "selected_config":    params,
            "selection_status":   "sweep_mode",
            "validation_summary": val_summary,
            "validation_runs":    build_validation_summary(val_results),
        }

    save_summary_json(summary, out_dir)
    save_selected_ecologies_json(summary, out_dir)
    print(f"\nDone. Outputs saved to: {out_dir}")


# ─────────────────────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────────────────────

def run_experiment(args) -> None:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir = os.path.join(
        PROJECT_ROOT, "outputs", "phase3_survival_full",
        f"auto_{args.duration}_{ts}",
    )
    os.makedirs(out_dir, exist_ok=True)

    n_workers = _n_workers(args.workers)

    print(f"Phase 3 Ecological Calibration  —  mode={args.mode}")
    print(f"Output dir : {out_dir}")
    print(f"Duration   : {args.duration} ticks")
    print(f"Workers    : {n_workers}")

    if args.mode == "pipeline":
        _run_pipeline(args, out_dir, n_workers)
        return

    if args.mode == "sweep":
        _run_sweep(args, out_dir, n_workers)
        return

    if args.mode == "caretrap":
        caretrap_dir = os.path.join(
            PROJECT_ROOT, "outputs", "phase3_survival_full", "caretrap_diagnostic"
        )
        run_caretrap_diagnostic(caretrap_dir, seed=42, duration=args.duration)
        return

    # single mode — one config, all diagnostic plots
    params = dict(BALANCED_BASELINE)
    params["name"] = "single"
    results, labels, summary = validate_params(params, args.duration, workers=n_workers)
    print_validation_runs("single", results)
    generate_diagnostic_plots(
        name="single", results=results, params=params,
        labels=labels, duration=args.duration, out_dir=out_dir,
    )
    save_validation_csv("single", results, out_dir)
    save_summary_json({"single": {"selected_config": params, "validation_summary": summary,
                                   "validation_runs": build_validation_summary(results)}},
                      out_dir)
    print(f"\nDone. Outputs saved to: {out_dir}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Phase 3 Ecological Calibration")
    parser.add_argument("--duration", type=int, default=400)
    parser.add_argument("--repeats",  type=int, default=3,
                        help="Repeats per seed (10 seeds x repeats = runs per config)")
    parser.add_argument("--mode", type=str,
                        choices=["pipeline", "sweep", "single", "caretrap"],
                        default="pipeline")
    parser.add_argument("--workers", type=int, default=4,
                        help="Parallel workers (0=auto, 1=sequential)")
    args = parser.parse_args()
    run_experiment(args)
