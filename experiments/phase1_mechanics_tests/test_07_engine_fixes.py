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
from simulation.world import GridWorld
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
    config.maturity_age = 100         # explicit mechanism window, independent of Config default
    config.infant_starvation_multiplier = 1.0  # no extra pressure so children reach maturity
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


def test_matured_child_does_not_reproduce_same_tick():
    """A child promoted to mother must not spawn a child in the same tick.

    The bug path is:
      _check_maturation() creates a new MotherAgent
      _check_reproduction() runs later in the same step
      the brand-new mother starts at energy=1.0 and may reproduce immediately

    The fix is to place the matured mother on reproduction cooldown.
    """
    config = Config()
    config.seed = DEFAULT_SEED
    config.init_mothers = 1
    config.children_enabled = True
    config.reproduction_enabled = True
    config.mutation_enabled = False
    config.maturity_age = 1
    config.infant_starvation_multiplier = 1.0
    config.hunger_rate = 0.0
    config.reproduction_threshold = -10.0  # deterministic success if cooldown is absent
    config.reproduction_cooldown = 7

    sim = Simulation(config)
    sim.initialize()

    birth_mother = sim.mothers[0]
    birth_mother.cooldown = 999  # isolate the new-mother path

    child = sim.children[0]
    child.age = config.maturity_age
    child.energy = 1.0

    sim._check_maturation()

    assert len(sim.mothers) == 2, f"Expected matured child to become a mother; got {len(sim.mothers)} mothers"
    new_mother = max(sim.mothers, key=lambda m: m.id)
    assert new_mother.cooldown == config.reproduction_cooldown, (
        f"Expected matured mother cooldown={config.reproduction_cooldown}, got {new_mother.cooldown}"
    )
    assert not new_mother.can_reproduce(config.reproduction_threshold), (
        "Matured mother should be blocked from same-tick reproduction by cooldown."
    )

    sim._check_reproduction()

    alive_children = [c for c in sim.children if c.alive]
    spawned_by_new_mother = [c for c in alive_children if c.mother_id == new_mother.id]

    assert not spawned_by_new_mother, (
        "No alive child should be spawned by a newly matured mother in the same tick."
    )

    _log(
        "test_matured_child_does_not_reproduce_same_tick",
        f"mothers={len(sim.mothers)};alive_children={len(alive_children)};cooldown={new_mother.cooldown}",
    )


def test_matured_child_spawn_does_not_stack_with_birth_mother():
    """A matured child promoted to mother must not share a blocking cell with its birth mother."""
    config = Config()
    config.seed = DEFAULT_SEED
    config.init_mothers = 1
    config.children_enabled = True
    config.reproduction_enabled = False
    config.mutation_enabled = False
    config.maturity_age = 1
    config.hunger_rate = 0.0
    config.infant_starvation_multiplier = 1.0

    sim = Simulation(config)
    sim.initialize()

    birth_mother = sim.mothers[0]
    child = sim.children[0]

    # Force the birth mother onto the child's cell before maturation.
    sim.world.occupied.discard(birth_mother.pos)
    birth_mother.move_to(child.x, child.y)
    sim.world.occupied.add(birth_mother.pos)
    child.age = config.maturity_age
    child.energy = 1.0

    sim._check_maturation()

    assert len(sim.mothers) == 2, "Expected both birth mother and matured mother to exist."
    positions = {m.pos for m in sim.mothers}
    assert len(positions) == 2, "Birth mother and matured mother must occupy distinct cells."
    _log(
        "test_matured_child_spawn_does_not_stack_with_birth_mother",
        f"positions={sorted(positions)}",
    )


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


def test_last_motivation_matches_final_domain_after_override():
    """Viewer ring should reflect the executed domain after starvation-floor override.

    Repro path:
      - mother strongly prefers CARE
      - own child is distressed on the same cell
      - mother has no food and is below care_energy_floor
      - engine overrides CARE -> FORAGE

    The viewer reads mother.last_motivation, so it must show FORAGE here rather
    than the pre-override CARE winner.
    """
    config = Config()
    config.seed = DEFAULT_SEED
    config.init_mothers = 1
    config.init_food = 0
    config.children_enabled = True
    config.care_enabled = True
    config.reproduction_enabled = False
    config.mutation_enabled = False
    config.care_weight = 1.0
    config.forage_weight = 0.0
    config.self_weight = 0.0
    config.care_energy_floor = 0.35
    config.hunger_rate = 0.02

    sim = Simulation(config)
    sim.initialize()

    mother = sim.mothers[0]
    child = sim.children[0]

    # Force an overlap state: own child distressed, mother empty-handed and hungry.
    sim.world.occupied.discard(mother.pos)
    mother.move_to(child.x, child.y)
    sim.world.occupied.add(mother.pos)
    mother.energy = 0.20
    mother.held_food = 0
    child.energy = 0.10
    child.hunger = 0.90
    child.update_distress()

    sim.step()

    assert mother.last_motivation != "CARE", (
        f"Expected empty-handed same-cell mother to leave CARE, got {mother.last_motivation!r}"
    )
    _log(
        "test_last_motivation_matches_final_domain_after_override",
        f"last_motivation={mother.last_motivation};last_action={mother.last_action}",
    )


