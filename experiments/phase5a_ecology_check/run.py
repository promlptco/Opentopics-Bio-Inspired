#!/usr/bin/env python3
"""
Phase 5a -- Reproduction-Enabled Ecology Check

Tests whether care improves population persistence when reproduction is ON.
Canonical genome from Phase 4b (cw=0.3, fw=0.85, sw=0.3) compared to
a no-care control and a high-care reference.

Settings:
  reproduction=ON, mutation=OFF, plasticity=OFF, children=ON
  infant_starvation_multiplier=1.5, init_mothers=12, init_food=45

Conditions:
  1. no_care:   cw=0.0, fw=0.85, sw=0.3
  2. canonical: cw=0.3, fw=0.85, sw=0.3
  3. high_care: cw=0.5, fw=0.85, sw=0.3

Usage:
    python experiments/phase5a_ecology_check/run.py --duration 3000 --seeds 30
"""

import argparse
import csv
import json
import math
import os
import sys
from datetime import datetime

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, PROJECT_ROOT)

from config import Config
from simulation.simulation import Simulation

# ── Constants ─────────────────────────────────────────────────────────────────

INFANT_STARVATION_MULTIPLIER = 1.5  # frozen from Phase 3

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

NICE_LABELS = {
    "no_care":   "No-Care (cw=0.0)",
    "canonical": "Canonical (cw=0.3)",
    "high_care": "High-Care (cw=0.5)",
}


# ── Config builder ─────────────────────────────────────────────────────────────

def make_config(cond: dict, seed: int, duration: int) -> Config:
    cfg = Config()
    cfg.seed = seed
    cfg.max_ticks = duration
    cfg.infant_starvation_multiplier = INFANT_STARVATION_MULTIPLIER
    cfg.care_weight   = cond["care_w"]
    cfg.forage_weight = cond["forage_w"]
    cfg.self_weight   = cond["self_w"]
    cfg.care_enabled         = cond["care_w"] > 0.0
    cfg.plasticity_enabled   = False
    cfg.reproduction_enabled = True
    cfg.mutation_enabled     = False
    cfg.children_enabled     = True
    cfg.init_mothers = 12
    cfg.init_food    = 45
    cfg.hunger_rate  = 0.008
    return cfg


# ── Single run ─────────────────────────────────────────────────────────────────

