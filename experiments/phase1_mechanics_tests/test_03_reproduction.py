"""
Test 03: Reproduction eligibility mechanics

Changes verified here:
  Change E — sigmoid reproduction gate: P = 1/(1+exp(-(energy-threshold)/0.05))
  Change F — one-child-per-lifetime: has_reproduced flag permanently blocks re-reproduction

Sub-tests:
  1. Sigmoid fires frequently at high energy (energy=1.0 → P≈0.95)
  2. Sigmoid rarely fires at low energy (energy=0.5 → P≈0.000)
  3. has_reproduced=True blocks reproduction deterministically
  4. own_child_id set blocks reproduction deterministically
  5. Cooldown > 0 blocks reproduction deterministically
  6. Cooldown ticks down correctly and floors at 0
"""
import sys
import os
import random

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
    print(f"[PASS] {name}")


def _make_mother() -> MotherAgent:
    return MotherAgent(5, 5, lineage_id=0, generation=0, genome=Genome())


# ─────────────────────────────────────────────────────────────────────────────
# Change E — Sigmoid gate probability
# ─────────────────────────────────────────────────────────────────────────────

def test_sigmoid_high_energy_reproduces_often():
    """At energy=1.0 (threshold=0.85), P≈0.95 — nearly always reproduces."""
    random.seed(DEFAULT_SEED)
    mother = _make_mother()
    mother.energy = 1.0
    mother.own_child_id = None
    mother.cooldown = 0
    mother.has_reproduced = False

    TRIALS = 300
    successes = sum(1 for _ in range(TRIALS) if mother.can_reproduce(threshold=0.85))
    rate = successes / TRIALS

    print(f"  energy=1.0 -> {successes}/{TRIALS} reproductions (rate={rate:.3f}, expected~0.95)")
    assert rate >= 0.85, f"Expected rate ≥0.85 at energy=1.0, got {rate:.3f}"

    _log(
        "test_sigmoid_high_energy_reproduces_often",
        f"trials={TRIALS};successes={successes};rate={rate:.3f};expected≈0.95",
    )


def test_sigmoid_low_energy_never_reproduces():
    """At energy=0.5 (threshold=0.85), P≈0.000 — reproduction essentially impossible."""
    random.seed(DEFAULT_SEED)
    mother = _make_mother()
    mother.energy = 0.5
    mother.own_child_id = None
    mother.cooldown = 0
    mother.has_reproduced = False

    TRIALS = 300
    successes = sum(1 for _ in range(TRIALS) if mother.can_reproduce(threshold=0.85))

    print(f"  energy=0.5 -> {successes}/{TRIALS} reproductions (expected~0, P~0.0009)")
    assert successes <= 3, (
        f"Expected near-zero reproductions at energy=0.5 (P~0.0009 per trial), "
        f"got {successes}/{TRIALS}"
    )

    _log(
        "test_sigmoid_low_energy_never_reproduces",
        f"trials={TRIALS};successes={successes};expected=0",
    )


# ─────────────────────────────────────────────────────────────────────────────
# Change F — Deterministic blocking conditions
# ─────────────────────────────────────────────────────────────────────────────

def test_has_reproduced_blocks_permanently():
    """has_reproduced=True must block reproduction regardless of energy or seed."""
    random.seed(DEFAULT_SEED)
    mother = _make_mother()
    mother.energy = 1.0
    mother.own_child_id = None
    mother.cooldown = 0
    mother.has_reproduced = True  # Change F flag

    TRIALS = 100
    successes = sum(1 for _ in range(TRIALS) if mother.can_reproduce(threshold=0.85))

    assert successes == 0, \
        f"has_reproduced=True must block all reproduction; got {successes}/{TRIALS}"

    _log(
        "test_has_reproduced_blocks_permanently",
        f"trials={TRIALS};successes={successes};has_reproduced=True",
    )


def test_cannot_reproduce_with_child():
    """own_child_id set must block reproduction deterministically."""
    random.seed(DEFAULT_SEED)
    mother = _make_mother()
    mother.energy = 1.0
    mother.own_child_id = 99
    mother.cooldown = 0
    mother.has_reproduced = False

    TRIALS = 100
    successes = sum(1 for _ in range(TRIALS) if mother.can_reproduce(threshold=0.85))

    assert successes == 0, \
        f"own_child_id set must block all reproduction; got {successes}/{TRIALS}"

    _log(
        "test_cannot_reproduce_with_child",
        f"trials={TRIALS};successes={successes};own_child_id=99",
    )


def test_cannot_reproduce_on_cooldown():
    """cooldown > 0 must block reproduction deterministically."""
    random.seed(DEFAULT_SEED)
    mother = _make_mother()
    mother.energy = 1.0
    mother.own_child_id = None
    mother.cooldown = 10
    mother.has_reproduced = False

    TRIALS = 100
    successes = sum(1 for _ in range(TRIALS) if mother.can_reproduce(threshold=0.85))

    assert successes == 0, \
        f"cooldown=10 must block all reproduction; got {successes}/{TRIALS}"

    _log(
        "test_cannot_reproduce_on_cooldown",
        f"trials={TRIALS};successes={successes};cooldown=10",
    )


def test_cooldown_ticks_down():
    """Cooldown decrements each tick and floors at 0."""
    mother = _make_mother()
    mother.cooldown = 2

    mother.tick_cooldown()
    assert mother.cooldown == 1, f"Expected 1, got {mother.cooldown}"

    mother.tick_cooldown()
    assert mother.cooldown == 0, f"Expected 0, got {mother.cooldown}"

    mother.tick_cooldown()
    assert mother.cooldown == 0, "Cooldown must not go below 0"

    _log("test_cooldown_ticks_down", "cooldown: 2→1→0→0")


if __name__ == "__main__":
    import csv

    test_sigmoid_high_energy_reproduces_often()
    test_sigmoid_low_energy_never_reproduces()
    test_has_reproduced_blocks_permanently()
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
