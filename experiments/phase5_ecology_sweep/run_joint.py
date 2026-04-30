# experiments/phase5_ecology_sweep/run_joint.py
"""Phase 5: Ecological Emergence — selection gradient reversal via infant dependency.

Continues directly from Phase 4 FIXED baseline (Scripts 05 & 06):
  Phase 4 result: care_weight is near-neutral at ~0.784 (r≈−0.033, p=0.055, NOT significant).
  Care is neutral because infant B≈0: children survive to maturity (tick 100) without any
  feeding (hunger_rate=0.008, threshold=1.0, death at tick ~125 > maturity_age=100).

Phase 5 scientific question:
  Does ecological pressure — making infant survival contingent on maternal care — cause
  care_weight to evolve ABOVE the Phase 4 neutral baseline of ~0.784?

Ecological pressure applied:
  1. Infant Dependency (elevating B to existential):
       infant_starvation_multiplier=1.65 — infants hunger 1.65x faster (rate=0.0132/tick).
       Without care, infant dies at tick ~75 (before maturity_age=100).
       Child needs ~3 feedings to survive to maturity; 0 feedings = death.
       B transitions from zero (Phase 4) to existential: care determines whether child
       reaches maturity at all. Hamilton's rule rB − C > 0 can now be satisfied.
       Calibrated: 1.65 is the maximum multiplier where population does not collapse
       (empirical sweep 2026-04-30; 1.75 collapses at seed=42).

  2. Natal Philopatry (amplifying effective r):
       Phase 5a: birth_scatter_radius=2 — newborns placed within 2 Chebyshev cells of mother.
       Keeps kin spatially clustered → effective r rises from near-zero toward ~0.2.
       No kin recognition required — spatial proximity does the work.
       Phase 5b: birth_scatter_radius=5 (Phase 4 standard) — dispersal control.
       Tests whether natal philopatry is required or if infant dependency alone suffices.

Starting conditions (Phase 4 baseline — direct continuation):
  care_weight   = 0.80       (Phase 4 Scripts 05/06 initial value)
  forage_weight = 1.0        (Phase 4 Scripts 05/06 initial value)
  self_weight   ~ U(0, 1)    (Phase 4 Scripts 05/06 initial value)
  Grid = 50×50, N=40, food=120 (Phase 4 ecology — unchanged)
  10,000 ticks, seeds 42–51  (Phase 4 duration — unchanged)

Primary measurements:
  - selection_gradient r: Pearson r of care_weight vs generation from birth_log.
    Phase 4 baseline: r≈−0.033 (near-neutral, not significant).
    Phase 5 prediction: r > 0 (care builds — selection now favours caring mothers).
  - final care_weight at tick 10,000: target > 0.784 (Phase 4 neutral baseline).

Stages:
  'survival_gate' — 1000-tick viability check (≈10 generations).
                    Population must reach ≥10 mothers. Verifies ecological pressure
                    does not immediately collapse the population.
  'evolution'     — Phase 5a: 10,000-tick evolution with natal philopatry (scatter=2).
                    Plasticity OFF — any care rise is from pure natural selection.
  'control'       — Phase 5b: same as evolution but scatter=5 (Phase 4 standard).
                    Tests whether natal philopatry is necessary for care to rise.
  'zeroshot'      — Load evolved genomes; run 1000 ticks, no reproduction/mutation/plasticity.
                    Records care behavior encoded in the evolved genome (Phase 6 precursor).
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

PHASE_NAME = "phase5_ecology_sweep"

# Phase 5 ecological parameters.
# mult=1.65: hunger_rate=0.0132/tick → death at tick ~75 without care (maturity_age=100).
# Child needs ~3 feedings (each reduces hunger by 0.2) to survive to maturity.
# Calibrated via survival gate sweep: 1.65 passes 3/3 seeds; 1.75 collapses at seed=42.
INFANT_STARVATION_MULT = 1.65
BIRTH_SCATTER_RADIUS   = 2    # Phase 5a: tight natal philopatry (effective r ↑)
CONTROL_SCATTER_RADIUS = 5    # Phase 5b: Phase 4 standard scatter (isolates philopatry variable)

# Phase 4 FIXED baselines (Scripts 05 & 06, definitive — 2026-04-27)
PHASE4_NEUTRAL_R          = -0.033  # Script 05 mean Pearson r (near-neutral, p=0.055)
PHASE4_NEUTRAL_CARE_WEIGHT = 0.784  # Script 06 final mean care_weight (true neutral)
PHASE4_SELECT_CARE_WEIGHT  = 0.789  # Script 05 final mean care_weight (standard costs)


# =============================================================================
# Phase 4 baseline genome initialisation
# =============================================================================

def _make_phase4_baseline_genomes(n: int) -> list[Genome]:
    """Generate n genomes matching Phase 4 Scripts 05/06 starting conditions.

    Direct continuation from Phase 4:
      care_weight   = 0.80         (Phase 4 ceiling-drop init — fixed)
      forage_weight = 1.0          (Phase 4 standard — fixed)
      self_weight   ~ U(0, 1)      (Phase 4 standard — random)

    Phase 5 null result: care stays at ~0.784 (same outcome as Phase 4, mult=1.0).
    Phase 5 prediction: care rises above 0.784 because caring mothers' children survive
    to maturity (fed repeatedly before tick 42) while non-caring mothers' children die.
    """
    genomes = []
    for _ in range(n):
        genomes.append(Genome(
            care_weight=0.80,
            forage_weight=1.0,
            self_weight=_random.uniform(0.0, 1.0),
        ))
    return genomes


# =============================================================================
# Helpers
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
            "Run phase5_ecology_sweep evolution stage first."
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
    Phase 4 reference: r≈−0.033 (near-neutral). Phase 5 target: positive r.
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
    window_care    = [r for r in care_records if r.success and r.tick <= window_end]
    window_m_ticks = sum(p for t, p in enumerate(population_history) if t < window_end)
    window_rate    = len(window_care) / window_m_ticks if window_m_ticks > 0 else 0.0
    return {
        "care_window_end_tick":           window_end,
        "care_events_in_window":          len(window_care),
        "mother_ticks_in_window":         window_m_ticks,
        "care_per_mother_tick_in_window": window_rate,
        "phase4_neutral_care_weight":     PHASE4_NEUTRAL_CARE_WEIGHT,
        "note": "Zero-shot care rate for Phase 6 (Baldwin assimilation) precursor.",
    }


# =============================================================================
# Phase 5 base config (matches Phase 4 ecology + ecological pressure)
# =============================================================================

def _make_config(seed: int, scatter_radius: int = BIRTH_SCATTER_RADIUS) -> Config:
    config = Config()
    config.seed = seed
    # Match Phase 4 Scripts 05/06 ecology exactly (direct comparison)
    config.width        = 50
    config.height       = 50
    config.init_mothers = 40
    config.init_food    = 120
    # Ecological pressure (Phase 5 addition over Phase 4)
    config.infant_starvation_multiplier = INFANT_STARVATION_MULT
    config.birth_scatter_radius         = scatter_radius
    # Pure genetic selection — no plasticity (clean signal, Phase 6 adds this)
    config.plasticity_enabled          = False
    config.plasticity_kin_conditional  = False
    config.children_enabled            = True
    config.care_enabled                = True
    config.reproduction_enabled        = True
    config.mutation_enabled            = True
    return config


# =============================================================================
# Stage: survival_gate (~10 generations)
# =============================================================================

def _run_survival_gate(seed: int) -> dict:
    """Viability check: 1000 ticks with Phase 5 ecological pressure.

    Population must reach ≥10 mothers at tick 1000.
    If it fails, the full run will also fail — skip it and log.
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
        note=(
            "Phase 5 viability check (10 gens). Requires ≥10 mothers at tick 1000. "
            "infant_starvation_multiplier=1.65: child dies at tick ~75 without care (~3 feedings needed)."
        ),
    )

    genomes = _make_phase4_baseline_genomes(config.init_mothers)
    sim = Simulation(config)
    sim.initialize(genomes)

    population_history = []
    while sim.tick < config.max_ticks:
        sim.step()
        sim.tick += 1
        population_history.append(len([m for m in sim.mothers if m.alive]))
        if population_history[-1] == 0:
            break

    final_pop = population_history[-1] if population_history else 0
    survived  = final_pop >= 10

    with open(os.path.join(output_dir, "population_history.json"), "w") as f:
        json.dump({"population": population_history}, f)

    print(f"\n[phase5 | survival_gate] Output: {output_dir}")
    print(f"  Final population : {final_pop} mothers (threshold: >=10)")
    print(f"  Result           : {'PASSED' if survived else 'FAILED — population collapsed under ecological pressure'}")

    return {
        "survived":       survived,
        "final_pop":      final_pop,
        "ticks_survived": len(population_history),
        "output_dir":     output_dir,
    }