def run_single(cond: dict, seed: int, duration: int) -> dict:
    cfg = make_config(cond, seed, duration)
    sim = Simulation(cfg)
    sim.initialize()

    initial_mother_ids = {m.id for m in sim.mothers}
    initial_child_ids  = {c.id for c in sim.children}
    n_initial_mothers  = len(sim.mothers)
    n_initial_children = len(sim.children)

    per_tick: list[dict] = []
    birth_records_raw: list[dict] = []

    for t in range(duration):
        births_before = len(sim.logger.birth_records)
        care_before   = len(sim.logger.care_records)

        sim.step()
        sim.tick += 1

        new_births  = sim.logger.birth_records[births_before:]
        n_born_tick = len(new_births)
        for br in new_births:
            birth_records_raw.append({
                "condition":          cond["label"],
                "seed":               seed,
                "tick":               br.tick,
                "mother_id":          br.mother_id,
                "child_id":           br.child_id,
                "mother_lineage_id":  br.mother_lineage_id,
                "mother_generation":  br.mother_generation,
                "child_generation":   br.mother_generation + 1,
                "mother_care_weight": round(br.mother_care_weight, 4),
            })

        new_care    = sim.logger.care_records[care_before:]
        n_feed_tick = sum(1 for r in new_care if r.benefit > 0)

        alive_mothers  = sim.mothers
        alive_children = sim.children

        mean_energy = (
            float(np.mean([m.energy for m in alive_mothers]))
            if alive_mothers else float("nan")
        )
        mean_child_hunger = (
            float(np.mean([c.hunger for c in alive_children]))
            if alive_children else float("nan")
        )

        per_tick.append({
            "tick":             t + 1,
            "n_mothers":        len(alive_mothers),
            "n_children":       len(alive_children),
            "total_pop":        len(alive_mothers) + len(alive_children),
            "mean_energy":      mean_energy,
            "mean_child_hunger": mean_child_hunger,
            "n_feed_tick":      n_feed_tick,
            "n_born_tick":      n_born_tick,
        })

    # ── Post-run outcomes ──────────────────────────────────────────────────────
    final_pop = len(sim.mothers) + len(sim.children)
    extinct   = final_pop == 0

    max_gen = max(sim.lineage.generations.values()) if sim.lineage.generations else 0

    total_births = len(sim.logger.birth_records)

    death_records = sim.logger.death_records
    n_mother_deaths       = sum(1 for d in death_records if d.agent_type == "mother")
    n_child_hunger_deaths = sum(
        1 for d in death_records if d.agent_type == "child" and d.cause == "hunger"
    )
    n_child_matured_all   = sum(
        1 for d in death_records if d.agent_type == "child" and d.cause == "matured"
    )

    # Initial 12 child outcomes
    init_matured   = sum(
        1 for d in death_records
        if d.agent_type == "child" and d.cause == "matured"
        and d.agent_id in initial_child_ids
    )
    init_alive_end = sum(1 for c in sim.children if c.id in initial_child_ids)
    initial_child_survival = (
        (init_matured + init_alive_end) / n_initial_children
        if n_initial_children > 0 else 0.0
    )
    initial_child_matured_rate = (
        init_matured / n_initial_children
        if n_initial_children > 0 else 0.0
    )

    # Overall child survival across all children ever born
    total_children_ever   = n_initial_children + total_births
    n_children_alive_end  = len(sim.children)
    overall_child_survival = (
        (n_child_matured_all + n_children_alive_end) / total_children_ever
        if total_children_ever > 0 else 0.0
    )

    # Initial mother survival (original 12)
    init_mothers_alive_end = sum(1 for m in sim.mothers if m.id in initial_mother_ids)
    initial_mother_survival = (
        init_mothers_alive_end / n_initial_mothers
        if n_initial_mothers > 0 else 0.0
    )

    n_feed_total = sum(1 for r in sim.logger.care_records if r.benefit > 0)
    feed_rate    = n_feed_total / duration

    # Descendants per founding lineage (births via reproduction)
    lineage_descendants: dict[int, int] = {}
    for br in sim.logger.birth_records:
        lid = br.mother_lineage_id
        lineage_descendants[lid] = lineage_descendants.get(lid, 0) + 1

    max_desc  = max(lineage_descendants.values()) if lineage_descendants else 0
    mean_desc = float(np.mean(list(lineage_descendants.values()))) if lineage_descendants else 0.0

    surviving_lineage_set = {m.lineage_id for m in sim.mothers}

    return {
        "condition":               cond["label"],
        "seed":                    seed,
        "final_pop":               final_pop,
        "final_n_mothers":         len(sim.mothers),
        "final_n_children":        len(sim.children),
        "extinct":                 extinct,
        "max_gen":                 max_gen,
        "total_births":            total_births,
        "n_mother_deaths":         n_mother_deaths,
        "n_child_hunger_deaths":   n_child_hunger_deaths,
        "n_child_matured_all":     n_child_matured_all,
        "initial_child_survival":  initial_child_survival,
        "initial_child_matured_rate": initial_child_matured_rate,
        "overall_child_survival":  overall_child_survival,
        "initial_mother_survival": initial_mother_survival,
        "feed_rate":               feed_rate,
        "n_feed_total":            n_feed_total,
        "max_desc":                max_desc,
        "mean_desc":               mean_desc,
        "surviving_lineages":      len(surviving_lineage_set),
        "per_tick":                per_tick,
        "birth_records_raw":       birth_records_raw,
        "lineage_descendants":     lineage_descendants,
        "surviving_lineage_set":   surviving_lineage_set,
    }


