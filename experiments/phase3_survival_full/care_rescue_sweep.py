#!/usr/bin/env python3
"""
Phase 4 — Care Rescue and Minimum Care Threshold

Tests whether maternal care rescues child survival under the Phase 3 selected
dependency setting (infant_starvation_multiplier=1.5, child hunger 0.012/tick).

Care rescue is valid only if realized FEED_CHILD behavior occurs AND improves
child survival — not merely if CARE motivation is selected.

Sweep:
    care_weight   = [0.0, 0.1, 0.2, 0.3, 0.5, 0.7]
    forage_weight = [0.7, 0.85, 1.0]
    self_weight   = [0.3, 0.5, 0.7]
    => 54 conditions x 30 seeds x 1000 ticks

Usage:
    python experiments/phase3_survival_full/care_rescue_sweep.py \\
        --duration 1000 --seeds 30 --child_hunger_rate 0.0120
"""

import argparse
import csv
import json
import math
import os
import sys
from datetime import datetime
from itertools import product

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, PROJECT_ROOT)

from config import Config
from simulation.simulation import Simulation

# ─── Constants ────────────────────────────────────────────────────────────────

INFANT_STARVATION_MULTIPLIER = 1.5   # selected from Phase 3

CARE_WEIGHTS   = [0.0, 0.1, 0.2, 0.3, 0.5, 0.7]
FORAGE_WEIGHTS = [0.7, 0.85, 1.0]
SELF_WEIGHTS   = [0.3, 0.5, 0.7]

CHILD_THRESHOLD  = 0.80
MOTHER_THRESHOLD = 0.80

# Representative cross-section for time-series plots
PLOT_FW = 0.85
PLOT_SW = 0.5

COLORS_CW = ["#aec7e8", "#1f77b4", "#98df8a", "#2ca02c", "#ffbb78", "#d62728"]


# ─── Config builder ───────────────────────────────────────────────────────────

def make_config(care_w: float, forage_w: float, self_w: float,
                seed: int, duration: int) -> Config:
    cfg = Config()
    cfg.seed = seed
    cfg.max_ticks = duration
    cfg.infant_starvation_multiplier = INFANT_STARVATION_MULTIPLIER
    cfg.care_weight   = care_w
    cfg.forage_weight = forage_w
    cfg.self_weight   = self_w
    cfg.care_enabled        = care_w > 0.0   # disable CARE domain for no-care control
    cfg.plasticity_enabled  = False
    cfg.reproduction_enabled = False
    cfg.mutation_enabled    = False
    cfg.children_enabled    = True
    cfg.init_mothers = 12
    cfg.init_food    = 45
    cfg.hunger_rate  = 0.008
    return cfg


# ─── Single run ───────────────────────────────────────────────────────────────

