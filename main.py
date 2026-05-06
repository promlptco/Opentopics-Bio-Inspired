# main.py
import sys
import os
import argparse

# Add project root to path
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJECT_ROOT)

from config import Config

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["survival", "maternal"], default="survival",
                        help="survival = Phase 2 mothers-only grid world; maternal = full mother+child simulation")
    parser.add_argument("--no-visual", action="store_true", help="Run headless (no pygame window)")
    args = parser.parse_args()

    MODE = args.mode
    USE_VISUAL = not args.no_visual

    config = Config()
    config.seed = 42
    
    if MODE == "survival":
        # Import survival simulation
        from experiments.phase2_survival_minimal.new_run import SurvivalSimulation
        
        config.width = 50
        config.height = 50
        config.init_mothers = 15
        config.init_food = 120
        config.initial_energy = 1.0
        config.hunger_rate = 0.0286
        config.move_cost = 0.01
        config.eat_gain = 0.5
        config.max_ticks = 400
        
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
        
        alive = [m for m in sim.mothers if m.alive]
        print(f"Surviving: {len(alive)}")
        print(f"Food eaten: {sim.action_counts['EAT']}")
    
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