# ── Aggregation ────────────────────────────────────────────────────────────────

def _ms(results: list[dict], key: str) -> tuple[float, float]:
    vals = [r[key] for r in results]
    return float(np.mean(vals)), float(np.std(vals))


def aggregate(results: list[dict]) -> dict:
    label = results[0]["condition"]
    n = len(results)

    extinction_rate = sum(1 for r in results if r["extinct"]) / n
    n_gen2plus      = sum(1 for r in results if r["max_gen"] >= 2)

    fp_m,   fp_s   = _ms(results, "final_pop")
    mg_m,   mg_s   = _ms(results, "max_gen")
    tb_m,   tb_s   = _ms(results, "total_births")
    ics_m,  ics_s  = _ms(results, "initial_child_survival")
    icmr_m, _      = _ms(results, "initial_child_matured_rate")
    ocs_m,  ocs_s  = _ms(results, "overall_child_survival")
    ims_m,  ims_s  = _ms(results, "initial_mother_survival")
    fr_m,   fr_s   = _ms(results, "feed_rate")
    md_m,   md_s   = _ms(results, "max_desc")
    sl_m,   sl_s   = _ms(results, "surviving_lineages")

    return {
        "condition":             label,
        "n_seeds":               n,
        "extinction_rate":       extinction_rate,
        "n_seeds_gen2plus":      n_gen2plus,
        "final_pop_mean":        fp_m,   "final_pop_sd":        fp_s,
        "max_gen_mean":          mg_m,   "max_gen_sd":          mg_s,
        "total_births_mean":     tb_m,   "total_births_sd":     tb_s,
        "init_child_survival_mean": ics_m, "init_child_survival_sd": ics_s,
        "init_child_matured_rate_mean": icmr_m,
        "overall_child_survival_mean": ocs_m, "overall_child_survival_sd": ocs_s,
        "init_mother_survival_mean": ims_m, "init_mother_survival_sd": ims_s,
        "feed_rate_mean":        fr_m,   "feed_rate_sd":        fr_s,
        "max_desc_mean":         md_m,   "max_desc_sd":         md_s,
        "surviving_lineages_mean": sl_m, "surviving_lineages_sd": sl_s,
    }


def aggregate_per_tick(results: list[dict], duration: int) -> list[dict]:
    agg = []
    for t in range(duration):
        rows = [r["per_tick"][t] for r in results if len(r["per_tick"]) > t]
        if not rows:
            continue

        def nanmean(key: str) -> float:
            finite = [row[key] for row in rows if not math.isnan(row[key])]
            return float(np.mean(finite)) if finite else float("nan")

        def nanstd(key: str) -> float:
            finite = [row[key] for row in rows if not math.isnan(row[key])]
            return float(np.std(finite)) if finite else float("nan")

        def mean(key: str) -> float:
            return float(np.mean([row[key] for row in rows]))

        def std(key: str) -> float:
            return float(np.std([row[key] for row in rows]))

        agg.append({
            "tick":             t + 1,
            "mean_n_mothers":   mean("n_mothers"),
            "mean_n_children":  mean("n_children"),
            "mean_total_pop":   mean("total_pop"),
            "std_total_pop":    std("total_pop"),
            "mean_energy":      nanmean("mean_energy"),
            "std_energy":       nanstd("mean_energy"),
            "mean_child_hunger": nanmean("mean_child_hunger"),
            "mean_feed_tick":   mean("n_feed_tick"),
            "std_feed_tick":    std("n_feed_tick"),
            "mean_born_tick":   mean("n_born_tick"),
        })
    return agg


# ── CSV output ─────────────────────────────────────────────────────────────────

