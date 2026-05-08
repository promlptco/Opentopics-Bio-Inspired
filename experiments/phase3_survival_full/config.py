# experiments/phase3_survival_full/config.py
"""
Phase 3 Ecological Calibration — Maternal Care with Children.

Research question:
    "What ecological conditions (init_food × eat_gain × move_cost) allow
     mother-child pairs to coexist, given unbiased motivation weights (1/1/1)?"

Methodology:
    Identical 8-step OVAT pipeline as Phase 2, but:
    - children_enabled = True   (15 mother–child pairs spawned at t=0)
    - care_enabled     = True   (CARE motivation domain active)
    - care_weight = forage_weight = self_weight = 1.0  (unbiased)
    - infant_starvation_multiplier = 35/15 ≈ 2.33  (LOGIC.md locked)
    - Same OVAT sweep axes: init_food, eat_gain, move_cost
    - Extended init_food range (children add resource pressure)
    - Option-C child criteria added on top of Phase 2 mother gate

Phase 2 anchor:
    Loads Phase 2's selected BALANCED ecology from
    outputs/phase2_survival_minimal/auto_400_percept8/selected_ecologies.json.
    Falls back to hardcoded provisional values if that file is absent.
"""

from itertools import product
from pathlib import Path
import json
import numpy as np


# ─────────────────────────────────────────────────────────────────────────────
# Global constants (same as Phase 2 where applicable)
# ─────────────────────────────────────────────────────────────────────────────
INIT_MOTHERS            = 15
INITIAL_ENERGY          = 1.0
VALIDATION_SEEDS        = list(range(42, 52))   # 10 seeds — same standard as Phase 2
DEFAULT_SWEEP_SEED_BASE = 43000                 # offset from Phase 2 (42000) to avoid seed collision
TAIL_WINDOW             = 200
PLOT_SMOOTH_WINDOW      = 25
DEFAULT_PERCEPTION_RADIUS = 8.0

# Phase 3 biological constants (LOGIC.md locked — do not tune)
ISM          = 35 / 15   # infant_starvation_multiplier ≈ 2.33; infant starves in 15 ticks = 3 days
MATURITY_AGE = 200       # ticks to reach maturity (5 ticks/day × 40 days)
MAX_TICKS    = 400       # simulation length (5 ticks/day × 80 days)


# ─────────────────────────────────────────────────────────────────────────────
# Phase 3 fixed simulation flags
# ─────────────────────────────────────────────────────────────────────────────
PHASE3_FLAGS = {
    "children_enabled":               True,
    "care_enabled":                   True,
    "reproduction_enabled":           False,
    "mutation_enabled":               False,
    "plasticity_enabled":             False,
    "mother_max_age":                 None,
    "infant_starvation_multiplier":   ISM,
    "maturity_age":                   MATURITY_AGE,
    "food_replace_on_pick":           True,
    "food_replenish_threshold_ratio": 0.0,   # burst replenishment off
    "init_mothers":                   INIT_MOTHERS,
    "food_perception_radius":         int(DEFAULT_PERCEPTION_RADIUS),
    "perception_radius":              int(DEFAULT_PERCEPTION_RADIUS),
}

# ─────────────────────────────────────────────────────────────────────────────
# Baseline genome (unbiased — all motivations compete on equal footing)
# ─────────────────────────────────────────────────────────────────────────────
BASELINE_GENOME_WEIGHTS = {
    "care_weight":   1.0,
    "forage_weight": 1.0,
    "self_weight":   1.0,
}


# ─────────────────────────────────────────────────────────────────────────────
# Phase 2 anchor — load BALANCED ecology as Phase 3 starting anchor
# ─────────────────────────────────────────────────────────────────────────────
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
_PHASE2_ECO_PATHS = [
    _PROJECT_ROOT / "outputs/phase2_survival_minimal/auto_400_percept8/selected_ecologies.json",
    _PROJECT_ROOT / "outputs/phase2_survival_minimal/auto_400_percept15/selected_ecologies.json",
    _PROJECT_ROOT / "outputs/phase2_survival_minimal/auto_400_percept25/selected_ecologies.json",
]


def _load_phase2_balanced() -> dict:
    """Load Phase 2 BALANCED ecology as Phase 3 anchor. Falls back to provisionals."""
    for path in _PHASE2_ECO_PATHS:
        if not path.exists():
            continue
        try:
            with open(path) as f:
                data = json.load(f)
            ec = data.get("balanced", {}).get("selected_config", {})
            if ec and "move_cost" in ec and "eat_gain" in ec and "init_food" in ec:
                return {
                    "perception_radius": float(ec.get("perception_radius", DEFAULT_PERCEPTION_RADIUS)),
                    "hunger_rate":       float(ec.get("hunger_rate", 1.0 / 35.0)),
                    "move_cost":         float(ec["move_cost"]),
                    "eat_gain":          float(ec["eat_gain"]),
                    "init_food":         int(ec["init_food"]),
                    "rest_recovery":     float(ec.get("rest_recovery", 0.005)),
                }
        except Exception:
            continue
    # Fallback: provisional balanced values
    return {
        "perception_radius": DEFAULT_PERCEPTION_RADIUS,
        "hunger_rate":       1.0 / 35.0,
        "move_cost":         0.01,
        "eat_gain":          0.20,
        "init_food":         40,
        "rest_recovery":     0.005,
    }


PHASE2_ANCHOR = _load_phase2_balanced()

# Provisional baseline: Phase 2 anchor + unbiased genome
BALANCED_BASELINE = {
    **PHASE2_ANCHOR,
    **BASELINE_GENOME_WEIGHTS,
}


