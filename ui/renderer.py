import pygame
from simulation.world import GridWorld
from agents.mother import MotherAgent
from agents.child import ChildAgent

# Colors
BG_COLOR = (245, 245, 245)
GRID_COLOR = (200, 200, 200)
OUTLINE_COLOR = (50, 50, 50)
FOOD_COLOR = (100, 180, 100)
MOTHER_COLOR = (70, 130, 180)
CHILD_COLOR = (255, 180, 120)
LINK_COLOR = (255, 220, 100)


def intensity_to_color(value: float, low_color: tuple, high_color: tuple) -> tuple:
    """Map 0-1 value to color gradient."""
    value = max(0.0, min(1.0, value))
    r = int(low_color[0] + (high_color[0] - low_color[0]) * value)
    g = int(low_color[1] + (high_color[1] - low_color[1]) * value)
    b = int(low_color[2] + (high_color[2] - low_color[2]) * value)
    return (r, g, b)


def draw_grid(surface, grid_w: int, grid_h: int, cell_px: int) -> None:
    """Draw grid background with lines and border."""
    surface.fill(BG_COLOR)
    pygame.draw.rect(surface, OUTLINE_COLOR, (0, 0, grid_w * cell_px, grid_h * cell_px), width=2)
    
    for x in range(1, grid_w):
        pygame.draw.line(surface, GRID_COLOR, (x * cell_px, 0), (x * cell_px, grid_h * cell_px))
    for y in range(1, grid_h):
        pygame.draw.line(surface, GRID_COLOR, (0, y * cell_px), (grid_w * cell_px, y * cell_px))


def draw_food(surface, x: int, y: int, cell_px: int) -> None:
    """Draw food as small square."""
    center_x = x * cell_px + cell_px // 2
    center_y = y * cell_px + cell_px // 2
    size = cell_px // 3
    rect = pygame.Rect(center_x - size // 2, center_y - size // 2, size, size)
    
    pygame.draw.rect(surface, FOOD_COLOR, rect)
    pygame.draw.rect(surface, OUTLINE_COLOR, rect, width=1)


def draw_mother(surface, mother: MotherAgent, cell_px: int, font: pygame.font.Font) -> None:
    """Draw mother as circle with state indicators."""
    if not mother.alive:
        return
    
    center_x = mother.x * cell_px + cell_px // 2
    center_y = mother.y * cell_px + cell_px // 2
    radius = cell_px // 3
    
    # Color based on energy (blue = high, red = low)
    color = intensity_to_color(mother.energy, (180, 80, 80), MOTHER_COLOR)
    
    # Body
    pygame.draw.circle(surface, color, (center_x, center_y), radius)
    pygame.draw.circle(surface, OUTLINE_COLOR, (center_x, center_y), radius, width=2)
    
    # Label
    text = font.render("M", True, (255, 255, 255))
    text_rect = text.get_rect(center=(center_x, center_y))
    surface.blit(text, text_rect)
    
    # Holding food indicator (orange ring)
    if mother.held_food > 0:
        pygame.draw.circle(surface, (230, 140, 40), (center_x, center_y), radius + 4, width=2)


def draw_child(surface, child: ChildAgent, cell_px: int, font: pygame.font.Font) -> None:
    """Draw child as smaller circle with distress color."""
    if not child.alive:
        return
    
    center_x = child.x * cell_px + cell_px // 2
    center_y = child.y * cell_px + cell_px // 2
    radius = cell_px // 4
    
    # Color based on distress (green = ok, red = high distress)
    color = intensity_to_color(child.distress, (120, 200, 120), (220, 80, 80))
    
    # Body
    pygame.draw.circle(surface, color, (center_x, center_y), radius)
    pygame.draw.circle(surface, OUTLINE_COLOR, (center_x, center_y), radius, width=2)
    
    # Label
    text = font.render("C", True, (0, 0, 0))
    text_rect = text.get_rect(center=(center_x, center_y))
    surface.blit(text, text_rect)


def draw_mother_child_link(surface, mother: MotherAgent, child: ChildAgent, cell_px: int) -> None:
    """Draw line connecting mother to her own child."""
    if not mother.alive or not child.alive:
        return
    
    mx = mother.x * cell_px + cell_px // 2
    my = mother.y * cell_px + cell_px // 2
    cx = child.x * cell_px + cell_px // 2
    cy = child.y * cell_px + cell_px // 2
    
    pygame.draw.line(surface, LINK_COLOR, (mx, my), (cx, cy), 1)


def draw_hud(surface, tick: int, mothers: int, children: int, font: pygame.font.Font) -> None:
    """Draw HUD with stats."""
    text = f"Tick: {tick} | Mothers: {mothers} | Children: {children}"
    text_surface = font.render(text, True, (50, 50, 50))
    surface.blit(text_surface, (10, 10))


class Renderer:
    def __init__(self, width: int, height: int, cell_size: int = 30):
        pygame.init()
        self.cell_size = cell_size
        self.grid_w = width
        self.grid_h = height
        self.screen_width = width * cell_size
        self.screen_height = height * cell_size + 40  # extra for HUD
        self.screen = pygame.display.set_mode((self.screen_width, self.screen_height))
        pygame.display.set_caption("Maternal Care Simulation")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont(None, 18)
    
    def handle_events(self) -> bool:
        """Return False if should quit."""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    return False
        return True
    
    def render(
        self,
        world: GridWorld,
        mothers: list[MotherAgent],
        children: list[ChildAgent],
        tick: int
    ) -> None:
        # Grid
        draw_grid(self.screen, self.grid_w, self.grid_h, self.cell_size)
        
        # Food
        for fx, fy in world.food_positions:
            draw_food(self.screen, fx, fy, self.cell_size)
        
        # Mother-child links
        for mother in mothers:
            if mother.own_child_id is not None:
                for child in children:
                    if child.id == mother.own_child_id:
                        draw_mother_child_link(self.screen, mother, child, self.cell_size)
        
        # Children
        for child in children:
            draw_child(self.screen, child, self.cell_size, self.font)
        
        # Mothers
        for mother in mothers:
            draw_mother(self.screen, mother, self.cell_size, self.font)
        
        # HUD
        alive_m = sum(1 for m in mothers if m.alive)
        alive_c = sum(1 for c in children if c.alive)
        draw_hud(self.screen, tick, alive_m, alive_c, self.font)
        
        pygame.display.flip()
    
    def tick(self, fps: int = 10) -> None:
        self.clock.tick(fps)
    
    def close(self) -> None:
        pygame.quit()