OUTCOME_FIELDS = [
    "condition", "seed",
    "final_pop", "final_n_mothers", "final_n_children", "extinct", "max_gen",
    "total_births", "n_mother_deaths", "n_child_hunger_deaths", "n_child_matured_all",
    "initial_child_survival", "initial_child_matured_rate", "overall_child_survival",
    "initial_mother_survival",
    "feed_rate", "n_feed_total",
    "max_desc", "mean_desc", "surviving_lineages",
]

PER_TICK_FIELDS = [
    "condition", "tick",
    "mean_n_mothers", "mean_n_children", "mean_total_pop", "std_total_pop",
    "mean_energy", "std_energy", "mean_child_hunger",
    "mean_feed_tick", "std_feed_tick", "mean_born_tick",
]

BIRTH_LOG_FIELDS = [
    "condition", "seed", "tick",
    "mother_id", "child_id", "mother_lineage_id",
    "mother_generation", "child_generation", "mother_care_weight",
]

LINEAGE_LOG_FIELDS = [
    "condition", "seed", "lineage_id", "n_descendants", "survived",
]


def _open_csv(out_dir: str, subdir: str, fname: str, fields: list):
    path = os.path.join(out_dir, subdir, fname)
    f = open(path, "w", newline="", encoding="utf-8")
    w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
    w.writeheader()
    return w, f


# ── JSON output ────────────────────────────────────────────────────────────────

def save_config_json(duration: int, n_seeds: int, out_dir: str) -> None:
    doc = {
        "phase": "5a",
        "experiment": "reproduction_enabled_ecology_check",
        "duration_ticks": duration,
        "n_seeds": n_seeds,
        "conditions": CONDITIONS,
        "frozen_from_phase3": {
            "infant_starvation_multiplier": INFANT_STARVATION_MULTIPLIER,
            "effective_child_hunger_rate":  round(0.008 * INFANT_STARVATION_MULTIPLIER, 4),
        },
        "fixed_settings": {
            "plasticity_enabled":     False,
            "reproduction_enabled":   True,
            "mutation_enabled":       False,
            "children_enabled":       True,
            "init_mothers":           12,
            "init_food":              45,
            "hunger_rate":            0.008,
            "reproduction_threshold": 0.95,
            "reproduction_cost":      0.35,
            "reproduction_cooldown":  80,
            "max_population":         100,
        },
        "success_criteria": [
            "no_care performs worse than care conditions",
            "care genome improves child survival or descendant count",
            "population does not collapse across most seeds",
            "at least one care condition reaches generation 2",
            "FEED_CHILD events occur in care conditions",
        ],
        "failure_criteria": [
            "all conditions go extinct",
            "care does not improve over no-care",
            "population explodes uncontrollably",
        ],
    }
    with open(os.path.join(out_dir, "config.json"), "w", encoding="utf-8") as f:
        json.dump(doc, f, indent=2)


