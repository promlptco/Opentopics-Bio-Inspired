# simulation/pathfinding.py
"""
Pathfinding algorithms for grid-world agents, ordered easiest → hardest.

All algorithms share the same signature:
    find_step(from_pos, to_pos, is_free, in_bounds) -> tuple[int, int]

    from_pos  : (x, y) current position
    to_pos    : (x, y) target position  (treated as passable even if occupied)
    is_free   : callable(pos) -> bool   (checks occupancy + bounds)
    in_bounds : callable(x, y) -> bool  (bounds check only)

    Returns: next (x, y) to move to, or from_pos if stuck / no path.

Usage in world.py:
    from simulation.pathfinding import astar_octile
    ...
    return astar_octile(from_pos, to_pos, self.is_free, self.in_bounds)

Algorithms
----------
1. naive_step        — original 3-direction greedy (can get stuck)
2. greedy_step       — try all 8 neighbours, pick closest to target
3. bfs_step          — BFS shortest path (unweighted, uniform move cost)
4. astar_chebyshev   — A* with Chebyshev heuristic (all 8 moves cost 1)
5. astar_octile      — A* with octile heuristic   (diagonal costs √2) ← best
"""

from __future__ import annotations
import heapq
import math
from typing import Callable

# 8-directional neighbour offsets
_DIRS = [
    (dx, dy)
    for dx in (-1, 0, 1)
    for dy in (-1, 0, 1)
    if not (dx == 0 and dy == 0)
]

Pos = tuple[int, int]
IsFree   = Callable[[Pos], bool]
InBounds = Callable[[int, int], bool]


# =============================================================================
# 1. NAIVE STEP  — original behaviour, fastest, can get stuck
# =============================================================================

def naive_step(from_pos: Pos, to_pos: Pos,
               is_free: IsFree, in_bounds: InBounds) -> Pos:
    """Try diagonal → horizontal → vertical. Give up (stay) if all blocked."""
    fx, fy = from_pos
    tx, ty = to_pos

    dx = 0 if tx == fx else (1 if tx > fx else -1)
    dy = 0 if ty == fy else (1 if ty > fy else -1)

    for candidate in (
        (fx + dx, fy + dy),          # diagonal
        (fx + dx, fy) if dx else None,
        (fx, fy + dy) if dy else None,
    ):
        if candidate and is_free(candidate):
            return candidate

    return from_pos


# =============================================================================
# 2. GREEDY STEP  — all 8 directions, pick free neighbour closest to target
# =============================================================================

def greedy_step(from_pos: Pos, to_pos: Pos,
                is_free: IsFree, in_bounds: InBounds) -> Pos:
    """
    Expand all 8 neighbours and pick whichever is free AND
    minimises Chebyshev distance to target.
    One step only — no lookahead. Can still get stuck in concave obstacles.
    """
    best_pos  = from_pos
    best_dist = math.inf

    for ddx, ddy in _DIRS:
        npos = (from_pos[0] + ddx, from_pos[1] + ddy)
        if npos != to_pos and not is_free(npos):
            continue
        dist = max(abs(npos[0] - to_pos[0]), abs(npos[1] - to_pos[1]))
        if dist < best_dist:
            best_dist = dist
            best_pos  = npos

    return best_pos


# =============================================================================
# 3. BFS STEP  — shortest hop-count path, uniform cost
# =============================================================================

def bfs_step(from_pos: Pos, to_pos: Pos,
             is_free: IsFree, in_bounds: InBounds) -> Pos:
    """
    Breadth-first search — guaranteed shortest path in number of steps.
    All 8 moves treated as cost 1.  Returns the first step of that path.
    Slower than greedy but handles all obstacle shapes.
    """
    if from_pos == to_pos:
        return from_pos

    visited: set[Pos] = {from_pos}
    # queue entries: (current_pos, first_step_taken)
    queue: list[tuple[Pos, Pos]] = []

    for ddx, ddy in _DIRS:
        npos = (from_pos[0] + ddx, from_pos[1] + ddy)
        if not in_bounds(*npos):
            continue
        if npos != to_pos and not is_free(npos):
            continue
        visited.add(npos)
        queue.append((npos, npos))

    head = 0
    while head < len(queue):
        pos, first_step = queue[head]; head += 1

        if pos == to_pos:
            return first_step

        for ddx, ddy in _DIRS:
            npos = (pos[0] + ddx, pos[1] + ddy)
            if not in_bounds(*npos) or npos in visited:
                continue
            if npos != to_pos and not is_free(npos):
                continue
            visited.add(npos)
            queue.append((npos, first_step))

    return from_pos  # no path


