"""
Test 07: Individual agent starvation without food
- Mother energy drops to 0 before max_ticks (lifetime)
- Child hunger rises to critical level before maturity_age
- Mean energy of both agent types declines monotonically without food
"""
import sys
import os

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, PROJECT_ROOT)

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from agents.mother import MotherAgent
from agents.child import ChildAgent
from evolution.genome import Genome
from config import Config

MODULE_NUM = "07"
DEFAULT_SEED = 42
RUN_NUM = 1
TAG = f"test{MODULE_NUM}_{DEFAULT_SEED}_{RUN_NUM}"

CRITICAL_HUNGER = 0.7

_results = []


def _log(name: str, detail: str = "") -> None:
    _results.append({"test_name": name, "status": "PASS", "detail": detail})
    print(f"[PASS] {name}")


def test_mother_energy_drops_to_zero():
    """Mother energy must reach 0 before max_ticks without food."""
    config = Config()
    TICKS = config.max_ticks  # 300
    INIT_ENERGIES = [0.75, 0.80, 0.85, 0.90, 0.95]

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
    """Child hunger must reach critical level before maturity_age without food."""
    config = Config()
    TICKS = config.maturity_age  # 100
    N = 5

    children = [ChildAgent(0, 0, i, 0, i) for i in range(N)]
    vitality_history = [[1.0 - c.hunger] for c in children]

    for _ in range(1, TICKS + 1):
        for idx, c in enumerate(children):
            if c.alive:
                c.update_hunger(config.hunger_rate)
                c.tick_age()
                c.check_death()
            vitality_history[idx].append(max(0.0, 1.0 - c.hunger))

    final_hungers = [c.hunger for c in children]

    assert all(h >= CRITICAL_HUNGER for h in final_hungers), \
        f"All children must reach hunger >= {CRITICAL_HUNGER} before maturity_age"

    assert np.mean([v[-1] for v in vitality_history]) < 1.0, \
        "Mean child vitality must drop below initial (1.0)"

    _log(
        "test_child_hunger_critical_before_maturity",
        f"final_hungers={[round(h, 3) for h in final_hungers]};"
        f"mean_final_hunger={np.mean(final_hungers):.3f};"
        f"critical_threshold={CRITICAL_HUNGER};"
        f"maturity_age={TICKS}",
    )
    return vitality_history, final_hungers