def save_summary_json(all_agg: list[dict], out_dir: str) -> str:
    no_care   = next((a for a in all_agg if a["condition"] == "no_care"),   {})
    canonical = next((a for a in all_agg if a["condition"] == "canonical"), {})
    high_care = next((a for a in all_agg if a["condition"] == "high_care"), {})

    care_improves_child = (
        canonical.get("init_child_survival_mean", 0) > no_care.get("init_child_survival_mean", 0)
        or high_care.get("init_child_survival_mean", 0) > no_care.get("init_child_survival_mean", 0)
    )
    care_improves_desc = (
        canonical.get("total_births_mean", 0) > no_care.get("total_births_mean", 0)
        or high_care.get("total_births_mean", 0) > no_care.get("total_births_mean", 0)
    )
    no_care_worse = (
        no_care.get("extinction_rate", 0) > canonical.get("extinction_rate", 1)
        or no_care.get("final_pop_mean", 0) < canonical.get("final_pop_mean", 0)
    )
    feed_events_occur = (
        canonical.get("feed_rate_mean", 0) > 0
        or high_care.get("feed_rate_mean", 0) > 0
    )
    any_reaches_gen2 = (
        canonical.get("n_seeds_gen2plus", 0) > 0
        or high_care.get("n_seeds_gen2plus", 0) > 0
    )
    all_extinct = all(a.get("extinction_rate", 0) >= 1.0 for a in all_agg)

    if all_extinct:
        verdict = "FAIL -- all conditions went extinct"
    elif not feed_events_occur:
        verdict = "FAIL -- no FEED_CHILD events in care conditions"
    elif not care_improves_child and not care_improves_desc:
        verdict = "FAIL -- care does not improve child survival or descendants"
    elif not any_reaches_gen2:
        verdict = "FAIL -- no seeds reached generation 2"
    else:
        verdict = "PASS -- care improves ecology"

    doc = {
        "phase": "5a",
        "verdict": verdict,
        "checks": {
            "care_improves_child_survival": care_improves_child,
            "care_improves_descendants":    care_improves_desc,
            "no_care_performs_worse":       no_care_worse,
            "feed_events_occur":            feed_events_occur,
            "any_condition_reaches_gen2":   any_reaches_gen2,
            "all_conditions_extinct":       all_extinct,
        },
        "conditions": [
            {k: (round(v, 4) if isinstance(v, float) else v) for k, v in a.items()}
            for a in all_agg
        ],
    }
    with open(os.path.join(out_dir, "summary.json"), "w", encoding="utf-8") as f:
        json.dump(doc, f, indent=2)
    return verdict


# ── Plots ─────────────────────────────────────────────────────────────────────

def plot_population_over_time(cond_tick_data: dict, out_dir: str, duration: int) -> None:
    fig, ax = plt.subplots(figsize=(11, 5))
    for label, tick_data in cond_tick_data.items():
        ticks   = [r["tick"] for r in tick_data]
        pop_arr = np.array([r["mean_total_pop"] for r in tick_data])
        std_arr = np.array([r["std_total_pop"]  for r in tick_data])
        c = COLORS[label]
        ax.plot(ticks, pop_arr, color=c, label=NICE_LABELS[label], linewidth=1.8)
        ax.fill_between(ticks,
                        np.maximum(0, pop_arr - std_arr),
                        pop_arr + std_arr,
                        color=c, alpha=0.15)
    ax.set_xlabel("Tick")
    ax.set_ylabel("Total Population (mean +/- SD, 30 seeds)")
    ax.set_title(
        f"Phase 5a: Population Over Time\n"
        f"(reproduction=ON, mutation=OFF, {duration} ticks)"
    )
    ax.legend(fontsize=9)
    ax.set_xlim(0, duration)
    ax.set_ylim(bottom=0)
    plt.tight_layout()
    plt.savefig(os.path.join(out_dir, "plots", "01_population_over_time.png"), dpi=150)
    plt.close()


def plot_final_population(all_agg: list[dict], out_dir: str) -> None:
    labels  = [a["condition"] for a in all_agg]
    means   = [a["final_pop_mean"] for a in all_agg]
    sds     = [a["final_pop_sd"]   for a in all_agg]
    ext_rates = [a["extinction_rate"] for a in all_agg]
    colors  = [COLORS[l] for l in labels]

    fig, ax = plt.subplots(figsize=(7, 5))
    x = np.arange(len(labels))
    bars = ax.bar(x, means, yerr=sds, capsize=6, color=colors, alpha=0.85, width=0.5)
    ax.set_xticks(x)
    ax.set_xticklabels([NICE_LABELS[l] for l in labels], rotation=10)
    ax.set_ylabel("Final Population (mean +/- SD, 30 seeds)")
    ax.set_title("Phase 5a: Final Population by Condition")
    for bar, m, s, e in zip(bars, means, sds, ext_rates):
        ax.text(bar.get_x() + bar.get_width() / 2,
                m + s + 0.5,
                f"ext={e:.0%}", ha="center", va="bottom", fontsize=8)
    ax.set_ylim(bottom=0)
    plt.tight_layout()
    plt.savefig(os.path.join(out_dir, "plots", "02_final_population.png"), dpi=150)
    plt.close()


