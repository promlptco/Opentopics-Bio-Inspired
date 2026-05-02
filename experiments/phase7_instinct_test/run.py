# experiments/phase7_instinct_test/run.py
"""Phase 7 — Zero-Shot Instinct Test

Two-stage single continuous run starting from Phase 6d evolved genomes:
  Stage 1 (ticks      0 - 15000): plasticity ON  (kin-conditional)
    Population runs with evolved care_weight + DS + CR.
    Plasticity boosts expressed_care above the genetic floor.

  Stage 2 (ticks 15001 - 20000): plasticity OFF (zero-shot)
    Plasticity disabled mid-run. expressed_care freezes, then gradually
    converges to genome value as old mothers are replaced by offspring.
    Key question: does the population STILL survive on genetic care alone?
    If yes => care behaviour is encoded as instinct (Baldwin Effect complete).

Ecology : MLE=1.10 (matching Phase 6d).
Genomes : Phase 6d mean final values — care=0.325, DS=0.068, CR=0.410,
          learning_rate=0.136 — so Stage 1 starts where Phase 6d ended.
"""
import sys
import os
import json

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, PROJECT_ROOT)

from config import Config
from simulation.simulation import Simulation
from evolution.genome import Genome
from utils.experiment import set_seed, create_run_dir, save_config, save_metadata

PHASE_NAME      = "phase7_instinct_test"

MLE_MULT        = 1.10   # matches Phase 6d

STAGE1_TICKS    = 15_000
STAGE2_TICKS    = 5_000
TOTAL_TICKS     = STAGE1_TICKS + STAGE2_TICKS

# Phase 6d mean final genome values (averaged across 10 surviving seeds)
INIT_CARE       = 0.325
INIT_FORAGE     = 1.0
INIT_SELF       = 0.70
INIT_DS         = 0.068   # distress_sensitivity (cortisol analog)
INIT_CR         = 0.410   # care_recovery (prolactin analog)
INIT_LR         = 0.136   # learning_rate
INIT_LC         = 0.099   # learning_cost (genome.learning_cost evolved from 0.05 default)

SCATTER         = 2
PLASTIC_GAIN    = 5.0
MIN_OLD         = 100
SNAPSHOT_INTERVAL = 100   # tight interval for a smooth graph


def _make_genomes(n: int, learning_cost: float = INIT_LC) -> list:
    return [
        Genome(
            care_weight=INIT_CARE,
            forage_weight=INIT_FORAGE,
            self_weight=INIT_SELF,
            distress_sensitivity=INIT_DS,
            care_recovery=INIT_CR,
            learning_rate=INIT_LR,
            learning_cost=learning_cost,
        )
        for _ in range(n)
    ]


def _build_config(seed: int, plasticity_energy_cost: float = 0.0) -> Config:
    cfg = Config()
    cfg.seed          = seed
    cfg.width         = 50
    cfg.height        = 50
    cfg.init_mothers  = 40
    cfg.init_food     = 120
    cfg.max_ticks     = TOTAL_TICKS

    cfg.infant_starvation_multiplier = MLE_MULT
    cfg.birth_scatter_radius         = SCATTER
    cfg.plastic_gain                 = PLASTIC_GAIN
    cfg.plasticity_energy_cost       = plasticity_energy_cost

    cfg.children_enabled           = True
    cfg.care_enabled               = True
    cfg.plasticity_enabled         = True    # Stage 1 starts ON
    cfg.plasticity_kin_conditional = True
    cfg.reproduction_enabled       = True
    cfg.mutation_enabled           = True
    return cfg