def run_single(care_w: float, forage_w: float, self_w: float,
               seed: int, duration: int) -> dict:
    cfg = make_config(care_w, forage_w, self_w, seed, duration)
    sim = Simulation(cfg)
    sim.initialize()

    n_initial_children = len(sim.children)
    n_initial_mothers  = len(sim.mothers)
    initial_mother_ids = {m.id for m in sim.mothers}

    per_tick: list[dict] = []

    for t in range(duration):
        care_before   = len(sim.logger.care_records)
        choice_before = len(sim.logger.choice_records)

        sim.step()
        sim.tick += 1   # match Simulation.run() bookkeeping

        alive_mothers  = sim.mothers
        alive_children = sim.children
        init_alive     = [m for m in alive_mothers if m.id in initial_mother_ids]

        mean_energy = (
            float(np.mean([m.energy for m in alive_mothers]))
            if alive_mothers else float("nan")
        )
        mean_child_hunger = (
            float(np.mean([c.hunger for c in alive_children]))
            if alive_children else float("nan")
        )

        # Mother–child distance (own-child pairs only)
        dists = []
        for m in alive_mothers:
            if m.own_child_id is not None:
                ch = sim._get_child_by_id(m.own_child_id)
                if ch and ch.alive:
                    dists.append(sim.world.get_distance(m.pos, ch.pos))
        mean_dist = float(np.mean(dists)) if dists else float("nan")

        # Care events this tick
        care_slice  = sim.logger.care_records[care_before:]
        n_feed_tick = sum(1 for r in care_slice if r.benefit > 0)
        n_care_att  = len(care_slice)

        # Choice records this tick (only logged when child distress >= 0.3)
        choice_slice    = sim.logger.choice_records[choice_before:]
        n_care_ch_tick  = sum(1 for r in choice_slice if r.winner_domain == "care")
        n_total_ch_tick = len(choice_slice)

        per_tick.append({
            "tick":                    t + 1,
            "n_alive_mothers":         len(alive_mothers),
            "n_initial_mothers_alive": len(init_alive),
            "n_alive_children":        len(alive_children),
            "mean_mother_energy":      mean_energy,
            "mean_child_hunger":       mean_child_hunger,
            "mean_dist":               mean_dist,
            "n_feed_this_tick":        n_feed_tick,
            "n_care_att_tick":         n_care_att,
            "n_care_choices_tick":     n_care_ch_tick,
            "n_total_choices_tick":    n_total_ch_tick,
        })

    # ── Post-run outcomes ──────────────────────────────────────────────────────
    child_deaths = [d for d in sim.logger.death_records if d.agent_type == "child"]
    n_matured    = sum(1 for d in child_deaths if d.cause == "matured")
    n_died       = sum(1 for d in child_deaths if d.cause == "hunger")
    n_alive_end  = len(sim.children)
    death_ticks  = [d.tick for d in child_deaths if d.cause == "hunger"]

    child_survival_rate = (n_matured + n_alive_end) / n_initial_children if n_initial_children else 0.0
    child_matured_rate  = n_matured / n_initial_children if n_initial_children else 0.0

    init_end = [m for m in sim.mothers if m.id in initial_mother_ids]
    mother_survival_rate     = len(init_end) / n_initial_mothers if n_initial_mothers else 0.0
    mean_mother_energy_final = float(np.mean([m.energy for m in init_end])) if init_end else 0.0

    care_recs = sim.logger.care_records
    n_feed_total     = sum(1 for r in care_recs if r.benefit > 0)
    n_care_att_total = len(care_recs)
    # failed_care_frac: fraction of adjacent feed attempts where benefit==0
    # (child hunger already 0 at moment of contact; rare with 1.5x multiplier)
    failed_care_frac = (
        (n_care_att_total - n_feed_total) / n_care_att_total
        if n_care_att_total > 0 else 0.0
    )
    feed_rate = n_feed_total / duration

    choice_recs = sim.logger.choice_records
    n_care_ch   = sum(1 for r in choice_recs if r.winner_domain == "care")
    n_total_ch  = len(choice_recs)
    # care_motivation_rate: conditional on distressed children being visible
    care_mot_rate = n_care_ch / n_total_ch if n_total_ch > 0 else 0.0

    return {
        "care_w":   care_w,
        "forage_w": forage_w,
        "self_w":   self_w,
        "seed":     seed,
        "n_initial_children": n_initial_children,
        "n_initial_mothers":  n_initial_mothers,
        "n_matured":   n_matured,
        "n_died":      n_died,
        "n_alive_end": n_alive_end,
        "death_ticks": death_ticks,
        "child_survival_rate":      child_survival_rate,
        "child_matured_rate":       child_matured_rate,
        "mother_survival_rate":     mother_survival_rate,
        "mean_mother_energy_final": mean_mother_energy_final,
        "n_feed_total":             n_feed_total,
        "n_care_att_total":         n_care_att_total,
        "failed_care_frac":         failed_care_frac,
        "feed_rate":                feed_rate,
        "care_mot_rate":            care_mot_rate,
        "per_tick":                 per_tick,
    }


# ─── Aggregation ──────────────────────────────────────────────────────────────

def _ms(results: list[dict], key: str) -> tuple[float, float]:
    vals = [r[key] for r in results]
    return float(np.mean(vals)), float(np.std(vals))


def aggregate(results: list[dict]) -> dict:
    csr_m, csr_s = _ms(results, "child_survival_rate")
    cmr_m, cmr_s = _ms(results, "child_matured_rate")
    msr_m, msr_s = _ms(results, "mother_survival_rate")
    mef_m, mef_s = _ms(results, "mean_mother_energy_final")
    fr_m,  fr_s  = _ms(results, "feed_rate")
    cm_m,  cm_s  = _ms(results, "care_mot_rate")
    fc_m,  fc_s  = _ms(results, "failed_care_frac")
    nf_m,  nf_s  = _ms(results, "n_feed_total")

    all_death_ticks: list[int] = []
    for r in results:
        all_death_ticks.extend(r["death_ticks"])

    return {
        "care_w":   results[0]["care_w"],
        "forage_w": results[0]["forage_w"],
        "self_w":   results[0]["self_w"],
        "n_seeds":  len(results),
        "child_survival_rate_mean":      csr_m, "child_survival_rate_sd":      csr_s,
        "child_matured_rate_mean":       cmr_m, "child_matured_rate_sd":       cmr_s,
        "mother_survival_rate_mean":     msr_m, "mother_survival_rate_sd":     msr_s,
        "mean_mother_energy_final_mean": mef_m, "mean_mother_energy_final_sd": mef_s,
        "feed_rate_mean":                fr_m,  "feed_rate_sd":                fr_s,
        "care_motivation_rate_mean":     cm_m,  "care_motivation_rate_sd":     cm_s,
        "failed_care_frac_mean":         fc_m,  "failed_care_frac_sd":         fc_s,
        "n_feed_total_mean":             nf_m,  "n_feed_total_sd":             nf_s,
        "all_death_ticks":               all_death_ticks,
        "passes_thresholds": (csr_m >= CHILD_THRESHOLD and msr_m >= MOTHER_THRESHOLD),
    }


