#!/usr/bin/env python3
"""
Phase 3 — Child Dependency Control

Sweeps infant_starvation_multiplier to find the minimum setting where
no-care child survival < 0.20. Confirms children require maternal care
to survive before Phase 4 tests whether care actually rescues them.

Usage:
    python experiments/phase3_survival_full/child_dependency_sweep.py --duration 1000 --seeds 30
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

# ─── Constants ────────────────────────────────────────────────────────────────

SWEEP_MULTIPLIERS = [1.0, 1.5, 2.0, 2.5, 3.0, 4.0]
SURVIVAL_THRESHOLD = 0.20   # weakest multiplier where survival < this → selected
COLORS = ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd", "#8c564b"]


# ─── Config builder ───────────────────────────────────────────────────────────

def make_config(multiplier: float, seed: int, duration: int) -> Config:
    cfg = Config()
    cfg.seed = seed
    cfg.max_ticks = duration
    cfg.infant_starvation_multiplier = multiplier

    # No-care control: child hunger, not maternal feeding, determines survival.
    cfg.care_weight = 0.0
    cfg.care_enabled = False        # removes CARE from softmax entirely
    cfg.plasticity_enabled = False
    cfg.reproduction_enabled = False
    cfg.mutation_enabled = False
    cfg.children_enabled = True

    # Ecological baseline kept at Phase 2 validated values.
    cfg.init_mothers = 12
    cfg.init_food = 45
    cfg.hunger_rate = 0.008

    return cfg


# ─── Single run ───────────────────────────────────────────────────────────────

def run_single(multiplier: float, seed: int, duration: int) -> dict:
    cfg = make_config(multiplier, seed, duration)
    sim = Simulation(cfg)
    sim.initialize()

    n_initial_children = len(sim.children)
    n_initial_mothers = len(sim.mothers)
    initial_mother_ids = {m.id for m in sim.mothers}

    per_tick: list[dict] = []

    for t in range(duration):
        sim.step()
        sim.tick += 1   # match Simulation.run() bookkeeping; required for correct DeathRecord.tick

        alive_children = sim.children  # already filtered to alive by step() cleanup
        alive_mothers = sim.mothers

        init_alive = [m for m in alive_mothers if m.id in initial_mother_ids]

        per_tick.append({
            "tick": t + 1,
            "n_alive_children": len(alive_children),
            "mean_child_hunger": (
                float(np.mean([c.hunger for c in alive_children]))
                if alive_children else float("nan")
            ),
            "n_alive_mothers": len(alive_mothers),
            "n_initial_mothers_alive": len(init_alive),
            "mean_mother_energy": (
                float(np.mean([m.energy for m in alive_mothers]))
                if alive_mothers else float("nan")
            ),
        })

    # Outcomes from death log
    child_deaths = [d for d in sim.logger.death_records if d.agent_type == "child"]
    n_matured = sum(1 for d in child_deaths if d.cause == "matured")
    n_died_hunger = sum(1 for d in child_deaths if d.cause == "hunger")
    n_alive_end = len(sim.children)
    death_ticks = [d.tick for d in child_deaths if d.cause == "hunger"]

    child_survival_rate = (n_matured + n_alive_end) / n_initial_children if n_initial_children > 0 else 0.0
    child_matured_rate = n_matured / n_initial_children if n_initial_children > 0 else 0.0

    init_alive_end = [m for m in sim.mothers if m.id in initial_mother_ids]
    mother_survival_rate = len(init_alive_end) / n_initial_mothers if n_initial_mothers > 0 else 0.0
    mean_mother_energy_final = (
        float(np.mean([m.energy for m in init_alive_end])) if init_alive_end else 0.0
    )

    n_care_events = len(sim.logger.care_records)

    return {
        "multiplier": multiplier,
        "seed": seed,
        "n_initial_children": n_initial_children,
        "n_initial_mothers": n_initial_mothers,
        "n_matured": n_matured,
        "n_died_hunger": n_died_hunger,
        "n_alive_end": n_alive_end,
        "child_survival_rate": child_survival_rate,
        "child_matured_rate": child_matured_rate,
        "death_ticks": death_ticks,
        "mother_survival_rate": mother_survival_rate,
        "mean_mother_energy_final": mean_mother_energy_final,
        "n_care_events": n_care_events,
        "per_tick": per_tick,
    }


# ─── Aggregation ──────────────────────────────────────────────────────────────

def aggregate(results: list[dict]) -> dict:
    def ms(key):
        vals = [r[key] for r in results]
        return float(np.mean(vals)), float(np.std(vals))

    csr_m, csr_s = ms("child_survival_rate")
    cmr_m, cmr_s = ms("child_matured_rate")
    msr_m, msr_s = ms("mother_survival_rate")
    mme_m, mme_s = ms("mean_mother_energy_final")

    all_death_ticks: list[int] = []
    for r in results:
        all_death_ticks.extend(r["death_ticks"])

    return {
        "multiplier": results[0]["multiplier"],
        "n_seeds": len(results),
        "child_survival_rate_mean": csr_m,
        "child_survival_rate_sd": csr_s,
        "child_matured_rate_mean": cmr_m,
        "child_matured_rate_sd": cmr_s,
        "mother_survival_rate_mean": msr_m,
        "mother_survival_rate_sd": msr_s,
        "mean_mother_energy_final_mean": mme_m,
        "mean_mother_energy_final_sd": mme_s,
        "all_death_ticks": all_death_ticks,
        "n_care_events_total": sum(r["n_care_events"] for r in results),
    }


# ─── CSV output ───────────────────────────────────────────────────────────────

def save_per_tick_csv(all_results: list[dict], out_dir: str) -> None:
    path = os.path.join(out_dir, "raw", "per_tick_log.csv")
    fields = [
        "multiplier", "seed", "tick",
        "n_alive_children", "mean_child_hunger",
        "n_alive_mothers", "n_initial_mothers_alive", "mean_mother_energy",
    ]
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in all_results:
            for row in r["per_tick"]:
                w.writerow({"multiplier": r["multiplier"], "seed": r["seed"], **row})


def save_child_outcomes_csv(all_results: list[dict], out_dir: str) -> None:
    path = os.path.join(out_dir, "raw", "child_outcomes.csv")
    fields = [
        "multiplier", "seed",
        "n_initial_children", "n_matured", "n_died_hunger", "n_alive_end",
        "child_survival_rate", "child_matured_rate",
        "mother_survival_rate", "mean_mother_energy_final",
        "death_ticks",
    ]
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in all_results:
            w.writerow({
                "multiplier": r["multiplier"],
                "seed": r["seed"],
                "n_initial_children": r["n_initial_children"],
                "n_matured": r["n_matured"],
                "n_died_hunger": r["n_died_hunger"],
                "n_alive_end": r["n_alive_end"],
                "child_survival_rate": r["child_survival_rate"],
                "child_matured_rate": r["child_matured_rate"],
                "mother_survival_rate": r["mother_survival_rate"],
                "mean_mother_energy_final": r["mean_mother_energy_final"],
                "death_ticks": ";".join(str(t) for t in r["death_ticks"]),
            })


def save_summary_csv(aggregated: list[dict], out_dir: str) -> None:
    path = os.path.join(out_dir, "dependency_summary.csv")
    fields = [
        "multiplier", "n_seeds",
        "child_survival_rate_mean", "child_survival_rate_sd",
        "child_matured_rate_mean", "child_matured_rate_sd",
        "mother_survival_rate_mean", "mother_survival_rate_sd",
        "mean_mother_energy_final_mean", "mean_mother_energy_final_sd",
        "n_care_events_total",
    ]
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for agg in aggregated:
            w.writerow({k: agg[k] for k in fields})


# ─── JSON output ──────────────────────────────────────────────────────────────

def save_config_json(duration: int, n_seeds: int, out_dir: str) -> None:
    ex = make_config(1.0, 42, duration)
    doc = {
        "phase": 3,
        "experiment": "child_dependency_sweep",
        "duration_ticks": duration,
        "n_seeds": n_seeds,
        "sweep_multipliers": SWEEP_MULTIPLIERS,
        "survival_threshold": SURVIVAL_THRESHOLD,
        "control": {
            "care_weight": ex.care_weight,
            "care_enabled": ex.care_enabled,
            "plasticity_enabled": ex.plasticity_enabled,
            "reproduction_enabled": ex.reproduction_enabled,
            "mutation_enabled": ex.mutation_enabled,
        },
        "ecology": {
            "init_mothers": ex.init_mothers,
            "init_food": ex.init_food,
            "hunger_rate": ex.hunger_rate,
            "maturity_age": ex.maturity_age,
            "starvation_threshold": ex.starvation_threshold,
        },
    }
    with open(os.path.join(out_dir, "config.json"), "w", encoding="utf-8") as f:
        json.dump(doc, f, indent=2)


def save_dependency_summary_json(
    aggregated: list[dict], selected: float | None, out_dir: str
) -> None:
    doc = {
        "phase": 3,
        "experiment": "child_dependency_sweep",
        "survival_threshold": SURVIVAL_THRESHOLD,
        "selected_multiplier": selected,
        "decision": (
            f"infant_starvation_multiplier={selected} is the weakest tested setting "
            f"where no-care child survival < {SURVIVAL_THRESHOLD:.0%}. "
            "Use this value for Phase 4 care-rescue sweep."
            if selected is not None
            else (
                "FAIL: All tested multipliers produce child survival >= "
                f"{SURVIVAL_THRESHOLD:.0%}. Children survive without care. "
                "Increase sweep range before proceeding to Phase 4."
            )
        ),
        "conditions": [
            {
                "multiplier": a["multiplier"],
                "child_survival_rate_mean": round(a["child_survival_rate_mean"], 4),
                "child_survival_rate_sd": round(a["child_survival_rate_sd"], 4),
                "child_matured_rate_mean": round(a["child_matured_rate_mean"], 4),
                "mother_survival_rate_mean": round(a["mother_survival_rate_mean"], 4),
                "n_care_events_total": a["n_care_events_total"],
                "passes_threshold": a["child_survival_rate_mean"] < SURVIVAL_THRESHOLD,
            }
            for a in aggregated
        ],
    }
    with open(os.path.join(out_dir, "dependency_summary.json"), "w", encoding="utf-8") as f:
        json.dump(doc, f, indent=2)


# ─── Plots ────────────────────────────────────────────────────────────────────

def _xtick_labels(multipliers: list[float]) -> list[str]:
    return [f"x{m:.1f}\n({0.008 * m:.4f}/tick)" for m in multipliers]


def plot_child_survival_rate(aggregated: list[dict], out_dir: str) -> None:
    mults = [a["multiplier"] for a in aggregated]
    means = [a["child_survival_rate_mean"] for a in aggregated]
    sds = [a["child_survival_rate_sd"] for a in aggregated]

    fig, ax = plt.subplots(figsize=(8, 5))
    ax.bar(range(len(mults)), means, yerr=sds, capsize=5,
           color=COLORS[:len(mults)], alpha=0.85, edgecolor="white")
    ax.axhline(SURVIVAL_THRESHOLD, color="red", linestyle="--", linewidth=1.5,
               label=f"Threshold ({SURVIVAL_THRESHOLD:.0%})")
    ax.set_xticks(range(len(mults)))
    ax.set_xticklabels(_xtick_labels(mults), fontsize=9)
    ax.set_ylabel("Child Survival Rate (mean ± SD)")
    ax.set_xlabel("infant_starvation_multiplier  (effective child hunger rate)")
    ax.set_title("Phase 3: No-Care Child Survival Rate vs Infant Dependency")
    ax.set_ylim(0, 1.15)
    ax.legend()
    plt.tight_layout()
    plt.savefig(os.path.join(out_dir, "plots", "01_child_survival_rate.png"), dpi=150)
    plt.close()


def plot_child_matured_rate(aggregated: list[dict], out_dir: str) -> None:
    mults = [a["multiplier"] for a in aggregated]
    means = [a["child_matured_rate_mean"] for a in aggregated]
    sds = [a["child_matured_rate_sd"] for a in aggregated]

    fig, ax = plt.subplots(figsize=(8, 5))
    ax.bar(range(len(mults)), means, yerr=sds, capsize=5,
           color=COLORS[:len(mults)], alpha=0.85, edgecolor="white")
    ax.set_xticks(range(len(mults)))
    ax.set_xticklabels(_xtick_labels(mults), fontsize=9)
    ax.set_ylabel("Child Matured Rate (mean ± SD)")
    ax.set_xlabel("infant_starvation_multiplier")
    ax.set_title("Phase 3: Fraction of Children Reaching Maturity (No Care)")
    ax.set_ylim(0, 1.15)
    plt.tight_layout()
    plt.savefig(os.path.join(out_dir, "plots", "02_child_matured_rate.png"), dpi=150)
    plt.close()


def plot_mean_child_hunger_over_time(all_results: list[dict], out_dir: str) -> None:
    fig, ax = plt.subplots(figsize=(10, 5))

    for idx, mult in enumerate(SWEEP_MULTIPLIERS):
        runs = [r for r in all_results if r["multiplier"] == mult]
        if not runs:
            continue
        T = max(len(r["per_tick"]) for r in runs)
        matrix = np.full((len(runs), T), np.nan)
        for i, r in enumerate(runs):
            for j, row in enumerate(r["per_tick"]):
                v = row["mean_child_hunger"]
                if not math.isnan(v):
                    matrix[i, j] = v
        mean_h = np.nanmean(matrix, axis=0)
        ticks = np.arange(1, T + 1)
        valid = ~np.isnan(mean_h)
        if valid.any():
            ax.plot(ticks[valid], mean_h[valid],
                    color=COLORS[idx], label=f"x{mult:.1f}", linewidth=1.8)

    ax.set_xlabel("Tick")
    ax.set_ylabel("Mean Child Hunger (alive children only)")
    ax.set_title("Phase 3: Mean Child Hunger Over Time by Multiplier (No Care)")
    ax.legend(title="Multiplier")
    ax.set_ylim(0, 1.05)
    plt.tight_layout()
    plt.savefig(os.path.join(out_dir, "plots", "03_mean_child_hunger_over_time.png"), dpi=150)
    plt.close()


def plot_time_to_death_distribution(all_results: list[dict], out_dir: str) -> None:
    mults_with_deaths = [
        m for m in SWEEP_MULTIPLIERS
        if any(r["n_died_hunger"] > 0 for r in all_results if r["multiplier"] == m)
    ]

    if not mults_with_deaths:
        fig, ax = plt.subplots(figsize=(6, 4))
        ax.text(0.5, 0.5,
                "No child deaths observed\n(all children survived or matured without care)",
                ha="center", va="center", transform=ax.transAxes, fontsize=12)
        ax.set_title("Phase 3: Time-to-Child-Death Distribution")
        plt.tight_layout()
        plt.savefig(os.path.join(out_dir, "plots", "04_time_to_death_distribution.png"), dpi=150)
        plt.close()
        return

    ncols = min(3, len(mults_with_deaths))
    nrows = math.ceil(len(mults_with_deaths) / ncols)
    fig, axes = plt.subplots(nrows, ncols, figsize=(5 * ncols, 4 * nrows), squeeze=False)

    for i, mult in enumerate(mults_with_deaths):
        r_idx, c_idx = divmod(i, ncols)
        ax = axes[r_idx][c_idx]
        runs = [r for r in all_results if r["multiplier"] == mult]
        death_ticks: list[int] = []
        for r in runs:
            death_ticks.extend(r["death_ticks"])
        if death_ticks:
            ax.hist(death_ticks, bins=30,
                    color=COLORS[SWEEP_MULTIPLIERS.index(mult)],
                    alpha=0.85, edgecolor="white")
        ax.set_title(f"x{mult:.1f}  (rate={0.008 * mult:.4f}/tick)")
        ax.set_xlabel("Death Tick")
        ax.set_ylabel("Count (all seeds combined)")

    for i in range(len(mults_with_deaths), nrows * ncols):
        r_idx, c_idx = divmod(i, ncols)
        axes[r_idx][c_idx].set_visible(False)

    fig.suptitle("Phase 3: Time-to-Child-Death Distribution (No Care)")
    plt.tight_layout()
    plt.savefig(os.path.join(out_dir, "plots", "04_time_to_death_distribution.png"), dpi=150)
    plt.close()


def plot_mother_survival_over_time(all_results: list[dict], out_dir: str) -> None:
    fig, ax = plt.subplots(figsize=(10, 5))

    for idx, mult in enumerate(SWEEP_MULTIPLIERS):
        runs = [r for r in all_results if r["multiplier"] == mult]
        if not runs:
            continue
        n_init = runs[0]["n_initial_mothers"]
        T = max(len(r["per_tick"]) for r in runs)
        matrix = np.zeros((len(runs), T))
        for i, r in enumerate(runs):
            for j, row in enumerate(r["per_tick"]):
                matrix[i, j] = row["n_initial_mothers_alive"] / n_init
        mean_surv = np.mean(matrix, axis=0)
        ax.plot(np.arange(1, T + 1), mean_surv,
                color=COLORS[idx], label=f"x{mult:.1f}", linewidth=1.8)

    ax.set_xlabel("Tick")
    ax.set_ylabel("Initial Mother Survival Rate (mean across seeds)")
    ax.set_title("Phase 3: Initial Mother Survival Over Time by Multiplier")
    ax.legend(title="Multiplier")
    ax.set_ylim(0, 1.05)
    plt.tight_layout()
    plt.savefig(os.path.join(out_dir, "plots", "05_mother_survival_over_time.png"), dpi=150)
    plt.close()


# ─── Main ─────────────────────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(description="Phase 3 — Child Dependency Control Sweep")
    parser.add_argument("--duration", type=int, default=1000)
    parser.add_argument("--seeds", type=int, default=30)
    args = parser.parse_args()

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir = os.path.join(PROJECT_ROOT, "outputs", "phase3_survival_full", timestamp)
    os.makedirs(os.path.join(out_dir, "raw"), exist_ok=True)
    os.makedirs(os.path.join(out_dir, "plots"), exist_ok=True)

    print(f"\n=== Phase 3 — Child Dependency Control ===")
    print(f"Duration: {args.duration} ticks  |  Seeds: {args.seeds}  |  Multipliers: {SWEEP_MULTIPLIERS}")
    print(f"Output: {out_dir}\n")

    save_config_json(args.duration, args.seeds, out_dir)

    all_results: list[dict] = []

    for m_idx, mult in enumerate(SWEEP_MULTIPLIERS):
        print(f"[{m_idx + 1}/{len(SWEEP_MULTIPLIERS)}] infant_starvation_multiplier={mult:.1f}")
        for seed in range(args.seeds):
            result = run_single(mult, seed, args.duration)
            all_results.append(result)
            if (seed + 1) % 10 == 0 or seed == args.seeds - 1:
                print(
                    f"  seed {seed + 1:3d}/{args.seeds} | "
                    f"child_survival={result['child_survival_rate']:.3f} | "
                    f"mother_survival={result['mother_survival_rate']:.3f}"
                )

    # Aggregate per multiplier
    aggregated = [
        aggregate([r for r in all_results if r["multiplier"] == m])
        for m in SWEEP_MULTIPLIERS
    ]

    # Select: weakest multiplier where child survival < threshold
    selected: float | None = None
    for agg in aggregated:
        if agg["child_survival_rate_mean"] < SURVIVAL_THRESHOLD:
            selected = agg["multiplier"]
            break

    # Save outputs
    save_per_tick_csv(all_results, out_dir)
    save_child_outcomes_csv(all_results, out_dir)
    save_summary_csv(aggregated, out_dir)
    save_dependency_summary_json(aggregated, selected, out_dir)

    # Plots
    plot_child_survival_rate(aggregated, out_dir)
    plot_child_matured_rate(aggregated, out_dir)
    plot_mean_child_hunger_over_time(all_results, out_dir)
    plot_time_to_death_distribution(all_results, out_dir)
    plot_mother_survival_over_time(all_results, out_dir)

    # Console summary
    print("\n=== Phase 3 Summary ===")
    header = f"{'Multiplier':>12} | {'Child Survival':>17} | {'Child Matured':>16} | {'Mother Survival':>17} | Care Events"
    print(header)
    print("-" * len(header))
    for agg in aggregated:
        flag = "  <-- SELECTED" if agg["multiplier"] == selected else ""
        print(
            f"  x{agg['multiplier']:.1f}        | "
            f"{agg['child_survival_rate_mean']:6.3f} ± {agg['child_survival_rate_sd']:.3f}   | "
            f"{agg['child_matured_rate_mean']:6.3f} ± {agg['child_matured_rate_sd']:.3f}  | "
            f"{agg['mother_survival_rate_mean']:6.3f} ± {agg['mother_survival_rate_sd']:.3f}    | "
            f"{agg['n_care_events_total']}"
            f"{flag}"
        )

    total_care = sum(r["n_care_events"] for r in all_results)
    print(f"\nTotal care events across all runs: {total_care}  (must be 0 for valid no-care control)")
    if total_care > 0:
        print("WARNING: Care events detected. Check care_enabled=False setting.")

    if selected is not None:
        print(f"\nPhase 3 PASS — selected infant_starvation_multiplier={selected}")
        print(f"  Weakest setting where no-care child survival < {SURVIVAL_THRESHOLD:.0%}")
        print(f"  Use in Phase 4 care-rescue sweep.")
    else:
        print(f"\nPhase 3 FAIL — no multiplier produced child survival < {SURVIVAL_THRESHOLD:.0%}")
        print("  Children survive without care. Extend sweep range before Phase 4.")

    print(f"\nOutputs: {out_dir}")
    return 0 if selected is not None else 1


if __name__ == "__main__":
    sys.exit(main())
