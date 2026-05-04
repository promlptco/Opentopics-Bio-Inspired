"""
Test 07 — Blocking Engine Fixes (Phase 0)

Validates the four blocking engine fixes identified in the repository audit:

  R01 — update_state() now uses linear energy depletion (energy -= hunger_rate/tick).
  R02 — core Simulation uses choose_motivation() (new environmental-cue model).
  R04 — Simulation.initialize() reads genome weights from config.
  R05 — matured children are logged with cause="matured", not cause="hunger".
"""
import sys
import os

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, PROJECT_ROOT)

import csv
from config import Config
from simulation.simulation import Simulation
from agents.mother import MotherAgent
from agents.child import ChildAgent
from evolution.genome import Genome

MODULE_NUM = "07"
DEFAULT_SEED = 42
RUN_NUM = 1
TAG = f"test{MODULE_NUM}_{DEFAULT_SEED}_{RUN_NUM}"

_results: list[dict] = []


def _log(name: str, detail: str = "") -> None:
    _results.append({"test_name": name, "status": "PASS", "detail": detail})
    print(f"[PASS] {name}")


# ─────────────────────────────────────────────────────────────────────────────
# R01 — Linear energy depletion
# ─────────────────────────────────────────────────────────────────────────────

def test_linear_energy_depletion():
    """update_state() must deplete energy by exactly hunger_rate per tick."""
    genome = Genome()
    mother = MotherAgent(0, 0, lineage_id=0, generation=0, genome=genome)
    hunger_rate = 0.008
    e0 = mother.energy  # 1.0

    for _ in range(50):
        mother.update_state(hunger_rate)

    expected = max(0.0, e0 - 50 * hunger_rate)
    assert abs(mother.energy - expected) < 1e-9, (
        f"Expected energy {expected:.6f} after 50 ticks at rate {hunger_rate}, "
        f"got {mother.energy:.6f}. Old accumulating-hunger model may still be active."
    )
    _log("test_linear_energy_depletion",
         f"e0={e0};e50={mother.energy:.6f};expected={expected:.6f};hunger_rate={hunger_rate}")


def test_update_state_rate_independence():
    """Energy after N ticks must equal e0 - N*rate, not depend on accumulated hunger.

    With the old model (hunger += rate; energy -= hunger*0.01), energy at t=100
    under rate=0.005 would be ~0.75 (fast drain after hunger saturates).
    With the new linear model it must be exactly 1.0 - 100*0.005 = 0.5.
    """
    genome = Genome()
    mother = MotherAgent(0, 0, lineage_id=0, generation=0, genome=genome)
    hunger_rate = 0.005
    e0 = 1.0

    for _ in range(100):
        mother.update_state(hunger_rate)

    expected_linear = max(0.0, e0 - 100 * hunger_rate)  # = 0.5
    assert abs(mother.energy - expected_linear) < 1e-9, (
        f"Energy should be {expected_linear:.6f} (linear model) after 100 ticks, "
        f"got {mother.energy:.6f}. Deviation suggests the old accumulating model."
    )
    _log("test_update_state_rate_independence",
         f"e100={mother.energy:.6f};expected_linear={expected_linear:.6f};hunger_rate={hunger_rate}")


# ─────────────────────────────────────────────────────────────────────────────
# R04 — Config genome weights applied in Simulation.initialize()
# ─────────────────────────────────────────────────────────────────────────────

def test_config_care_weight_zero_applied():
    """config.care_weight=0.0 must be reflected in every initial mother's genome."""
    config = Config()
    config.seed = DEFAULT_SEED
    config.init_mothers = 6
    config.care_weight = 0.0
    config.forage_weight = 1.0
    config.self_weight = 1.0
    config.children_enabled = False
    config.reproduction_enabled = False

    sim = Simulation(config)
    sim.initialize()

    for m in sim.mothers:
        assert m.genome.care_weight == 0.0, (
            f"Mother {m.id}: genome.care_weight={m.genome.care_weight}, expected 0.0. "
            "Simulation.initialize() is not reading config.care_weight."
        )
        assert m.genome.forage_weight == 1.0, (
            f"Mother {m.id}: genome.forage_weight={m.genome.forage_weight}, expected 1.0."
        )
    _log("test_config_care_weight_zero_applied",
         f"mothers={len(sim.mothers)};all_care_weight=0.0;all_forage_weight=1.0")


def test_config_nondefault_genome_weights_applied():
    """Non-default genome weights in config must reach every initial mother without mutation."""
    config = Config()
    config.seed = DEFAULT_SEED
    config.init_mothers = 4
    config.care_weight = 0.3
    config.forage_weight = 0.7
    config.self_weight = 0.6
    config.children_enabled = False
    config.reproduction_enabled = False
    config.mutation_enabled = False

    sim = Simulation(config)
    sim.initialize()

    for m in sim.mothers:
        assert abs(m.genome.care_weight - 0.3) < 1e-9, (
            f"care_weight mismatch: got {m.genome.care_weight}, expected 0.3"
        )
        assert abs(m.genome.forage_weight - 0.7) < 1e-9, (
            f"forage_weight mismatch: got {m.genome.forage_weight}, expected 0.7"
        )
        assert abs(m.genome.self_weight - 0.6) < 1e-9, (
            f"self_weight mismatch: got {m.genome.self_weight}, expected 0.6"
        )
    _log("test_config_nondefault_genome_weights_applied",
         f"care=0.3;forage=0.7;self=0.6;mothers={len(sim.mothers)}")


# ─────────────────────────────────────────────────────────────────────────────
# R05 — Maturation logged as "matured", not "hunger"
# ─────────────────────────────────────────────────────────────────────────────

