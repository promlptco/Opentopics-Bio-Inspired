import pygame
from simulation.world import GridWorld
from agents.mother import MotherAgent
from agents.child import ChildAgent

# Colors
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GRAY = (200, 200, 200)
GREEN = (100, 200, 100)
RED = (200, 100, 100)
BLUE = (100, 100, 200)
YELLOW = (255, 255, 100)

class Renderer:
    def __init__(self, width: int, height: int, cell_size: int = 30):
        pygame.init()
        self.cell_size = cell_size
        self.screen_width = width * cell_size
        self.screen_height = height * cell_size
        self.screen = pygame.display.set_mode((self.screen_width, self.screen_height))
        pygame.display.set_caption("Evo-Maternal Simulation")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.Font(None, 20)
    
    def handle_events(self) -> bool:
        """Return False if should quit"""
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
        self.screen.fill(WHITE)
        
        # Draw grid
        for x in range(world.width + 1):
            pygame.draw.line(
                self.screen, GRAY,
                (x * self.cell_size, 0),
                (x * self.cell_size, self.screen_height)
            )
        for y in range(world.height + 1):
            pygame.draw.line(
                self.screen, GRAY,
                (0, y * self.cell_size),
                (self.screen_width, y * self.cell_size)
            )
        
        # Draw food
        for fx, fy in world.food_positions:
            rect = pygame.Rect(
                fx * self.cell_size + 2,
                fy * self.cell_size + 2,
                self.cell_size - 4,
                self.cell_size - 4
            )
            pygame.draw.rect(self.screen, GREEN, rect)
        
        # Draw children
        for child in children:
            if not child.alive:
                continue
            cx = child.x * self.cell_size + self.cell_size // 2
            cy = child.y * self.cell_size + self.cell_size // 2
            radius = self.cell_size // 4
            
            # Color based on distress
            r = int(100 + 155 * child.distress)
            color = (r, 100, 100)
            pygame.draw.circle(self.screen, color, (cx, cy), radius)
        
        # Draw mothers
        for mother in mothers:
            if not mother.alive:
                continue
            mx = mother.x * self.cell_size + self.cell_size // 2
            my = mother.y * self.cell_size + self.cell_size // 2
            radius = self.cell_size // 3
            
            # Color based on energy
            b = int(100 + 155 * mother.energy)
            color = (100, 100, b)
            pygame.draw.circle(self.screen, color, (mx, my), radius)
            
            # Draw line to own child
            if mother.own_child_id is not None:
                for child in children:
                    if child.id == mother.own_child_id and child.alive:
                        cx = child.x * self.cell_size + self.cell_size // 2
                        cy = child.y * self.cell_size + self.cell_size // 2
                        pygame.draw.line(self.screen, YELLOW, (mx, my), (cx, cy), 1)
        
        # Draw tick counter
        tick_text = self.font.render(f"Tick: {tick}", True, BLACK)
        self.screen.blit(tick_text, (10, 10))
        
        # Draw stats
        alive_mothers = sum(1 for m in mothers if m.alive)
        alive_children = sum(1 for c in children if c.alive)
        stats_text = self.font.render(f"M: {alive_mothers}  C: {alive_children}", True, BLACK)
        self.screen.blit(stats_text, (10, 30))
        
        pygame.display.flip()
    
    def tick(self, fps: int = 10) -> None:
        self.clock.tick(fps)
    
    def close(self) -> None:
        pygame.quit()