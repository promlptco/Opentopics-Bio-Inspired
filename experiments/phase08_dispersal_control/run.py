# experiments/phase08_dispersal_control/run.py
"""Phase 08: Dispersal Control — natal philopatry ablation.

Scientific question:
  Phase 07 demonstrated care emergence with mult=1.15 + scatter=2 (tight philopatry).
  Phase 08 removes the philopatry by setting birth_scatter_radius=8 (standard dispersal),
  keeping infant dependency identical (mult=1.15).

  Control config: same as Phase 07 except birth_scatter_radius=8.
  Result: Phase 08 gradient = +0.050 vs Phase 07 = +0.079.
  Philopatry strengthens the effect; both conditions together maximise emergence.

  Stages:
    'evolution'  — full 5000-tick evolution, scatter=8, depleted init cw~U(0,0.5)
    'zeroshot'   — freeze evolved genomes, run 1000 ticks (plast=OFF, mut=OFF, repro=OFF)
                   measures care_window_rate for direct comparison with Phase 10
"""
import sys
import os
import json

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, PROJECT_ROOT)

from experiments.phase07_ecological_emergence.run import (
    run as _run_p7,
    _load_genomes,
    _care_window_metrics,
    INFANT_STARVATION_MULT,
    CONTROL_SCATTER_RADIUS,
    PHASE3_ZS_BASELINE,
)
from config import Config
from simulation.simulation import Simulation
from utils.experiment import set_seed, create_run_dir, save_config, save_metadata
from utils.plotting import generate_all_plots

PHASE_NAME = "phase08_dispersal_control"


def run_evolution(seed: int = 42) -> str:
    """Run Phase 08 dispersal control evolution (scatter=8) for one seed.

    Delegates to Phase 07's 'control' stage — same infrastructure, scatter=8.
    Returns the output directory path.
    """
    return _run_p7(seed=seed, stage="control")


def run_zeroshot(seed: int = 42, source_dir: str = None) -> str:
    """Zero-shot test for Phase 08 evolved genomes.

    Loads evolved genomes from source_dir (Phase 08 control run).
    Runs 1000 ticks with:
      - plasticity=OFF, mutation=OFF, reproduction=OFF
      - Same ecology: mult=1.15, scatter=8 (conditions genomes evolved under)
    Measures care_window_rate (ticks 0-100) for comparison with Phase 10.
    """
    if source_dir is None:
        raise ValueError("source_dir required: path to Phase 08 evolution output dir.")

    genomes   = _load_genomes(source_dir)
    n_mothers = len(genomes)

    config = Config()
    config.seed         = seed
    config.init_mothers = n_mothers
    config.init_food    = n_mothers * 4
    config.max_ticks    = 1000

    # Ecology: same conditions genomes evolved under
    config.infant_starvation_multiplier = INFANT_STARVATION_MULT   # 1.15
    config.birth_scatter_radius         = CONTROL_SCATTER_RADIUS    # 8 (scatter control)

    # Freeze genome — pure zero-shot test
    config.plasticity_enabled   = False
    config.reproduction_enabled = False
    config.mutation_enabled     = False
    config.children_enabled     = True
    config.care_enabled         = True

    set_seed(config.seed)
    output_dir = create_run_dir(PHASE_NAME, config.seed)
    save_config(config, output_dir)
    save_metadata(
        output_dir,
        phase=PHASE_NAME,
        stage="zeroshot",
        seed=config.seed,
        num_agents=n_mothers * 2,
        source_dir=source_dir,
        infant_starvation_multiplier=INFANT_STARVATION_MULT,
        birth_scatter_radius=CONTROL_SCATTER_RADIUS,
        note=(
            "Phase 08 zero-shot. Evolved genomes (scatter=8, mult=1.15). "
            "plast=OFF, mut=OFF, repro=OFF. "
            "Compare care_window_rate to Phase 10 depleted baseline."
        ),
    )

    sim = Simulation(config)
    sim.initialize(genomes)

    population_history = []
    while sim.tick < config.max_ticks:
        sim.step()
        sim.tick += 1
        alive_m = [m for m in sim.mothers if m.alive]
        population_history.append(len(alive_m))

    sim.logger.save_all(output_dir)
    with open(os.path.join(output_dir, "population_history.json"), "w") as f:
        json.dump({"population": population_history}, f)

    successful_care = len([r for r in sim.logger.care_records if r.success])
    total_m_ticks   = sum(population_history)
    care_per_m_tick = successful_care / total_m_ticks if total_m_ticks > 0 else 0.0
    last_alive_tick = max((t for t, p in enumerate(population_history) if p > 0), default=0)

    window = _care_window_metrics(
        sim.logger.care_records, population_history, config.maturity_age
    )
    window_rate = window["care_per_mother_tick_in_window"]

    metrics = {
        "stage":                    "zeroshot",
        "phase":                    "phase08_dispersal_control",
        "source_dir":               source_dir,
        "successful_care_events":   successful_care,
        "surviving_mothers":        len([m for m in sim.mothers if m.alive]),
        "care_per_mother_tick_all": care_per_m_tick,
        "total_mother_ticks":       total_m_ticks,
        "last_alive_tick":          last_alive_tick,
        "care_window":              window,
        "phase05_baseline":         PHASE3_ZS_BASELINE,   # Phase 05 standard evolved baseline
        "note": (
            "Compare window_rate to Phase 10 depleted-init baseline for fair assimilation signal. "
            "Phase 05 standard baseline (0.09069) is for reference only — different init cw."
        ),
    }
    with open(os.path.join(output_dir, "zeroshot_metrics.json"), "w") as f:
        json.dump(metrics, f, indent=2)

    generate_all_plots(output_dir)

    print(f"\n[phase08 | zeroshot] Output: {output_dir}")
    print(f"  Source genomes       : {source_dir}")
    print(f"  Surviving mothers    : {metrics['surviving_mothers']} / {n_mothers}")
    print(f"  Care/m-tick (window) : {window_rate:.5f}")
    print(f"  Phase 05 std baseline: {PHASE3_ZS_BASELINE:.5f}  (diff init — reference only)")
    print(f"  Compare to Phase 10  : run phase10_zeroshot_depleted for correct baseline")
    return output_dir


def run(seed: int = 42, stage: str = "evolution", source_dir: str = None) -> str:
    """
    stage:
      'evolution' — 5000t evolution, scatter=8 (delegates to phase07 control stage)
      'zeroshot'  — freeze evolved genomes, measure care_window_rate (requires source_dir)
    """
    if stage == "evolution":
        return run_evolution(seed)
    elif stage == "zeroshot":
        return run_zeroshot(seed, source_dir)
    else:
        raise ValueError(f"Unknown stage: {stage!r}. Use 'evolution' or 'zeroshot'.")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Phase 08: Dispersal Control")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--stage", default="evolution", choices=["evolution", "zeroshot"])
    parser.add_argument("--source-dir", default=None)
    args = parser.parse_args()
    out = run(seed=args.seed, stage=args.stage, source_dir=args.source_dir)
    print(f"\nPhase 08 {args.stage} complete. Output: {out}")
