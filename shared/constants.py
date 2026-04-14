# shared/constants.py
# Single source of truth for all cross-phase constants.
# EXPERIMENT_DESIGN.md §4: "No phase may hardcode a value measured in another phase."
#
# Update rules:
#   CANONICAL_MULT / CANONICAL_SCATTER  — set after Phase 5 ecology sweep completes.
#   DEPLETED_BASELINE                   — set after Phase 10 multi-seed run completes.
#   All other values below are frozen baselines — do NOT change without a Session Note entry.

# ---------------------------------------------------------------------------
# Frozen ecological parameters (set in Phase 07, used in Phases 08, 09, 10, 11)
# ---------------------------------------------------------------------------
INFANT_STARVATION_MULT  = 1.15   # infants hunger 15% faster; B near-existential
BIRTH_SCATTER_RADIUS    = 2      # tight natal philopatry — keeps kin clustered
CONTROL_SCATTER_RADIUS  = 8      # Phase 08 dispersal ablation (standard dispersal)

# ---------------------------------------------------------------------------
# Frozen baseline measurements
# ---------------------------------------------------------------------------
# Phase 05 (standard evolved genomes, high-care): care_window_rate ticks 0–100.
# Source: outputs/phase05_zeroshot_standard/run_20260409_233243_seed42
PHASE3_ZS_BASELINE = 0.09069

# ---------------------------------------------------------------------------
# Canonical good ecology (set after Phase 5 sweep — placeholder until then)
# ---------------------------------------------------------------------------
CANONICAL_MULT    = None   # infant_starvation_multiplier for selected good ecology
CANONICAL_SCATTER = None   # birth_scatter_radius for selected good ecology

# ---------------------------------------------------------------------------
# Depleted-init zero-shot baseline (set after Phase 10 multi-seed run)
# ---------------------------------------------------------------------------
# care_window_rate from fresh depleted genomes (cw~U(0,0.5)), mult=1.15, scatter=2,
# no evolution/plasticity. Fair comparison baseline for Phases 08 and 09 zero-shot rates.
DEPLETED_BASELINE = None
