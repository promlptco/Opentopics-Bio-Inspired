#!/usr/bin/env python3
"""
Phase 7 -- Mutation-Enabled Genetic Evolution With Care-Specific Plasticity

Tests whether lifetime plasticity scaffolds care behavior and shifts the
selection gradient toward inherited care (Baldwin Effect test).

Two conditions (both mutation ON):
  no_plasticity -- plasticity OFF; Phase 6 exact replay
  plasticity    -- plasticity ON; care_weight only; kin-conditional (own child)

Same frozen ecology and initial genome distributions as Phase 6.
Plasticity triggers only from successful own-child feeding (benefit > 0).
Only expressed_care_weight is updated; forage_weight and self_weight unchanged.

Success criteria (Baldwin scaffolding):
  - plasticity improves crash_tick / max_gen / child_surv over no_plasticity
  - realized FEED_CHILD rate increases
  - selection gradient (Spearman r, initial_cw vs descendants) becomes more positive
  - mean genome care_weight increases over time in plasticity condition

Usage:
    python experiments/phase7_evo_with_plasticity/run.py --duration 10000 --seeds 10
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import os
import random as _random
import sys
from collections import defaultdict
from datetime import datetime

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, PROJECT_ROOT)

from config import Config
from simulation.simulation import Simulation
from evolution.genome import Genome

# ── Frozen ecology (identical to Phase 6) ─────────────────────────────────────
REPRO_COST           = 0.10
INIT_FOOD            = 45
REPLENISH_AMOUNT     = 20
THRESHOLD_RATIO      = 0.5
CONTINUOUS_FOOD_RATE = 0.1
CONTINUOUS_FOOD_MAX  = 200
INFANT_STARVATION    = 1.5
MUTATION_RATE        = 0.1    # hardcoded in Genome.mutate()
MUTATION_SIGMA       = 0.05
N_INIT_MOTHERS       = 12
EXTINCT_PATIENCE     = 200

# ── Plasticity settings ────────────────────────────────────────────────────────
PLASTIC_GAIN = 0.5        # reward scaling in plastic_update
INIT_LR_LOW  = 0.1        # lower bound for initial learning_rate
INIT_LR_HIGH = 0.5        # upper bound for initial learning_rate

CONDITIONS = [
    {"label": "no_plasticity", "plasticity_on": False},
    {"label": "plasticity",    "plasticity_on": True},
]

COLORS = {
    "no_plasticity": "#9467bd",   # matches Phase 6 "evolving"
    "plasticity":    "#17becf",   # teal for Phase 7
}
NICE = {
    "no_plasticity": "Evolving (plasticity OFF)",
    "plasticity":    "Evolving (plasticity ON)",
}

# ── Helpers ────────────────────────────────────────────────────────────────────
def _nanmean(lst):
    vals = [v for v in lst if v is not None and not (isinstance(v, float) and math.isnan(v))]
    return float(np.mean(vals)) if vals else float("nan")

def _nanstd(lst):
    vals = [v for v in lst if v is not None and not (isinstance(v, float) and math.isnan(v))]
    return float(np.std(vals)) if len(vals) > 1 else 0.0

def _spearman(x, y):
    n = len(x)
    if n < 3:
        return float("nan")
    rx = np.argsort(np.argsort(np.array(x, dtype=float))).astype(float)
    ry = np.argsort(np.argsort(np.array(y, dtype=float))).astype(float)
    cc = np.corrcoef(rx, ry)
    return float(cc[0, 1]) if cc.shape == (2, 2) else float("nan")

# Metrics that are 0 (not NaN) when population is extinct
_ZERO_ON_EXTINCT = {
    "total_pop", "n_births_this_tick", "n_child_deaths_hunger_this_tick",
    "n_child_matured_this_tick", "n_mother_deaths_this_tick",
    "n_feed_this_tick", "n_plasticity_events_this_tick",
}

def _zero_row(t2, seed, cond_label):
    return {
        "tick":    t2,
        "seed":    seed,
        "condition": cond_label,
        "n_mothers":  0,
        "n_children": 0,
        "total_pop":  0,
        "food_count":                          float("nan"),
        "mean_genome_care_weight":             float("nan"),
        "mean_forage_weight":                  float("nan"),
        "mean_self_weight":                    float("nan"),
        "mean_expressed_care_weight":          float("nan"),
        "mean_learning_rate":                  float("nan"),
        "mean_mother_energy":                  float("nan"),
        "mean_child_hunger":                   float("nan"),
        "n_births_this_tick":                  0,
        "n_child_deaths_hunger_this_tick":     0,
        "n_child_matured_this_tick":           0,
        "n_mother_deaths_this_tick":           0,
        "n_feed_this_tick":                    0,
        "n_plasticity_events_this_tick":       0,
    }


# ── Config ─────────────────────────────────────────────────────────────────────
def make_config(cond: dict, seed: int, duration: int) -> Config:
    cfg = Config()
    cfg.seed                           = seed
    cfg.max_ticks                      = duration
    cfg.init_mothers                   = N_INIT_MOTHERS
    cfg.reproduction_cost              = REPRO_COST
    cfg.infant_starvation_multiplier   = INFANT_STARVATION
    cfg.init_food                      = INIT_FOOD
    cfg.food_replenish_amount          = REPLENISH_AMOUNT
    cfg.food_replenish_threshold_ratio = THRESHOLD_RATIO
    cfg.continuous_food_rate           = CONTINUOUS_FOOD_RATE
    cfg.continuous_food_max            = CONTINUOUS_FOOD_MAX
    cfg.hunger_rate                    = 0.008
    cfg.reproduction_enabled           = True
    cfg.children_enabled               = True
    cfg.care_enabled                   = True
    cfg.mutation_enabled               = True
    cfg.plasticity_enabled             = cond["plasticity_on"]
    cfg.lock_learning_rate             = not cond["plasticity_on"]
    cfg.plasticity_kin_conditional     = True   # own-child only
    cfg.plastic_gain                   = PLASTIC_GAIN
    cfg.plasticity_energy_cost         = 0.0
    cfg.plasticity_noise_sigma         = 0.0
    # fallback genome weights (overridden by initialize(genomes))
    cfg.care_weight   = 0.3
    cfg.forage_weight = 0.85
    cfg.self_weight   = 0.30
    return cfg


def make_initial_genomes(seed: int, include_learning_rate: bool = False) -> list:
    """12 founding genomes. care/forage/self identical to Phase 6 (same RNG seed).
    For plasticity condition, learning_rate ~ U(0.1, 0.5) from a separate RNG
    so it does not shift the care/forage/self sequence."""
    rng    = _random.Random(seed * 999983 + 7)   # same sequence as Phase 6
    lr_rng = _random.Random(seed * 777777 + 13)  # separate RNG for learning_rate
    genomes = []
    for _ in range(N_INIT_MOTHERS):
        cw = rng.uniform(0.0, 0.6)
        fw = rng.uniform(0.7, 1.0)
        sw = rng.uniform(0.2, 0.6)
        lr = lr_rng.uniform(INIT_LR_LOW, INIT_LR_HIGH) if include_learning_rate else 0.0
        genomes.append(Genome(care_weight=cw, forage_weight=fw, self_weight=sw,
                               learning_rate=lr))
    return genomes


# ── Single simulation run ──────────────────────────────────────────────────────
def run_single(cond: dict, seed: int, duration: int) -> dict:
    cfg = make_config(cond, seed, duration)
    sim = Simulation(cfg)

    genomes_list = make_initial_genomes(seed, include_learning_rate=cond["plasticity_on"])
    init_care = {i: g.care_weight    for i, g in enumerate(genomes_list)}
    init_lr   = {i: g.learning_rate  for i, g in enumerate(genomes_list)}
    sim.initialize(genomes_list)

    per_tick:              list[dict] = []
    mut_deltas:            list[dict] = []
    lin_births:            dict       = defaultdict(int)
    lin_last_tick:         dict       = {i: 0 for i in range(N_INIT_MOTHERS)}
    lin_birth_care:        dict       = defaultdict(list)
    lin_plasticity_events: dict       = defaultdict(int)

    crash_tick = -1
    max_gen    = 1
    ext_count  = 0

    for t in range(duration):
        b0 = len(sim.logger.birth_records)
        c0 = len(sim.logger.care_records)
        d0 = len(sim.logger.death_records)

        sim.step()
        sim.tick += 1

        mothers  = sim.mothers
        children = sim.children
        n_m   = len(mothers)
        n_c   = len(children)
        total = n_m + n_c

        care_ws  = [m.genome.care_weight       for m in mothers]
        forg_ws  = [m.genome.forage_weight     for m in mothers]
        self_ws  = [m.genome.self_weight       for m in mothers]
        expr_ws  = [m.expressed_care_weight    for m in mothers]
        lr_vals  = [m.genome.learning_rate     for m in mothers]
        energies = [m.energy                   for m in mothers]
        hungers  = [c.hunger                   for c in children]
        food     = len(sim.world.food_positions)

        new_births = sim.logger.birth_records[b0:]
        new_care   = sim.logger.care_records[c0:]
        new_deaths = sim.logger.death_records[d0:]

        n_born   = len(new_births)
        n_ch_hd  = sum(1 for d in new_deaths if d.agent_type == "child" and d.cause == "hunger")
        n_ch_mat = sum(1 for d in new_deaths if d.agent_type == "child" and d.cause == "matured")
        n_m_died = sum(1 for d in new_deaths if d.agent_type == "mother")
        n_feed   = sum(1 for r in new_care   if r.benefit > 0)
        # Meaningful plasticity events: own-child, successful feed, hunger actually reduced
        n_plastic = sum(
            1 for r in new_care
            if r.is_own_child and r.success and r.benefit > 0
        )

        for m in mothers:
            if m.generation > max_gen: max_gen = m.generation
        for c in children:
            if c.generation > max_gen: max_gen = c.generation

        if total == 0 and crash_tick == -1:
            crash_tick = t + 1
        ext_count = ext_count + 1 if total == 0 else 0

        # Lineage tracking
        for br in new_births:
            lid = br.mother_lineage_id
            lin_births[lid] += 1
            lin_birth_care[lid].append(br.mother_care_weight)
        for m in mothers:
            lin_last_tick[m.lineage_id] = t + 1
        for c in children:
            lin_last_tick[c.lineage_id] = t + 1

        # Mutation deltas (child genome care_weight vs parent)
        for br in new_births:
            child_agent = sim._child_by_id.get(br.child_id)
            if child_agent is not None and child_agent.genome is not None:
                mut_deltas.append({
                    "seed":        seed,
                    "tick":        t + 1,
                    "condition":   cond["label"],
                    "lineage_id":  br.mother_lineage_id,
                    "mother_care": br.mother_care_weight,
                    "child_care":  child_agent.genome.care_weight,
                    "delta_care":  child_agent.genome.care_weight - br.mother_care_weight,
                })

        # Plasticity events per lineage
        for r in new_care:
            if r.is_own_child and r.success and r.benefit > 0:
                lin_plasticity_events[r.mother_lineage_id] += 1

        row = {
            "tick":    t + 1,
            "seed":    seed,
            "condition": cond["label"],
            "n_mothers":  n_m,
            "n_children": n_c,
            "total_pop":  total,
            "food_count":                          food if total > 0 else float("nan"),
            "mean_genome_care_weight":             _nanmean(care_ws),
            "mean_forage_weight":                  _nanmean(forg_ws),
            "mean_self_weight":                    _nanmean(self_ws),
            "mean_expressed_care_weight":          _nanmean(expr_ws),
            "mean_learning_rate":                  _nanmean(lr_vals),
            "mean_mother_energy":                  _nanmean(energies),
            "mean_child_hunger":                   _nanmean(hungers),
            "n_births_this_tick":                  n_born,
            "n_child_deaths_hunger_this_tick":     n_ch_hd,
            "n_child_matured_this_tick":           n_ch_mat,
            "n_mother_deaths_this_tick":           n_m_died,
            "n_feed_this_tick":                    n_feed,
            "n_plasticity_events_this_tick":       n_plastic,
        }
        per_tick.append(row)

        if ext_count >= EXTINCT_PATIENCE:
            for t2 in range(t + 2, duration + 1):
                per_tick.append(_zero_row(t2, seed, cond["label"]))
            break

    # ── Outcomes ───────────────────────────────────────────────────────────────
    all_deaths   = sim.logger.death_records
    total_ch_hd  = sum(1 for d in all_deaths if d.agent_type == "child" and d.cause == "hunger")
    total_ch_mat = sum(1 for d in all_deaths if d.agent_type == "child" and d.cause == "matured")
    resolved     = total_ch_hd + total_ch_mat
    child_surv   = total_ch_mat / resolved if resolved > 0 else float("nan")

    total_births   = len(sim.logger.birth_records)
    total_feeds    = sum(1 for r in sim.logger.care_records if r.benefit > 0)
    total_plastics = sum(
        1 for r in sim.logger.care_records
        if r.is_own_child and r.success and r.benefit > 0
    )

    init_mean_cw = _nanmean(list(init_care.values()))
    init_mean_lr = _nanmean(list(init_lr.values()))
    final_cw     = _nanmean([m.genome.care_weight   for m in sim.mothers]) if sim.mothers else float("nan")
    final_lr     = _nanmean([m.genome.learning_rate for m in sim.mothers]) if sim.mothers else float("nan")

    # Temporal care_weight trend: mean in first 100 vs last 100 alive ticks
    alive_rows = [r for r in per_tick if r["n_mothers"] > 0]
    first_100  = alive_rows[:100]
    last_100   = alive_rows[-100:]
    early_cw   = _nanmean([r["mean_genome_care_weight"] for r in first_100])
    late_cw    = _nanmean([r["mean_genome_care_weight"] for r in last_100])
    care_increased_temporal = (
        not math.isnan(early_cw) and not math.isnan(late_cw) and late_cw > early_cw
    )

    outcomes = {
        "condition":               cond["label"],
        "seed":                    seed,
        "plasticity_on":           cond["plasticity_on"],
        "crash_tick":              crash_tick,
        "survived_to_end":         crash_tick == -1,
        "final_pop":               len(sim.mothers),
        "max_gen":                 max_gen,
        "total_births":            total_births,
        "total_feed_events":       total_feeds,
        "total_plasticity_events": total_plastics,
        "child_surv_rate":         child_surv,
        "n_child_hunger_deaths":   total_ch_hd,
        "n_child_matured":         total_ch_mat,
        "initial_mean_care_wt":    init_mean_cw,
        "final_mean_care_wt":      final_cw,
        "initial_mean_lr":         init_mean_lr,
        "final_mean_lr":           final_lr,
        "early_cw_mean":           early_cw,
        "late_cw_mean":            late_cw,
        "care_increased_temporal": care_increased_temporal,
    }

    # ── Lineage outcomes ───────────────────────────────────────────────────────
    lin_out: list[dict] = []
    for lid in range(N_INIT_MOTHERS):
        lin_out.append({
            "seed":                   seed,
            "condition":              cond["label"],
            "lineage_id":             lid,
            "initial_care_weight":    init_care.get(lid, float("nan")),
            "total_descendants":      lin_births[lid],
            "lineage_last_tick":      lin_last_tick[lid],
            "mean_birth_care_weight": _nanmean(lin_birth_care.get(lid, [])),
            "n_plasticity_events":    lin_plasticity_events.get(lid, 0),
        })

    assert len(per_tick) == duration, f"per_tick={len(per_tick)} != {duration}"
    assert per_tick[-1]["tick"] == duration

    return {
        "outcomes":   outcomes,
        "per_tick":   per_tick,
        "lin_out":    lin_out,
        "mut_deltas": mut_deltas,
    }


# ── Plot helpers ───────────────────────────────────────────────────────────────
def _mean_sd_over_seeds(arr2d: np.ndarray):
    with np.errstate(all="ignore"):
        mn = np.nanmean(arr2d, axis=0)
        sd = np.nanstd(arr2d, axis=0)
    return mn, sd

def _rolling_child_surv(mat_arr: np.ndarray, hd_arr: np.ndarray, window: int) -> np.ndarray:
    n_seeds, T = mat_arr.shape
    result = np.full((n_seeds, T), np.nan)
    for s in range(n_seeds):
        cum_m = np.concatenate([[0.0], np.cumsum(mat_arr[s].astype(float))])
        cum_h = np.concatenate([[0.0], np.cumsum(hd_arr[s].astype(float))])
        for t in range(T):
            lo    = max(0, t - window + 1)
            m_sum = cum_m[t + 1] - cum_m[lo]
            h_sum = cum_h[t + 1] - cum_h[lo]
            tot   = m_sum + h_sum
            result[s, t] = m_sum / tot if tot > 0 else np.nan
    return result


# ── 12 Plot functions ──────────────────────────────────────────────────────────

def plot_01_population(tick_arrs: dict, duration: int, out_dir: str):
    """Population over time: plasticity OFF vs ON."""
    fig, ax = plt.subplots(figsize=(10, 5))
    ticks = np.arange(1, duration + 1)
    for label in ["no_plasticity", "plasticity"]:
        arr = tick_arrs.get(label, {}).get("total_pop")
        if arr is not None:
            for s in range(arr.shape[0]):
                ax.plot(ticks, arr[s], alpha=0.2, lw=0.7, color=COLORS[label])
            mn, sd = _mean_sd_over_seeds(arr)
            ax.plot(ticks, mn, color=COLORS[label], lw=2, label=NICE[label])
            ax.fill_between(ticks, np.maximum(0, mn - sd), mn + sd,
                            alpha=0.2, color=COLORS[label])
    ax.set_xlabel("Tick")
    ax.set_ylabel("Total population")
    ax.set_title("Phase 7 - Population over time: Phase 6 vs Phase 7")
    ax.legend()
    fig.tight_layout()
    fig.savefig(os.path.join(out_dir, "01_population_over_time.png"), dpi=120)
    plt.close(fig)


def plot_02_extinction_time(all_outcomes: list, duration: int, out_dir: str):
    """Extinction time by seed: plasticity OFF vs ON."""
    fig, ax = plt.subplots(figsize=(7, 5))
    for i, cond_label in enumerate(["no_plasticity", "plasticity"]):
        vals = [o["crash_tick"] if o["crash_tick"] != -1 else duration
                for o in all_outcomes if o["condition"] == cond_label]
        x = np.full(len(vals), i) + np.random.uniform(-0.15, 0.15, len(vals))
        ax.scatter(x, vals, color=COLORS[cond_label], alpha=0.75, s=55, zorder=3)
        if vals:
            ax.hlines(np.mean(vals), i - 0.3, i + 0.3,
                      color=COLORS[cond_label], lw=2.5, zorder=4,
                      label=f"{NICE[cond_label]}: mean={np.mean(vals):.0f}")
    ax.set_xticks([0, 1])
    ax.set_xticklabels([NICE[c] for c in ["no_plasticity", "plasticity"]], rotation=10, ha="right")
    ax.set_ylabel("Extinction tick")
    ax.set_title("Phase 7 - Extinction time by seed: plasticity OFF vs ON")
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(os.path.join(out_dir, "02_extinction_time.png"), dpi=120)
    plt.close(fig)


def plot_03_max_generation(all_outcomes: list, out_dir: str):
    """Max generation by seed: plasticity OFF vs ON."""
    fig, ax = plt.subplots(figsize=(7, 5))
    for i, cond_label in enumerate(["no_plasticity", "plasticity"]):
        vals = [o["max_gen"] for o in all_outcomes if o["condition"] == cond_label]
        x = np.full(len(vals), i) + np.random.uniform(-0.15, 0.15, len(vals))
        ax.scatter(x, vals, color=COLORS[cond_label], alpha=0.75, s=55, zorder=3)
        if vals:
            ax.hlines(np.mean(vals), i - 0.3, i + 0.3,
                      color=COLORS[cond_label], lw=2.5, zorder=4,
                      label=f"{NICE[cond_label]}: mean={np.mean(vals):.1f}")
    ax.set_xticks([0, 1])
    ax.set_xticklabels([NICE[c] for c in ["no_plasticity", "plasticity"]], rotation=10, ha="right")
    ax.set_ylabel("Max generation reached")
    ax.set_title("Phase 7 - Max generation by seed: plasticity OFF vs ON")
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(os.path.join(out_dir, "03_max_generation.png"), dpi=120)
    plt.close(fig)


def plot_04_inherited_care_weight(tick_arrs: dict, duration: int, out_dir: str):
    """Inherited (genome) care_weight over time for both conditions."""
    fig, ax = plt.subplots(figsize=(10, 5))
    ticks = np.arange(1, duration + 1)
    for label in ["no_plasticity", "plasticity"]:
        arr = tick_arrs.get(label, {}).get("mean_genome_care_weight")
        if arr is not None:
            mn, sd = _mean_sd_over_seeds(arr)
            ax.plot(ticks, mn, color=COLORS[label], lw=2, label=NICE[label])
            ax.fill_between(ticks, np.maximum(0, mn - sd), np.minimum(1, mn + sd),
                            alpha=0.15, color=COLORS[label])
    ax.set_xlabel("Tick")
    ax.set_ylabel("Mean genome care_weight")
    ax.set_ylim(0, 1)
    ax.set_title("Phase 7 - Inherited (genome) care_weight over time\n(increase = genetic assimilation)")
    ax.legend()
    fig.tight_layout()
    fig.savefig(os.path.join(out_dir, "04_inherited_care_weight.png"), dpi=120)
    plt.close(fig)


def plot_05_expressed_care_weight(tick_arrs: dict, duration: int, out_dir: str):
    """Effective (expressed) care_weight over time. Dashed = genome baseline for plasticity."""
    fig, ax = plt.subplots(figsize=(10, 5))
    ticks = np.arange(1, duration + 1)
    for label in ["no_plasticity", "plasticity"]:
        arr = tick_arrs.get(label, {}).get("mean_expressed_care_weight")
        if arr is not None:
            mn, sd = _mean_sd_over_seeds(arr)
            ax.plot(ticks, mn, color=COLORS[label], lw=2, label=f"{NICE[label]} (expressed)")
            ax.fill_between(ticks, np.maximum(0, mn - sd), np.minimum(1, mn + sd),
                            alpha=0.15, color=COLORS[label])
    # Dashed genome reference for plasticity condition
    arr_g = tick_arrs.get("plasticity", {}).get("mean_genome_care_weight")
    if arr_g is not None:
        mn_g, _ = _mean_sd_over_seeds(arr_g)
        ax.plot(ticks, mn_g, color=COLORS["plasticity"], lw=1.3, ls="--", alpha=0.6,
                label="Plasticity genome (ref)")
    ax.set_xlabel("Tick")
    ax.set_ylabel("Mean expressed care_weight")
    ax.set_ylim(0, 1)
    ax.set_title("Phase 7 - Effective (expressed) care_weight over time")
    ax.legend()
    fig.tight_layout()
    fig.savefig(os.path.join(out_dir, "05_expressed_care_weight.png"), dpi=120)
    plt.close(fig)


def plot_06_plasticity_delta(tick_arrs: dict, duration: int, out_dir: str):
    """Plasticity delta (expressed - genome) over time. Positive = learned care above genome baseline."""
    fig, ax = plt.subplots(figsize=(10, 5))
    ticks = np.arange(1, duration + 1)
    for label in ["no_plasticity", "plasticity"]:
        expr   = tick_arrs.get(label, {}).get("mean_expressed_care_weight")
        genome = tick_arrs.get(label, {}).get("mean_genome_care_weight")
        if expr is not None and genome is not None:
            with np.errstate(all="ignore"):
                delta_2d = np.where(np.isnan(expr) | np.isnan(genome), np.nan, expr - genome)
            mn, sd = _mean_sd_over_seeds(delta_2d)
            ax.plot(ticks, mn, color=COLORS[label], lw=2, label=NICE[label])
            ax.fill_between(ticks, mn - sd, mn + sd, alpha=0.15, color=COLORS[label])
    ax.axhline(0, color="black", lw=1, ls="--", alpha=0.5)
    ax.set_xlabel("Tick")
    ax.set_ylabel("Mean (expressed − genome) care_weight")
    ax.set_title("Phase 7 - Plasticity delta over time\n(positive = learned care above genetic baseline)")
    ax.legend()
    fig.tight_layout()
    fig.savefig(os.path.join(out_dir, "06_plasticity_delta.png"), dpi=120)
    plt.close(fig)


def plot_07_feed_rate(tick_arrs: dict, duration: int, out_dir: str):
    """Realized FEED_CHILD rate over time."""
    fig, ax = plt.subplots(figsize=(10, 5))
    ticks = np.arange(1, duration + 1)
    for label in ["no_plasticity", "plasticity"]:
        ev       = tick_arrs.get(label, {})
        pop_arr  = ev.get("total_pop")
        feed_arr = ev.get("n_feed_this_tick")
        if pop_arr is not None and feed_arr is not None:
            with np.errstate(invalid="ignore", divide="ignore"):
                rate_arr = np.where(pop_arr > 0, feed_arr / np.maximum(pop_arr, 1), np.nan)
            mn, sd = _mean_sd_over_seeds(rate_arr)
            ax.plot(ticks, mn, color=COLORS[label], lw=2, label=NICE[label])
            ax.fill_between(ticks, np.maximum(0, mn - sd), mn + sd,
                            alpha=0.15, color=COLORS[label])
    ax.set_xlabel("Tick")
    ax.set_ylabel("FEED events per agent per tick")
    ax.set_title("Phase 7 - Realized FEED_CHILD rate over time")
    ax.legend()
    fig.tight_layout()
    fig.savefig(os.path.join(out_dir, "07_feed_rate.png"), dpi=120)
    plt.close(fig)


def plot_08_child_survival_over_time(tick_arrs: dict, duration: int, out_dir: str, window: int = 200):
    """Rolling child survival rate over time."""
    fig, ax = plt.subplots(figsize=(10, 5))
    ticks = np.arange(1, duration + 1)
    for label in ["no_plasticity", "plasticity"]:
        ev      = tick_arrs.get(label, {})
        mat_arr = ev.get("n_child_matured_this_tick")
        hd_arr  = ev.get("n_child_deaths_hunger_this_tick")
        if mat_arr is None or hd_arr is None:
            continue
        rolling = _rolling_child_surv(mat_arr, hd_arr, window)
        mn, sd  = _mean_sd_over_seeds(rolling)
        ax.plot(ticks, mn, color=COLORS[label], lw=2, label=NICE[label])
        ax.fill_between(ticks, np.maximum(0, mn - sd), np.minimum(1, mn + sd),
                        alpha=0.15, color=COLORS[label])
    ax.set_xlabel("Tick")
    ax.set_ylabel(f"Child survival rate (rolling {window}-tick window)")
    ax.set_ylim(0, 1)
    ax.set_title("Phase 7 - Child survival rate over time")
    ax.legend()
    fig.tight_layout()
    fig.savefig(os.path.join(out_dir, "08_child_survival_over_time.png"), dpi=120)
    plt.close(fig)


def plot_09_descendants_vs_initial_care(lin_by_cond: dict, out_dir: str):
    """Descendant count vs initial care_weight for both conditions."""
    fig, axes = plt.subplots(1, 2, figsize=(13, 5))
    for ax, label in zip(axes, ["no_plasticity", "plasticity"]):
        lin_data = lin_by_cond.get(label, [])
        x = [d["initial_care_weight"] for d in lin_data
             if not math.isnan(d["initial_care_weight"])]
        y = [d["total_descendants"]   for d in lin_data
             if not math.isnan(d["initial_care_weight"])]
        if x:
            ax.scatter(x, y, alpha=0.5, s=30, color=COLORS[label])
            if len(x) > 2:
                m, b = np.polyfit(x, y, 1)
                xs = np.linspace(min(x), max(x), 100)
                ax.plot(xs, m * xs + b, "k--", lw=1.5, label=f"Slope={m:.1f}")
                r = _spearman(x, y)
                ax.set_title(f"{NICE[label]}\nDescendants vs Initial cw  r={r:.3f}")
            else:
                ax.set_title(f"{NICE[label]}\nDescendants vs Initial cw")
            ax.legend(fontsize=8)
        ax.set_xlabel("Founding care_weight")
        ax.set_ylabel("Total descendants")
    fig.suptitle("Phase 7 - Descendants vs Initial inherited care_weight")
    fig.tight_layout()
    fig.savefig(os.path.join(out_dir, "09_descendants_vs_initial_care.png"), dpi=120)
    plt.close(fig)


def plot_10_descendants_vs_final_care(lin_by_cond: dict, out_dir: str):
    """Descendant count vs mean birth (evolved/final) care_weight."""
    fig, axes = plt.subplots(1, 2, figsize=(13, 5))
    for ax, label in zip(axes, ["no_plasticity", "plasticity"]):
        lin_data = lin_by_cond.get(label, [])
        x = [d["mean_birth_care_weight"] for d in lin_data
             if not math.isnan(d.get("mean_birth_care_weight", float("nan")))]
        y = [d["total_descendants"]      for d in lin_data
             if not math.isnan(d.get("mean_birth_care_weight", float("nan")))]
        if x:
            ax.scatter(x, y, alpha=0.5, s=30, color="#e377c2")
            if len(x) > 2:
                m, b = np.polyfit(x, y, 1)
                xs = np.linspace(min(x), max(x), 100)
                ax.plot(xs, m * xs + b, "k--", lw=1.5, label=f"Slope={m:.1f}")
                r = _spearman(x, y)
                ax.set_title(f"{NICE[label]}\nDescendants vs Final cw  r={r:.3f}")
            else:
                ax.set_title(f"{NICE[label]}\nDescendants vs Final cw")
            ax.legend(fontsize=8)
        ax.set_xlabel("Mean birth (evolved) care_weight")
        ax.set_ylabel("Total descendants")
    fig.suptitle("Phase 7 - Descendants vs Final/Evolved care_weight")
    fig.tight_layout()
    fig.savefig(os.path.join(out_dir, "10_descendants_vs_final_care.png"), dpi=120)
    plt.close(fig)


def plot_11_selection_gradient_comparison(spearman_by_cond: dict, n_seeds: int, out_dir: str):
    """Per-seed Spearman r: Phase 6 (no_plasticity) vs Phase 7 (plasticity)."""
    fig, ax = plt.subplots(figsize=(10, 5))
    seeds = list(range(n_seeds))
    width = 0.35
    for i, label in enumerate(["no_plasticity", "plasticity"]):
        rs = spearman_by_cond.get(label, [float("nan")] * n_seeds)
        x_pos = np.array(seeds) + (i - 0.5) * width
        bar_colors = [COLORS[label] if not math.isnan(r) else "gray" for r in rs]
        ax.bar(x_pos, [r if not math.isnan(r) else 0 for r in rs],
               width=width, color=bar_colors, alpha=0.8, label=NICE[label])
    ax.axhline(0, color="black", lw=1)
    for label in ["no_plasticity", "plasticity"]:
        valid = [r for r in spearman_by_cond.get(label, []) if not math.isnan(r)]
        if valid:
            mean_r = float(np.mean(valid))
            ax.axhline(mean_r, color=COLORS[label], lw=2, ls="--", alpha=0.7,
                       label=f"{NICE[label]} mean r={mean_r:.3f}")
    ax.set_xticks(seeds)
    ax.set_xticklabels([f"s{s}" for s in seeds])
    ax.set_ylabel("Spearman r (initial_care_wt vs descendants)")
    ax.set_ylim(-1, 1)
    ax.set_title("Phase 7 - Selection gradient comparison: Phase 6 vs Phase 7")
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(os.path.join(out_dir, "11_selection_gradient_comparison.png"), dpi=120)
    plt.close(fig)


def plot_12_baldwin_summary(tick_arrs: dict, duration: int, out_dir: str):
    """Baldwin summary: fitness proxy (population) + plasticity delta over time."""
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 9), sharex=True)
    ticks = np.arange(1, duration + 1)

    # Panel 1: total population as fitness proxy
    for label in ["no_plasticity", "plasticity"]:
        arr = tick_arrs.get(label, {}).get("total_pop")
        if arr is not None:
            mn, sd = _mean_sd_over_seeds(arr)
            ax1.plot(ticks, mn, color=COLORS[label], lw=2, label=NICE[label])
            ax1.fill_between(ticks, np.maximum(0, mn - sd), mn + sd,
                             alpha=0.2, color=COLORS[label])
    ax1.set_ylabel("Total population")
    ax1.set_title("Baldwin Effect Summary: Fitness proxy (population)")
    ax1.legend()

    # Panel 2: plasticity delta (expressed - genome)
    for label in ["no_plasticity", "plasticity"]:
        expr   = tick_arrs.get(label, {}).get("mean_expressed_care_weight")
        genome = tick_arrs.get(label, {}).get("mean_genome_care_weight")
        if expr is not None and genome is not None:
            with np.errstate(all="ignore"):
                delta_2d = np.where(np.isnan(expr) | np.isnan(genome), np.nan, expr - genome)
            mn, sd = _mean_sd_over_seeds(delta_2d)
            ax2.plot(ticks, mn, color=COLORS[label], lw=2, label=NICE[label])
            ax2.fill_between(ticks, mn - sd, mn + sd, alpha=0.15, color=COLORS[label])
    ax2.axhline(0, color="black", lw=1, ls="--", alpha=0.5)
    ax2.set_xlabel("Tick")
    ax2.set_ylabel("Plasticity delta\n(expressed − genome care_weight)")
    ax2.set_title("Phenotypic plasticity over time\n(positive = learned care above genetic baseline)")
    ax2.legend()

    fig.tight_layout()
    fig.savefig(os.path.join(out_dir, "12_baldwin_summary.png"), dpi=120)
    plt.close(fig)


# ── Main ───────────────────────────────────────────────────────────────────────
def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--duration", type=int, default=10000)
    p.add_argument("--seeds",    type=int, default=10)
    return p.parse_args()


def main():
    args = parse_args()
    N_SEEDS  = args.seeds
    DURATION = args.duration

    ts        = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir   = os.path.join(PROJECT_ROOT, "outputs", "phase7_evo_with_plasticity", ts)
    data_dir  = os.path.join(out_dir, "data")
    plots_dir = os.path.join(out_dir, "plots")
    os.makedirs(data_dir,  exist_ok=True)
    os.makedirs(plots_dir, exist_ok=True)

    n_total = len(CONDITIONS) * N_SEEDS
    print(f"Phase 7: {n_total} runs ({len(CONDITIONS)} conditions x {N_SEEDS} seeds x {DURATION} ticks)")

    # ── CSV field definitions ─────────────────────────────────────────────────
    RAW_FIELDS = [
        "tick", "seed", "condition",
        "n_mothers", "n_children", "total_pop", "food_count",
        "mean_genome_care_weight", "mean_forage_weight", "mean_self_weight",
        "mean_expressed_care_weight", "mean_learning_rate",
        "mean_mother_energy", "mean_child_hunger",
        "n_births_this_tick", "n_child_deaths_hunger_this_tick",
        "n_child_matured_this_tick", "n_mother_deaths_this_tick",
        "n_feed_this_tick", "n_plasticity_events_this_tick",
    ]
    EVO_FIELDS = [
        "tick", "seed", "treatment",
        "n_alive_mothers", "n_alive_children",
        "mean_genome_care_weight", "mean_expressed_care_weight",
        "n_births_this_tick", "n_child_deaths_hunger_this_tick",
    ]
    DELTA_FIELDS = [
        "seed", "tick", "condition", "lineage_id",
        "mother_care", "child_care", "delta_care",
    ]

    raw_log_f  = open(os.path.join(data_dir, "raw_logs.csv"),           "w", newline="", encoding="utf-8")
    evo_log_f  = open(os.path.join(data_dir, "evolution_tick_log.csv"), "w", newline="", encoding="utf-8")
    out_f      = open(os.path.join(data_dir, "outcomes_all.csv"),       "w", newline="", encoding="utf-8")
    lin_f      = open(os.path.join(data_dir, "lineage_data.csv"),       "w", newline="", encoding="utf-8")
    delta_f    = open(os.path.join(data_dir, "mutation_deltas.csv"),    "w", newline="", encoding="utf-8")

    raw_writer   = csv.DictWriter(raw_log_f,  fieldnames=RAW_FIELDS, extrasaction="ignore")
    evo_writer   = csv.DictWriter(evo_log_f,  fieldnames=EVO_FIELDS)
    delta_writer = csv.DictWriter(delta_f,    fieldnames=DELTA_FIELDS)
    out_writer   = None
    lin_writer   = None

    raw_writer.writeheader()
    evo_writer.writeheader()
    delta_writer.writeheader()

    # ── Per-tick arrays (compact: [n_seeds, T]) for plotting ─────────────────
    PLOT_METRICS = [
        "total_pop",
        "mean_genome_care_weight",
        "mean_expressed_care_weight",
        "mean_learning_rate",
        "mean_forage_weight",
        "mean_self_weight",
        "n_feed_this_tick",
        "n_births_this_tick",
        "n_child_deaths_hunger_this_tick",
        "n_child_matured_this_tick",
        "n_plasticity_events_this_tick",
    ]
    tick_data: dict = {c["label"]: {m: [] for m in PLOT_METRICS} for c in CONDITIONS}

    all_outcomes:    list = []
    lin_by_cond:     dict = {"no_plasticity": [], "plasticity": []}
    all_mut_deltas:  list = []

    run_num = 0
    for cond in CONDITIONS:
        for seed in range(N_SEEDS):
            run_num += 1
            print(f"  [{run_num}/{n_total}] {cond['label']} seed={seed}", end="  ", flush=True)

            result     = run_single(cond, seed, DURATION)
            outcomes   = result["outcomes"]
            per_tick   = result["per_tick"]
            lin_out    = result["lin_out"]
            mut_deltas = result["mut_deltas"]

            all_outcomes.append(outcomes)
            lin_by_cond[cond["label"]].extend(lin_out)
            all_mut_deltas.extend(mut_deltas)

            # Raw log
            raw_writer.writerows(per_tick)

            # Evolution tick log (Baldwin format)
            for row in per_tick:
                evo_writer.writerow({
                    "tick":                            row["tick"],
                    "seed":                            row["seed"],
                    "treatment":                       row["condition"],
                    "n_alive_mothers":                 row["n_mothers"],
                    "n_alive_children":                row["n_children"],
                    "mean_genome_care_weight":         row["mean_genome_care_weight"],
                    "mean_expressed_care_weight":      row["mean_expressed_care_weight"],
                    "n_births_this_tick":              row["n_births_this_tick"],
                    "n_child_deaths_hunger_this_tick": row["n_child_deaths_hunger_this_tick"],
                })

            # Outcomes CSV
            if out_writer is None:
                out_writer = csv.DictWriter(out_f, fieldnames=list(outcomes.keys()))
                out_writer.writeheader()
            out_writer.writerow(outcomes)

            # Lineage CSV
            if lin_out:
                if lin_writer is None:
                    lin_writer = csv.DictWriter(lin_f, fieldnames=list(lin_out[0].keys()))
                    lin_writer.writeheader()
                lin_writer.writerows(lin_out)

            # Mutation deltas
            if mut_deltas:
                delta_writer.writerows(mut_deltas)

            # Compact tick arrays — NaN-preserving for weight metrics
            label = cond["label"]
            for m in PLOT_METRICS:
                arr = np.array([
                    r[m] if (r[m] is not None and
                             not (isinstance(r[m], float) and math.isnan(r[m])))
                    else (0.0 if m in _ZERO_ON_EXTINCT else float("nan"))
                    for r in per_tick
                ], dtype=float)
                tick_data[label][m].append(arr)

            cw_f = outcomes["final_mean_care_wt"]
            cw_str = f"{cw_f:.3f}" if (cw_f is not None and not math.isnan(cw_f)) else "extinct"
            pev    = outcomes["total_plasticity_events"]
            print(f"crash={outcomes['crash_tick']} max_gen={outcomes['max_gen']} "
                  f"cw_final={cw_str} plastic_ev={pev}")

    raw_log_f.close()
    evo_log_f.close()
    out_f.close()
    lin_f.close()
    delta_f.close()

    print("\nSanity checks...")
    assert len(all_outcomes) == n_total, f"Expected {n_total} outcome rows, got {len(all_outcomes)}"
    for cond in CONDITIONS:
        n = sum(1 for o in all_outcomes if o["condition"] == cond["label"])
        assert n == N_SEEDS, f"{cond['label']}: expected {N_SEEDS}, got {n}"
    print("Sanity checks passed.")

    # ── Convert tick lists to 2D arrays ───────────────────────────────────────
    tick_arrs: dict = {}
    for cond_label, metric_dict in tick_data.items():
        tick_arrs[cond_label] = {}
        for metric, seed_lists in metric_dict.items():
            if seed_lists:
                try:
                    tick_arrs[cond_label][metric] = np.stack(seed_lists, axis=0)
                except ValueError:
                    pass

    # ── Aggregate outcomes ─────────────────────────────────────────────────────
    agg: dict = {}
    for cond in CONDITIONS:
        label = cond["label"]
        items = [o for o in all_outcomes if o["condition"] == label]
        crash_ticks = [o["crash_tick"] for o in items if o["crash_tick"] != -1]
        survived    = sum(1 for o in items if o["survived_to_end"])
        agg[label] = {
            "condition":             label,
            "n_seeds":               len(items),
            "extinction_rate":       (len(items) - survived) / len(items),
            "n_survived":            survived,
            "crash_tick_mean":       _nanmean(crash_ticks),
            "crash_tick_sd":         _nanstd(crash_ticks),
            "max_gen_mean":          _nanmean([o["max_gen"]          for o in items]),
            "max_gen_sd":            _nanstd([o["max_gen"]           for o in items]),
            "child_surv_mean":       _nanmean([o["child_surv_rate"]  for o in items]),
            "total_births_mean":     _nanmean([o["total_births"]     for o in items]),
            "init_care_mean":        _nanmean([o["initial_mean_care_wt"]  for o in items]),
            "total_plasticity_mean": _nanmean([o["total_plasticity_events"] for o in items]),
            "care_increased_frac":   sum(1 for o in items if o["care_increased_temporal"]) / len(items),
        }

    # ── Selection gradient ─────────────────────────────────────────────────────
    spearman_by_cond: dict = {}
    for label in ["no_plasticity", "plasticity"]:
        by_seed: dict = defaultdict(list)
        for d in lin_by_cond[label]:
            by_seed[d["seed"]].append(d)
        rs = []
        for s in sorted(by_seed.keys()):
            items = by_seed[s]
            xi = [d["initial_care_weight"] for d in items
                  if not math.isnan(d["initial_care_weight"])]
            yi = [d["total_descendants"]   for d in items
                  if not math.isnan(d["initial_care_weight"])]
            rs.append(_spearman(xi, yi))
        spearman_by_cond[label] = rs

    mean_r_np = _nanmean(spearman_by_cond.get("no_plasticity", []))
    mean_r_p  = _nanmean(spearman_by_cond.get("plasticity",    []))

    # ── Lineage care comparison ────────────────────────────────────────────────
    care_increased_lineage: dict = {}
    for label in ["no_plasticity", "plasticity"]:
        lin_items = lin_by_cond[label]
        xi = [d["initial_care_weight"]   for d in lin_items
              if not math.isnan(d["initial_care_weight"])
              and not math.isnan(d.get("mean_birth_care_weight", float("nan")))]
        yi = [d["mean_birth_care_weight"] for d in lin_items
              if not math.isnan(d["initial_care_weight"])
              and not math.isnan(d.get("mean_birth_care_weight", float("nan")))]
        care_increased_lineage[label] = (
            float(np.mean(yi)) > float(np.mean(xi)) if (xi and yi) else False
        )

    # ── Generate 12 plots ─────────────────────────────────────────────────────
    print("Generating 12 plots...")
    plot_01_population(tick_arrs, DURATION, plots_dir)
    plot_02_extinction_time(all_outcomes, DURATION, plots_dir)
    plot_03_max_generation(all_outcomes, plots_dir)
    plot_04_inherited_care_weight(tick_arrs, DURATION, plots_dir)
    plot_05_expressed_care_weight(tick_arrs, DURATION, plots_dir)
    plot_06_plasticity_delta(tick_arrs, DURATION, plots_dir)
    plot_07_feed_rate(tick_arrs, DURATION, plots_dir)
    plot_08_child_survival_over_time(tick_arrs, DURATION, plots_dir)
    plot_09_descendants_vs_initial_care(lin_by_cond, plots_dir)
    plot_10_descendants_vs_final_care(lin_by_cond, plots_dir)
    plot_11_selection_gradient_comparison(spearman_by_cond, N_SEEDS, plots_dir)
    plot_12_baldwin_summary(tick_arrs, DURATION, plots_dir)
    print(f"12 plots saved to {plots_dir}")

    # ── config.json ────────────────────────────────────────────────────────────
    cfg_out = {
        "phase": "7",
        "description": "Mutation-enabled evolution with care-specific plasticity",
        "duration": DURATION,
        "n_seeds": N_SEEDS,
        "ecology": {
            "reproduction_cost":           REPRO_COST,
            "init_food":                   INIT_FOOD,
            "replenish_amount":            REPLENISH_AMOUNT,
            "threshold_ratio":             THRESHOLD_RATIO,
            "continuous_food_rate":        CONTINUOUS_FOOD_RATE,
            "continuous_food_max":         CONTINUOUS_FOOD_MAX,
            "infant_starvation_multiplier": INFANT_STARVATION,
        },
        "evolution": {
            "mutation_rate":  MUTATION_RATE,
            "mutation_sigma": MUTATION_SIGMA,
            "plasticity_settings": {
                "plastic_gain":             PLASTIC_GAIN,
                "kin_conditional":          True,
                "care_only":                True,
                "energy_cost":              0.0,
                "noise_sigma":              0.0,
                "init_learning_rate_range": [INIT_LR_LOW, INIT_LR_HIGH],
            },
            "initial_genome_distribution": {
                "care_weight":    "Uniform(0.0, 0.6)  [same as Phase 6]",
                "forage_weight":  "Uniform(0.7, 1.0)  [same as Phase 6]",
                "self_weight":    "Uniform(0.2, 0.6)  [same as Phase 6]",
                "learning_rate":  f"Uniform({INIT_LR_LOW}, {INIT_LR_HIGH})  [plasticity ON only]",
            },
        },
        "conditions": [c["label"] for c in CONDITIONS],
        "phase6_baselines": {
            "evolving_crash_tick": 898,
            "evolving_spearman_r": -0.212,
        },
    }
    with open(os.path.join(out_dir, "config.json"), "w") as f:
        json.dump(cfg_out, f, indent=2)

    # ── summary.json ───────────────────────────────────────────────────────────
    np_agg = agg.get("no_plasticity", {})
    p_agg  = agg.get("plasticity",    {})

    plasticity_improves_survival    = p_agg.get("crash_tick_mean", 0) > np_agg.get("crash_tick_mean", 0)
    plasticity_improves_max_gen     = p_agg.get("max_gen_mean", 0)    > np_agg.get("max_gen_mean", 0)
    plasticity_improves_child_surv  = p_agg.get("child_surv_mean", 0) > np_agg.get("child_surv_mean", 0)
    selection_gradient_positive_p   = not math.isnan(mean_r_p) and mean_r_p > 0.1
    selection_gradient_improved     = (not math.isnan(mean_r_p) and
                                       not math.isnan(mean_r_np) and
                                       mean_r_p > mean_r_np)
    care_increased_in_plasticity    = care_increased_lineage.get("plasticity", False)
    care_increased_temporal_frac    = p_agg.get("care_increased_frac", 0.0)

    baldwin_supported = (
        plasticity_improves_survival and
        selection_gradient_improved  and
        care_increased_in_plasticity
    )

    summary = {
        "phase":       "7",
        "description": "Mutation-enabled evolution with care-specific plasticity",
        "duration":    DURATION,
        "n_seeds":     N_SEEDS,
        "aggregate_outcomes": agg,
        "selection_gradient": {
            "no_plasticity": {
                "spearman_r_per_seed": spearman_by_cond.get("no_plasticity", []),
                "mean_spearman_r":     mean_r_np,
            },
            "plasticity": {
                "spearman_r_per_seed": spearman_by_cond.get("plasticity", []),
                "mean_spearman_r":     mean_r_p,
            },
            "selection_gradient_improved_by_plasticity": selection_gradient_improved,
            "selection_gradient_positive_plasticity":    selection_gradient_positive_p,
        },
        "care_weight_evolution": {
            "no_plasticity": {
                "care_increased_lineage_comparison": care_increased_lineage.get("no_plasticity", False),
                "care_increased_temporal_frac":      np_agg.get("care_increased_frac", 0.0),
                "mean_mutation_delta_care": _nanmean(
                    [d["delta_care"] for d in all_mut_deltas if d["condition"] == "no_plasticity"]
                ),
            },
            "plasticity": {
                "care_increased_lineage_comparison": care_increased_lineage.get("plasticity", False),
                "care_increased_temporal_frac":      care_increased_temporal_frac,
                "mean_mutation_delta_care": _nanmean(
                    [d["delta_care"] for d in all_mut_deltas if d["condition"] == "plasticity"]
                ),
                "mean_plasticity_events_per_run": p_agg.get("total_plasticity_mean", float("nan")),
            },
        },
        "success_criteria": {
            "plasticity_improves_survival":   plasticity_improves_survival,
            "plasticity_improves_max_gen":    plasticity_improves_max_gen,
            "plasticity_improves_child_surv": plasticity_improves_child_surv,
            "selection_gradient_positive":    selection_gradient_positive_p,
            "selection_gradient_improved":    selection_gradient_improved,
            "care_weight_increases":          care_increased_in_plasticity,
            "care_increased_temporal_frac":   care_increased_temporal_frac,
        },
        "verdict": {
            "baldwin_scaffolding_supported": baldwin_supported,
            "note": (
                "Baldwin supported: plasticity improves survival AND selection gradient improves "
                "AND care_weight increases in plasticity condition."
                if baldwin_supported else
                "Baldwin not fully supported: see individual success_criteria for details."
            ),
        },
    }
    with open(os.path.join(out_dir, "summary.json"), "w") as f:
        json.dump(summary, f, indent=2)

    # ── Console summary ────────────────────────────────────────────────────────
    print(f"\nOutput: {out_dir}")
    print(f"\nAggregate outcomes:")
    for label, a in agg.items():
        print(f"  {label:20s}: ext={a['extinction_rate']:.3f}  "
              f"crash_t={a['crash_tick_mean']:.0f}+/-{a['crash_tick_sd']:.0f}  "
              f"max_gen={a['max_gen_mean']:.1f}  "
              f"child_surv={a['child_surv_mean']:.3f}  "
              f"plastic_ev={a['total_plasticity_mean']:.0f}")

    print(f"\nSelection gradient (Spearman r, initial_cw vs descendants):")
    for label in ["no_plasticity", "plasticity"]:
        rs   = spearman_by_cond.get(label, [])
        mean = _nanmean(rs)
        print(f"  {label:20s}: per-seed={[f'{r:.3f}' for r in rs]}  mean={mean:.3f}")

    print(f"\nCare weight evolution:")
    for label in ["no_plasticity", "plasticity"]:
        print(f"  {label:20s}: increased_lineage={care_increased_lineage.get(label)}  "
              f"increased_temporal_frac={agg.get(label, {}).get('care_increased_frac', 0):.2f}")

    print(f"\nSuccess criteria:")
    for k, v in summary["success_criteria"].items():
        print(f"  {k}: {v}")

    print(f"\nBaldwin scaffolding supported: {baldwin_supported}")


if __name__ == "__main__":
    main()