def test_forage_explores_when_no_food_visible():
    """FORAGE should explore stochastically instead of freezing when no food is visible."""
    config = Config()
    config.seed = DEFAULT_SEED
    config.init_mothers = 1
    config.init_food = 0
    config.children_enabled = True
    config.care_enabled = True
    config.reproduction_enabled = False
    config.mutation_enabled = False
    config.care_weight = 1.0
    config.forage_weight = 0.0
    config.self_weight = 0.0
    config.care_energy_floor = 0.35
    config.hunger_rate = 0.02
    config.width = 5
    config.height = 5

    sim = Simulation(config)
    sim.initialize()

    mother = sim.mothers[0]
    child = sim.children[0]

    # Force same-cell, empty-hand state and exercise the FORAGE branch directly.
    sim.world.occupied.discard(mother.pos)
    mother.move_to(child.x, child.y)
    sim.world.occupied.add(mother.pos)
    mother.energy = 0.20
    mother.held_food = 0
    child.energy = 0.10
    child.hunger = 0.90
    child.update_distress()

    start_pos = mother.pos
    sim._execute_action(mother, "forage", [child])

    assert mother.last_action == "FORAGE_EXPLORE", (
        f"Expected stochastic forage exploration, got {mother.last_action!r}"
    )
    assert mother.pos != start_pos, "Mother should move away from the stall cell while exploring."
    _log(
        "test_forage_explores_when_no_food_visible",
        f"start_pos={start_pos};end_pos={mother.pos};last_action={mother.last_action}",
    )


def test_same_cell_empty_handed_mother_does_not_repeat_care():
    """Empty-handed mothers on the child's cell should not keep selecting CARE."""
    config = Config()
    config.seed = DEFAULT_SEED
    config.init_mothers = 1
    config.init_food = 0
    config.children_enabled = True
    config.care_enabled = True
    config.reproduction_enabled = False
    config.mutation_enabled = False
    config.care_weight = 1.0
    config.forage_weight = 0.0
    config.self_weight = 1.0
    config.care_energy_floor = 0.0
    config.hunger_rate = 0.02
    config.width = 5
    config.height = 5

    sim = Simulation(config)
    sim.initialize()

    mother = sim.mothers[0]
    child = sim.children[0]

    sim.world.occupied.discard(mother.pos)
    mother.move_to(child.x, child.y)
    sim.world.occupied.add(mother.pos)
    mother.energy = 0.60
    mother.held_food = 0
    child.energy = 0.10
    child.hunger = 0.90
    child.update_distress()

    sim.step()

    assert mother.last_motivation != "CARE", (
        "Same-cell, empty-handed mother should not keep selecting CARE."
    )
    assert mother.last_action != "FAILED_CARE_EMPTY", (
        "Same-cell, empty-handed mother should re-route to SELF/FORAGE rather than failed care."
    )
    _log(
        "test_same_cell_empty_handed_mother_does_not_repeat_care",
        f"last_motivation={mother.last_motivation};last_action={mother.last_action}",
    )


def test_empty_handed_mother_has_blind_forage_drive():
    """Empty-handed mothers should retain a small forage cue even when no food is visible."""
    mother = MotherAgent(0, 0, lineage_id=0, generation=0, genome=Genome())
    mother.held_food = 0
    cue_empty = mother.compute_forage_cue(
        perception_radius=10,
        nearest_food=None,
        distance_to_food=None,
    )

    mother.held_food = 1
    cue_holding = mother.compute_forage_cue(
        perception_radius=10,
        nearest_food=None,
        distance_to_food=None,
    )

    assert cue_empty > 0.0, "Expected a nonzero exploratory forage cue when empty-handed."
    assert cue_holding == 0.0, "Holding food should still suppress blind forage."
    _log(
        "test_empty_handed_mother_has_blind_forage_drive",
        f"cue_empty={cue_empty};cue_holding={cue_holding}",
    )


