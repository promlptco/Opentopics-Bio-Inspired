# experiments/phase6d_biology_test/run.py
"""Phase 6d — Combined Biological Instinct Variables (Options A + D) at MLE=1.10

Phase 6c (MLE=1.25) confirmed the Baldwin mechanism is working — genetic
care_weight rose past 0.30 in 4/10 seeds and Pearson r was positive — but all
10 seeds went extinct because MLE=1.25 kills infants faster than mothers can
care for them, causing a demographic collapse before genetic assimilation
completes.

Phase 6d lowers MLE to 1.10, reducing the demographic pressure while keeping
all biological variables identical to Phase 6c:

  Option A — distress_sensitivity=0.005 (cortisol analog)
  Option D — care_recovery=0.40 (prolactin analog)

At MLE=1.10 infants survive long enough for care_recovery to accumulate,
allowing mothers to clear the reproduction threshold (0.95 energy) and maintain
population size through the genetic assimilation window.

Ecology: MLE=1.10, scatter=2, care_init=0.30.
Biological genes: identical to Phase 6c.
Plasticity: kin-conditional ON (same as Phase 6a/6c — proper Baldwin Effect test).
"""
import sys
import os
import csv
import json

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, PROJECT_ROOT)

from config import Config
from simulation.simulation import Simulation
from evolution.genome import Genome
from utils.experiment import set_seed, create_run_dir, save_config, save_metadata

PHASE_NAME   = "phase6d_biology_test"
MULT         = 1.10   # Relaxed from Phase 6c (1.25) — gives infants more survival time
SCATTER      = 2
INIT_CARE    = 0.30
INIT_FORAGE  = 1.0
INIT_SELF    = 0.70
INIT_DS      = 0.005  # distress_sensitivity starting value (cortisol analog)
INIT_CR      = 0.40   # care_recovery starting value (prolactin analog)
PLASTIC_GAIN = 5.0
MIN_OLD      = 100
SNAPSHOT_INTERVAL = 200


def _make_genomes(n: int) -> list[Genome]:
    return [
        Genome(
            care_weight=INIT_CARE,
            forage_weight=INIT_FORAGE,
            self_weight=INIT_SELF,
            distress_sensitivity=INIT_DS,
            care_recovery=INIT_CR,
        )
        for _ in range(n)
    ]


def _pearson_r(birth_log_path: str):
    if not os.path.exists(birth_log_path):
        return None
    with open(birth_log_path) as f:
        rows = list(csv.DictReader(f))
    if len(rows) < 10:
        return None
    cw   = [float(r["mother_care_weight"]) for r in rows]
    gens = [float(r["mother_generation"])  for r in rows]
    n = len(cw)
    mc, mg = sum(cw) / n, sum(gens) / n
    num = sum((cw[i] - mc) * (gens[i] - mg) for i in range(n))
    dc  = sum((x - mc) ** 2 for x in cw) ** 0.5
    dg  = sum((x - mg) ** 2 for x in gens) ** 0.5
    return num / (dc * dg) if dc and dg else None


def _build_config(seed: int) -> Config:
    cfg = Config()
    cfg.seed          = seed
    cfg.width         = 50
    cfg.height        = 50
    cfg.init_mothers  = 40
    cfg.init_food     = 120
    cfg.max_ticks     = 10_000

    cfg.infant_starvation_multiplier = MULT
    cfg.birth_scatter_radius         = SCATTER
    cfg.plastic_gain                 = PLASTIC_GAIN

    cfg.children_enabled           = True
    cfg.care_enabled               = True
    cfg.plasticity_enabled         = True
    cfg.plasticity_kin_conditional = True
    cfg.reproduction_enabled       = True
    cfg.mutation_enabled           = True
    return cfg