# =============================================================================
# Stage: evolution (Phase 5a — 10,000 ticks, matches Phase 4 duration)
# =============================================================================

def _run_evolution(seed: int, stage: str = "evolution",
                   scatter_radius: int = BIRTH_SCATTER_RADIUS) -> str:
    config = _make_config(seed, scatter_radius=scatter_radius)
    config.max_ticks = 10000  # ~98 generations; matches Phase 4 Scripts 05/06

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
        phase4_neutral_baseline=PHASE4_NEUTRAL_CARE_WEIGHT,
        note=(
            "Phase 5a — Ecological Emergence. Phase 4 baseline init (care=0.80, forage=1.0, self~U). "
            "infant_starvation_multiplier=1.65: child dies at tick ~75 without care (~3 feedings needed). "
            "birth_scatter_radius=2: natal philopatry amplifies effective r. "
            "Plasticity OFF — any care rise above 0.784 is pure natural selection."
            if stage == "evolution" else
            "Phase 5b — Dispersal control. Same as 5a but birth_scatter_radius=5 (Phase 4 standard). "
            "Tests whether natal philopatry is necessary or if infant dependency alone suffices."
        ),
    )

    genomes = _make_phase4_baseline_genomes(config.init_mothers)
    sim = Simulation(config)
    sim.initialize(genomes)

    population_history   = []
    energy_history       = []
    generation_snapshots = []
    SNAPSHOT_INTERVAL    = 200  # matches Phase 4 Script 05

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

    alive_m_final = [m for m in sim.mothers if m.alive]
    n = len(alive_m_final)
    final_cw = sum(m.genome.care_weight for m in alive_m_final) / n if n else 0.0

    print(f"\n[phase5 | {stage}] Output: {output_dir}")
    print(f"  Surviving mothers     : {n}")
    print(f"  Final avg care_weight : {final_cw:.4f}  (Phase 4 neutral baseline: {PHASE4_NEUTRAL_CARE_WEIGHT})")
    print(f"  Selection gradient r  : {grad:.4f}  (Phase 4 baseline: {PHASE4_NEUTRAL_R})"
          if grad is not None else "  Selection gradient r  : N/A (insufficient birth data)")
    print(f"  genome_fallback_count : {sim.genome_fallback_count}  (must be 0)")
    return output_dir