def aggregate_per_tick(results: list[dict], duration: int) -> list[dict]:
    """Mean across seeds per tick for one condition."""
    agg = []
    for t in range(duration):
        rows = [r["per_tick"][t] for r in results if len(r["per_tick"]) > t]
        if not rows:
            continue

        def nanmean(key: str) -> float:
            vals = [row[key] for row in rows]
            finite = [v for v in vals if not math.isnan(v)]
            return float(np.mean(finite)) if finite else float("nan")

        def mean(key: str) -> float:
            return float(np.mean([row[key] for row in rows]))

        agg.append({
            "tick":               t + 1,
            "mean_n_mothers":     mean("n_alive_mothers"),
            "mean_n_children":    mean("n_alive_children"),
            "mean_energy":        nanmean("mean_mother_energy"),
            "mean_child_hunger":  nanmean("mean_child_hunger"),
            "mean_dist":          nanmean("mean_dist"),
            "mean_feed_tick":     mean("n_feed_this_tick"),
            "mean_care_choices":  mean("n_care_choices_tick"),
            "mean_total_choices": mean("n_total_choices_tick"),
        })
    return agg


# ─── CSV output ───────────────────────────────────────────────────────────────

OUTCOME_FIELDS = [
    "care_w", "forage_w", "self_w", "seed",
    "child_survival_rate", "child_matured_rate", "mother_survival_rate",
    "mean_mother_energy_final", "n_feed_total", "feed_rate",
    "care_mot_rate", "failed_care_frac", "n_care_att_total",
]

PER_TICK_AGG_FIELDS = [
    "care_w", "forage_w", "self_w", "tick",
    "mean_n_mothers", "mean_n_children", "mean_energy", "mean_child_hunger",
    "mean_dist", "mean_feed_tick", "mean_care_choices", "mean_total_choices",
]


def open_outcome_csv(out_dir: str):
    path = os.path.join(out_dir, "raw", "condition_outcomes.csv")
    f = open(path, "w", newline="", encoding="utf-8")
    w = csv.DictWriter(f, fieldnames=OUTCOME_FIELDS, extrasaction="ignore")
    w.writeheader()
    return w, f


def write_outcome_rows(writer: csv.DictWriter, results: list[dict]) -> None:
    for r in results:
        writer.writerow({k: r[k] for k in OUTCOME_FIELDS})


def open_per_tick_agg_csv(out_dir: str):
    path = os.path.join(out_dir, "raw", "per_tick_agg.csv")
    f = open(path, "w", newline="", encoding="utf-8")
    w = csv.DictWriter(f, fieldnames=PER_TICK_AGG_FIELDS)
    w.writeheader()
    return w, f


def write_per_tick_agg_rows(
    writer: csv.DictWriter,
    care_w: float, forage_w: float, self_w: float,
    tick_data: list[dict],
) -> None:
    for row in tick_data:
        full = {"care_w": care_w, "forage_w": forage_w, "self_w": self_w}
        full.update(row)
        writer.writerow({k: full.get(k, "") for k in PER_TICK_AGG_FIELDS})


def save_summary_csv(aggregated: list[dict], out_dir: str) -> None:
    fields = [
        "care_w", "forage_w", "self_w", "n_seeds",
        "child_survival_rate_mean", "child_survival_rate_sd",
        "child_matured_rate_mean",  "child_matured_rate_sd",
        "mother_survival_rate_mean","mother_survival_rate_sd",
        "mean_mother_energy_final_mean", "mean_mother_energy_final_sd",
        "feed_rate_mean", "feed_rate_sd",
        "care_motivation_rate_mean", "care_motivation_rate_sd",
        "failed_care_frac_mean",
        "passes_thresholds",
    ]
    path = os.path.join(out_dir, "rescue_summary.csv")
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        for a in aggregated:
            w.writerow({k: a[k] for k in fields})


# ─── JSON output ──────────────────────────────────────────────────────────────

