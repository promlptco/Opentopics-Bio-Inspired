# ui/renderer_survival.py
"""Renderer for survival-only mode (no children). Theme-driven via RendererTheme."""
import pygame
from simulation.world import GridWorld
from agents.mother import MotherAgent
from ui.renderer_config import RendererTheme, LIGHT_THEME, lerp_color

_MOTIVATION_RING_KEYS = ("ring_forage", "ring_self", "ring_care")
_MOTIVATION_MAP = {"FORAGE": "ring_forage", "SELF": "ring_self", "CARE": "ring_care"}


class SurvivalRenderer:
    def __init__(self, width: int, height: int, cell_size: int = 20, theme: RendererTheme = LIGHT_THEME):
        pygame.init()
        self.cell_size = cell_size
        self.grid_w = width
        self.grid_h = height
        self.theme = theme
        self.screen_width = width * cell_size
        self.screen_height = height * cell_size + 40
        self.screen = pygame.display.set_mode((self.screen_width, self.screen_height))
        pygame.display.set_caption("Survival Simulation")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont(None, 18)

    def handle_events(self) -> bool:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                return False
        return True

    def render(self, world: GridWorld, mothers: list[MotherAgent], tick: int) -> None:
        t = self.theme
        cs = self.cell_size

        self.screen.fill(t.bg_color)

        # Grid lines
        for x in range(self.grid_w + 1):
            pygame.draw.line(self.screen, t.grid_color,
                             (x * cs, 0), (x * cs, self.grid_h * cs))
        for y in range(self.grid_h + 1):
            pygame.draw.line(self.screen, t.grid_color,
                             (0, y * cs), (self.grid_w * cs, y * cs))

        # Food — small circle
        for fx, fy in world.food_positions:
            pygame.draw.circle(self.screen, t.food_color,
                               (fx * cs + cs // 2, fy * cs + cs // 2), cs // 5)

        # Mothers
        for mother in mothers:
            if not mother.alive:
                continue
            mx = mother.x * cs + cs // 2
            my = mother.y * cs + cs // 2
            radius = cs // 3

            # Motivation ring (drawn first so body sits on top)
            ring_key = _MOTIVATION_MAP.get(mother.last_motivation)
            if ring_key:
                pygame.draw.circle(self.screen, getattr(t, ring_key),
                                   (mx, my), radius + 5, width=2)

            # Body — neon gradient by energy
            body_color = lerp_color(mother.energy, t.mother_color_low, t.mother_color_high)
            pygame.draw.circle(self.screen, body_color, (mx, my), radius)
            pygame.draw.circle(self.screen, t.outline_color, (mx, my), radius, width=1)

        # HUD
        alive = sum(1 for m in mothers if m.alive)
        food_count = len(world.food_positions)
        avg_e = sum(m.energy for m in mothers if m.alive) / alive if alive > 0 else 0.0
        hud_y = self.grid_h * cs + 5
        text = f"Tick: {tick}  |  Alive: {alive}  |  Food: {food_count}  |  Avg Energy: {avg_e:.2f}"
        self.screen.blit(self.font.render(text, True, t.hud_text_color), (10, hud_y))

        pygame.display.flip()

    def tick(self, fps: int = 15) -> None:
        self.clock.tick(fps)

    def close(self) -> None:
        pygame.quit()
