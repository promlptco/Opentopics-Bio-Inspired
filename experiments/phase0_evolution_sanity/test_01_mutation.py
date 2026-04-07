"""
Test 01: Mutation works correctly
- Mutated genome differs from parent
- Values stay in [0,1]
- Distribution is reasonable
"""
import sys
sys.path.append("../..")

from evolution.genome import Genome
import statistics


def test_mutation_changes_values():
    """Mutated genome should differ from parent."""
    parent = Genome(
        care_weight=0.5,
        forage_weight=0.5,
        self_weight=0.5,
        learning_rate=0.1,
        learning_cost=0.05
    )
    
    changes = 0
    trials = 100
    
    for _ in range(trials):
        child = parent.mutate(mutation_rate=1.0)  # 100% mutation
        if child.care_weight != parent.care_weight:
            changes += 1
    
    print(f"Mutations occurred: {changes}/{trials}")
    assert changes > 50, "Mutation should change values most of the time"
    print("✓ test_mutation_changes_values PASSED")


def test_mutation_stays_in_bounds():
    """Mutated values should stay in [0,1]."""
    genome = Genome(care_weight=0.99, forage_weight=0.01)
    
    for _ in range(1000):
        genome = genome.mutate(mutation_rate=1.0)
        assert 0.0 <= genome.care_weight <= 1.0, f"care_weight out of bounds: {genome.care_weight}"
        assert 0.0 <= genome.forage_weight <= 1.0, f"forage_weight out of bounds: {genome.forage_weight}"
    
    print("✓ test_mutation_stays_in_bounds PASSED")


def test_mutation_distribution():
    """Mutations should be roughly normally distributed."""
    parent = Genome(care_weight=0.5)
    
    values = []
    for _ in range(1000):
        child = parent.mutate(mutation_rate=1.0)
        values.append(child.care_weight)
    
    mean = statistics.mean(values)
    stdev = statistics.stdev(values)
    
    print(f"Mean: {mean:.3f}, Stdev: {stdev:.3f}")
    assert 0.4 < mean < 0.6, f"Mean should be near 0.5, got {mean}"
    assert 0.05 < stdev < 0.2, f"Stdev should be reasonable, got {stdev}"
    print("✓ test_mutation_distribution PASSED")


if __name__ == "__main__":
    test_mutation_changes_values()
    test_mutation_stays_in_bounds()
    test_mutation_distribution()
    print("\n=== All mutation tests PASSED ===")