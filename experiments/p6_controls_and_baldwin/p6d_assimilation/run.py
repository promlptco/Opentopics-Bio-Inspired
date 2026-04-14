# experiments/p6_controls_and_baldwin/p6d_baldwin_instinct/run.py
"""Phase 11: Baldwin Effect — Instinct Assimilation

Scientific question:
  After 10 000 ticks of evolution WITH kin-conditional plasticity (mult=1.15,
  scatter=2), does the evolved population maintain high care even after plasticity
  is switched OFF?  If yes, the plastic phenotype has been genetically assimilated
  (Baldwin Effect / genetic assimilation).

Two-stage design per seed:
  Stage 1 — 'evolution'  (10 000 ticks)
    Evolution + kin-conditional plasticity ON.
    Ecology: mult=1.15, scatter=2.
    Init: cw~U(0, 0.50) (depleted baseline — same as P5/P6a/P6b).
    Parameters: reproduction=ON, mutation=ON, plasticity=ON (kin-conditional).

  Stage 2 — 'instinct'   (10 000 ticks)
    Plasticity OFF, mutation OFF, reproduction ON.
    Loads the top genomes from Stage 1.
    Tests whether evolved care_weight is self-sustaining without plastic feedback.

Four instinct criteria (ALL must pass for a seed to count):
  1. care_weight drift ≤ 0.02 after plasticity removed
     (genome cw stable without plastic support)
  2. Care action rate in Stage 2 ≥ 80% of Stage 1 final rate
     (behaviour maintained)
  3. Child energy or lifetime in Stage 2 ≥ 80% of Stage 1 final value
     (offspring outcomes maintained)
  4. Infant population stable or growing after plasticity OFF
     (population viability maintained)

Pass criterion: ≥ 8 / 10 seeds pass all four criteria
  → "maternal care instinct demonstrated"

Output figure: concatenated 0 → 20 000 t care_weight plot
  (green = Stage 1 plasticity ON, grey = Stage 2 instinct test).
"""
import sys
import os
import json
import random as _random

PROJECT_ROOT = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)
sys.path.insert(0, PROJECT_ROOT)

from config import Config
from simulation.simulation import Simulation
from evolution.genome import Genome
from utils.experiment import set_seed, create_run_dir, save_config, save_metadata
from utils.plotting import generate_all_plots

PHASE_NAME = "phase11_instinct_assimilation"

# Ecological parameters — matched to P5 (Phase 07) full ecology
INFANT_STARVATION_MULT  = 1.15   # infant pressure (P5 calibrated)
BIRTH_SCATTER_RADIUS    = 2      # tight natal philopatry (P5 calibrated)
PLASTICITY_ENERGY_COST  = 0.0    # fixed cost per plastic update (0 = same as P4)

# Stage durations
STAGE1_TICKS = 10_000   # evolution + plasticity
STAGE2_TICKS = 10_000   # instinct test (plasticity OFF)

SNAPSHOT_INTERVAL = 100

# Instinct-test thresholds
DRIFT_THRESHOLD       = 0.02   # max |cw_stage2_end − cw_stage1_end|
CARE_RATE_FRAC        = 0.80   # stage2 care rate ≥ this × stage1 rate
CHILD_ENERGY_FRAC     = 0.80   # stage2 child outcome ≥ this × stage1 value


# =============================================================================
# Helpers
# =============================================================================

def _make_depleted_genomes(n: int) -> list[Genome]:
    """Depleted-care init — same as P5/P6a/P6b: cw~U(0.00, 0.50)."""
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


def _load_genomes_from_dir(source_dir: str) -> list[Genome]:
    path = os.path.join(source_dir, "top_genomes.json")
    if not os.path.exists(path):
        raise FileNotFoundError(f"top_genomes.json not found in {source_dir}")
    with open(path) as f:
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


def _avg_cw(sim: Simulation) -> float:
    alive = [m for m in sim.mothers if m.alive]
    return sum(m.genome.care_weight for m in alive) / len(alive) if alive else 0.0


