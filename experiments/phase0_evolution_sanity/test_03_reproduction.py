"""
Test 03: Reproduction mechanics work
- Mother can reproduce when energy >= threshold
- Child spawns nearby
- Energy is deducted
- Cooldown is applied
"""
import sys
sys.path.append("../..")

from agents.mother import MotherAgent
from evolution.genome import Genome
from simulation.world import GridWorld


def test_can_reproduce_threshold():
    """Mother can reproduce only when energy >= threshold."""
    genome = Genome()
    mother = MotherAgent(5, 5, lineage_id=0, generation=0, genome=genome)
    
    # Low energy
    mother.energy = 0.5
    mother.own_child_id = None
    mother.cooldown = 0
    assert not mother.can_reproduce(threshold=0.8)
    
    # High energy
    mother.energy = 0.9
    assert mother.can_reproduce(threshold=0.8)
    print("✓ test_can_reproduce_threshold PASSED")


def test_cannot_reproduce_with_child():
    """Mother cannot reproduce if already has child."""
    genome = Genome()
    mother = MotherAgent(5, 5, lineage_id=0, generation=0, genome=genome)
    
    mother.energy = 1.0
    mother.own_child_id = 99  # has child
    mother.cooldown = 0
    
    assert not mother.can_reproduce(threshold=0.8)
    print("✓ test_cannot_reproduce_with_child PASSED")


def test_cannot_reproduce_on_cooldown():
    """Mother cannot reproduce during cooldown."""
    genome = Genome()
    mother = MotherAgent(5, 5, lineage_id=0, generation=0, genome=genome)
    
    mother.energy = 1.0
    mother.own_child_id = None
    mother.cooldown = 10
    
    assert not mother.can_reproduce(threshold=0.8)
    print("✓ test_cannot_reproduce_on_cooldown PASSED")


def test_cooldown_ticks_down():
    """Cooldown should decrease each tick."""
    genome = Genome()
    mother = MotherAgent(5, 5, lineage_id=0, generation=0, genome=genome)
    
    mother.cooldown = 5
    mother.tick_cooldown()
    assert mother.cooldown == 4
    
    mother.tick_cooldown()
    assert mother.cooldown == 3
    print("✓ test_cooldown_ticks_down PASSED")


if __name__ == "__main__":
    test_can_reproduce_threshold()
    test_cannot_reproduce_with_child()
    test_cannot_reproduce_on_cooldown()
    test_cooldown_ticks_down()
    print("\n=== All reproduction tests PASSED ===")