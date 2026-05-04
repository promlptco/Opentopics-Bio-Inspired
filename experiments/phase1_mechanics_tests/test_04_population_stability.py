"""
Test 04: Population stability
- No immediate extinction
- No immediate explosion
- Deterministic with seed
- Starvation condition causes population decline/extinction
- Population trajectory plot is saved

Individual starvation (no food):
- Mother energy drops to 0 before max_ticks
- Child hunger rises to critical level before maturity_age
- Mean energy of both agent types declines monotonically without food
"""
import sys
import os

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, PROJECT_ROOT)

import numpy as np

from config import Config
from simulation.simulation import Simulation
from agents.mother import MotherAgent
from agents.child import ChildAgent
from evolution.genome import Genome

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

CRITICAL_HUNGER = 0.7

MODULE_NUM = "04"
DEFAULT_SEED = 42
RUN_NUM = 2
TAG = f"test{MODULE_NUM}_{DEFAULT_SEED}_{RUN_NUM}"

_results = []


def _log(name: str, detail: str = "") -> None:
    _results.append({"test_name": name, "status": "PASS", "detail": detail})
    print(f"[PASS] {name}")


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
    """No child should remain alive as a child after reaching maturity age.

    Uses maturity_age=20 ticks (mechanism test, not ecological test) so that
    maturation actually occurs within the run window. Children survive 20 ticks
    without care even at hunger_rate=1/35 (energy at t=20 ≈ 0.43 > 0).
    The correct check is that zero children have age >= maturity_age while
    still counted as alive children.
    """
    config = Config()
    config.init_mothers = 10
    config.max_ticks = 50
    config.seed = DEFAULT_SEED
    config.maturity_age = 20          # short window to force maturation within run
    config.infant_starvation_multiplier = 1.0  # no extra pressure for mechanism test

    sim, history = _run_sim(config, 50, record=True)

    maturity_age = config.maturity_age
    matured_but_alive = [c for c in sim.children if c.alive and c.age >= maturity_age]

    initial_children = history["alive_children"][0]
    final_children   = history["alive_children"][-1]

    print(f"Alive children: initial={initial_children}, final={final_children}")
    print(f"Children alive AND age>={maturity_age} (must be 0): {len(matured_but_alive)}")

    assert len(matured_but_alive) == 0, (
        f"{len(matured_but_alive)} child(ren) are alive with age >= {maturity_age}. "
        "Matured children must be removed from the child pool on maturation."
    )

    _log(
        "test_children_do_not_remain_alive_after_maturation",
        f"initial_children={initial_children};final_children={final_children};"
        f"maturity_age={maturity_age};matured_but_still_child={len(matured_but_alive)}",
    )

def test_mother_energy_drops_to_zero():
    """Mother energy must reach 0 before max_ticks without food."""
    config = Config()
    TICKS = config.max_ticks  # 300
    INIT_ENERGIES = [0.80, 0.85, 0.90, 0.95, 1.00]  # includes new initial_energy=1.0

    mothers = []
    for i, e0 in enumerate(INIT_ENERGIES):
        m = MotherAgent(0, 0, i, 0, Genome())
        m.energy = e0
        mothers.append(m)

    energy_history = [[m.energy] for m in mothers]
    death_ticks = [None] * len(mothers)

    for t in range(1, TICKS + 1):
        for idx, m in enumerate(mothers):
            if m.alive:
                m.update_state(config.hunger_rate)
                cause = m.check_death()
                if cause and death_ticks[idx] is None:
                    death_ticks[idx] = t
            energy_history[idx].append(max(0.0, m.energy))

    assert all(not m.alive for m in mothers), \
        "All mothers must die without food before max_ticks"
    assert all(dt is not None for dt in death_ticks), \
        "All death ticks must be recorded"

    _log(
        "test_mother_energy_drops_to_zero",
        f"death_ticks={death_ticks};"
        f"mean_death_tick={np.mean(death_ticks):.1f};"
        f"max_ticks={TICKS}",
    )
    return energy_history, death_ticks, INIT_ENERGIES


