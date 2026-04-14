# experiments/p6_controls_and_baldwin/p6c_depleted_baseline/run.py
"""Phase 10: Depleted-Init Baseline Zero-Shot

Scientific purpose:
  PHASE3_ZS_BASELINE (0.09069) was measured from HIGH-CARE evolved genomes
  (care_weight ≈ 0.43 after Phase 3 erosion). Phases P6a/P6b evolved from a
  DEPLETED init (cw~U(0, 0.50), mean≈0.25). A fair zero-shot comparison for
  P6a/P6b requires a baseline from the same depleted starting point.

  This script provides that baseline:
    - No evolution: fresh depleted genomes (no loading from any evolved run)
    - mult=1.15, scatter=2  (same ecology as P5/P6b so baseline is ecologically matched)
    - 1000 ticks, plast=OFF, mut=OFF, repro=OFF
    - Output metric: care_window_rate = successful care events / alive-mother-ticks,
      ticks 0–100  (matches the window used for PHASE3_ZS_BASELINE)

  Result stored in zeroshot_metrics.json as 'care_window_rate'.
  Update shared/constants.py with DEPLETED_ZS_BASELINE after running.

Key comparisons:
  PHASE3_ZS_BASELINE : 0.09069  (high-care genomes, Phase 3 erosion end)
  Phase 10 baseline  : ???       (depleted genomes — this script)
  P6b zero-shot rate : ???       (evolved under mult=1.0 scatter=2 — from p6b run_zeroshot)
"""
import sys
import os
import json
import random as _random

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, PROJECT_ROOT)

from config import Config
from simulation.simulation import Simulation
from evolution.genome import Genome
from utils.experiment import set_seed, create_run_dir, save_config, save_metadata
from utils.plotting import generate_all_plots

PHASE_NAME = "phase10_depleted_baseline"

# Ecological parameters — matched to P5/P6b so the baseline is ecologically comparable
INFANT_STARVATION_MULT = 1.15  # same as P5 (Phase 07)
BIRTH_SCATTER_RADIUS   = 2     # same as P5 (Phase 07)

# Window for care rate — must match PHASE3_ZS_BASELINE window
CARE_WINDOW_END = 100  # ticks 0–100 (= one maturity cycle)


def _make_depleted_genomes(n: int) -> list[Genome]:
    """Fresh depleted-care genomes — same init as P5/P6a/P6b evolution.

    care_weight ~ U(0.00, 0.50), mean≈0.25
    Below Phase 3 eroded equilibrium (0.42) — represents random naive agents.
    """
    return [
        Genome(
            care_weight=_random.uniform(0.0, 0.50),
            forage_weight=_random.uniform(0.0, 1.0),
            self_weight=_random.uniform(0.0, 1.0),
        )
        for _ in range(n)
    ]


def _care_window_rate(care_records, population_history: list[int], window_end: int) -> dict:
    """Compute care events / alive-mother-ticks over ticks 0 to window_end."""
    window_care    = [r for r in care_records if r.success and r.tick <= window_end]
    window_m_ticks = sum(p for t, p in enumerate(population_history) if t < window_end)
    rate = len(window_care) / window_m_ticks if window_m_ticks > 0 else 0.0
    return {
        "care_window_end_tick":           window_end,
        "care_events_in_window":          len(window_care),
        "mother_ticks_in_window":         window_m_ticks,
        "care_per_mother_tick_in_window": rate,
    }


