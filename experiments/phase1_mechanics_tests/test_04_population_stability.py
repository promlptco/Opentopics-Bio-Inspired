"""
Test 04: Population stability
- No immediate extinction
- No immediate explosion
- Deterministic with seed
"""
import sys
import os
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, PROJECT_ROOT)

from config import Config
from simulation.simulation import Simulation

MODULE_NUM = "04"
DEFAULT_SEED = 42
RUN_NUM = 1
TAG = f"test{MODULE_NUM}_{DEFAULT_SEED}_{RUN_NUM}"

_results = []


def _log(name: str, detail: str = "") -> None:
    _results.append({"test_name": name, "status": "PASS", "detail": detail})
    print(f"✓ {name} PASSED")


def _run_sim(config: Config, ticks: int) -> "Simulation":
    sim = Simulation(config)
    sim.initialize()
    for _ in range(ticks):
        sim.step()
    return sim


def test_no_immediate_extinction():
    """Population should not die out in first 100 ticks."""
    config = Config()
    config.init_mothers = 10
    config.max_ticks = 100
    config.seed = DEFAULT_SEED

    sim = _run_sim(config, 100)

    alive = len([m for m in sim.mothers if m.alive])
    print(f"Alive after 100 ticks: {alive}")
    assert alive > 0, "Population should not extinct immediately"
    _log("test_no_immediate_extinction", f"alive_at_t100={alive}")


def test_no_immediate_explosion():
    """Population should not grow unreasonably fast in first 100 ticks.
    
    Not a hard cap test — verifies growth is bounded relative to initial size.
    Threshold: total population must not exceed 5x initial mothers.
    """
    INIT_MOTHERS = 10
    EXPLOSION_THRESHOLD = INIT_MOTHERS * 5  # 50

    config = Config()
    config.init_mothers = INIT_MOTHERS
    config.max_ticks = 100
    config.seed = DEFAULT_SEED

    sim = _run_sim(config, 100)

    total = len(sim.mothers) + len(sim.children)
    print(f"Total population after 100 ticks: {total} (explosion threshold={EXPLOSION_THRESHOLD})")
    assert total < EXPLOSION_THRESHOLD, f"Population grew unreasonably fast: {total} > {EXPLOSION_THRESHOLD}"
    _log("test_no_immediate_explosion", f"total_at_t100={total};init_mothers={INIT_MOTHERS};threshold={EXPLOSION_THRESHOLD}")


def test_deterministic_with_seed():
    """Same seed should produce same result."""
    results = []

    for _ in range(2):
        config = Config()
        config.init_mothers = 5
        config.max_ticks = 50
        config.seed = 12345

        sim = _run_sim(config, 50)
        alive = len([m for m in sim.mothers if m.alive])
        results.append(alive)

    print(f"Run 1: {results[0]}, Run 2: {results[1]}")
    assert results[0] == results[1], "Same seed should give same result"
    _log("test_deterministic_with_seed", f"run1={results[0]};run2={results[1]};seed=12345")


def test_no_food_causes_extinction():
    """Without food or rest recovery, population should die (pure starvation).

    Children and reproduction are disabled so no new agents with fresh energy
    enter the simulation — this isolates the hunger/energy depletion mechanic.
    """
    config = Config()
    config.init_mothers = 5
    config.init_food = 0
    config.rest_recovery = 0.0
    config.children_enabled = False
    config.reproduction_enabled = False
    config.max_ticks = 200
    config.seed = DEFAULT_SEED

    sim = Simulation(config)
    sim.initialize()

    for _ in range(200):
        sim.world.food_positions.clear()
        sim.step()

    alive = len([m for m in sim.mothers if m.alive])
    print(f"Alive without food: {alive}")
    assert alive == 0, "Should extinct without food"
    _log("test_no_food_causes_extinction",
         f"alive_at_t200={alive};rest_recovery=0;children_enabled=False;reproduction_enabled=False")


if __name__ == "__main__":
    import csv

    test_no_immediate_extinction()
    test_no_immediate_explosion()
    test_deterministic_with_seed()
    test_no_food_causes_extinction()

    out_dir = os.path.join(PROJECT_ROOT, "outputs", "phase1_mechanics_tests", TAG)
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, "logs.csv"), "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["test_name", "status", "detail"])
        writer.writeheader()
        writer.writerows(_results)

    print(f"\n=== All population stability tests PASSED ===")
    print(f"Logs saved → outputs/phase1_mechanics_tests/{TAG}/logs.csv")