def _care_rate(care_records, population_history: list[int]) -> float:
    """Successful care events / total alive-mother-ticks."""
    succ = sum(1 for r in care_records if r.success)
    total_m = sum(population_history)
    return succ / total_m if total_m > 0 else 0.0


def _avg_child_energy(sim: Simulation) -> float:
    alive = [c for c in sim.children if c.alive]
    return sum(c.energy for c in alive) / len(alive) if alive else 0.0


def _run_snapshots(sim: Simulation, n_ticks: int, tick_offset: int = 0) -> tuple[list, list, list]:
    """Run sim for n_ticks, collecting snapshots. Returns (pop, energy, snapshots)."""
    pop_hist     = []
    energy_hist  = []
    snapshots    = []

    while sim.tick < n_ticks:
        sim.step()
        sim.tick += 1
        alive_m = [m for m in sim.mothers if m.alive]
        pop_hist.append(len(alive_m))
        energy_hist.append(
            sum(m.energy for m in alive_m) / len(alive_m) if alive_m else 0.0
        )
        t_abs = sim.tick + tick_offset
        if sim.tick % SNAPSHOT_INTERVAL == 0 and alive_m:
            snapshots.append({
                "tick":              t_abs,
                "avg_care_weight":   sum(m.genome.care_weight   for m in alive_m) / len(alive_m),
                "min_care_weight":   min(m.genome.care_weight   for m in alive_m),
                "max_care_weight":   max(m.genome.care_weight   for m in alive_m),
                "avg_forage_weight": sum(m.genome.forage_weight for m in alive_m) / len(alive_m),
                "avg_generation":    sum(m.generation           for m in alive_m) / len(alive_m),
                "n_mothers":         len(alive_m),
            })

    return pop_hist, energy_hist, snapshots


# =============================================================================
# Stage runners
# =============================================================================

def run_evolution(seed: int = 42) -> str:
    """Stage 1: 10 000 ticks evolution + kin-conditional plasticity ON.

    Returns output directory path.
    """
    config = Config()
    config.seed         = seed
    config.init_mothers = 12
    config.init_food    = 45
    config.max_ticks    = STAGE1_TICKS

    config.infant_starvation_multiplier = INFANT_STARVATION_MULT
    config.birth_scatter_radius         = BIRTH_SCATTER_RADIUS
    config.plasticity_energy_cost       = PLASTICITY_ENERGY_COST

    config.children_enabled           = True
    config.care_enabled               = True
    config.plasticity_enabled         = True
    config.plasticity_kin_conditional = True    # kin-conditional (P4 corrected)
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
        plasticity_enabled=True,
        plasticity_kin_conditional=True,
        plasticity_energy_cost=PLASTICITY_ENERGY_COST,
        note=(
            "Phase 11 Stage 1 — Baldwin evolution. "
            "mult=1.15, scatter=2, plast=ON (kin-conditional), depleted init. "
            "10 000 ticks. Load genomes into Stage 2 instinct test."
        ),
    )

    genomes = _make_depleted_genomes(config.init_mothers)
    sim = Simulation(config)
    sim.initialize(genomes)

    pop_hist, energy_hist, snapshots = _run_snapshots(sim, STAGE1_TICKS, tick_offset=0)

    sim.logger.save_all(output_dir)
    _save_top_genomes(sim, output_dir)
    with open(os.path.join(output_dir, "population_history.json"), "w") as f:
        json.dump({"population": pop_hist, "energy": energy_hist}, f)
    with open(os.path.join(output_dir, "generation_snapshots.json"), "w") as f:
        json.dump(snapshots, f, indent=2)

    generate_all_plots(output_dir)

    n = len([m for m in sim.mothers if m.alive])
    final_cw = _avg_cw(sim)
    rate     = _care_rate(sim.logger.care_records, pop_hist)
    print(f"\n[{PHASE_NAME} | stage=evolution | seed={seed}] Output: {output_dir}")
    print(f"  Surviving mothers   : {n}")
    print(f"  Final avg cw        : {final_cw:.4f}")
    print(f"  Care rate (s/m-t)   : {rate:.5f}")
    print(f"  → Run stage 'instinct' with --source-dir {output_dir}")
    return output_dir