# =============================================================================
# Stage: zeroshot (Phase 5c — genome assimilation precursor for Phase 6)
# =============================================================================

def _run_zeroshot(seed: int, source_dir: str) -> str:
    """Load evolved Phase 5 genomes; run 1000 ticks without reproduction/mutation/plasticity.

    Records care behavior encoded purely in the evolved genome.
    This is a Phase 6 precursor — the assimilation test proper is in Phase 6.
    """
    genomes   = _load_genomes(source_dir)
    n_mothers = len(genomes)

    config = Config()
    config.seed         = seed
    config.init_mothers = n_mothers
    config.init_food    = n_mothers * 4
    config.width        = 50
    config.height       = 50
    config.max_ticks    = 1000
    config.infant_starvation_multiplier = INFANT_STARVATION_MULT
    config.birth_scatter_radius         = BIRTH_SCATTER_RADIUS
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
            "Phase 5c: zero-shot genome test (Phase 6 precursor). "
            "Evolved genomes, no plasticity/reproduction/mutation. "
            "care_window rate measures care encoded in genome vs Phase 6 plasticity baseline."
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

    window = _care_window_metrics(
        sim.logger.care_records, population_history, config.maturity_age
    )
    window_rate = window["care_per_mother_tick_in_window"]

    metrics = {
        "stage":                    "zeroshot",
        "source_dir":               source_dir,
        "successful_care_events":   successful_care,
        "surviving_mothers":        len([m for m in sim.mothers if m.alive]),
        "care_per_mother_tick_all": care_per_m_tick,
        "total_mother_ticks":       total_m_ticks,
        "care_window":              window,
        "note": (
            "Zero-shot care rate for Phase 6 comparison. "
            "Phase 6 will add plasticity to these evolved genomes and test Baldwin assimilation."
        ),
    }
    with open(os.path.join(output_dir, "zeroshot_metrics.json"), "w") as f:
        json.dump(metrics, f, indent=2)

    generate_all_plots(output_dir)

    print(f"\n[phase5 | zeroshot] Output: {output_dir}")
    print(f"  Source genomes       : {source_dir}")
    print(f"  Surviving mothers    : {metrics['surviving_mothers']} / {n_mothers}")
    print(f"  Care/m-tick (window) : {window_rate:.5f}  (Phase 6 will compare with plasticity-enabled)")
    return output_dir


# =============================================================================
# Entry point
# =============================================================================

def run(seed: int = 42, stage: str = "evolution", source_dir: str = None) -> str | dict:
    """
    stage:
      'survival_gate'  — 1000-tick viability check (returns dict, not str)
      'evolution'      — Phase 5a: 10,000 ticks, birth_scatter_radius=2
      'control'        — Phase 5b: 10,000 ticks, birth_scatter_radius=5 (Phase 4 standard)
      'zeroshot'       — Phase 5c: genome assimilation precursor (requires source_dir)
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
    # Step 1: Survival gate — must pass before committing to full run
    gate = run(seed=42, stage="survival_gate")
    if not gate["survived"]:
        print("\nSurvival gate FAILED. Population collapsed under mult=3.0 pressure.")
        import sys
        sys.exit(1)

    # Step 2: Phase 5a — full evolution with natal philopatry (scatter=2)
    evo_dir = run(seed=42, stage="evolution")

    # Step 3: Phase 5b — dispersal control (scatter=5, Phase 4 standard)
    run(seed=42, stage="control")

    # Step 4: Zero-shot genome test (Phase 6 precursor)
    run(seed=42, stage="zeroshot", source_dir=evo_dir)