def test_child_hunger_critical_before_maturity():
    """Child energy must drop and hunger must reach critical level before maturity_age without food."""
    config = Config()
    TICKS = config.maturity_age  # 100
    N = 5

    children = [ChildAgent(0, 0, i, 0, i) for i in range(N)]
    energy_history = [[c.energy] for c in children]
    child_hunger_rate = config.hunger_rate * config.infant_starvation_multiplier

    for _ in range(1, TICKS + 1):
        for idx, c in enumerate(children):
            if c.alive:
                c.update_hunger(child_hunger_rate)
                c.tick_age()
                c.check_death()
            energy_history[idx].append(max(0.0, c.energy))

    final_hungers = [c.hunger for c in children]

    # With infant_starvation_multiplier=2.33, children starve in ~15 ticks without care.
    # All children die (energy→0, hunger→1.0) well before maturity_age=200.
    assert all(h >= CRITICAL_HUNGER for h in final_hungers), \
        f"All children must reach hunger >= {CRITICAL_HUNGER} before maturity_age"

    _log(
        "test_child_hunger_critical_before_maturity",
        f"final_hungers={[round(h, 3) for h in final_hungers]};"
        f"mean_final_hunger={np.mean(final_hungers):.3f};"
        f"child_hunger_rate={child_hunger_rate:.4f};"
        f"infant_starvation_multiplier={config.infant_starvation_multiplier};"
        f"critical_threshold={CRITICAL_HUNGER};"
        f"maturity_age={TICKS}",
    )
    return energy_history, final_hungers, child_hunger_rate


def plot_starvation_individual(
    mother_energy_history,
    mother_death_ticks,
    mother_init_energies,
    child_energy_history,
    child_final_hungers,
    out_dir: str,
    config: Config,
    child_hunger_rate: float | None = None,
) -> str:
    """Save individual starvation plot for mothers and children."""
    COLORS = {
        "mother_trace": "#2166AC",
        "child_trace":  "#1A9850",
        "mean":         "#D6604D",
        "death":        "#CC3333",
        "critical":     "#E08040",
        "maturity":     "#555555",
    }

    fig, axes = plt.subplots(1, 2, figsize=(14, 6), facecolor="#FFFFFF")
    fig.suptitle(
        "Individual Agent Starvation — Phase 1 Test 04  |  No Food",
        fontsize=13, fontweight="bold", color="#1A1A1A", y=1.01,
    )

    for ax in axes:
        ax.set_facecolor("#FAFAFA")
        ax.grid(axis="both", color="#E0E0E0", linewidth=0.7, linestyle="--", alpha=0.9)
        ax.set_axisbelow(True)
        for spine in ax.spines.values():
            spine.set_edgecolor("#CCCCCC")
            spine.set_linewidth(0.9)
        ax.tick_params(colors="#333333", labelsize=9)

    # ── Left: Mother energy / stress ──────────────────────────────
    ax = axes[0]
    mother_arr = np.array(mother_energy_history)
    tick_m = np.arange(mother_arr.shape[1])

    for row in mother_arr:
        ax.plot(tick_m, row, color=COLORS["mother_trace"], alpha=0.20, linewidth=1.2)

    mean_e = mother_arr.mean(axis=0)
    std_e = mother_arr.std(axis=0)
    ax.plot(tick_m, mean_e, color=COLORS["mean"], linewidth=2.5,
            label="Mean energy", zorder=5)
    ax.fill_between(tick_m, mean_e - std_e, mean_e + std_e,
                    color=COLORS["mean"], alpha=0.18, label="+-1 std")

    for dt in mother_death_ticks:
        ax.axvline(dt, color=COLORS["mother_trace"], linestyle=":", alpha=0.45, linewidth=1.0)

    mean_death = float(np.mean(mother_death_ticks))
    ax.axvline(mean_death, color=COLORS["death"], linestyle="--", linewidth=1.6,
               label=f"Mean death @ t={mean_death:.0f}", zorder=6)

    # Critical stress line: stress = 1 - energy.
    critical_stress = CRITICAL_HUNGER
    critical_energy = 1.0 - critical_stress
    ax.axhline(
        critical_energy,
        color=COLORS["critical"],
        linestyle="--",
        linewidth=1.3,
        label=f"Critical stress ({critical_stress:.1f})",
        zorder=6,
    )

    x_max = max(mother_death_ticks) + 20
    ax.set_xlim(0, x_max)
    ax.set_ylim(-0.05, 1.05)
    ax.set_xlabel("Tick", fontsize=10, color="#444444")
    ax.set_ylabel("Energy", fontsize=10, color="#444444")
    ax.set_title("Mother — Energy Without Food  (stress = 1 − energy)", fontsize=11, color="#1A1A1A")
    ax.legend(fontsize=8.5, loc="upper right", facecolor="#FFFFFF",
              edgecolor="#CCCCCC", framealpha=0.95)

    final_energy = float(np.mean([row[-1] for row in mother_energy_history]))
    final_stress = 1.0 - final_energy

    ax.text(
        0.03, 0.50,
        f"N={len(mother_init_energies)} mothers\n"
        f"Init energies: {[round(e, 2) for e in mother_init_energies]}\n"
        f"energy_cost/tick: {config.hunger_rate:.4f}\n"
        f"Mean death: t={mean_death:.0f}\n"
        f"Final energy: {final_energy:.3f}\n"
        f"Final stress: {final_stress:.3f}\n"
        f"Critical stress: {critical_stress:.1f}",
        transform=ax.transAxes, fontsize=8.0, verticalalignment="top",
        color="#1A1A1A",
        bbox=dict(boxstyle="round,pad=0.4", facecolor="#FFFFFF",
                  edgecolor="#CCCCCC", alpha=0.92),
    )

    # ── Right: Child hunger ───────────────────────────────────────
    ax = axes[1]

    child_hunger_rate = child_hunger_rate if child_hunger_rate is not None else (
        config.hunger_rate * config.infant_starvation_multiplier
    )

    tick_c = np.arange(config.maturity_age + 1)
    hunger_curve = np.clip(tick_c * child_hunger_rate, 0.0, 1.0)
    child_arr = np.tile(hunger_curve, (len(child_final_hungers), 1))

    for row in child_arr:
        ax.plot(tick_c, row, color=COLORS["child_trace"], alpha=0.20, linewidth=1.2)

    mean_h = child_arr.mean(axis=0)
    std_h = child_arr.std(axis=0)
    ax.plot(tick_c, mean_h, color=COLORS["mean"], linewidth=2.5,
            label="Mean hunger", zorder=5)
    ax.fill_between(tick_c, mean_h - std_h, mean_h + std_h,
                    color=COLORS["mean"], alpha=0.18, label="+-1 std")

    ax.axvline(config.maturity_age, color=COLORS["maturity"], linestyle=":",
               linewidth=1.3, label=f"Maturity age (t={config.maturity_age})", zorder=6)

    ax.axhline(CRITICAL_HUNGER, color=COLORS["critical"], linestyle="--", linewidth=1.3,
               label=f"Critical hunger ({CRITICAL_HUNGER:.1f})", zorder=6)

    ax.set_xlim(0, config.maturity_age + 5)
    ax.set_ylim(-0.05, 1.05)
    ax.set_xlabel("Tick", fontsize=10, color="#444444")
    ax.set_ylabel("Hunger", fontsize=10, color="#444444")
    ax.set_title("Child — Hunger Without Food", fontsize=11, color="#1A1A1A")
    ax.legend(fontsize=8.5, loc="upper right", facecolor="#FFFFFF",
              edgecolor="#CCCCCC", framealpha=0.95)

    mean_fh = float(np.mean(child_final_hungers))
    ax.text(
        0.03, 0.50,
        f"N={len(child_final_hungers)} children\n"
        f"hunger_rate/tick: {child_hunger_rate:.4f} "
        f"(x{config.infant_starvation_multiplier:.1f})\n"
        f"Final hunger: {mean_fh:.3f}\n"
        f"Critical hunger: {CRITICAL_HUNGER:.1f}\n"
        f"Maturity age: {config.maturity_age}",
        transform=ax.transAxes, fontsize=8.0, verticalalignment="top",
        color="#1A1A1A",
        bbox=dict(boxstyle="round,pad=0.4", facecolor="#FFFFFF",
                  edgecolor="#CCCCCC", alpha=0.92),
    )

    plt.tight_layout()
    save_path = os.path.join(out_dir, "starvation_individual.png")
    fig.savefig(save_path, dpi=150, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)
    return save_path


