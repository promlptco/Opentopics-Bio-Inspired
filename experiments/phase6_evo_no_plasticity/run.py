#!/usr/bin/env python3
"""
Phase 6 -- Mutation-Enabled Genetic Evolution Without Plasticity

Frozen ecology (Phase 5f fallback rc=0.10):
  init_food=45, replenish_amount=20, threshold_ratio=0.5
  continuous_food_rate=0.10, continuous_food_max=200
  reproduction_cost=0.10, infant_starvation_multiplier=1.5

4 conditions x seeds:
  evolving        -- mutation ON, plasticity OFF, initial genomes Uniform distributed
  no_care_fixed   -- mutation OFF, plasticity OFF, cw=0.0, fw=0.85, sw=0.30
  canonical_fixed -- mutation OFF, plasticity OFF, cw=0.3, fw=0.85, sw=0.30
  high_care_fixed -- mutation OFF, plasticity OFF, cw=0.5, fw=0.85, sw=0.30

Tests whether mutation-enabled evolution discovers/reinforces care genomes,
and whether higher-care lineages leave more descendants before extinction.

Also produces evolution_tick_log.csv required by Baldwin analysis (Phase 7).

Usage:
    python experiments/phase6_evo_no_plasticity/run.py --duration 10000 --seeds 10
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
from agents.mother import MotherAgent
from agents.child import ChildAgent
from evolution.genome import Genome

# ── Frozen ecology constants ───────────────────────────────────────────────────
REPRO_COST           = 0.10
INIT_FOOD            = 45
REPLENISH_AMOUNT     = 20
THRESHOLD_RATIO      = 0.5
CONTINUOUS_FOOD_RATE = 0.1
CONTINUOUS_FOOD_MAX  = 200
INFANT_STARVATION    = 1.5
MUTATION_RATE        = 0.1    # hardcoded in Genome.mutate()
MUTATION_SIGMA       = 0.05   # hardcoded in Genome.mutate()
N_INIT_MOTHERS       = 12
EXTINCT_PATIENCE     = 200    # ticks of zero pop before early-stop padding

CONDITIONS = [
    {"label": "evolving",        "mutation_on": True,  "use_random": True,
     "care_w": None,  "forage_w": None, "self_w": None},
    {"label": "no_care_fixed",   "mutation_on": False, "use_random": False,
     "care_w": 0.0,   "forage_w": 0.85, "self_w": 0.30},
    {"label": "canonical_fixed", "mutation_on": False, "use_random": False,
     "care_w": 0.3,   "forage_w": 0.85, "self_w": 0.30},
    {"label": "high_care_fixed", "mutation_on": False, "use_random": False,
     "care_w": 0.5,   "forage_w": 0.85, "self_w": 0.30},
]

COLORS = {
    "evolving":        "#9467bd",
    "no_care_fixed":   "#d62728",
    "canonical_fixed": "#1f77b4",
    "high_care_fixed": "#2ca02c",
}
NICE = {
    "evolving":        "Evolving (mut ON)",
    "no_care_fixed":   "No-care fixed",
    "canonical_fixed": "Canonical fixed",
    "high_care_fixed": "High-care fixed",
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

def _zero_row(t2, seed, cond_label):
    return {
        "tick": t2, "seed": seed, "condition": cond_label,
        "n_mothers": 0, "n_children": 0, "total_pop": 0,
        "food_count": float("nan"),
        "mean_genome_care_weight": float("nan"),
        "mean_forage_weight": float("nan"),
        "mean_self_weight": float("nan"),
        "mean_expressed_care_weight": float("nan"),
        "mean_mother_energy": float("nan"),
        "mean_child_hunger": float("nan"),
        "n_births_this_tick": 0,
        "n_child_deaths_hunger_this_tick": 0,
        "n_child_matured_this_tick": 0,
        "n_mother_deaths_this_tick": 0,
        "n_feed_this_tick": 0,
    }


# ── Config & initial genomes ───────────────────────────────────────────────────
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
    cfg.mutation_enabled               = cond["mutation_on"]
    cfg.plasticity_enabled             = False
    cfg.lock_learning_rate             = True   # learning_rate gene not evolved in Phase 6
    if cond["use_random"]:
        cfg.care_weight   = 0.3    # fallback; overridden by genomes passed to initialize()
        cfg.forage_weight = 0.85
        cfg.self_weight   = 0.30
        cfg.care_enabled  = True
    else:
        cfg.care_weight   = cond["care_w"]
        cfg.forage_weight = cond["forage_w"]
        cfg.self_weight   = cond["self_w"]
        cfg.care_enabled  = cond["care_w"] > 0.0
    return cfg


def make_initial_genomes(seed: int) -> list:
    """12 random founding genomes: care~U[0,0.6], forage~U[0.7,1.0], self~U[0.2,0.6]."""
    rng = _random.Random(seed * 999983 + 7)
    return [
        Genome(
            care_weight=  rng.uniform(0.0, 0.6),
            forage_weight=rng.uniform(0.7, 1.0),
            self_weight=  rng.uniform(0.2, 0.6),
        )
        for _ in range(N_INIT_MOTHERS)
    ]


# ── Single simulation run ──────────────────────────────────────────────────────
def run_single(cond: dict, seed: int, duration: int) -> dict:
    cfg = make_config(cond, seed, duration)
    sim = Simulation(cfg)

    init_care: dict[int, float] = {}
    if cond["use_random"]:
        genomes_list = make_initial_genomes(seed)
        for i, g in enumerate(genomes_list):
            init_care[i] = g.care_weight
        sim.initialize(genomes_list)
    else:
        sim.initialize()

    per_tick:   list[dict] = []
    mut_deltas: list[dict] = []
    lin_births:     dict   = defaultdict(int)
    lin_last_tick:  dict   = {i: 0 for i in range(N_INIT_MOTHERS)}
    lin_birth_care: dict   = defaultdict(list)

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

        care_ws  = [m.genome.care_weight    for m in mothers]
        forg_ws  = [m.genome.forage_weight  for m in mothers]
        self_ws  = [m.genome.self_weight    for m in mothers]
        expr_ws  = [m.expressed_care_weight for m in mothers]
        energies = [m.energy                for m in mothers]
        hungers  = [c.hunger                for c in children]
        food     = len(sim.world.food_positions)

        new_births = sim.logger.birth_records[b0:]
        n_born     = len(new_births)
        new_deaths = sim.logger.death_records[d0:]
        n_ch_hd  = sum(1 for d in new_deaths if d.agent_type == "child" and d.cause == "hunger")
        n_ch_mat = sum(1 for d in new_deaths if d.agent_type == "child" and d.cause == "matured")
        n_m_died = sum(1 for d in new_deaths if d.agent_type == "mother")
        n_feed   = sum(1 for r in sim.logger.care_records[c0:] if r.benefit > 0)

        # Track max generation
        for m in mothers:
            if m.generation > max_gen:
                max_gen = m.generation
        for c in children:
            if c.generation > max_gen:
                max_gen = c.generation

        if total == 0 and crash_tick == -1:
            crash_tick = t + 1
        ext_count = ext_count + 1 if total == 0 else 0

        # Lineage tracking (evolving condition only)
        if cond["use_random"]:
            for br in new_births:
                lid = br.mother_lineage_id
                lin_births[lid] += 1
                lin_birth_care[lid].append(br.mother_care_weight)
            for m in mothers:
                lin_last_tick[m.lineage_id] = t + 1
            for c in children:
                lin_last_tick[c.lineage_id] = t + 1
            for br in new_births:
                child_agent = sim._child_by_id.get(br.child_id)
                if child_agent is not None and child_agent.genome is not None:
                    mut_deltas.append({
                        "seed":        seed,
                        "tick":        t + 1,
                        "lineage_id":  br.mother_lineage_id,
                        "mother_care": br.mother_care_weight,
                        "child_care":  child_agent.genome.care_weight,
                        "delta_care":  child_agent.genome.care_weight - br.mother_care_weight,
                    })

        row = {
            "tick":    t + 1,
            "seed":    seed,
            "condition": cond["label"],
            "n_mothers":  n_m,
            "n_children": n_c,
            "total_pop":  total,
            "food_count":                     food if total > 0 else float("nan"),
            "mean_genome_care_weight":         _nanmean(care_ws),
            "mean_forage_weight":              _nanmean(forg_ws),
            "mean_self_weight":                _nanmean(self_ws),
            "mean_expressed_care_weight":      _nanmean(expr_ws),
            "mean_mother_energy":              _nanmean(energies),
            "mean_child_hunger":               _nanmean(hungers),
            "n_births_this_tick":              n_born,
            "n_child_deaths_hunger_this_tick": n_ch_hd,
            "n_child_matured_this_tick":       n_ch_mat,
            "n_mother_deaths_this_tick":       n_m_died,
            "n_feed_this_tick":                n_feed,
        }
        per_tick.append(row)

        if ext_count >= EXTINCT_PATIENCE:
            for t2 in range(t + 2, duration + 1):
                per_tick.append(_zero_row(t2, seed, cond["label"]))
            break

    # ── Outcomes ───────────────────────────────────────────────────────────────
    all_deaths = sim.logger.death_records
    total_ch_hd  = sum(1 for d in all_deaths if d.agent_type == "child" and d.cause == "hunger")
    total_ch_mat = sum(1 for d in all_deaths if d.agent_type == "child" and d.cause == "matured")
    resolved     = total_ch_hd + total_ch_mat
    child_surv   = total_ch_mat / resolved if resolved > 0 else float("nan")

    total_births = len(sim.logger.birth_records)
    total_feeds  = sum(1 for r in sim.logger.care_records if r.benefit > 0)

    init_mean_cw  = _nanmean(list(init_care.values())) if init_care else (cond.get("care_w") or 0.0)
    final_cw      = _nanmean([m.genome.care_weight for m in sim.mothers]) if sim.mothers else float("nan")

    outcomes = {
        "condition":         cond["label"],
        "seed":              seed,
        "mutation_on":       cond["mutation_on"],
        "crash_tick":        crash_tick,
        "survived_to_end":   crash_tick == -1,
        "final_pop":         len(sim.mothers),
        "max_gen":           max_gen,
        "total_births":      total_births,
        "total_feed_events": total_feeds,
        "child_surv_rate":   child_surv,
        "n_child_hunger_deaths": total_ch_hd,
        "n_child_matured":   total_ch_mat,
        "initial_mean_care_wt": init_mean_cw,
        "final_mean_care_wt":   final_cw,
    }

    # ── Lineage outcomes (evolving only) ───────────────────────────────────────
    lin_out: list[dict] = []
    if cond["use_random"]:
        for lid in range(N_INIT_MOTHERS):
            lin_out.append({
                "seed":                  seed,
                "lineage_id":            lid,
                "initial_care_weight":   init_care.get(lid, float("nan")),
                "total_descendants":     lin_births[lid],
                "lineage_last_tick":     lin_last_tick[lid],
                "mean_birth_care_weight": _nanmean(lin_birth_care.get(lid, [])),
            })

    # Sanity check
    assert len(per_tick) == duration, f"per_tick={len(per_tick)} != duration={duration}"
    assert per_tick[-1]["tick"] == duration, f"last tick={per_tick[-1]['tick']} != {duration}"

    return {
        "outcomes":  outcomes,
        "per_tick":  per_tick,
        "lin_out":   lin_out,
        "mut_deltas": mut_deltas,
    }


# ── Plot helpers ───────────────────────────────────────────────────────────────
def _mean_sd_over_seeds(arr2d: np.ndarray):
    """arr2d shape [n_seeds, T]. Return mean[T] and sd[T], ignoring NaN."""
    with np.errstate(all="ignore"):
        mn = np.nanmean(arr2d, axis=0)
        sd = np.nanstd(arr2d, axis=0)
    return mn, sd


# ── 11 Plot functions ──────────────────────────────────────────────────────────

def plot_01_population(tick_arrs: dict, duration: int, out_dir: str):
    """Population over time by seed (evolving condition)."""
    fig, ax = plt.subplots(figsize=(10, 5))
    ticks = np.arange(1, duration + 1)
    arr = tick_arrs.get("evolving", {}).get("total_pop")
    if arr is not None:
        for s in range(arr.shape[0]):
            ax.plot(ticks, arr[s], alpha=0.3, lw=0.8, color=COLORS["evolving"])
        mn, sd = _mean_sd_over_seeds(arr)
        ax.plot(ticks, mn, color=COLORS["evolving"], lw=2, label="Mean")
        ax.fill_between(ticks, np.maximum(0, mn - sd), mn + sd,
                        alpha=0.2, color=COLORS["evolving"])
    ax.set_xlabel("Tick")
    ax.set_ylabel("Total population")
    ax.set_title("Phase 6 - Population over time (Evolving condition, all seeds)")
    ax.legend()
    fig.tight_layout()
    fig.savefig(os.path.join(out_dir, "01_population_over_time.png"), dpi=120)
    plt.close(fig)


def plot_02_extinction_time(all_outcomes: list, duration: int, out_dir: str):
    """Extinction time (crash_tick) per condition."""
    fig, ax = plt.subplots(figsize=(8, 5))
    cond_labels = [c["label"] for c in CONDITIONS]
    positions = list(range(len(cond_labels)))
    for i, cond_label in enumerate(cond_labels):
        vals = [o["crash_tick"] if o["crash_tick"] != -1 else duration
                for o in all_outcomes if o["condition"] == cond_label]
        x = np.full(len(vals), i) + np.random.uniform(-0.15, 0.15, len(vals))
        ax.scatter(x, vals, color=COLORS[cond_label], alpha=0.7, s=40, zorder=3)
        if vals:
            ax.hlines(np.mean(vals), i - 0.3, i + 0.3,
                      color=COLORS[cond_label], lw=2.5, zorder=4)
    ax.set_xticks(positions)
    ax.set_xticklabels([NICE[c] for c in cond_labels], rotation=12, ha="right")
    ax.set_ylabel("Extinction tick")
    ax.set_title("Phase 6 - Extinction time by condition")
    fig.tight_layout()
    fig.savefig(os.path.join(out_dir, "02_extinction_time.png"), dpi=120)
    plt.close(fig)


def plot_03_max_generation(all_outcomes: list, out_dir: str):
    """Max generation per condition."""
    fig, ax = plt.subplots(figsize=(8, 5))
    cond_labels = [c["label"] for c in CONDITIONS]
    for i, cond_label in enumerate(cond_labels):
        vals = [o["max_gen"] for o in all_outcomes if o["condition"] == cond_label]
        x = np.full(len(vals), i) + np.random.uniform(-0.15, 0.15, len(vals))
        ax.scatter(x, vals, color=COLORS[cond_label], alpha=0.7, s=40, zorder=3)
        if vals:
            ax.hlines(np.mean(vals), i - 0.3, i + 0.3,
                      color=COLORS[cond_label], lw=2.5, zorder=4)
    ax.set_xticks(list(range(len(cond_labels))))
    ax.set_xticklabels([NICE[c] for c in cond_labels], rotation=12, ha="right")
    ax.set_ylabel("Max generation reached")
    ax.set_title("Phase 6 - Max generation by condition")
    fig.tight_layout()
    fig.savefig(os.path.join(out_dir, "03_max_generation.png"), dpi=120)
    plt.close(fig)


def plot_04_genome_weights(tick_arrs: dict, duration: int, out_dir: str):
    """Care/forage/self genome weights over time (evolving condition)."""
    fig, ax = plt.subplots(figsize=(10, 5))
    ticks = np.arange(1, duration + 1)
    ev = tick_arrs.get("evolving", {})
    for metric, color, label in [
        ("mean_genome_care_weight",  "#2ca02c",  "Care weight"),
        ("mean_forage_weight",       "#ff7f0e",  "Forage weight"),
        ("mean_self_weight",         "#d62728",  "Self weight"),
    ]:
        arr = ev.get(metric)
        if arr is not None:
            mn, sd = _mean_sd_over_seeds(arr)
            ax.plot(ticks, mn, color=color, lw=2, label=label)
            ax.fill_between(ticks, np.maximum(0, mn - sd), np.minimum(1, mn + sd),
                            alpha=0.15, color=color)
    ax.set_xlabel("Tick")
    ax.set_ylabel("Mean genome weight (0-1)")
    ax.set_ylim(0, 1)
    ax.set_title("Phase 6 - Genome weight evolution over time (Evolving, mean +/- SD)")
    ax.legend()
    fig.tight_layout()
    fig.savefig(os.path.join(out_dir, "04_genome_weights_over_time.png"), dpi=120)
    plt.close(fig)


def plot_05_feed_rate(tick_arrs: dict, duration: int, out_dir: str):
    """FEED_CHILD events per alive mother over time (all care conditions)."""
    fig, ax = plt.subplots(figsize=(10, 5))
    ticks = np.arange(1, duration + 1)
    for cond_label in ["evolving", "canonical_fixed", "high_care_fixed"]:
        ev = tick_arrs.get(cond_label, {})
        pop_arr  = ev.get("total_pop")
        feed_arr = ev.get("n_feed_this_tick")
        if pop_arr is not None and feed_arr is not None:
            with np.errstate(invalid="ignore", divide="ignore"):
                rate_arr = np.where(pop_arr > 0, feed_arr / np.maximum(pop_arr, 1), np.nan)
            mn, sd = _mean_sd_over_seeds(rate_arr)
            ax.plot(ticks, mn, color=COLORS[cond_label], lw=2, label=NICE[cond_label])
            ax.fill_between(ticks, np.maximum(0, mn - sd), mn + sd,
                            alpha=0.15, color=COLORS[cond_label])
    ax.set_xlabel("Tick")
    ax.set_ylabel("FEED events per agent per tick")
    ax.set_title("Phase 6 - FEED_CHILD rate over time")
    ax.legend()
    fig.tight_layout()
    fig.savefig(os.path.join(out_dir, "05_feed_rate_over_time.png"), dpi=120)
    plt.close(fig)


def plot_06_child_survival(all_outcomes: list, out_dir: str):
    """Child survival rate per condition (bar chart)."""
    fig, ax = plt.subplots(figsize=(8, 5))
    cond_labels = [c["label"] for c in CONDITIONS]
    means = []
    sds   = []
    for cond_label in cond_labels:
        vals = [o["child_surv_rate"] for o in all_outcomes
                if o["condition"] == cond_label and not math.isnan(o["child_surv_rate"])]
        means.append(_nanmean(vals))
        sds.append(_nanstd(vals))
    x = np.arange(len(cond_labels))
    bars = ax.bar(x, means, yerr=sds, capsize=4,
                  color=[COLORS[c] for c in cond_labels], alpha=0.8)
    ax.set_xticks(x)
    ax.set_xticklabels([NICE[c] for c in cond_labels], rotation=12, ha="right")
    ax.set_ylabel("Child survival rate (matured / resolved)")
    ax.set_ylim(0, 1)
    ax.set_title("Phase 6 - Child survival rate by condition")
    for bar, mn in zip(bars, means):
        if not math.isnan(mn):
            ax.text(bar.get_x() + bar.get_width() / 2, mn + 0.02,
                    f"{mn:.3f}", ha="center", va="bottom", fontsize=9)
    fig.tight_layout()
    fig.savefig(os.path.join(out_dir, "06_child_survival.png"), dpi=120)
    plt.close(fig)


def plot_07_descendants_vs_initial_care(lin_data: list, out_dir: str):
    """Descendant count vs initial care_weight (selection gradient on founding genome)."""
    if not lin_data:
        return
    x = [d["initial_care_weight"] for d in lin_data
         if not math.isnan(d["initial_care_weight"])]
    y = [d["total_descendants"]   for d in lin_data
         if not math.isnan(d["initial_care_weight"])]
    if not x:
        return
    fig, ax = plt.subplots(figsize=(7, 6))
    ax.scatter(x, y, alpha=0.5, s=30, color=COLORS["evolving"])
    # Regression line
    if len(x) > 2:
        m, b = np.polyfit(x, y, 1)
        xs = np.linspace(min(x), max(x), 100)
        ax.plot(xs, m * xs + b, "k--", lw=1.5, label=f"Slope={m:.1f}")
        r = _spearman(x, y)
        ax.set_title(f"Phase 6 - Descendants vs Initial care_weight\nSpearman r={r:.3f} across all seeds x lineages")
    else:
        ax.set_title("Phase 6 - Descendants vs Initial care_weight")
    ax.set_xlabel("Founding mother care_weight")
    ax.set_ylabel("Total descendants (births in lineage)")
    ax.legend()
    fig.tight_layout()
    fig.savefig(os.path.join(out_dir, "07_descendants_vs_initial_care.png"), dpi=120)
    plt.close(fig)


def plot_08_descendants_vs_evolved_care(lin_data: list, out_dir: str):
    """Descendant count vs mean birth care_weight (evolved care level in lineage)."""
    if not lin_data:
        return
    x = [d["mean_birth_care_weight"] for d in lin_data
         if not math.isnan(d.get("mean_birth_care_weight", float("nan")))]
    y = [d["total_descendants"]      for d in lin_data
         if not math.isnan(d.get("mean_birth_care_weight", float("nan")))]
    if not x:
        return
    fig, ax = plt.subplots(figsize=(7, 6))
    ax.scatter(x, y, alpha=0.5, s=30, color="#e377c2")
    if len(x) > 2:
        m, b = np.polyfit(x, y, 1)
        xs = np.linspace(min(x), max(x), 100)
        ax.plot(xs, m * xs + b, "k--", lw=1.5, label=f"Slope={m:.1f}")
        r = _spearman(x, y)
        ax.set_title(f"Phase 6 - Descendants vs Evolved care_weight\nSpearman r={r:.3f}")
    else:
        ax.set_title("Phase 6 - Descendants vs Evolved care_weight")
    ax.set_xlabel("Mean birth care_weight in lineage (evolved)")
    ax.set_ylabel("Total descendants (births in lineage)")
    ax.legend()
    fig.tight_layout()
    fig.savefig(os.path.join(out_dir, "08_descendants_vs_evolved_care.png"), dpi=120)
    plt.close(fig)


def plot_09_care_evolution_scatter(lin_data: list, out_dir: str):
    """Initial care_weight vs mean-birth care_weight per lineage.

    Points above the diagonal: care weight increased in that lineage.
    Color = total descendants (proxy for fitness).
    """
    if not lin_data:
        return
    valid = [d for d in lin_data
             if not math.isnan(d["initial_care_weight"])
             and not math.isnan(d.get("mean_birth_care_weight", float("nan")))]
    if not valid:
        return
    x = np.array([d["initial_care_weight"]   for d in valid])
    y = np.array([d["mean_birth_care_weight"] for d in valid])
    c = np.array([d["total_descendants"]      for d in valid], dtype=float)
    fig, ax = plt.subplots(figsize=(7, 6))
    sc = ax.scatter(x, y, c=c, cmap="viridis", alpha=0.7, s=35, vmin=0)
    plt.colorbar(sc, ax=ax, label="Total descendants")
    lo, hi = min(min(x), min(y)) - 0.02, max(max(x), max(y)) + 0.02
    ax.plot([lo, hi], [lo, hi], "k--", lw=1, alpha=0.5, label="No change")
    ax.set_xlabel("Initial (founding) care_weight")
    ax.set_ylabel("Mean birth care_weight (evolved)")
    ax.set_title("Phase 6 - Lineage care weight evolution\n(above diagonal = care increased)")
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(os.path.join(out_dir, "09_lineage_care_trajectories.png"), dpi=120)
    plt.close(fig)


def plot_10_mutation_deltas(mut_data: list, out_dir: str):
    """Distribution of per-birth care_weight mutation deltas."""
    if not mut_data:
        return
    deltas = [d["delta_care"] for d in mut_data]
    fig, ax = plt.subplots(figsize=(7, 5))
    ax.hist(deltas, bins=50, color=COLORS["evolving"], alpha=0.75, edgecolor="white")
    ax.axvline(0, color="black", lw=1.5, ls="--")
    mn = float(np.mean(deltas))
    ax.axvline(mn, color="red", lw=1.5, ls="-",
               label=f"Mean delta={mn:+.4f}")
    ax.set_xlabel("care_weight delta (child - parent)")
    ax.set_ylabel("Count")
    ax.set_title(f"Phase 6 - Mutation delta distribution\n(n={len(deltas)} births with recorded child genome)")
    ax.legend()
    fig.tight_layout()
    fig.savefig(os.path.join(out_dir, "10_mutation_deltas.png"), dpi=120)
    plt.close(fig)


def plot_11_selection_gradient(lin_data: list, n_seeds: int, out_dir: str):
    """Spearman correlation between initial_care_weight and total_descendants per seed."""
    if not lin_data:
        return
    by_seed: dict = defaultdict(list)
    for d in lin_data:
        by_seed[d["seed"]].append(d)

    seeds = sorted(by_seed.keys())
    rs = []
    for s in seeds:
        items = by_seed[s]
        x = [d["initial_care_weight"] for d in items
             if not math.isnan(d["initial_care_weight"])]
        y = [d["total_descendants"]   for d in items
             if not math.isnan(d["initial_care_weight"])]
        rs.append(_spearman(x, y))

    valid_rs = [r for r in rs if not math.isnan(r)]
    fig, ax = plt.subplots(figsize=(8, 5))
    x_pos = np.arange(len(seeds))
    colors = ["#2ca02c" if r > 0 else "#d62728" for r in rs]
    ax.bar(x_pos, rs, color=colors, alpha=0.8)
    ax.axhline(0, color="black", lw=1)
    if valid_rs:
        mean_r = float(np.mean(valid_rs))
        ax.axhline(mean_r, color="black", lw=2, ls="--",
                   label=f"Mean r={mean_r:.3f}")
    ax.set_xticks(x_pos)
    ax.set_xticklabels([f"seed={s}" for s in seeds], rotation=20, ha="right")
    ax.set_ylabel("Spearman r")
    ax.set_ylim(-1, 1)
    ax.set_title("Phase 6 - Selection gradient: initial_care_weight vs descendants")
    ax.legend()
    fig.tight_layout()
    fig.savefig(os.path.join(out_dir, "11_selection_gradient.png"), dpi=120)
    plt.close(fig)
    return rs


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

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir   = os.path.join(PROJECT_ROOT, "outputs", "phase6_evo_no_plasticity", ts)
    data_dir  = os.path.join(out_dir, "data")
    plots_dir = os.path.join(out_dir, "plots")
    os.makedirs(data_dir,  exist_ok=True)
    os.makedirs(plots_dir, exist_ok=True)

    n_total = len(CONDITIONS) * N_SEEDS
    print(f"Phase 6: {n_total} runs ({len(CONDITIONS)} conditions x {N_SEEDS} seeds x {DURATION} ticks)")

    # ── CSV writers ───────────────────────────────────────────────────────────
    RAW_FIELDS = [
        "tick", "seed", "condition",
        "n_mothers", "n_children", "total_pop", "food_count",
        "mean_genome_care_weight", "mean_forage_weight", "mean_self_weight",
        "mean_expressed_care_weight", "mean_mother_energy", "mean_child_hunger",
        "n_births_this_tick", "n_child_deaths_hunger_this_tick",
        "n_child_matured_this_tick", "n_mother_deaths_this_tick", "n_feed_this_tick",
    ]
    EVO_FIELDS = [
        "tick", "seed", "treatment",
        "n_alive_mothers", "n_alive_children",
        "mean_genome_care_weight", "mean_expressed_care_weight",
        "n_births_this_tick", "n_child_deaths_hunger_this_tick",
    ]

    raw_log_f  = open(os.path.join(data_dir, "raw_logs.csv"),            "w", newline="", encoding="utf-8")
    evo_log_f  = open(os.path.join(data_dir, "evolution_tick_log.csv"),  "w", newline="", encoding="utf-8")
    out_f      = open(os.path.join(data_dir, "outcomes_all.csv"),        "w", newline="", encoding="utf-8")
    lin_f      = open(os.path.join(data_dir, "lineage_data.csv"),        "w", newline="", encoding="utf-8")
    delta_f    = open(os.path.join(data_dir, "mutation_deltas.csv"),     "w", newline="", encoding="utf-8")

    raw_writer   = csv.DictWriter(raw_log_f, fieldnames=RAW_FIELDS, extrasaction="ignore")
    evo_writer   = csv.DictWriter(evo_log_f, fieldnames=EVO_FIELDS)
    out_writer   = None   # initialized after first run
    lin_writer   = None
    delta_writer = csv.DictWriter(delta_f,
                                  fieldnames=["seed","tick","lineage_id","mother_care","child_care","delta_care"])

    raw_writer.writeheader()
    evo_writer.writeheader()
    delta_writer.writeheader()

    # ── Per-tick arrays for plotting (compact: [n_seeds, T]) ─────────────────
    PLOT_METRICS = [
        "total_pop", "mean_genome_care_weight", "mean_forage_weight",
        "mean_self_weight", "n_feed_this_tick",
        "n_births_this_tick", "n_child_deaths_hunger_this_tick",
    ]
    tick_data: dict = {c["label"]: {m: [] for m in PLOT_METRICS} for c in CONDITIONS}

    all_outcomes: list = []
    all_lin_out:  list = []
    all_mut_deltas: list = []

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
            all_lin_out.extend(lin_out)
            all_mut_deltas.extend(mut_deltas)

            # Write raw log rows
            raw_writer.writerows(per_tick)

            # Write evolution_tick_log rows (rename columns)
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

            # Outcomes CSV (init writer on first run)
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

            # Mutation deltas CSV
            if mut_deltas:
                delta_writer.writerows(mut_deltas)

            # Compact arrays for plotting
            label = cond["label"]
            for m in PLOT_METRICS:
                arr = np.array([
                    r[m] if not (isinstance(r[m], float) and math.isnan(r[m])) else 0.0
                    for r in per_tick
                ], dtype=float)
                tick_data[label][m].append(arr)

            cw_f = outcomes["final_mean_care_wt"]
            cw_str = f"{cw_f:.3f}" if (cw_f is not None and not math.isnan(cw_f)) else "extinct"
            print(f"crash={outcomes['crash_tick']} max_gen={outcomes['max_gen']} cw_final={cw_str}")

    raw_log_f.close()
    evo_log_f.close()
    out_f.close()
    lin_f.close()
    delta_f.close()

    print("\nSanity checks...")
    assert len(all_outcomes) == n_total, f"Expected {n_total} outcome rows"
    # Verify each condition has correct n_seeds
    for cond in CONDITIONS:
        n = sum(1 for o in all_outcomes if o["condition"] == cond["label"])
        assert n == N_SEEDS, f"{cond['label']}: expected {N_SEEDS} seeds, got {n}"
    print("Sanity checks passed.")

    # ── Convert tick lists to 2D arrays ───────────────────────────────────────
    tick_arrs: dict = {}
    for cond_label, metric_dict in tick_data.items():
        tick_arrs[cond_label] = {}
        for metric, seed_lists in metric_dict.items():
            if seed_lists:
                try:
                    tick_arrs[cond_label][metric] = np.stack(seed_lists, axis=0)  # [n_seeds, T]
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
            "condition":         label,
            "n_seeds":           len(items),
            "extinction_rate":   (len(items) - survived) / len(items),
            "n_survived":        survived,
            "crash_tick_mean":   _nanmean(crash_ticks),
            "crash_tick_sd":     _nanstd(crash_ticks),
            "max_gen_mean":      _nanmean([o["max_gen"]          for o in items]),
            "max_gen_sd":        _nanstd([o["max_gen"]           for o in items]),
            "child_surv_mean":   _nanmean([o["child_surv_rate"]  for o in items]),
            "total_births_mean": _nanmean([o["total_births"]     for o in items]),
            "init_care_mean":    _nanmean([o["initial_mean_care_wt"] for o in items]),
        }

    # ── Selection gradient ─────────────────────────────────────────────────────
    spearman_rs: list = []
    if all_lin_out:
        by_seed: dict = defaultdict(list)
        for d in all_lin_out:
            by_seed[d["seed"]].append(d)
        for s in sorted(by_seed.keys()):
            items = by_seed[s]
            xi = [d["initial_care_weight"] for d in items
                  if not math.isnan(d["initial_care_weight"])]
            yi = [d["total_descendants"]   for d in items
                  if not math.isnan(d["initial_care_weight"])]
            spearman_rs.append(_spearman(xi, yi))
    mean_spearman = _nanmean(spearman_rs)

    # ── Plots ──────────────────────────────────────────────────────────────────
    print("Generating 11 plots...")
    plot_01_population(tick_arrs, DURATION, plots_dir)
    plot_02_extinction_time(all_outcomes, DURATION, plots_dir)
    plot_03_max_generation(all_outcomes, plots_dir)
    plot_04_genome_weights(tick_arrs, DURATION, plots_dir)
    plot_05_feed_rate(tick_arrs, DURATION, plots_dir)
    plot_06_child_survival(all_outcomes, plots_dir)
    plot_07_descendants_vs_initial_care(all_lin_out, plots_dir)
    plot_08_descendants_vs_evolved_care(all_lin_out, plots_dir)
    plot_09_care_evolution_scatter(all_lin_out, plots_dir)
    plot_10_mutation_deltas(all_mut_deltas, plots_dir)
    plot_11_selection_gradient(all_lin_out, N_SEEDS, plots_dir)
    print(f"11 plots saved to {plots_dir}")

    # ── config.json ────────────────────────────────────────────────────────────
    cfg_out = {
        "phase": "6",
        "description": "Mutation-enabled evolution without plasticity",
        "duration": DURATION,
        "n_seeds": N_SEEDS,
        "ecology": {
            "reproduction_cost": REPRO_COST,
            "init_food": INIT_FOOD,
            "replenish_amount": REPLENISH_AMOUNT,
            "threshold_ratio": THRESHOLD_RATIO,
            "continuous_food_rate": CONTINUOUS_FOOD_RATE,
            "continuous_food_max": CONTINUOUS_FOOD_MAX,
            "infant_starvation_multiplier": INFANT_STARVATION,
        },
        "evolution": {
            "mutation_rate": MUTATION_RATE,
            "mutation_sigma": MUTATION_SIGMA,
            "plasticity": False,
            "initial_genome_distribution": {
                "care_weight":   "Uniform(0.0, 0.6)",
                "forage_weight": "Uniform(0.7, 1.0)",
                "self_weight":   "Uniform(0.2, 0.6)",
            },
        },
        "conditions": [c["label"] for c in CONDITIONS],
        "phase5f_baselines": {
            "no_care_crash_tick": 339,
            "canonical_crash_tick": 977,
            "high_care_crash_tick": 1192,
        },
    }
    with open(os.path.join(out_dir, "config.json"), "w") as f:
        json.dump(cfg_out, f, indent=2)

    # ── summary.json ───────────────────────────────────────────────────────────
    ev = agg.get("evolving", {})
    nc = agg.get("no_care_fixed", {})
    ca = agg.get("canonical_fixed", {})
    hc = agg.get("high_care_fixed", {})

    # Check Phase 6 success criteria
    care_increased = False
    if all_lin_out:
        x = [d["initial_care_weight"] for d in all_lin_out
             if not math.isnan(d["initial_care_weight"])
             and not math.isnan(d.get("mean_birth_care_weight", float("nan")))]
        y = [d["mean_birth_care_weight"] for d in all_lin_out
             if not math.isnan(d["initial_care_weight"])
             and not math.isnan(d.get("mean_birth_care_weight", float("nan")))]
        if x and y:
            care_increased = float(np.mean(y)) > float(np.mean(x))

    high_care_more_descendants = (
        not math.isnan(mean_spearman) and mean_spearman > 0.1
    )

    summary = {
        "phase": "6",
        "description": "Mutation-enabled evolution without plasticity",
        "duration": DURATION,
        "n_seeds": N_SEEDS,
        "aggregate_outcomes": agg,
        "selection_gradient": {
            "spearman_r_per_seed": spearman_rs,
            "mean_spearman_r": mean_spearman,
            "high_care_more_descendants": high_care_more_descendants,
        },
        "care_weight_evolution": {
            "care_increased_on_average": care_increased,
            "n_mutation_deltas_recorded": len(all_mut_deltas),
            "mean_mutation_delta_care": _nanmean([d["delta_care"] for d in all_mut_deltas]),
        },
        "success_criteria": {
            "care_weight_increases": care_increased,
            "selection_gradient_positive": high_care_more_descendants,
            "evolving_outlasts_no_care": (
                ev.get("crash_tick_mean", 0) > nc.get("crash_tick_mean", 0)
            ),
            "evolving_outlasts_canonical": (
                ev.get("crash_tick_mean", 0) > ca.get("crash_tick_mean", 0)
            ),
        },
    }
    with open(os.path.join(out_dir, "summary.json"), "w") as f:
        json.dump(summary, f, indent=2)

    # ── Console summary ────────────────────────────────────────────────────────
    print(f"\nOutput: {out_dir}")
    print(f"\nAggregate outcomes:")
    for cond_label, a in agg.items():
        print(f"  {cond_label:20s}: ext={a['extinction_rate']:.3f}  "
              f"crash_t={a['crash_tick_mean']:.0f}+/-{a['crash_tick_sd']:.0f}  "
              f"max_gen={a['max_gen_mean']:.1f}  "
              f"child_surv={a['child_surv_mean']:.3f}")

    print(f"\nSelection gradient (Spearman r, initial_cw vs descendants, evolving):")
    for i, r in enumerate(spearman_rs):
        print(f"  seed={i}: r={r:.3f}")
    print(f"  Mean: {mean_spearman:.3f}")

    print(f"\nCare weight evolution: increased={care_increased}")
    print(f"High-care lineages have more descendants: {high_care_more_descendants}")


if __name__ == "__main__":
    main()
