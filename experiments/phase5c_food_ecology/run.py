#!/usr/bin/env python3
"""
Phase 5c -- Extended Food Replenishment Sweep with Reproduction ON

Phase 5b showed that burst replenishment amounts [5,10,15] produce a
Malthusian boom-bust trap in all 12 tested ecologies (canonical ext >= 0.97).
Phase 5c extends the sweep to larger burst amounts [20,30,50] to find the
weakest food ecology where canonical care can sustain multi-generational
ecology through tick 3000.

Food sweep (3 x 3 = 9 ecologies):
  init_food             = [45, 60, 80]
  food_replenish_amount = [20, 30, 50]
  food_replenish_threshold_ratio = 0.5 (fixed)

Conditions per ecology:
  1. no_care:   cw=0.0, fw=0.85, sw=0.3
  2. canonical: cw=0.3, fw=0.85, sw=0.3
  3. high_care: cw=0.5, fw=0.85, sw=0.3

Usage:
    python experiments/phase5c_food_ecology/run.py --duration 3000 --seeds 30
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

# ── Constants ──────────────────────────────────────────────────────────────────

INFANT_STARVATION_MULTIPLIER = 1.5   # frozen from Phase 3
THRESHOLD_RATIO              = 0.5   # food_replenish_threshold_ratio — fixed

INIT_FOOD_VALUES  = [45, 60, 80]
REPLENISH_AMOUNTS = [20, 30, 50]

CONDITIONS = [
    {"label": "no_care",   "care_w": 0.0, "forage_w": 0.85, "self_w": 0.3},
    {"label": "canonical", "care_w": 0.3, "forage_w": 0.85, "self_w": 0.3},
    {"label": "high_care", "care_w": 0.5, "forage_w": 0.85, "self_w": 0.3},
]

COLORS_COND = {
    "no_care":   "#d62728",
    "canonical": "#1f77b4",
    "high_care": "#2ca02c",
}
NICE_LABELS_COND = {
    "no_care":   "No-Care (cw=0.0)",
    "canonical": "Canonical (cw=0.3)",
    "high_care": "High-Care (cw=0.5)",
}

# 9 distinct colors for ecology lines
_ECO_COLORS = [
    "#1f77b4", "#ff7f0e", "#2ca02c",
    "#d62728", "#9467bd", "#8c564b",
    "#e377c2", "#7f7f7f", "#bcbd22",
]


def eco_key(init_food: int, replenish: int) -> str:
    return f"F{init_food}_R{replenish}"


def eco_nice(init_food: int, replenish: int) -> str:
    return f"init_food={init_food}, replenish={replenish}"


# ── Config builder ─────────────────────────────────────────────────────────────

def make_config(cond: dict, init_food: int, replenish: int, seed: int, duration: int) -> Config:
    cfg = Config()
    cfg.seed      = seed
    cfg.max_ticks = duration
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
    cfg.init_food                      = init_food
    cfg.food_replenish_amount          = replenish
    cfg.food_replenish_threshold_ratio = THRESHOLD_RATIO
    return cfg


# ── Single run ─────────────────────────────────────────────────────────────────

def run_single(cond: dict, init_food: int, replenish: int, seed: int, duration: int) -> dict:
    cfg = make_config(cond, init_food, replenish, seed, duration)
    sim = Simulation(cfg)
    sim.initialize()

    initial_mother_ids = {m.id for m in sim.mothers}
    initial_child_ids  = {c.id for c in sim.children}
    n_initial_mothers  = len(sim.mothers)
    n_initial_children = len(sim.children)

    per_tick: list[dict] = []
    food_depletion_tick: int | None = None
    peak_pop       = 0
    peak_pop_tick  = 0
    crash_tick: int | None = None

    for t in range(duration):
        births_before = len(sim.logger.birth_records)
        care_before   = len(sim.logger.care_records)
        deaths_before = len(sim.logger.death_records)

        sim.step()
        sim.tick += 1

        n_born_tick = len(sim.logger.birth_records) - births_before
        n_feed_tick = sum(
            1 for r in sim.logger.care_records[care_before:] if r.benefit > 0
        )
        n_died_tick = len(sim.logger.death_records) - deaths_before

        alive_mothers  = sim.mothers
        alive_children = sim.children
        total_pop  = len(alive_mothers) + len(alive_children)
        food_count = len(sim.world.food_positions)

        if food_depletion_tick is None and food_count == 0:
            food_depletion_tick = t + 1

        if total_pop > peak_pop:
            peak_pop      = total_pop
            peak_pop_tick = t + 1

        if crash_tick is None and peak_pop > 0 and total_pop == 0:
            crash_tick = t + 1

        mean_energy = (
            float(np.mean([m.energy for m in alive_mothers]))
            if alive_mothers else float("nan")
        )
        mean_child_hunger = (
            float(np.mean([c.hunger for c in alive_children]))
            if alive_children else float("nan")
        )

        per_tick.append({
            "tick":              t + 1,
            "n_mothers":         len(alive_mothers),
            "n_children":        len(alive_children),
            "total_pop":         total_pop,
            "food_count":        food_count,
            "mean_energy":       mean_energy,
            "mean_child_hunger": mean_child_hunger,
            "n_feed_tick":       n_feed_tick,
            "n_born_tick":       n_born_tick,
            "n_died_tick":       n_died_tick,
        })

        # Early exit: pad remaining ticks with zeros
        if total_pop == 0 and t < duration - 1:
            zero_row: dict = {
                "n_mothers": 0, "n_children": 0, "total_pop": 0, "food_count": 0,
                "mean_energy": float("nan"), "mean_child_hunger": float("nan"),
                "n_feed_tick": 0, "n_born_tick": 0, "n_died_tick": 0,
            }
            for rt in range(t + 1, duration):
                per_tick.append({"tick": rt + 1, **zero_row})
            break

    # ── Post-run outcomes ──────────────────────────────────────────────────────
    final_pop = len(sim.mothers) + len(sim.children)
    extinct   = final_pop == 0
    max_gen   = max(sim.lineage.generations.values()) if sim.lineage.generations else 0
    total_births = len(sim.logger.birth_records)

    death_records         = sim.logger.death_records
    n_mother_deaths       = sum(1 for d in death_records if d.agent_type == "mother")
    n_child_hunger_deaths = sum(
        1 for d in death_records if d.agent_type == "child" and d.cause == "hunger"
    )
    n_child_matured_all   = sum(
        1 for d in death_records if d.agent_type == "child" and d.cause == "matured"
    )

    init_matured   = sum(
        1 for d in death_records
        if d.agent_type == "child" and d.cause == "matured" and d.agent_id in initial_child_ids
    )
    init_alive_end = sum(1 for c in sim.children if c.id in initial_child_ids)
    initial_child_survival = (
        (init_matured + init_alive_end) / n_initial_children
        if n_initial_children > 0 else 0.0
    )

    total_children_ever    = n_initial_children + total_births
    n_children_alive_end   = len(sim.children)
    overall_child_survival = (
        (n_child_matured_all + n_children_alive_end) / total_children_ever
        if total_children_ever > 0 else 0.0
    )

    init_mothers_alive_end  = sum(1 for m in sim.mothers if m.id in initial_mother_ids)
    initial_mother_survival = (
        init_mothers_alive_end / n_initial_mothers
        if n_initial_mothers > 0 else 0.0
    )

    n_feed_total = sum(1 for r in sim.logger.care_records if r.benefit > 0)
    feed_rate    = n_feed_total / duration

    lineage_descendants: dict[int, int] = {}
    for br in sim.logger.birth_records:
        lid = br.mother_lineage_id
        lineage_descendants[lid] = lineage_descendants.get(lid, 0) + 1
    max_desc = max(lineage_descendants.values()) if lineage_descendants else 0

    return {
        "init_food":               init_food,
        "replenish_amount":        replenish,
        "ecology_label":           eco_key(init_food, replenish),
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
        "overall_child_survival":  overall_child_survival,
        "initial_mother_survival": initial_mother_survival,
        "feed_rate":               feed_rate,
        "n_feed_total":            n_feed_total,
        "max_desc":                max_desc,
        "peak_pop":                peak_pop,
        "peak_pop_tick":           peak_pop_tick,
        "food_depletion_tick":     food_depletion_tick if food_depletion_tick is not None else -1,
        "crash_tick":              crash_tick if crash_tick is not None else -1,
        "per_tick":                per_tick,
    }


# ── Aggregation ────────────────────────────────────────────────────────────────

def _ms(results: list[dict], key: str) -> tuple[float, float]:
    vals = [r[key] for r in results]
    return float(np.mean(vals)), float(np.std(vals))


def aggregate(results: list[dict], init_food: int, replenish: int) -> dict:
    label = results[0]["condition"]
    n     = len(results)
    extinction_rate = sum(1 for r in results if r["extinct"]) / n
    n_gen2plus      = sum(1 for r in results if r["max_gen"] >= 2)

    fp_m,  fp_s  = _ms(results, "final_pop")
    mg_m,  mg_s  = _ms(results, "max_gen")
    tb_m,  tb_s  = _ms(results, "total_births")
    ics_m, ics_s = _ms(results, "initial_child_survival")
    ocs_m, ocs_s = _ms(results, "overall_child_survival")
    ims_m, _     = _ms(results, "initial_mother_survival")
    fr_m,  fr_s  = _ms(results, "feed_rate")
    md_m,  _     = _ms(results, "max_desc")
    pp_m,  pp_s  = _ms(results, "peak_pop")

    fdt = [r["food_depletion_tick"] for r in results if r["food_depletion_tick"] > 0]
    ct  = [r["crash_tick"]          for r in results if r["crash_tick"]          > 0]

    return {
        "init_food":              init_food,
        "replenish_amount":       replenish,
        "ecology_label":          eco_key(init_food, replenish),
        "condition":              label,
        "n_seeds":                n,
        "extinction_rate":        extinction_rate,
        "n_seeds_gen2plus":       n_gen2plus,
        "final_pop_mean":         fp_m,  "final_pop_sd":   fp_s,
        "max_gen_mean":           mg_m,  "max_gen_sd":     mg_s,
        "total_births_mean":      tb_m,  "total_births_sd": tb_s,
        "init_child_surv_mean":   ics_m, "init_child_surv_sd": ics_s,
        "overall_child_surv_mean": ocs_m, "overall_child_surv_sd": ocs_s,
        "init_mother_surv_mean":  ims_m,
        "feed_rate_mean":         fr_m,  "feed_rate_sd":   fr_s,
        "max_desc_mean":          md_m,
        "peak_pop_mean":          pp_m,  "peak_pop_sd":    pp_s,
        "mean_food_dep_tick":     float(np.mean(fdt)) if fdt else -1.0,
        "mean_crash_tick":        float(np.mean(ct))  if ct  else -1.0,
    }


def aggregate_per_tick(results: list[dict], duration: int) -> list[dict]:
    """Mean over ALL seeds including extinct (zero-padded) at each tick."""
    agg = []
    for t in range(duration):
        total_pop_v = []
        food_v      = []
        energy_v    = []
        child_h_v   = []
        feed_v      = []
        born_v      = []
        died_v      = []
        n_alive     = 0

        for r in results:
            if len(r["per_tick"]) > t:
                row = r["per_tick"][t]
                total_pop_v.append(row["total_pop"])
                food_v.append(row["food_count"])
                energy_v.append(row["mean_energy"])
                child_h_v.append(row["mean_child_hunger"])
                feed_v.append(row["n_feed_tick"])
                born_v.append(row["n_born_tick"])
                died_v.append(row["n_died_tick"])
                if row["total_pop"] > 0:
                    n_alive += 1
            else:
                total_pop_v.append(0)
                food_v.append(0)
                energy_v.append(float("nan"))
                child_h_v.append(float("nan"))
                feed_v.append(0)
                born_v.append(0)
                died_v.append(0)

        def safe_nanmean(vals: list) -> float:
            finite = [v for v in vals if not math.isnan(v)]
            return float(np.mean(finite)) if finite else float("nan")

        agg.append({
            "tick":              t + 1,
            "mean_total_pop":    float(np.mean(total_pop_v)),
            "std_total_pop":     float(np.std(total_pop_v)),
            "mean_food_count":   float(np.mean(food_v)),
            "std_food_count":    float(np.std(food_v)),
            "mean_energy":       safe_nanmean(energy_v),
            "mean_child_hunger": safe_nanmean(child_h_v),
            "mean_feed_tick":    float(np.mean(feed_v)),
            "mean_born_tick":    float(np.mean(born_v)),
            "mean_died_tick":    float(np.mean(died_v)),
            "n_seeds_alive":     n_alive,
        })
    return agg


# ── Ecology selection ──────────────────────────────────────────────────────────

def select_ecology(all_agg: list[dict]) -> dict:
    """Return weakest viable food ecology (canonical care survives, no-care still worse).

    Searches progressively relaxed thresholds. Returns canonical aggregate dict.
    """
    canonical_by_eco = {
        eco_key(a["init_food"], a["replenish_amount"]): a
        for a in all_agg if a["condition"] == "canonical"
    }
    no_care_by_eco = {
        eco_key(a["init_food"], a["replenish_amount"]): a
        for a in all_agg if a["condition"] == "no_care"
    }

    sorted_canonical = sorted(
        canonical_by_eco.values(),
        key=lambda a: (a["init_food"], a["replenish_amount"]),
    )

    criteria = [
        ("strict",   0.50, 15),
        ("moderate", 0.70, 10),
        ("relaxed",  0.90,  5),
    ]

    for _tier, ext_threshold, gen2_min in criteria:
        for a in sorted_canonical:
            if a["extinction_rate"] >= ext_threshold:
                continue
            if a["n_seeds_gen2plus"] < gen2_min:
                continue
            nc = no_care_by_eco.get(eco_key(a["init_food"], a["replenish_amount"]), {})
            if nc.get("extinction_rate", 1.0) < a["extinction_rate"]:
                continue
            return a

    return min(sorted_canonical, key=lambda a: (a["extinction_rate"], a["init_food"], a["replenish_amount"]))


# ── CSV helpers ────────────────────────────────────────────────────────────────

OUTCOME_FIELDS = [
    "init_food", "replenish_amount", "ecology_label", "condition", "seed",
    "final_pop", "final_n_mothers", "final_n_children", "extinct", "max_gen",
    "total_births", "n_mother_deaths", "n_child_hunger_deaths", "n_child_matured_all",
    "initial_child_survival", "overall_child_survival", "initial_mother_survival",
    "feed_rate", "n_feed_total", "max_desc",
    "peak_pop", "peak_pop_tick", "food_depletion_tick", "crash_tick",
]

ECOLOGY_SUMMARY_FIELDS = [
    "init_food", "replenish_amount", "ecology_label", "condition",
    "n_seeds", "extinction_rate", "n_seeds_gen2plus",
    "final_pop_mean", "final_pop_sd", "max_gen_mean", "max_gen_sd",
    "total_births_mean", "total_births_sd",
    "init_child_surv_mean", "init_child_surv_sd",
    "overall_child_surv_mean", "overall_child_surv_sd",
    "init_mother_surv_mean",
    "feed_rate_mean", "feed_rate_sd",
    "max_desc_mean", "peak_pop_mean", "peak_pop_sd",
    "mean_food_dep_tick", "mean_crash_tick",
]

PER_TICK_FIELDS = [
    "ecology_label", "init_food", "replenish_amount", "condition", "tick",
    "mean_total_pop", "std_total_pop", "mean_food_count", "std_food_count",
    "mean_energy", "mean_child_hunger",
    "mean_feed_tick", "mean_born_tick", "mean_died_tick", "n_seeds_alive",
]


def _open_csv(path: str, fields: list):
    f = open(path, "w", newline="", encoding="utf-8")
    w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
    w.writeheader()
    return w, f


# ── JSON output ────────────────────────────────────────────────────────────────

def save_config_json(duration: int, n_seeds: int, out_dir: str) -> None:
    doc = {
        "phase": "5c",
        "experiment": "extended_food_replenishment_sweep",
        "duration_ticks": duration,
        "n_seeds": n_seeds,
        "conditions": CONDITIONS,
        "food_sweep": {
            "init_food_values": INIT_FOOD_VALUES,
            "replenish_amount_values": REPLENISH_AMOUNTS,
            "food_replenish_threshold_ratio": THRESHOLD_RATIO,
            "n_ecologies": len(INIT_FOOD_VALUES) * len(REPLENISH_AMOUNTS),
        },
        "phase5b_context": {
            "phase5b_result": "all ecologies extinct (ext >= 0.97) with replenish in [5,10,15]",
            "root_cause": "boom-bust Malthusian trap; burst replenishment too small for 30-100 agent populations",
        },
        "frozen_from_phase3": {
            "infant_starvation_multiplier": INFANT_STARVATION_MULTIPLIER,
            "effective_child_hunger_rate": round(0.008 * INFANT_STARVATION_MULTIPLIER, 4),
        },
        "fixed_settings": {
            "plasticity_enabled":     False,
            "reproduction_enabled":   True,
            "mutation_enabled":       False,
            "children_enabled":       True,
            "init_mothers":           12,
            "hunger_rate":            0.008,
            "reproduction_threshold": 0.95,
            "reproduction_cost":      0.35,
            "reproduction_cooldown":  80,
            "max_population":         100,
        },
        "selection_criteria": {
            "primary": "weakest ecology where canonical extinction_rate < 0.5 and n_seeds_gen2plus >= 15",
            "constraint": "no-care extinction_rate >= canonical extinction_rate",
            "fallback": "lowest canonical extinction_rate if primary criteria unmet",
        },
    }
    with open(os.path.join(out_dir, "config.json"), "w", encoding="utf-8") as f:
        json.dump(doc, f, indent=2)


def save_summary_json(all_agg: list[dict], selected: dict, out_dir: str, duration: int) -> str:
    canonical_agg = [a for a in all_agg if a["condition"] == "canonical"]
    no_care_agg   = [a for a in all_agg if a["condition"] == "no_care"]

    n_ecologies          = len(canonical_agg)
    n_canonical_viable   = sum(1 for a in canonical_agg if a["extinction_rate"] < 0.5)
    any_canonical_viable = n_canonical_viable > 0

    sel_eco_key = eco_key(selected["init_food"], selected["replenish_amount"])

    sel_nc = next(
        (a for a in no_care_agg
         if eco_key(a["init_food"], a["replenish_amount"]) == sel_eco_key),
        {}
    )
    sel_hc_list = [
        a for a in all_agg
        if a["condition"] == "high_care"
        and eco_key(a["init_food"], a["replenish_amount"]) == sel_eco_key
    ]
    sel_hc = sel_hc_list[0] if sel_hc_list else {}

    no_care_worse = (
        sel_nc.get("extinction_rate", 1.0) >= selected.get("extinction_rate", 0.0)
    )
    feed_events_occur = selected.get("feed_rate_mean", 0.0) > 0.0
    care_improves     = (
        selected.get("init_child_surv_mean", 0.0) > sel_nc.get("init_child_surv_mean", 0.0)
    )
    multi_gen_reached = selected.get("n_seeds_gen2plus", 0) >= 15
    pop_viable        = selected.get("extinction_rate", 1.0) < 1.0

    if any_canonical_viable and no_care_worse and feed_events_occur and care_improves:
        verdict = (
            "PASS -- viable food ecology found; canonical care survives and outperforms no-care"
        )
    elif any_canonical_viable:
        verdict = (
            "PASS (partial) -- viable ecology found but no-care contrast weaker than expected"
        )
    else:
        verdict = (
            f"FAIL -- no food ecology supports canonical care persistence by tick {duration}"
        )

    doc = {
        "phase": "5c",
        "verdict": verdict,
        "n_ecologies_tested": n_ecologies,
        "n_canonical_viable": n_canonical_viable,
        "checks": {
            "any_canonical_ecology_viable":    any_canonical_viable,
            "no_care_performs_worse":          no_care_worse,
            "feed_events_occur":               feed_events_occur,
            "care_improves_child_survival":    care_improves,
            "multi_generation_reached":        multi_gen_reached,
            "population_not_instantly_extinct": pop_viable,
        },
        "selected_ecology": {
            "init_food":       selected["init_food"],
            "replenish_amount": selected["replenish_amount"],
            "ecology_label":   sel_eco_key,
            "canonical_extinction_rate":  round(selected["extinction_rate"], 4),
            "canonical_max_gen_mean":     round(selected["max_gen_mean"], 2),
            "canonical_n_seeds_gen2plus": selected["n_seeds_gen2plus"],
            "canonical_init_child_surv":  round(selected.get("init_child_surv_mean", 0.0), 4),
            "canonical_feed_rate":        round(selected.get("feed_rate_mean", 0.0), 4),
            "canonical_final_pop_mean":   round(selected.get("final_pop_mean", 0.0), 2),
            "canonical_mean_crash_tick":  round(selected.get("mean_crash_tick", -1.0), 1),
            "no_care_extinction_rate":    round(sel_nc.get("extinction_rate", 1.0), 4),
            "high_care_extinction_rate":  round(sel_hc.get("extinction_rate", 1.0), 4),
        },
        "all_canonical_ecology_summary": [
            {
                "ecology_label":    eco_key(a["init_food"], a["replenish_amount"]),
                "init_food":        a["init_food"],
                "replenish_amount": a["replenish_amount"],
                "extinction_rate":  round(a["extinction_rate"], 4),
                "max_gen_mean":     round(a["max_gen_mean"], 2),
                "n_seeds_gen2plus": a["n_seeds_gen2plus"],
                "final_pop_mean":   round(a["final_pop_mean"], 2),
                "mean_crash_tick":  round(a["mean_crash_tick"], 1) if a["mean_crash_tick"] > 0 else -1,
            }
            for a in sorted(canonical_agg, key=lambda x: (x["init_food"], x["replenish_amount"]))
        ],
    }
    with open(os.path.join(out_dir, "summary.json"), "w", encoding="utf-8") as f:
        json.dump(doc, f, indent=2)
    return verdict


# ── Heatmap helper ─────────────────────────────────────────────────────────────

def _build_heatmap_array(all_agg: list[dict], condition: str, metric: str) -> np.ndarray:
    """Returns (len(REPLENISH_AMOUNTS) x len(INIT_FOOD_VALUES)) array."""
    data = {
        (a["init_food"], a["replenish_amount"]): a[metric]
        for a in all_agg if a["condition"] == condition
    }
    arr = np.zeros((len(REPLENISH_AMOUNTS), len(INIT_FOOD_VALUES)))
    for ri, ra in enumerate(REPLENISH_AMOUNTS):
        for ci, ifv in enumerate(INIT_FOOD_VALUES):
            arr[ri, ci] = data.get((ifv, ra), float("nan"))
    return arr


def _draw_heatmap(ax, data: np.ndarray, title: str, cmap: str,
                  vmin: float | None = None, vmax: float | None = None,
                  fmt: str = ".2f") -> None:
    im = ax.imshow(data, cmap=cmap, aspect="auto", vmin=vmin, vmax=vmax)
    ax.set_xticks(range(len(INIT_FOOD_VALUES)))
    ax.set_xticklabels([str(v) for v in INIT_FOOD_VALUES])
    ax.set_yticks(range(len(REPLENISH_AMOUNTS)))
    ax.set_yticklabels([str(v) for v in REPLENISH_AMOUNTS])
    ax.set_xlabel("init_food")
    ax.set_ylabel("replenish_amount")
    ax.set_title(title, fontsize=10)
    for ri in range(len(REPLENISH_AMOUNTS)):
        for ci in range(len(INIT_FOOD_VALUES)):
            val = data[ri, ci]
            if not math.isnan(val):
                ax.text(ci, ri, format(val, fmt), ha="center", va="center", fontsize=9,
                        color="white" if (vmin is not None and val < (vmin + (vmax or 1) * 0.6)) else "black")
    plt.colorbar(im, ax=ax, fraction=0.046, pad=0.04)


# ── Plot functions ─────────────────────────────────────────────────────────────

def plot_pop_over_time_canonical(all_per_tick: dict, out_dir: str, duration: int) -> None:
    """Plot 01: canonical population over time for all 9 ecologies."""
    fig, ax = plt.subplots(figsize=(13, 6))
    eco_list = sorted(all_per_tick.keys(), key=lambda k: (
        int(k.split("_")[0][1:]), int(k.split("_")[1][1:])
    ))
    for i, ek in enumerate(eco_list):
        tick_data = all_per_tick[ek].get("canonical")
        if tick_data is None:
            continue
        ticks   = [r["tick"] for r in tick_data]
        pop_arr = np.array([r["mean_total_pop"] for r in tick_data])
        parts   = ek.split("_")
        ifv = int(parts[0][1:])
        ra  = int(parts[1][1:])
        ax.plot(ticks, pop_arr, color=_ECO_COLORS[i % len(_ECO_COLORS)],
                label=f"F={ifv} R={ra}", linewidth=1.6, alpha=0.9)
    ax.set_xlabel("Tick")
    ax.set_ylabel("Total Population (mean, 30 seeds incl. extinct=0)")
    ax.set_title(
        f"Phase 5c: Population Over Time — Canonical Care (cw=0.3)\n"
        f"All 9 food ecologies | reproduction=ON | {duration} ticks"
    )
    ax.legend(fontsize=9, ncol=3, loc="upper right")
    ax.set_xlim(0, duration)
    ax.set_ylim(bottom=0)
    plt.tight_layout()
    plt.savefig(os.path.join(out_dir, "plots", "01_pop_over_time_canonical.png"), dpi=150)
    plt.close()


def plot_extinction_heatmap(all_agg: list[dict], out_dir: str) -> None:
    """Plot 02: extinction rate heatmap (canonical)."""
    arr = _build_heatmap_array(all_agg, "canonical", "extinction_rate")
    fig, ax = plt.subplots(figsize=(7, 5))
    _draw_heatmap(ax, arr,
                  "Extinction Rate — Canonical (cw=0.3)\n(0.0 = all survive, 1.0 = all extinct)",
                  "RdYlGn_r", vmin=0.0, vmax=1.0, fmt=".2f")
    plt.tight_layout()
    plt.savefig(os.path.join(out_dir, "plots", "02_extinction_heatmap.png"), dpi=150)
    plt.close()


def plot_crash_tick_heatmap(all_agg: list[dict], out_dir: str, duration: int) -> None:
    """Plot 03: mean crash tick heatmap (canonical). -1 = no crash (survived or never grew)."""
    arr = _build_heatmap_array(all_agg, "canonical", "mean_crash_tick")
    # Replace -1 (no crash recorded) with duration for display
    arr_display = np.where(arr < 0, float(duration), arr)
    fig, ax = plt.subplots(figsize=(7, 5))
    _draw_heatmap(ax, arr_display,
                  f"Mean Crash Tick — Canonical (cw=0.3)\n"
                  f"(later crash = better; {duration} = survived or no crash)",
                  "YlOrRd_r", vmin=0.0, vmax=float(duration), fmt=".0f")
    plt.tight_layout()
    plt.savefig(os.path.join(out_dir, "plots", "03_crash_tick_heatmap.png"), dpi=150)
    plt.close()


def plot_maxgen_heatmap(all_agg: list[dict], out_dir: str) -> None:
    """Plot 04: max generation heatmap (canonical)."""
    arr = _build_heatmap_array(all_agg, "canonical", "max_gen_mean")
    fig, ax = plt.subplots(figsize=(7, 5))
    _draw_heatmap(ax, arr, "Max Generation Mean — Canonical (cw=0.3)",
                  "YlGn", vmin=0.0, vmax=float(np.nanmax(arr)) + 0.5, fmt=".1f")
    plt.tight_layout()
    plt.savefig(os.path.join(out_dir, "plots", "04_maxgen_heatmap.png"), dpi=150)
    plt.close()


def plot_food_count_over_time(all_per_tick: dict, out_dir: str, duration: int) -> None:
    """Plot 05: food count over time for all ecologies (canonical condition)."""
    fig, ax = plt.subplots(figsize=(13, 6))
    eco_list = sorted(all_per_tick.keys(), key=lambda k: (
        int(k.split("_")[0][1:]), int(k.split("_")[1][1:])
    ))
    for i, ek in enumerate(eco_list):
        tick_data = all_per_tick[ek].get("canonical")
        if tick_data is None:
            continue
        ticks    = [r["tick"] for r in tick_data]
        food_arr = np.array([r["mean_food_count"] for r in tick_data])
        parts = ek.split("_")
        ifv = int(parts[0][1:])
        ra  = int(parts[1][1:])
        ax.plot(ticks, food_arr, color=_ECO_COLORS[i % len(_ECO_COLORS)],
                label=f"F={ifv} R={ra}", linewidth=1.6, alpha=0.9)
    ax.set_xlabel("Tick")
    ax.set_ylabel("Food Count (mean across 30 seeds)")
    ax.set_title(
        f"Phase 5c: Food Count Over Time — Canonical Care\n"
        f"All 9 food ecologies | {duration} ticks"
    )
    ax.legend(fontsize=9, ncol=3, loc="upper right")
    ax.set_xlim(0, duration)
    ax.set_ylim(bottom=0)
    plt.tight_layout()
    plt.savefig(os.path.join(out_dir, "plots", "05_food_count_over_time.png"), dpi=150)
    plt.close()


def plot_condition_comparison_selected(all_per_tick: dict, all_agg: list[dict],
                                        sel_eco_key: str, out_dir: str, duration: int) -> None:
    """Plot 06: population over time for all 3 conditions under selected ecology."""
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))

    ax = axes[0]
    for cond_label in ["no_care", "canonical", "high_care"]:
        tick_data = all_per_tick.get(sel_eco_key, {}).get(cond_label)
        if tick_data is None:
            continue
        ticks   = [r["tick"] for r in tick_data]
        pop_arr = np.array([r["mean_total_pop"] for r in tick_data])
        std_arr = np.array([r["std_total_pop"]  for r in tick_data])
        c = COLORS_COND[cond_label]
        ax.plot(ticks, pop_arr, color=c, label=NICE_LABELS_COND[cond_label], linewidth=1.8)
        ax.fill_between(ticks,
                        np.maximum(0, pop_arr - std_arr),
                        pop_arr + std_arr,
                        color=c, alpha=0.12)
    ax.set_xlabel("Tick")
    ax.set_ylabel("Total Population (mean +/- SD)")
    ax.set_title("Population Over Time")
    ax.legend(fontsize=9)
    ax.set_xlim(0, duration)
    ax.set_ylim(bottom=0)

    ax2 = axes[1]
    parts  = sel_eco_key.split("_")
    ifv_i  = int(parts[0][1:])
    ra_i   = int(parts[1][1:])
    sel_agg = [a for a in all_agg
               if a["init_food"] == ifv_i and a["replenish_amount"] == ra_i]
    cond_order = ["no_care", "canonical", "high_care"]
    ext_vals = []
    mg_vals  = []
    cs_vals  = []
    for c in cond_order:
        a = next((x for x in sel_agg if x["condition"] == c), {})
        ext_vals.append(a.get("extinction_rate", 1.0))
        mg_vals.append(a.get("max_gen_mean", 0.0))
        cs_vals.append(a.get("init_child_surv_mean", 0.0))

    x = np.arange(3)
    width = 0.25
    max_gen_scale = max(mg_vals) if max(mg_vals) > 0 else 1.0
    ax2.bar(x - width, ext_vals, width, label="Extinction Rate",
            color=[COLORS_COND[c] for c in cond_order], alpha=0.5)
    ax2.bar(x,          [v / max_gen_scale for v in mg_vals], width,
            label=f"Max Gen / {max_gen_scale:.0f} (scaled)",
            color=[COLORS_COND[c] for c in cond_order], alpha=0.75)
    ax2.bar(x + width,  cs_vals, width, label="Init Child Surv.",
            color=[COLORS_COND[c] for c in cond_order], edgecolor="black", linewidth=0.6)
    ax2.set_xticks(x)
    ax2.set_xticklabels([NICE_LABELS_COND[c] for c in cond_order], rotation=12, fontsize=8)
    ax2.set_ylabel("Value (extinction & survival in [0,1])")
    ax2.set_title("Key Metrics Comparison")
    ax2.legend(fontsize=8)
    ax2.set_ylim(0, 1.1)

    fig.suptitle(
        f"Phase 5c: Selected Ecology — init_food={ifv_i}, replenish={ra_i}\n"
        f"No-Care vs Canonical vs High-Care",
        fontsize=11,
    )
    plt.tight_layout()
    plt.savefig(os.path.join(out_dir, "plots", "06_condition_comparison_selected.png"), dpi=150)
    plt.close()


def plot_child_survival_by_condition(all_agg: list[dict], sel_init_food: int,
                                      sel_replenish: int, out_dir: str) -> None:
    """Plot 07: child survival by condition under selected ecology."""
    sel_key = eco_key(sel_init_food, sel_replenish)
    sel_agg = [a for a in all_agg
               if eco_key(a["init_food"], a["replenish_amount"]) == sel_key]
    if not sel_agg:
        return

    cond_order   = ["no_care", "canonical", "high_care"]
    init_surv    = []
    overall_surv = []
    colors       = []
    x_labels     = []

    for c in cond_order:
        a = next((x for x in sel_agg if x["condition"] == c), None)
        if a is None:
            continue
        init_surv.append(a.get("init_child_surv_mean", 0.0))
        overall_surv.append(a.get("overall_child_surv_mean", 0.0))
        colors.append(COLORS_COND[c])
        x_labels.append(NICE_LABELS_COND[c])

    x = np.arange(len(x_labels))
    width = 0.35
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.bar(x - width / 2, init_surv,    width, label="Init Child Survival",
           color=[c + "cc" for c in colors], edgecolor="black", linewidth=0.6)
    ax.bar(x + width / 2, overall_surv, width, label="Overall Child Survival",
           color=colors, edgecolor="black", linewidth=0.6, alpha=0.75)
    ax.axhline(0.8, color="black", linestyle="--", linewidth=1.2, label="80% threshold")
    ax.set_xticks(x)
    ax.set_xticklabels(x_labels, rotation=10)
    ax.set_ylabel("Child Survival Rate (mean, 30 seeds)")
    ax.set_title(
        f"Phase 5c: Child Survival by Condition\n"
        f"Selected ecology: init_food={sel_init_food}, replenish={sel_replenish}"
    )
    ax.legend(fontsize=9)
    ax.set_ylim(0, 1.1)
    plt.tight_layout()
    plt.savefig(os.path.join(out_dir, "plots", "07_child_survival_by_condition.png"), dpi=150)
    plt.close()


def plot_births_deaths_over_time(all_per_tick: dict, sel_eco_key: str,
                                  out_dir: str, duration: int) -> None:
    """Plot 08: births and deaths per tick for all 3 conditions under selected ecology."""
    fig, axes = plt.subplots(1, 2, figsize=(14, 5), sharey=False)
    for ax, metric, label_str in zip(axes, ["mean_born_tick", "mean_died_tick"],
                                     ["Mean Births/Tick", "Mean Deaths/Tick"]):
        for cond_label in ["no_care", "canonical", "high_care"]:
            tick_data = all_per_tick.get(sel_eco_key, {}).get(cond_label)
            if tick_data is None:
                continue
            ticks  = [r["tick"] for r in tick_data]
            values = np.array([r[metric] for r in tick_data])
            ax.plot(ticks, values, color=COLORS_COND[cond_label],
                    label=NICE_LABELS_COND[cond_label], linewidth=1.6)
        ax.set_xlabel("Tick")
        ax.set_ylabel(label_str)
        ax.set_xlim(0, duration)
        ax.set_ylim(bottom=0)
        ax.legend(fontsize=9)

    parts = sel_eco_key.split("_")
    ifv = parts[0][1:]; ra = parts[1][1:]
    fig.suptitle(
        f"Phase 5c: Births & Deaths Over Time — Selected Ecology "
        f"(init_food={ifv}, replenish={ra})",
        fontsize=11,
    )
    plt.tight_layout()
    plt.savefig(os.path.join(out_dir, "plots", "08_births_deaths_over_time.png"), dpi=150)
    plt.close()


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(description="Phase 5c -- Extended Food Replenishment Sweep")
    parser.add_argument("--duration", type=int, default=3000)
    parser.add_argument("--seeds",    type=int, default=30)
    args = parser.parse_args()

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir   = os.path.join(PROJECT_ROOT, "outputs", "phase5c_food_ecology", timestamp)
    os.makedirs(os.path.join(out_dir, "data"),  exist_ok=True)
    os.makedirs(os.path.join(out_dir, "plots"), exist_ok=True)

    n_ecologies = len(INIT_FOOD_VALUES) * len(REPLENISH_AMOUNTS)
    total_runs  = n_ecologies * len(CONDITIONS) * args.seeds

    print(f"\n=== Phase 5c -- Extended Food Replenishment Sweep ===")
    print(f"Duration: {args.duration} ticks  |  Seeds: {args.seeds}")
    print(f"Food ecologies: {n_ecologies}  (init_food x replenish_amount grid)")
    print(f"Conditions: {len(CONDITIONS)}  (no_care / canonical / high_care)")
    print(f"Total runs: {total_runs}")
    print(f"infant_starvation_multiplier: {INFANT_STARVATION_MULTIPLIER}  "
          f"(child hunger {0.008 * INFANT_STARVATION_MULTIPLIER:.4f}/tick)")
    print(f"Reproduction: ON  |  Mutation: OFF  |  Plasticity: OFF")
    print(f"Output: {out_dir}\n")

    save_config_json(args.duration, args.seeds, out_dir)

    outcomes_w, outcomes_f = _open_csv(
        os.path.join(out_dir, "data", "outcomes_all.csv"), OUTCOME_FIELDS
    )
    summary_w, summary_f = _open_csv(
        os.path.join(out_dir, "data", "ecology_summary.csv"), ECOLOGY_SUMMARY_FIELDS
    )
    ptick_w, ptick_f = _open_csv(
        os.path.join(out_dir, "data", "per_tick_canonical.csv"), PER_TICK_FIELDS
    )

    all_agg: list[dict] = []
    all_per_tick: dict[str, dict[str, list[dict]]] = {}

    ecology_idx = 0
    for init_food in INIT_FOOD_VALUES:
        for replenish in REPLENISH_AMOUNTS:
            ecology_idx += 1
            ek = eco_key(init_food, replenish)
            all_per_tick[ek] = {}
            print(f"\n--- Ecology {ecology_idx}/{n_ecologies}: {eco_nice(init_food, replenish)} ---")

            for cond in CONDITIONS:
                cond_label = cond["label"]
                results: list[dict] = []

                for s in range(args.seeds):
                    seed = s + 1
                    r = run_single(cond, init_food, replenish, seed, args.duration)

                    outcomes_w.writerow({k: r[k] for k in OUTCOME_FIELDS})
                    outcomes_f.flush()

                    results.append(r)

                    if (s + 1) % 5 == 0 or s + 1 == args.seeds:
                        ext_so_far = sum(1 for rr in results if rr["extinct"])
                        mg_so_far  = float(np.mean([rr["max_gen"] for rr in results]))
                        cs_so_far  = float(np.mean([rr["initial_child_survival"] for rr in results]))
                        fp_so_far  = float(np.mean([rr["final_pop"] for rr in results]))
                        print(
                            f"  [{cond_label:9s}] Seeds {s+1:2d}/{args.seeds}  "
                            f"ext={ext_so_far}  gen={mg_so_far:.1f}  "
                            f"child_surv={cs_so_far:.3f}  pop={fp_so_far:.1f}"
                        )

                agg = aggregate(results, init_food, replenish)
                all_agg.append(agg)

                summary_w.writerow({k: agg[k] for k in ECOLOGY_SUMMARY_FIELDS})
                summary_f.flush()

                tick_agg = aggregate_per_tick(results, args.duration)
                all_per_tick[ek][cond_label] = tick_agg

                if cond_label == "canonical":
                    for row in tick_agg:
                        ptick_w.writerow({
                            "ecology_label":    ek,
                            "init_food":        init_food,
                            "replenish_amount": replenish,
                            "condition":        cond_label,
                            **row,
                        })
                    ptick_f.flush()

                for r in results:
                    del r["per_tick"]

                print(
                    f"  [{cond_label:9s}] DONE: "
                    f"ext={agg['extinction_rate']:.2f}  "
                    f"gen={agg['max_gen_mean']:.1f}  "
                    f"pop={agg['final_pop_mean']:.1f}  "
                    f"births={agg['total_births_mean']:.1f}  "
                    f"feed={agg['feed_rate_mean']:.3f}/tick  "
                    f"crash_tick={agg['mean_crash_tick']:.0f}"
                )

    outcomes_f.close()
    summary_f.close()
    ptick_f.close()

    selected = select_ecology(all_agg)
    sel_key  = eco_key(selected["init_food"], selected["replenish_amount"])

    verdict = save_summary_json(all_agg, selected, out_dir, args.duration)

    print("\nGenerating plots...")
    plot_pop_over_time_canonical(all_per_tick, out_dir, args.duration)
    plot_extinction_heatmap(all_agg, out_dir)
    plot_crash_tick_heatmap(all_agg, out_dir, args.duration)
    plot_maxgen_heatmap(all_agg, out_dir)
    plot_food_count_over_time(all_per_tick, out_dir, args.duration)
    plot_condition_comparison_selected(all_per_tick, all_agg, sel_key, out_dir, args.duration)
    plot_child_survival_by_condition(all_agg, selected["init_food"], selected["replenish_amount"], out_dir)
    plot_births_deaths_over_time(all_per_tick, sel_key, out_dir, args.duration)

    print(f"\n=== Phase 5c Summary ===")
    print(f"Verdict: {verdict}")
    print(f"\nSelected ecology: {eco_nice(selected['init_food'], selected['replenish_amount'])}")
    print(f"  canonical extinction_rate = {selected['extinction_rate']:.2f}")
    print(f"  canonical max_gen_mean    = {selected['max_gen_mean']:.1f}")
    print(f"  canonical n_seeds_gen2+   = {selected['n_seeds_gen2plus']}/30")
    print(f"  canonical final_pop_mean  = {selected['final_pop_mean']:.1f}")
    print(f"  canonical mean_crash_tick = {selected['mean_crash_tick']:.0f}")
    print(f"  canonical feed_rate       = {selected.get('feed_rate_mean', 0.0):.3f}/tick")

    print(f"\nCanonical ecology summary (all 9):")
    canonical_rows = sorted(
        [a for a in all_agg if a["condition"] == "canonical"],
        key=lambda a: (a["init_food"], a["replenish_amount"]),
    )
    print(f"  {'Ecology':22s}  ext_rate  max_gen  gen2+  final_pop  crash_tick")
    for a in canonical_rows:
        marker = " <-- SELECTED" if eco_key(a["init_food"], a["replenish_amount"]) == sel_key else ""
        ct_str = f"{a['mean_crash_tick']:.0f}" if a["mean_crash_tick"] > 0 else "  N/A"
        print(
            f"  {eco_nice(a['init_food'], a['replenish_amount']):22s}  "
            f"{a['extinction_rate']:.2f}     {a['max_gen_mean']:5.1f}  "
            f"{a['n_seeds_gen2plus']:3d}/30  "
            f"{a['final_pop_mean']:7.1f}  "
            f"{ct_str}{marker}"
        )

    print(f"\nOutputs: {out_dir}")
    return 0 if "PASS" in verdict else 1


if __name__ == "__main__":
    sys.exit(main())
