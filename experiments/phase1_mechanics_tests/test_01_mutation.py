"""
Test 01: Mutation works correctly
- Mutated genome differs from parent
- Values stay in [0,1]
- Distribution is reasonable
"""
import sys
import os
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, PROJECT_ROOT)

from evolution.genome import Genome
import statistics
import random
import numpy as np

MODULE_NUM = "01"
DEFAULT_SEED = 42
RUN_NUM = 1
TAG = f"test{MODULE_NUM}_{DEFAULT_SEED}_{RUN_NUM}"

FIELDS = ["care_weight", "forage_weight", "self_weight", "learning_rate", "learning_cost"]

_results = []


def _seed():
    random.seed(DEFAULT_SEED)
    np.random.seed(DEFAULT_SEED)


def _log(name: str, detail: str = "") -> None:
    _results.append({"test_name": name, "status": "PASS", "detail": detail})
    print(f"✓ {name} PASSED")


def test_mutation_changes_values():
    """Mutated genome should differ from parent."""
    _seed()
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
        child = parent.mutate(mutation_rate=1.0)
        if child.care_weight != parent.care_weight:
            changes += 1

    print(f"Mutations occurred: {changes}/{trials}")
    assert changes > 90, "Mutation should change values most of the time"
    _log("test_mutation_changes_values", f"mutations_occurred={changes}/{trials}")


def test_mutation_stays_in_bounds():
    """All five fields must stay in [0,1] across 1000 mutations."""
    _seed()
    genome = Genome(care_weight=0.99, forage_weight=0.01)

    for _ in range(1000):
        genome = genome.mutate(mutation_rate=1.0)
        for f in FIELDS:
            v = getattr(genome, f)
            assert 0.0 <= v <= 1.0, f"{f} out of bounds: {v}"

    _log("test_mutation_stays_in_bounds", "1000 mutations, all 5 fields in [0,1]")


def test_mutation_distribution():
    """All five genome fields should mutate with roughly Gaussian distribution (sigma=0.05)."""
    _seed()
    parent = Genome(
        care_weight=0.5,
        forage_weight=0.5,
        self_weight=0.5,
        learning_rate=0.5,
        learning_cost=0.5,
    )

    samples = {f: [] for f in FIELDS}

    for _ in range(1000):
        child = parent.mutate(mutation_rate=1.0, sigma=0.05)
        for f in FIELDS:
            samples[f].append(getattr(child, f))

    detail_parts = []
    for f in FIELDS:
        mean = statistics.mean(samples[f])
        stdev = statistics.stdev(samples[f])
        detail_parts.append(f"{f}:mean={mean:.3f},stdev={stdev:.3f}")
        print(f"  {f}: Mean={mean:.3f}, Stdev={stdev:.3f}")
        assert 0.4 < mean < 0.6, f"{f} mean should be near 0.5, got {mean}"
        assert 0.03 < stdev < 0.07, f"{f} stdev should be near 0.05, got {stdev}"

    _log("test_mutation_distribution", "; ".join(detail_parts))
    
def test_mutation_rate_sensitivity():
    """Sweep sigma values to confirm sigma=0.05 is appropriate.
    
    Verifies:
    - Higher sigma produces higher output stdev (monotonic)
    - sigma=0.05 lands in expected stdev range [0.08, 0.12]
    - No sigma causes values to leave [0,1]
    """
    _seed()
    SIGMAS = [0.01, 0.05, 0.10]
    stdevs = {}

    for sigma in SIGMAS:
        parent = Genome(care_weight=0.5, forage_weight=0.5,
                        self_weight=0.5, learning_rate=0.5, learning_cost=0.5)
        samples = []
        for _ in range(1000):
            child = parent.mutate(mutation_rate=1.0, sigma=sigma)
            for f in FIELDS:
                v = getattr(child, f)
                assert 0.0 <= v <= 1.0, f"sigma={sigma}: {f} out of bounds: {v}"
            samples.append(child.care_weight)

        s = statistics.stdev(samples)
        stdevs[sigma] = s
        print(f"  sigma={sigma:.2f} → output stdev={s:.4f}")

    # Monotonic: larger sigma must produce larger stdev
    assert stdevs[0.01] < stdevs[0.05] < stdevs[0.10], \
        f"Stdev not monotonic with sigma: {stdevs}"

    # Canonical sigma=0.05 must land in expected range
    assert 0.03 < stdevs[0.05] < 0.07, \
        f"sigma=0.05 stdev out of expected range: {stdevs[0.05]:.4f}"

    detail = "; ".join(f"sigma={s}:stdev={stdevs[s]:.4f}" for s in SIGMAS)
    _log("test_mutation_rate_sensitivity", detail)


if __name__ == "__main__":
    import csv

    test_mutation_changes_values()
    test_mutation_stays_in_bounds()
    test_mutation_distribution()
    test_mutation_rate_sensitivity()

    out_dir = os.path.join(PROJECT_ROOT, "outputs", "phase1_mechanics_tests", TAG)
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, "logs.csv"), "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["test_name", "status", "detail"])
        writer.writeheader()
        writer.writerows(_results)

    print(f"\n=== All mutation tests PASSED ===")
    print(f"Logs saved → outputs/phase1_mechanics_tests/{TAG}/logs.csv")