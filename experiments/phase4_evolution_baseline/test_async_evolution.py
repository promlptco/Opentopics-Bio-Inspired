"""Phase 4 Prerequisite: Asynchronous Evolution Sanity Test

Verifies that the simulation's evolutionary mechanics work correctly before
committing to 10,000-tick multi-seed runs.

Five checks (ALL must pass):
  1. Birth events occur         -- reproduction is active
  2. Generations progress       -- children mature and inherit genomes
  3. Async generation overlap   -- multiple generations coexist at tick 1000
  4. Genome variation in births -- mutation produces diversity (SD > 0.01)
  5. Population survives        -- at least 3 mothers alive at tick 2000

Output: PASS or FAIL per check. Phase 4 may only proceed if ALL pass.
"""
import sys
import os

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, PROJECT_ROOT)

import random as _random
from config import Config
from simulation.simulation import Simulation
from evolution.genome import Genome
from utils.experiment import set_seed

SEED          = 42
TEST_TICKS    = 2000
SNAPSHOT_TICK = 1000


def _make_neutral_genomes(n: int) -> list[Genome]:
    return [
        Genome(
            care_weight=_random.uniform(0.0, 1.0),
            forage_weight=_random.uniform(0.0, 1.0),
            self_weight=_random.uniform(0.0, 1.0),
        )
        for _ in range(n)
    ]


def _sd(values: list[float]) -> float:
    n = len(values)
    if n < 2:
        return 0.0
    m = sum(values) / n
    return (sum((x - m) ** 2 for x in values) / (n - 1)) ** 0.5


def run_test() -> bool:
    config = Config()
    config.seed                         = SEED
    config.init_mothers                 = 12
    config.init_food                    = 45
    config.max_ticks                    = TEST_TICKS
    config.infant_starvation_multiplier = 1.0
    config.birth_scatter_radius         = 5
    config.plasticity_enabled           = False
    config.plasticity_kin_conditional   = False
    config.children_enabled             = True
    config.care_enabled                 = True
    config.reproduction_enabled         = True
    config.mutation_enabled             = True

    set_seed(SEED)
    genomes = _make_neutral_genomes(config.init_mothers)
    sim = Simulation(config)
    sim.initialize(genomes)

    population_history: list[int] = []
    gen_snapshot: dict | None = None

    while sim.tick < TEST_TICKS:
        sim.step()
        sim.tick += 1
        alive = [m for m in sim.mothers if m.alive]
        population_history.append(len(alive))
        if sim.tick == SNAPSHOT_TICK and alive:
            gens = [m.generation for m in alive]
            gen_snapshot = {
                "min_gen": min(gens),
                "max_gen": max(gens),
                "n_alive": len(alive),
            }

    births = sim.logger.birth_records
    final_pop = population_history[-1] if population_history else 0

    results: list[tuple[str, bool, str]] = []

    # Check 1: Birth events occur (>=20 births in 2000 ticks)
    n_births = len(births)
    results.append(("Birth events occur (>= 20 births)", n_births >= 20, f"n_births={n_births}"))

    # Check 2: Generations progress (max mother_generation in births >= 5)
    max_gen_birth = max((b.mother_generation for b in births), default=0)
    results.append(("Generations progress (max_gen >= 5)", max_gen_birth >= 5, f"max_gen={max_gen_birth}"))

    # Check 3: Async generation overlap at tick 1000 (range >= 2)
    if gen_snapshot:
        gen_range = gen_snapshot["max_gen"] - gen_snapshot["min_gen"]
        t3 = gen_range >= 2
        results.append((
            f"Async overlap at tick {SNAPSHOT_TICK} (gen_range >= 2)",
            t3,
            f"min={gen_snapshot['min_gen']} max={gen_snapshot['max_gen']} range={gen_range}",
        ))
    else:
        results.append((
            f"Async overlap at tick {SNAPSHOT_TICK} (gen_range >= 2)",
            False,
            "no snapshot -- population extinct at tick 1000",
        ))

    # Check 4: Genome variation (SD of care_weight across births > 0.01)
    cw_sd = _sd([b.mother_care_weight for b in births]) if births else 0.0
    results.append(("Genome variation in births (SD > 0.01)", cw_sd > 0.01, f"cw_sd={cw_sd:.4f}"))

    # Check 5: Population survives (>= 3 mothers at tick 2000)
    results.append(("Population survives (>= 3 mothers at end)", final_pop >= 3, f"final_pop={final_pop}"))

    # Report
    print(f"\n=== Phase 4 Async Evolution Sanity Test  (seed={SEED}, {TEST_TICKS} ticks) ===")
    print(f"  {'Check':<55}  {'Result':>6}  Detail")
    print("  " + "-" * 85)
    all_pass = True
    for name, passed, detail in results:
        tag = "PASS" if passed else "FAIL"
        if not passed:
            all_pass = False
        print(f"  {name:<55}  {tag:>6}  {detail}")
    print("  " + "-" * 85)
    if all_pass:
        print("\n  [ALL PASS]  Asynchronous evolution is working correctly.")
        print("  Phase 4 main run may proceed.\n")
    else:
        print("\n  [FAILED]  One or more checks failed.")
        print("  Investigate before proceeding to Phase 4.\n")
    return all_pass


if __name__ == "__main__":
    passed = run_test()
    sys.exit(0 if passed else 1)
