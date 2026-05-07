from dataclasses import dataclass

@dataclass
class Config:
    # World — 50×50 gives proper spatial separation (Change A)
    width: int = 50
    height: int = 50

    # Population
    init_mothers: int = 12
    init_food: int = 45
    max_population: int = 100

    # Perception
    perception_radius: int = 8
    # food_perception_radius: sensory range for food detection only.
    # Separate from perception_radius so child cry (acoustic, global) and
    # food odour (chemical, short-range) use independent radii.
    # Smaller value → lower forage_cue → CARE can win the softmax earlier.
    food_perception_radius: int = 15

    # Energy — derived from starvation constraints (Change J)
    # initial_energy=1.0: full tank at birth
    # hunger_rate=1/35: adult starves in 35 ticks = 7 days (5 ticks/day convention)
    initial_energy: float = 1.0
    hunger_rate: float = 1 / 35
    move_cost: float = 0.005
    feed_cost: float = 0.03
    eat_gain: float = 0.25
    rest_recovery: float = 0.03

    # Reproduction — sigmoid midpoint at 0.85 (Change E)
    reproduction_threshold: float = 0.85
    reproduction_cost: float = 0.35
    reproduction_cooldown: int = 80

    # Child — time convention 5 ticks=1 day (Change I)
    # maturity_age=200 ticks = 40 days; mother_max_age=400 ticks = 80 days
    maturity_age: int = 200
    starvation_threshold: float = 1.0

    # Mother lifetime cap (Change I).
    # None = disabled; set to integer to enforce age-based death.
    mother_max_age: int | None = 400

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

    # Softmax / mutation hyperparameters — now Config-visible (Change G)
    softmax_tau: float = 0.1
    mutation_rate: float = 0.1
    mutation_sigma: float = 0.05

    # Warm behavior — spatial thermoregulation (Change H)
    # Within warmth_radius cells, maternal proximity reduces infant hunger_rate.
    # hunger_rate *= (1 - warmth_factor * warmth_proximity)
    # warmth_factor locked at 0.0 for Phase 3/4 — reserved for Phase 5+ spatial ecology.
    warmth_radius: int = 3
    warmth_factor: float = 0.0

    # Phase 5 — Ecological Emergence
    # infant_starvation_multiplier=2.33 = 35/15: infant starves in 15 ticks (Change J)
    # B becomes existential (alive/dead) — without care, infant cannot reach maturity.
    infant_starvation_multiplier: float = 2.33
    # birth_scatter_radius: Chebyshev radius searched for a free cell at birth.
    #   Tighter radius keeps kin spatially clustered (natal philopatry).
    #   Phase 5 sets this to 2; default 8 ~ random placement (current Phase 3/4 behaviour).
    birth_scatter_radius: int = 8

    # Phase 5b — Food Ecology Calibration
    # food_replace_on_pick: spawn 1 food unit every time a mother picks one.
    #   True (default) = 1:1 replacement — food count stays near init_food.
    #   This is the universal rule across all phases, matching Phase 2 SurvivalSimulation.
    food_replace_on_pick: bool = True
    # food_replenish_amount: food units spawned per threshold-burst replenishment event.
    food_replenish_amount: int = 5
    # food_replenish_threshold_ratio: burst fires when food_count < init_food * ratio.
    #   0.0 disables burst; 1:1 replacement (above) is the primary mechanism.
    food_replenish_threshold_ratio: float = 0.0

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

    # Birth cry — neonatal acoustic distress floor
    # For the first birth_cry_duration ticks of a child's life, distress is floored
    # at birth_cry_floor regardless of hunger/separation state.
    # 0 / 0.0 = disabled — all prior phases unaffected.
    # Biological basis: mammalian neonates emit high-intensity cries at birth to signal
    # their existence before hunger has time to accumulate. The mother's response remains
    # stochastic (softmax-governed) — this is a signal, not a forced outcome.
    birth_cry_duration: int = 0
    birth_cry_floor: float = 0.0

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


# ── Visual grid world presets (main.py) ───────────────────────────────────────
# Edit these to change what main.py renders — do not touch main.py itself.

VISUAL_SURVIVAL_CONFIG = Config(
    width=50, height=50,
    init_mothers=15,
    init_food=120,
    initial_energy=1.0,
    hunger_rate=1 / 35,
    move_cost=0.01,
    eat_gain=0.5,
    max_ticks=400,
    seed=42,
)

VISUAL_MATERNAL_CONFIG = Config(
    seed=42,
)