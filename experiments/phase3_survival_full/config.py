from itertools import product

import numpy as np


# ============================================================
# Global simulation constants
# ============================================================

INIT_MOTHERS = 15
INITIAL_ENERGY = 0.75

VALIDATION_SEEDS = list(range(42, 47))
DEFAULT_SWEEP_SEED_BASE = 42000
DEFAULT_PERCEPTION_RADIUS = 8.0
TAIL_WINDOW = 200


# ============================================================
# Plot switches
# ============================================================

PLOT_SMOOTH_WINDOW = 25

ENABLE_VALIDATION_PLOT = True
ENABLE_ACTION_SELECTION_PLOT = True
ENABLE_MOTIVATION_SELECTION_PLOT = True
ENABLE_FAILED_SELECTION_PLOT = True
ENABLE_MOTHER_CHILD_DIAGNOSTIC_PLOT = True
ENABLE_FEED_RATE_PLOT = True
ENABLE_SPATIAL_HEATMAP_PLOT = True


# ============================================================
# Phase 3 baseline
# ============================================================

# Phase 3 starts from the Phase 2 ecological baseline, then adds
# mother-child caregiving parameters.
#
# The main hypothesis is:
#   adding a child increases caregiving demand,
#   therefore the required resource level should increase.
PHASE3_BASELINE = {
    # Mother ecology, inherited from Phase 2 style baseline.
    "width": 30,
    "height": 30,
    "perception_radius": DEFAULT_PERCEPTION_RADIUS,
    "hunger_rate": 0.005,
    "move_cost": 0.001,
    "eat_gain": 0.07,
    "init_food": 60,
    "rest_recovery": 0.005,
    "fatigue_rate": 0.01,

    # Child physiology.
    # ChildAgent.update_hunger() increases child hunger by this amount per tick.
    "child_hunger_rate": 0.005,

    # Feeding mechanics.
    # feed_amount = how much child hunger is reduced by one successful feed.
    # feed_cost   = mother energy paid when feeding the child.
    # feed_distance = max grid distance for feeding.
    "feed_amount": 0.20,
    "feed_cost": 0.01,
    "feed_distance": 1,

    # Food respawn control.
    "food_respawn_per_tick": 3,

    # Motivation weights.
    # These are fixed in Phase 3 baseline validation.
    "care_weight": 0.85,
    "forage_weight": 0.70,
    "self_weight": 0.30,
}


# ============================================================
# Baseline selection targets for run.py
# ============================================================

SELECTION_TARGETS = {
    "balanced": {
        # Family-level edge of stability:
        # mothers and children mostly survive, child hunger is controlled,
        # but mother energy is not saturated.
        "min_final_mothers": 14.0,
        "min_final_children": 14.0,
        "mother_energy_low": 0.65,
        "mother_energy_high": 0.80,
        "target_mother_energy": 0.72,
        "max_child_hunger": 0.35,
        "max_child_distress": 0.40,
    },
    "easy": {
        # Comfortable mother-child condition.
        "min_final_mothers": 14.5,
        "min_final_children": 14.5,
        "min_mother_energy": 0.85,
        "max_child_hunger": 0.20,
        "max_child_distress": 0.25,
    },
    "harsh": {
        # Harsh should preferably expose caregiving failure:
        # mothers may still partially survive, but children collapse.
        "min_final_mothers": 5.0,
        "max_final_children": 5.0,
        "target_final_children": 3.0,
    },
}


# ============================================================
# Candidate grid for run.py baseline selection
# ============================================================

def candidate_configs(mode="sweep"):
    """
    Generate candidate parameter sets for Phase 3 run.py.

    mode="single":
        Runs one hand-picked mother-child configuration.

    mode="sweep":
        Sweeps init_food while keeping mother ecology and child/feed
        parameters fixed. This directly tests whether adding children
        increases the required resource level relative to Phase 2.
    """
    if mode == "single":
        return [
            {
                **PHASE3_BASELINE,
                "init_food": 70,
                "name": "single_test",
            }
        ]

    grid = {
        **{k: [v] for k, v in PHASE3_BASELINE.items() if k != "init_food"},

        # Main Phase 3 resource axis.
        # Start near Phase 2 levels and extend upward because caregiving
        # should require more resources.
        "init_food": [
            20, 25, 30, 35, 40, 45, 50, 55, 60,
            65, 70, 75, 80, 90, 100, 110, 120,
        ],
    }

    keys = list(grid.keys())
    configs = []

    for values in product(*[grid[k] for k in keys]):
        params = dict(zip(keys, values))
        params["name"] = "candidate"
        configs.append(params)

    return configs


# ============================================================
# Sensitivity sweep configuration
# ============================================================

# Same spirit as Phase 2:
# choose which sets to run using sensitivity_sweep.py --sets A, AB, ABCD, etc.
#
# Recommended first run:
#   --sets A
#
# Full diagnostic run:
#   --sets ABCD
PHASE3_SENSITIVITY_SWEEPS = {
    "A": {
        "label": "init_food",
        "key": "init_food",
        "values": [
            20, 25, 30, 35, 40, 45, 50, 55, 60,
            65, 70, 75, 80, 90, 100, 110, 120,
        ],
    },
    "B": {
        "label": "child_hunger_rate",
        "key": "child_hunger_rate",
        "values": np.unique(
            np.round(
                np.array([0.0025, 0.0035, 0.005, 0.0075, 0.01, 0.0125, 0.015]),
                5,
            )
        ).tolist(),
    },
    "C": {
        "label": "feed_amount",
        "key": "feed_amount",
        "values": np.unique(
            np.round(
                np.array([0.10, 0.15, 0.20, 0.25, 0.30, 0.35]),
                4,
            )
        ).tolist(),
    },
    "D": {
        "label": "feed_cost",
        "key": "feed_cost",
        "values": np.unique(
            np.round(
                np.array([0.0, 0.005, 0.01, 0.02, 0.03, 0.05]),
                4,
            )
        ).tolist(),
    },
}


PHASE3_SENSITIVITY_SUBPLOT_CONFIG = [
    ("A", "init_food", "Initial Food Count", "#D08770"),
    ("B", "child_hunger_rate", "Child Hunger Rate", "#BF616A"),
    ("C", "feed_amount", "Feed Amount", "#A3BE8C"),
    ("D", "feed_cost", "Feed Cost", "#5E81AC"),
]


# Hide vertical baseline lines in sensitivity plots.
# Use set() to show all baseline lines.
HIDE_BASELINE_FOR = set()