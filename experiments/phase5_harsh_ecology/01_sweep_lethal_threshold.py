# experiments/phase5_harsh_ecology/01_sweep_lethal_threshold.py
"""Phase 5 — Ecological Threshold Sweep (Plasticity OFF)

Sweeps infant_starvation_multiplier across 9 values to find the
Minimum Lethal Ecology (MLE): the lowest multiplier at which pure
Darwinian selection (no plasticity) fails to save any seed.

This MLE becomes the locked-in ecology parameter for Phase 6,
ensuring that Phase 6 survival is caused by plasticity alone.

Settings (frozen):
  Genome    : care=0.30, forage=1.0, self=0.70  (Phase 3 canonical)
  Plasticity: OFF
  Mutation  : ON
  Grid      : 50x50, init_mothers=40, init_food=120
  Scatter   : birth_scatter_radius=2  (tight kin clustering)
  Duration  : 5,000 ticks (early stop at alive_mothers == 0)
  Seeds     : 42-46 (5 per multiplier)

Output columns:
  Multiplier | Seeds Survived | Survival % | Mean Final Pop | Mean Ticks to Extinction
"""
import sys
import os
import csv
import json
from datetime import datetime

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, PROJECT_ROOT)

from config import Config
from simulation.simulation import Simulation
from evolution.genome import Genome
from utils.experiment import set_seed

OUTPUT_DIR = os.path.join(PROJECT_ROOT, "outputs", "phase5_harsh_ecology")

SWEEP_MULTS  = [1.10, 1.15, 1.20, 1.25, 1.30, 1.35, 1.40, 1.50, 1.65]
SEEDS        = [42, 43, 44, 45, 46]
MAX_TICKS    = 5_000
INIT_CARE    = 0.30
INIT_FORAGE  = 1.0
INIT_SELF    = 0.70
SCATTER      = 2


def _build_config(seed: int, mult: float) -> Config:
    cfg = Config()
    cfg.seed          = seed
    cfg.width         = 50
    cfg.height        = 50
    cfg.init_mothers  = 40
    cfg.init_food     = 120
    cfg.max_ticks     = MAX_TICKS

    cfg.infant_starvation_multiplier = mult
    cfg.birth_scatter_radius         = SCATTER

    cfg.children_enabled    = True
    cfg.care_enabled        = True
    cfg.plasticity_enabled  = False   # CONTROL — no plasticity
    cfg.reproduction_enabled = True
    cfg.mutation_enabled    = True
    return cfg


def _make_genomes(n: int) -> list:
    return [Genome(care_weight=INIT_CARE, forage_weight=INIT_FORAGE, self_weight=INIT_SELF)
            for _ in range(n)]


def _run_single(seed: int, mult: float) -> dict:
    """Run one seed. Returns result dict with survived, final_pop, extinction_tick."""
    cfg = _build_config(seed, mult)
    set_seed(seed)

    sim = Simulation(cfg)
    sim.initialize(_make_genomes(cfg.init_mothers))

    extinction_tick = None
    while sim.tick < cfg.max_ticks:
        sim.step()
        sim.tick += 1

        alive = sum(1 for m in sim.mothers if m.alive)
        if alive == 0:
            extinction_tick = sim.tick
            break

    alive_final = sum(1 for m in sim.mothers if m.alive)
    survived    = alive_final > 0

    return {
        "seed":             seed,
        "mult":             mult,
        "survived":         survived,
        "final_pop":        alive_final,
        "extinction_tick":  extinction_tick,   # None if survived
    }


def _run_sweep() -> dict:
    """Outer loop: all multipliers x seeds. Returns results keyed by mult."""
    all_results = {}
    total = len(SWEEP_MULTS) * len(SEEDS)
    done  = 0

    for mult in SWEEP_MULTS:
        mult_results = []
        for seed in SEEDS:
            done += 1
            print(f"  [{done:>2}/{total}] mult={mult:.2f}  seed={seed} ...", end="", flush=True)
            r = _run_single(seed, mult)
            status = "SURVIVED" if r["survived"] else f"extinct @ tick {r['extinction_tick']}"
            print(f"  pop={r['final_pop']:>3}  {status}")
            mult_results.append(r)
        all_results[mult] = mult_results

    return all_results


