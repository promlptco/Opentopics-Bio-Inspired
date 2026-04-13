# main.py
import sys
import os

# Add project root to path
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJECT_ROOT)

from config import Config

# === MODE SELECTION ===
MODE = "survival"  # "survival" or "maternal"
USE_VISUAL = True

if __name__ == "__main__":
    config = Config()
    config.seed = 42
    
    if MODE == "survival":
        # Import survival simulation
        from experiments.p2_survival_minimal.run import SurvivalSimulation
        
        config.width = 30
        config.height = 30
        config.init_mothers = 12
        config.init_food = 45
        config.initial_energy = 0.85
        config.hunger_rate = 0.008
        config.move_cost = 0.005
        config.eat_gain = 0.25
        config.max_ticks = 300
        
        sim = SurvivalSimulation(config)
        sim.initialize()
        
        if USE_VISUAL:
            from ui.renderer_survival import SurvivalRenderer
            renderer = SurvivalRenderer(config.width, config.height, cell_size=20)
            
            running = True
            while running and sim.tick < config.max_ticks:
                running = renderer.handle_events()
                sim.step()
                sim.tick += 1
                renderer.render(sim.world, sim.mothers, sim.tick)
                renderer.tick(fps=15)
            
            renderer.close()
        else:
            while sim.tick < config.max_ticks:
                sim.step()
                sim.tick += 1
        
        results = sim.get_results()
        print(f"Surviving: {results['surviving_mothers']}")
        print(f"Food eaten: {results['total_food_eaten']}")
    
    else:  # maternal
        from simulation.simulation import Simulation
        
        sim = Simulation(config)
        
        if USE_VISUAL:
            from ui.renderer import Renderer
            renderer = Renderer(config.width, config.height, cell_size=20)
            sim.initialize()
            
            running = True
            while running and sim.tick < config.max_ticks:
                running = renderer.handle_events()
                sim.step()
                sim.tick += 1
                renderer.render(sim.world, sim.mothers, sim.children, sim.tick)
                renderer.tick(fps=10)
            
            renderer.close()
        else:
            sim.run()
        
        print(f"Surviving mothers: {len([m for m in sim.mothers if m.alive])}")
        print(f"Surviving children: {len([c for c in sim.children if c.alive])}")