def run_phase6d(seed: int = 42) -> str:
    """Run Phase 6d single seed. Returns output_dir."""
    config = _build_config(seed)
    set_seed(seed)

    output_dir = create_run_dir(PHASE_NAME, seed)
    save_config(config, output_dir)
    save_metadata(
        output_dir,
        phase=PHASE_NAME,
        seed=seed,
        num_agents=config.init_mothers * 2,
        grid_size=[config.width, config.height],
        plasticity_enabled=True,
        plasticity_kin_conditional=True,
        infant_starvation_multiplier=MULT,
        birth_scatter_radius=SCATTER,
        init_care=INIT_CARE,
        init_distress_sensitivity=INIT_DS,
        init_care_recovery=INIT_CR,
        note=(
            "Phase 6d: identical to Phase 6c (Options A+D) but MLE lowered from "
            "1.25 to 1.10 to reduce demographic collapse. Tests whether the Baldwin "
            "mechanism can complete genetic assimilation with less ecology pressure."
        ),
    )

    genomes = _make_genomes(config.init_mothers)
    sim = Simulation(config)
    sim.initialize(genomes)

    generation_snapshots = []

    while sim.tick < config.max_ticks:
        sim.step()
        sim.tick += 1

        if sim.tick % SNAPSHOT_INTERVAL == 0:
            alive = [m for m in sim.mothers if m.alive]
            if not alive:
                break
            old            = [m for m in alive if m.age >= MIN_OLD] or alive
            alive_children = [c for c in sim.children if c.alive]

            generation_snapshots.append({
                "tick":                      sim.tick,
                "n_mothers":                 len(alive),
                "n_old_mothers":             len(old),
                "n_children":                len(alive_children),
                "avg_care_weight":           sum(m.genome.care_weight           for m in alive) / len(alive),
                "min_care_weight":           min(m.genome.care_weight           for m in alive),
                "max_care_weight":           max(m.genome.care_weight           for m in alive),
                "avg_forage_weight":         sum(m.genome.forage_weight         for m in alive) / len(alive),
                "avg_self_weight":           sum(m.genome.self_weight           for m in alive) / len(alive),
                "avg_learning_rate":         sum(m.genome.learning_rate         for m in alive) / len(alive),
                "avg_learning_cost":         sum(m.genome.learning_cost         for m in alive) / len(alive),
                "avg_distress_sensitivity":  sum(m.genome.distress_sensitivity  for m in alive) / len(alive),
                "min_distress_sensitivity":  min(m.genome.distress_sensitivity  for m in alive),
                "max_distress_sensitivity":  max(m.genome.distress_sensitivity  for m in alive),
                "avg_care_recovery":         sum(m.genome.care_recovery         for m in alive) / len(alive),
                "min_care_recovery":         min(m.genome.care_recovery         for m in alive),
                "max_care_recovery":         max(m.genome.care_recovery         for m in alive),
                "avg_generation":            sum(m.generation                   for m in alive) / len(alive),
                "max_generation":            max(m.generation                   for m in alive),
                "avg_mother_energy":         sum(m.energy                       for m in alive) / len(alive),
                "avg_child_hunger":          (sum(c.hunger for c in alive_children) / len(alive_children)
                                              if alive_children else 0.0),
                "avg_expressed_care_weight": sum(m.expressed_care_weight        for m in old) / len(old),
                "avg_care_weight_old":       sum(m.genome.care_weight           for m in old) / len(old),
            })

    sim.logger.save_all(output_dir)
    with open(os.path.join(output_dir, "generation_snapshots.json"), "w") as f:
        json.dump(generation_snapshots, f, indent=2)

    alive     = [m for m in sim.mothers if m.alive]
    n         = len(alive)
    final_cw  = sum(m.genome.care_weight          for m in alive) / n if n else 0.0
    final_ecw = sum(m.expressed_care_weight        for m in alive) / n if n else 0.0
    final_lr  = sum(m.genome.learning_rate         for m in alive) / n if n else 0.0
    final_ds  = sum(m.genome.distress_sensitivity  for m in alive) / n if n else 0.0
    final_cr  = sum(m.genome.care_recovery         for m in alive) / n if n else 0.0
    grad_r    = _pearson_r(os.path.join(output_dir, "birth_log.csv"))

    survived = n >= 10
    print(f"\n[phase6d] seed={seed}  Output: {output_dir}")
    print(f"  Surviving mothers         : {n}  ({'SURVIVED' if survived else 'EXTINCT'})")
    print(f"  Final care_weight [genetic]     : {final_cw:.4f}  (start: {INIT_CARE})")
    print(f"  Final expressed_care [phenotypic]: {final_ecw:.4f}")
    print(f"  Final learning_rate             : {final_lr:.4f}  (start: 0.1000)")
    print(f"  Final distress_sensitivity      : {final_ds:.4f}  (start: {INIT_DS})")
    print(f"  Final care_recovery             : {final_cr:.4f}  (start: {INIT_CR})")
    if grad_r is not None:
        print(f"  Pearson r (birth)               : {grad_r:+.4f}")
    else:
        print(f"  Pearson r (birth)               : N/A")

    return output_dir


if __name__ == "__main__":
    run_phase6d(seed=42)
