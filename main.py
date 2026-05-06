# main.py
import sys
import os
import argparse

# Add project root to path
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJECT_ROOT)

from config import VISUAL_SURVIVAL_CONFIG, VISUAL_MATERNAL_CONFIG
from ui.renderer_config import THEMES

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["survival", "maternal"], default="survival",
                        help="survival = Phase 2 mothers-only grid world; maternal = full mother+child simulation")
    parser.add_argument("--theme", choices=["light", "dark"], default="light",
                        help="light = white background; dark = dark background with neon gradient")
    parser.add_argument("--no-visual", action="store_true", help="Run headless (no pygame window)")
    args = parser.parse_args()

    MODE = args.mode
    USE_VISUAL = not args.no_visual
    THEME = THEMES[args.theme]

    if MODE == "survival":
        from experiments.phase2_survival_minimal.new_run import SurvivalSimulation
        config = VISUAL_SURVIVAL_CONFIG
        
        sim = SurvivalSimulation(config)
        sim.initialize()
        
        if USE_VISUAL:
            from ui.renderer_survival import SurvivalRenderer
            renderer = SurvivalRenderer(config.width, config.height, cell_size=20, theme=THEME)
            
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
        config = VISUAL_MATERNAL_CONFIG
        sim = Simulation(config)
        
        if USE_VISUAL:
            from ui.renderer import Renderer
            renderer = Renderer(config.width, config.height, cell_size=20, theme=THEME)
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