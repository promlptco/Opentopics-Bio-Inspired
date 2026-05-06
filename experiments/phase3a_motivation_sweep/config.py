# experiments/phase3a_motivation_sweep/config.py
"""
Phase 3a configuration.

Ecology: loaded at runtime from the locked Phase 2 BALANCED baseline JSON.
Do not hardcode ecology values here — load from the JSON so changes propagate.
"""
import json
from pathlib import Path
from config import Config

_PHASE2_JSON = (
    Path(__file__).resolve().parent.parent.parent
    / "outputs/phase2_survival_minimal"
    / "auto_400_percept15_repeat3_validation_selected_baselines"
    / "selected_ecologies.json"
)

# Phase 3 food calibration result — init_food recalibrated for Phase 3a mechanics.
# Phase 2 BALANCED used init_food=40 (mothers only). Phase 3a needs more food
# because 15 children also compete for resources. Selected by food calibration sweep.
_PHASE3_FOOD_JSON = (
    Path(__file__).resolve().parent.parent.parent
    / "outputs/phase3_food_calibration"
    / "20260506_210302_food_sweep"
    / "selected_init_food.json"
)


def load_balanced_config() -> Config:
    """Build Phase 3a base Config from the locked Phase 2 BALANCED ecology."""
    with open(_PHASE2_JSON) as f:
        data = json.load(f)
    ec = data["balanced"]["selected_config"]

    with open(_PHASE3_FOOD_JSON) as f:
        calibrated_food = json.load(f)["recommended_init_food"]

    return Config(
        # Ecology — from Phase 2 BALANCED (do not override)
        perception_radius=float(ec["perception_radius"]),
        hunger_rate=float(ec["hunger_rate"]),
        move_cost=float(ec["move_cost"]),
        eat_gain=float(ec["eat_gain"]),
        # init_food overridden by Phase 3 food calibration (was 40, now 120).
        # Phase 2 BALANCED had no children; Phase 3a adds 15 children competing for food.
        init_food=calibrated_food,
        rest_recovery=float(ec["rest_recovery"]),
        # Food replenishment — 1:1 replacement is the universal default (food_replace_on_pick=True).
        # No override needed; Config default keeps food count at init_food across all phases.
        # Age cap — disabled: Phase 2 SurvivalSimulation has no age cap; BALANCED ecology
        # was calibrated without one. Setting 400 would kill every survivor at the last tick.
        mother_max_age=None,
        # Phase 3a mode flags
        children_enabled=True,
        care_enabled=True,
        reproduction_enabled=False,
        mutation_enabled=False,
        plasticity_enabled=False,
        # Restored to LOGIC.md Change J: infant starves in 15 ticks = 3 days (35/15 ≈ 2.33)
        infant_starvation_multiplier=35 / 15,
        max_ticks=400,
        init_mothers=15,
        # Genome weights — overridden per sweep point in run.py
        care_weight=0.0,
        forage_weight=0.0,
        self_weight=0.0,
    )


# ── Genome sweep grids ────────────────────────────────────────────────────────

# Coarse (step=0.2): 6×6×6 = 216 combinations — default first pass
COARSE_VALS = [0.0, 0.2, 0.4, 0.6, 0.8, 1.0]

# Fine (step=0.1): 11×11×11 = 1331 combinations — refine around passing region
FINE_VALS = [0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]

GRID_VALS: dict[str, list[float]] = {
    "coarse": COARSE_VALS,
    "fine": FINE_VALS,
}

# ── Selection thresholds ──────────────────────────────────────────────────────

CHILD_SURVIVAL_MIN = 0.0      # any child reached maturity
MOTHER_SURVIVAL_MIN = 0.5     # at least half of mothers alive at tick 400
MOTHER_ENERGY_MIN = 0.1       # mean mother energy not collapsed
CARE_CHOICE_MIN = 0.05        # CARE is non-trivial (>5% of visible-child choices)
