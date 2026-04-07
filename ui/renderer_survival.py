# ui/renderer_survival.py
"""Renderer for survival-only mode (no children)."""
import pygame
from simulation.world import GridWorld
from agents.mother import MotherAgent

# Colors
BG_COLOR = (245, 245, 245)
GRID_COLOR = (200, 200, 200)
OUTLINE_COLOR = (50, 50, 50)
FOOD_COLOR = (100, 180, 100)
MOTHER_COLOR = (70, 130, 180)


def intensity_to_color(value: float, low_color: tuple, high_color: tuple) -> tuple:
    value = max(0.0, min(1.0, value))
    r = int(low_color[0] + (high_color[0] - low_color[0]) * value)
    g = int(low_color[1] + (high_color[1] - low_color[1]) * value)
    b = int(low_color[2] + (high_color[2] - low_color[2]) * value)
    return (r, g, b)


class SurvivalRenderer:
    def __init__(self, width: int, height: int, cell_size: int = 20):
        pygame.init()
        self.cell_size = cell_size
        self.grid_w = width
        self.grid_h = height
        self.screen_width = width * cell_size
        self.screen_height = height * cell_size + 40
        self.screen = pygame.display.set_mode((self.screen_width, self.screen_height))
        pygame.display.set_caption("Survival Check")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont(None, 18)
    
    def handle_events(self) -> bool:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    return False
        return True
    
    def render(self, world: GridWorld, mothers: list[MotherAgent], tick: int) -> None:
        # Background
        self.screen.fill(BG_COLOR)
        
        # Grid
        for x in range(self.grid_w + 1):
            pygame.draw.line(self.screen, GRID_COLOR,
                (x * self.cell_size, 0),
                (x * self.cell_size, self.grid_h * self.cell_size))
        for y in range(self.grid_h + 1):
            pygame.draw.line(self.screen, GRID_COLOR,
                (0, y * self.cell_size),
                (self.grid_w * self.cell_size, y * self.cell_size))
        
        # Food
        for fx, fy in world.food_positions:
            cx = fx * self.cell_size + self.cell_size // 2
            cy = fy * self.cell_size + self.cell_size // 2
            size = self.cell_size // 3
            rect = pygame.Rect(cx - size//2, cy - size//2, size, size)
            pygame.draw.rect(self.screen, FOOD_COLOR, rect)
        
        # Mothers
        for mother in mothers:
            if not mother.alive:
                continue
            mx = mother.x * self.cell_size + self.cell_size // 2
            my = mother.y * self.cell_size + self.cell_size // 2
            radius = self.cell_size // 3
            
            # Color by energy
            color = intensity_to_color(mother.energy, (180, 80, 80), MOTHER_COLOR)
            pygame.draw.circle(self.screen, color, (mx, my), radius)
            pygame.draw.circle(self.screen, OUTLINE_COLOR, (mx, my), radius, width=2)
            
            # Food indicator
            if mother.held_food > 0:
                pygame.draw.circle(self.screen, (230, 140, 40), (mx, my), radius + 4, width=2)
        
        # HUD
        alive = sum(1 for m in mothers if m.alive)
        food_count = len(world.food_positions)
        avg_energy = sum(m.energy for m in mothers if m.alive) / alive if alive > 0 else 0
        
        hud_y = self.grid_h * self.cell_size + 5
        text = f"Tick: {tick} | Alive: {alive} | Food: {food_count} | Avg Energy: {avg_energy:.2f}"
        text_surface = self.font.render(text, True, (50, 50, 50))
        self.screen.blit(text_surface, (10, hud_y))
        
        pygame.display.flip()
    
    def tick(self, fps: int = 15) -> None:
        self.clock.tick(fps)
    
    def close(self) -> None:
        pygame.quit()