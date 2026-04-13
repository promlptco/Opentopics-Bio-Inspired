# experiments/p5_enhanced_ecology/run.py
"""Phase 5: Ecological Emergence — selection gradient reversal via infant dependency.

Scientific question:
  Phases 3–4 established the EROSION mechanism: without strong ecological pressure,
  natural selection erodes care (r=−0.178, Phase 3). Hamilton's rule is violated because
  r~0.1 (spatial mixing) and B is marginal (infants survive fine without care).

  Phase 5 tests whether infant dependency can REVERSE this gradient:

    1. Infant Dependency (elevating B):
         infant_starvation_multiplier=1.15 — infants hunger 15% faster.
         Without sustained care, infants die BEFORE maturing (hungry at tick ~108 < maturity 100).
         B transitions from marginal (hunger reduction) to near-existential (survival threshold).
         This shifts the cost-benefit ratio so that rB − C > 0 at lower r.

         Note: multipliers ≥1.25 create an evolutionary trap — selection works but the
         population crashes before it can stabilize. 1.15 is the calibrated working point.

    2. Tighter Natal Philopatry (amplifying effective r):
         birth_scatter_radius=2 — newborns placed within 2 Chebyshev cells of mother.
         Keeps kin spatially clustered → effective r rises from ~0.1 toward ~0.20.
         No kin recognition required — spatial proximity does the work.

  Initial care level: U(0, 0.50), mean=0.25 — half of Phase 3's starting level and
  well below Phase 3's eroded equilibrium (0.42). This represents a "depleted" population.

Stages:
  'survival_gate' — 10-gen test (~1000 ticks). Population must survive ≥10 gens with
                    ≥5 mothers at end. Gates the full 50-gen run.
  'evolution'     — 5a: full 50-gen evolution (5000 ticks), no plasticity.
                    Clean genetic signal: any care rise is from pure natural selection.
  'control'       — 5b: same as evolution but birth_scatter_radius=8 (dispersal control).
                    Tests whether natal philopatry is required or if dependency alone suffices.
  'zeroshot'      — 5c: load evolved genomes, run 1 generation (no reproduction, no mutation).
                    Measures care_window rate vs Phase 05 baseline (0.09069).
                    Genetic assimilation confirmed if rate is significantly higher.

Key measurement:
  - selection_gradient: care_weight vs generation (r). Phase 3 = −0.178. Phase 5 target: POSITIVE.
  - trajectory: Phase 3 declines 0.50→0.42. Phase 5 target: rises from 0.25 toward 0.35+.
  - zero-shot care_window rate: vs Phase 3 baseline 0.09069. Phase 5 target: significantly higher.
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

PHASE_NAME = "phase07_ecological_emergence"

# Phase 5 ecological parameters
# mult=1.15: infants die at tick ~108 without care (maturity_age=100) → B near-existential.
# Calibration note: mult ≥ 1.25 creates an evolutionary trap (selection works but population
# crashes during the bottleneck). 1.15 is the maximum that allows stable evolutionary dynamics.
INFANT_STARVATION_MULT = 1.15
BIRTH_SCATTER_RADIUS   = 2      # Phase 5a (tight natal philopatry)
CONTROL_SCATTER_RADIUS = 8      # Phase 5b control (standard/dispersed)

# Selection gradient window for early gens (Phase 3 comparison baseline)
PHASE3_SELECTION_R = -0.178
PHASE3_ZS_BASELINE = 0.09069   # care/mother-tick in ticks 0–100


# =============================================================================
# Near-zero genome initialisation
# =============================================================================

def _make_emergence_genomes(n: int) -> list[Genome]:
    """Generate n genomes at a DEPLETED care baseline — the Phase 5 starting point.

    care_weight  ~ Uniform(0.00, 0.50)  mean=0.25 — half of Phase 3's start (0.50)
                                         and below Phase 3's eroded equilibrium (0.42).
    forage/self  ~ Uniform(0.00, 1.00)  [unconstrained]

    This represents a population where care exists but is below the level that Phase 3
    stabilised at. Without ecological pressure (control), selection would continue to
    erode it. With infant dependency (Phase 5a), selection reverses direction.

    Calibration note: starting at true near-zero (0.00–0.05) creates an evolutionary
    trap with INFANT_STARVATION_MULT=1.15: selection gradient is immediately positive but
    the initial bottleneck (first 400 ticks without viable care) kills the population.
    Starting at 0.00–0.50 gives enough initial care capacity to survive the first generation.
    """
    genomes = []
    for _ in range(n):
        genomes.append(Genome(
            care_weight=_random.uniform(0.0, 0.50),
            forage_weight=_random.uniform(0.0, 1.0),
            self_weight=_random.uniform(0.0, 1.0),
        ))
    return genomes


# =============================================================================
# Helpers (shared with multi-seed runner)
# =============================================================================

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


def _load_genomes(source_dir: str) -> list[Genome]:
    genome_path = os.path.join(source_dir, "top_genomes.json")
    if not os.path.exists(genome_path):
        raise FileNotFoundError(
            f"top_genomes.json not found in {source_dir}. "
            "Run phase07_ecological_emergence evolution stage first."
        )
    with open(genome_path) as f:
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


def _compute_selection_gradient(birth_log_path: str) -> float | None:
    """Pearson r of care_weight vs generation from birth_log.csv.
    Phase 3 reference: r=−0.178 (eroding). Phase 5 target: positive r.
    """
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


def _care_window_metrics(care_records, population_history: list[int], window_end: int) -> dict:
    window_care   = [r for r in care_records if r.success and r.tick <= window_end]
    window_m_ticks = sum(p for t, p in enumerate(population_history) if t < window_end)
    window_rate   = len(window_care) / window_m_ticks if window_m_ticks > 0 else 0.0
    return {
        "care_window_end_tick":           window_end,
        "care_events_in_window":          len(window_care),
        "mother_ticks_in_window":         window_m_ticks,
        "care_per_mother_tick_in_window": window_rate,
        "phase05_zeroshot_baseline":       PHASE3_ZS_BASELINE,
        "note": "Compare to phase05 zero-shot window rate 0.09069 for assimilation test.",
    }


# =============================================================================
# Phase 5 base config
# =============================================================================

def _make_config(seed: int, scatter_radius: int = BIRTH_SCATTER_RADIUS) -> Config:
    config = Config()
    config.seed = seed
    config.init_mothers = 12
    config.init_food    = 45
    # Ecological pressure
    config.infant_starvation_multiplier = INFANT_STARVATION_MULT
    config.birth_scatter_radius         = scatter_radius
    # Pure genetic selection — no plasticity (clean signal)
    config.plasticity_enabled          = False
    config.plasticity_kin_conditional  = False
    config.children_enabled            = True
    config.care_enabled                = True
    config.reproduction_enabled        = True
    config.mutation_enabled            = True
    return config


# =============================================================================
# Stage: survival_gate (10 generations ~ 1000 ticks)
# =============================================================================

def _run_survival_gate(seed: int) -> dict:
    """Quick viability check before committing to a full 50-gen run.

    Returns: {"survived": bool, "final_pop": int, "ticks_survived": int, "output_dir": str}
    Failure criteria: fewer than 5 mothers at tick 1000.
    If failed, caller should reduce infant_starvation_multiplier (try 2.0).
    """
    config = _make_config(seed)
    config.max_ticks = 1000

    set_seed(config.seed)
    output_dir = create_run_dir(PHASE_NAME, config.seed)
    save_config(config, output_dir)
    save_metadata(
        output_dir,
        phase=PHASE_NAME,
        stage="survival_gate",
        seed=config.seed,
        infant_starvation_multiplier=config.infant_starvation_multiplier,
        birth_scatter_radius=config.birth_scatter_radius,
        note="10-gen viability check. Population must reach ≥5 mothers at tick 1000.",
    )

    genomes = _make_emergence_genomes(config.init_mothers)
    sim = Simulation(config)
    sim.initialize(genomes)

    population_history = []
    while sim.tick < config.max_ticks:
        sim.step()
        sim.tick += 1
        population_history.append(len([m for m in sim.mothers if m.alive]))
        if population_history[-1] == 0:
            break  # extinct — no point continuing

    final_pop = population_history[-1] if population_history else 0
    survived  = final_pop >= 5

    with open(os.path.join(output_dir, "population_history.json"), "w") as f:
        json.dump({"population": population_history}, f)

    print(f"\n[phase07 | survival_gate] Output: {output_dir}")
    print(f"  Final population : {final_pop} mothers")
    print(f"  Result           : {'PASSED' if survived else 'FAILED — reduce infant_starvation_multiplier'}")

    return {
        "survived":       survived,
        "final_pop":      final_pop,
        "ticks_survived": len(population_history),
        "output_dir":     output_dir,
    }


# =============================================================================
# Stage: evolution (5a — full 50 generations)
# =============================================================================

def _run_evolution(seed: int, stage: str = "evolution",
                   scatter_radius: int = BIRTH_SCATTER_RADIUS) -> str:
    config = _make_config(seed, scatter_radius=scatter_radius)
    config.max_ticks = 5000

    set_seed(config.seed)
    output_dir = create_run_dir(PHASE_NAME, config.seed)
    save_config(config, output_dir)
    save_metadata(
        output_dir,
        phase=PHASE_NAME,
        stage=stage,
        seed=config.seed,
        num_agents=config.init_mothers * 2,
        grid_size=[config.width, config.height],
        infant_starvation_multiplier=config.infant_starvation_multiplier,
        birth_scatter_radius=scatter_radius,
        plasticity_enabled=False,
        note=(
            "Phase 5a — Ecological Emergence. Near-zero care init (0–0.05). "
            "infant_starvation_multiplier=1.15 makes B existential. "
            "birth_scatter_radius=2 increases effective r via natal philopatry. "
            "Plasticity OFF — any care rise is pure genetic selection."
            if stage == "evolution" else
            "Phase 5b — Dispersal control. Same as 5a but birth_scatter_radius=8 (standard). "
            "Tests whether natal philopatry is necessary or if dependency alone suffices."
        ),
    )

    genomes = _make_emergence_genomes(config.init_mothers)
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
                "avg_learning_rate": sum(m.genome.learning_rate for m in alive_m) / len(alive_m),
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

    # Selection gradient (key Phase 5 measurement)
    grad = _compute_selection_gradient(os.path.join(output_dir, "birth_log.csv"))

    generate_all_plots(output_dir)

    alive_m_final = [m for m in sim.mothers if m.alive]
    n = len(alive_m_final)
    final_cw = sum(m.genome.care_weight for m in alive_m_final) / n if n else 0.0

    print(f"\n[phase07 | {stage}] Output: {output_dir}")
    print(f"  Surviving mothers     : {n}")
    print(f"  Final avg care_weight : {final_cw:.4f}  (Phase 3 start was 0.500, final was 0.420)")
    print(f"  Selection gradient r  : {grad:.4f}  (Phase 04 baseline: {PHASE3_SELECTION_R})"
          if grad is not None else "  Selection gradient r  : N/A (insufficient birth data)")
    print(f"  Initial care_weight   : 0.000–0.500 (mean=0.250, Phase 3 start: 0.500)")
    return output_dir


# =============================================================================
# Stage: zeroshot (5c — genetic assimilation test)
# =============================================================================

def _run_zeroshot(seed: int, source_dir: str) -> str:
    """Load evolved Phase 5 genomes and run 1 gen without reproduction/mutation/plasticity.

    Measures care_window rate vs Phase 05 baseline (0.09069).
    Genetic assimilation confirmed if rate is significantly higher.
    """
    genomes   = _load_genomes(source_dir)
    n_mothers = len(genomes)

    config = Config()
    config.seed        = seed
    config.init_mothers = n_mothers
    config.init_food   = n_mothers * 4
    config.max_ticks   = 1000
    # Ecological pressure still active (same conditions evolved under)
    config.infant_starvation_multiplier = INFANT_STARVATION_MULT
    config.birth_scatter_radius         = BIRTH_SCATTER_RADIUS
    # Freeze genome — pure assimilation test
    config.plasticity_enabled    = False
    config.reproduction_enabled  = False
    config.mutation_enabled      = False
    config.children_enabled      = True
    config.care_enabled          = True

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
        infant_starvation_multiplier=config.infant_starvation_multiplier,
        note=(
            "Phase 5c genetic assimilation test. Evolved genomes, no plasticity/reproduction. "
            "Compare care_window rate to Phase 3 baseline 0.09069. "
            "Higher rate = care encoded in genome (assimilation confirmed)."
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

    successful_care  = len([r for r in sim.logger.care_records if r.success])
    total_m_ticks    = sum(population_history)
    care_per_m_tick  = successful_care / total_m_ticks if total_m_ticks > 0 else 0.0
    last_alive_tick  = max((t for t, p in enumerate(population_history) if p > 0), default=0)

    window = _care_window_metrics(
        sim.logger.care_records, population_history, config.maturity_age
    )
    window_rate = window["care_per_mother_tick_in_window"]
    assimilated = window_rate > PHASE3_ZS_BASELINE

    metrics = {
        "stage":                    "zeroshot",
        "source_dir":               source_dir,
        "successful_care_events":   successful_care,
        "surviving_mothers":        len([m for m in sim.mothers if m.alive]),
        "care_per_mother_tick_all": care_per_m_tick,
        "total_mother_ticks":       total_m_ticks,
        "last_alive_tick":          last_alive_tick,
        "care_window":              window,
        "phase05_zeroshot_baseline":          PHASE3_ZS_BASELINE,
        "assimilation_signal":      assimilated,
        "note": (
            "assimilation_signal=True means window rate > Phase 3 baseline — "
            "care encoded in genome, not just learned in-lifetime."
        ),
    }
    with open(os.path.join(output_dir, "zeroshot_metrics.json"), "w") as f:
        json.dump(metrics, f, indent=2)

    generate_all_plots(output_dir)

    print(f"\n[phase07 | zeroshot] Output: {output_dir}")
    print(f"  Source genomes       : {source_dir}")
    print(f"  Surviving mothers    : {metrics['surviving_mothers']} / {n_mothers}")
    print(f"  Care/m-tick (window) : {window_rate:.5f}  (Phase 3 baseline: {PHASE3_ZS_BASELINE:.5f})")
    print(f"  Assimilation signal  : {'YES — care in genome' if assimilated else 'NO — not above baseline'}")
    return output_dir


# =============================================================================
# Entry point
# =============================================================================

def run(seed: int = 42, stage: str = "evolution", source_dir: str = None) -> str | dict:
    """
    stage:
      'survival_gate'  — quick 10-gen viability check (returns dict, not str)
      'evolution'      — 5a: full 50-gen, birth_scatter_radius=2
      'control'        — 5b: full 50-gen, birth_scatter_radius=8 (dispersal control)
      'zeroshot'       — 5c: genetic assimilation test (requires source_dir)
    """
    if stage == "survival_gate":
        return _run_survival_gate(seed)
    elif stage == "evolution":
        return _run_evolution(seed, stage="evolution", scatter_radius=BIRTH_SCATTER_RADIUS)
    elif stage == "control":
        return _run_evolution(seed, stage="control", scatter_radius=CONTROL_SCATTER_RADIUS)
    elif stage == "zeroshot":
        if source_dir is None:
            raise ValueError("source_dir required for zeroshot stage.")
        return _run_zeroshot(seed, source_dir)
    else:
        raise ValueError(
            f"Unknown stage: {stage!r}. "
            "Use 'survival_gate', 'evolution', 'control', or 'zeroshot'."
        )


if __name__ == "__main__":
    # Step 1: Survival gate — must pass before full run
    gate = run(seed=42, stage="survival_gate")
    if not gate["survived"]:
        print("\nSurvival gate FAILED. Tune infant_starvation_multiplier in run.py and retry.")
        import sys
        sys.exit(1)

    # Step 2: Full evolution (5a)
    evo_dir = run(seed=42, stage="evolution")

    # Step 3: Dispersal control (5b)
    run(seed=42, stage="control")

    # Step 4: Genetic assimilation test (5c)
    run(seed=42, stage="zeroshot", source_dir=evo_dir)
