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

    # Phase 6d — Baldwin Instinct Assimilation
    # plasticity_energy_cost: fixed energy deducted per plastic_update call (in addition
    #   to the variable learning_cost * |delta| already applied). Default 0.0 leaves all
    #   prior experiments unaffected. Phase 6d may set this to a small positive value (e.g.
    #   0.005) to make plasticity metabolically costly, strengthening the assimilation test.
    plasticity_energy_cost: float = 0.0