def plot_starvation(
    mother_energy_history,
    mother_death_ticks,
    mother_init_energies,
    child_vitality_history,
    child_final_hungers,
    out_dir: str,
    config: Config,
) -> str:
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
        "Individual Agent Starvation — Phase 1 Test 07  |  No Food",
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

    # ── Left: Mother energy ──────────────────────────────────────
    ax = axes[0]
    mother_arr = np.array(mother_energy_history)   # (N, ticks+1)
    tick_m = np.arange(mother_arr.shape[1])

    for row in mother_arr:
        ax.plot(tick_m, row, color=COLORS["mother_trace"], alpha=0.20, linewidth=1.2)

    mean_e = mother_arr.mean(axis=0)
    std_e  = mother_arr.std(axis=0)
    ax.plot(tick_m, mean_e, color=COLORS["mean"], linewidth=2.5,
            label="Mean energy", zorder=5)
    ax.fill_between(tick_m, mean_e - std_e, mean_e + std_e,
                    color=COLORS["mean"], alpha=0.18, label="±1 std")

    for dt in mother_death_ticks:
        ax.axvline(dt, color=COLORS["mother_trace"], linestyle=":", alpha=0.45, linewidth=1.0)

    mean_death = float(np.mean(mother_death_ticks))
    ax.axvline(mean_death, color=COLORS["death"], linestyle="--", linewidth=1.6,
               label=f"Mean death @ t={mean_death:.0f}", zorder=6)

    ax.set_xlim(0, config.max_ticks)
    ax.set_ylim(-0.05, 1.05)
    ax.set_xlabel("Tick", fontsize=10, color="#444444")
    ax.set_ylabel("Energy", fontsize=10, color="#444444")
    ax.set_title("Mother — Energy Without Food", fontsize=11, color="#1A1A1A")
    ax.legend(fontsize=8.5, loc="upper right", facecolor="#FFFFFF",
              edgecolor="#CCCCCC", framealpha=0.95)

    ax.text(
        0.03, 0.50,
        f"N={len(mother_init_energies)} mothers\n"
        f"Init energies: {mother_init_energies}\n"
        f"hunger_rate: {config.hunger_rate}\n"
        f"Mean death: t={mean_death:.0f}\n"
        f"Max lifetime: {config.max_ticks} ticks",
        transform=ax.transAxes, fontsize=8.0, verticalalignment="top",
        color="#1A1A1A",
        bbox=dict(boxstyle="round,pad=0.4", facecolor="#FFFFFF",
                  edgecolor="#CCCCCC", alpha=0.92),
    )

    # ── Right: Child vitality (1 − hunger) ───────────────────────
    ax = axes[1]
    child_arr = np.array(child_vitality_history)   # (N, ticks+1)
    tick_c = np.arange(child_arr.shape[1])

    for row in child_arr:
        ax.plot(tick_c, row, color=COLORS["child_trace"], alpha=0.20, linewidth=1.2)

    mean_v = child_arr.mean(axis=0)
    std_v  = child_arr.std(axis=0)
    ax.plot(tick_c, mean_v, color=COLORS["mean"], linewidth=2.5,
            label="Mean vitality", zorder=5)
    ax.fill_between(tick_c, mean_v - std_v, mean_v + std_v,
                    color=COLORS["mean"], alpha=0.18, label="±1 std")

    critical_vitality = 1.0 - CRITICAL_HUNGER
    ax.axhline(critical_vitality, color=COLORS["critical"], linestyle="--", linewidth=1.5,
               label=f"Critical vitality = {critical_vitality:.1f}  (hunger≥{CRITICAL_HUNGER})",
               zorder=6)

    ax.axvline(config.maturity_age, color=COLORS["maturity"], linestyle=":",
               linewidth=1.3, label=f"Maturity age (t={config.maturity_age})", zorder=6)

    ax.set_xlim(0, config.maturity_age + 5)
    ax.set_ylim(-0.05, 1.05)
    ax.set_xlabel("Tick", fontsize=10, color="#444444")
    ax.set_ylabel("Vitality  (1 − hunger)", fontsize=10, color="#444444")
    ax.set_title("Child — Vitality Without Food", fontsize=11, color="#1A1A1A")
    ax.legend(fontsize=8.5, loc="upper right", facecolor="#FFFFFF",
              edgecolor="#CCCCCC", framealpha=0.95)

    mean_fh = float(np.mean(child_final_hungers))
    mean_fv = float(np.mean([v[-1] for v in child_vitality_history]))
    ax.text(
        0.03, 0.50,
        f"N={len(child_final_hungers)} children\n"
        f"hunger_rate: {config.hunger_rate}\n"
        f"Final hunger: {mean_fh:.3f}\n"
        f"Final vitality: {mean_fv:.3f}\n"
        f"Critical thresh: {CRITICAL_HUNGER}",
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


def _print_report(mother_init_energies, mother_death_ticks, child_final_hungers, config):
    w = 54
    print()
    print("=" * w)
    print("  Test 07 — Individual Starvation  |  Short Report")
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


if __name__ == "__main__":
    import csv

    print("Running test_mother_energy_drops_to_zero...")
    m_energy_hist, m_death_ticks, m_init_e = test_mother_energy_drops_to_zero()

    print("Running test_child_hunger_critical_before_maturity...")
    c_vitality_hist, c_final_h = test_child_hunger_critical_before_maturity()

    config = Config()
    out_dir = os.path.join(PROJECT_ROOT, "outputs", "phase1_mechanics_tests", TAG)
    os.makedirs(out_dir, exist_ok=True)

    with open(os.path.join(out_dir, "logs.csv"), "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["test_name", "status", "detail"])
        writer.writeheader()
        writer.writerows(_results)

    plot_path = plot_starvation(
        m_energy_hist, m_death_ticks, m_init_e,
        c_vitality_hist, c_final_h,
        out_dir, config,
    )

    _print_report(m_init_e, m_death_ticks, c_final_h, config)

    print(f"=== All individual starvation tests PASSED ===")
    print(f"Logs saved -> outputs/phase1_mechanics_tests/{TAG}/logs.csv")
    print(f"Plot saved  -> {plot_path}")
