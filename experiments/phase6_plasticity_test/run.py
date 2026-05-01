# experiments/phase6_plasticity_test/run.py
"""Phase 6 — Plasticity / Baldwin Effect

Phase 5 showed that populations starting from the Phase 3 canonical genome
(care=0.30) go extinct under ecological pressure (mult=1.65, scatter=2)
because pure Darwinian selection cannot shift the genome fast enough to
cross the bistability threshold before collapse.

Baldwin Effect hypothesis:
  Kin-conditional phenotypic plasticity allows mothers to express higher care
  when their own infant is distressed. This raises effective infant survival
  rate, slowing extinction and buying generations for genetic selection to
  encode care_weight above the bistability threshold. Learning_rate should
  be positively selected as a genetic assimilation signature.

Two conditions (same ecology, differ only in plasticity wiring):
  phase6a — kin_conditional=True  : plasticity fires only on own-child care events.
                                    Signal aligned with inclusive fitness. Proper test.
  phase6b — kin_conditional=False : plasticity fires on all care events.
                                    Signal anti-correlated with fitness. Null control.

Ecology (identical to Phase 5 — the only change is plasticity_enabled=True):
  infant_starvation_multiplier = 1.65
  birth_scatter_radius         = 2
  care_weight init              = 0.30  (Phase 3 canonical)
  forage_weight init            = 1.0
  self_weight init              = 0.70
  grid = 50x50, init_mothers = 40, init_food = 120, max_ticks = 10,000

Primary metrics:
  1. Population survival  (Phase 5 = extinct; Phase 6 target = >=10 mothers)
  2. Pearson r(care_weight, generation) from birth_log  (Phase 5 = N/A)
  3. Final mean care_weight  (Phase 5 = 0.0 fallback; Phase 6 target = > 0.30)
  4. Learning_rate trajectory  (positive selection = genetic assimilation signal)
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

PHASE_NAME        = "phase6_plasticity_test"
MULT              = 1.25   # MLE confirmed by Phase 5 sweep (2026-05-01)
SCATTER           = 2
INIT_CARE         = 0.30
INIT_FORAGE       = 1.0
INIT_SELF         = 0.70
PLASTIC_GAIN      = 5.0   # raised from 2.0 — makes expressed-genetic gap clearly visible
MIN_OLD           = 100   # min mother age (ticks) for plastic-gap snapshot; removes birth-reset artifact
SNAPSHOT_INTERVAL = 200


def _make_phase3_canonical_genomes(n: int) -> list[Genome]:
    return [Genome(care_weight=INIT_CARE, forage_weight=INIT_FORAGE, self_weight=INIT_SELF)
            for _ in range(n)]


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


def _build_config(seed: int, kin_conditional: bool) -> Config:
    config = Config()
    config.seed          = seed
    config.width         = 50
    config.height        = 50
    config.init_mothers  = 40
    config.init_food     = 120
    config.max_ticks     = 10_000

    config.infant_starvation_multiplier = MULT
    config.birth_scatter_radius         = SCATTER
    config.plastic_gain                 = PLASTIC_GAIN

    config.children_enabled           = True
    config.care_enabled               = True
    config.plasticity_enabled         = True
    config.plasticity_kin_conditional = kin_conditional
    config.reproduction_enabled       = True
    config.mutation_enabled           = True
    return config


def run_evolution(seed: int = 42, kin_conditional: bool = True) -> str:
    """Run Phase 6 single seed. Returns output_dir."""
    stage  = "phase6a_kin_conditional" if kin_conditional else "phase6b_blind_control"
    config = _build_config(seed, kin_conditional)

    set_seed(seed)
    output_dir = create_run_dir(PHASE_NAME, seed)
    save_config(config, output_dir)
    save_metadata(
        output_dir,
        phase=PHASE_NAME,
        stage=stage,
        seed=seed,
        num_agents=config.init_mothers * 2,
        grid_size=[config.width, config.height],
        plasticity_enabled=True,
        plasticity_kin_conditional=kin_conditional,
        infant_starvation_multiplier=MULT,
        birth_scatter_radius=SCATTER,
        init_care=INIT_CARE,
        note=(
            "Phase 3 canonical init (care=0.30). Kin-conditional plasticity — "
            "Baldwin Effect test: can plasticity bridge the Phase 5 extinction gap?"
            if kin_conditional else
            "Phase 3 canonical init (care=0.30). Lineage-blind plasticity — "
            "null control: signal anti-correlated with inclusive fitness."
        ),
    )

    genomes = _make_phase3_canonical_genomes(config.init_mothers)
    sim = Simulation(config)
    sim.initialize(genomes)

    generation_snapshots = []

    while sim.tick < config.max_ticks:
        sim.step()
        sim.tick += 1

        if sim.tick % SNAPSHOT_INTERVAL == 0:
            alive = [m for m in sim.mothers if m.alive]
            if alive:
                # old mothers (age >= MIN_OLD) have had time to accumulate plastic updates.
                # Using them for expressed_care_weight removes the birth-reset artifact.
                old   = [m for m in alive if m.age >= MIN_OLD] or alive
                alive_children = [c for c in sim.children if c.alive]
                generation_snapshots.append({
                    "tick":                          sim.tick,
                    "n_mothers":                     len(alive),
                    "n_old_mothers":                 len(old),
                    "n_children":                    len(alive_children),
                    # genetic weights — all alive mothers
                    "avg_care_weight":               sum(m.genome.care_weight         for m in alive) / len(alive),
                    "min_care_weight":               min(m.genome.care_weight         for m in alive),
                    "max_care_weight":               max(m.genome.care_weight         for m in alive),
                    "avg_forage_weight":             sum(m.genome.forage_weight       for m in alive) / len(alive),
                    "avg_self_weight":               sum(m.genome.self_weight         for m in alive) / len(alive),
                    "avg_learning_rate":             sum(m.genome.learning_rate       for m in alive) / len(alive),
                    "min_learning_rate":             min(m.genome.learning_rate       for m in alive),
                    "max_learning_rate":             max(m.genome.learning_rate       for m in alive),
                    "avg_learning_cost":             sum(m.genome.learning_cost       for m in alive) / len(alive),
                    "avg_generation":                sum(m.generation                 for m in alive) / len(alive),
                    "max_generation":                max(m.generation                 for m in alive),
                    "avg_mother_energy":             sum(m.energy                     for m in alive) / len(alive),
                    "avg_child_energy":              sum(c.energy for c in alive_children) / len(alive_children) if alive_children else 0.0,
                    # phenotypic — old mothers only (artifact-free)
                    "avg_expressed_care_weight":     sum(m.expressed_care_weight      for m in old) / len(old),
                    "avg_care_weight_old":           sum(m.genome.care_weight         for m in old) / len(old),
                })

    sim.logger.save_all(output_dir)
    with open(os.path.join(output_dir, "generation_snapshots.json"), "w") as f:
        json.dump(generation_snapshots, f, indent=2)

    alive        = [m for m in sim.mothers if m.alive]
    n            = len(alive)
    final_cw     = sum(m.genome.care_weight       for m in alive) / n if n else 0.0
    final_ecw    = sum(m.expressed_care_weight    for m in alive) / n if n else 0.0
    final_lr     = sum(m.genome.learning_rate     for m in alive) / n if n else 0.0
    grad_r       = _pearson_r(os.path.join(output_dir, "birth_log.csv"))

    survived = n >= 10
    print(f"\n[{stage}] seed={seed}  Output: {output_dir}")
    print(f"  Surviving mothers    : {n}  ({'SURVIVED' if survived else 'EXTINCT'})")
    print(f"  Final care_weight    : {final_cw:.4f}  [genetic]  (Phase 3 start: {INIT_CARE})")
    print(f"  Final expressed_care : {final_ecw:.4f}  [phenotypic]")
    print(f"  Final learn_rate     : {final_lr:.4f}  [genetic]  (Genome start: 0.1000)")
    if grad_r is not None:
        print(f"  Pearson r (birth) : {grad_r:+.4f}")
    else:
        print(f"  Pearson r (birth) : N/A (insufficient births — likely extinct)")
    return output_dir


if __name__ == "__main__":
    run_evolution(seed=42, kin_conditional=True)