def test_self_cue_matches_feasible_self_maintenance():
    """Hunger should drive SELF only when eating is feasible; otherwise fatigue drives rest."""
    mother = MotherAgent(0, 0, lineage_id=0, generation=0, genome=Genome())
    mother.energy = 0.2
    mother.fatigue = 0.7

    mother.held_food = 0
    cue_without_food = mother.compute_self_cue()

    mother.held_food = 1
    cue_with_food = mother.compute_self_cue()

    assert abs(cue_without_food - 0.7) < 1e-9, (
        f"Expected fatigue-driven SELF cue 0.7 without food, got {cue_without_food}"
    )
    assert abs(cue_with_food - 0.8) < 1e-9, (
        f"Expected hunger-driven SELF cue 0.8 with food, got {cue_with_food}"
    )
    _log(
        "test_self_cue_matches_feasible_self_maintenance",
        f"cue_without_food={cue_without_food};cue_with_food={cue_with_food}",
    )


def test_no_valid_child_target_means_no_care_domain():
    """A mother should not sample CARE when no valid child target exists."""
    config = Config()
    config.seed = DEFAULT_SEED
    config.init_mothers = 1
    config.init_food = 0
    config.children_enabled = False
    config.care_enabled = True
    config.reproduction_enabled = False
    config.mutation_enabled = False
    config.food_entropy_alpha = 0.0
    config.food_replace_on_pick = False
    config.continuous_food_rate = 0.0
    config.care_weight = 1.0
    config.forage_weight = 0.0
    config.self_weight = 1.0
    config.hunger_rate = 0.02

    sim = Simulation(config)
    sim.initialize()
    mother = sim.mothers[0]
    mother.energy = 0.4

    sim.step()

    assert mother.last_motivation != "CARE", (
        "Mother should not choose CARE when there is no valid care target."
    )
    _log(
        "test_no_valid_child_target_means_no_care_domain",
        f"last_motivation={mother.last_motivation};last_action={mother.last_action}",
    )


def test_circle_world_bounds_use_inscribed_arena():
    """Circle-world bounds should exclude corners and keep the center valid."""
    world = GridWorld(width=10, height=10, circle_world=True)
    assert not world.in_bounds(0, 0), "Corner cell should be outside the circular arena."
    assert world.in_bounds(5, 5), "Center cell should remain inside the circular arena."
    _log(
        "test_circle_world_bounds_use_inscribed_arena",
        "corner_outside=True;center_inside=True",
    )


def test_blocked_visible_food_uses_detour_instead_of_stalling():
    """Visible food with a blocked path should trigger a detour, not a silent no-op."""
    config = Config()
    config.seed = DEFAULT_SEED
    config.width = 6
    config.height = 6
    config.init_mothers = 0
    config.init_food = 0
    config.children_enabled = False
    config.care_enabled = False
    config.reproduction_enabled = False
    config.mutation_enabled = False
    config.food_perception_radius = 10

    sim = Simulation(config)

    mover = MotherAgent(1, 2, lineage_id=0, generation=0, genome=Genome())
    blockers = [
        MotherAgent(2, 0, 1, 0, Genome()),
        MotherAgent(2, 1, 2, 0, Genome()),
        MotherAgent(2, 2, 3, 0, Genome()),
        MotherAgent(2, 3, 4, 0, Genome()),
        MotherAgent(2, 4, 5, 0, Genome()),
        MotherAgent(2, 5, 6, 0, Genome()),
    ]

    sim.mothers = [mover, *blockers]
    sim._mother_by_id = {m.id: m for m in sim.mothers}
    sim.world.place_entity(mover)
    for blocker in blockers:
        sim.world.place_entity(blocker)
    sim.world.place_food(4, 2)

    start_pos = mover.pos
    sim._execute_action(mover, "forage", [])

    assert mover.last_action == "FORAGE_DETOUR", (
        f"Expected forage detour under unreachable visible path, got {mover.last_action!r}"
    )
    assert mover.pos != start_pos, "Mover should step aside rather than stall in place."
    _log(
        "test_blocked_visible_food_uses_detour_instead_of_stalling",
        f"start_pos={start_pos};end_pos={mover.pos};last_action={mover.last_action}",
    )


# ─────────────────────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────────────────────