def run(seed: int = 42) -> str:
    """Run Phase 10 depleted-init zero-shot baseline for one seed (1000 ticks).

    Returns the output directory path.
    """
    config = Config()
    config.seed         = seed
    config.init_mothers = 12
    config.init_food    = 48   # 4× init_mothers — same ratio as p3 measure_baseline
    config.max_ticks    = 1000

    # Ecology matched to P5/P6b
    config.infant_starvation_multiplier = INFANT_STARVATION_MULT  # 1.15
    config.birth_scatter_radius         = BIRTH_SCATTER_RADIUS     # 2

    # Zero-shot: no evolution, no plasticity
    config.children_enabled           = True
    config.care_enabled               = True
    config.plasticity_enabled         = False
    config.plasticity_kin_conditional = False
    config.reproduction_enabled       = False
    config.mutation_enabled           = False

    set_seed(config.seed)
    output_dir = create_run_dir(PHASE_NAME, config.seed)
    save_config(config, output_dir)
    save_metadata(
        output_dir,
        phase=PHASE_NAME,
        seed=config.seed,
        num_agents=config.init_mothers * 2,
        grid_size=[config.width, config.height],
        infant_starvation_multiplier=INFANT_STARVATION_MULT,
        birth_scatter_radius=BIRTH_SCATTER_RADIUS,
        plasticity_enabled=False,
        note=(
            "Phase 10 — Depleted-Init Baseline Zero-Shot. "
            "Fresh genomes cw~U(0,0.50). mult=1.15, scatter=2. "
            "No evolution/plasticity/mutation/reproduction. "
            "Provides fair comparison baseline for P6a/P6b zero-shot rates."
        ),
    )

    genomes = _make_depleted_genomes(config.init_mothers)
    sim = Simulation(config)
    sim.initialize(genomes)

    population_history = []
    energy_history     = []

    while sim.tick < config.max_ticks:
        sim.step()
        sim.tick += 1
        alive_m = [m for m in sim.mothers if m.alive]
        population_history.append(len(alive_m))
        energy_history.append(
            sum(m.energy for m in alive_m) / len(alive_m) if alive_m else 0.0
        )

    sim.logger.save_all(output_dir)
    with open(os.path.join(output_dir, "population_history.json"), "w") as f:
        json.dump({"population": population_history, "energy": energy_history}, f)

    # ── Metrics ────────────────────────────────────────────────────────────────
    total_care      = len(sim.logger.care_records)
    successful_care = len([r for r in sim.logger.care_records if r.success])
    total_m_ticks   = sum(population_history)
    care_per_m_tick = successful_care / total_m_ticks if total_m_ticks > 0 else 0.0

    window      = _care_window_rate(sim.logger.care_records, population_history, CARE_WINDOW_END)
    window_rate = window["care_per_mother_tick_in_window"]

    last_alive = max((t for t, p in enumerate(population_history) if p > 0), default=0)

    metrics = {
        "phase":                       PHASE_NAME,
        "stage":                       "zeroshot_depleted_baseline",
        "seed":                        seed,
        "infant_starvation_mult":      INFANT_STARVATION_MULT,
        "birth_scatter_radius":        BIRTH_SCATTER_RADIUS,
        "total_care_events":           total_care,
        "successful_care_events":      successful_care,
        "surviving_mothers":           len([m for m in sim.mothers if m.alive]),
        "total_mother_ticks":          total_m_ticks,
        "care_per_mother_tick_all":    care_per_m_tick,
        "care_window":                 window,
        "care_window_rate":            window_rate,   # ← primary metric
        "last_alive_tick":             last_alive,
        "phase3_zs_baseline":          0.09069,
        "note": (
            "DEPLETED_ZS_BASELINE: use care_window_rate as the matching baseline "
            "for P6a/P6b zero-shot comparisons (depleted-init genomes only). "
            "Compare to PHASE3_ZS_BASELINE=0.09069 (high-care Phase 3 genomes)."
        ),
    }
    with open(os.path.join(output_dir, "zeroshot_metrics.json"), "w") as f:
        json.dump(metrics, f, indent=2)

    generate_all_plots(output_dir)

    print(f"\n[{PHASE_NAME} | seed={seed}] Output: {output_dir}")
    print(f"  Init care_weight        : U(0.00, 0.50)  mean≈0.25 (depleted)")
    print(f"  Surviving mothers       : {metrics['surviving_mothers']} / {config.init_mothers}  "
          f"(extinction expected — no reproduction)")
    print(f"  Last alive tick         : {last_alive} / {config.max_ticks}")
    print(f"  Care / m-tick (window)  : {window_rate:.5f}  "
          f"← DEPLETED_ZS_BASELINE  "
          f"(PHASE3_ZS_BASELINE = 0.09069)")
    print(f"  Care / m-tick (all)     : {care_per_m_tick:.5f}")
    print(f"\n  → Update shared/constants.py: DEPLETED_ZS_BASELINE = {window_rate:.5f}")

    return output_dir


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Phase 10: Depleted-Init Baseline Zero-Shot")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    out = run(seed=args.seed)
    print(f"\nPhase 10 complete. Output: {out}")
