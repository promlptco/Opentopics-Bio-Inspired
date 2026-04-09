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

    # Simulation
    max_ticks: int = 300
    seed: int = 42
    
    # Mode Flags
    children_enabled: bool = True
    care_enabled: bool = True
    plasticity_enabled: bool = True
    reproduction_enabled: bool = True
    mutation_enabled: bool = True