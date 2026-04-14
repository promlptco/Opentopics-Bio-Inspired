"""
Test 05: Stochasticity Identity

Verifies that the stochastic mechanics are seed-controlled, not truly random:
  (a) Identical seed → 100% identical action sequences across repeated runs.
  (b) Different seeds → meaningfully different action sequences.

Design reference: EXPERIMENT_DESIGN.md Phase 1, Test 05 (amended 2026-04-14).
"""
import sys
import os
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, PROJECT_ROOT)

import random
import numpy as np
from config import Config
from simulation.simulation import Simulation

MODULE_NUM = "05"
DEFAULT_SEED = 42
RUN_NUM = 1
TAG = f"test{MODULE_NUM}_{DEFAULT_SEED}_{RUN_NUM}"

# Number of ticks to record action sequences for comparison.
# Short enough to be fast; long enough to catch divergence.
TICKS = 100

_results = []


def _log(name: str, detail: str = "") -> None:
    _results.append({"test_name": name, "status": "PASS", "detail": detail})
    print(f"✓ {name} PASSED")


def _run_and_collect_domains(seed: int, ticks: int) -> list[str]:
    """Run simulation for `ticks` steps and return the sequence of
    mother domain choices logged at each tick (one entry per mother per tick).

    We intercept choose_domain() calls by monkey-patching the MotherAgent class
    inside the simulation so we capture exactly what the engine produces,
    in order, without modifying production code.
    """
    from agents.mother import MotherAgent

    domains_log: list[str] = []
    original_choose = MotherAgent.choose_domain

    def recording_choose(self, visible_children):
        result = original_choose(self, visible_children)
        domains_log.append(result)
        return result

    MotherAgent.choose_domain = recording_choose
    try:
        config = Config()
        config.seed = seed
        config.max_ticks = ticks
        config.mutation_enabled = False   # freeze genomes — isolate stochastic mechanics
        config.reproduction_enabled = False

        sim = Simulation(config)
        sim.initialize()
        for _ in range(ticks):
            sim.step()
    finally:
        MotherAgent.choose_domain = original_choose

    return domains_log


def test_same_seed_identical():
    """Two runs with the same seed must produce 100% identical action sequences.

    Contract: seed controls ALL randomness — random.random() and
    np.random.choice() — so the output is deterministic.
    """
    seq_a = _run_and_collect_domains(seed=DEFAULT_SEED, ticks=TICKS)
    seq_b = _run_and_collect_domains(seed=DEFAULT_SEED, ticks=TICKS)

    assert len(seq_a) > 0, "No domain choices logged — simulation produced no actions"
    assert len(seq_a) == len(seq_b), (
        f"Action sequence lengths differ: {len(seq_a)} vs {len(seq_b)}"
    )

    mismatches = sum(a != b for a, b in zip(seq_a, seq_b))
    total = len(seq_a)
    match_rate = (total - mismatches) / total
    print(f"  Identical choices: {total - mismatches}/{total} ({match_rate:.1%})")

    assert mismatches == 0, (
        f"Identical seeds must produce 100% identical sequences. "
        f"Got {mismatches}/{total} mismatches."
    )
    _log(
        "test_same_seed_identical",
        f"seed={DEFAULT_SEED};ticks={TICKS};total_actions={total};mismatches=0;match_rate=100%"
    )


def test_different_seed_diverges():
    """Two runs with different seeds must produce meaningfully different sequences.

    'Meaningful' is defined as > 5% divergence — an extremely conservative
    threshold. True stochasticity would produce ~50% divergence at τ=0.1
    from a different distribution over 100 ticks.
    """
    SEED_A = DEFAULT_SEED       # 42
    SEED_B = DEFAULT_SEED + 7   # 49 — well-separated seed

    seq_a = _run_and_collect_domains(seed=SEED_A, ticks=TICKS)
    seq_b = _run_and_collect_domains(seed=SEED_B, ticks=TICKS)

    # Compare element-wise up to the shorter sequence (population drifts differ)
    compare_len = min(len(seq_a), len(seq_b))
    assert compare_len > 0, "No actions logged for one or both seeds"

    mismatches = sum(a != b for a, b in zip(seq_a[:compare_len], seq_b[:compare_len]))
    divergence_rate = mismatches / compare_len
    print(
        f"  Seeds {SEED_A} vs {SEED_B}: "
        f"{mismatches}/{compare_len} divergences ({divergence_rate:.1%})"
    )

    MIN_DIVERGENCE = 0.05  # must differ on at least 5% of actions
    assert divergence_rate > MIN_DIVERGENCE, (
        f"Different seeds should produce divergent sequences. "
        f"Got only {divergence_rate:.1%} divergence (threshold: {MIN_DIVERGENCE:.0%})."
    )
    _log(
        "test_different_seed_diverges",
        f"seed_a={SEED_A};seed_b={SEED_B};ticks={TICKS};"
        f"compared={compare_len};mismatches={mismatches};"
        f"divergence_rate={divergence_rate:.4f}"
    )


def test_numpy_seeded_in_simulation():
    """Confirm that numpy is seeded inside Simulation.__init__ alongside random.

    This is a structural guard: if the numpy seed is missing the Softmax
    np.random.choice calls are not deterministic and test_same_seed_identical
    would catch it — but this test pinpoints the root cause early.
    """
    import inspect
    import simulation.simulation as sim_module

    source = inspect.getsource(sim_module.Simulation.__init__)
    has_np_seed = "np.random.seed" in source or "numpy.random.seed" in source
    print(f"  np.random.seed present in Simulation.__init__: {has_np_seed}")
    assert has_np_seed, (
        "Simulation.__init__ must call np.random.seed(config.seed). "
        "Without it, Softmax np.random.choice is not deterministic."
    )
    _log("test_numpy_seeded_in_simulation", f"np_seed_present={has_np_seed}")


if __name__ == "__main__":
    import csv

    test_numpy_seeded_in_simulation()
    test_same_seed_identical()
    test_different_seed_diverges()

    out_dir = os.path.join(PROJECT_ROOT, "outputs", "phase1_mechanics_tests", TAG)
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, "logs.csv"), "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["test_name", "status", "detail"])
        writer.writeheader()
        writer.writerows(_results)

    print(f"\n=== All stochasticity identity tests PASSED ===")
    print(f"Logs saved → outputs/phase1_mechanics_tests/{TAG}/logs.csv")
