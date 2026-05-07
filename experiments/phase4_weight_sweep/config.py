# experiments/phase4_weight_sweep/config.py
"""
Phase 4 — Motivation Weight Sweep

Research question:
    "What is the minimum care_weight fraction that enables child maturation?"

Ecological baseline locked from Phase 3b BEST_ECOLOGICAL:
    ISM=1.2, eat_gain=0.70, init_food=600, move_cost=0.005, rest_recovery=0.005

Swept axes (simplex fractions; care + forage + self = 1.0):
    care_weight   — fraction of motivation budget allocated to CARE domain
    forage_weight — OVAT/grid secondary axis (fraction)
    self_weight   — derived as 1 − care − forage, or OVAT tertiary

Fixed (all Phase 4 runs):
    perception_radius=8, food_perception_radius=8
    hunger_rate=1/35, warmth_factor=0.0
    maturity_age=200, max_ticks=400, init_mothers=15

Scientific rationale:
    compute_motivation_scores() normalises by weight sum, so stored fractions are
    the actual effective weights — axes are scale-invariant and bounded in [0, 1].
    With care_weight=0.50 (50% of budget), CARE wins softmax when distress > 0.50.
    feeds_needed at ISM=1.2, eat_gain=0.70 ≈ 8.4 → must feed ~9× in 200 ticks.
"""
import json
from pathlib import Path
from itertools import product

# ── Population / timing ───────────────────────────────────────────────────────
INIT_MOTHERS = 15
MAX_TICKS    = 400
MATURITY_AGE = 200

# ── Phase 3b BEST_ECOLOGICAL — loaded from Phase 3b output JSON ───────────────
# Fallback values used only if Phase 3b has not yet produced its output file.
_PHASE3B_JSON = (
    Path(__file__).resolve().parent.parent.parent
    / "outputs" / "phase3_survival_full" / "phase3b_calibration" / "selected_ecologies.json"
)

_FALLBACK_ECO = {
    "infant_starvation_multiplier": 1.2,
    "eat_gain":                     0.70,
    "init_food":                    600,
    "move_cost":                    0.005,
    "rest_recovery":                0.005,
}


def _load_best_eco() -> dict:
    if _PHASE3B_JSON.exists():
        with open(_PHASE3B_JSON, encoding="utf-8") as f:
            data = json.load(f)
        eco = data.get("regimes", {}).get("BEST_ECOLOGICAL")
        if eco:
            return {
                "infant_starvation_multiplier": float(eco["infant_starvation_multiplier"]),
                "eat_gain":                     float(eco["eat_gain"]),
                "init_food":                    int(eco["init_food"]),
                "move_cost":                    float(eco["move_cost"]),
                "rest_recovery":                float(eco["rest_recovery"]),
            }
    return dict(_FALLBACK_ECO)


BEST_ECO = _load_best_eco()

# ── Seeds ─────────────────────────────────────────────────────────────────────
THRESHOLD_SEEDS  = list(range(42, 47))   # 5 seeds — care_weight threshold scan
OVAT_SEEDS       = list(range(42, 47))   # 5 seeds per OVAT value
GRID_SEEDS       = list(range(42, 47))   # 5 seeds per grid combo
VALIDATION_SEEDS = list(range(42, 52))   # 10 seeds — final validation

# ── Primary care_weight threshold scan ────────────────────────────────────────
# Independent weights: forage=self=0.5 fixed; care varies across [0,1].
CARE_WEIGHT_VALUES = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]

# ── OVAT baseline ─────────────────────────────────────────────────────────────
# Equal independent weights — each drive at midpoint of [0,1].
OVAT_BASELINE = {
    "care_weight":   0.5,
    "forage_weight": 0.5,
    "self_weight":   0.5,
}

# ── OVAT sweep sets ────────────────────────────────────────────────────────────
OVAT_SWEEPS = {
    "A": {
        "label":  "care_weight",
        "key":    "care_weight",
        "values": [0.1, 0.2, 0.3, 0.5, 0.7, 0.9, 1.0],
    },
    "B": {
        "label":  "forage_weight",
        "key":    "forage_weight",
        "values": [0.1, 0.2, 0.3, 0.5, 0.7, 0.9, 1.0],
    },
    "C": {
        "label":  "self_weight",
        "key":    "self_weight",
        "values": [0.1, 0.2, 0.3, 0.5, 0.7, 0.9, 1.0],
    },
}

# ── Full 2D grid: care_weight × forage_weight (self_weight=0.5 fixed) ─────────
# 5 × 5 = 25 combos × 5 seeds = 125 runs.
SWEEP_GRID = {
    "care_weight":   [0.2, 0.4, 0.6, 0.8, 1.0],
    "forage_weight": [0.2, 0.4, 0.6, 0.8, 1.0],
}

# ── Regime selection thresholds ────────────────────────────────────────────────
VIABLE_MIN_C_MATR = 0.0    # any C_matr > 0 is viable
VIABLE_MIN_M_SURV = 0.10   # at least 10% mother survival

# ── Phase 4 locked simulation flags ───────────────────────────────────────────
PHASE4_FLAGS = {
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
    "warmth_factor":                0.0,
    # Approach A: own-child exclusivity enabled via simulation._execute_action logic.
    # Approach E: starvation floor — mother self-preserves below 0.3 energy.
    "care_energy_floor":            0.3,
    **BEST_ECO,
}


def make_config(care_weight: float, forage_weight: float, self_weight: float, seed: int):
    """Build a Config for one Phase 4 simulation run."""
    from config import Config
    return Config(
        seed=seed,
        care_weight=care_weight,
        forage_weight=forage_weight,
        self_weight=self_weight,
        **{k: v for k, v in PHASE4_FLAGS.items()},
    )


def expand_threshold() -> list[dict]:
    """care_weight threshold scan: forage=self=0.5 fixed (independent weights)."""
    return [
        {"care_weight": cw, "forage_weight": 0.5, "self_weight": 0.5}
        for cw in CARE_WEIGHT_VALUES
    ]


def expand_ovat(set_key: str) -> list[dict]:
    """OVAT: vary one weight, fix others at OVAT_BASELINE (independent weights)."""
    sw     = OVAT_SWEEPS[set_key]
    combos = []
    for v in sw["values"]:
        params = dict(OVAT_BASELINE)
        params[sw["key"]] = v
        combos.append(params)
    return combos


def expand_grid() -> list[dict]:
    """care × forage grid; self_weight=0.5 fixed (independent weights)."""
    combos = []
    for cw in SWEEP_GRID["care_weight"]:
        for fw in SWEEP_GRID["forage_weight"]:
            combos.append({
                "care_weight":   cw,
                "forage_weight": fw,
                "self_weight":   0.5,
            })
    return combos


def feeds_needed(ism: float, eat_gain: float) -> float:
    """Theoretical minimum feeds for child survival (hunger_rate = 1/35)."""
    return max(0.0, (MATURITY_AGE * (1 / 35) * ism - 1.0) / eat_gain)