def run_phase7(seed: int = 42, plasticity_energy_cost: float = 0.0) -> str:
    """Run Phase 7 single seed. Returns output_dir."""
    config = _build_config(seed, plasticity_energy_cost=plasticity_energy_cost)
    set_seed(seed)

    output_dir = create_run_dir(PHASE_NAME, seed)
    save_config(config, output_dir)
    save_metadata(
        output_dir,
        phase=PHASE_NAME,
        seed=seed,
        num_agents=config.init_mothers * 2,
        grid_size=[config.width, config.height],
        mle_mult=MLE_MULT,
        stage1_ticks=STAGE1_TICKS,
        stage2_ticks=STAGE2_TICKS,
        init_care=INIT_CARE,
        init_distress_sensitivity=INIT_DS,
        init_care_recovery=INIT_CR,
        init_learning_rate=INIT_LR,
        note=(
            f"Phase 7 zero-shot instinct test at MLE={MLE_MULT}. "
            f"Genomes initialised from Phase 6d mean final values. "
            f"Stage 1 (0-{STAGE1_TICKS}): plasticity ON. "
            f"Stage 2 ({STAGE1_TICKS}-{TOTAL_TICKS}): plasticity OFF. "
            "Survival in Stage 2 => genetic assimilation (instinct)."
        ),
    )

    genomes = _make_genomes(config.init_mothers)
    sim = Simulation(config)
    sim.initialize(genomes)

    generation_snapshots = []

    while sim.tick < TOTAL_TICKS:
        if sim.tick == STAGE1_TICKS and sim.config.plasticity_enabled:
            sim.config.plasticity_enabled = False
            print(f"  [seed={seed}] tick={sim.tick} — Stage 2 START: plasticity OFF")

        sim.step()
        sim.tick += 1

        # Discard per-event records every 1000 ticks — Phase 7 only needs snapshots.
        if sim.tick % 1000 == 0:
            sim.logger.choice_records.clear()
            sim.logger.care_records.clear()
            sim.logger.death_records.clear()
            sim.logger.birth_records.clear()

        if sim.tick % SNAPSHOT_INTERVAL == 0:
            alive = [m for m in sim.mothers if m.alive]
            if not alive:
                break
            stage          = 1 if sim.tick <= STAGE1_TICKS else 2
            old            = [m for m in alive if m.age >= MIN_OLD] or alive
            alive_children = [c for c in sim.children if c.alive]

            generation_snapshots.append({
                "tick":                      sim.tick,
                "stage":                     stage,
                "plasticity_on":             (stage == 1),
                "n_mothers":                 len(alive),
                "n_old_mothers":             len(old),
                "n_children":                len(alive_children),
                # genetic
                "avg_care_weight":           sum(m.genome.care_weight          for m in alive) / len(alive),
                "min_care_weight":           min(m.genome.care_weight          for m in alive),
                "max_care_weight":           max(m.genome.care_weight          for m in alive),
                "avg_forage_weight":         sum(m.genome.forage_weight        for m in alive) / len(alive),
                "avg_learning_rate":         sum(m.genome.learning_rate        for m in alive) / len(alive),
                "avg_learning_cost":         sum(m.genome.learning_cost        for m in alive) / len(alive),
                "avg_distress_sensitivity":  sum(m.genome.distress_sensitivity for m in alive) / len(alive),
                "avg_care_recovery":         sum(m.genome.care_recovery        for m in alive) / len(alive),
                "avg_generation":            sum(m.generation                  for m in alive) / len(alive),
                "max_generation":            max(m.generation                  for m in alive),
                "avg_mother_energy":         sum(m.energy                      for m in alive) / len(alive),
                "avg_child_hunger":          (sum(c.hunger for c in alive_children) / len(alive_children)
                                              if alive_children else 0.0),
                # phenotypic — ALL alive mothers (used for Baldwin graph)
                "avg_expressed_care_weight": sum(m.expressed_care_weight       for m in alive) / len(alive),
                # phenotypic — old mothers only (for reference)
                "avg_expressed_care_weight_old": sum(m.expressed_care_weight   for m in old) / len(old),
                "avg_care_weight_old":       sum(m.genome.care_weight          for m in old) / len(old),
            })

    with open(os.path.join(output_dir, "generation_snapshots.json"), "w") as f:
        json.dump(generation_snapshots, f, indent=2)

    alive     = [m for m in sim.mothers if m.alive]
    n         = len(alive)
    final_cw  = sum(m.genome.care_weight    for m in alive) / n if n else 0.0
    final_ecw = sum(m.expressed_care_weight for m in alive) / n if n else 0.0
    final_lr  = sum(m.genome.learning_rate  for m in alive) / n if n else 0.0
    survived  = n >= 10

    s2_entry = next((s for s in reversed(generation_snapshots) if s["stage"] == 1), None)
    entry_cw = s2_entry["avg_care_weight"] if s2_entry else None
    entry_ecw = s2_entry["avg_expressed_care_weight"] if s2_entry else None

    print(f"\n[Phase 7] seed={seed}  Output: {output_dir}")
    print(f"  Stage 2 survival             : {n} mothers  ({'SURVIVED' if survived else 'EXTINCT'})")
    if entry_cw is not None:
        print(f"  care_weight at Stage 2 entry : {entry_cw:.4f}  (expressed: {entry_ecw:.4f})")
    print(f"  Final care_weight (genetic)  : {final_cw:.4f}  (Phase 6d start: {INIT_CARE})")
    print(f"  Final expressed_care         : {final_ecw:.4f}")
    print(f"  Final learning_rate          : {final_lr:.4f}  (Phase 6d start: {INIT_LR:.4f})")

    instinct_confirmed = survived and final_cw >= INIT_CARE
    print(f"  Instinct confirmed?          : {'YES' if instinct_confirmed else 'NO'}")

    return output_dir


if __name__ == "__main__":
    run_phase7(seed=42)
