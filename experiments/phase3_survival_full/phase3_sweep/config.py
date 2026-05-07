# experiments/phase3_sweep/config.py
"""
Phase 3 Sensitivity Sweep — init_food only.

Locked parameters (biological / ecological constraints):
  infant_starvation_multiplier = 2.33  (infants starve ~2.3x faster than adults)
  care_weight = forage_weight = self_weight = 1.0  (unbiased motivation)

Baseline options:
  percept8  — perception_radius=8,  eat_gain=0.2, init_food=150 (Phase 2 default)
  percept15 — perception_radius=15, eat_gain=0.5, init_food=40  (wider sensing)

Sweep variable:
  init_food  — primary resource that scales when 15 children are added to the ecosystem.

Research question:
  Can food density alone create enough ecological pressure for child survival
  through maternal care, with no motivational bias?
"""
import json
from pathlib import Path
from config import Config

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent

_PHASE2_JSON = {
    "percept8":  _PROJECT_ROOT / "outputs/phase2_survival_minimal/auto_400_percept8/selected_ecologies.json",
    "percept15": _PROJECT_ROOT / "outputs/phase2_survival_minimal/auto_400_percept15/selected_ecologies.json",
}

# Sweep values — starts at percept8 BALANCED baseline (150), extends upward.
# Lower values (40, 80) included to anchor the "Phase 2 only" reference point.
INIT_FOOD_VALUES = [40, 80, 150, 250, 400, 600, 900]

# 10 seeds — same validation standard as Phase 2.
SWEEP_SEEDS = list(range(42, 52))

# Viability thresholds
MOTHER_SURVIVAL_MIN  = 0.50   # at least half of mothers alive at tick 400
CHILD_MATURATION_MIN = 0.0    # strictly > 0: at least one child matured per seed on average


def load_sweep_config(init_food: int, seed: int = 42, baseline: str = "percept8") -> Config:
    """Build Phase 3 Config with the specified baseline ecology and given init_food."""
    if baseline not in _PHASE2_JSON:
        raise ValueError(f"Unknown baseline '{baseline}'. Choose from: {list(_PHASE2_JSON)}")
    with open(_PHASE2_JSON[baseline]) as f:
        data = json.load(f)
    ec = data["balanced"]["selected_config"]

    return Config(
        # Ecology — from selected baseline (do not change per-baseline values)
        perception_radius      = float(ec["perception_radius"]),
        hunger_rate            = float(ec["hunger_rate"]),
        move_cost              = float(ec["move_cost"]),
        eat_gain               = float(ec["eat_gain"]),
        rest_recovery          = float(ec["rest_recovery"]),
        food_perception_radius = int(ec["perception_radius"]),

        # Sweep variable
        init_food = init_food,

        # Phase 3 locked additions
        children_enabled             = True,
        care_enabled                 = True,
        infant_starvation_multiplier = 35 / 15,   # LOGIC.md Change J — locked
        reproduction_enabled         = False,
        mutation_enabled             = False,
        plasticity_enabled           = False,
        mother_max_age               = None,

        # Unbiased fixed genome — all motivations compete on equal footing
        care_weight   = 1.0,
        forage_weight = 1.0,
        self_weight   = 1.0,

        max_ticks    = 400,
        init_mothers = 15,
        seed         = seed,
    )
