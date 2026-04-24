# experiments/phase1_mechanics_tests/run.py
"""Phase 1: Run all mechanics tests and aggregate results."""
import os
import sys
import subprocess

TESTS = [
    "test_01_mutation.py",
    "test_02_inheritance.py",
    "test_03_reproduction.py",
    "test_04_population_stability.py",
    "test_05_stochasticity_identity.py",
    "test_06_softmax_calibration.py",
]

phase_dir = os.path.dirname(os.path.abspath(__file__))


def main() -> int:
    failed = []
    passed = []

    print("\n=== Phase 1 Mechanics Tests ===\n")

    for test in TESTS:
        test_path = os.path.join(phase_dir, test)

        if not os.path.exists(test_path):
            print(f"✗ MISSING: {test}")
            failed.append(test)
            continue

        print(f"\n--- Running {test} ---")

        result = subprocess.run(
            [sys.executable, test_path],
            cwd=phase_dir,
        )

        if result.returncode == 0:
            print(f"✓ PASSED: {test}")
            passed.append(test)
        else:
            print(f"✗ FAILED: {test}")
            failed.append(test)

    print("\n=== Phase 1 Summary ===")
    print(f"Passed: {len(passed)}/{len(TESTS)}")
    print(f"Failed: {len(failed)}/{len(TESTS)}")

    if failed:
        print("\nFailed tests:")
        for test in failed:
            print(f"- {test}")
        return 1

    print("\n=== Phase 1: ALL TESTS PASSED ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())