def save_config_json(duration: int, n_seeds: int, out_dir: str) -> None:
    ex = make_config(0.3, 0.85, 0.5, 42, duration)
    doc = {
        "phase": 4,
        "experiment": "care_rescue_sweep",
        "duration_ticks": duration,
        "n_seeds": n_seeds,
        "sweep": {
            "care_weights":    CARE_WEIGHTS,
            "forage_weights":  FORAGE_WEIGHTS,
            "self_weights":    SELF_WEIGHTS,
            "n_conditions":    len(CARE_WEIGHTS) * len(FORAGE_WEIGHTS) * len(SELF_WEIGHTS),
            "n_total_runs":    len(CARE_WEIGHTS) * len(FORAGE_WEIGHTS) * len(SELF_WEIGHTS) * n_seeds,
        },
        "frozen_from_phase3": {
            "infant_starvation_multiplier":  INFANT_STARVATION_MULTIPLIER,
            "effective_child_hunger_rate":   0.008 * INFANT_STARVATION_MULTIPLIER,
        },
        "fixed_settings": {
            "plasticity_enabled":  False,
            "reproduction_enabled": False,
            "mutation_enabled":    False,
            "init_mothers":        ex.init_mothers,
            "init_food":           ex.init_food,
            "hunger_rate":         ex.hunger_rate,
            "feed_cost":           ex.feed_cost,
            "maturity_age":        ex.maturity_age,
        },
        "success_criteria": {
            "child_survival_threshold":  CHILD_THRESHOLD,
            "mother_survival_threshold": MOTHER_THRESHOLD,
        },
    }
    with open(os.path.join(out_dir, "config.json"), "w", encoding="utf-8") as f:
        json.dump(doc, f, indent=2)


def save_rescue_summary_json(
    aggregated: list[dict], selected: dict | None, out_dir: str
) -> None:
    passing = [a for a in aggregated if a["passes_thresholds"]]
    doc = {
        "phase": 4,
        "experiment": "care_rescue_sweep",
        "n_conditions_total":   len(aggregated),
        "n_conditions_passing": len(passing),
        "success_criteria": {
            "child_survival_threshold":  CHILD_THRESHOLD,
            "mother_survival_threshold": MOTHER_THRESHOLD,
        },
        "selected_canonical_genome": (
            {
                "care_weight":   selected["care_w"],
                "forage_weight": selected["forage_w"],
                "self_weight":   selected["self_w"],
            }
            if selected else None
        ),
        "all_conditions": [
            {
                "care_w":              a["care_w"],
                "forage_w":            a["forage_w"],
                "self_w":              a["self_w"],
                "child_survival_rate": round(a["child_survival_rate_mean"], 4),
                "mother_survival_rate":round(a["mother_survival_rate_mean"], 4),
                "feed_rate_per_tick":  round(a["feed_rate_mean"], 4),
                "care_motivation_rate":round(a["care_motivation_rate_mean"], 4),
                "n_feed_total_mean":   round(a["n_feed_total_mean"], 1),
                "passes_thresholds":   a["passes_thresholds"],
            }
            for a in aggregated
        ],
    }
    with open(os.path.join(out_dir, "rescue_summary.json"), "w", encoding="utf-8") as f:
        json.dump(doc, f, indent=2)


def save_canonical_genome_json(
    selected: dict | None, aggregated: list[dict], out_dir: str
) -> None:
    if selected is None:
        best = max(aggregated, key=lambda a: a["child_survival_rate_mean"])
        doc = {
            "phase": 4,
            "selected": False,
            "reason": (
                "No condition met both child_survival >= "
                f"{CHILD_THRESHOLD:.0%} and mother_survival >= {MOTHER_THRESHOLD:.0%}. "
                "Best-available condition saved below."
            ),
            "genome": {
                "care_weight":   best["care_w"],
                "forage_weight": best["forage_w"],
                "self_weight":   best["self_w"],
            },
            "performance": {
                "child_survival_rate_mean":  round(best["child_survival_rate_mean"], 4),
                "mother_survival_rate_mean": round(best["mother_survival_rate_mean"], 4),
                "feed_rate_per_tick_mean":   round(best["feed_rate_mean"], 4),
            },
        }
    else:
        doc = {
            "phase": 4,
            "selected": True,
            "reason": (
                f"Minimum care_weight satisfying child_survival >= {CHILD_THRESHOLD:.0%} "
                f"and mother_survival >= {MOTHER_THRESHOLD:.0%}. "
                "Tie-broken by minimum forage_weight, then minimum self_weight."
            ),
            "genome": {
                "care_weight":   selected["care_w"],
                "forage_weight": selected["forage_w"],
                "self_weight":   selected["self_w"],
            },
            "performance": {
                "child_survival_rate_mean":  round(selected["child_survival_rate_mean"], 4),
                "child_survival_rate_sd":    round(selected["child_survival_rate_sd"], 4),
                "mother_survival_rate_mean": round(selected["mother_survival_rate_mean"], 4),
                "mother_survival_rate_sd":   round(selected["mother_survival_rate_sd"], 4),
                "feed_rate_per_tick_mean":   round(selected["feed_rate_mean"], 4),
                "care_motivation_rate_mean": round(selected["care_motivation_rate_mean"], 4),
                "failed_care_fraction_mean": round(selected["failed_care_frac_mean"], 4),
            },
            "selection_criteria": {
                "child_survival_threshold":  CHILD_THRESHOLD,
                "mother_survival_threshold": MOTHER_THRESHOLD,
                "rule": "minimum care_weight, then minimum forage_weight, then minimum self_weight",
            },
        }
    with open(os.path.join(out_dir, "selected_canonical_genome.json"), "w", encoding="utf-8") as f:
        json.dump(doc, f, indent=2)


