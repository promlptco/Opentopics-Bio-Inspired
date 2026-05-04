#!/usr/bin/env python3
"""
Phase 5f -- Reproduction Cost Calibration

Same fixed ecology as Phase 5e (cfr_0.10):
  init_food=45, food_replenish_amount=20, threshold_ratio=0.5
  continuous_food_rate=0.1, continuous_food_max=200
  infant_starvation_multiplier=1.5

Sweep: reproduction_cost = [0.35, 0.25, 0.20, 0.15, 0.10]
3 conditions x 30 seeds = 90 runs per rc = 450 total.

Selection: highest reproduction_cost where canonical extinction_rate < 0.5,
multi-generation, no-care clearly worse, and population is not unbounded.

Usage:
    python experiments/phase5f_repro_cost/run.py --duration 3000 --seeds 30
"""

from __future__ import annotations

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

# ── Fixed ecology (same as Phase 5e) ──────────────────────────────────────────
INFANT_STARVATION_MULTIPLIER = 1.5
INIT_FOOD                    = 45
REPLENISH_AMOUNT             = 20
THRESHOLD_RATIO              = 0.5
CONTINUOUS_FOOD_RATE         = 0.1
CONTINUOUS_FOOD_MAX          = 200
GRID_CELLS                   = 900   # 30 x 30

REPRO_COSTS = [0.35, 0.25, 0.20, 0.15, 0.10]

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
RC_COLORS = {
    0.35: "#d62728",
    0.25: "#ff7f0e",
    0.20: "#2ca02c",
    0.15: "#1f77b4",
    0.10: "#9467bd",
}


# ── Config ─────────────────────────────────────────────────────────────────────