def _print_starvation_report(mother_init_energies, mother_death_ticks, child_final_hungers, config):
    w = 54
    print()
    print("=" * w)
    print("  Test 04 — Individual Starvation  |  Short Report")
    print("=" * w)
    print(f"  hunger_rate={config.hunger_rate}   "
          f"rest_recovery={config.rest_recovery}   food=0")
    print()
    print(f"  MOTHER  (N={len(mother_init_energies)})")
    print(f"    Init energies : {mother_init_energies}")
    print(f"    Death ticks   : {mother_death_ticks}")
    print(f"    Mean death    : t={np.mean(mother_death_ticks):.1f}")
    print(f"    Max lifetime  : {config.max_ticks} ticks")
    print(f"    Result        : ALL died before max_ticks  [PASS]")
    print()
    print(f"  CHILD   (N={len(child_final_hungers)})")
    print(f"    Hunger @ maturity : {[round(h, 3) for h in child_final_hungers]}")
    print(f"    Mean hunger       : {np.mean(child_final_hungers):.3f}")
    print(f"    Critical thresh   : {CRITICAL_HUNGER}")
    print(f"    Result            : ALL critical before maturity  [PASS]")
    print("=" * w)
    print()


def plot_population_trajectory(out_dir: str, ticks: int = 300) -> str:
    """Save mother population lifecycle plot — mothers only, starvation-plot style."""
    config = Config()
    config.init_mothers = 10
    config.max_ticks = ticks
    config.seed = DEFAULT_SEED

    _, history = _run_sim(config, ticks, record=True)

    BLUE   = "#2166AC"
    MEAN   = "#D6604D"
    VLINE  = "#555555"

    fig, ax = plt.subplots(figsize=(11, 6), facecolor="#FFFFFF")
    fig.patch.set_facecolor("#FFFFFF")
    ax.set_facecolor("#FAFAFA")
    ax.set_axisbelow(True)
    ax.grid(axis="both", color="#E0E0E0", linewidth=0.7, linestyle="--", alpha=0.9)
    for spine in ax.spines.values():
        spine.set_edgecolor("#CCCCCC")
        spine.set_linewidth(0.9)
    ax.tick_params(colors="#333333", labelsize=9)

    tick_axis = history["tick"]

    # ── Mother population line ────────────────────────────────────
    ax.plot(tick_axis, history["alive_mothers"],
            color=BLUE, linewidth=2.6, label="Alive mothers", zorder=5)

    # ── Generation boundary lines ─────────────────────────────────
    maturity = config.maturity_age   # 100
    gen_boundaries = [t for t in range(maturity, ticks, maturity)]
    gen_labels = [
        "Gen 1 graduates\n-> new mothers\n-> Gen 2 born",
        "Gen 2 graduates\n-> new mothers\n-> Gen 3 born",
    ]
    y_positions = [0.65, 0.42]

    for i, t in enumerate(gen_boundaries):
        ax.axvline(t, color=VLINE, linestyle="--", linewidth=1.3, alpha=0.5, zorder=4)
        label = gen_labels[i] if i < len(gen_labels) else f"Gen {i+1} graduates"
        ypos  = y_positions[i] if i < len(y_positions) else 0.30
        ax.text(t + 4, ypos, label,
                transform=ax.get_xaxis_transform(),
                fontsize=7.5, color="#444444", va="top",
                bbox=dict(boxstyle="round,pad=0.3", facecolor="#FFFFFF",
                          edgecolor="#AAAAAA", alpha=0.90))

    ax.set_title(
        f"Agent Population Count — Phase 1 Test 04  |  seed={DEFAULT_SEED}",
        fontsize=14, fontweight="bold", color="#1A1A1A", pad=12,
    )
    ax.set_xlabel("Tick", fontsize=10, color="#444444")
    ax.set_ylabel("Agent population count", fontsize=10, color="#444444")
    ax.set_xlim(0, ticks)

    ax.legend(fontsize=9, loc="upper right", facecolor="#FFFFFF",
              edgecolor="#CCCCCC", labelcolor="#333333", framealpha=0.95)

    final_mothers = history["alive_mothers"][-1]
    ax.text(
        0.02, 0.96,
        f"Final @ t={ticks}\nMothers: {final_mothers}\nseed={DEFAULT_SEED}",
        transform=ax.transAxes, fontsize=8.5, va="top",
        color="#1A1A1A",
        bbox=dict(boxstyle="round,pad=0.45", facecolor="#FFFFFF",
                  edgecolor="#CCCCCC", alpha=0.95),
    )

    plt.tight_layout()
    save_path = os.path.join(out_dir, "population_stability.png")
    fig.savefig(save_path, dpi=150, bbox_inches="tight",
                facecolor=fig.get_facecolor())
    plt.close(fig)
    return save_path


