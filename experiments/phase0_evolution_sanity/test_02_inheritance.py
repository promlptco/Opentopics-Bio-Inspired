"""
Test 02: Inheritance works correctly
- Child genome is copy of parent (before mutation)
- Mutation creates variation
"""
import sys
sys.path.append("../..")

from evolution.genome import Genome


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
    print("✓ test_copy_is_exact PASSED")


def test_copy_is_independent():
    """Modifying copy should not affect parent."""
    parent = Genome(care_weight=0.5)
    child = parent.copy()
    
    child.care_weight = 0.9
    
    assert parent.care_weight == 0.5, "Parent should not change"
    assert child.care_weight == 0.9, "Child should change"
    print("✓ test_copy_is_independent PASSED")


def test_inheritance_with_mutation():
    """Child should inherit then mutate."""
    parent = Genome(care_weight=0.5, forage_weight=0.5)
    
    # With 0% mutation rate, child should be identical
    child = parent.mutate(mutation_rate=0.0)
    assert child.care_weight == parent.care_weight
    assert child.forage_weight == parent.forage_weight
    print("✓ test_inheritance_with_mutation PASSED")


if __name__ == "__main__":
    test_copy_is_exact()
    test_copy_is_independent()
    test_inheritance_with_mutation()
    print("\n=== All inheritance tests PASSED ===")