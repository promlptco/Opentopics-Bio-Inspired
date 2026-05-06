# ui/renderer_config.py
"""
Visual theme configuration for all renderers.

To create a new theme: add a RendererTheme instance and register it in THEMES.
To change a theme: edit the values below — do not touch renderer_survival.py or renderer.py.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class RendererTheme:
    # Background & grid
    bg_color: tuple
    grid_color: tuple
    hud_text_color: tuple

    # Food
    food_color: tuple

    # Agent body gradient — lerped from low→high by energy (0→1)
    mother_color_low: tuple   # low energy (dying)
    mother_color_high: tuple  # high energy (healthy)
    child_color_low: tuple    # high distress
    child_color_high: tuple   # low distress

    # Agent outline
    outline_color: tuple

    # Motivation rings
    ring_forage: tuple
    ring_self: tuple
    ring_care: tuple

    # Mother-child link line (maternal mode)
    link_color: tuple


def lerp_color(t: float, low: tuple, high: tuple) -> tuple:
    """Linearly interpolate between two RGB colors. t in [0, 1]."""
    t = max(0.0, min(1.0, t))
    return (
        int(low[0] + (high[0] - low[0]) * t),
        int(low[1] + (high[1] - low[1]) * t),
        int(low[2] + (high[2] - low[2]) * t),
    )


# ── Light theme (original white background) ───────────────────────────────────

LIGHT_THEME = RendererTheme(
    bg_color=(245, 245, 245),
    grid_color=(200, 200, 200),
    hud_text_color=(50, 50, 50),
    food_color=(100, 180, 100),
    mother_color_low=(180, 80, 80),
    mother_color_high=(70, 130, 180),
    child_color_low=(220, 80, 80),
    child_color_high=(120, 200, 120),
    outline_color=(50, 50, 50),
    ring_forage=(230, 160, 30),
    ring_self=(80, 80, 200),
    ring_care=(30, 180, 80),
    link_color=(255, 220, 100),
)

# ── Dark theme (neon gradient) ─────────────────────────────────────────────────

DARK_THEME = RendererTheme(
    bg_color=(12, 12, 20),
    grid_color=(25, 25, 38),
    hud_text_color=(180, 180, 180),
    food_color=(0, 255, 90),
    mother_color_low=(255, 50, 80),
    mother_color_high=(0, 230, 255),
    child_color_low=(255, 50, 80),
    child_color_high=(0, 255, 120),
    outline_color=(80, 80, 100),
    ring_forage=(255, 220, 0),
    ring_self=(0, 140, 255),
    ring_care=(0, 255, 120),
    link_color=(80, 80, 120),
)

# ── Registry ───────────────────────────────────────────────────────────────────

THEMES: dict[str, RendererTheme] = {
    "light": LIGHT_THEME,
    "dark": DARK_THEME,
}
