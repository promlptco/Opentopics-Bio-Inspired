# experiments/phase3_basic/config.py
"""
Phase 3 Basic — Mother + Child, fixed genome (all weights = 1.0).

Ecology: Phase 2 BALANCED from percept8 baseline (selected baseline).
  perception_radius=8, eat_gain=0.2, move_cost=0.005, init_food=150

Phase 3 adds:
  - One child per mother at initialization
  - CARE motivation enabled
  - Fixed genome: care=1.0, forage=1.0, self=1.0
  - Infant starvation multiplier = 35/15 ≈ 2.33 (LOGIC.md Change J)
  - food_perception_radius matches perception_radius=8 (percept8 baseline)

Everything else stays identical to Phase 2.
"""
import json
from pathlib import Path
from config import Config

_PHASE2_JSON = (
    Path(__file__).resolve().parent.parent.parent
    / "outputs/phase2_survival_minimal"
    / "auto_400_percept8"
    / "selected_ecologies.json"
)


def load_phase3_config(seed: int = 42) -> Config:
    """Build Phase 3 Config from Phase 2 BALANCED (percept8) ecology."""
    with open(_PHASE2_JSON) as f:
        data = json.load(f)
    ec = data["balanced"]["selected_config"]

    return Config(
        # Ecology — Phase 2 BALANCED percept8 (do not change)
        perception_radius=float(ec["perception_radius"]),
        hunger_rate=float(ec["hunger_rate"]),
        move_cost=float(ec["move_cost"]),
        eat_gain=float(ec["eat_gain"]),
        init_food=int(ec["init_food"]),
        rest_recovery=float(ec["rest_recovery"]),

        # food_perception_radius must match percept8 baseline (perception_radius=8).
        # Config default is 15 — override here so food sensing scale is consistent.
        food_perception_radius=int(ec["perception_radius"]),

        # Phase 3 additions
        children_enabled=True,
        care_enabled=True,
        infant_starvation_multiplier=35 / 15,  # LOGIC.md Change J

        # Subsystems OFF — same as Phase 2
        reproduction_enabled=False,
        mutation_enabled=False,
        plasticity_enabled=False,
        mother_max_age=None,

        # Fixed genome — all weights equal at 1.0 so all motivations compete fairly
        care_weight=1.0,
        forage_weight=1.0,
        self_weight=1.0,

        # Duration and population
        max_ticks=400,
        init_mothers=15,
        seed=seed,
    )
