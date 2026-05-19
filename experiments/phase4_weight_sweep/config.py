# experiments/phase4_weight_sweep/config.py
"""
Phase 4 Motivation Weight Sweep.

Research question:
    "What is the minimum care_weight bias that enables child maturation,
     given the Phase 3b BEST_ECOLOGICAL baseline?"

Ecology: Phase 3b BEST_ECOLOGICAL (ISM=1.0, eat_gain=0.70, init_food=600,
         move_cost=0.005).  Loaded from saved JSON; hardcoded fallback included.

Sweep: care_weight × forage_weight  (5 × 5 = 25 combos × 5 seeds = 125 runs).
       self_weight = 1.0 fixed.

Fixes carried forward from Phase 4 original analysis:
  Approach A — own-child exclusivity (already in simulation._execute_action)
  Approach E — starvation floor (care_energy_floor=0.3)
"""

from pathlib import Path
import json

# ─────────────────────────────────────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────────────────────────────────────
INIT_MOTHERS       = 15
INITIAL_ENERGY     = 1.0
MATURITY_AGE       = 80
MAX_TICKS          = 400
SWEEP_SEEDS        = list(range(42, 52))          # 10 seeds per combo
VALIDATION_SEEDS   = list(range(42, 52))          # 10 seeds for final validation

# ─────────────────────────────────────────────────────────────────────────────
# Phase 4 simulation flags
# ─────────────────────────────────────────────────────────────────────────────
PHASE4_FLAGS = {
    "children_enabled":             True,
    "care_enabled":                 True,
    "reproduction_enabled":         False,
    "mutation_enabled":             False,
    "plasticity_enabled":           False,
    "mother_max_age":               None,
    "maturity_age":                 MATURITY_AGE,
    "food_replace_on_pick":         True,
    "food_replenish_threshold_ratio": 0.0,
    "init_mothers":                 INIT_MOTHERS,
    "care_energy_floor":            0.3,          # Approach E starvation floor
}

# ─────────────────────────────────────────────────────────────────────────────
# Ecology baseline — Phase 3b BEST_ECOLOGICAL (ISM=1.2)
#
# Phase 3 (ISM=2.33 locked) showed the care trap null result.
# Phase 3b swept ISM and found ISM=1.2 as the ecology where child maturation
# is most feasible (feeds_needed=8.4 vs 17.6 at ISM=2.33).
# Phase 4's question is "what weight bias enables maturation?" — which requires
# an ecology where maturation is physically possible, hence ISM=1.2.
# ─────────────────────────────────────────────────────────────────────────────
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

# Phase 3b BEST_ECOLOGICAL — hardcoded (Phase 3b JSON may not exist after restructure)
BEST_ECOLOGICAL = {
    "infant_starvation_multiplier": 1.2,
    "eat_gain":               0.70,
    "init_food":              600,
    "move_cost":              0.005,
    "rest_recovery":          0.005,
    "hunger_rate":            1.0 / 35.0,
    "food_perception_radius": 8,
    "perception_radius":      8,
}

# Try to load from saved Phase 3b JSON — overrides hardcoded values if found.
_PHASE3B_PATHS = [
    _PROJECT_ROOT / "outputs/phase3b_calibration/selected_ecologies.json",
    _PROJECT_ROOT / "outputs/phase3_survival_full/phase3b_calibration/selected_ecologies.json",
]


def _load_phase3b_ecology() -> dict:
    for path in _PHASE3B_PATHS:
        if not path.exists():
            continue
        try:
            with open(path) as f:
                data = json.load(f)
            ec = data.get("best_ecological", {}).get("selected_config", {})
            if not ec:
                for v in data.values():
                    if isinstance(v, dict) and "selected_config" in v:
                        ec = v["selected_config"]
                        break
            if ec and "eat_gain" in ec and "init_food" in ec:
                print(f"  [Phase4 ecology] loaded BEST_ECOLOGICAL from {path.name}")
                return {
                    "infant_starvation_multiplier": float(ec.get("infant_starvation_multiplier", 1.2)),
                    "eat_gain":    float(ec["eat_gain"]),
                    "init_food":   int(ec["init_food"]),
                    "move_cost":   float(ec.get("move_cost", 0.005)),
                    "rest_recovery": float(ec.get("rest_recovery", 0.005)),
                    "hunger_rate": float(ec.get("hunger_rate", 1.0 / 35.0)),
                    "food_perception_radius": int(ec.get("food_perception_radius", ec.get("perception_radius", 8))),
                    "perception_radius":      int(ec.get("perception_radius", ec.get("food_perception_radius", 8))),
                }
        except Exception:
            continue
    print("  [Phase4 ecology] using hardcoded Phase 3b BEST_ECOLOGICAL (ISM=1.2)")
    return dict(BEST_ECOLOGICAL)


BEST_ECOLOGICAL = _load_phase3b_ecology()

# ─────────────────────────────────────────────────────────────────────────────
# Sweep grid
# ─────────────────────────────────────────────────────────────────────────────
CARE_WEIGHT_VALUES   = [0.1, 0.5, 1.0, 1.5, 2.0]
FORAGE_WEIGHT_VALUES = [0.1, 0.5, 1.0, 1.5, 2.0]
SELF_WEIGHT_FIXED    = 1.0

# Selection thresholds
VIABLE_MIN_C_MATR    = 0.10   # minimum C_matr to be considered VIABLE_MIN
OPTIMAL_LABEL        = "OPTIMAL"
VIABLE_LABEL         = "VIABLE_MIN"

# ─────────────────────────────────────────────────────────────────────────────
# Config factory
# ─────────────────────────────────────────────────────────────────────────────

def make_config(care_weight: float, forage_weight: float,
                self_weight: float = SELF_WEIGHT_FIXED,
                duration: int = MAX_TICKS):
    """Build a Phase 4 Config for the given weight combination."""
    from config import Config
    cfg = Config()
    cfg.max_ticks      = duration
    cfg.initial_energy = INITIAL_ENERGY

    eco = BEST_ECOLOGICAL
    cfg.infant_starvation_multiplier = float(eco["infant_starvation_multiplier"])
    cfg.eat_gain                     = float(eco["eat_gain"])
    cfg.init_food                    = int(eco["init_food"])
    cfg.move_cost                    = float(eco["move_cost"])
    cfg.rest_recovery                = float(eco["rest_recovery"])
    cfg.hunger_rate                  = float(eco["hunger_rate"])
    cfg.food_perception_radius       = int(eco["food_perception_radius"])
    cfg.perception_radius            = int(eco["perception_radius"])

    cfg.care_weight   = float(care_weight)
    cfg.forage_weight = float(forage_weight)
    cfg.self_weight   = float(self_weight)

    for k, v in PHASE4_FLAGS.items():
        setattr(cfg, k, v)

    return cfg