def plot_max_generation(all_agg: list[dict], out_dir: str) -> None:
    labels = [a["condition"] for a in all_agg]
    means  = [a["max_gen_mean"] for a in all_agg]
    sds    = [a["max_gen_sd"]   for a in all_agg]
    gen2   = [a["n_seeds_gen2plus"] for a in all_agg]
    colors = [COLORS[l] for l in labels]

    fig, ax = plt.subplots(figsize=(7, 5))
    x = np.arange(len(labels))
    bars = ax.bar(x, means, yerr=sds, capsize=6, color=colors, alpha=0.85, width=0.5)
    ax.set_xticks(x)
    ax.set_xticklabels([NICE_LABELS[l] for l in labels], rotation=10)
    ax.set_ylabel("Max Generation Reached (mean +/- SD, 30 seeds)")
    ax.set_title("Phase 5a: Max Generation by Condition")
    for bar, m, s, g in zip(bars, means, sds, gen2):
        ax.text(bar.get_x() + bar.get_width() / 2,
                m + s + 0.05,
                f"gen2+: {g}/30", ha="center", va="bottom", fontsize=8)
    ax.set_ylim(bottom=0)
    plt.tight_layout()
    plt.savefig(os.path.join(out_dir, "plots", "03_max_generation.png"), dpi=150)
    plt.close()


def plot_child_survival(all_agg: list[dict], out_dir: str) -> None:
    labels  = [a["condition"] for a in all_agg]
    init_m  = [a["init_child_survival_mean"]    for a in all_agg]
    init_s  = [a["init_child_survival_sd"]      for a in all_agg]
    ovr_m   = [a["overall_child_survival_mean"] for a in all_agg]
    ovr_s   = [a["overall_child_survival_sd"]   for a in all_agg]

    x = np.arange(len(labels))
    width = 0.35
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.bar(x - width / 2, init_m, width, yerr=init_s, capsize=5,
           color=[COLORS[l] for l in labels], alpha=0.85,
           label="Initial 12 children")
    ax.bar(x + width / 2, ovr_m, width, yerr=ovr_s, capsize=5,
           color=[COLORS[l] for l in labels], alpha=0.45, hatch="//",
           label="All children (incl. born-in-run)")
    ax.set_xticks(x)
    ax.set_xticklabels([NICE_LABELS[l] for l in labels], rotation=10)
    ax.set_ylabel("Child Survival Rate (mean +/- SD)")
    ax.set_ylim(0, 1.15)
    ax.axhline(0.80, color="black", linestyle="--", linewidth=1, label="80% threshold")
    ax.set_title("Phase 5a: Child Survival / Maturation by Condition")
    ax.legend(fontsize=8)
    plt.tight_layout()
    plt.savefig(os.path.join(out_dir, "plots", "04_child_survival.png"), dpi=150)
    plt.close()


def plot_feed_child_rate(cond_tick_data: dict, out_dir: str, duration: int) -> None:
    fig, ax = plt.subplots(figsize=(11, 5))
    for label, tick_data in cond_tick_data.items():
        if label == "no_care":
            continue
        ticks = [r["tick"] for r in tick_data]
        feeds = [r["mean_feed_tick"] for r in tick_data]
        ax.plot(ticks, feeds, color=COLORS[label], label=NICE_LABELS[label], linewidth=1.6)
    ax.set_xlabel("Tick")
    ax.set_ylabel("Mean FEED_CHILD Events per Tick (across 30 seeds)")
    ax.set_title(
        "Phase 5a: FEED_CHILD Rate Over Time\n"
        "(no_care condition excluded -- zero by design)"
    )
    ax.legend(fontsize=9)
    ax.set_xlim(0, duration)
    ax.set_ylim(bottom=0)
    plt.tight_layout()
    plt.savefig(os.path.join(out_dir, "plots", "05_feed_child_rate.png"), dpi=150)
    plt.close()


