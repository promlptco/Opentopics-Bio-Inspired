from itertools import product

import numpy as np


INIT_MOTHERS = 15
INITIAL_ENERGY = 0.75

VALIDATION_SEEDS = list(range(42, 47))
DEFAULT_SWEEP_SEED_BASE = 42000
DEFAULT_PERCEPTION_RADIUS = 30.0
TAIL_WINDOW = 200

# ====================================================================
# Balanced baseline used as the reference point for sensitivity sweep.
# ====================================================================
BALANCED_BASELINE = {
    "perception_radius": DEFAULT_PERCEPTION_RADIUS,
    "hunger_rate": 0.005,
    "move_cost": 0.001,
    "eat_gain": 0.07,
    "init_food": 60,
    "rest_recovery": 0.005,
}

SENSITIVITY_SWEEPS = {
    "A": {
        "label": "hunger_rate",
        "key": "hunger_rate",
        "values": np.unique(
            np.round(
                np.concatenate(
                    [
                        np.arange(0.001, 0.004, 0.001),
                        np.arange(0.004, 0.0085, 0.0005),
                        np.arange(0.009, 0.016, 0.001),
                    ]
                ),
                5,
            )
        ).tolist(),
    },
    "B": {
        "label": "move_cost",
        "key": "move_cost",
        "values": np.unique(
            np.round(
                np.concatenate(
                    [
                        np.arange(0.0005, 0.001, 0.0002),
                        np.arange(0.001, 0.0045, 0.0005),
                        np.arange(0.005, 0.0086, 0.001),
                    ]
                ),
                5,
            )
        ).tolist(),
    },
    "C": {
        "label": "eat_gain",
        "key": "eat_gain",
        "values": np.unique(
            np.round(
                np.concatenate(
                    [
                        np.arange(0.03, 0.05, 0.01),
                        np.arange(0.05, 0.085, 0.005),
                        np.arange(0.09, 0.165, 0.01),
                    ]
                ),
                5,
            )
        ).tolist(),
    },
    "D": {
        "label": "init_food",
        "key": "init_food",
        "values": np.unique(
            np.concatenate(
                [
                    np.arange(20, 30, 5),
                    np.arange(30, 65, 2),
                    np.arange(65, 106, 5),
                ]
            ).astype(int)
        ).tolist(),
    },
    "E": {
        "label": "rest_recovery",
        "key": "rest_recovery",
        "values": list(np.round(np.arange(0.005, 0.111, 0.005), 4)),
    },
}


SENSITIVITY_SUBPLOT_CONFIG = [
    ("A", "hunger_rate", "Hunger Rate (per tick)", "#4C566A"),
    ("B", "move_cost", "Move Cost (per step)", "#5E81AC"),
    ("C", "eat_gain", "Eat Gain (energy per food)", "#8FBCBB"),
    ("D", "init_food", "Initial Food Count", "#D08770"),
    ("E", "rest_recovery", "Rest Recovery (per tick)", "#B48EAD"),
]


HIDE_BASELINE_FOR = set(["hunger_rate", "move_cost", "eat_gain", "init_food", "rest_recovery"])
# Example:
# HIDE_BASELINE_FOR = {"rest_recovery", "init_food"}    

# ====================================================================
# Candidate grid for run.py baseline selection -- sweep or single test.
# ====================================================================

SELECTION_TARGETS = {
    "balanced": {
        "min_final_pop": 14.0,
        "energy_low": 0.70,
        "energy_high": 0.75,
        "target_energy": 0.725,
        "max_tail_sd": 0.05,
        "max_abs_energy_slope": 0.00005,
        "max_abs_pop_slope": 0.002,
    },
    "easy": {
        "min_final_pop": 14.5,
        "min_energy": 0.90,
        "target_energy": 0.95,
        "max_tail_sd": 0.08,
    },
    "harsh": {
        "min_final_pop": 0.5,
        "max_final_pop": 5.0,
        "energy_low": 0.05,
        "energy_high": 0.55,
        "target_pop": 3.0,
        "target_energy": 0.30,
    },
}

def candidate_configs(mode="sweep"):
    if mode == "single":
        return [
            {
                "perception_radius": DEFAULT_PERCEPTION_RADIUS,
                "hunger_rate": 0.0045,
                "move_cost": 0.0005,
                "eat_gain": 0.08,
                "init_food": 45,
                "rest_recovery": 0.005,
                "name": "single_test",
            }
        ]

    grid = {
        "perception_radius": [DEFAULT_PERCEPTION_RADIUS],
        "hunger_rate": [0.005],
        "move_cost": [0.001],
        "eat_gain": [0.07],
        "init_food": [20, 25, 30, 35, 40, 43, 45, 48, 50, 53, 55, 60, 65, 70, 75, 80],
        "rest_recovery": [0.005, 0.01, 0.015, 0.02, 0.025, 0.03, 0.035, 0.04, 0.045, 0.05, 0.06, 0.08, 0.10, 0.15],
    }
    # After we rough sensitivity sweep we got a balanced hunger_rate, move_cost and eat_gain, 
    # so we keep those fixed and do a finer sweep on init_food and rest_recovery to find good candidates around the balanced baseline then saperate the easy and harsh alongside.

    keys = list(grid.keys())
    configs = []

    for values in product(*[grid[k] for k in keys]):
        params = dict(zip(keys, values))
        params["name"] = "candidate"
        configs.append(params)

    return configs