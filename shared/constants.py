# shared/constants.py
"""Constants shared across multiple experiment phases.

All values are measured/verified from actual run outputs on disk.
Do not change these without re-running the relevant phase.
"""

# Phase 3e (p3_care_erosion / phase04_care_erosion) — measured zero-shot baseline
# Source: outputs/phase05_zeroshot_standard/run_20260409_233243_seed42/zeroshot_metrics.json
PHASE3_ZS_BASELINE = 0.09069  # care events / alive-mother-tick, ticks 0-100

# Phase 5 (p5_enhanced_ecology / phase07_ecological_emergence) — calibrated ecology
INFANT_STARVATION_MULT = 1.15  # infant starvation multiplier
BIRTH_SCATTER_RADIUS   = 2     # tight natal philopatry radius
CONTROL_SCATTER_RADIUS = 8     # dispersal control scatter radius (Phase 6a)

# Phase 5 multi-seed result (verified from statistical_tests.json)
PHASE07_MEAN_R = 0.079  # mean selection gradient, seeds 42-51