# =============================================================================
# 4. A* WITH CHEBYSHEV HEURISTIC  — optimal, all moves cost 1
# =============================================================================

def astar_chebyshev(from_pos: Pos, to_pos: Pos,
                    is_free: IsFree, in_bounds: InBounds) -> Pos:
    """
    A* search where every move (cardinal or diagonal) costs 1.
    Heuristic: Chebyshev distance  h = max(|dx|, |dy|).
    Admissible and consistent — finds optimal path.
    """
    if from_pos == to_pos:
        return from_pos

    def h(pos: Pos) -> int:
        return max(abs(pos[0] - to_pos[0]), abs(pos[1] - to_pos[1]))

    counter = 0
    # heap: (f, g, tie_breaker, pos, first_step)
    open_heap: list = [(h(from_pos), 0, counter, from_pos, None)]
    closed: set[Pos] = set()

    while open_heap:
        _f, g, _tie, pos, first_step = heapq.heappop(open_heap)

        if pos in closed:
            continue
        closed.add(pos)

        if pos == to_pos:
            return first_step  # type: ignore[return-value]

        for ddx, ddy in _DIRS:
            npos = (pos[0] + ddx, pos[1] + ddy)
            if not in_bounds(*npos) or npos in closed:
                continue
            if npos != to_pos and not is_free(npos):
                continue

            ng = g + 1
            nf = ng + h(npos)
            first = npos if first_step is None else first_step
            counter += 1
            heapq.heappush(open_heap, (nf, ng, counter, npos, first))

    return from_pos  # no path


# =============================================================================
# 5. A* WITH OCTILE HEURISTIC  — optimal, diagonal costs √2
# =============================================================================

_SQRT2 = math.sqrt(2)

def astar_octile(from_pos: Pos, to_pos: Pos,
                 is_free: IsFree, in_bounds: InBounds) -> Pos:
    """
    A* search with octile distance heuristic.

    Move costs:
        cardinal  (N/S/E/W)  : 1.0
        diagonal  (NE/NW/…)  : √2 ≈ 1.414

    Heuristic (octile distance):
        h = max(|dx|,|dy|) + (√2 − 1) × min(|dx|,|dy|)

    Admissible and consistent — finds the true shortest weighted path.
    Better than Chebyshev A* when diagonal moves genuinely cost more.
    """
    if from_pos == to_pos:
        return from_pos

    def h(pos: Pos) -> float:
        dx = abs(pos[0] - to_pos[0])
        dy = abs(pos[1] - to_pos[1])
        return max(dx, dy) + (_SQRT2 - 1) * min(dx, dy)

    counter = 0
    open_heap: list = [(h(from_pos), 0.0, counter, from_pos, None)]
    closed: set[Pos] = set()

    while open_heap:
        _f, g, _tie, pos, first_step = heapq.heappop(open_heap)

        if pos in closed:
            continue
        closed.add(pos)

        if pos == to_pos:
            return first_step  # type: ignore[return-value]

        for ddx, ddy in _DIRS:
            npos = (pos[0] + ddx, pos[1] + ddy)
            if not in_bounds(*npos) or npos in closed:
                continue
            if npos != to_pos and not is_free(npos):
                continue

            step_cost = _SQRT2 if (ddx != 0 and ddy != 0) else 1.0
            ng  = g + step_cost
            nf  = ng + h(npos)
            first = npos if first_step is None else first_step
            counter += 1
            heapq.heappush(open_heap, (nf, ng, counter, npos, first))

    return from_pos  # no path
