# experiments/phase04_care_erosion/watch.py
"""
Live visualisation of Baseline-C0 (balanced genome).
Re-runs the same seed so the trajectory is identical to the logged run.

Controls:
  ESC / close window  — quit
  SPACE               — pause / unpause
  UP / DOWN arrow     — speed up / slow down
"""
import sys
import os
import random as _random

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, PROJECT_ROOT)

from config import Config
from simulation.simulation import Simulation
from evolution.genome import Genome
from utils.experiment import set_seed
from ui.renderer import Renderer

# ── config mirrors run.py baseline_c0 exactly (Can Change) ──────────────────────────────
SEED         = 42
CARE_WEIGHT  = 0.7
FORAGE_WEIGHT = 0.85
SELF_WEIGHT  = 0.55
MAX_TICKS    = 5000
INIT_FPS     = 15   # starting speed; UP/DOWN to change


def main():
    config = Config()
    config.seed          = SEED
    config.init_mothers  = 12
    config.init_food     = 45
    config.max_ticks     = MAX_TICKS

    config.children_enabled     = True
    config.care_enabled         = True
    config.plasticity_enabled   = False
    config.reproduction_enabled = True
    config.mutation_enabled     = False

    set_seed(config.seed)

    genomes = [
        Genome(care_weight=CARE_WEIGHT, forage_weight=FORAGE_WEIGHT, self_weight=SELF_WEIGHT)
        for _ in range(config.init_mothers)
    ]

    sim = Simulation(config)
    sim.initialize(genomes)

    renderer = Renderer(config.width, config.height, cell_size=22)

    fps     = INIT_FPS
    paused  = False

    while sim.tick < config.max_ticks:
        # ── events ──
        for event in __import__("pygame").event.get():
            import pygame
            if event.type == pygame.QUIT:
                renderer.close(); return
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    renderer.close(); return
                if event.key == pygame.K_SPACE:
                    paused = not paused
                if event.key == pygame.K_UP:
                    fps = min(fps + 5, 120)
                if event.key == pygame.K_DOWN:
                    fps = max(fps - 5, 1)

        if not paused:
            sim.step()
            sim.tick += 1

        renderer.render(sim.world, sim.mothers, sim.children, sim.tick)
        renderer.tick(fps)

    renderer.close()
    print(f"Simulation finished at tick {sim.tick}.")


if __name__ == "__main__":
    main()