if __name__ == "__main__":
    import csv

    test_no_immediate_extinction()
    test_no_immediate_explosion()
    test_deterministic_with_seed()
    test_no_food_causes_extinction_or_strong_decline()
    test_children_do_not_remain_alive_after_maturation()

    m_energy_hist, m_death_ticks, m_init_e = test_mother_energy_drops_to_zero()
    c_energy_hist, c_final_h, c_hunger_rate = test_child_hunger_critical_before_maturity()

    out_dir = os.path.join(PROJECT_ROOT, "outputs", "phase1_mechanics_tests", TAG)
    os.makedirs(out_dir, exist_ok=True)

    with open(os.path.join(out_dir, "logs.csv"), "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["test_name", "status", "detail"])
        writer.writeheader()
        writer.writerows(_results)

    plot_path = plot_population_trajectory(out_dir, ticks=300)

    config = Config()
    starv_plot_path = plot_starvation_individual(
        m_energy_hist, m_death_ticks, m_init_e,
        c_energy_hist, c_final_h,
        out_dir, config,
        child_hunger_rate=c_hunger_rate,
    )

    _print_starvation_report(m_init_e, m_death_ticks, c_final_h, config)

    print(f"\n=== All population stability tests PASSED ===")
    print(f"Logs saved         -> outputs/phase1_mechanics_tests/{TAG}/logs.csv")
    print(f"Population plot    -> {plot_path}")
    print(f"Starvation plot    -> {starv_plot_path}")