# ─────────────────────────────────────────────────────────────────────────────
# OVAT sensitivity sweep sets
# Same parameter axes as Phase 2; init_food range extended upward because
# 15 children add substantial indirect resource pressure on mothers.
# ─────────────────────────────────────────────────────────────────────────────
SENSITIVITY_SWEEPS = {
    "A": {
        "label":  "init_food",
        "key":    "init_food",
        "values": [40, 100, 200, 400, 700, 1000, 1500],
    },
    "B": {
        "label":  "eat_gain",
        "key":    "eat_gain",
        "values": [0.10, 0.20, 0.30, 0.50, 0.70],
    },
    "C": {
        "label":  "move_cost",
        "key":    "move_cost",
        "values": [0.005, 0.01, 0.02, 0.05, 0.10],
    },
}

SENSITIVITY_SUBPLOT_CONFIG = [
    ("A", "init_food",  "Initial Food Count",        "#D08770"),
    ("B", "eat_gain",   "Eat Gain (energy per food)", "#8FBCBB"),
    ("C", "move_cost",  "Move Cost (per step)",       "#5E81AC"),
]

HIDE_BASELINE_FOR = {"move_cost", "eat_gain", "init_food", "rest_recovery"}


# ─────────────────────────────────────────────────────────────────────────────
# Multi-parameter validation grid
# ─────────────────────────────────────────────────────────────────────────────
SWEEP_GRID = {
    "hunger_rate":   [1.0 / 35.0],
    "init_food":     [40, 100, 200, 400, 700, 1000],
    "eat_gain":      [0.10, 0.20, 0.30, 0.50, 0.70],
    "move_cost":     [0.005, 0.01, 0.02, 0.05, 0.10],
    "rest_recovery": [0.005],
}


# ─────────────────────────────────────────────────────────────────────────────
# Regime selection targets
# ─────────────────────────────────────────────────────────────────────────────

# Mother criteria: identical to Phase 2
SELECTION_TARGETS = {
    "harsh": {
        "min_survival_rate":    0.10,
        "max_survival_rate":    0.45,
        "target_survival_rate": 0.25,
        "energy_low":           0.00,
        "energy_high":          0.70,
        "target_energy":        0.20,
        "max_tail_sd":          0.25,
    },
    "balanced": {
        "min_survival_rate":    0.50,
        "max_survival_rate":    0.75,
        "target_survival_rate": 0.625,
        "energy_low":           0.05,
        "energy_high":          0.80,
        "target_energy":        0.35,
        "max_tail_sd":          0.25,
    },
    "easy": {
        "min_survival_rate":    0.80,
        "target_survival_rate": 0.90,
        "min_energy":           0.10,
        "target_energy":        0.50,
        "max_tail_sd":          0.25,
    },
}

# Child criteria: Option C (dual metric — C_matr + child longevity)
# Applied as secondary gate after the mother gate passes.
# HARSH: no child constraint (children rarely survive under harsh pressure; expected).
# BALANCED: at least some child survival + meaningful longevity.
# EASY: meaningful maturation rate + children close to reaching maturity.
CHILD_SELECTION_TARGETS = {
    "harsh":    None,
    "balanced": {
        "min_c_matr":         0.0,    # strictly > 0 (any maturation counts)
        "min_child_death_mu": 50.0,   # children live ≥ 50 ticks (= 10 days) on average
    },
    "easy": {
        "min_c_matr":         0.10,   # ≥ 10% maturation rate
        "min_child_death_mu": 120.0,  # children live ≥ 120 ticks (= 24 days; 60% of maturity_age)
    },
}


# ─────────────────────────────────────────────────────────────────────────────
# Config factory
# ─────────────────────────────────────────────────────────────────────────────

def make_config(params: dict, duration: int):
    """Build a Phase 3 Config from a params dict (ecological + genome parameters)."""
    from config import Config
    cfg = Config()
    cfg.max_ticks      = duration
    cfg.initial_energy = INITIAL_ENERGY

    # Ecological parameters
    _pr = int(params.get("perception_radius", DEFAULT_PERCEPTION_RADIUS))
    cfg.perception_radius      = _pr
    cfg.food_perception_radius = _pr
    cfg.hunger_rate            = params.get("hunger_rate", 1.0 / 35.0)
    cfg.move_cost              = float(params["move_cost"])
    cfg.eat_gain               = float(params["eat_gain"])
    cfg.init_food              = int(params["init_food"])
    cfg.rest_recovery          = float(params.get("rest_recovery", 0.005))
    cfg.fatigue_rate           = float(params.get("fatigue_rate", 0.01))

    # Genome weights
    cfg.care_weight   = float(params.get("care_weight",   BASELINE_GENOME_WEIGHTS["care_weight"]))
    cfg.forage_weight = float(params.get("forage_weight", BASELINE_GENOME_WEIGHTS["forage_weight"]))
    cfg.self_weight   = float(params.get("self_weight",   BASELINE_GENOME_WEIGHTS["self_weight"]))

    # Phase 3 locked flags
    for k, v in PHASE3_FLAGS.items():
        setattr(cfg, k, v)

    return cfg


def _expand_grid(grid: dict, name: str = "candidate") -> list:
    """Return a flat list of parameter dicts from a compact grid spec."""
    full_grid = {
        "perception_radius": [DEFAULT_PERCEPTION_RADIUS],
        **grid,
        **{k: [v] for k, v in BASELINE_GENOME_WEIGHTS.items()},
    }
    keys = list(full_grid.keys())
    configs = []
    for values in product(*[full_grid[k] for k in keys]):
        p = dict(zip(keys, values))
        p["name"] = name
        configs.append(p)
    return configs


def candidate_configs() -> list:
    """Generate the full Phase 3 validation grid (init_food × eat_gain × move_cost)."""
    return _expand_grid(SWEEP_GRID, name="candidate")
