# experiments/phase7_instinct_test/run.py
"""Phase 7 — Zero-Shot Instinct Test

Two-stage single continuous run:
  Stage 1 (ticks     0 - 5000): plasticity ON  (kin-conditional)
    Natural selection + plasticity should drive genetic care_weight upward.
    Learning_rate should be positively selected (assimilation signal).

  Stage 2 (ticks 5001 - 10000): plasticity OFF (zero-shot)
    Plasticity is disabled mid-run. No code resets expressed_care_weight.
    Mothers keep whatever expressed value they accumulated.
    Key question: does the population STILL survive on genetic care_weight alone?
    If yes => care behaviour has been encoded as instinct (Baldwin Effect complete).

Ecology: MLE_MULT (Minimum Lethal Ecology from Phase 5 sweep).
  *** UPDATE MLE_MULT AFTER PHASE 5 SWEEP COMPLETES ***

Genome: Phase 3 canonical — care=0.30, forage=1.0, self=0.70.
Spatial: 50x50 grid, 40 mothers, 120 food, scatter=2.
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

# *** UPDATE THIS after Phase 5 sweep gives the MLE ***
MLE_MULT        = 1.25   # confirmed by Phase 5 sweep (2026-05-01)

STAGE1_TICKS    = 5_000   # plasticity ON
STAGE2_TICKS    = 5_000   # plasticity OFF  (zero-shot)
TOTAL_TICKS     = STAGE1_TICKS + STAGE2_TICKS

INIT_CARE       = 0.30
INIT_FORAGE     = 1.0
INIT_SELF       = 0.70
SCATTER         = 2
PLASTIC_GAIN    = 5.0
MIN_OLD         = 100     # min age (ticks) for old-mother filter
SNAPSHOT_INTERVAL = 200


def _make_genomes(n: int) -> list:
    return [Genome(care_weight=INIT_CARE, forage_weight=INIT_FORAGE, self_weight=INIT_SELF)
            for _ in range(n)]


def _build_config(seed: int) -> Config:
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

    cfg.children_enabled             = True
    cfg.care_enabled                 = True
    cfg.plasticity_enabled           = True    # Stage 1 starts with plasticity ON
    cfg.plasticity_kin_conditional   = True
    cfg.reproduction_enabled         = True
    cfg.mutation_enabled             = True
    return cfg


def run_phase7(seed: int = 42) -> str:
    """Run Phase 7 single seed. Returns output_dir."""
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
        mle_mult=MLE_MULT,
        stage1_ticks=STAGE1_TICKS,
        stage2_ticks=STAGE2_TICKS,
        note=(
            f"Two-stage zero-shot test at MLE={MLE_MULT}. "
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
        # Switch to Stage 2 at the boundary
        if sim.tick == STAGE1_TICKS and sim.config.plasticity_enabled:
            sim.config.plasticity_enabled = False
            print(f"  [seed={seed}] tick={sim.tick} — Stage 2 START: plasticity OFF")

        sim.step()
        sim.tick += 1

        if sim.tick % SNAPSHOT_INTERVAL == 0:
            alive = [m for m in sim.mothers if m.alive]
            if not alive:
                break   # extinct — stop early
            stage = 1 if sim.tick <= STAGE1_TICKS else 2
            old   = [m for m in alive if m.age >= MIN_OLD] or alive
            alive_children = [c for c in sim.children if c.alive]

            generation_snapshots.append({
                "tick":                      sim.tick,
                "stage":                     stage,
                "plasticity_on":             (stage == 1),
                "n_mothers":                 len(alive),
                "n_old_mothers":             len(old),
                "n_children":                len(alive_children),
                # genetic — all alive mothers
                "avg_care_weight":           sum(m.genome.care_weight     for m in alive) / len(alive),
                "min_care_weight":           min(m.genome.care_weight     for m in alive),
                "max_care_weight":           max(m.genome.care_weight     for m in alive),
                "avg_forage_weight":         sum(m.genome.forage_weight   for m in alive) / len(alive),
                "avg_learning_rate":         sum(m.genome.learning_rate   for m in alive) / len(alive),
                "avg_learning_cost":         sum(m.genome.learning_cost   for m in alive) / len(alive),
                "avg_generation":            sum(m.generation             for m in alive) / len(alive),
                "max_generation":            max(m.generation             for m in alive),
                "avg_mother_energy":         sum(m.energy                 for m in alive) / len(alive),
                "avg_child_energy":          (sum(c.energy for c in alive_children) / len(alive_children)
                                              if alive_children else 0.0),
                # phenotypic — old mothers only
                "avg_expressed_care_weight": sum(m.expressed_care_weight  for m in old) / len(old),
                "avg_care_weight_old":       sum(m.genome.care_weight     for m in old) / len(old),
            })

    sim.logger.save_all(output_dir)
    with open(os.path.join(output_dir, "generation_snapshots.json"), "w") as f:
        json.dump(generation_snapshots, f, indent=2)

    alive     = [m for m in sim.mothers if m.alive]
    n         = len(alive)
    final_cw  = sum(m.genome.care_weight    for m in alive) / n if n else 0.0
    final_ecw = sum(m.expressed_care_weight for m in alive) / n if n else 0.0
    final_lr  = sum(m.genome.learning_rate  for m in alive) / n if n else 0.0
    survived  = n >= 10

    # Find Stage 2 entry stats (last snapshot at stage boundary)
    s2_entry = next((s for s in reversed(generation_snapshots) if s["stage"] == 1), None)
    entry_cw = s2_entry["avg_care_weight"] if s2_entry else None

    print(f"\n[Phase 7] seed={seed}  Output: {output_dir}")
    print(f"  Stage 2 survival : {n} mothers  ({'SURVIVED' if survived else 'EXTINCT'})")
    print(f"  care_weight at Stage 2 entry : {entry_cw:.4f}" if entry_cw else "  care_weight at Stage 2 entry : N/A")
    print(f"  Final care_weight (genetic)  : {final_cw:.4f}  (Phase 3 start: {INIT_CARE})")
    print(f"  Final expressed_care         : {final_ecw:.4f}")
    print(f"  Final learning_rate          : {final_lr:.4f}  (Genome start: 0.1000)")

    instinct_confirmed = survived and final_cw > INIT_CARE
    print(f"  Instinct confirmed?          : {'YES' if instinct_confirmed else 'NO'}")

    return output_dir


if __name__ == "__main__":
    run_phase7(seed=42)
