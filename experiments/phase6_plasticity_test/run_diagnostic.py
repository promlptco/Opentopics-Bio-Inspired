# experiments/phase6_plasticity_test/run_diagnostic.py
"""Quick parameter scan for Phase 6 ecology calibration.

Tests mult=1.10 and mult=1.15 with kin_cond=True vs False (gain=2.0, 5000 ticks, seed=42).
Goal: confirm which mult gives  kin_cond=True survives, kin_cond=False degrades.
"""
import sys, os
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, PROJECT_ROOT)

from experiments.phase6_plasticity_test.run import _build_config, _make_phase3_canonical_genomes
from simulation.simulation import Simulation
from utils.experiment import set_seed

TESTS = [
    # (mult, kin_conditional, label)
    (1.10, True,  "mult=1.10 kin_cond=True "),
    (1.10, False, "mult=1.10 kin_cond=False"),
    (1.15, True,  "mult=1.15 kin_cond=True "),
    (1.15, False, "mult=1.15 kin_cond=False"),
    (1.15, None,  "mult=1.15 no-plasticity "),   # None = plasticity OFF
]
TICKS = 5_000
SEED  = 42

print(f"\n=== Phase 6 Quick Diagnostic ({TICKS} ticks, seed={SEED}) ===\n")
print(f"  {'Config':38s}  {'pop':>4}  {'genetic_cw':>10}  {'expressed_cw':>12}  {'lr':>7}")
print("-" * 82)

for mult, kin, label in TESTS:
    set_seed(SEED)
    kin_bool = bool(kin) if kin is not None else False
    config = _build_config(SEED, kin_bool)
    config.infant_starvation_multiplier = mult
    config.max_ticks = TICKS
    if kin is None:
        config.plasticity_enabled = False

    genomes = _make_phase3_canonical_genomes(config.init_mothers)
    sim = Simulation(config)
    sim.initialize(genomes)

    while sim.tick < TICKS:
        sim.step()
        sim.tick += 1

    alive = [m for m in sim.mothers if m.alive]
    n    = len(alive)
    gcw  = sum(m.genome.care_weight    for m in alive) / n if n else 0.0
    ecw  = sum(m.expressed_care_weight for m in alive) / n if n else 0.0
    lr   = sum(m.genome.learning_rate  for m in alive) / n if n else 0.0

    print(f"  {label:38s}  pop={n:>3}  genetic_cw={gcw:.4f}  expressed_cw={ecw:.4f}  lr={lr:.4f}")

print()
