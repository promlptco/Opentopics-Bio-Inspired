# experiments/p6_controls_and_baldwin/p6b_spatial_control/run.py
"""Phase 09: Spatial-Only Control

Scientific question:
  Phase 5a established that infant_starvation_multiplier=1.15 + birth_scatter_radius=2
  TOGETHER reverse the selection gradient. Phase 5b (scatter=8) showed philopatry
  strengthens the effect. But neither isolates philopatry alone.

  Phase 09 removes infant dependency entirely (mult=1.0, same as Phase 3/4) while
  keeping tight natal philopatry (scatter=2). This isolates the spatial mechanism:

    mult=1.0 + scatter=2  →  Phase 09  (philopatry only — no infant pressure)

  Expected result: gradient stays ≤ 0.
  If confirmed → infant dependency is a NECESSARY condition; philopatry alone is insufficient.
  If gradient goes positive → spatial structure alone suffices (weaker thesis claim).

Key comparison table:
  Phase 04:  mult=1.0, scatter=8, cw init=0.50  → r=−0.178  (baseline erosion)
  Phase 07:  mult=1.15, scatter=2, cw init=0.25 → r=+0.079  (full reversal)
  Phase 08:  mult=1.15, scatter=8, cw init=0.25 → r=+0.050  (philopatry weakens, both needed)
  Phase 09:  mult=1.0,  scatter=2, cw init=0.25 → r=???      (philopatry alone)

Stages:
  'evolution' — 5000t evolution, mult=1.0, scatter=2, depleted init cw~U(0,0.5)
  'zeroshot'  — freeze evolved genomes, 1000t (plast=OFF, mut=OFF, repro=OFF)
                measures care_window_rate for comparison with Phase 10
"""
import sys
import os
import json
import random as _random

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, PROJECT_ROOT)

from config import Config
from simulation.simulation import Simulation
from evolution.genome import Genome
from utils.experiment import set_seed, create_run_dir, save_config, save_metadata
from utils.plotting import generate_all_plots

PHASE_NAME = "phase09_spatial_control"

# Phase 09 ecological parameters
# mult=1.0: NO infant pressure (same as Phase 3/4 — infants hunger at adult rate)
# scatter=2: tight natal philopatry (same as Phase 5a — keeps kin clustered)
INFANT_STARVATION_MULT = 1.0   # KEY: no extra infant pressure
BIRTH_SCATTER_RADIUS   = 2     # Tight philopatry (same as Phase 5a)

PHASE3_SELECTION_R = -0.178    # Phase 3 reference gradient