def test_forage_explore_avoids_immediate_backtrack_when_possible():
    """Blind forage exploration should avoid a direct one-tick reversal when alternatives exist."""
    config = Config()
    config.seed = DEFAULT_SEED
    config.width = 5
    config.height = 5
    config.init_mothers = 0
    config.init_food = 0
    config.children_enabled = False
    config.care_enabled = False
    config.reproduction_enabled = False
    config.mutation_enabled = False

    sim = Simulation(config)
    mother = MotherAgent(2, 2, lineage_id=0, generation=0, genome=Genome())
    mother.last_pos = (2, 1)
    sim.mothers = [mother]
    sim._mother_by_id = {mother.id: mother}
    sim.world.place_entity(mother)

    sim._execute_action(mother, "forage", [])

    assert mother.last_action == "FORAGE_EXPLORE", (
        f"Expected forage explore action, got {mother.last_action!r}"
    )
    assert mother.pos != (2, 1), "Explore should avoid immediate backtracking when other moves exist."
    _log(
        "test_forage_explore_avoids_immediate_backtrack_when_possible",
        f"end_pos={mother.pos};recorded_last_pos={mother.last_pos}",
    )


def test_blocked_visible_food_avoids_immediate_backtrack_when_detouring():
    """Visible-food detours should not bounce straight back to the prior cell."""
    config = Config()
    config.seed = DEFAULT_SEED
    config.width = 6
    config.height = 6
    config.init_mothers = 0
    config.init_food = 0
    config.children_enabled = False
    config.care_enabled = False
    config.reproduction_enabled = False
    config.mutation_enabled = False
    config.food_perception_radius = 10

    sim = Simulation(config)

    mover = MotherAgent(1, 1, lineage_id=0, generation=0, genome=Genome())
    mover.last_pos = (1, 2)
    blockers = [
        MotherAgent(2, 0, 1, 0, Genome()),
        MotherAgent(2, 1, 2, 0, Genome()),
        MotherAgent(2, 2, 3, 0, Genome()),
        MotherAgent(2, 3, 4, 0, Genome()),
        MotherAgent(2, 4, 5, 0, Genome()),
        MotherAgent(2, 5, 6, 0, Genome()),
    ]

    sim.mothers = [mover, *blockers]
    sim._mother_by_id = {m.id: m for m in sim.mothers}
    sim.world.place_entity(mover)
    for blocker in blockers:
        sim.world.place_entity(blocker)
    sim.world.place_food(4, 2)

    sim._execute_action(mover, "forage", [])

    assert mover.last_action == "FORAGE_DETOUR", (
        f"Expected a detour action, got {mover.last_action!r}"
    )
    assert mover.pos != (1, 2), "Detour should avoid snapping straight back to the previous cell."
    _log(
        "test_blocked_visible_food_avoids_immediate_backtrack_when_detouring",
        f"end_pos={mover.pos};recorded_last_pos={mover.last_pos}",
    )


if __name__ == "__main__":
    test_linear_energy_depletion()
    test_update_state_rate_independence()
    test_config_care_weight_zero_applied()
    test_config_nondefault_genome_weights_applied()
    test_matured_flag_exists_and_defaults_false()
    test_maturation_logged_as_matured_not_hunger()
    test_matured_child_does_not_reproduce_same_tick()
    test_matured_child_spawn_does_not_stack_with_birth_mother()
    test_choose_motivation_care_pathway_accessible()
    test_simulation_runs_without_crash_new_motivation_model()
    test_last_motivation_matches_final_domain_after_override()
    test_forage_explores_when_no_food_visible()
    test_same_cell_empty_handed_mother_does_not_repeat_care()
    test_empty_handed_mother_has_blind_forage_drive()
    test_self_cue_matches_feasible_self_maintenance()
    test_no_valid_child_target_means_no_care_domain()
    test_circle_world_bounds_use_inscribed_arena()
    test_blocked_visible_food_uses_detour_instead_of_stalling()
    test_forage_explore_avoids_immediate_backtrack_when_possible()
    test_blocked_visible_food_avoids_immediate_backtrack_when_detouring()

    out_dir = os.path.join(PROJECT_ROOT, "outputs", "phase1_mechanics_tests", TAG)
    os.makedirs(out_dir, exist_ok=True)

    with open(os.path.join(out_dir, "logs.csv"), "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["test_name", "status", "detail"])
        writer.writeheader()
        writer.writerows(_results)

    print(f"\n=== Test 07 — Engine Fixes: ALL TESTS PASSED ===")
    print(f"Logs saved -> outputs/phase1_mechanics_tests/{TAG}/logs.csv")