# ─── Plots ────────────────────────────────────────────────────────────────────

def _heatmap_matrix(aggregated: list[dict], self_w: float, key: str) -> np.ndarray:
    mat = np.full((len(CARE_WEIGHTS), len(FORAGE_WEIGHTS)), np.nan)
    for a in aggregated:
        if abs(a["self_w"] - self_w) < 1e-9:
            ci = CARE_WEIGHTS.index(a["care_w"])
            fi = FORAGE_WEIGHTS.index(a["forage_w"])
            mat[ci, fi] = a[key]
    return mat


def _draw_heatmap(aggregated: list[dict], key: str, title: str,
                  fname: str, out_dir: str, vmin: float = 0.0, vmax: float = 1.0) -> None:
    fig, axes = plt.subplots(1, 3, figsize=(14, 5), sharey=True)
    fig.suptitle(title, fontsize=11)
    for idx, sw in enumerate(SELF_WEIGHTS):
        ax = axes[idx]
        mat = _heatmap_matrix(aggregated, sw, key)
        im = ax.imshow(mat, vmin=vmin, vmax=vmax, cmap="RdYlGn",
                       aspect="auto", origin="lower")
        ax.set_xticks(range(len(FORAGE_WEIGHTS)))
        ax.set_xticklabels([f"{fw:.2f}" for fw in FORAGE_WEIGHTS])
        ax.set_yticks(range(len(CARE_WEIGHTS)))
        ax.set_yticklabels([f"{cw:.1f}" for cw in CARE_WEIGHTS])
        ax.set_xlabel("forage_weight")
        if idx == 0:
            ax.set_ylabel("care_weight")
        ax.set_title(f"self_weight={sw:.1f}")
        for ci in range(len(CARE_WEIGHTS)):
            for fi in range(len(FORAGE_WEIGHTS)):
                v = mat[ci, fi]
                if not math.isnan(v):
                    ax.text(fi, ci, f"{v:.2f}", ha="center", va="center",
                            fontsize=7, color="black")
        fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    plt.tight_layout()
    plt.savefig(os.path.join(out_dir, "plots", fname), dpi=150)
    plt.close()


def plot_heatmaps(aggregated: list[dict], out_dir: str) -> None:
    _draw_heatmap(
        aggregated, "child_survival_rate_mean",
        f"Phase 4: Child Survival Rate (infant_starvation_multiplier={INFANT_STARVATION_MULTIPLIER}, "
        f"30 seeds, 1000 ticks)",
        "01_child_survival_heatmap.png", out_dir,
    )
    _draw_heatmap(
        aggregated, "mother_survival_rate_mean",
        "Phase 4: Mother Survival Rate (initial mothers only, 30 seeds, 1000 ticks)",
        "02_mother_survival_heatmap.png", out_dir,
    )


