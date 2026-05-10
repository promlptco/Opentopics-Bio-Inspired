# experiments/phase4_weight_sweep/phase4b_config.py
"""
Phase 4b Ecology Calibration — sweep init_food × eat_gain with OPTIMAL weights.

Research question:
    "Given OPTIMAL motivation weights (care=0.5, forage=2.0, self=1.0) and
     ISM=1.0, which init_food × eat_gain ecology produces a stable mother
     population AND feasible child maturation (C_matr >= 0.05)?"

Context:
    Phase 4's OPTIMAL weights were validated on Phase 3b's ecology (eat_gain=0.70,
    init_food=600).  Block 2 was intended to use Phase 2 easy ecology
    (eat_gain=0.50, init_food=150, move_cost=0.02).  Those two ecologies differ
    substantially in energy availability per tick — Phase 4's weights cannot be
    assumed to produce viable C_matr under Phase 2 easy conditions.

    Phase 4b finds the BEST_CALIBRATED (EASY) ecology under the actual OPTIMAL
    weight bias, giving Phase 5 a validated starting condition.

Fixed:
    ISM       = 1.0   (most permissive child vulnerability)
    move_cost = 0.005 (matches Phase 4 working ecology; 0.02 is too harsh for 30 agents)
    care_weight=0.5, forage_weight=2.0, self_weight=1.0 (Phase 4 OPTIMAL)

Sweep:
    init_food × eat_gain  (7 × 4 = 28 combos × 10 seeds × 3 repeats = 840 runs)

Selection:
    BEST_CALIBRATED = EASY ecology: mother_survival >= 0.80 AND C_matr >= 0.05.
    Among valid combos: highest C_matr (most maturation headroom for Phase 5).
"""

# ─────────────────────────────────────────────────────────────────────────────
# Locked parameters
# ─────────────────────────────────────────────────────────────────────────────
ISM               = 1.0           # infant_starvation_multiplier
MOVE_COST_FIXED   = 0.005         # matches Phase 4 working ecology (0.02 too harsh with 30 agents)
REST_RECOVERY     = 0.005
HUNGER_RATE       = 1.0 / 35.0
PERCEPTION_RADIUS = 8

OPTIMAL_WEIGHTS = {
    "care_weight":   0.5,
    "forage_weight": 2.0,
    "self_weight":   1.0,
}

INIT_MOTHERS   = 15
INITIAL_ENERGY = 1.0
MATURITY_AGE   = 200
MAX_TICKS      = 400
SWEEP_SEEDS    = list(range(42, 52))    # 10 seeds
N_REPEATS      = 3

# ─────────────────────────────────────────────────────────────────────────────
# Simulation flags
# ─────────────────────────────────────────────────────────────────────────────
PHASE4B_FLAGS = {
    "children_enabled":               True,
    "care_enabled":                   True,
    "reproduction_enabled":           False,
    "mutation_enabled":               False,
    "plasticity_enabled":             False,
    "mother_max_age":                 None,
    "infant_starvation_multiplier":   ISM,
    "maturity_age":                   MATURITY_AGE,
    "food_replace_on_pick":           True,
    "food_replenish_threshold_ratio": 0.0,
    "init_mothers":                   INIT_MOTHERS,
    "care_energy_floor":              0.3,    # Approach E starvation floor (Phase 4)
}

# ─────────────────────────────────────────────────────────────────────────────
# Sweep grid
# ─────────────────────────────────────────────────────────────────────────────
INIT_FOOD_VALUES = [50, 100, 150, 200, 300, 400, 600]
EAT_GAIN_VALUES  = [0.20, 0.30, 0.50, 0.70]

# ─────────────────────────────────────────────────────────────────────────────
# Selection thresholds (EASY + non-trivial maturation)
# ─────────────────────────────────────────────────────────────────────────────
MOTHER_SURVIVAL_MIN   = 0.80    # mothers must be stable (EASY criterion)
CMATR_MIN             = 0.05    # at least 5% child maturation (non-trivial)
BEST_CALIBRATED_LABEL = "BEST_CALIBRATED"


# ─────────────────────────────────────────────────────────────────────────────
# Config factory
# ─────────────────────────────────────────────────────────────────────────────

def make_config(init_food: int, eat_gain: float, duration: int = MAX_TICKS):
    """Build a Phase 4b Config for one (init_food, eat_gain) combination."""
    from config import Config
    cfg = Config()
    cfg.max_ticks      = duration
    cfg.initial_energy = INITIAL_ENERGY

    cfg.eat_gain                     = float(eat_gain)
    cfg.init_food                    = int(init_food)
    cfg.move_cost                    = MOVE_COST_FIXED
    cfg.rest_recovery                = REST_RECOVERY
    cfg.hunger_rate                  = HUNGER_RATE
    cfg.food_perception_radius       = PERCEPTION_RADIUS
    cfg.perception_radius            = PERCEPTION_RADIUS

    cfg.care_weight   = OPTIMAL_WEIGHTS["care_weight"]
    cfg.forage_weight = OPTIMAL_WEIGHTS["forage_weight"]
    cfg.self_weight   = OPTIMAL_WEIGHTS["self_weight"]

    for k, v in PHASE4B_FLAGS.items():
        setattr(cfg, k, v)

    return cfg
