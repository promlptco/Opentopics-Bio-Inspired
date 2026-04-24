"""
Test 05: Stochasticity control
- Same seed produces identical action sequences
- Different seeds produce meaningfully different action sequences
- Randomness is controlled through Simulation(config.seed)

Design reference: EXPERIMENT_DESIGN.md Phase 1, Test 05.
"""
import sys
import os

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, PROJECT_ROOT)

from config import Config
from simulation.simulation import Simulation

MODULE_NUM = "05"
DEFAULT_SEED = 42
RUN_NUM = 1
TAG = f"test{MODULE_NUM}_{DEFAULT_SEED}_{RUN_NUM}"

TICKS = 100
MIN_DIVERGENCE = 0.05

_results = []


def _log(name: str, detail: str = "") -> None:
    _results.append({"test_name": name, "status": "PASS", "detail": detail})
    print(f"✓ {name} PASSED")


def _make_config(seed: int, ticks: int) -> Config:
    """Create a controlled config for stochasticity testing."""
    config = Config()
    config.seed = seed
    config.max_ticks = ticks

    # Isolate action stochasticity.
    config.mutation_enabled = False
    config.reproduction_enabled = False

    return config


def _run_and_collect_domains(seed: int, ticks: int) -> list[str]:
    """Run simulation and record mother domain choices.

    The MotherAgent.choose_domain method is temporarily wrapped so the test can
    record the actual choices made by the simulation without changing production code.
    """
    from agents.mother import MotherAgent

    domains_log: list[str] = []
    original_choose_domain = MotherAgent.choose_domain

    def recording_choose_domain(self, visible_children):
        domain = original_choose_domain(self, visible_children)
        domains_log.append(domain)
        return domain

    MotherAgent.choose_domain = recording_choose_domain

    try:
        config = _make_config(seed=seed, ticks=ticks)

        sim = Simulation(config)
        sim.initialize()

        for _ in range(ticks):
            sim.step()

    finally:
        MotherAgent.choose_domain = original_choose_domain

    return domains_log


def _sequence_mismatch_stats(seq_a: list[str], seq_b: list[str]) -> tuple[int, int, float]:
    """Return compared length, mismatch count, and mismatch rate."""
    compare_len = min(len(seq_a), len(seq_b))

    assert compare_len > 0, (
        f"No comparable actions logged: len(seq_a)={len(seq_a)}, len(seq_b)={len(seq_b)}"
    )

    mismatches = sum(
        a != b
        for a, b in zip(seq_a[:compare_len], seq_b[:compare_len])
    )

    mismatch_rate = mismatches / compare_len
    return compare_len, mismatches, mismatch_rate


def test_same_seed_identical():
    """Two runs with the same seed must produce identical action sequences."""
    seq_a = _run_and_collect_domains(seed=DEFAULT_SEED, ticks=TICKS)
    seq_b = _run_and_collect_domains(seed=DEFAULT_SEED, ticks=TICKS)

    assert len(seq_a) > 0, "No domain choices logged in first run"
    assert len(seq_b) > 0, "No domain choices logged in second run"

    assert len(seq_a) == len(seq_b), (
        f"Same-seed sequence lengths differ: {len(seq_a)} vs {len(seq_b)}"
    )

    compare_len, mismatches, mismatch_rate = _sequence_mismatch_stats(seq_a, seq_b)

    print(
        f"Same seed {DEFAULT_SEED}: "
        f"{compare_len - mismatches}/{compare_len} identical "
        f"({1.0 - mismatch_rate:.1%} match)"
    )

    assert mismatches == 0, (
        f"Same seed should produce identical sequences. "
        f"Got {mismatches}/{compare_len} mismatches."
    )

    _log(
        "test_same_seed_identical",
        f"seed={DEFAULT_SEED};ticks={TICKS};"
        f"actions={compare_len};mismatches={mismatches};match_rate=1.0000",
    )


def test_different_seed_diverges():
    """Two different seeds should produce meaningfully different action sequences."""
    seed_a = DEFAULT_SEED
    seed_b = DEFAULT_SEED + 7

    seq_a = _run_and_collect_domains(seed=seed_a, ticks=TICKS)
    seq_b = _run_and_collect_domains(seed=seed_b, ticks=TICKS)

    compare_len, mismatches, divergence_rate = _sequence_mismatch_stats(seq_a, seq_b)

    print(
        f"Seeds {seed_a} vs {seed_b}: "
        f"{mismatches}/{compare_len} divergences "
        f"({divergence_rate:.1%})"
    )

    assert divergence_rate > MIN_DIVERGENCE, (
        f"Different seeds should produce divergent sequences. "
        f"Got {divergence_rate:.1%}, threshold={MIN_DIVERGENCE:.1%}."
    )

    _log(
        "test_different_seed_diverges",
        f"seed_a={seed_a};seed_b={seed_b};ticks={TICKS};"
        f"compared={compare_len};mismatches={mismatches};"
        f"divergence_rate={divergence_rate:.4f};"
        f"threshold={MIN_DIVERGENCE:.4f}",
    )


def test_repeated_same_seed_after_different_seed():
    """Same seed should remain deterministic even after another seed is run.

    This catches global RNG contamination between simulations.
    """
    seq_a = _run_and_collect_domains(seed=12345, ticks=TICKS)
    _ = _run_and_collect_domains(seed=99999, ticks=TICKS)
    seq_b = _run_and_collect_domains(seed=12345, ticks=TICKS)

    assert len(seq_a) == len(seq_b), (
        f"Repeated same-seed sequence lengths differ: {len(seq_a)} vs {len(seq_b)}"
    )

    compare_len, mismatches, mismatch_rate = _sequence_mismatch_stats(seq_a, seq_b)

    print(
        f"Repeated seed 12345 after different seed: "
        f"{compare_len - mismatches}/{compare_len} identical "
        f"({1.0 - mismatch_rate:.1%} match)"
    )

    assert mismatches == 0, (
        "Same seed should remain deterministic even after running a different seed. "
        f"Got {mismatches}/{compare_len} mismatches."
    )

    _log(
        "test_repeated_same_seed_after_different_seed",
        f"seed=12345;intermediate_seed=99999;ticks={TICKS};"
        f"actions={compare_len};mismatches={mismatches}",
    )


if __name__ == "__main__":
    import csv

    test_same_seed_identical()
    test_different_seed_diverges()
    test_repeated_same_seed_after_different_seed()

    out_dir = os.path.join(PROJECT_ROOT, "outputs", "phase1_mechanics_tests", TAG)
    os.makedirs(out_dir, exist_ok=True)

    with open(os.path.join(out_dir, "logs.csv"), "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["test_name", "status", "detail"])
        writer.writeheader()
        writer.writerows(_results)

    print(f"\n=== All stochasticity control tests PASSED ===")
    print(f"Logs saved → outputs/phase1_mechanics_tests/{TAG}/logs.csv")