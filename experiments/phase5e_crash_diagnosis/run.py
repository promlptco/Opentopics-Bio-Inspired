#!/usr/bin/env python3
"""
Phase 5e -- Crash Mechanism Diagnosis

Fixed ecology (Phase 5d fallback cfr_0.10):
  init_food=45, food_replenish_amount=20, threshold_ratio=0.5
  continuous_food_rate=0.1, continuous_food_max=200
  infant_starvation_multiplier=1.5

3 conditions x 30 seeds = 90 runs.
Goal: determine why populations crash (food, reproduction, energy, or crowding).

Usage:
    python experiments/phase5e_crash_diagnosis/run.py --duration 3000 --seeds 30
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import os
import sys
from collections import defaultdict
from datetime import datetime

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, PROJECT_ROOT)

from config import Config
from simulation.simulation import Simulation

# ── Fixed ecology ──────────────────────────────────────────────────────────────
INFANT_STARVATION_MULTIPLIER = 1.5
INIT_FOOD                    = 45
REPLENISH_AMOUNT             = 20
THRESHOLD_RATIO              = 0.5
CONTINUOUS_FOOD_RATE         = 0.1
CONTINUOUS_FOOD_MAX          = 200
GRID_CELLS                   = 900   # 30 x 30

CONDITIONS = [
    {"label": "no_care",   "care_w": 0.0, "forage_w": 0.85, "self_w": 0.3},
    {"label": "canonical", "care_w": 0.3, "forage_w": 0.85, "self_w": 0.3},
    {"label": "high_care", "care_w": 0.5, "forage_w": 0.85, "self_w": 0.3},
]

COLORS = {
    "no_care":   "#d62728",
    "canonical": "#1f77b4",
    "high_care": "#2ca02c",
}
NICE = {
    "no_care":   "No-Care (cw=0.0)",
    "canonical": "Canonical (cw=0.3)",
    "high_care": "High-Care (cw=0.5)",
}


# ── Config ─────────────────────────────────────────────────────────────────────

def make_config(cond: dict, seed: int, duration: int) -> Config:
    cfg = Config()
    cfg.seed                           = seed
    cfg.max_ticks                      = duration
    cfg.infant_starvation_multiplier   = INFANT_STARVATION_MULTIPLIER
    cfg.care_weight                    = cond["care_w"]
    cfg.forage_weight                  = cond["forage_w"]
    cfg.self_weight                    = cond["self_w"]
    cfg.care_enabled                   = cond["care_w"] > 0.0
    cfg.plasticity_enabled             = False
    cfg.reproduction_enabled           = True
    cfg.mutation_enabled               = False
    cfg.children_enabled               = True
    cfg.init_mothers                   = 12
    cfg.hunger_rate                    = 0.008
    cfg.init_food                      = INIT_FOOD
    cfg.food_replenish_amount          = REPLENISH_AMOUNT
    cfg.food_replenish_threshold_ratio = THRESHOLD_RATIO
    cfg.continuous_food_rate           = CONTINUOUS_FOOD_RATE
    cfg.continuous_food_max            = CONTINUOUS_FOOD_MAX
    return cfg


# ── Helpers ────────────────────────────────────────────────────────────────────

def _nanmean(vals: list) -> float:
    finite = [v for v in vals if not math.isnan(v)]
    return float(np.mean(finite)) if finite else float("nan")


def _nanstd(vals: list) -> float:
    finite = [v for v in vals if not math.isnan(v)]
    return float(np.std(finite)) if len(finite) > 1 else 0.0


def _nanpct(vals: list, q: float) -> float:
    finite = [v for v in vals if not math.isnan(v)]
    return float(np.percentile(finite, q)) if finite else float("nan")


def _smooth(arr: list, w: int = 20) -> list:
    """Simple box-car moving average."""
    out = []
    for i in range(len(arr)):
        lo = max(0, i - w // 2)
        hi = min(len(arr), i + w // 2 + 1)
        chunk = [v for v in arr[lo:hi] if not math.isnan(v)]
        out.append(float(np.mean(chunk)) if chunk else float("nan"))
    return out


# ── Single run ─────────────────────────────────────────────────────────────────

def run_single(cond: dict, seed: int, duration: int) -> dict:
    cfg = make_config(cond, seed, duration)
    sim = Simulation(cfg)
    sim.initialize()

    initial_child_ids  = {c.id for c in sim.children}
    initial_mother_ids = {m.id for m in sim.mothers}
    n_initial_children = len(sim.children)

    per_tick: list[dict] = []

    peak_pop        = 0
    peak_pop_tick   = 0
    crash_tick      = None
    food_depl_tick  = None
    birth_peak_tick = 0
    birth_peak_val  = 0
    death_peak_tick = 0
    death_peak_val  = 0

    for t in range(duration):
        births_before = len(sim.logger.birth_records)
        care_before   = len(sim.logger.care_records)
        deaths_before = len(sim.logger.death_records)

        sim.step()
        sim.tick += 1

        n_born_tick = len(sim.logger.birth_records) - births_before
        n_feed_tick = sum(1 for r in sim.logger.care_records[care_before:] if r.benefit > 0)
        new_deaths  = sim.logger.death_records[deaths_before:]
        n_died_tick          = len(new_deaths)
        n_died_mother        = sum(1 for d in new_deaths if d.agent_type == "mother")
        n_died_child_hunger  = sum(1 for d in new_deaths if d.agent_type == "child" and d.cause == "hunger")
        n_died_child_matured = sum(1 for d in new_deaths if d.agent_type == "child" and d.cause == "matured")

        alive_m = sim.mothers
        alive_c = sim.children
        n_m     = len(alive_m)
        n_c     = len(alive_c)
        total   = n_m + n_c
        food    = len(sim.world.food_positions)

        if food_depl_tick is None and food == 0:
            food_depl_tick = t + 1
        if total > peak_pop:
            peak_pop, peak_pop_tick = total, t + 1
        if crash_tick is None and peak_pop > 0 and total == 0:
            crash_tick = t + 1
        if n_born_tick > birth_peak_val:
            birth_peak_val, birth_peak_tick = n_born_tick, t + 1
        if n_died_tick > death_peak_val:
            death_peak_val, death_peak_tick = n_died_tick, t + 1

        energies = [m.energy for m in alive_m]
        hungers  = [c.hunger for c in alive_c]

        # Mean mother-to-own-child distance
        child_pos = {c.id: c.pos for c in alive_c}
        mc_dists  = [
            sim.world.get_distance(m.pos, child_pos[m.own_child_id])
            for m in alive_m
            if m.own_child_id is not None and m.own_child_id in child_pos
        ]

        row: dict = {
            "tick":                  t + 1,
            "n_mothers":             n_m,
            "n_children":            n_c,
            "total_pop":             total,
            "food_count":            food if total > 0 else float("nan"),
            "occupied_density":      total / GRID_CELLS,
            "eng_mean":              _nanmean(energies),
            "eng_p25":               _nanpct(energies, 25),
            "eng_med":               _nanpct(energies, 50),
            "eng_p75":               _nanpct(energies, 75),
            "mean_child_hunger":     _nanmean(hungers),
            "mean_mc_dist":          _nanmean(mc_dists),
            "n_feed_tick":           n_feed_tick,
            "n_born_tick":           n_born_tick,
            "n_died_tick":           n_died_tick,
            "n_died_mother":         n_died_mother,
            "n_died_child_hunger":   n_died_child_hunger,
            "n_died_child_matured":  n_died_child_matured,
            "food_unavail":          int(food == 0),
        }
        per_tick.append(row)

        if total == 0 and t < duration - 1:
            zero: dict = {
                "n_mothers": 0, "n_children": 0, "total_pop": 0,
                "food_count": float("nan"), "occupied_density": 0.0,
                "eng_mean": float("nan"), "eng_p25": float("nan"),
                "eng_med": float("nan"), "eng_p75": float("nan"),
                "mean_child_hunger": float("nan"), "mean_mc_dist": float("nan"),
                "n_feed_tick": 0, "n_born_tick": 0, "n_died_tick": 0,
                "n_died_mother": 0, "n_died_child_hunger": 0,
                "n_died_child_matured": 0, "food_unavail": 0,
            }
            for rt in range(t + 1, duration):
                per_tick.append({"tick": rt + 1, **zero})
            break

    # ── Post-run outcomes ──────────────────────────────────────────────────────
    final_pop = len(sim.mothers) + len(sim.children)
    extinct   = final_pop == 0
    max_gen   = max(sim.lineage.generations.values()) if sim.lineage.generations else 0

    dr = sim.logger.death_records
    n_mother_deaths       = sum(1 for d in dr if d.agent_type == "mother")
    n_child_hunger_deaths = sum(1 for d in dr if d.agent_type == "child" and d.cause == "hunger")
    n_child_matured_all   = sum(1 for d in dr if d.agent_type == "child" and d.cause == "matured")

    init_matured   = sum(1 for d in dr if d.agent_type == "child" and d.cause == "matured"
                         and d.agent_id in initial_child_ids)
    init_alive_end = sum(1 for c in sim.children if c.id in initial_child_ids)
    init_cs        = (init_matured + init_alive_end) / n_initial_children if n_initial_children > 0 else 0.0

    total_births  = len(sim.logger.birth_records)
    n_feed_total  = sum(1 for r in sim.logger.care_records if r.benefit > 0)
    feed_rate     = n_feed_total / duration

    births_per_mother: dict[int, int] = defaultdict(int)
    for br in sim.logger.birth_records:
        births_per_mother[br.mother_id] += 1
    mean_births_per_m = float(np.mean(list(births_per_mother.values()))) if births_per_mother else 0.0

    assert len(per_tick) == duration, (
        f"per_tick {len(per_tick)} != {duration} (seed={seed}, cond={cond['label']})"
    )
    assert per_tick[-1]["tick"] == duration

    return {
        "condition":              cond["label"],
        "seed":                   seed,
        "final_pop":              final_pop,
        "extinct":                extinct,
        "max_gen":                max_gen,
        "total_births":           total_births,
        "n_mother_deaths":        n_mother_deaths,
        "n_child_hunger_deaths":  n_child_hunger_deaths,
        "n_child_matured_all":    n_child_matured_all,
        "init_child_survival":    init_cs,
        "feed_rate":              feed_rate,
        "mean_births_per_mother": mean_births_per_m,
        "peak_pop":               peak_pop,
        "peak_pop_tick":          peak_pop_tick,
        "food_depl_tick":         food_depl_tick if food_depl_tick is not None else -1,
        "birth_peak_tick":        birth_peak_tick,
        "death_peak_tick":        death_peak_tick,
        "crash_tick":             crash_tick if crash_tick is not None else -1,
        "per_tick":               per_tick,
    }


# ── Aggregation ────────────────────────────────────────────────────────────────

def agg_outcomes(results: list[dict]) -> dict:
    def ms(k: str) -> tuple[float, float]:
        v = [r[k] for r in results]
        return float(np.mean(v)), float(np.std(v))

    n   = len(results)
    ext = sum(1 for r in results if r["extinct"]) / n

    pp_m, pp_s  = ms("peak_pop")
    mg_m, mg_s  = ms("max_gen")
    tb_m, _     = ms("total_births")
    fr_m, _     = ms("feed_rate")
    cs_m, _     = ms("init_child_survival")
    bpm_m, _    = ms("mean_births_per_mother")

    def tick_stats(key: str) -> tuple[float, float]:
        vals = [r[key] for r in results if r[key] > 0]
        return (float(np.mean(vals)), float(np.std(vals))) if vals else (-1.0, 0.0)

    ppt_m, ppt_s  = tick_stats("peak_pop_tick")
    fdt_m, fdt_s  = tick_stats("food_depl_tick")
    bpt_m, bpt_s  = tick_stats("birth_peak_tick")
    dpt_m, dpt_s  = tick_stats("death_peak_tick")
    ct_m,  ct_s   = tick_stats("crash_tick")

    return {
        "condition":                  results[0]["condition"],
        "n_seeds":                    n,
        "extinction_rate":            ext,
        "peak_pop_mean":              pp_m,   "peak_pop_sd":              pp_s,
        "max_gen_mean":               mg_m,   "max_gen_sd":               mg_s,
        "total_births_mean":          tb_m,
        "feed_rate_mean":             fr_m,
        "init_child_surv_mean":       cs_m,
        "mean_births_per_mother":     bpm_m,
        "n_mother_deaths_mean":       float(np.mean([r["n_mother_deaths"] for r in results])),
        "n_child_hunger_deaths_mean": float(np.mean([r["n_child_hunger_deaths"] for r in results])),
        "peak_pop_tick_mean":         ppt_m,  "peak_pop_tick_sd":         ppt_s,
        "food_depl_tick_mean":        fdt_m,  "food_depl_tick_sd":        fdt_s,
        "birth_peak_tick_mean":       bpt_m,  "birth_peak_tick_sd":       bpt_s,
        "death_peak_tick_mean":       dpt_m,  "death_peak_tick_sd":       dpt_s,
        "crash_tick_mean":            ct_m,   "crash_tick_sd":            ct_s,
    }


def agg_per_tick(results: list[dict], duration: int) -> list[dict]:
    out = []
    keys = [
        "n_mothers", "n_children", "total_pop", "food_count",
        "occupied_density", "eng_mean", "eng_p25", "eng_med", "eng_p75",
        "mean_child_hunger", "mean_mc_dist",
        "n_feed_tick", "n_born_tick", "n_died_tick",
        "n_died_mother", "n_died_child_hunger", "n_died_child_matured",
        "food_unavail",
    ]
    for t in range(duration):
        bucket: dict[str, list] = {k: [] for k in keys}
        for r in results:
            row = r["per_tick"][t]
            for k in keys:
                bucket[k].append(row[k])

        agg_row: dict = {"tick": t + 1}
        for k in keys:
            agg_row[f"mean_{k}"]  = _nanmean(bucket[k])
            agg_row[f"std_{k}"]   = _nanstd(bucket[k])
        out.append(agg_row)
    return out


# ── Plotting ───────────────────────────────────────────────────────────────────

def _ticks(agg: list[dict]) -> list[int]:
    return [r["tick"] for r in agg]


def plot_adult_child_pop(agg_by_cond: dict, out_dir: str) -> None:
    fig, axes = plt.subplots(1, 3, figsize=(15, 4), sharey=True)
    for ax, cond_label in zip(axes, ["no_care", "canonical", "high_care"]):
        a = agg_by_cond[cond_label]
        tks = _ticks(a)
        m_m = np.array([r["mean_n_mothers"]  for r in a])
        c_m = np.array([r["mean_n_children"] for r in a])
        m_s = np.array([r["std_n_mothers"]   for r in a])
        c_s = np.array([r["std_n_children"]  for r in a])
        ax.fill_between(tks, m_m - m_s, m_m + m_s, alpha=0.2, color="#1f77b4")
        ax.fill_between(tks, c_m - c_s, c_m + c_s, alpha=0.2, color="#ff7f0e")
        ax.plot(tks, m_m, color="#1f77b4", lw=1.5, label="Mothers")
        ax.plot(tks, c_m, color="#ff7f0e", lw=1.5, label="Children")
        ax.set_title(NICE[cond_label], fontsize=10)
        ax.set_xlabel("Tick")
        ax.legend(fontsize=8)
    axes[0].set_ylabel("Mean population")
    fig.suptitle("Phase 5e — Adult vs Child Population Over Time", fontsize=12)
    plt.tight_layout()
    plt.savefig(os.path.join(out_dir, "01_adult_child_pop.png"), dpi=120)
    plt.close(fig)


def plot_food_pop(agg_by_cond: dict, out_dir: str) -> None:
    fig, axes = plt.subplots(1, 3, figsize=(15, 4))
    for ax, cond_label in zip(axes, ["no_care", "canonical", "high_care"]):
        a = agg_by_cond[cond_label]
        tks = _ticks(a)
        pop  = np.array([r["mean_total_pop"]  for r in a])
        food = np.array([r["mean_food_count"] for r in a])

        ax2 = ax.twinx()
        ax.plot(tks, pop,  color=COLORS[cond_label], lw=1.5, label="Population")
        ax2.plot(tks, food, color="darkorange", lw=1.2, linestyle="--", label="Food")
        ax2.set_ylabel("Food count", color="darkorange", fontsize=8)
        ax2.tick_params(axis="y", colors="darkorange")
        ax.set_title(NICE[cond_label], fontsize=10)
        ax.set_xlabel("Tick")
    axes[0].set_ylabel("Mean total population")
    fig.suptitle("Phase 5e — Food Count + Population Over Time (dual axis)", fontsize=12)
    plt.tight_layout()
    plt.savefig(os.path.join(out_dir, "02_food_pop.png"), dpi=120)
    plt.close(fig)


def plot_births_deaths(agg_by_cond: dict, out_dir: str) -> None:
    fig, axes = plt.subplots(2, 3, figsize=(15, 7), sharey="row")
    W = 15
    for col, cond_label in enumerate(["no_care", "canonical", "high_care"]):
        a   = agg_by_cond[cond_label]
        tks = _ticks(a)
        births = _smooth([r["mean_n_born_tick"]  for r in a], W)
        deaths = _smooth([r["mean_n_died_tick"]  for r in a], W)
        axes[0][col].plot(tks, births, color=COLORS[cond_label], lw=1.5)
        axes[0][col].set_title(NICE[cond_label], fontsize=9)
        axes[1][col].plot(tks, deaths, color=COLORS[cond_label], lw=1.5)
        axes[0][col].set_xlabel("Tick")
        axes[1][col].set_xlabel("Tick")
    axes[0][0].set_ylabel("Births / tick (smoothed)")
    axes[1][0].set_ylabel("Deaths / tick (smoothed)")
    fig.suptitle("Phase 5e — Births and Deaths Over Time", fontsize=12)
    plt.tight_layout()
    plt.savefig(os.path.join(out_dir, "03_births_deaths.png"), dpi=120)
    plt.close(fig)


def plot_energy_dist(agg_by_cond: dict, out_dir: str) -> None:
    fig, axes = plt.subplots(1, 3, figsize=(15, 4), sharey=True)
    for ax, cond_label in zip(axes, ["no_care", "canonical", "high_care"]):
        a   = agg_by_cond[cond_label]
        tks = np.array(_ticks(a))
        med = np.array([r["mean_eng_med"] for r in a])
        p25 = np.array([r["mean_eng_p25"] for r in a])
        p75 = np.array([r["mean_eng_p75"] for r in a])
        # mask NaNs
        mask = ~np.isnan(med)
        ax.fill_between(tks[mask], p25[mask], p75[mask],
                        alpha=0.3, color=COLORS[cond_label], label="p25–p75")
        ax.plot(tks[mask], med[mask], color=COLORS[cond_label], lw=1.5, label="Median")
        ax.axhline(0, color="gray", lw=0.5, linestyle=":")
        ax.set_title(NICE[cond_label], fontsize=10)
        ax.set_xlabel("Tick")
        ax.set_ylim(-0.05, 1.05)
        ax.legend(fontsize=8)
    axes[0].set_ylabel("Mother energy")
    fig.suptitle("Phase 5e — Mother Energy Distribution Over Time", fontsize=12)
    plt.tight_layout()
    plt.savefig(os.path.join(out_dir, "04_energy_dist.png"), dpi=120)
    plt.close(fig)


def plot_death_causes(results_by_cond: dict, duration: int, out_dir: str) -> None:
    BIN = 50
    edges = list(range(0, duration + BIN, BIN))
    bin_mid = [(edges[i] + edges[i + 1]) / 2 for i in range(len(edges) - 1)]

    fig, axes = plt.subplots(1, 3, figsize=(15, 4), sharey=True)
    for ax, cond_label in zip(axes, ["no_care", "canonical", "high_care"]):
        results = results_by_cond[cond_label]
        m_star  = [0.0] * len(bin_mid)
        ch_star = [0.0] * len(bin_mid)
        cm_star = [0.0] * len(bin_mid)
        n = len(results)
        for r in results:
            for row in r["per_tick"]:
                b = min(int((row["tick"] - 1) // BIN), len(bin_mid) - 1)
                m_star[b]  += row["n_died_mother"]
                ch_star[b] += row["n_died_child_hunger"]
                cm_star[b] += row["n_died_child_matured"]
        # average over seeds
        m_star  = [v / n for v in m_star]
        ch_star = [v / n for v in ch_star]
        cm_star = [v / n for v in cm_star]

        ax.bar(bin_mid, m_star,  width=BIN * 0.8, color="#d62728", alpha=0.8, label="Mother starvation")
        ax.bar(bin_mid, ch_star, width=BIN * 0.8, bottom=m_star, color="#ff7f0e", alpha=0.8, label="Child hunger")
        bot2 = [a + b for a, b in zip(m_star, ch_star)]
        ax.bar(bin_mid, cm_star, width=BIN * 0.8, bottom=bot2, color="#2ca02c", alpha=0.8, label="Child matured")
        ax.set_title(NICE[cond_label], fontsize=10)
        ax.set_xlabel("Tick")
        ax.legend(fontsize=7)
    axes[0].set_ylabel(f"Mean deaths per {BIN}-tick bin")
    fig.suptitle("Phase 5e — Death Cause Breakdown Over Time", fontsize=12)
    plt.tight_layout()
    plt.savefig(os.path.join(out_dir, "05_death_causes.png"), dpi=120)
    plt.close(fig)


def plot_forage_crowding(agg_by_cond: dict, out_dir: str) -> None:
    fig, axes = plt.subplots(1, 3, figsize=(15, 4))
    for ax, cond_label in zip(axes, ["no_care", "canonical", "high_care"]):
        a   = agg_by_cond[cond_label]
        tks = _ticks(a)
        unavail  = [r["mean_food_unavail"]       for r in a]
        crowding = [r["mean_occupied_density"]   for r in a]

        ax2 = ax.twinx()
        ax.plot(tks, unavail,  color="crimson",    lw=1.5, label="Food unavail (frac seeds)")
        ax2.plot(tks, crowding, color="steelblue", lw=1.2, linestyle="--", label="Crowding density")
        ax.set_ylim(-0.05, 1.05)
        ax2.set_ylim(0)
        ax2.set_ylabel("Occupied / 900", color="steelblue", fontsize=8)
        ax2.tick_params(axis="y", colors="steelblue")
        ax.set_title(NICE[cond_label], fontsize=10)
        ax.set_xlabel("Tick")
    axes[0].set_ylabel("Fraction seeds with food==0")
    fig.suptitle("Phase 5e — Food Unavailability + Crowding Over Time", fontsize=12)
    plt.tight_layout()
    plt.savefig(os.path.join(out_dir, "06_forage_crowding.png"), dpi=120)
    plt.close(fig)


def plot_care_burden(agg_by_cond: dict, out_dir: str) -> None:
    fig, axes = plt.subplots(2, 3, figsize=(15, 7), sharey="row")
    W = 10
    for col, cond_label in enumerate(["no_care", "canonical", "high_care"]):
        a   = agg_by_cond[cond_label]
        tks = _ticks(a)
        feed = _smooth([r["mean_n_feed_tick"]       for r in a], W)
        hung = [r["mean_mean_child_hunger"] for r in a]

        axes[0][col].plot(tks, feed, color=COLORS[cond_label], lw=1.5)
        axes[0][col].set_title(NICE[cond_label], fontsize=9)
        axes[1][col].plot(tks, hung, color="darkorange", lw=1.2)
        axes[0][col].set_xlabel("Tick")
        axes[1][col].set_xlabel("Tick")
    axes[0][0].set_ylabel("FEED_CHILD / tick (smoothed)")
    axes[1][0].set_ylabel("Mean child hunger")
    fig.suptitle("Phase 5e — Care Burden: FEED Rate and Child Hunger Over Time", fontsize=12)
    plt.tight_layout()
    plt.savefig(os.path.join(out_dir, "07_care_burden.png"), dpi=120)
    plt.close(fig)


def plot_crash_timeline(results_by_cond: dict, out_dir: str) -> None:
    """Jitter scatter: each seed a point; x=tick; events as colour/marker."""
    EVENT_KEYS = [
        ("peak_pop_tick",   "Peak pop",          "o", "#1f77b4"),
        ("food_depl_tick",  "Food depleted",     "s", "#d62728"),
        ("birth_peak_tick", "Birth peak",         "^", "#ff7f0e"),
        ("death_peak_tick", "Death peak",         "v", "#9467bd"),
        ("crash_tick",      "Extinction",         "X", "#2ca02c"),
    ]
    cond_labels = ["no_care", "canonical", "high_care"]
    y_pos = {c: i for i, c in enumerate(cond_labels)}

    fig, ax = plt.subplots(figsize=(12, 5))
    legend_handles = []
    rng = np.random.default_rng(0)

    for ek, label, marker, color in EVENT_KEYS:
        for cond_label in cond_labels:
            results = results_by_cond[cond_label]
            vals = [r[ek] for r in results if r[ek] > 0]
            if not vals:
                continue
            y_base = y_pos[cond_label]
            jitter = rng.uniform(-0.15, 0.15, len(vals))
            sc = ax.scatter(vals, y_base + jitter, marker=marker, color=color,
                            alpha=0.5, s=20, zorder=3)
        # one handle per event type
        from matplotlib.lines import Line2D
        legend_handles.append(Line2D([0], [0], marker=marker, color="w",
                                      markerfacecolor=color, markersize=8, label=label))

    ax.set_yticks(list(y_pos.values()))
    ax.set_yticklabels([NICE[c] for c in cond_labels])
    ax.set_xlabel("Tick")
    ax.set_title("Phase 5e — Crash Timeline (per-seed events)", fontsize=12)
    ax.legend(handles=legend_handles, loc="upper left", fontsize=8)
    ax.grid(axis="x", alpha=0.3)
    plt.tight_layout()
    plt.savefig(os.path.join(out_dir, "08_crash_timeline.png"), dpi=120)
    plt.close(fig)


# ── CSV writers ────────────────────────────────────────────────────────────────

OUTCOME_FIELDS = [
    "condition", "seed", "final_pop", "extinct", "max_gen",
    "total_births", "n_mother_deaths", "n_child_hunger_deaths", "n_child_matured_all",
    "init_child_survival", "feed_rate", "mean_births_per_mother",
    "peak_pop", "peak_pop_tick", "food_depl_tick", "birth_peak_tick",
    "death_peak_tick", "crash_tick",
]

PER_TICK_FIELDS = [
    "condition", "tick",
    "mean_n_mothers", "std_n_mothers",
    "mean_n_children", "std_n_children",
    "mean_total_pop", "std_total_pop",
    "mean_food_count", "std_food_count",
    "mean_occupied_density", "std_occupied_density",
    "mean_eng_mean", "mean_eng_p25", "mean_eng_med", "mean_eng_p75",
    "mean_mean_child_hunger", "mean_mean_mc_dist",
    "mean_n_feed_tick", "mean_n_born_tick", "mean_n_died_tick",
    "mean_n_died_mother", "mean_n_died_child_hunger", "mean_n_died_child_matured",
    "mean_food_unavail",
]


# ── Main ───────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--duration", type=int, default=3000)
    parser.add_argument("--seeds",    type=int, default=30)
    args = parser.parse_args()

    ts     = datetime.now().strftime("%Y%m%d_%H%M%S")
    outdir = os.path.join(PROJECT_ROOT, "outputs", "phase5e_crash_diagnosis", ts)
    data_dir = os.path.join(outdir, "data")
    plot_dir = os.path.join(outdir, "plots")
    os.makedirs(data_dir, exist_ok=True)
    os.makedirs(plot_dir, exist_ok=True)

    total_runs = len(CONDITIONS) * args.seeds
    print(f"Phase 5e: {total_runs} runs ({len(CONDITIONS)} conds x {args.seeds} seeds x {args.duration} ticks)")

    results_by_cond: dict[str, list[dict]] = {c["label"]: [] for c in CONDITIONS}
    run_idx = 0

    # ── CSV writers (open before run loop) ────────────────────────────────────
    outcome_path  = os.path.join(data_dir, "outcomes_all.csv")
    per_tick_path = os.path.join(data_dir, "per_tick_diagnostic.csv")

    out_f = open(outcome_path, "w", newline="", encoding="utf-8")
    out_w = csv.DictWriter(out_f, fieldnames=OUTCOME_FIELDS, extrasaction="ignore")
    out_w.writeheader()

    pt_f  = open(per_tick_path, "w", newline="", encoding="utf-8")
    pt_w  = csv.DictWriter(pt_f, fieldnames=PER_TICK_FIELDS, extrasaction="ignore")
    pt_w.writeheader()

    for cond in CONDITIONS:
        for seed in range(args.seeds):
            run_idx += 1
            print(f"  [{run_idx}/{total_runs}] {cond['label']} seed={seed}", end="\r", flush=True)
            r = run_single(cond, seed, args.duration)
            results_by_cond[cond["label"]].append(r)
            out_w.writerow(r)

    out_f.close()
    print()

    # ── Aggregate per-tick and write CSV ──────────────────────────────────────
    agg_by_cond: dict[str, list[dict]] = {}
    for cond in CONDITIONS:
        cl  = cond["label"]
        agg = agg_per_tick(results_by_cond[cl], args.duration)
        agg_by_cond[cl] = agg
        for row in agg:
            pt_w.writerow({"condition": cl, **row})
    pt_f.close()

    # ── Aggregate outcomes ────────────────────────────────────────────────────
    summary_by_cond = {
        c["label"]: agg_outcomes(results_by_cond[c["label"]]) for c in CONDITIONS
    }

    # ── Sanity checks ─────────────────────────────────────────────────────────
    for cl, agg in agg_by_cond.items():
        assert len(agg) == args.duration, f"[{cl}] agg length {len(agg)} != {args.duration}"
        assert agg[-1]["tick"] == args.duration, f"[{cl}] last tick {agg[-1]['tick']}"
    print("Sanity checks passed: per_tick coverage verified.")

    # ── Plots ──────────────────────────────────────────────────────────────────
    plot_adult_child_pop(agg_by_cond, plot_dir)
    plot_food_pop(agg_by_cond, plot_dir)
    plot_births_deaths(agg_by_cond, plot_dir)
    plot_energy_dist(agg_by_cond, plot_dir)
    plot_death_causes(results_by_cond, args.duration, plot_dir)
    plot_forage_crowding(agg_by_cond, plot_dir)
    plot_care_burden(agg_by_cond, plot_dir)
    plot_crash_timeline(results_by_cond, plot_dir)
    print(f"8 plots saved to {plot_dir}")

    # ── Crash mechanism analysis ───────────────────────────────────────────────
    # Compute mean lag: food_depl_tick vs death_peak_tick vs crash_tick
    mechanism_notes: list[str] = []
    for cl in ["no_care", "canonical", "high_care"]:
        s = summary_by_cond[cl]
        _fdt = s["food_depl_tick_mean"]
        _dpt = s["death_peak_tick_mean"]
        _ct  = s["crash_tick_mean"]
        _ppt = s["peak_pop_tick_mean"]
        if _ct > 0:
            food_str = f"food_depl={_fdt:.0f}t" if _fdt > 0 else "food_depl=NEVER"
            mechanism_notes.append(
                f"{cl}: peak_pop_t={_ppt:.0f} peak_pop_val={s['peak_pop_mean']:.1f} "
                f"{food_str} birth_peak={s['birth_peak_tick_mean']:.0f}t "
                f"death_peak={_dpt:.0f}t crash={_ct:.0f}t "
                f"decline_duration={(_ct - _ppt):.0f}"
            )

    # Determine dominant mechanism from crash-event ordering and food status
    canonical = summary_by_cond["canonical"]
    bpt = canonical["birth_peak_tick_mean"]
    fdt = canonical["food_depl_tick_mean"]
    dpt = canonical["death_peak_tick_mean"]
    ct  = canonical["crash_tick_mean"]
    ppt = canonical["peak_pop_tick_mean"]
    decline_dur = ct - ppt  # ticks from peak to extinction

    if fdt <= 0:
        # Food NEVER hits zero — burst replenishment prevents it.
        # Crash driven by chronic energy deficit, not acute food collapse.
        if decline_dur > 200:
            dominant_mechanism = "CHRONIC_ENERGY_DEPLETION"
            mechanism_detail   = (
                f"Food never depletes to zero (burst replenishment prevents it). "
                f"Crash is gradual: peak_pop at tick {ppt:.0f}, extinction at tick {ct:.0f} "
                f"({decline_dur:.0f}-tick decline). Root cause: reproduction_cost drains "
                f"mothers faster than limited food supply can restore energy; "
                f"chronic energy deficit accumulates over {decline_dur:.0f} ticks."
            )
        else:
            dominant_mechanism = "CHRONIC_ENERGY_DEPLETION_FAST"
            mechanism_detail   = (
                f"Food never hits zero but population declines rapidly ({decline_dur:.0f} ticks "
                f"from peak to extinction). Energy drain from reproduction cost and foraging "
                f"outpaces food intake."
            )
    elif fdt > 0 and bpt > 0 and bpt < fdt:
        dominant_mechanism = "REPRODUCTION_PRESSURE_then_FOOD_COLLAPSE"
        mechanism_detail   = (
            f"Birth peak ({bpt:.0f}) precedes food depletion ({fdt:.0f}) by {fdt-bpt:.0f} ticks. "
            f"Reproduction boom exhausts food; death cascade follows {dpt-fdt:.0f} ticks later."
        )
    elif fdt > 0 and dpt > 0 and dpt - fdt < 50:
        dominant_mechanism = "FOOD_COLLAPSE"
        mechanism_detail   = (
            f"Food depletes at tick {fdt:.0f}; death peak follows {dpt-fdt:.0f} ticks later. "
            f"Rapid starvation cascade after food exhaustion."
        )
    else:
        dominant_mechanism = "UNDETERMINED"
        mechanism_detail   = "Multiple factors; inspect plots for primary signal."

    # ── Summary JSON ──────────────────────────────────────────────────────────
    summary = {
        "phase":             "5e",
        "description":       "Crash mechanism diagnosis — fixed cfr_0.10 ecology",
        "n_conditions":      len(CONDITIONS),
        "n_seeds":           args.seeds,
        "duration":          args.duration,
        "ecology": {
            "init_food":              INIT_FOOD,
            "replenish_amount":       REPLENISH_AMOUNT,
            "threshold_ratio":        THRESHOLD_RATIO,
            "continuous_food_rate":   CONTINUOUS_FOOD_RATE,
            "continuous_food_max":    CONTINUOUS_FOOD_MAX,
            "infant_starvation_mult": INFANT_STARVATION_MULTIPLIER,
        },
        "dominant_mechanism":  dominant_mechanism,
        "mechanism_detail":    mechanism_detail,
        "mechanism_notes":     mechanism_notes,
        "condition_summaries": {cl: summary_by_cond[cl] for cl in ["no_care", "canonical", "high_care"]},
    }

    summary_path = os.path.join(outdir, "summary.json")
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    # ── Print digest ──────────────────────────────────────────────────────────
    print(f"\nOutput: {outdir}")
    print(f"Dominant crash mechanism: {dominant_mechanism}")
    print(f"Detail: {mechanism_detail}")
    print("\nCondition summaries (canonical):")
    for cl in ["no_care", "canonical", "high_care"]:
        s = summary_by_cond[cl]
        print(
            f"  {cl:12s}: ext={s['extinction_rate']:.2f} "
            f"peak_pop={s['peak_pop_mean']:.1f}+/-{s['peak_pop_sd']:.1f} "
            f"peak_pop_t={s['peak_pop_tick_mean']:.0f} "
            f"food_depl_t={s['food_depl_tick_mean']:.0f} "
            f"crash_t={s['crash_tick_mean']:.0f} "
            f"max_gen={s['max_gen_mean']:.1f}"
        )
    print()
    for note in mechanism_notes:
        print(" ", note)

    # exit code: 0 (diagnostic — no pass/fail verdict)
    sys.exit(0)


if __name__ == "__main__":
    main()