def _print_summary(all_results: dict):
    print("\n" + "=" * 75)
    print("  PHASE 5 — ECOLOGICAL THRESHOLD SWEEP SUMMARY  (plasticity OFF)")
    print("=" * 75)

    header = (
        f"  {'Mult':>6}  {'Survived':>9}  {'Survival%':>10}  "
        f"{'Mean Final Pop':>15}  {'Mean Ticks->Extinct':>20}"
    )
    print(header)
    print("-" * 75)

    mle_candidate = None

    for mult in SWEEP_MULTS:
        results      = all_results[mult]
        n_seeds      = len(results)
        n_survived   = sum(1 for r in results if r["survived"])
        survival_pct = 100.0 * n_survived / n_seeds
        mean_pop     = sum(r["final_pop"] for r in results) / n_seeds

        ext_ticks = [r["extinction_tick"] for r in results if not r["survived"]]
        if ext_ticks:
            mean_ext = f"{sum(ext_ticks) / len(ext_ticks):.0f}"
        else:
            mean_ext = "N/A (all survived)"

        print(
            f"  {mult:>6.2f}  {n_survived:>4}/{n_seeds:<4}  {survival_pct:>9.0f}%  "
            f"{mean_pop:>15.1f}  {mean_ext:>20}"
        )

        if n_survived == 0 and mle_candidate is None:
            mle_candidate = mult

    print("=" * 75)

    print("\n--- MLE VERDICT ---")
    if mle_candidate is not None:
        print(f"  Minimum Lethal Ecology (MLE) = {mle_candidate:.2f}")
        print(f"  All {len(SEEDS)} seeds went extinct at mult={mle_candidate:.2f} with plasticity OFF.")
        print(f"  -> Lock this value as the Phase 6 ecology parameter.")
        print(f"  -> Survival in Phase 6 at mult={mle_candidate:.2f} will be attributable")
        print(f"     solely to kin-conditional plasticity (Baldwin Effect test).")
    else:
        print("  WARNING: No multiplier in the sweep produced 0% survival.")
        print("  The MLE lies above the highest tested value (1.65).")
        print("  Consider extending the sweep to higher multipliers.")
    print()


def _save_results(all_results: dict, mle_candidate: float | None) -> str:
    """Save per-seed CSV, per-multiplier JSON summary, and verdict txt. Returns output dir."""
    run_dir = os.path.join(OUTPUT_DIR, datetime.now().strftime("%Y%m%d_%H%M%S"))
    os.makedirs(run_dir, exist_ok=True)

    # Per-seed raw results — one row per (mult, seed)
    csv_path = os.path.join(run_dir, "sweep_results.csv")
    with open(csv_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["mult", "seed", "survived", "final_pop", "extinction_tick"])
        writer.writeheader()
        for mult in SWEEP_MULTS:
            for r in all_results[mult]:
                writer.writerow({
                    "mult":             r["mult"],
                    "seed":             r["seed"],
                    "survived":         r["survived"],
                    "final_pop":        r["final_pop"],
                    "extinction_tick":  r["extinction_tick"],
                })

    # Per-multiplier summary JSON
    summary = {}
    for mult in SWEEP_MULTS:
        results      = all_results[mult]
        n_seeds      = len(results)
        n_survived   = sum(1 for r in results if r["survived"])
        ext_ticks    = [r["extinction_tick"] for r in results if not r["survived"]]
        summary[str(mult)] = {
            "n_survived":       n_survived,
            "n_seeds":          n_seeds,
            "survival_pct":     round(100.0 * n_survived / n_seeds, 1),
            "mean_final_pop":   round(sum(r["final_pop"] for r in results) / n_seeds, 2),
            "mean_extinction_tick": round(sum(ext_ticks) / len(ext_ticks), 1) if ext_ticks else None,
        }
    with open(os.path.join(run_dir, "sweep_summary.json"), "w") as f:
        json.dump(summary, f, indent=2)

    # Verdict plain-text (easy to read as evidence)
    verdict_lines = [
        "PHASE 5 — ECOLOGICAL THRESHOLD SWEEP VERDICT",
        f"Run timestamp : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"Multipliers   : {SWEEP_MULTS}",
        f"Seeds         : {SEEDS}",
        f"Max ticks     : {MAX_TICKS}",
        f"Plasticity    : OFF  |  Mutation: ON  |  Scatter: {SCATTER}",
        "",
    ]
    if mle_candidate is not None:
        verdict_lines += [
            f"Minimum Lethal Ecology (MLE) = {mle_candidate:.2f}",
            f"All {len(SEEDS)} seeds went extinct at mult={mle_candidate:.2f} with plasticity OFF.",
            f"-> Lock this value as the Phase 6 ecology parameter.",
            f"-> Survival in Phase 6 at mult={mle_candidate:.2f} will be attributable",
            f"   solely to kin-conditional plasticity (Baldwin Effect test).",
        ]
    else:
        verdict_lines += [
            "WARNING: No multiplier produced 0% survival.",
            "MLE lies above the highest tested value (1.65).",
        ]
    with open(os.path.join(run_dir, "verdict.txt"), "w") as f:
        f.write("\n".join(verdict_lines) + "\n")

    print(f"\n  [saved] {run_dir}/")
    print(f"    sweep_results.csv  — per-seed raw data")
    print(f"    sweep_summary.json — per-multiplier aggregates")
    print(f"    verdict.txt        — MLE verdict\n")
    return run_dir


def _get_mle(all_results: dict) -> float | None:
    for mult in SWEEP_MULTS:
        if sum(1 for r in all_results[mult] if r["survived"]) == 0:
            return mult
    return None


def main():
    print(f"\nPhase 5 — Ecological Threshold Sweep")
    print(f"  Multipliers : {SWEEP_MULTS}")
    print(f"  Seeds       : {SEEDS}")
    print(f"  Max ticks   : {MAX_TICKS}  (early stop if alive == 0)")
    print(f"  Plasticity  : OFF  |  Mutation: ON  |  Scatter: {SCATTER}\n")

    all_results   = _run_sweep()
    mle_candidate = _get_mle(all_results)
    _print_summary(all_results)
    _save_results(all_results, mle_candidate)


if __name__ == "__main__":
    main()