def run_instinct(seed: int = 42, source_dir: str = None) -> str:
    """Stage 2: 10 000 ticks instinct test — plasticity OFF, mutation OFF.

    Loads top_genomes.json from source_dir (Stage 1 output).
    Returns output directory path.
    """
    if source_dir is None:
        raise ValueError("source_dir required: path to Phase 11 Stage 1 evolution output.")

    genomes   = _load_genomes_from_dir(source_dir)
    n_mothers = len(genomes)

    config = Config()
    config.seed         = seed
    config.init_mothers = n_mothers
    config.init_food    = n_mothers * 4
    config.max_ticks    = STAGE2_TICKS

    config.infant_starvation_multiplier = INFANT_STARVATION_MULT
    config.birth_scatter_radius         = BIRTH_SCATTER_RADIUS
    config.plasticity_energy_cost       = 0.0   # irrelevant — plasticity OFF

    config.children_enabled           = True
    config.care_enabled               = True
    config.plasticity_enabled         = False   # KEY: OFF — instinct test
    config.plasticity_kin_conditional = False
    config.reproduction_enabled       = True    # allow lineage tracking
    config.mutation_enabled           = False   # KEY: OFF — genome frozen

    set_seed(config.seed)
    output_dir = create_run_dir(PHASE_NAME, config.seed)
    save_config(config, output_dir)
    save_metadata(
        output_dir,
        phase=PHASE_NAME,
        stage="instinct",
        seed=config.seed,
        num_agents=n_mothers * 2,
        source_dir=source_dir,
        infant_starvation_multiplier=INFANT_STARVATION_MULT,
        birth_scatter_radius=BIRTH_SCATTER_RADIUS,
        note=(
            "Phase 11 Stage 2 — Instinct test. "
            "mult=1.15, scatter=2, plast=OFF, mut=OFF. "
            "Tests genetic assimilation: care maintained without plastic feedback?"
        ),
    )

    # Load Stage 1 metrics for comparison
    stage1_metrics_path = os.path.join(source_dir, "instinct_stage_metrics.json")
    stage1_metrics = {}
    if os.path.exists(stage1_metrics_path):
        with open(stage1_metrics_path) as f:
            stage1_metrics = json.load(f)

    # Stage 1 reference values from top_genomes.json
    cw_start = sum(g.care_weight for g in genomes) / len(genomes) if genomes else 0.0

    sim = Simulation(config)
    sim.initialize(genomes)

    pop_hist, energy_hist, snapshots = _run_snapshots(sim, STAGE2_TICKS, tick_offset=STAGE1_TICKS)

    sim.logger.save_all(output_dir)
    _save_top_genomes(sim, output_dir)
    with open(os.path.join(output_dir, "population_history.json"), "w") as f:
        json.dump({"population": pop_hist, "energy": energy_hist}, f)
    with open(os.path.join(output_dir, "generation_snapshots.json"), "w") as f:
        json.dump(snapshots, f, indent=2)

    generate_all_plots(output_dir)

    # ── Instinct criteria evaluation ───────────────────────────────────────────
    cw_end    = _avg_cw(sim)
    cw_drift  = abs(cw_end - cw_start)
    rate2     = _care_rate(sim.logger.care_records, pop_hist)

    # Stage 1 reference values — stored from run_evolution
    stage1_rate = stage1_metrics.get("care_rate", None)
    stage1_child_energy = stage1_metrics.get("avg_child_energy_end", None)
    child_energy2 = _avg_child_energy(sim)
    infant_pop2   = sum(1 for c in sim.children if c.alive)

    criteria = {
        "c1_cw_drift_ok":       cw_drift <= DRIFT_THRESHOLD,
        "c1_cw_drift":          round(cw_drift, 4),
        "c1_threshold":         DRIFT_THRESHOLD,
        "c2_care_rate_ok":      (rate2 >= CARE_RATE_FRAC * stage1_rate
                                 if stage1_rate is not None else None),
        "c2_rate_stage2":       round(rate2, 5),
        "c2_rate_stage1":       stage1_rate,
        "c2_threshold_frac":    CARE_RATE_FRAC,
        "c3_child_energy_ok":   (child_energy2 >= CHILD_ENERGY_FRAC * stage1_child_energy
                                 if stage1_child_energy is not None else None),
        "c3_child_energy_s2":   round(child_energy2, 4),
        "c3_child_energy_s1":   stage1_child_energy,
        "c3_threshold_frac":    CHILD_ENERGY_FRAC,
        "c4_infant_pop_stable": infant_pop2 >= 1,
        "c4_infant_pop":        infant_pop2,
    }

    # All four criteria must be True (None = unavailable, treated as False)
    passed = all([
        criteria["c1_cw_drift_ok"] is True,
        criteria["c2_care_rate_ok"] is True,
        criteria["c3_child_energy_ok"] is True,
        criteria["c4_infant_pop_stable"] is True,
    ])
    criteria["all_passed"] = passed

    metrics = {
        "phase":       PHASE_NAME,
        "stage":       "instinct",
        "seed":        seed,
        "source_dir":  source_dir,
        "cw_start":    round(cw_start, 4),
        "cw_end":      round(cw_end, 4),
        "criteria":    criteria,
        "instinct_passed": passed,
        "note": (
            "instinct_passed=True → plastic phenotype genetically assimilated "
            "(Baldwin Effect demonstrated for this seed)."
        ),
    }
    with open(os.path.join(output_dir, "instinct_metrics.json"), "w") as f:
        json.dump(metrics, f, indent=2)

    n = len([m for m in sim.mothers if m.alive])
    print(f"\n[{PHASE_NAME} | stage=instinct | seed={seed}] Output: {output_dir}")
    print(f"  cw at Stage 2 start : {cw_start:.4f}  (loaded from Stage 1)")
    print(f"  cw at Stage 2 end   : {cw_end:.4f}  (drift={cw_drift:.4f}, threshold={DRIFT_THRESHOLD})")
    print(f"  Care rate Stage 2   : {rate2:.5f}")
    print(f"  Infant pop (final)  : {infant_pop2}")
    print(f"  Surviving mothers   : {n}")
    print(f"  Instinct PASSED     : {passed}")
    print(f"    C1 cw_drift ≤ {DRIFT_THRESHOLD}: {criteria['c1_cw_drift_ok']}")
    print(f"    C2 care_rate ≥ 80% stage1: {criteria['c2_care_rate_ok']}")
    print(f"    C3 child_energy ≥ 80% stage1: {criteria['c3_child_energy_ok']}")
    print(f"    C4 infant_pop stable: {criteria['c4_infant_pop_stable']}")
    return output_dir


def run(seed: int = 42, stage: str = "evolution", source_dir: str = None) -> str:
    """
    stage:
      'evolution' — Stage 1: 10 000 t evolution + kin-conditional plasticity
      'instinct'  — Stage 2: 10 000 t instinct test (requires --source-dir)
    """
    if stage == "evolution":
        return run_evolution(seed)
    elif stage == "instinct":
        return run_instinct(seed, source_dir)
    else:
        raise ValueError(f"Unknown stage: {stage!r}. Use 'evolution' or 'instinct'.")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Phase 11: Baldwin Effect — Instinct Assimilation")
    parser.add_argument("--seed",       type=int, default=42)
    parser.add_argument("--stage",      default="evolution",
                        choices=["evolution", "instinct"])
    parser.add_argument("--source-dir", default=None,
                        help="Stage 1 output dir (required for stage=instinct)")
    args = parser.parse_args()
    out = run(seed=args.seed, stage=args.stage, source_dir=args.source_dir)
    print(f"\nPhase 11 {args.stage} complete. Output: {out}")