def _make_depleted_genomes(n: int) -> list[Genome]:
    """Depleted-care baseline — same as Phase 5a initialisation.

    care_weight ~ U(0.00, 0.50), mean=0.25
    Below Phase 3 eroded equilibrium (0.42) and Phase 3 start (0.50).
    """
    return [
        Genome(
            care_weight=_random.uniform(0.0, 0.50),
            forage_weight=_random.uniform(0.0, 1.0),
            self_weight=_random.uniform(0.0, 1.0),
        )
        for _ in range(n)
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


def _compute_selection_gradient(birth_log_path: str) -> float | None:
    """Pearson r of care_weight vs generation from birth_log.csv."""
    import csv
    if not os.path.exists(birth_log_path):
        return None
    with open(birth_log_path) as f:
        rows = list(csv.DictReader(f))
    if len(rows) < 10:
        return None
    cw   = [float(r["mother_care_weight"]) for r in rows]
    gens = [float(r["mother_generation"])  for r in rows]
    n = len(cw)
    mean_cw  = sum(cw) / n
    mean_gen = sum(gens) / n
    num = sum((cw[i] - mean_cw) * (gens[i] - mean_gen) for i in range(n))
    den_cw  = sum((x - mean_cw)  ** 2 for x in cw)  ** 0.5
    den_gen = sum((x - mean_gen) ** 2 for x in gens) ** 0.5
    if den_cw == 0 or den_gen == 0:
        return None
    return num / (den_cw * den_gen)


def run(seed: int = 42) -> str:
    """Run Phase 09 spatial-only control for one seed (5000 ticks).

    Returns the output directory path.
    """
    config = Config()
    config.seed        = seed
    config.init_mothers = 12
    config.init_food   = 45
    config.max_ticks   = 5000

    # Ecological parameters — KEY: no infant pressure, tight philopatry only
    config.infant_starvation_multiplier = INFANT_STARVATION_MULT   # 1.0
    config.birth_scatter_radius         = BIRTH_SCATTER_RADIUS      # 2

    # Pure genetic selection — no plasticity
    config.children_enabled           = True
    config.care_enabled               = True
    config.plasticity_enabled         = False
    config.plasticity_kin_conditional = False
    config.reproduction_enabled       = True
    config.mutation_enabled           = True

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
            "Phase 09 — Spatial-Only Control. "
            "mult=1.0 (no infant pressure), scatter=2 (natal philopatry). "
            "Isolates spatial mechanism. Expected: gradient stays ≤ 0."
        ),
    )

    genomes = _make_depleted_genomes(config.init_mothers)
    sim = Simulation(config)
    sim.initialize(genomes)

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
                "tick":              sim.tick,
                "avg_care_weight":   sum(m.genome.care_weight   for m in alive_m) / len(alive_m),
                "min_care_weight":   min(m.genome.care_weight   for m in alive_m),
                "max_care_weight":   max(m.genome.care_weight   for m in alive_m),
                "avg_forage_weight": sum(m.genome.forage_weight for m in alive_m) / len(alive_m),
                "avg_self_weight":   sum(m.genome.self_weight   for m in alive_m) / len(alive_m),
                "avg_generation":    sum(m.generation           for m in alive_m) / len(alive_m),
                "max_generation":    max(m.generation           for m in alive_m),
                "n_mothers":         len(alive_m),
            })

    sim.logger.save_all(output_dir)
    _save_top_genomes(sim, output_dir)
    with open(os.path.join(output_dir, "population_history.json"), "w") as f:
        json.dump({"population": population_history, "energy": energy_history}, f)
    with open(os.path.join(output_dir, "generation_snapshots.json"), "w") as f:
        json.dump(generation_snapshots, f, indent=2)

    grad = _compute_selection_gradient(os.path.join(output_dir, "birth_log.csv"))

    generate_all_plots(output_dir)

    alive_final = [m for m in sim.mothers if m.alive]
    n = len(alive_final)
    final_cw = sum(m.genome.care_weight for m in alive_final) / n if n else 0.0

    print(f"\n[phase09 | seed={seed}] Output: {output_dir}")
    print(f"  Surviving mothers     : {n}")
    print(f"  Final avg care_weight : {final_cw:.4f}  (Phase 07: ~0.29-0.36)")
    print(f"  Selection gradient r  : {grad:+.4f}  (Phase 07: +0.079, Phase 04: -0.178)"
          if grad is not None else "  Selection gradient r  : N/A (insufficient birth data)")
    return output_dir


def _load_genomes_from_dir(source_dir: str) -> list:
    """Load top_genomes.json from a run directory."""
    import json as _json
    from evolution.genome import Genome as _Genome
    genome_path = os.path.join(source_dir, "top_genomes.json")
    if not os.path.exists(genome_path):
        raise FileNotFoundError(f"top_genomes.json not found in {source_dir}.")
    with open(genome_path) as f:
        data = _json.load(f)
    return [
        _Genome(
            care_weight=g.get("care_weight", 0.5),
            forage_weight=g.get("forage_weight", 0.5),
            self_weight=g.get("self_weight", 0.5),
            learning_rate=g.get("learning_rate", 0.1),
            learning_cost=g.get("learning_cost", 0.05),
        )
        for g in data
    ]


