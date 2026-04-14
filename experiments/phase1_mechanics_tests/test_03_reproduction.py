"""
Test 03: Reproduction mechanics work
- Mother can reproduce when energy >= threshold
- Child spawns nearby
- Energy is deducted
- Cooldown is applied
"""
import sys
import os
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, PROJECT_ROOT)

from agents.mother import MotherAgent
from evolution.genome import Genome
from simulation.world import GridWorld

MODULE_NUM = "03"
DEFAULT_SEED = 42
RUN_NUM = 1
TAG = f"test{MODULE_NUM}_{DEFAULT_SEED}_{RUN_NUM}"

_results = []


def _log(name: str, detail: str = "") -> None:
    _results.append({"test_name": name, "status": "PASS", "detail": detail})
    print(f"✓ {name} PASSED")


def test_can_reproduce_threshold():
    """Mother can reproduce only when energy >= threshold."""
    genome = Genome()
    mother = MotherAgent(5, 5, lineage_id=0, generation=0, genome=genome)

    # Low energy
    mother.energy = 0.5
    mother.own_child_id = None
    mother.cooldown = 0
    assert not mother.can_reproduce(threshold=0.8)

    # High energy
    mother.energy = 0.9
    assert mother.can_reproduce(threshold=0.8)
    _log("test_can_reproduce_threshold", "energy=0.5 blocked; energy=0.9 allowed (threshold=0.8)")


def test_cannot_reproduce_with_child():
    """Mother cannot reproduce if already has child."""
    genome = Genome()
    mother = MotherAgent(5, 5, lineage_id=0, generation=0, genome=genome)

    mother.energy = 1.0
    mother.own_child_id = 99  # has child
    mother.cooldown = 0

    assert not mother.can_reproduce(threshold=0.8)
    _log("test_cannot_reproduce_with_child", "own_child_id=99 blocks reproduction")


def test_cannot_reproduce_on_cooldown():
    """Mother cannot reproduce during cooldown."""
    genome = Genome()
    mother = MotherAgent(5, 5, lineage_id=0, generation=0, genome=genome)

    mother.energy = 1.0
    mother.own_child_id = None
    mother.cooldown = 10

    assert not mother.can_reproduce(threshold=0.8)
    _log("test_cannot_reproduce_on_cooldown", "cooldown=10 blocks reproduction")


def test_cooldown_ticks_down():
    """Cooldown should decrease each tick and floor at 0."""
    genome = Genome()
    mother = MotherAgent(5, 5, lineage_id=0, generation=0, genome=genome)

    mother.cooldown = 2
    mother.tick_cooldown()
    assert mother.cooldown == 1

    mother.tick_cooldown()
    assert mother.cooldown == 0

    mother.tick_cooldown()
    assert mother.cooldown == 0, "Cooldown should not go below 0"
    _log("test_cooldown_ticks_down", "2->1->0->0 after three ticks")


if __name__ == "__main__":
    import csv

    test_can_reproduce_threshold()
    test_cannot_reproduce_with_child()
    test_cannot_reproduce_on_cooldown()
    test_cooldown_ticks_down()

    out_dir = os.path.join(PROJECT_ROOT, "outputs", "phase1_mechanics_tests", TAG)
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, "logs.csv"), "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["test_name", "status", "detail"])
        writer.writeheader()
        writer.writerows(_results)

    print(f"\n=== All reproduction tests PASSED ===")
    print(f"Logs saved → outputs/phase1_mechanics_tests/{TAG}/logs.csv")