def plot_descendant_count(all_agg: list[dict], out_dir: str) -> None:
    labels = [a["condition"] for a in all_agg]
    means  = [a["total_births_mean"] for a in all_agg]
    sds    = [a["total_births_sd"]   for a in all_agg]
    colors = [COLORS[l] for l in labels]

    fig, ax = plt.subplots(figsize=(7, 5))
    x = np.arange(len(labels))
    ax.bar(x, means, yerr=sds, capsize=6, color=colors, alpha=0.85, width=0.5)
    ax.set_xticks(x)
    ax.set_xticklabels([NICE_LABELS[l] for l in labels], rotation=10)
    ax.set_ylabel("Total Births via Reproduction (mean +/- SD, 30 seeds)")
    ax.set_title(
        "Phase 5a: Descendant Count by Condition\n"
        "(births via reproduction, excluding initial 12 children)"
    )
    ax.set_ylim(bottom=0)
    plt.tight_layout()
    plt.savefig(os.path.join(out_dir, "plots", "06_descendant_count.png"), dpi=150)
    plt.close()


def plot_mother_energy(cond_tick_data: dict, out_dir: str, duration: int) -> None:
    fig, ax = plt.subplots(figsize=(11, 5))
    for label, tick_data in cond_tick_data.items():
        valid_rows = [(r["tick"], r["mean_energy"])
                      for r in tick_data if not math.isnan(r["mean_energy"])]
        if not valid_rows:
            continue
        ticks, energies = zip(*valid_rows)
        ax.plot(ticks, energies, color=COLORS[label], label=NICE_LABELS[label], linewidth=1.6)
    ax.set_xlabel("Tick")
    ax.set_ylabel("Mean Mother Energy (alive mothers, mean across 30 seeds)")
    ax.set_title("Phase 5a: Mother Energy Over Time")
    ax.legend(fontsize=9)
    ax.set_xlim(0, duration)
    ax.set_ylim(0, 1.05)
    plt.tight_layout()
    plt.savefig(os.path.join(out_dir, "plots", "07_mother_energy.png"), dpi=150)
    plt.close()