def test_matured_flag_exists_and_defaults_false():
    """ChildAgent must have a matured attribute that defaults to False."""
    child = ChildAgent(0, 0, lineage_id=0, generation=1, mother_id=0)
    assert hasattr(child, "matured"), "ChildAgent must have a 'matured' attribute"
    assert child.matured is False, f"matured should default to False, got {child.matured}"
    child.matured = True
    assert child.matured is True
    _log("test_matured_flag_exists_and_defaults_false", "matured_attr=exists;default=False")


def test_maturation_logged_as_matured_not_hunger():
    """Children reaching maturity_age must appear in death log with cause='matured'.

    Setup: slow hunger (0.004/tick) so children survive to maturity_age=100 without care.
    Ample food so mothers survive the full 110 ticks.
    care_weight=0.0 (default) means no active feeding — children mature purely on
    their own hunger trajectory.
    """
    config = Config()
    config.seed = DEFAULT_SEED
    config.init_mothers = 3
    config.care_weight = 0.0          # no feeding — children mature under their own hunger
    config.forage_weight = 1.0
    config.self_weight = 1.0
    config.children_enabled = True
    config.reproduction_enabled = False
    config.mutation_enabled = False
    config.init_food = 300            # ample food to keep mothers alive
    config.hunger_rate = 0.004        # 0.004 * 100 = 0.40 at maturity; well below death (1.0)
    config.max_ticks = 115            # past maturity_age=100

    sim = Simulation(config)
    sim.initialize()

    for _ in range(115):
        sim.step()

    child_deaths = [d for d in sim.logger.death_records if d.agent_type == "child"]
    matured = [d for d in child_deaths if d.cause == "matured"]
    hunger  = [d for d in child_deaths if d.cause == "hunger"]

    print(f"  child deaths: total={len(child_deaths)}, matured={len(matured)}, hunger={len(hunger)}")

    assert len(matured) > 0, (
        "Expected at least one cause='matured' death record after tick 100. "
        "Check that _check_maturation sets child.matured=True before die()."
    )
    _log("test_maturation_logged_as_matured_not_hunger",
         f"total_child_deaths={len(child_deaths)};matured={len(matured)};hunger={len(hunger)}")


# ─────────────────────────────────────────────────────────────────────────────
# R02 — choose_motivation() integrated into core Simulation
# ─────────────────────────────────────────────────────────────────────────────

def test_choose_motivation_care_pathway_accessible():
    """With care_weight=0.5 and children present, care records must be produced.

    This confirms that the choose_motivation() care pathway is reachable in the
    core Simulation after the R02 fix.  If choose_domain() (old method) were
    still used, care would still be selected — so this test primarily confirms
    the new path does not crash and the care action executes correctly.
    """
    config = Config()
    config.seed = DEFAULT_SEED
    config.init_mothers = 5
    config.care_weight = 0.5
    config.forage_weight = 1.0
    config.self_weight = 1.0
    config.care_enabled = True
    config.children_enabled = True
    config.reproduction_enabled = False
    config.mutation_enabled = False
    config.init_food = 80
    config.hunger_rate = 0.004        # slow enough for children to survive and be cared for
    config.max_ticks = 200

    sim = Simulation(config)
    sim.initialize()

    for _ in range(200):
        sim.step()

    care_records = sim.logger.care_records
    print(f"  care_weight=0.5: care_records={len(care_records)}")

    assert len(care_records) > 0, (
        "Expected some care records with care_weight=0.5 and children present. "
        "The care pathway in choose_motivation() may be broken or unreachable."
    )
    _log("test_choose_motivation_care_pathway_accessible",
         f"care_records={len(care_records)};care_weight=0.5;ticks=200;mothers=5")


def test_simulation_runs_without_crash_new_motivation_model():
    """Core Simulation must complete 300 ticks without error using choose_motivation()."""
    config = Config()
    config.seed = DEFAULT_SEED
    config.init_mothers = 8
    config.care_weight = 0.0
    config.forage_weight = 1.0
    config.self_weight = 1.0
    config.care_enabled = False       # mother-only baseline — mirrors Phase 2 scope
    config.children_enabled = False
    config.reproduction_enabled = False
    config.mutation_enabled = False
    config.init_food = 60
    config.max_ticks = 300

    sim = Simulation(config)
    sim.initialize()

    completed = 0
    for _ in range(300):
        sim.step()
        completed += 1

    assert completed == 300, f"Simulation stopped early at tick {completed}"
    _log("test_simulation_runs_without_crash_new_motivation_model",
         f"completed_ticks={completed};care_enabled=False;children_enabled=False")


# ─────────────────────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    test_linear_energy_depletion()
    test_update_state_rate_independence()
    test_config_care_weight_zero_applied()
    test_config_nondefault_genome_weights_applied()
    test_matured_flag_exists_and_defaults_false()
    test_maturation_logged_as_matured_not_hunger()
    test_choose_motivation_care_pathway_accessible()
    test_simulation_runs_without_crash_new_motivation_model()

    out_dir = os.path.join(PROJECT_ROOT, "outputs", "phase1_mechanics_tests", TAG)
    os.makedirs(out_dir, exist_ok=True)

    with open(os.path.join(out_dir, "logs.csv"), "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["test_name", "status", "detail"])
        writer.writeheader()
        writer.writerows(_results)

    print(f"\n=== Test 07 — Engine Fixes: ALL TESTS PASSED ===")
    print(f"Logs saved -> outputs/phase1_mechanics_tests/{TAG}/logs.csv")
