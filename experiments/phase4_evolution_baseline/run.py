"""Phase 4: Evolution Baseline

Open empirical question: under standard ecology (no infant dependency,
moderate dispersal), does care_weight erode, persist, or build under
natural selection?

Expected based on Hamilton's rule:
  r is low (scatter=5, moderate mixing)
  B is marginal (infants survive without care, mult=1.0)
  C is real (feed_cost drains energy)
  => rB < C => selection should disfavour care (r < 0)

But this is an empirical question. Report as-is. Do not force interpretation.

Protocol:
  infant_starvation_multiplier = 1.0
  birth_scatter_radius         = 5
  care_weight init             = U(0.0, 1.0), mean=0.50
  plasticity                   = OFF
  mutation                     = ON
  duration                     = 10,000 ticks
  seeds                        = 42-51 (10 seeds)
  primary metric               = Pearson r(care_weight, generation) from birth_log
"""
import sys
import os
import json
import csv
import random as _random

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, PROJECT_ROOT)

from config import Config
from simulation.simulation import Simulation
from evolution.genome import Genome
from utils.experiment import set_seed, create_run_dir, save_config, save_metadata
from utils.plotting import generate_all_plots

PHASE_NAME        = "phase4_evolution_baseline"
INFANT_MULT       = 1.0
BIRTH_SCATTER     = 5
SNAPSHOT_INTERVAL = 200   # every 200 ticks => 50 snapshots per 10,000-tick run


# =============================================================================
# Helpers (exported for multi-seed runner)
# =============================================================================

def _make_neutral_genomes(n: int) -> list[Genome]:
    """Phase 4 genome init: care_weight ~ U(0, 1), mean=0.50 (neutral)."""
    return [
        Genome(
            care_weight=_random.uniform(0.0, 1.0),
            forage_weight=_random.uniform(0.0, 1.0),
            self_weight=_random.uniform(0.0, 1.0),
        )
        for _ in range(n)
    ]


def compute_selection_gradient(birth_log_path: str) -> float | None:
    """Pearson r of mother_care_weight vs mother_generation from birth_log.csv.

    r < 0: care erodes (higher-generation mothers have lower care_weight)
    r > 0: care builds (higher-generation mothers have higher care_weight)
    r ~ 0: selectively invisible
    """
    if not os.path.exists(birth_log_path):
        return None
    with open(birth_log_path) as f:
        rows = list(csv.DictReader(f))
    if len(rows) < 10:
        return None
    cw   = [float(r["mother_care_weight"]) for r in rows]
    gens = [float(r["mother_generation"])  for r in rows]
    n = len(cw)
    mean_cw  = sum(cw)   / n
    mean_gen = sum(gens) / n
    num      = sum((cw[i] - mean_cw) * (gens[i] - mean_gen) for i in range(n))
    den_cw   = sum((x - mean_cw)  ** 2 for x in cw)  ** 0.5
    den_gen  = sum((x - mean_gen) ** 2 for x in gens) ** 0.5
    if den_cw == 0 or den_gen == 0:
        return None
    return num / (den_cw * den_gen)


def _variance(values: list[float]) -> float:
    n = len(values)
    if n < 2:
        return 0.0
    m = sum(values) / n
    return sum((x - m) ** 2 for x in values) / (n - 1)


# =============================================================================
# Main single-seed run
# =============================================================================

def run(seed: int = 42) -> str:
    """Run Phase 4 evolution baseline for one seed. Returns output_dir."""
    config = Config()
    config.seed                         = seed
    config.init_mothers                 = 12
    config.init_food                    = 45
    config.max_ticks                    = 10_000
    config.infant_starvation_multiplier = INFANT_MULT
    config.birth_scatter_radius         = BIRTH_SCATTER
    config.plasticity_enabled           = False
    config.plasticity_kin_conditional   = False
    config.children_enabled             = True
    config.care_enabled                 = True
    config.reproduction_enabled         = True
    config.mutation_enabled             = True

    set_seed(seed)
    output_dir = create_run_dir(PHASE_NAME, seed)
    save_config(config, output_dir)
    save_metadata(
        output_dir,
        phase=PHASE_NAME,
        seed=seed,
        num_agents=config.init_mothers * 2,
        infant_starvation_multiplier=INFANT_MULT,
        birth_scatter_radius=BIRTH_SCATTER,
        plasticity_enabled=False,
        note=(
            "Phase 4: Evolution Baseline. "
            "Standard ecology: mult=1.0, scatter=5. "
            "care_weight init U(0,1), mean=0.50. "
            "Open question: does care erode, persist, or build?"
        ),
    )

    genomes = _make_neutral_genomes(config.init_mothers)
    sim     = Simulation(config)
    sim.initialize(genomes)

    population_history:   list[int]   = []
    energy_history:       list[float] = []
    generation_snapshots: list[dict]  = []

    while sim.tick < config.max_ticks:
        sim.step()
        sim.tick += 1
        alive_m = [m for m in sim.mothers if m.alive]
        population_history.append(len(alive_m))
        energy_history.append(
            sum(m.energy for m in alive_m) / len(alive_m) if alive_m else 0.0
        )
        if sim.tick % SNAPSHOT_INTERVAL == 0 and alive_m:
            cw_vals = [m.genome.care_weight   for m in alive_m]
            fw_vals = [m.genome.forage_weight for m in alive_m]
            sw_vals = [m.genome.self_weight   for m in alive_m]
            generation_snapshots.append({
                "tick":              sim.tick,
                "avg_care_weight":   sum(cw_vals) / len(cw_vals),
                "var_care_weight":   _variance(cw_vals),
                "min_care_weight":   min(cw_vals),
                "max_care_weight":   max(cw_vals),
                "avg_forage_weight": sum(fw_vals) / len(fw_vals),
                "avg_self_weight":   sum(sw_vals) / len(sw_vals),
                "avg_generation":    sum(m.generation for m in alive_m) / len(alive_m),
                "max_generation":    max(m.generation for m in alive_m),
                "n_mothers":         len(alive_m),
            })

    sim.logger.save_all(output_dir)
    with open(os.path.join(output_dir, "population_history.json"), "w") as f:
        json.dump({"population": population_history, "energy": energy_history}, f)
    with open(os.path.join(output_dir, "generation_snapshots.json"), "w") as f:
        json.dump(generation_snapshots, f, indent=2)

    grad = compute_selection_gradient(os.path.join(output_dir, "birth_log.csv"))

    generate_all_plots(output_dir)

    alive_final = [m for m in sim.mothers if m.alive]
    n_alive     = len(alive_final)
    final_cw    = sum(m.genome.care_weight for m in alive_final) / n_alive if n_alive else 0.0
    final_gen   = max(m.generation for m in alive_final) if alive_final else 0

    print(f"\n[{PHASE_NAME} | seed={seed}] Output: {output_dir}")
    print(f"  Surviving mothers    : {n_alive}")
    print(f"  Final avg care_weight: {final_cw:.4f}  (init mean=0.500)")
    print(f"  Final max generation : {final_gen}")
    if grad is not None:
        direction = "eroding" if grad < -0.02 else ("building" if grad > 0.02 else "neutral")
        print(f"  Selection gradient r : {grad:+.4f}  ({direction})")
    else:
        print("  Selection gradient r : N/A (insufficient birth data)")

    return output_dir


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Phase 4: Evolution Baseline (single seed)")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    run(seed=args.seed)