def _load_per_tick_agg(out_dir: str, forage_w: float, self_w: float) -> dict:
    """Return {care_w: [tick_row, ...]} for the given forage_w / self_w cross-section."""
    path = os.path.join(out_dir, "raw", "per_tick_agg.csv")
    result: dict[float, list[dict]] = {}
    with open(path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if (abs(float(row["forage_w"]) - forage_w) < 1e-6 and
                    abs(float(row["self_w"]) - self_w) < 1e-6):
                cw = float(row["care_w"])
                if cw not in result:
                    result[cw] = []
                result[cw].append({
                    k: float(row[k])
                    for k in row
                    if k not in ("care_w", "forage_w", "self_w")
                })
    return result


def plot_feed_child_rate_over_time(per_tick_data: dict, out_dir: str) -> None:
    fig, ax = plt.subplots(figsize=(10, 5))
    for idx, cw in enumerate(CARE_WEIGHTS):
        if cw not in per_tick_data:
            continue
        rows = sorted(per_tick_data[cw], key=lambda r: r["tick"])
        ticks = [r["tick"] for r in rows]
        feeds = [r["mean_feed_tick"] for r in rows]
        label = f"care_w={cw:.1f}" if cw > 0 else "care_w=0.0 (control)"
        ax.plot(ticks, feeds, color=COLORS_CW[idx], label=label, linewidth=1.6)
    ax.set_xlabel("Tick")
    ax.set_ylabel("Mean FEED_CHILD Events per Tick (across seeds)")
    ax.set_title(
        f"Phase 4: FEED_CHILD Rate Over Time\n"
        f"(forage_w={PLOT_FW}, self_w={PLOT_SW})"
    )
    ax.legend(loc="upper right", fontsize=8)
    plt.tight_layout()
    plt.savefig(os.path.join(out_dir, "plots", "03_feed_child_rate_over_time.png"), dpi=150)
    plt.close()


def plot_child_hunger_over_time(per_tick_data: dict, out_dir: str) -> None:
    fig, ax = plt.subplots(figsize=(10, 5))
    for idx, cw in enumerate(CARE_WEIGHTS):
        if cw not in per_tick_data:
            continue
        rows = sorted(per_tick_data[cw], key=lambda r: r["tick"])
        valid = [(r["tick"], r["mean_child_hunger"])
                 for r in rows if not math.isnan(r["mean_child_hunger"])]
        if not valid:
            continue
        t_v, h_v = zip(*valid)
        label = f"care_w={cw:.1f}" if cw > 0 else "care_w=0.0 (control)"
        ax.plot(t_v, h_v, color=COLORS_CW[idx], label=label, linewidth=1.6)
    ax.set_xlabel("Tick")
    ax.set_ylabel("Mean Child Hunger (alive children only)")
    ax.set_ylim(0, 1.05)
    ax.set_title(
        f"Phase 4: Mean Child Hunger Over Time\n"
        f"(forage_w={PLOT_FW}, self_w={PLOT_SW})"
    )
    ax.legend(loc="upper left", fontsize=8)
    plt.tight_layout()
    plt.savefig(os.path.join(out_dir, "plots", "04_child_hunger_over_time.png"), dpi=150)
    plt.close()


def plot_mother_child_distance_over_time(per_tick_data: dict, out_dir: str) -> None:
    fig, ax = plt.subplots(figsize=(10, 5))
    for idx, cw in enumerate(CARE_WEIGHTS):
        if cw == 0.0 or cw not in per_tick_data:
            continue
        rows = sorted(per_tick_data[cw], key=lambda r: r["tick"])
        valid = [(r["tick"], r["mean_dist"])
                 for r in rows if not math.isnan(r["mean_dist"])]
        if not valid:
            continue
        t_v, d_v = zip(*valid)
        ax.plot(t_v, d_v, color=COLORS_CW[idx], label=f"care_w={cw:.1f}", linewidth=1.6)
    ax.set_xlabel("Tick")
    ax.set_ylabel("Mean Mother–Child Distance (grid steps, active pairs)")
    ax.set_title(
        f"Phase 4: Mother–Child Distance Over Time\n"
        f"(forage_w={PLOT_FW}, self_w={PLOT_SW}; care_w=0 excluded)"
    )
    ax.legend(loc="upper right", fontsize=8)
    plt.tight_layout()
    plt.savefig(os.path.join(out_dir, "plots", "05_mother_child_distance_over_time.png"), dpi=150)
    plt.close()


def plot_care_trap(aggregated: list[dict], out_dir: str) -> None:
    """care_weight vs final mother energy — shows metabolic cost of care."""
    forage_colors = ["#2ca02c", "#1f77b4", "#d62728"]
    fig, axes = plt.subplots(1, 3, figsize=(14, 4), sharey=True)
    fig.suptitle(
        "Phase 4: Care Trap — care_weight vs Final Mother Energy\n"
        "(higher care_weight should reduce mother energy if care is costly)",
        fontsize=11,
    )
    for idx, sw in enumerate(SELF_WEIGHTS):
        ax = axes[idx]
        for fi, fw in enumerate(FORAGE_WEIGHTS):
            cws, means, sds = [], [], []
            for cw in CARE_WEIGHTS:
                a = next(
                    (x for x in aggregated
                     if abs(x["care_w"] - cw) < 1e-9
                     and abs(x["forage_w"] - fw) < 1e-9
                     and abs(x["self_w"] - sw) < 1e-9),
                    None
                )
                if a:
                    cws.append(cw)
                    means.append(a["mean_mother_energy_final_mean"])
                    sds.append(a["mean_mother_energy_final_sd"])
            ax.errorbar(
                cws, means, yerr=sds, capsize=4, marker="o",
                color=forage_colors[fi], label=f"fw={fw:.2f}", linewidth=1.5,
            )
        ax.set_xlabel("care_weight")
        if idx == 0:
            ax.set_ylabel("Final Mother Energy (mean +/- SD)")
        ax.set_title(f"self_weight={sw:.1f}")
        ax.legend(fontsize=8)
        ax.set_ylim(0, 1.0)
    plt.tight_layout()
    plt.savefig(os.path.join(out_dir, "plots", "06_care_trap.png"), dpi=150)
    plt.close()


def plot_motivation_breakdown(aggregated: list[dict], out_dir: str) -> None:
    """
    CARE motivation rate vs FEED_CHILD rate per tick for the representative
    cross-section (forage_w=PLOT_FW, self_w=PLOT_SW).

    Motivation rate: conditional on distressed children being visible (from choice_records).
    Feed rate: realized FEED_CHILD events / tick (from care_records).
    Gap between bars shows how much of CARE motivation translates to actual feeding.
    """
    cws, care_mot, feed_means, feed_sds = [], [], [], []
    for cw in CARE_WEIGHTS:
        a = next(
            (x for x in aggregated
             if abs(x["care_w"] - cw) < 1e-9
             and abs(x["forage_w"] - PLOT_FW) < 1e-9
             and abs(x["self_w"] - PLOT_SW) < 1e-9),
            None
        )
        if a:
            cws.append(cw)
            care_mot.append(a["care_motivation_rate_mean"])
            feed_means.append(a["feed_rate_mean"])
            feed_sds.append(a["feed_rate_sd"])

    if not cws:
        return

    x = np.arange(len(cws))
    width = 0.35

    fig, ax = plt.subplots(figsize=(9, 5))
    ax.bar(x - width / 2, care_mot, width,
           label="CARE motivation rate\n(conditional on child distress ≥ 0.3)",
           color="#1f77b4", alpha=0.85)
    ax.bar(x + width / 2, feed_means, width,
           label="FEED_CHILD rate (events/tick)",
           color="#2ca02c", alpha=0.85,
           yerr=feed_sds, capsize=4)
    ax.set_xticks(x)
    ax.set_xticklabels([f"cw={cw:.1f}" for cw in cws], rotation=15)
    ax.set_ylabel("Rate")
    ax.set_title(
        f"Phase 4: CARE Motivation Rate vs Realized FEED_CHILD Rate\n"
        f"(forage_w={PLOT_FW}, self_w={PLOT_SW})"
    )
    ax.legend(loc="upper left", fontsize=9)
    top = max(max(care_mot, default=0), max(feed_means, default=0))
    ax.set_ylim(0, top * 1.3 + 0.05)
    plt.tight_layout()
    plt.savefig(os.path.join(out_dir, "plots", "07_motivation_breakdown.png"), dpi=150)
    plt.close()


# ─── Selection ────────────────────────────────────────────────────────────────

def select_canonical(aggregated: list[dict]) -> dict | None:
    """Return min care_weight condition that passes both thresholds."""
    passing = [a for a in aggregated if a["passes_thresholds"]]
    if not passing:
        return None
    return min(passing, key=lambda a: (a["care_w"], a["forage_w"], a["self_w"]))


# ─── Main ─────────────────────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(description="Phase 4 — Care Rescue Sweep")
    parser.add_argument("--duration", type=int, default=1000)
    parser.add_argument("--seeds",    type=int, default=30)
    parser.add_argument(
        "--child_hunger_rate", type=float, default=0.0120,
        help="Effective child hunger rate (documentation only; "
             "actual = hunger_rate × infant_starvation_multiplier)",
    )
    parser.add_argument(
        "--out_label", type=str, default="phase4_care_rescue",
        help="Output folder name prefix (e.g. 'phase4b_care_rescue' for short-horizon rerun)",
    )
    args = parser.parse_args()

    expected_rate = 0.008 * INFANT_STARVATION_MULTIPLIER
    if abs(args.child_hunger_rate - expected_rate) > 1e-6:
        print(
            f"WARNING: --child_hunger_rate={args.child_hunger_rate:.4f} does not match "
            f"0.008 × {INFANT_STARVATION_MULTIPLIER} = {expected_rate:.4f}. "
            f"Actual child hunger rate is {expected_rate:.4f}/tick."
        )

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir = os.path.join(PROJECT_ROOT, "outputs", args.out_label, timestamp)
    os.makedirs(os.path.join(out_dir, "raw"),   exist_ok=True)
    os.makedirs(os.path.join(out_dir, "plots"), exist_ok=True)

    conditions = list(product(CARE_WEIGHTS, FORAGE_WEIGHTS, SELF_WEIGHTS))
    n_conditions = len(conditions)

    print(f"\n=== Phase 4 — Care Rescue and Minimum Care Threshold ===")
    print(f"Duration: {args.duration} ticks  |  Seeds: {args.seeds}")
    print(f"Conditions: {n_conditions}  |  Total runs: {n_conditions * args.seeds}")
    print(f"infant_starvation_multiplier: {INFANT_STARVATION_MULTIPLIER}  "
          f"(child hunger {expected_rate:.4f}/tick)")
    print(f"Output: {out_dir}\n")

    save_config_json(args.duration, args.seeds, out_dir)

    outcome_writer, outcome_file = open_outcome_csv(out_dir)
    ptick_writer, ptick_file     = open_per_tick_agg_csv(out_dir)

    all_aggregated: list[dict] = []

    for cond_idx, (care_w, forage_w, self_w) in enumerate(conditions):
        cond_label = f"cw={care_w:.2f} fw={forage_w:.2f} sw={self_w:.2f}"
        print(f"[{cond_idx + 1:3d}/{n_conditions}] {cond_label}")

        condition_results: list[dict] = []
        for seed in range(args.seeds):
            r = run_single(care_w, forage_w, self_w, seed, args.duration)
            condition_results.append(r)

        agg = aggregate(condition_results)
        all_aggregated.append(agg)

        write_outcome_rows(outcome_writer, condition_results)
        outcome_file.flush()

        # Save per-tick aggregate only for representative cross-section
        if abs(forage_w - PLOT_FW) < 1e-6 and abs(self_w - PLOT_SW) < 1e-6:
            tick_agg = aggregate_per_tick(condition_results, args.duration)
            write_per_tick_agg_rows(ptick_writer, care_w, forage_w, self_w, tick_agg)
            ptick_file.flush()

        # Free per-tick memory before next condition
        for r in condition_results:
            del r["per_tick"]

        flag = "PASS" if agg["passes_thresholds"] else "----"
        print(
            f"         [{flag}] "
            f"child={agg['child_survival_rate_mean']:.3f}+/-{agg['child_survival_rate_sd']:.3f}  "
            f"mother={agg['mother_survival_rate_mean']:.3f}+/-{agg['mother_survival_rate_sd']:.3f}  "
            f"feed_rate={agg['feed_rate_mean']:.3f}/tick  "
            f"care_mot={agg['care_motivation_rate_mean']:.3f}"
        )

    outcome_file.close()
    ptick_file.close()

    save_summary_csv(all_aggregated, out_dir)
    selected = select_canonical(all_aggregated)
    save_rescue_summary_json(all_aggregated, selected, out_dir)
    save_canonical_genome_json(selected, all_aggregated, out_dir)

    # ── Plots ─────────────────────────────────────────────────────────────────
    print("\nGenerating plots...")
    plot_heatmaps(all_aggregated, out_dir)

    per_tick_data = _load_per_tick_agg(out_dir, PLOT_FW, PLOT_SW)
    plot_feed_child_rate_over_time(per_tick_data, out_dir)
    plot_child_hunger_over_time(per_tick_data, out_dir)
    plot_mother_child_distance_over_time(per_tick_data, out_dir)
    plot_care_trap(all_aggregated, out_dir)
    plot_motivation_breakdown(all_aggregated, out_dir)

    # ── Console summary ───────────────────────────────────────────────────────
    passing = [a for a in all_aggregated if a["passes_thresholds"]]
    print(f"\n=== Phase 4 Summary ===")
    print(f"Total conditions: {n_conditions}  |  Passing both thresholds: {len(passing)}")

    ctrl = next(
        (a for a in all_aggregated
         if abs(a["care_w"]) < 1e-9
         and abs(a["forage_w"] - PLOT_FW) < 1e-9
         and abs(a["self_w"] - PLOT_SW) < 1e-9),
        None
    )
    if ctrl:
        print(
            f"No-care control (cw=0.0, fw={PLOT_FW}, sw={PLOT_SW}): "
            f"child_surv={ctrl['child_survival_rate_mean']:.3f}  "
            f"mother_surv={ctrl['mother_survival_rate_mean']:.3f}  "
            f"feed_events={ctrl['n_feed_total_mean']:.1f}"
        )

    if selected is not None:
        print(
            f"\nPhase 4 PASS — selected canonical genome:\n"
            f"  care_weight={selected['care_w']}  "
            f"forage_weight={selected['forage_w']}  "
            f"self_weight={selected['self_w']}\n"
            f"  child_survival={selected['child_survival_rate_mean']:.3f}"
            f"+/-{selected['child_survival_rate_sd']:.3f}  "
            f"mother_survival={selected['mother_survival_rate_mean']:.3f}"
            f"+/-{selected['mother_survival_rate_sd']:.3f}\n"
            f"  feed_rate={selected['feed_rate_mean']:.3f}/tick  "
            f"care_motivation={selected['care_motivation_rate_mean']:.3f}  "
            f"failed_care={selected['failed_care_frac_mean']:.4f}"
        )
    else:
        best = max(all_aggregated, key=lambda a: a["child_survival_rate_mean"])
        print(
            f"\nPhase 4 FAIL — no condition met both thresholds.\n"
            f"  Best child survival: {best['child_survival_rate_mean']:.3f} "
            f"at cw={best['care_w']}, fw={best['forage_w']}, sw={best['self_w']}"
        )

    print(f"\nOutputs: {out_dir}")
    return 0 if selected is not None else 1


if __name__ == "__main__":
    sys.exit(main())
