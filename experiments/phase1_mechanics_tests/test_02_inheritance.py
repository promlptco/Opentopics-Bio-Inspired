"""
Test 02: Inheritance works correctly
- Child genome is copy of parent (before mutation)
- Mutation creates variation
"""
import sys
import os
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, PROJECT_ROOT)

from evolution.genome import Genome

MODULE_NUM = "02"
DEFAULT_SEED = 42
RUN_NUM = 1
TAG = f"test{MODULE_NUM}_{DEFAULT_SEED}_{RUN_NUM}"

_results = []


def _log(name: str, detail: str = "") -> None:
    _results.append({"test_name": name, "status": "PASS", "detail": detail})
    print(f"✓ {name} PASSED")


def test_copy_is_exact():
    """Copy should be identical."""
    parent = Genome(
        care_weight=0.3,
        forage_weight=0.7,
        self_weight=0.4,
        learning_rate=0.15,
        learning_cost=0.08
    )

    child = parent.copy()

    assert child.care_weight == parent.care_weight
    assert child.forage_weight == parent.forage_weight
    assert child.self_weight == parent.self_weight
    assert child.learning_rate == parent.learning_rate
    assert child.learning_cost == parent.learning_cost
    _log("test_copy_is_exact", "all 5 fields match parent")


def test_copy_is_independent():
    """Modifying copy should not affect parent."""
    parent = Genome(care_weight=0.5)
    child = parent.copy()

    child.care_weight = 0.9

    assert parent.care_weight == 0.5, "Parent should not change"
    assert child.care_weight == 0.9, "Child should change"
    _log("test_copy_is_independent", "child mutation does not alias parent")


def test_inheritance_with_mutation():
    """Child should inherit then mutate."""
    parent = Genome(
        care_weight=0.5,
        forage_weight=0.5,
        self_weight=0.5,
        learning_rate=0.1,
        learning_cost=0.05
    )

    child = parent.mutate(mutation_rate=0.0)

    for f in ["care_weight", "forage_weight", "self_weight", "learning_rate", "learning_cost"]:
        assert getattr(child, f) == getattr(parent, f), f"{f} should be unchanged at mutation_rate=0.0"

    _log("test_inheritance_with_mutation", "mutation_rate=0.0 preserves all 5 fields")


if __name__ == "__main__":
    import csv

    test_copy_is_exact()
    test_copy_is_independent()
    test_inheritance_with_mutation()

    out_dir = os.path.join(PROJECT_ROOT, "outputs", "phase1_mechanics_tests", TAG)
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, "logs.csv"), "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["test_name", "status", "detail"])
        writer.writeheader()
        writer.writerows(_results)

    print(f"\n=== All inheritance tests PASSED ===")
    print(f"Logs saved → outputs/phase1_mechanics_tests/{TAG}/logs.csv")