def make_config(cond: dict, seed: int, duration: int, repro_cost: float) -> Config:
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
    cfg.reproduction_cost              = repro_cost
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
    out = []
    for i in range(len(arr)):
        lo = max(0, i - w // 2)
        hi = min(len(arr), i + w // 2 + 1)
        chunk = [v for v in arr[lo:hi] if not math.isnan(v)]
        out.append(float(np.mean(chunk)) if chunk else float("nan"))
    return out


# ── Single run ─────────────────────────────────────────────────────────────────

def run_single(cond: dict, seed: int, duration: int, repro_cost: float) -> dict:
    cfg = make_config(cond, seed, duration, repro_cost)
    sim = Simulation(cfg)
    sim.initialize()

    initial_child_ids  = {c.id for c in sim.children}
    n_initial_children = len(sim.children)

    per_tick: list[dict] = []

    peak_pop        = 0
    peak_pop_tick   = 0
    crash_tick      = None
    food_depl_tick  = None
    birth_peak_val  = 0
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
        n_died_child_hunger  = sum(1 for d in new_deaths
                                   if d.agent_type == "child" and d.cause == "hunger")
        n_died_child_matured = sum(1 for d in new_deaths
                                   if d.agent_type == "child" and d.cause == "matured")

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
            birth_peak_val = n_born_tick
        if n_died_tick > death_peak_val:
            death_peak_val = n_died_tick

        energies = [m.energy for m in alive_m]
        hungers  = [c.hunger for c in alive_c]

        row: dict = {
            "tick":                 t + 1,
            "n_mothers":            n_m,
            "n_children":           n_c,
            "total_pop":            total,
            "food_count":           food if total > 0 else float("nan"),
            "occupied_density":     total / GRID_CELLS,
            "eng_mean":             _nanmean(energies),
            "eng_p25":              _nanpct(energies, 25),
            "eng_med":              _nanpct(energies, 50),
            "eng_p75":              _nanpct(energies, 75),
            "mean_child_hunger":    _nanmean(hungers),
            "n_feed_tick":          n_feed_tick,
            "n_born_tick":          n_born_tick,
            "n_died_tick":          n_died_tick,
            "n_died_mother":        n_died_mother,
            "n_died_child_hunger":  n_died_child_hunger,
            "n_died_child_matured": n_died_child_matured,
            "food_unavail":         int(food == 0),
        }
        per_tick.append(row)

        if total == 0 and t < duration - 1:
            zero: dict = {
                "n_mothers": 0, "n_children": 0, "total_pop": 0,
                "food_count": float("nan"), "occupied_density": 0.0,
                "eng_mean": float("nan"), "eng_p25": float("nan"),
                "eng_med": float("nan"), "eng_p75": float("nan"),
                "mean_child_hunger": float("nan"),
                "n_feed_tick": 0, "n_born_tick": 0, "n_died_tick": 0,
                "n_died_mother": 0, "n_died_child_hunger": 0,
                "n_died_child_matured": 0, "food_unavail": 0,
            }
            for rt in range(t + 1, duration):
                per_tick.append({"tick": rt + 1, **zero})
            break

    final_pop = len(sim.mothers) + len(sim.children)
    extinct   = final_pop == 0
    max_gen   = max(sim.lineage.generations.values()) if sim.lineage.generations else 0

    dr = sim.logger.death_records
    n_mother_deaths       = sum(1 for d in dr if d.agent_type == "mother")
    n_child_hunger_deaths = sum(1 for d in dr
                                if d.agent_type == "child" and d.cause == "hunger")

    init_matured   = sum(1 for d in dr if d.agent_type == "child" and d.cause == "matured"
                         and d.agent_id in initial_child_ids)
    init_alive_end = sum(1 for c in sim.children if c.id in initial_child_ids)
    init_cs = (init_matured + init_alive_end) / n_initial_children if n_initial_children > 0 else 0.0

    total_births = len(sim.logger.birth_records)
    n_feed_total = sum(1 for r in sim.logger.care_records if r.benefit > 0)
    feed_rate    = n_feed_total / duration

    assert len(per_tick) == duration, (
        f"per_tick {len(per_tick)} != {duration} "
        f"(seed={seed}, cond={cond['label']}, rc={repro_cost})"
    )
    assert per_tick[-1]["tick"] == duration

    return {
        "condition":             cond["label"],
        "repro_cost":            repro_cost,
        "seed":                  seed,
        "final_pop":             final_pop,
        "extinct":               extinct,
        "max_gen":               max_gen,
        "total_births":          total_births,
        "n_mother_deaths":       n_mother_deaths,
        "n_child_hunger_deaths": n_child_hunger_deaths,
        "init_child_survival":   init_cs,
        "feed_rate":             feed_rate,
        "peak_pop":              peak_pop,
        "peak_pop_tick":         peak_pop_tick,
        "food_depl_tick":        food_depl_tick if food_depl_tick is not None else -1,
        "crash_tick":            crash_tick if crash_tick is not None else -1,
        "per_tick":              per_tick,
    }


# ── Aggregation ────────────────────────────────────────────────────────────────

def agg_outcomes(results: list[dict]) -> dict:
    def ms(k: str) -> tuple[float, float]:
        v = [r[k] for r in results]
        return float(np.mean(v)), float(np.std(v))

    n   = len(results)
    ext = sum(1 for r in results if r["extinct"]) / n
    pp_m, pp_s = ms("peak_pop")
    mg_m, mg_s = ms("max_gen")
    tb_m, _    = ms("total_births")
    fr_m, _    = ms("feed_rate")
    cs_m, _    = ms("init_child_survival")
    fp_m, _    = ms("final_pop")

    def tick_mean(key: str) -> float:
        vals = [r[key] for r in results if r[key] > 0]
        return float(np.mean(vals)) if vals else -1.0

    return {
        "condition":            results[0]["condition"],
        "repro_cost":           results[0]["repro_cost"],
        "n_seeds":              n,
        "extinction_rate":      ext,
        "peak_pop_mean":        pp_m,  "peak_pop_sd":    pp_s,
        "max_gen_mean":         mg_m,  "max_gen_sd":     mg_s,
        "total_births_mean":    tb_m,
        "feed_rate_mean":       fr_m,
        "init_child_surv_mean": cs_m,
        "final_pop_mean":       fp_m,
        "crash_tick_mean":      tick_mean("crash_tick"),
        "food_depl_tick_mean":  tick_mean("food_depl_tick"),
    }


def agg_per_tick(results: list[dict], duration: int) -> list[dict]:
    keys = [
        "n_mothers", "n_children", "total_pop", "food_count",
        "occupied_density", "eng_mean", "eng_p25", "eng_med", "eng_p75",
        "mean_child_hunger",
        "n_feed_tick", "n_born_tick", "n_died_tick",
        "n_died_mother", "n_died_child_hunger", "n_died_child_matured",
        "food_unavail",
    ]
    out = []
    for t in range(duration):
        bucket: dict[str, list] = {k: [] for k in keys}
        for r in results:
            row = r["per_tick"][t]
            for k in keys:
                bucket[k].append(row[k])
        agg_row: dict = {"tick": t + 1}
        for k in keys:
            agg_row[f"mean_{k}"] = _nanmean(bucket[k])
            agg_row[f"std_{k}"]  = _nanstd(bucket[k])
        out.append(agg_row)
    return out


# ── Plotting ───────────────────────────────────────────────────────────────────

def plot_extinction_vs_rc(outcomes: dict, out_dir: str) -> None:
    fig, ax = plt.subplots(figsize=(8, 5))
    for cond_label, color in COLORS.items():
        y = [outcomes[rc][cond_label]["extinction_rate"] for rc in REPRO_COSTS]
        ax.plot(REPRO_COSTS, y, "o-", color=color, lw=2, markersize=7,
                label=NICE[cond_label])
    ax.axhline(0.5, color="gray", lw=1.2, linestyle="--", label="Target threshold (ext<0.5)")
    ax.set_xlabel("Reproduction cost")
    ax.set_ylabel("Extinction rate by tick 3000")
    ax.set_title("Phase 5f -- Extinction Rate vs Reproduction Cost")
    ax.set_ylim(-0.05, 1.05)
    ax.invert_xaxis()
    ax.legend(fontsize=9)
    ax.grid(alpha=0.3)
    plt.tight_layout()
    plt.savefig(os.path.join(out_dir, "01_extinction_vs_rc.png"), dpi=120)
    plt.close(fig)


def plot_pop_over_time_canonical(agg_by_rc_cond: dict, out_dir: str) -> None:
    fig, ax = plt.subplots(figsize=(10, 5))
    for rc in REPRO_COSTS:
        agg = agg_by_rc_cond[rc]["canonical"]
        tks = [r["tick"] for r in agg]
        pop = [r["mean_total_pop"] for r in agg]
        ax.plot(tks, pop, color=RC_COLORS[rc], lw=1.5, label=f"rc={rc}")
    ax.set_xlabel("Tick")
    ax.set_ylabel("Mean total population")
    ax.set_title("Phase 5f -- Canonical Population Over Time by Reproduction Cost")
    ax.legend(fontsize=9)
    ax.grid(alpha=0.3)
    plt.tight_layout()
    plt.savefig(os.path.join(out_dir, "02_pop_over_time_canonical.png"), dpi=120)
    plt.close(fig)


def plot_final_pop_vs_rc(outcomes: dict, out_dir: str) -> None:
    fig, ax = plt.subplots(figsize=(8, 5))
    x = np.arange(len(REPRO_COSTS))
    w = 0.25
    offsets = {"no_care": -w, "canonical": 0.0, "high_care": w}
    for cond_label, color in COLORS.items():
        y = [outcomes[rc][cond_label]["final_pop_mean"] for rc in REPRO_COSTS]
        ax.bar(x + offsets[cond_label], y, width=w * 0.85,
               color=color, alpha=0.8, label=NICE[cond_label])
    ax.set_xticks(x)
    ax.set_xticklabels([str(rc) for rc in REPRO_COSTS])
    ax.set_xlabel("Reproduction cost")
    ax.set_ylabel("Mean final population at tick 3000")
    ax.set_title("Phase 5f -- Final Population vs Reproduction Cost")
    ax.legend(fontsize=9)
    ax.grid(axis="y", alpha=0.3)
    plt.tight_layout()
    plt.savefig(os.path.join(out_dir, "03_final_pop_vs_rc.png"), dpi=120)
    plt.close(fig)


def plot_max_gen_vs_rc(outcomes: dict, out_dir: str) -> None:
    fig, ax = plt.subplots(figsize=(8, 5))
    for cond_label, color in COLORS.items():
        y = [outcomes[rc][cond_label]["max_gen_mean"] for rc in REPRO_COSTS]
        ax.plot(REPRO_COSTS, y, "o-", color=color, lw=2, markersize=7,
                label=NICE[cond_label])
    ax.set_xlabel("Reproduction cost")
    ax.set_ylabel("Mean max generation")
    ax.set_title("Phase 5f -- Max Generation vs Reproduction Cost")
    ax.invert_xaxis()
    ax.legend(fontsize=9)
    ax.grid(alpha=0.3)
    plt.tight_layout()
    plt.savefig(os.path.join(out_dir, "04_max_gen_vs_rc.png"), dpi=120)
    plt.close(fig)


def plot_child_survival_selected(outcomes: dict, selected_rc: float, out_dir: str) -> None:
    fig, ax = plt.subplots(figsize=(7, 5))
    cond_labels = ["no_care", "canonical", "high_care"]
    x = np.arange(len(cond_labels))
    y = [outcomes[selected_rc][cl]["init_child_surv_mean"] for cl in cond_labels]
    colors_list = [COLORS[cl] for cl in cond_labels]
    ax.bar(x, y, color=colors_list, alpha=0.8)
    ax.set_xticks(x)
    ax.set_xticklabels([NICE[cl] for cl in cond_labels], fontsize=9)
    ax.set_ylabel("Initial child survival rate")
    ax.set_ylim(0, 1.05)
    ax.axhline(0.8, color="gray", lw=1.2, linestyle="--", label="80% threshold")
    ax.set_title(f"Phase 5f -- Child Survival by Condition (selected rc={selected_rc})")
    ax.legend(fontsize=9)
    ax.grid(axis="y", alpha=0.3)
    plt.tight_layout()
    plt.savefig(os.path.join(out_dir, "05_child_survival_selected.png"), dpi=120)
    plt.close(fig)


def plot_food_over_time_selected(agg_by_rc_cond: dict, selected_rc: float,
                                  out_dir: str) -> None:
    fig, ax = plt.subplots(figsize=(10, 5))
    for cond_label, color in COLORS.items():
        agg  = agg_by_rc_cond[selected_rc][cond_label]
        tks  = [r["tick"] for r in agg]
        food = [r["mean_food_count"] for r in agg]
        ax.plot(tks, food, color=color, lw=1.5, label=NICE[cond_label])
    ax.axhline(CONTINUOUS_FOOD_MAX, color="gray", lw=0.8, linestyle=":",
               label=f"food_max ({CONTINUOUS_FOOD_MAX})")
    ax.set_xlabel("Tick")
    ax.set_ylabel("Mean food count")
    ax.set_title(f"Phase 5f -- Food Count Over Time (selected rc={selected_rc})")
    ax.legend(fontsize=9)
    ax.grid(alpha=0.3)
    plt.tight_layout()
    plt.savefig(os.path.join(out_dir, "06_food_over_time_selected.png"), dpi=120)
    plt.close(fig)


def plot_energy_over_time_selected(agg_by_rc_cond: dict, selected_rc: float,
                                    out_dir: str) -> None:
    fig, ax = plt.subplots(figsize=(10, 5))
    for cond_label, color in COLORS.items():
        agg = agg_by_rc_cond[selected_rc][cond_label]
        tks = np.array([r["tick"] for r in agg])
        med = np.array([r["mean_eng_med"] for r in agg])
        p25 = np.array([r["mean_eng_p25"] for r in agg])
        p75 = np.array([r["mean_eng_p75"] for r in agg])
        mask = ~np.isnan(med)
        ax.fill_between(tks[mask], p25[mask], p75[mask],
                        alpha=0.15, color=color)
        ax.plot(tks[mask], med[mask], color=color, lw=1.5, label=NICE[cond_label])
    ax.axhline(0, color="gray", lw=0.5, linestyle=":")
    ax.set_xlabel("Tick")
    ax.set_ylabel("Mother energy (median + p25-p75 band)")
    ax.set_ylim(-0.05, 1.05)
    ax.set_title(f"Phase 5f -- Mother Energy Over Time (selected rc={selected_rc})")
    ax.legend(fontsize=9)
    ax.grid(alpha=0.3)
    plt.tight_layout()
    plt.savefig(os.path.join(out_dir, "07_energy_over_time_selected.png"), dpi=120)
    plt.close(fig)


def plot_births_deaths_selected(agg_by_rc_cond: dict, selected_rc: float,
                                 out_dir: str) -> None:
    fig, axes = plt.subplots(2, 1, figsize=(10, 8), sharex=True)
    W = 20
    for cond_label, color in COLORS.items():
        agg    = agg_by_rc_cond[selected_rc][cond_label]
        tks    = [r["tick"] for r in agg]
        births = _smooth([r["mean_n_born_tick"] for r in agg], W)
        deaths = _smooth([r["mean_n_died_tick"] for r in agg], W)
        axes[0].plot(tks, births, color=color, lw=1.5, label=NICE[cond_label])
        axes[1].plot(tks, deaths, color=color, lw=1.5, label=NICE[cond_label])
    axes[0].set_ylabel("Births / tick (smoothed)")
    axes[1].set_ylabel("Deaths / tick (smoothed)")
    axes[1].set_xlabel("Tick")
    axes[0].set_title(f"Phase 5f -- Births and Deaths Over Time (selected rc={selected_rc})")
    axes[0].legend(fontsize=9)
    axes[0].grid(alpha=0.3)
    axes[1].grid(alpha=0.3)
    plt.tight_layout()
    plt.savefig(os.path.join(out_dir, "08_births_deaths_selected.png"), dpi=120)
    plt.close(fig)


# ── CSV field names ────────────────────────────────────────────────────────────

OUTCOME_FIELDS = [
    "condition", "repro_cost", "seed",
    "final_pop", "extinct", "max_gen",
    "total_births", "n_mother_deaths", "n_child_hunger_deaths",
    "init_child_survival", "feed_rate",
    "peak_pop", "peak_pop_tick", "food_depl_tick", "crash_tick",
]

PER_TICK_FIELDS = [
    "repro_cost", "condition", "tick",
    "mean_n_mothers", "std_n_mothers",
    "mean_n_children", "std_n_children",
    "mean_total_pop", "std_total_pop",
    "mean_food_count", "std_food_count",
    "mean_occupied_density",
    "mean_eng_mean", "mean_eng_p25", "mean_eng_med", "mean_eng_p75",
    "mean_mean_child_hunger",
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

    ts       = datetime.now().strftime("%Y%m%d_%H%M%S")
    outdir   = os.path.join(PROJECT_ROOT, "outputs", "phase5f_repro_cost", ts)
    data_dir = os.path.join(outdir, "data")
    plot_dir = os.path.join(outdir, "plots")
    os.makedirs(data_dir, exist_ok=True)
    os.makedirs(plot_dir, exist_ok=True)

    total_runs = len(REPRO_COSTS) * len(CONDITIONS) * args.seeds
    print(
        f"Phase 5f: {total_runs} runs "
        f"({len(REPRO_COSTS)} rc x {len(CONDITIONS)} conds x {args.seeds} seeds)"
    )

    # results_by_rc_cond[rc][cond_label] = [run_result, ...]
    results_by_rc_cond: dict = {
        rc: {c["label"]: [] for c in CONDITIONS} for rc in REPRO_COSTS
    }
    run_idx = 0

    # Open outcomes CSV early so we stream writes
    outcome_path = os.path.join(data_dir, "outcomes_all.csv")
    out_f = open(outcome_path, "w", newline="", encoding="utf-8")
    out_w = csv.DictWriter(out_f, fieldnames=OUTCOME_FIELDS, extrasaction="ignore")
    out_w.writeheader()

    for rc in REPRO_COSTS:
        for cond in CONDITIONS:
            for seed in range(args.seeds):
                run_idx += 1
                print(
                    f"  [{run_idx}/{total_runs}] rc={rc} {cond['label']} seed={seed}",
                    end="\r", flush=True,
                )
                r = run_single(cond, seed, args.duration, rc)
                results_by_rc_cond[rc][cond["label"]].append(r)
                out_w.writerow(r)

    out_f.close()
    print()

    # ── Aggregate outcomes ────────────────────────────────────────────────────
    outcomes: dict = {}
    for rc in REPRO_COSTS:
        outcomes[rc] = {}
        for cond in CONDITIONS:
            outcomes[rc][cond["label"]] = agg_outcomes(
                results_by_rc_cond[rc][cond["label"]]
            )

    # ── Aggregate per-tick ────────────────────────────────────────────────────
    agg_by_rc_cond: dict = {}
    for rc in REPRO_COSTS:
        agg_by_rc_cond[rc] = {}
        for cond in CONDITIONS:
            cl = cond["label"]
            agg_by_rc_cond[rc][cl] = agg_per_tick(
                results_by_rc_cond[rc][cl], args.duration
            )

    # ── Write per_tick aggregated CSV ─────────────────────────────────────────
    pt_path = os.path.join(data_dir, "per_tick_agg.csv")
    with open(pt_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=PER_TICK_FIELDS, extrasaction="ignore")
        w.writeheader()
        for rc in REPRO_COSTS:
            for cond in CONDITIONS:
                cl = cond["label"]
                for row in agg_by_rc_cond[rc][cl]:
                    w.writerow({"repro_cost": rc, "condition": cl, **row})

    # ── Sanity checks ─────────────────────────────────────────────────────────
    for rc in REPRO_COSTS:
        for cond in CONDITIONS:
            cl  = cond["label"]
            agg = agg_by_rc_cond[rc][cl]
            assert len(agg) == args.duration, (
                f"[rc={rc} {cl}] agg length {len(agg)} != {args.duration}"
            )
            assert agg[-1]["tick"] == args.duration, (
                f"[rc={rc} {cl}] last tick {agg[-1]['tick']} != {args.duration}"
            )
    print("Sanity checks passed.")

    # ── Selection ─────────────────────────────────────────────────────────────
    # Select highest rc where all criteria are met (weakest sufficient fix).
    selected_rc   = None
    selection_log: list[str] = []

    for rc in sorted(REPRO_COSTS, reverse=True):  # highest first
        can = outcomes[rc]["canonical"]
        nc  = outcomes[rc]["no_care"]
        hc  = outcomes[rc]["high_care"]

        c1 = can["extinction_rate"] < 0.5                   # viable canonical
        c2 = can["max_gen_mean"] >= 3.0                     # multi-generation
        c3 = nc["extinction_rate"] > can["extinction_rate"] # no-care clearly worse
        c4 = can["peak_pop_mean"] < 400                     # no unbounded explosion

        passed = c1 and c2 and c3 and c4
        selection_log.append(
            f"rc={rc}: canonical_ext={can['extinction_rate']:.3f} "
            f"max_gen={can['max_gen_mean']:.1f} "
            f"no_care_ext={nc['extinction_rate']:.3f} "
            f"hc_ext={hc['extinction_rate']:.3f} "
            f"peak_pop={can['peak_pop_mean']:.0f} "
            f"PASS={passed}"
        )
        if selected_rc is None and passed:
            selected_rc = rc

    if selected_rc is None:
        selected_rc = min(REPRO_COSTS)
        selection_log.append(
            f"No rc met all criteria. Fallback: rc={selected_rc} (lowest tested)."
        )

    # ── Plots ──────────────────────────────────────────────────────────────────
    plot_extinction_vs_rc(outcomes, plot_dir)
    plot_pop_over_time_canonical(agg_by_rc_cond, plot_dir)
    plot_final_pop_vs_rc(outcomes, plot_dir)
    plot_max_gen_vs_rc(outcomes, plot_dir)
    plot_child_survival_selected(outcomes, selected_rc, plot_dir)
    plot_food_over_time_selected(agg_by_rc_cond, selected_rc, plot_dir)
    plot_energy_over_time_selected(agg_by_rc_cond, selected_rc, plot_dir)
    plot_births_deaths_selected(agg_by_rc_cond, selected_rc, plot_dir)
    print(f"8 plots saved to {plot_dir}")

    # ── Config JSON ───────────────────────────────────────────────────────────
    config_data = {
        "phase": "5f",
        "duration": args.duration,
        "seeds": args.seeds,
        "repro_costs_swept": REPRO_COSTS,
        "conditions": CONDITIONS,
        "ecology": {
            "init_food":                    INIT_FOOD,
            "replenish_amount":             REPLENISH_AMOUNT,
            "threshold_ratio":              THRESHOLD_RATIO,
            "continuous_food_rate":         CONTINUOUS_FOOD_RATE,
            "continuous_food_max":          CONTINUOUS_FOOD_MAX,
            "infant_starvation_multiplier": INFANT_STARVATION_MULTIPLIER,
        },
    }
    with open(os.path.join(outdir, "config.json"), "w", encoding="utf-8") as f:
        json.dump(config_data, f, indent=2)

    # ── Summary JSON ──────────────────────────────────────────────────────────
    sel = outcomes[selected_rc]
    summary = {
        "phase":            "5f",
        "description":      "Reproduction cost calibration sweep",
        "duration":         args.duration,
        "n_seeds":          args.seeds,
        "repro_costs_swept": REPRO_COSTS,
        "selected_rc":      selected_rc,
        "selection_log":    selection_log,
        "selected_outcomes": {
            cl: sel[cl] for cl in ["no_care", "canonical", "high_care"]
        },
        "all_outcomes": {
            str(rc): {
                cl: outcomes[rc][cl]
                for cl in ["no_care", "canonical", "high_care"]
            }
            for rc in REPRO_COSTS
        },
    }
    with open(os.path.join(outdir, "summary.json"), "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    # ── Print digest ──────────────────────────────────────────────────────────
    print(f"\nOutput: {outdir}")
    print(f"Selected reproduction_cost: {selected_rc}")
    print("\nSelection log (highest to lowest rc):")
    for note in selection_log:
        print(" ", note)
    print(f"\nOutcomes under selected rc={selected_rc}:")
    for cl in ["no_care", "canonical", "high_care"]:
        s = sel[cl]
        print(
            f"  {cl:12s}: ext={s['extinction_rate']:.3f} "
            f"max_gen={s['max_gen_mean']:.1f}+/-{s['max_gen_sd']:.1f} "
            f"peak_pop={s['peak_pop_mean']:.0f} "
            f"child_surv={s['init_child_surv_mean']:.3f} "
            f"crash_t={s['crash_tick_mean']:.0f} "
            f"feed={s['feed_rate_mean']:.4f}"
        )

    sys.exit(0)


if __name__ == "__main__":
    main()
