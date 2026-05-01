# experiments/phase6c_biology_test/run.py
"""Phase 6c — Combined Biological Instinct Variables (Options A + D)

Phase 6a showed that kin-conditional plasticity alone (plastic_gain=5.0) cannot
rescue the population at MLE=1.25.  Root cause: high care frequency depletes
mother energy below reproduction_threshold (0.95) → reproductive failure.

This phase adds two new heritable genome parameters that directly fix the energy
economics and create a stronger selection gradient toward care:

  Option A — distress_sensitivity  (cortisol analog)
    When a mother ignores her own distressed infant (chooses FORAGE or SELF while
    her own child is nearby and distressed), she pays an energy penalty:
        penalty = distress_sensitivity * own_child.distress  (per tick)
    Makes NOT caring metabolically costly → selection drives distress_sensitivity
    and care_weight upward together.

  Option D — care_recovery  (prolactin analog)
    Each successful feeding of own infant returns energy:
        recovered = care_recovery * hunger_reduced
    Offsets feed_cost (0.03), making care energetically self-sustaining at high
    care frequency → population can survive long enough for genetic assimilation.

Combined effect: ignoring is doubly punished (child dies + cortisol cost) while
caring is energetically viable (prolactin recovery).  Both genes are heritable
and mutate identically to care_weight.  Default = 0.0 in Genome dataclass, so
all prior Phase 1–6 results are unaffected.

Ecology: identical to Phase 6 (MLE=1.25, scatter=2, care_init=0.30).
Initial gene values: distress_sensitivity=0.10, care_recovery=0.10.
Plasticity: kin-conditional ON (same as Phase 6a — proper Baldwin Effect test).
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

PHASE_NAME   = "phase6c_biology_test"
MULT         = 1.25   # MLE confirmed by Phase 5 sweep (2026-05-01)
SCATTER      = 2
INIT_CARE    = 0.30
INIT_FORAGE  = 1.0
INIT_SELF    = 0.70
INIT_DS      = 0.005  # distress_sensitivity starting value (cortisol — very gentle, evolves up)
INIT_CR      = 0.40   # care_recovery starting value (prolactin — net +0.05 energy per feeding)
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


def run_phase6c(seed: int = 42) -> str:
    """Run Phase 6c single seed. Returns output_dir."""
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
            "Phase 6c: combined Option A (distress_sensitivity cortisol-analog) + "
            "Option D (care_recovery prolactin-analog). Addresses Phase 6a energy "
            "depletion failure. Both genes heritable and mutable."
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
                # domain weights
                "avg_care_weight":           sum(m.genome.care_weight           for m in alive) / len(alive),
                "min_care_weight":           min(m.genome.care_weight           for m in alive),
                "max_care_weight":           max(m.genome.care_weight           for m in alive),
                "avg_forage_weight":         sum(m.genome.forage_weight         for m in alive) / len(alive),
                "avg_self_weight":           sum(m.genome.self_weight           for m in alive) / len(alive),
                # plasticity genes
                "avg_learning_rate":         sum(m.genome.learning_rate         for m in alive) / len(alive),
                "avg_learning_cost":         sum(m.genome.learning_cost         for m in alive) / len(alive),
                # new biological genes
                "avg_distress_sensitivity":  sum(m.genome.distress_sensitivity  for m in alive) / len(alive),
                "min_distress_sensitivity":  min(m.genome.distress_sensitivity  for m in alive),
                "max_distress_sensitivity":  max(m.genome.distress_sensitivity  for m in alive),
                "avg_care_recovery":         sum(m.genome.care_recovery         for m in alive) / len(alive),
                "min_care_recovery":         min(m.genome.care_recovery         for m in alive),
                "max_care_recovery":         max(m.genome.care_recovery         for m in alive),
                # population state
                "avg_generation":            sum(m.generation                   for m in alive) / len(alive),
                "max_generation":            max(m.generation                   for m in alive),
                "avg_mother_energy":         sum(m.energy                       for m in alive) / len(alive),
                "avg_child_hunger":          (sum(c.hunger for c in alive_children) / len(alive_children)
                                              if alive_children else 0.0),
                # phenotypic — old mothers only
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
    print(f"\n[phase6c] seed={seed}  Output: {output_dir}")
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
    run_phase6c(seed=42)