# ── Main ─────────────────────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(description="Phase 5a -- Reproduction-Enabled Ecology Check")
    parser.add_argument("--duration", type=int, default=3000)
    parser.add_argument("--seeds",    type=int, default=30)
    args = parser.parse_args()

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir = os.path.join(PROJECT_ROOT, "outputs", "phase5a_ecology_check", timestamp)
    os.makedirs(os.path.join(out_dir, "raw"),   exist_ok=True)
    os.makedirs(os.path.join(out_dir, "plots"), exist_ok=True)

    print(f"\n=== Phase 5a -- Reproduction-Enabled Ecology Check ===")
    print(f"Duration: {args.duration} ticks  |  Seeds: {args.seeds}")
    print(f"Conditions: {len(CONDITIONS)}  (no_care / canonical / high_care)")
    print(f"infant_starvation_multiplier: {INFANT_STARVATION_MULTIPLIER}  "
          f"(child hunger {0.008 * INFANT_STARVATION_MULTIPLIER:.4f}/tick)")
    print(f"Reproduction: ON  |  Mutation: OFF  |  Plasticity: OFF")
    print(f"Output: {out_dir}\n")

    save_config_json(args.duration, args.seeds, out_dir)

    outcome_w, outcome_f = _open_csv(out_dir, "raw", "condition_outcomes.csv", OUTCOME_FIELDS)
    ptick_w,   ptick_f   = _open_csv(out_dir, "raw", "per_tick_agg.csv",       PER_TICK_FIELDS)
    birth_w,   birth_f   = _open_csv(out_dir, "raw", "birth_log.csv",           BIRTH_LOG_FIELDS)
    lineage_w, lineage_f = _open_csv(out_dir, "raw", "lineage_log.csv",         LINEAGE_LOG_FIELDS)

    all_agg: list[dict]  = []
    cond_tick_data: dict = {}   # label -> aggregated per-tick list (for plots)

    for cond in CONDITIONS:
        label = cond["label"]
        print(f"\n--- Condition: {NICE_LABELS[label]} ---")
        cond_results: list[dict] = []

        for seed in range(args.seeds):
            r = run_single(cond, seed, args.duration)

            # Write per-seed rows immediately
            outcome_w.writerow(r)
            outcome_f.flush()

            for row in r["birth_records_raw"]:
                birth_w.writerow(row)
            birth_f.flush()

            # All 12 founding lineages (0–11)
            for lid in range(12):
                n_desc = r["lineage_descendants"].get(lid, 0)
                lineage_w.writerow({
                    "condition":    label,
                    "seed":         seed,
                    "lineage_id":   lid,
                    "n_descendants": n_desc,
                    "survived":     lid in r["surviving_lineage_set"],
                })
            lineage_f.flush()

            cond_results.append(r)

            # Progress report every 5 seeds
            if (seed + 1) % 5 == 0 or seed == args.seeds - 1:
                n_done   = seed + 1
                ext      = sum(1 for x in cond_results if x["extinct"])
                births_m = np.mean([x["total_births"] for x in cond_results])
                gen_m    = np.mean([x["max_gen"] for x in cond_results])
                child_m  = np.mean([x["initial_child_survival"] for x in cond_results])
                print(
                    f"  Seeds {n_done:2d}/{args.seeds}  "
                    f"ext={ext}  births={births_m:.1f}  "
                    f"max_gen={gen_m:.1f}  child_surv={child_m:.3f}"
                )

        agg = aggregate(cond_results)
        all_agg.append(agg)

        tick_agg = aggregate_per_tick(cond_results, args.duration)
        cond_tick_data[label] = tick_agg
        for row in tick_agg:
            ptick_w.writerow({"condition": label, **row})
        ptick_f.flush()

        # Free large per-seed data
        for r in cond_results:
            del r["per_tick"]
            del r["birth_records_raw"]
            del r["lineage_descendants"]
            del r["surviving_lineage_set"]

        print(
            f"  DONE: ext={agg['extinction_rate']:.2f}  "
            f"pop={agg['final_pop_mean']:.1f}+/-{agg['final_pop_sd']:.1f}  "
            f"max_gen={agg['max_gen_mean']:.1f}  "
            f"births={agg['total_births_mean']:.1f}  "
            f"child_surv={agg['init_child_survival_mean']:.3f}  "
            f"feed={agg['feed_rate_mean']:.3f}/tick"
        )

    outcome_f.close()
    ptick_f.close()
    birth_f.close()
    lineage_f.close()

    verdict = save_summary_json(all_agg, out_dir)

    print("\nGenerating plots...")
    plot_population_over_time(cond_tick_data, out_dir, args.duration)
    plot_final_population(all_agg, out_dir)
    plot_max_generation(all_agg, out_dir)
    plot_child_survival(all_agg, out_dir)
    plot_feed_child_rate(cond_tick_data, out_dir, args.duration)
    plot_descendant_count(all_agg, out_dir)
    plot_mother_energy(cond_tick_data, out_dir, args.duration)

    print(f"\n=== Phase 5a Summary ===")
    print(f"Verdict: {verdict}")
    print()
    for a in all_agg:
        print(
            f"  {NICE_LABELS[a['condition']]:32s}  "
            f"ext={a['extinction_rate']:.2f}  "
            f"pop={a['final_pop_mean']:.1f}  "
            f"gen={a['max_gen_mean']:.1f}  "
            f"births={a['total_births_mean']:.1f}  "
            f"child={a['init_child_survival_mean']:.3f}  "
            f"feed={a['feed_rate_mean']:.3f}/tick"
        )
    print(f"\nOutputs: {out_dir}")
    return 0 if "PASS" in verdict else 1


if __name__ == "__main__":
    sys.exit(main())
