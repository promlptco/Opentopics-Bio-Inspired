from config import Config
from simulation.simulation import Simulation

USE_VISUAL = True  # Change to False to disable visualization
if __name__ == "__main__":
    config = Config()
    sim = Simulation(config)
    
    if USE_VISUAL:
        from ui.renderer import Renderer
        renderer = Renderer(config.width, config.height, cell_size=30)
        sim.initialize()
        
        running = True
        while running and sim.tick < config.max_ticks:
            running = renderer.handle_events()
            sim.step()
            sim.tick += 1
            renderer.render(sim.world, sim.mothers, sim.children, sim.tick)
            renderer.tick(fps=10)
        
        renderer.close()
        sim._export_logs()
    else:
        sim.run()
    
    print(f"Simulation finished at tick {sim.tick}")
    print(f"Surviving mothers: {len(sim.mothers)}")
    print(f"Surviving children: {len(sim.children)}")