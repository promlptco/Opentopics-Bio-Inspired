# experiments/phase06_baldwin_effect/run.py
"""Phase 4: Plasticity / Baldwin Effect Analysis

Four stages:
  evolution_plastic     : evolution, plasticity on (lineage-blind) — null result / control
  zeroshot_plastic      : zero-shot from above, plasticity on lineage-blind
  evolution_plastic_kin : evolution, plasticity kin-conditional (only own-child) — proper Baldwin test
  zeroshot_plastic_kin  : zero-shot from above, plasticity kin-conditional — Baldwin transfer test

Scientific design:
  - 'evolution_plastic' (v1) showed plasticity accelerated care decline (r=−0.2158 vs −0.178 baseline).
    Cause: 90%+ of plastic updates reward foreign care (r=0) — lineage-blind signal anti-correlated
    with inclusive fitness. That run is a valid null result: "lineage-blind plasticity cannot rescue care."
  - 'evolution_plastic_kin' (v2, corrected): plastic_update fires only on is_own_child=True events.
    This is NOT kin recognition (mothers still choose by distress, not lineage). It's outcome-based
    learning aligned with inclusive fitness — the signal now only fires when the mother helped her
    own offspring. Proper Baldwin Effect test: does kin-aligned plastic feedback lead to genetic
    assimilation of higher care_weight and/or learning_rate?
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
from utils.plotting import generate_all_plots

PHASE_NAME = "phase06_baldwin_effect"


# =============================================================================
# Helpers
# =============================================================================

def _load_genomes(source_dir: str) -> list[Genome]:
    genome_path = os.path.join(source_dir, "top_genomes.json")
    if not os.path.exists(genome_path):
        raise FileNotFoundError(
            f"top_genomes.json not found in {source_dir}. "
            "Run a phase06_baldwin_effect evolution stage first."
        )
    with open(genome_path, "r") as f:
        data = json.load(f)
    return [
        Genome(
            care_weight=g.get("care_weight", 0.5),
            forage_weight=g.get("forage_weight", 0.5),
            self_weight=g.get("self_weight", 0.5),
            learning_rate=g.get("learning_rate", 0.1),
            learning_cost=g.get("learning_cost", 0.05),
        )
        for g in data
    ]


def _save_top_genomes(sim: Simulation, output_dir: str) -> None:
    alive = [m for m in sim.mothers if m.alive]
    data = [
        {
            "care_weight":   m.genome.care_weight,
            "forage_weight": m.genome.forage_weight,
            "self_weight":   m.genome.self_weight,
            "learning_rate": m.genome.learning_rate,
            "learning_cost": m.genome.learning_cost,
            "lineage_id":    m.lineage_id,
            "generation":    m.generation,
        }
        for m in alive
    ]
    with open(os.path.join(output_dir, "top_genomes.json"), "w") as f:
        json.dump(data, f, indent=2)


def _save_surviving_lineages(sim: Simulation, output_dir: str) -> None:
    lineages = sim.get_surviving_lineages()
    with open(os.path.join(output_dir, "surviving_lineages.json"), "w") as f:
        json.dump(lineages, f, indent=2)


def _care_window_metrics(care_records, population_history: list[int], window_end: int) -> dict:
    """Compute care metrics restricted to ticks 0–window_end (the care window).

    This removes the dormancy confound: after all children mature and no reproduction
    occurs, mothers accumulate mother-ticks with no children to care for. The per-
    mother-tick rate computed over all ticks underweights the actual care period.
    """
    window_care = [r for r in care_records if r.success and r.tick <= window_end]
    window_m_ticks = sum(p for t, p in enumerate(population_history) if t < window_end)
    window_rate = len(window_care) / window_m_ticks if window_m_ticks > 0 else 0.0
    return {
        "care_window_end_tick":          window_end,
        "care_events_in_window":         len(window_care),
        "mother_ticks_in_window":        window_m_ticks,
        "care_per_mother_tick_in_window": window_rate,
        "phase05_window_baseline":        0.09069,   # phase04-genomes, no plasticity, ticks 0-100
        "note": "Window metric removes dormancy confound (ticks after children mature, no reproduction).",
    }


# =============================================================================
# Evolution runner (parametrized)
# =============================================================================

def _run_evolution(seed: int, kin_conditional: bool) -> str:
    stage_name = "evolution_plastic_kin" if kin_conditional else "evolution_plastic"

    config = Config()
    config.seed = seed
    config.init_mothers = 12
    config.init_food = 45
    config.max_ticks = 5000

    config.children_enabled            = True
    config.care_enabled                = True
    config.plasticity_enabled          = True
    config.plasticity_kin_conditional  = kin_conditional
    config.reproduction_enabled        = True
    config.mutation_enabled            = True

    set_seed(config.seed)
    output_dir = create_run_dir(PHASE_NAME, config.seed)
    save_config(config, output_dir)
    save_metadata(
        output_dir,
        phase=PHASE_NAME,
        stage=stage_name,
        seed=config.seed,
        num_agents=config.init_mothers * 2,
        grid_size=[config.width, config.height],
        plasticity_enabled=True,
        plasticity_kin_conditional=kin_conditional,
        plastic_gain=config.plastic_gain,
        note=(
            "Kin-conditional plasticity: plastic_update fires only on own-child care events. "
            "Proper Baldwin Effect test — signal aligned with inclusive fitness."
            if kin_conditional else
            "Lineage-blind plasticity (v1). Expected null result: signal anti-correlated with fitness."
        ),
    )

    sim = Simulation(config)
    sim.initialize()

    population_history   = []
    energy_history       = []
    generation_snapshots = []
    SNAPSHOT_INTERVAL    = 100

    while sim.tick < config.max_ticks:
        sim.step()
        sim.tick += 1
        alive_m = [m for m in sim.mothers if m.alive]
        population_history.append(len(alive_m))
        energy_history.append(
            sum(m.energy for m in alive_m) / len(alive_m) if alive_m else 0.0
        )
        if sim.tick % SNAPSHOT_INTERVAL == 0 and alive_m:
            generation_snapshots.append({
                "tick":                sim.tick,
                "avg_care_weight":     sum(m.genome.care_weight     for m in alive_m) / len(alive_m),
                "min_care_weight":     min(m.genome.care_weight     for m in alive_m),
                "max_care_weight":     max(m.genome.care_weight     for m in alive_m),
                "avg_forage_weight":   sum(m.genome.forage_weight   for m in alive_m) / len(alive_m),
                "avg_self_weight":     sum(m.genome.self_weight     for m in alive_m) / len(alive_m),
                "avg_learning_rate":   sum(m.genome.learning_rate   for m in alive_m) / len(alive_m),
                "min_learning_rate":   min(m.genome.learning_rate   for m in alive_m),
                "max_learning_rate":   max(m.genome.learning_rate   for m in alive_m),
                "avg_learning_cost":   sum(m.genome.learning_cost   for m in alive_m) / len(alive_m),
                "avg_generation":      sum(m.generation             for m in alive_m) / len(alive_m),
                "max_generation":      max(m.generation             for m in alive_m),
                "n_mothers":           len(alive_m),
            })

    sim.logger.save_all(output_dir)
    _save_top_genomes(sim, output_dir)
    _save_surviving_lineages(sim, output_dir)
    with open(os.path.join(output_dir, "population_history.json"), "w") as f:
        json.dump({"population": population_history, "energy": energy_history}, f)
    with open(os.path.join(output_dir, "generation_snapshots.json"), "w") as f:
        json.dump(generation_snapshots, f, indent=2)

    generate_all_plots(output_dir)

    alive_m_final = [m for m in sim.mothers if m.alive]
    n = len(alive_m_final)
    final_cw = sum(m.genome.care_weight   for m in alive_m_final) / n if n else 0.0
    final_lr = sum(m.genome.learning_rate for m in alive_m_final) / n if n else 0.0
    alive_c  = len([c for c in sim.children if c.alive])

    print(f"\n[phase06 | {stage_name}] Output: {output_dir}")
    print(f"  Surviving mothers    : {n}")
    print(f"  Surviving children   : {alive_c}")
    print(f"  Care records         : {len(sim.logger.care_records)}")
    print(f"  Final avg care_weight: {final_cw:.4f}")
    print(f"  Final avg learn_rate : {final_lr:.4f}")
    return output_dir


# =============================================================================
# Zero-shot runner (parametrized)
# =============================================================================

def _run_zeroshot(seed: int, source_dir: str, kin_conditional: bool) -> str:
    stage_name = "zeroshot_plastic_kin" if kin_conditional else "zeroshot_plastic"

    genomes = _load_genomes(source_dir)
    n_mothers = len(genomes)

    config = Config()
    config.seed = seed
    config.init_mothers = n_mothers
    config.init_food = n_mothers * 4
    config.max_ticks = 1000

    config.children_enabled            = True
    config.care_enabled                = True
    config.plasticity_enabled          = True
    config.plasticity_kin_conditional  = kin_conditional
    config.reproduction_enabled        = False
    config.mutation_enabled            = False

    set_seed(config.seed)
    output_dir = create_run_dir(PHASE_NAME, config.seed)
    save_config(config, output_dir)
    save_metadata(
        output_dir,
        phase=PHASE_NAME,
        stage=stage_name,
        seed=config.seed,
        num_agents=n_mothers * 2,
        grid_size=[config.width, config.height],
        plasticity_enabled=True,
        plasticity_kin_conditional=kin_conditional,
        source_dir=source_dir,
        note=(
            "Zero-shot with kin-conditional plasticity — Baldwin transfer test. "
            "Compare care_window rate to phase05 baseline (0.09069)."
            if kin_conditional else
            "Zero-shot with lineage-blind plasticity (v1 control). Confounded by long survival."
        ),
    )

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

    total_care      = len(sim.logger.care_records)
    successful_care = len([r for r in sim.logger.care_records if r.success])
    surviving_m     = len([m for m in sim.mothers if m.alive])
    surviving_c     = len([c for c in sim.children if c.alive])
    total_m_ticks   = sum(population_history)
    care_per_m_tick = successful_care / total_m_ticks if total_m_ticks > 0 else 0.0
    last_alive_tick = max((t for t, p in enumerate(population_history) if p > 0), default=0)

    # Care-window metric: only ticks 0–maturity_age (removes dormancy confound)
    window = _care_window_metrics(
        sim.logger.care_records, population_history, config.maturity_age
    )

    metrics = {
        "stage":                    stage_name,
        "source_dir":               source_dir,
        "kin_conditional":          kin_conditional,
        "total_care_events":        total_care,
        "successful_care_events":   successful_care,
        "surviving_mothers":        surviving_m,
        "surviving_children":       surviving_c,
        "care_per_mother_tick_all": care_per_m_tick,
        "total_mother_ticks":       total_m_ticks,
        "last_alive_tick":          last_alive_tick,
        "care_window":              window,
        "phase05_baseline_all":      0.0144,
        "phase05_baseline_window":   0.09069,
        "note": (
            "Use care_window metrics for fair comparison — removes dormancy confound. "
            "Phase2 window baseline (no plasticity): 0.076/mother-tick in ticks 0–100."
        ),
    }
    with open(os.path.join(output_dir, "zeroshot_metrics.json"), "w") as f:
        json.dump(metrics, f, indent=2)

    generate_all_plots(output_dir)

    print(f"\n[phase06 | {stage_name}] Output: {output_dir}")
    print(f"  Source genomes              : {source_dir}")
    print(f"  Surviving mothers           : {surviving_m} / {n_mothers}")
    print(f"  Last alive tick             : {last_alive_tick} / {config.max_ticks}")
    print(f"  Care events (successful)    : {successful_care}")
    print(f"  Care/m-tick (all)           : {care_per_m_tick:.5f}  [confounded — avoid]")
    print(f"  Care/m-tick (window 0-{config.maturity_age})   : {window['care_per_mother_tick_in_window']:.5f}  [fair — compare to 0.09069]")
    return output_dir


# =============================================================================
# Entry point
# =============================================================================

def run(seed: int = 42, stage: str = "evolution_plastic_kin", source_dir: str = None) -> str:
    """
    stage:
      'evolution_plastic'     — v1 control: lineage-blind plasticity (null result expected)
      'zeroshot_plastic'      — v1 zero-shot (lineage-blind, confounded metric)
      'evolution_plastic_kin' — v2 corrected: kin-conditional plasticity (proper Baldwin test)
      'zeroshot_plastic_kin'  — v2 zero-shot with kin-conditional plasticity + care-window metric
    """
    if stage == "evolution_plastic":
        return _run_evolution(seed, kin_conditional=False)
    elif stage == "zeroshot_plastic":
        if source_dir is None:
            raise ValueError("source_dir required for zeroshot_plastic.")
        return _run_zeroshot(seed, source_dir, kin_conditional=False)
    elif stage == "evolution_plastic_kin":
        return _run_evolution(seed, kin_conditional=True)
    elif stage == "zeroshot_plastic_kin":
        if source_dir is None:
            raise ValueError("source_dir required for zeroshot_plastic_kin.")
        return _run_zeroshot(seed, source_dir, kin_conditional=True)
    else:
        raise ValueError(
            f"Unknown stage: {stage!r}. "
            "Use 'evolution_plastic', 'zeroshot_plastic', "
            "'evolution_plastic_kin', or 'zeroshot_plastic_kin'."
        )


if __name__ == "__main__":
    # Proper Baldwin Effect test: kin-conditional plasticity
    evo_dir = run(seed=42, stage="evolution_plastic_kin")
    run(seed=42, stage="zeroshot_plastic_kin", source_dir=evo_dir)
