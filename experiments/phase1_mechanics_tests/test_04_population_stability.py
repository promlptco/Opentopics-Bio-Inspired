"""
Test 04: Population stability
- No immediate extinction
- No immediate explosion
- Deterministic with seed
- Starvation condition causes population decline/extinction
- Population trajectory plot is saved
"""
import sys
import os

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, PROJECT_ROOT)

from config import Config
from simulation.simulation import Simulation

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

MODULE_NUM = "04"
DEFAULT_SEED = 42
RUN_NUM = 1
TAG = f"test{MODULE_NUM}_{DEFAULT_SEED}_{RUN_NUM}"

_results = []


def _log(name: str, detail: str = "") -> None:
    _results.append({"test_name": name, "status": "PASS", "detail": detail})
    print(f"✓ {name} PASSED")


def _count_alive_mothers(sim: Simulation) -> int:
    return sum(1 for m in sim.mothers if m.alive)


def _count_alive_children(sim: Simulation) -> int:
    return sum(1 for c in sim.children if c.alive)


def _count_total_alive(sim: Simulation) -> int:
    return _count_alive_mothers(sim) + _count_alive_children(sim)


def _run_sim(config: Config, ticks: int, record: bool = False):
    """Run simulation for fixed ticks.

    If record=True, return both simulation and population history.
    """
    sim = Simulation(config)
    sim.initialize()

    history = {
        "tick": [0],
        "alive_mothers": [_count_alive_mothers(sim)],
        "alive_children": [_count_alive_children(sim)],
        "total_alive": [_count_total_alive(sim)],
        "total_mothers_created": [len(sim.mothers)],
        "total_children_created": [len(sim.children)],
    }

    for t in range(1, ticks + 1):
        sim.step()

        if record:
            history["tick"].append(t)
            history["alive_mothers"].append(_count_alive_mothers(sim))
            history["alive_children"].append(_count_alive_children(sim))
            history["total_alive"].append(_count_total_alive(sim))
            history["total_mothers_created"].append(len(sim.mothers))
            history["total_children_created"].append(len(sim.children))

    if record:
        return sim, history

    return sim


def test_no_immediate_extinction():
    """Population should not die out in first 100 ticks."""
    config = Config()
    config.init_mothers = 10
    config.max_ticks = 100
    config.seed = DEFAULT_SEED

    sim = _run_sim(config, 100)

    alive = _count_alive_mothers(sim)
    print(f"Alive mothers after 100 ticks: {alive}")

    assert alive > 0, "Population should not extinct immediately"

    _log("test_no_immediate_extinction", f"alive_mothers_at_t100={alive}")


def test_no_immediate_explosion():
    """Population should not grow unreasonably fast in first 100 ticks.

    Threshold: total created agents should not exceed 5x initial mothers.
    This uses created population, not only alive population, to catch reproduction bursts.
    """
    INIT_MOTHERS = 10
    EXPLOSION_THRESHOLD = INIT_MOTHERS * 5

    config = Config()
    config.init_mothers = INIT_MOTHERS
    config.max_ticks = 100
    config.seed = DEFAULT_SEED

    sim = _run_sim(config, 100)

    total_created = len(sim.mothers) + len(sim.children)

    print(
        f"Total created population after 100 ticks: {total_created} "
        f"(threshold={EXPLOSION_THRESHOLD})"
    )

    assert total_created <= EXPLOSION_THRESHOLD, \
        f"Population grew unreasonably fast: {total_created} > {EXPLOSION_THRESHOLD}"

    _log(
        "test_no_immediate_explosion",
        f"total_created_at_t100={total_created};"
        f"init_mothers={INIT_MOTHERS};"
        f"threshold={EXPLOSION_THRESHOLD}",
    )


def test_deterministic_with_seed():
    """Same seed should produce the same population trajectory."""
    trajectories = []

    for _ in range(2):
        config = Config()
        config.init_mothers = 5
        config.max_ticks = 50
        config.seed = 12345

        _, history = _run_sim(config, 50, record=True)
        trajectories.append(history["total_alive"])

    print(f"Run 1 final alive: {trajectories[0][-1]}")
    print(f"Run 2 final alive: {trajectories[1][-1]}")

    assert trajectories[0] == trajectories[1], \
        "Same seed should produce identical population trajectory"

    _log(
        "test_deterministic_with_seed",
        f"final_run1={trajectories[0][-1]};"
        f"final_run2={trajectories[1][-1]};"
        f"seed=12345",
    )


def test_no_food_causes_extinction_or_strong_decline():
    """Without food or rest recovery, population should collapse.

    Children and reproduction are disabled so no new agents with fresh energy
    enter the simulation. This isolates hunger/energy depletion.
    """
    INIT_MOTHERS = 5
    TICKS = 300

    config = Config()
    config.init_mothers = INIT_MOTHERS
    config.init_food = 0
    config.rest_recovery = 0.0
    config.children_enabled = False
    config.reproduction_enabled = False
    config.max_ticks = TICKS
    config.seed = DEFAULT_SEED

    sim = Simulation(config)
    sim.initialize()

    initial_alive = _count_alive_mothers(sim)

    for _ in range(TICKS):
        # Defensive clear: prevents food regrowth/spawn from breaking starvation isolation.
        sim.world.food_positions.clear()
        sim.step()

    final_alive = _count_alive_mothers(sim)

    print(f"Alive without food: initial={initial_alive}, final={final_alive}")

    assert final_alive < initial_alive, \
        "Population should decline without food and rest recovery"

    # Stronger condition: if your energy depletion is fast enough, this should reach zero.
    assert final_alive == 0, \
        f"Expected extinction under pure starvation by t={TICKS}, got alive={final_alive}"

    _log(
        "test_no_food_causes_extinction_or_strong_decline",
        f"initial_alive={initial_alive};"
        f"final_alive={final_alive};"
        f"ticks={TICKS};"
        f"rest_recovery=0;"
        f"children_enabled=False;"
        f"reproduction_enabled=False",
    )

