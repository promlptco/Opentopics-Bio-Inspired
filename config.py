from dataclasses import dataclass

@dataclass
class Config:
    # World
    width: int = 30
    height: int = 30

    # Population
    init_mothers: int = 12
    init_food: int = 45
    max_population: int = 100

    # Perception
    perception_radius: int = 8

    # Energy
    initial_energy: float = 0.85
    hunger_rate: float = 0.008
    move_cost: float = 0.005
    feed_cost: float = 0.03
    eat_gain: float = 0.25
    rest_recovery: float = 0.03

    # Reproduction
    reproduction_threshold: float = 0.95
    reproduction_cost: float = 0.35
    reproduction_cooldown: int = 80

    # Child
    maturity_age: int = 100
    starvation_threshold: float = 1.0

    # Mother lifetime cap (optional).
    # None = disabled; mothers die from energy depletion only (default, all phases safe).
    # Set to an integer to enforce age-based death on top of starvation.
    mother_max_age: int | None = None

    # Fatigue
    fatigue_rate: float = 0.01

    # Plasticity
    plastic_gain: float = 0.1
    # If True, plastic_update fires only on own-child care events (is_own_child=True).
    # This aligns the learning signal with inclusive fitness — proper Baldwin Effect test.
    # If False (default), fires on all care events (lineage-blind — null result by design).
    plasticity_kin_conditional: bool = False

    # Simulation
    max_ticks: int = 300
    seed: int = 42
    
    # Mode Flags
    children_enabled: bool = True
    care_enabled: bool = True
    plasticity_enabled: bool = True
    reproduction_enabled: bool = True
    mutation_enabled: bool = True

    # Phase 5 — Ecological Emergence
    # infant_starvation_multiplier: infants hunger this many times faster than adults
    #   during [0, maturity_age]. B becomes existential (alive/dead) instead of marginal.
    #   Phase 5 sets this to 3.0; default 1.0 = Phase 3/4 behaviour.
    infant_starvation_multiplier: float = 1.0
    # birth_scatter_radius: Chebyshev radius searched for a free cell at birth.
    #   Tighter radius keeps kin spatially clustered (natal philopatry).
    #   Phase 5 sets this to 2; default 8 ~ random placement (current Phase 3/4 behaviour).
    birth_scatter_radius: int = 8

    # Phase 5b — Food Ecology Calibration
    # food_replenish_amount: food units spawned per replenishment event.
    #   Default 5 matches the value hardcoded in all prior phases.
    food_replenish_amount: int = 5
    # food_replenish_threshold_ratio: replenish when food_count < init_food * ratio.
    #   Default 0.5 matches the init_food // 2 threshold used in all prior phases.
    food_replenish_threshold_ratio: float = 0.5

    # Phase 5d — Hybrid Food Replenishment
    # continuous_food_rate: food units added per tick unconditionally (fractional
    #   accumulator — fractions carry over to the next tick).
    #   0.0 = disabled (default). All prior phases unaffected.
    continuous_food_rate: float = 0.0
    # continuous_food_max: cap on food_count when continuous trickle is active.
    #   0 = no cap. Phase 5d sets this to 200 to prevent unbounded accumulation.
    continuous_food_max: int = 0

    # Genome weights (used by Phase 2+ survival experiments)
    # care_weight=0.0 disables CARE motivation; FORAGE/SELF are neutral at 1.0.
    forage_weight: float = 1.0
    self_weight: float = 1.0
    care_weight: float = 0.0

    # Phase 6d — Baldwin Instinct Assimilation
    # plasticity_energy_cost: fixed energy deducted per plastic_update call (in addition
    #   to the variable learning_cost * |delta| already applied). Default 0.0 leaves all
    #   prior experiments unaffected. Phase 6d may set this to a small positive value (e.g.
    #   0.005) to make plasticity metabolically costly, strengthening the assimilation test.
    plasticity_energy_cost: float = 0.0

    # Phase 8 — Genuine Baldwin Effect controls
    # plasticity_noise_sigma: std-dev of multiplicative Gaussian noise added to the
    #   reward signal in plastic_update(). 0.0 = deterministic (Phase 7 behaviour).
    #   Higher values make learning unreliable, creating a fitness advantage for
    #   genetic instinct over learned behaviour (Hinton & Nowlan 1987 mechanism).
    plasticity_noise_sigma: float = 0.0
    # lock_learning_rate: if True, learning_rate gene is not mutated during reproduction.
    #   Closes the "become a better learner" escape route so selection can only act on
    #   the genetic care_weight floor. 0.0 = evolvable (all prior phases unaffected).
    lock_learning_rate: bool = False