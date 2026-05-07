# experiments/phase3b_calibration/config.py
"""
Phase 3b Ecological Calibration — Standalone child-survival calibration.

Research question:
    "Can ecologically plausible parameters, with unbiased motivation weights
     (all = 1.0), produce child maturation (reach tick 200)?"

Swept axes:
    infant_starvation_multiplier (ISM) — key child vulnerability parameter
    eat_gain                           — energy per feed event
    init_food                          — food density → forage cycle speed

Fixed (locked for Phase 3b):
    hunger_rate = 1/35, move_cost = 0.005, rest_recovery = 0.005
    care/forage/self weights = 1.0 (unbiased)
    warmth_factor = 0.0 (reserved Phase 5+)
    init_mothers = 15, maturity_age = 200, max_ticks = 400

Mathematical foundation:
    feeds_needed = (200 * hunger_rate * ISM - 1.0) / eat_gain
                 = (5.714 * ISM - 1.0) / eat_gain

    ISM=1.5, eat_gain=0.30 → feeds_needed ≈ 25  (achievable)
    ISM=2.33, eat_gain=0.20 → feeds_needed ≈ 62  (impossible with unbiased weights)
"""
from itertools import product

# ── Population / timing constants ─────────────────────────────────────────────
INIT_MOTHERS = 15
MAX_TICKS    = 400
MATURITY_AGE = 200

# ── Seeds ─────────────────────────────────────────────────────────────────────
ANCHOR_SEEDS     = list(range(42, 45))   # 3 seeds — feasibility anchor
OVAT_SEEDS       = list(range(42, 47))   # 5 seeds per OVAT value
GRID_SEEDS       = list(range(42, 47))   # 5 seeds per grid combo
VALIDATION_SEEDS = list(range(42, 52))   # 10 seeds — final validation

# ── Feasibility anchor ─────────────────────────────────────────────────────────
# Fix init_food=600, sweep ISM x eat_gain to find first C_matr > 0
ANCHOR_INIT_FOOD = 600
ANCHOR_ISM       = [1.0, 1.5, 2.0, 2.33, 2.5]
ANCHOR_EAT_GAIN  = [0.15, 0.20, 0.30, 0.50, 0.70]

# ── OVAT baseline (center point) ──────────────────────────────────────────────
OVAT_BASELINE = {
    "infant_starvation_multiplier": 2.0,
    "eat_gain":                     0.30,
    "init_food":                    400,
    "move_cost":                    0.005,
    "rest_recovery":                0.005,
}

# ── OVAT sweep sets ────────────────────────────────────────────────────────────
OVAT_SWEEPS = {
    "A": {
        "label": "ISM",
        "key":   "infant_starvation_multiplier",
        "values": [1.0, 1.5, 2.0, 2.33, 2.5],
        "hold_eat_gain": 0.30,
        "hold_init_food": 400,
    },
    "B": {
        "label": "eat_gain",
        "key":   "eat_gain",
        "values": [0.15, 0.20, 0.30, 0.50, 0.70],
        "hold_ism": 1.5,
        "hold_init_food": 400,
    },
    "C": {
        "label": "init_food",
        "key":   "init_food",
        "values": [100, 200, 400, 600, 900],
        "hold_ism": 1.5,
        "hold_eat_gain": 0.30,
    },
}

# ── Full 3D grid (ISM x eat_gain x init_food) ─────────────────────────────────
# 4 x 4 x 4 = 64 combos x 5 seeds = 320 runs
SWEEP_GRID = {
    "infant_starvation_multiplier": [1.2, 1.5, 2.0, 2.33],
    "eat_gain":                     [0.20, 0.30, 0.50, 0.70],
    "init_food":                    [100, 300, 600, 900],
}

# ── Regime selection thresholds ────────────────────────────────────────────────
# Priority: C_matr > child_death_tick_mean > M_surv
VIABLE_MIN_M_SURV = 0.30   # must have at least 30% mother survival
VIABLE_MIN_C_MATR = 0.0    # any C_matr > 0 counts

# ── Phase 3b locked simulation flags ──────────────────────────────────────────
PHASE3B_FLAGS = {
    "children_enabled":             True,
    "care_enabled":                 True,
    "reproduction_enabled":         False,
    "mutation_enabled":             False,
    "plasticity_enabled":           False,
    "mother_max_age":               None,
    "perception_radius":            8,
    "food_perception_radius":       8,
    "init_mothers":                 INIT_MOTHERS,
    "maturity_age":                 MATURITY_AGE,
    "max_ticks":                    MAX_TICKS,
    "care_weight":                  1.0,
    "forage_weight":                1.0,
    "self_weight":                  1.0,
    "warmth_factor":                0.0,
    "move_cost":                    0.005,
    "rest_recovery":                0.005,
}


def make_config(ism: float, eat_gain: float, init_food: int, seed: int):
    """Build a Config for one simulation run."""
    from config import Config
    return Config(
        seed=seed,
        infant_starvation_multiplier=ism,
        eat_gain=eat_gain,
        init_food=init_food,
        **{k: v for k, v in PHASE3B_FLAGS.items()},
    )


def expand_anchor() -> list[dict]:
    """All ISM x eat_gain combos for the anchor sweep."""
    combos = []
    for ism in ANCHOR_ISM:
        for eg in ANCHOR_EAT_GAIN:
            combos.append({
                "infant_starvation_multiplier": ism,
                "eat_gain": eg,
                "init_food": ANCHOR_INIT_FOOD,
            })
    return combos


def expand_ovat(set_key: str) -> list[dict]:
    """Return param dicts for one OVAT set (A, B, or C)."""
    sw = OVAT_SWEEPS[set_key]
    combos = []
    for v in sw["values"]:
        params = {
            "infant_starvation_multiplier": sw.get("hold_ism", OVAT_BASELINE["infant_starvation_multiplier"]),
            "eat_gain":                     sw.get("hold_eat_gain", OVAT_BASELINE["eat_gain"]),
            "init_food":                    sw.get("hold_init_food", OVAT_BASELINE["init_food"]),
        }
        params[sw["key"]] = v
        combos.append(params)
    return combos


def expand_grid() -> list[dict]:
    """Return flat list of ISM x eat_gain x init_food combos."""
    keys   = list(SWEEP_GRID.keys())
    combos = []
    for values in product(*[SWEEP_GRID[k] for k in keys]):
        combos.append(dict(zip(keys, values)))
    return combos


def feeds_needed(ism: float, eat_gain: float) -> float:
    """Theoretical minimum feeds for child survival (hunger_rate = 1/35)."""
    return max(0.0, (200 * (1 / 35) * ism - 1.0) / eat_gain)
