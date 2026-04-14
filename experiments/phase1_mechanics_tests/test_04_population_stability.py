"""
Test 04: Population stability
- No immediate extinction
- No immediate explosion
- Deterministic with seed
"""
import sys
import os
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, PROJECT_ROOT)

import random
from config import Config
from simulation.simulation import Simulation


def test_no_immediate_extinction():
    """Population should not die out in first 100 ticks."""
    config = Config()
    config.init_mothers = 10
    config.max_ticks = 100
    config.seed = 42
    
    sim = Simulation(config)
    sim.initialize()
    
    for _ in range(100):
        sim.step()
        sim.tick += 1
    
    alive = len([m for m in sim.mothers if m.alive])
    print(f"Alive after 100 ticks: {alive}")
    assert alive > 0, "Population should not extinct immediately"
    print("✓ test_no_immediate_extinction PASSED")


def test_no_immediate_explosion():
    """Population should not explode in first 100 ticks."""
    config = Config()
    config.init_mothers = 10
    config.max_population = 200
    config.max_ticks = 100
    config.seed = 42
    
    sim = Simulation(config)
    sim.initialize()
    
    for _ in range(100):
        sim.step()
        sim.tick += 1
    
    total = len(sim.mothers) + len(sim.children)
    print(f"Total population after 100 ticks: {total}")
    assert total < 200, "Population should not explode"
    print("✓ test_no_immediate_explosion PASSED")


def test_deterministic_with_seed():
    """Same seed should produce same result."""
    results = []
    
    for _ in range(2):
        config = Config()
        config.init_mothers = 5
        config.max_ticks = 50
        config.seed = 12345
        
        sim = Simulation(config)
        sim.initialize()
        
        for _ in range(50):
            sim.step()
            sim.tick += 1
        
        alive = len([m for m in sim.mothers if m.alive])
        results.append(alive)
    
    print(f"Run 1: {results[0]}, Run 2: {results[1]}")
    assert results[0] == results[1], "Same seed should give same result"
    print("✓ test_deterministic_with_seed PASSED")


def test_no_food_causes_extinction():
    """Without food, population should die."""
    config = Config()
    config.init_mothers = 5
    config.init_food = 0
    config.max_ticks = 200
    config.seed = 42
    
    sim = Simulation(config)
    sim.initialize()
    sim.world.food_positions.clear()  # ensure no food
    
    for _ in range(200):
        sim.step()
        sim.tick += 1
        # Don't spawn food
        sim.world.food_positions.clear()
    
    alive = len([m for m in sim.mothers if m.alive])
    print(f"Alive without food: {alive}")
    assert alive == 0, "Should extinct without food"
    print("✓ test_no_food_causes_extinction PASSED")


if __name__ == "__main__":
    test_no_immediate_extinction()
    test_no_immediate_explosion()
    test_deterministic_with_seed()
    test_no_food_causes_extinction()
    print("\n=== All population stability tests PASSED ===")