def _care_window_rate(care_records, population_history: list[int], window_end: int) -> dict:
    window_care   = [r for r in care_records if r.success and r.tick <= window_end]
    window_m_ticks = sum(p for t, p in enumerate(population_history) if t < window_end)
    rate = len(window_care) / window_m_ticks if window_m_ticks > 0 else 0.0
    return {
        "care_window_end_tick":           window_end,
        "care_events_in_window":          len(window_care),
        "mother_ticks_in_window":         window_m_ticks,
        "care_per_mother_tick_in_window": rate,
        "note": "Compare to Phase 10 depleted-init baseline for fair assimilation signal.",
    }


def run_zeroshot(seed: int = 42, source_dir: str = None) -> str:
    """Zero-shot test for Phase 09 evolved genomes.

    Loads evolved genomes from source_dir (Phase 09 evolution run).
    Runs 1000 ticks with plasticity=OFF, mutation=OFF, reproduction=OFF.
    Ecology kept same as Phase 09: mult=1.0, scatter=2.
    Measures care_window_rate (ticks 0-100) for comparison with Phase 10.
    """
    if source_dir is None:
        raise ValueError("source_dir required: path to Phase 09 evolution output dir.")

    genomes   = _load_genomes_from_dir(source_dir)
    n_mothers = len(genomes)

    config = Config()
    config.seed         = seed
    config.init_mothers = n_mothers
    config.init_food    = n_mothers * 4
    config.max_ticks    = 1000

    # Same ecology as Phase 09 evolution
    config.infant_starvation_multiplier = INFANT_STARVATION_MULT   # 1.0
    config.birth_scatter_radius         = BIRTH_SCATTER_RADIUS      # 2

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
        birth_scatter_radius=BIRTH_SCATTER_RADIUS,
        note=(
            "Phase 09 zero-shot. Evolved genomes (mult=1.0, scatter=2). "
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
        population_history.append(len([m for m in sim.mothers if m.alive]))

    import json as _json
    sim.logger.save_all(output_dir)
    with open(os.path.join(output_dir, "population_history.json"), "w") as f:
        _json.dump({"population": population_history}, f)

    successful_care = len([r for r in sim.logger.care_records if r.success])
    total_m_ticks   = sum(population_history)
    care_per_m_tick = successful_care / total_m_ticks if total_m_ticks > 0 else 0.0
    window = _care_window_rate(sim.logger.care_records, population_history, config.maturity_age)
    window_rate = window["care_per_mother_tick_in_window"]

    metrics = {
        "stage":                    "zeroshot",
        "phase":                    "phase09_spatial_control",
        "source_dir":               source_dir,
        "successful_care_events":   successful_care,
        "surviving_mothers":        len([m for m in sim.mothers if m.alive]),
        "care_per_mother_tick_all": care_per_m_tick,
        "total_mother_ticks":       total_m_ticks,
        "care_window":              window,
        "note": "Compare window_rate to Phase 10 depleted-init baseline.",
    }
    with open(os.path.join(output_dir, "zeroshot_metrics.json"), "w") as f:
        _json.dump(metrics, f, indent=2)

    generate_all_plots(output_dir)

    print(f"\n[phase09 | zeroshot] Output: {output_dir}")
    print(f"  Source: {source_dir}")
    print(f"  Surviving mothers    : {metrics['surviving_mothers']} / {n_mothers}")
    print(f"  Care/m-tick (window) : {window_rate:.5f}")
    print(f"  Compare to Phase 10  : run phase10_zeroshot_depleted for correct baseline")
    return output_dir


def run(seed: int = 42, stage: str = "evolution", source_dir: str = None) -> str:
    """
    stage:
      'evolution' — 5000t evolution, mult=1.0, scatter=2
      'zeroshot'  — freeze evolved genomes, measure care_window_rate (requires source_dir)
    """
    if stage == "evolution":
        return run_evolution(seed)
    elif stage == "zeroshot":
        return run_zeroshot(seed, source_dir)
    else:
        raise ValueError(f"Unknown stage: {stage!r}. Use 'evolution' or 'zeroshot'.")


def run_evolution(seed: int = 42) -> str:
    """Alias for the original run() — 5000t evolution only."""
    # Build config and run (reuses the original body)
    import random as _random
    from evolution.genome import Genome as _Genome

    config = Config()
    config.seed        = seed
    config.init_mothers = 12
    config.init_food   = 45
    config.max_ticks   = 5000
    config.infant_starvation_multiplier = INFANT_STARVATION_MULT
    config.birth_scatter_radius         = BIRTH_SCATTER_RADIUS
    config.children_enabled           = True
    config.care_enabled               = True
    config.plasticity_enabled         = False
    config.plasticity_kin_conditional = False
    config.reproduction_enabled       = True
    config.mutation_enabled           = True

    set_seed(config.seed)
    output_dir = create_run_dir(PHASE_NAME, config.seed)
    save_config(config, output_dir)
    save_metadata(
        output_dir,
        phase=PHASE_NAME,
        stage="evolution",
        seed=config.seed,
        num_agents=config.init_mothers * 2,
        infant_starvation_multiplier=INFANT_STARVATION_MULT,
        birth_scatter_radius=BIRTH_SCATTER_RADIUS,
        note="Phase 09 — Spatial-Only Control evolution. mult=1.0, scatter=2.",
    )

    genomes = _make_depleted_genomes(config.init_mothers)
    sim = Simulation(config)
    sim.initialize(genomes)

    population_history = []
    energy_history     = []
    generation_snapshots = []
    SNAPSHOT_INTERVAL  = 100

    while sim.tick < config.max_ticks:
        sim.step()
        sim.tick += 1
        alive_m = [m for m in sim.mothers if m.alive]
        population_history.append(len(alive_m))
        energy_history.append(sum(m.energy for m in alive_m) / len(alive_m) if alive_m else 0.0)
        if sim.tick % SNAPSHOT_INTERVAL == 0 and alive_m:
            generation_snapshots.append({
                "tick":              sim.tick,
                "avg_care_weight":   sum(m.genome.care_weight   for m in alive_m) / len(alive_m),
                "min_care_weight":   min(m.genome.care_weight   for m in alive_m),
                "max_care_weight":   max(m.genome.care_weight   for m in alive_m),
                "avg_forage_weight": sum(m.genome.forage_weight for m in alive_m) / len(alive_m),
                "avg_self_weight":   sum(m.genome.self_weight   for m in alive_m) / len(alive_m),
                "avg_generation":    sum(m.generation           for m in alive_m) / len(alive_m),
                "max_generation":    max(m.generation           for m in alive_m),
                "n_mothers":         len(alive_m),
            })

    import json as _json
    sim.logger.save_all(output_dir)
    _save_top_genomes(sim, output_dir)
    with open(os.path.join(output_dir, "population_history.json"), "w") as f:
        _json.dump({"population": population_history, "energy": energy_history}, f)
    with open(os.path.join(output_dir, "generation_snapshots.json"), "w") as f:
        _json.dump(generation_snapshots, f, indent=2)

    grad = _compute_selection_gradient(os.path.join(output_dir, "birth_log.csv"))
    generate_all_plots(output_dir)

    alive_final = [m for m in sim.mothers if m.alive]
    n = len(alive_final)
    final_cw = sum(m.genome.care_weight for m in alive_final) / n if n else 0.0
    print(f"\n[phase09 | seed={seed}] Output: {output_dir}")
    print(f"  Surviving mothers     : {n}")
    print(f"  Final avg care_weight : {final_cw:.4f}")
    print(f"  Selection gradient r  : {grad:+.4f}  (Phase 07: +0.079, Phase 04: -0.178)"
          if grad is not None else "  Selection gradient r  : N/A")
    return output_dir


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Phase 09: Spatial-Only Control")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--stage", default="evolution", choices=["evolution", "zeroshot"])
    parser.add_argument("--source-dir", default=None)
    args = parser.parse_args()
    out = run(seed=args.seed, stage=args.stage, source_dir=args.source_dir)
    print(f"\nPhase 09 {args.stage} complete. Output: {out}")
