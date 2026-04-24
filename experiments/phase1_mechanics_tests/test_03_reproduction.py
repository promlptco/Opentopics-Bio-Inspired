"""
Test 03: Reproduction eligibility mechanics work
- Mother can reproduce when energy >= threshold
- Mother cannot reproduce below threshold
- Mother cannot reproduce if already caring for a child
- Mother cannot reproduce during cooldown
- Cooldown ticks down and floors at 0

Note:
This test checks reproduction eligibility only.
Actual child spawning, energy deduction, and world placement should be tested separately
if MotherAgent has a reproduce()/spawn_child() method.
"""
import sys
import os

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, PROJECT_ROOT)

from agents.mother import MotherAgent
from evolution.genome import Genome

MODULE_NUM = "03"
DEFAULT_SEED = 42
RUN_NUM = 1
TAG = f"test{MODULE_NUM}_{DEFAULT_SEED}_{RUN_NUM}"

_results = []


def _log(name: str, detail: str = "") -> None:
    _results.append({"test_name": name, "status": "PASS", "detail": detail})
    print(f"✓ {name} PASSED")


def _make_mother() -> MotherAgent:
    """Create a clean mother agent for reproduction mechanics tests."""
    genome = Genome()
    mother = MotherAgent(
        5,
        5,
        lineage_id=0,
        generation=0,
        genome=genome,
    )
    return mother


def test_can_reproduce_above_threshold():
    """Mother can reproduce when energy is above threshold."""
    mother = _make_mother()

    mother.energy = 0.9
    mother.own_child_id = None
    mother.cooldown = 0

    assert mother.can_reproduce(threshold=0.8), \
        "Mother should reproduce when energy > threshold"

    _log(
        "test_can_reproduce_above_threshold",
        "energy=0.9 allowed at threshold=0.8",
    )


def test_can_reproduce_at_exact_threshold():
    """Mother can reproduce when energy is exactly equal to threshold."""
    mother = _make_mother()

    mother.energy = 0.8
    mother.own_child_id = None
    mother.cooldown = 0

    assert mother.can_reproduce(threshold=0.8), \
        "Mother should reproduce when energy == threshold"

    _log(
        "test_can_reproduce_at_exact_threshold",
        "energy=0.8 allowed at threshold=0.8",
    )


def test_cannot_reproduce_below_threshold():
    """Mother cannot reproduce when energy is below threshold."""
    mother = _make_mother()

    mother.energy = 0.5
    mother.own_child_id = None
    mother.cooldown = 0

    assert not mother.can_reproduce(threshold=0.8), \
        "Mother should not reproduce when energy < threshold"

    _log(
        "test_cannot_reproduce_below_threshold",
        "energy=0.5 blocked at threshold=0.8",
    )


def test_cannot_reproduce_with_child():
    """Mother cannot reproduce if already caring for a child."""
    mother = _make_mother()

    mother.energy = 1.0
    mother.own_child_id = 99
    mother.cooldown = 0

    assert not mother.can_reproduce(threshold=0.8), \
        "Mother should not reproduce while own_child_id is set"

    _log(
        "test_cannot_reproduce_with_child",
        "own_child_id=99 blocks reproduction",
    )


def test_cannot_reproduce_on_cooldown():
    """Mother cannot reproduce during cooldown."""
    mother = _make_mother()

    mother.energy = 1.0
    mother.own_child_id = None
    mother.cooldown = 10

    assert not mother.can_reproduce(threshold=0.8), \
        "Mother should not reproduce while cooldown > 0"

    _log(
        "test_cannot_reproduce_on_cooldown",
        "cooldown=10 blocks reproduction",
    )


def test_cooldown_ticks_down():
    """Cooldown should decrease each tick and floor at 0."""
    mother = _make_mother()

    mother.cooldown = 2

    mother.tick_cooldown()
    assert mother.cooldown == 1, \
        f"Expected cooldown 1 after first tick, got {mother.cooldown}"

    mother.tick_cooldown()
    assert mother.cooldown == 0, \
        f"Expected cooldown 0 after second tick, got {mother.cooldown}"

    mother.tick_cooldown()
    assert mother.cooldown == 0, \
        "Cooldown should not go below 0"

    _log(
        "test_cooldown_ticks_down",
        "cooldown sequence: 2 -> 1 -> 0 -> 0",
    )


if __name__ == "__main__":
    import csv

    test_can_reproduce_above_threshold()
    test_can_reproduce_at_exact_threshold()
    test_cannot_reproduce_below_threshold()
    test_cannot_reproduce_with_child()
    test_cannot_reproduce_on_cooldown()
    test_cooldown_ticks_down()

    out_dir = os.path.join(PROJECT_ROOT, "outputs", "phase1_mechanics_tests", TAG)
    os.makedirs(out_dir, exist_ok=True)

    with open(os.path.join(out_dir, "logs.csv"), "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["test_name", "status", "detail"])
        writer.writeheader()
        writer.writerows(_results)

    print(f"\n=== All reproduction eligibility tests PASSED ===")
    print(f"Logs saved → outputs/phase1_mechanics_tests/{TAG}/logs.csv")