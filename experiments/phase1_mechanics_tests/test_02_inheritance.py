"""
Test 02: Inheritance works correctly
- Child genome is an exact copy of parent before mutation
- Copy is independent from parent
- mutation_rate=0.0 preserves inherited genome exactly
- mutation_rate=1.0 creates variation
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

FIELDS = ["care_weight", "forage_weight", "self_weight", "learning_rate", "learning_cost"]

_results = []


def _log(name: str, detail: str = "") -> None:
    _results.append({"test_name": name, "status": "PASS", "detail": detail})
    print(f"✓ {name} PASSED")


def _make_parent() -> Genome:
    """Create a non-default genome so inheritance errors are easier to detect."""
    return Genome(
        care_weight=0.3,
        forage_weight=0.7,
        self_weight=0.4,
        learning_rate=0.15,
        learning_cost=0.08,
    )


def test_copy_is_exact():
    """Copy should preserve all genome fields exactly."""
    parent = _make_parent()
    child = parent.copy()

    for f in FIELDS:
        assert getattr(child, f) == getattr(parent, f), \
            f"{f} mismatch: child={getattr(child, f)}, parent={getattr(parent, f)}"

    _log("test_copy_is_exact", "all 5 fields match parent")


def test_copy_is_independent():
    """Modifying copy should not affect parent."""
    parent = _make_parent()
    child = parent.copy()

    child.care_weight = 0.9
    child.forage_weight = 0.1

    assert parent.care_weight == 0.3, "Parent care_weight should not change"
    assert parent.forage_weight == 0.7, "Parent forage_weight should not change"

    assert child.care_weight == 0.9, "Child care_weight should change"
    assert child.forage_weight == 0.1, "Child forage_weight should change"

    _log("test_copy_is_independent", "editing child copy does not affect parent")


def test_mutation_rate_zero_preserves_parent_values():
    """mutation_rate=0.0 should produce an inherited child with no changes."""
    parent = _make_parent()
    child = parent.mutate(mutation_rate=0.0)

    for f in FIELDS:
        assert getattr(child, f) == getattr(parent, f), \
            f"{f} should be unchanged at mutation_rate=0.0"

    _log("test_mutation_rate_zero_preserves_parent_values",
         "mutation_rate=0.0 preserves all 5 fields")


def test_mutation_creates_variation():
    """mutation_rate=1.0 should create at least one changed genome field."""
    parent = _make_parent()
    child = parent.mutate(mutation_rate=1.0)

    changed_fields = [
        f for f in FIELDS
        if getattr(child, f) != getattr(parent, f)
    ]

    assert len(changed_fields) > 0, \
        "At least one field should change when mutation_rate=1.0"

    for f in FIELDS:
        v = getattr(child, f)
        assert 0.0 <= v <= 1.0, f"{f} out of bounds after mutation: {v}"

    _log("test_mutation_creates_variation",
         f"changed_fields={changed_fields}")


if __name__ == "__main__":
    import csv

    test_copy_is_exact()
    test_copy_is_independent()
    test_mutation_rate_zero_preserves_parent_values()
    test_mutation_creates_variation()

    out_dir = os.path.join(PROJECT_ROOT, "outputs", "phase1_mechanics_tests", TAG)
    os.makedirs(out_dir, exist_ok=True)

    with open(os.path.join(out_dir, "logs.csv"), "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["test_name", "status", "detail"])
        writer.writeheader()
        writer.writerows(_results)

    print(f"\n=== All inheritance tests PASSED ===")
    print(f"Logs saved → outputs/phase1_mechanics_tests/{TAG}/logs.csv")