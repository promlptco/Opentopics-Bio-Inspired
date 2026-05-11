"""Phase 5 — Live pygame grid viewer for Baldwin evolution runs."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pygame

from ui.renderer_config import DARK_THEME, LIGHT_THEME, RendererTheme, lerp_color

if TYPE_CHECKING:
    from simulation.simulation import Simulation


class Phase5GridViewer:
    """Live pygame grid viewer for Phase 5 Baldwin evolution runs.

    Draws the spatial world (food, mothers, children) plus a two-line Phase 5
    HUD showing genetic care weight, child maturation rate, generation count,
    and a condition label (mutation / plasticity settings).

    Only one seed at a time can be visualized. EvolutionRunner routes to this
    class when --headless is not set, bypassing ProcessPoolExecutor entirely.

    Example:
        viewer = Phase5GridViewer(
            grid_width=50, grid_height=50, condition_label="mut=ON plast=OFF"
        )
        for tick in range(max_ticks):
            sim.step()
            snapshot = runner._sample(sim, tick)
            if not viewer.step(sim, tick, snapshot):
                break  # user closed window
        viewer.close()
    """

    _HUD_HEIGHT: int = 80

    _MOTIVATION_RINGS: dict[str, str] = {
        "FORAGE": "ring_forage",
        "SELF":   "ring_self",
        "CARE":   "ring_care",
    }

    def __init__(
        self,
        grid_width: int,
        grid_height: int,
        cell_size: int = 15,
        fps: int = 10,
        vis_every: int = 1,
        condition_label: str = "",
        circle_world: bool = False,
        theme: RendererTheme = DARK_THEME, #DARK_THEME, LIGHT_THEME
    ) -> None:
        """Initialize the pygame window.

        Args:
            grid_width: Simulation world width in cells (cfg.width).
            grid_height: Simulation world height in cells (cfg.height).
            cell_size: Pixels per grid cell. Default 14 → 700 px for a 50-cell grid.
            fps: Target frames per second; caps rendering speed.
            vis_every: Render one frame every N ticks. Use 1 for full fidelity,
                10+ for fast preview of long runs.
            condition_label: Short label shown in HUD line 1, e.g. "mut=ON plast=OFF".
            circle_world: Whether the arena is restricted to an inscribed circle.
            theme: RendererTheme colour scheme; defaults to LIGHT_THEME.
        """
        self._gw = grid_width
        self._gh = grid_height
        self._cs = cell_size
        self._fps = fps
        self._vis_every = vis_every
        self._label = condition_label
        self._circle_world = circle_world
        self._theme = theme
        self._open = True

        pygame.init()
        screen_w = grid_width * cell_size
        screen_h = grid_height * cell_size + self._HUD_HEIGHT
        self._screen = pygame.display.set_mode((screen_w, screen_h))
        pygame.display.set_caption("Phase 5 — Baldwin Evolution Live")
        self._clock = pygame.time.Clock()
        self._font_hud     = pygame.font.SysFont(None, 20)
        self._font_metrics = pygame.font.SysFont(None, 17)

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def step(
        self,
        sim: Simulation,
        tick: int,
        snapshot: dict | None = None,
    ) -> bool:
        """Render one simulation tick and poll pygame window events.

        Skips drawing when tick is not a multiple of vis_every, but always
        polls events so the window stays responsive between frames.

        Args:
            sim: Running Simulation instance (reads .world, .mothers, .children).
            tick: Current tick number.
            snapshot: Optional metrics dict from EvolutionRunner._sample()
                (keys: mean_genome_care, c_matr_cum, mean_generation,
                highest_generation).

        Returns:
            True to continue; False if the user closed the window or pressed Esc.
        """
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self._open = False
                return False
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                self._open = False
                return False

        if not self._open:
            return False

        if tick % self._vis_every == 0:
            self._draw(sim, tick, snapshot or {})
            self._clock.tick(self._fps)

        return True

    def close(self) -> None:
        """Shut down the pygame window and release resources."""
        self._open = False
        pygame.quit()

    # ------------------------------------------------------------------
    # Private — full frame rendering
    # ------------------------------------------------------------------

    def _draw(self, sim: Simulation, tick: int, snapshot: dict) -> None:
        """Draw world + HUD and flip the display.

        Args:
            sim: Running Simulation instance.
            tick: Current tick number for the HUD display.
            snapshot: Metrics dict from _sample() for Phase 5 HUD overlay.
        """
        t  = self._theme
        cs = self._cs

        self._screen.fill(t.bg_color)
        self._draw_grid(t, cs)
        self._draw_world_mask(t, cs)
        self._draw_food(sim.world, t, cs)
        self._draw_links(sim.mothers, sim.children, t, cs)
        self._draw_children(sim.children, t, cs)
        self._draw_mothers(sim.mothers, t, cs)
        self._draw_hud(sim.mothers, sim.children, tick, snapshot, t, cs)
        pygame.display.flip()

    def _cell_in_world(self, x: int, y: int) -> bool:
        if not self._circle_world:
            return True
        dx = (x + 0.5) - (self._gw / 2.0)
        dy = (y + 0.5) - (self._gh / 2.0)
        radius = min(self._gw, self._gh) / 2.0
        return dx * dx + dy * dy <= radius * radius

    def _draw_grid(self, t: RendererTheme, cs: int) -> None:
        for x in range(self._gw + 1):
            pygame.draw.line(
                self._screen, t.grid_color,
                (x * cs, 0), (x * cs, self._gh * cs),
            )
        for y in range(self._gh + 1):
            pygame.draw.line(
                self._screen, t.grid_color,
                (0, y * cs), (self._gw * cs, y * cs),
            )

    def _draw_world_mask(self, t: RendererTheme, cs: int) -> None:
        if not self._circle_world:
            return
        for x in range(self._gw):
            for y in range(self._gh):
                if self._cell_in_world(x, y):
                    continue
                pygame.draw.rect(
                    self._screen,
                    t.bg_color,
                    (x * cs + 1, y * cs + 1, cs - 1, cs - 1),
                )
        center = (self._gw * cs // 2, self._gh * cs // 2)
        radius = int(min(self._gw, self._gh) * cs / 2.0)
        pygame.draw.circle(self._screen, pygame.Color(255, 255, 255, 80), center, radius, width=3)

    def _draw_food(self, world, t: RendererTheme, cs: int) -> None:
        for fx, fy in world.food_positions:
            pygame.draw.circle(
                self._screen, t.food_color,
                (fx * cs + cs // 2, fy * cs + cs // 2),
                cs // 5,
            )

    def _draw_links(self, mothers, children, t: RendererTheme, cs: int) -> None:
        child_by_id = {c.id: c for c in children if c.alive}
        for mother in mothers:
            if not mother.alive or mother.own_child_id is None:
                continue
            child = child_by_id.get(mother.own_child_id)
            if child:
                pygame.draw.line(
                    self._screen, t.link_color,
                    (mother.x * cs + cs // 2, mother.y * cs + cs // 2),
                    (child.x  * cs + cs // 2, child.y  * cs + cs // 2),
                    1,
                )

    def _draw_children(self, children, t: RendererTheme, cs: int) -> None:
        for child in children:
            if not child.alive:
                continue
            cx = child.x * cs + cs // 2
            cy = child.y * cs + cs // 2
            r = max(6, cs // 6)
            body = lerp_color(1.0 - child.distress, t.child_color_low, t.child_color_high)
            diamond = [
                (cx, cy - r),
                (cx + r, cy),
                (cx, cy + r),
                (cx - r, cy),
            ]
            pygame.draw.polygon(self._screen, body, diamond)
            pygame.draw.polygon(self._screen, t.outline_color, diamond, width=1)
            pygame.draw.circle(
                self._screen, t.outline_color, (cx, cy), max(1, r // 3)
            )

    def _draw_mothers(self, mothers, t: RendererTheme, cs: int) -> None:
        for mother in mothers:
            if not mother.alive:
                continue
            mx = mother.x * cs + cs // 2
            my = mother.y * cs + cs // 2
            r  = cs // 2.5
            ring_key = self._MOTIVATION_RINGS.get(mother.last_motivation)
            if ring_key:
                pygame.draw.circle(
                    self._screen, getattr(t, ring_key),
                    (mx, my), r + 3, width=1,
                )
            body = lerp_color(mother.energy, t.mother_color_low, t.mother_color_high)
            pygame.draw.circle(self._screen, body, (mx, my), r)
            pygame.draw.circle(self._screen, t.outline_color, (mx, my), r, width=1)

    def _draw_hud(
        self,
        mothers,
        children,
        tick: int,
        snapshot: dict,
        t: RendererTheme,
        cs: int,
    ) -> None:
        """Draw two-line Phase 5 HUD below the grid.

        Line 1: Tick, alive mothers, alive children, condition label.
        Line 2: genome_care vs 1/3 baseline, c_matr_cum, mean/highest generation.
        Legend row: motivation ring colour key.

        Args:
            mothers: List of MotherAgent instances.
            children: List of ChildAgent instances.
            tick: Current tick for display.
            snapshot: Metrics dict from EvolutionRunner._sample().
            t: Active RendererTheme.
            cs: Cell size in pixels.
        """
        hud_y = self._gh * cs

        # Clear HUD area (covers any agent circle overflow from the bottom row)
        pygame.draw.rect(
            self._screen, t.bg_color,
            (0, hud_y, self._gw * cs, self._HUD_HEIGHT),
        )

        alive_m = sum(1 for m in mothers if m.alive)
        alive_c = sum(1 for c in children if c.alive)

        line1 = f"Tick {tick}  |  Mothers: {alive_m}  |  Children: {alive_c}"
        if self._label:
            line1 += f"  |  {self._label}"

        genome_care = snapshot.get("mean_genome_care", 0.0)
        c_matr      = snapshot.get("c_matr_cum",       0.0)
        mean_gen    = snapshot.get("mean_generation",   0.0)
        high_gen    = snapshot.get("highest_generation", 0)
        line2 = (
            f"genome_care: {genome_care:.3f}  [baseline 0.333]  |  "
            f"c_matr_cum: {c_matr:.3f}  |  gen: {mean_gen:.1f}  |  high_gen: {int(high_gen)}"
        )

        self._screen.blit(
            self._font_hud.render(line1, True, t.hud_text_color),
            (10, hud_y + 8),
        )
        self._screen.blit(
            self._font_metrics.render(line2, True, t.hud_text_color),
            (10, hud_y + 30),
        )

        # Motivation ring colour legend
        legend = [
            ("FORAGE", t.ring_forage),
            ("SELF",   t.ring_self),
            ("CARE",   t.ring_care),
        ]
        lx = 10
        for lbl, color in legend:
            pygame.draw.circle(self._screen, color, (lx + 5, hud_y + 62), 5)
            self._screen.blit(
                self._font_metrics.render(lbl, True, t.hud_text_color),
                (lx + 14, hud_y + 56),
            )
            lx += 75
