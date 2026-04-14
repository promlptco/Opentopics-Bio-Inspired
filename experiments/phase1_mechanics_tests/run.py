# experiments/phase1_mechanics_tests/run.py
"""Phase 1: Run all unit tests and aggregate results."""
import subprocess
import sys
import os

TESTS = [
    "test_01_mutation.py",
    "test_02_inheritance.py",
    "test_03_reproduction.py",
    "test_04_population_stability.py",
    "test_05_stochasticity_identity.py",
    "test_06_softmax_calibration.py",
]

phase_dir = os.path.dirname(os.path.abspath(__file__))

failed = []
for test in TESTS:
    result = subprocess.run([sys.executable, os.path.join(phase_dir, test)])
    if result.returncode != 0:
        failed.append(test)

if failed:
    print(f"\n=== FAILED: {failed} ===")
    sys.exit(1)
else:
    print("\n=== Phase 1: ALL TESTS PASSED ===")