def test_children_do_not_remain_alive_after_maturation():
    """Children should not be counted as alive children after becoming mothers."""
    config = Config()
    config.init_mothers = 10
    config.max_ticks = 120
    config.seed = DEFAULT_SEED

    sim, history = _run_sim(config, 120, record=True)

    # If children mature around tick 100, alive children should decrease or change.
    initial_children = history["alive_children"][0]
    final_children = history["alive_children"][-1]

    print(f"Alive children: initial={initial_children}, final={final_children}")

    assert final_children <= initial_children, (
        "Alive children should not stay constant/increase after maturation. "
        "Possible bug: matured children are still counted as alive children."
    )

    _log(
        "test_children_do_not_remain_alive_after_maturation",
        f"initial_children={initial_children};final_children={final_children}",
    )

def plot_population_trajectory(out_dir: str, ticks: int = 200) -> str:
    """Save polished population stability trajectory plot."""
    config = Config()
    config.init_mothers = 10
    config.max_ticks = ticks
    config.seed = DEFAULT_SEED

    _, history = _run_sim(config, ticks, record=True)

    # Colors matched to Test01-style palette
    COLORS = {
        "alive_mothers": "#2166AC",   # blue
        "alive_children": "#1A9850",  # green
        "total_alive": "#D6604D",     # red/orange
    }

    plt.style.use("default")
    fig, ax = plt.subplots(figsize=(11, 6), facecolor="#FFFFFF")
    fig.patch.set_facecolor("#FFFFFF")

    ax.set_facecolor("#FAFAFA")

    ax.plot(
        history["tick"],
        history["alive_mothers"],
        color=COLORS["alive_mothers"],
        linewidth=2.6,
        label="Alive mothers",
    )

    ax.plot(
        history["tick"],
        history["alive_children"],
        color=COLORS["alive_children"],
        linewidth=2.6,
        label="Alive children",
    )

    ax.plot(
        history["tick"],
        history["total_alive"],
        color=COLORS["total_alive"],
        linewidth=3.0,
        linestyle="-",
        label="Total alive",
    )

    # Highlight maturation / transition-looking jumps if visible
    ax.axvspan(95, 105, color="#2166AC", alpha=0.06)
    ax.axvspan(195, 205, color="#2166AC", alpha=0.06)

    ax.set_title(
        f"Population Stability — Phase 1 Test 04  |  seed={DEFAULT_SEED}",
        fontsize=14,
        fontweight="bold",
        color="#1A1A1A",
        pad=12,
    )

    ax.set_xlabel("Tick", fontsize=10, color="#444444")
    ax.set_ylabel("Population count", fontsize=10, color="#444444")

    ax.tick_params(colors="#333333", labelsize=9)

    for spine in ax.spines.values():
        spine.set_edgecolor("#CCCCCC")
        spine.set_linewidth(0.9)

    ax.grid(
        axis="both",
        color="#E0E0E0",
        linewidth=0.7,
        linestyle="--",
        alpha=0.9,
    )
    ax.set_axisbelow(True)

    ax.legend(
        fontsize=9,
        loc="upper right",
        facecolor="#FFFFFF",
        edgecolor="#CCCCCC",
        labelcolor="#333333",
        framealpha=0.95,
    )

    # Small summary box
    final_mothers = history["alive_mothers"][-1]
    final_children = history["alive_children"][-1]
    final_total = history["total_alive"][-1]

    summary = (
        f"Final @ t={ticks}\n"
        f"Mothers: {final_mothers}\n"
        f"Children: {final_children}\n"
        f"Total: {final_total}"
    )

    ax.text(
        0.02,
        0.96,
        summary,
        transform=ax.transAxes,
        fontsize=8.5,
        verticalalignment="top",
        horizontalalignment="left",
        color="#1A1A1A",
        bbox=dict(
            boxstyle="round,pad=0.45",
            facecolor="#FFFFFF",
            edgecolor="#CCCCCC",
            alpha=0.95,
        ),
    )

    plt.tight_layout()

    save_path = os.path.join(out_dir, "population_stability.png")
    fig.savefig(
        save_path,
        dpi=150,
        bbox_inches="tight",
        facecolor=fig.get_facecolor(),
    )
    plt.close(fig)

    return save_path


if __name__ == "__main__":
    import csv

    test_no_immediate_extinction()
    test_no_immediate_explosion()
    test_deterministic_with_seed()
    test_no_food_causes_extinction_or_strong_decline()
    test_children_do_not_remain_alive_after_maturation()

    out_dir = os.path.join(PROJECT_ROOT, "outputs", "phase1_mechanics_tests", TAG)
    os.makedirs(out_dir, exist_ok=True)

    with open(os.path.join(out_dir, "logs.csv"), "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["test_name", "status", "detail"])
        writer.writeheader()
        writer.writerows(_results)

    plot_path = plot_population_trajectory(out_dir, ticks=200)

    print(f"\n=== All population stability tests PASSED ===")
    print(f"Logs saved → outputs/phase1_mechanics_tests/{TAG}/logs.csv")
    print(f"Plot saved  → {plot_path}")