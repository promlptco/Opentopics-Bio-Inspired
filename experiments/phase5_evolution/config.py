# experiments/phase5_evolution/config.py
"""
Phase 5 — Block 2 Baldwin Emergence.

Research question:
    "Does ecological pressure cause mean_genome_care_weight to rise above the
     neutral 1/3 baseline through genetic selection, starting from an equal
     (care = forage = self = 1/3) genome?"

Ecology: Phase 3b BEST_ECOLOGICAL (ISM=1.2, eat_gain=0.70, init_food=600,
         move_cost=0.005).  Phase 4 fixes carried forward:
           Approach A — own-child exclusivity (baked into simulation)
           Approach E — starvation floor care_energy_floor=0.3

Genome: normalized weights (care + forage + self = 1.0 after every mutation).
        Starting point: care = forage = self = 1/3.
        Success criterion: mean_genome_care_weight > 1/3 in mut_on_plast_off.

Four conditions (2×2 mutation × plasticity):
    mut_on_plast_off  — genetic selection only          (PRIMARY result)
    mut_on_plast_on   — Baldwin scaffold + evolution
    mut_off_plast_on  — phenotypic adjustment only
    mut_off_plast_off — fixed genome null baseline

Mechanisms: food_entropy_alpha=0.0, cry_decay_radius=0.0,
            temperature_sensitivity=0.0  (Block 1/2 baseline — all disabled).
"""

# ─────────────────────────────────────────────────────────────────────────────
# Ecology — BEST_ECOLOGICAL from Phase 3b
# ─────────────────────────────────────────────────────────────────────────────
BEST_ECOLOGICAL = {
    "infant_starvation_multiplier": 1.2,
    "eat_gain":    0.70,
    "init_food":   600,
    "move_cost":   0.005,
    "rest_recovery": 0.005,
    "hunger_rate": 1.0 / 35.0,
    "food_perception_radius": 8,
    "perception_radius": 8,
}

# ─────────────────────────────────────────────────────────────────────────────
# Starting genome — normalized equal allocation
# ─────────────────────────────────────────────────────────────────────────────
INIT_GENOME_CARE   = 1 / 3
INIT_GENOME_FORAGE = 1 / 3
INIT_GENOME_SELF   = 1 / 3

# ─────────────────────────────────────────────────────────────────────────────
# Phase 4 fixes
# ─────────────────────────────────────────────────────────────────────────────
CARE_ENERGY_FLOOR = 0.3   # Approach E starvation floor

# ─────────────────────────────────────────────────────────────────────────────
# Population & timing
# ─────────────────────────────────────────────────────────────────────────────
INIT_MOTHERS  = 15
MATURITY_AGE  = 200        # ticks for child to reach maturity (5 ticks/day × 40 days)
MAX_TICKS     = 40_000     # ≈ 100–200 async generations
SAMPLE_WINDOW = 200        # ticks between genome snapshots

# ─────────────────────────────────────────────────────────────────────────────
# Evolution hyperparameters
# ─────────────────────────────────────────────────────────────────────────────
MUTATION_RATE  = 0.1
MUTATION_SIGMA = 0.05

# ─────────────────────────────────────────────────────────────────────────────
# Seeds
# ─────────────────────────────────────────────────────────────────────────────
SWEEP_SEEDS = list(range(42, 52))   # 10 seeds

# ─────────────────────────────────────────────────────────────────────────────
# Four conditions
# ─────────────────────────────────────────────────────────────────────────────
CONDITIONS = {
    "mut_on_plast_off":  {"mutation_enabled": True,  "plasticity_enabled": False},
    "mut_on_plast_on":   {"mutation_enabled": True,  "plasticity_enabled": True},
    "mut_off_plast_on":  {"mutation_enabled": False, "plasticity_enabled": True},
    "mut_off_plast_off": {"mutation_enabled": False, "plasticity_enabled": False},
}

# ─────────────────────────────────────────────────────────────────────────────
# Success criterion
# ─────────────────────────────────────────────────────────────────────────────
SUCCESS_CARE_THRESHOLD = 1 / 3   # mean_genome_care_weight must rise above this


# ─────────────────────────────────────────────────────────────────────────────
# Config factory
# ─────────────────────────────────────────────────────────────────────────────

def make_config(condition_name: str, seed: int):
    """Build a Phase 5 Config for the given condition and seed."""
    from config import Config
    condition = CONDITIONS[condition_name]
    cfg = Config()

    cfg.seed      = seed
    cfg.max_ticks = MAX_TICKS

    # Ecology
    eco = BEST_ECOLOGICAL
    cfg.infant_starvation_multiplier = float(eco["infant_starvation_multiplier"])
    cfg.eat_gain                     = float(eco["eat_gain"])
    cfg.init_food                    = int(eco["init_food"])
    cfg.move_cost                    = float(eco["move_cost"])
    cfg.rest_recovery                = float(eco["rest_recovery"])
    cfg.hunger_rate                  = float(eco["hunger_rate"])
    cfg.food_perception_radius       = int(eco["food_perception_radius"])
    cfg.perception_radius            = int(eco["perception_radius"])

    # Starting genome (equal allocation — only ratios matter in softmax)
    cfg.care_weight   = INIT_GENOME_CARE
    cfg.forage_weight = INIT_GENOME_FORAGE
    cfg.self_weight   = INIT_GENOME_SELF

    # Phase 4 fixes
    cfg.care_energy_floor = CARE_ENERGY_FLOOR

    # Population
    cfg.init_mothers  = INIT_MOTHERS
    cfg.maturity_age  = MATURITY_AGE
    cfg.mother_max_age = None   # natural starvation death; no age cap

    # Reproduction — allow multiple offspring per mother over her lifetime
    cfg.one_child_per_lifetime = False
    cfg.reproduction_cooldown  = 80   # ticks between births

    # Mode flags
    cfg.children_enabled     = True
    cfg.care_enabled         = True
    cfg.reproduction_enabled = True
    cfg.mutation_enabled     = condition["mutation_enabled"]
    cfg.plasticity_enabled   = condition["plasticity_enabled"]

    # Evolution hyperparameters
    cfg.mutation_rate  = MUTATION_RATE
    cfg.mutation_sigma = MUTATION_SIGMA

    # Food — 1:1 replacement (mechanisms disabled, Block 1/2 baseline)
    cfg.food_replace_on_pick  = True
    cfg.food_entropy_alpha    = 0.0

    # Three mechanisms disabled
    cfg.cry_decay_radius       = 0.0
    cfg.temperature_sensitivity = 0.0

    return cfg
