from dataclasses import dataclass

@dataclass
class Config:
    # World
    width: int = 30
    height: int = 30
    
    # Population
    init_mothers: int = 10
    init_food: int = 30
    max_population: int = 100
    
    # Perception
    perception_radius: int = 6
    
    # Energy
    initial_energy: float = 1.0
    hunger_rate: float = 0.02
    move_cost: float = 0.01
    feed_cost: float = 0.03
    eat_gain: float = 0.20
    rest_recovery: float = 0.05
    
    # Reproduction
    reproduction_threshold: float = 0.8
    reproduction_cost: float = 0.3
    reproduction_cooldown: int = 50
    
    # Child
    maturity_age: int = 100
    starvation_threshold: float = 1.0
    
    # Plasticity
    plastic_gain: float = 0.1
    
    # Simulation
    max_ticks: int = 5000
    seed: int = 42