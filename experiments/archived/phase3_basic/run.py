# experiments/phase3_basic/run.py
"""
Phase 3 Basic — diagnostic run.

Purpose: observe what happens when Phase 2 is extended with one child per mother.
No sweep, no parallelism. Prints tick-by-tick diagnostics for one seed,
then summary statistics across 5 seeds.

Usage:
    python -m experiments.phase3_basic.run
    python -m experiments.phase3_basic.run --seeds 5 --trace_ticks 30
"""
import argparse
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from simulation.simulation import Simulation
from experiments.phase3_basic.config import load_phase3_config


# ── Tick-by-tick trace for one seed ──────────────────────────────────────────

def trace_one_seed(seed: int, n_ticks: int = 40) -> None:
    """Print tick-by-tick state for the first n_ticks of one simulation."""
    cfg = load_phase3_config(seed=seed)
    sim = Simulation(cfg)
    sim.initialize()

    # Pick mother 0 and her child for the trace
    m0 = sim.mothers[0]
    own_child = sim._child_by_id.get(m0.own_child_id)

    print(f"\n{'='*72}")
    print(f"TRACE  seed={seed}  ecology: eat_gain={cfg.eat_gain}  init_food={cfg.init_food}"
          f"  move_cost={cfg.move_cost}  perception_radius={cfg.perception_radius}")
    print(f"infant_starvation_multiplier={cfg.infant_starvation_multiplier:.2f}"
          f"  -> child hunger_rate={cfg.hunger_rate * cfg.infant_starvation_multiplier:.4f}/tick"
          f"  -> starves in {1.0 / (cfg.hunger_rate * cfg.infant_starvation_multiplier):.1f} ticks unfed")
    print(f"{'='*72}")
    print(f"{'Tick':>4} | {'M_E':>5} | {'M_hld':>5} | {'Action':>7} | "
          f"{'C_E':>5} | {'C_dist':>6} | {'C_distr':>7} | {'n_alive_c':>9}")
    print(f"{'-'*72}")

    for t in range(n_ticks):
        if not m0.alive:
            print(f"  Mother 0 DIED at tick {t}")
            break

        # State BEFORE this step
        own_child = sim._child_by_id.get(m0.own_child_id) if m0.own_child_id else own_child
        c_energy  = own_child.energy   if own_child and own_child.alive else 0.0
        c_dist    = sim.world.get_distance(m0.pos, own_child.pos) if own_child and own_child.alive else -1
        c_distress = own_child.distress if own_child and own_child.alive else 0.0
        n_alive_c = sum(1 for c in sim.children if c.alive)

        sim.step()
        sim.tick += 1

        action = m0.last_motivation if m0.alive else "DEAD"
        print(f"  {t:>3} | {m0.energy if m0.alive else 0:>5.3f} | {m0.held_food if m0.alive else 0:>5} | "
              f"{action:>7} | {c_energy:>5.3f} | {c_dist:>6} | {c_distress:>7.3f} | {n_alive_c:>9}")

    print()


# ── Summary statistics across multiple seeds ─────────────────────────────────

def run_summary(seeds: list[int]) -> None:
    """Run full 400-tick simulation for each seed and print summary."""
    print(f"\n{'='*72}")
    print(f"SUMMARY across {len(seeds)} seeds")
    print(f"{'='*72}")
    print(f"{'Seed':>6} | {'M_surv':>8} | {'C_surv':>8} | {'C_matured':>9} | "
          f"{'Feeds':>7} | {'CARE%':>6} | {'FORAGE%':>8} | {'SELF%':>6}")
    print(f"{'-'*72}")

    totals = {"m_surv": [], "c_surv": [], "feeds": [], "care_pct": [], "forage_pct": [], "self_pct": []}

    for seed in seeds:
        cfg = load_phase3_config(seed=seed)
        sim = Simulation(cfg)
        sim.run()

        alive_m  = sum(1 for m in sim.mothers if m.alive)
        matured  = sum(1 for r in sim.logger.death_records
                       if r.agent_type == "child" and r.cause == "matured")
        feeds    = len(sim.logger.care_records)

        # Action distribution from choice records (when a distressed child was visible)
        choices  = sim.logger.choice_records
        n_total  = len(choices)
        care_pct   = 100 * sum(1 for r in choices if r.winner_domain == "care")   / n_total if n_total else 0
        forage_pct = 100 * sum(1 for r in choices if r.winner_domain == "forage") / n_total if n_total else 0
        self_pct   = 100 * sum(1 for r in choices if r.winner_domain == "self")   / n_total if n_total else 0

        m_surv = alive_m / cfg.init_mothers
        c_surv = matured / cfg.init_mothers

        totals["m_surv"].append(m_surv)
        totals["c_surv"].append(c_surv)
        totals["feeds"].append(feeds)
        totals["care_pct"].append(care_pct)
        totals["forage_pct"].append(forage_pct)
        totals["self_pct"].append(self_pct)

        print(f"  {seed:>4} | {m_surv:>8.3f} | {c_surv:>8.3f} | {matured:>9} | "
              f"{feeds:>7} | {care_pct:>6.1f} | {forage_pct:>8.1f} | {self_pct:>6.1f}")

    # Mean row
    def mean(lst): return sum(lst) / len(lst) if lst else 0
    print(f"{'-'*72}")
    print(f"  {'mean':>4} | {mean(totals['m_surv']):>8.3f} | {mean(totals['c_surv']):>8.3f} | "
          f"{'---':>9} | {mean(totals['feeds']):>7.0f} | "
          f"{mean(totals['care_pct']):>6.1f} | {mean(totals['forage_pct']):>8.1f} | {mean(totals['self_pct']):>6.1f}")
    print()

    # Child death breakdown
    print("Child death causes (last seed):")
    cfg = load_phase3_config(seed=seeds[-1])
    sim = Simulation(cfg)
    sim.run()
    hunger_deaths  = sum(1 for r in sim.logger.death_records if r.agent_type == "child" and r.cause == "hunger")
    matured_count  = sum(1 for r in sim.logger.death_records if r.agent_type == "child" and r.cause == "matured")
    print(f"  Died of hunger : {hunger_deaths}")
    print(f"  Matured        : {matured_count}")

    # Tick distribution of child deaths (when do they die?)
    child_deaths = [r for r in sim.logger.death_records
                    if r.agent_type == "child" and r.cause == "hunger"]
    if child_deaths:
        death_ticks = [r.tick for r in child_deaths]
        print(f"  Death tick range: {min(death_ticks)}–{max(death_ticks)}"
              f"  (mean {sum(death_ticks)/len(death_ticks):.1f})")
    print()


# ── Entry point ───────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Phase 3 Basic — diagnostic run")
    parser.add_argument("--seeds",      type=int, default=5,
                        help="Number of seeds for summary (default 5)")
    parser.add_argument("--trace_seed", type=int, default=42,
                        help="Seed for the tick-by-tick trace (default 42)")
    parser.add_argument("--trace_ticks", type=int, default=40,
                        help="How many ticks to trace (default 40)")
    parser.add_argument("--no_trace",   action="store_true",
                        help="Skip the tick trace, only print summary")
    args = parser.parse_args()

    # Print config summary first
    cfg = load_phase3_config()
    print("\nPhase 3 Basic Configuration")
    print(f"  Ecology (percept8 BALANCED):")
    print(f"    eat_gain={cfg.eat_gain}  init_food={cfg.init_food}"
          f"  move_cost={cfg.move_cost}  perception_radius={cfg.perception_radius}"
          f"  food_perception_radius={cfg.food_perception_radius}")
    print(f"    hunger_rate={cfg.hunger_rate:.4f}  rest_recovery={cfg.rest_recovery}")
    print(f"  Phase 3 additions:")
    print(f"    infant_starvation_multiplier={cfg.infant_starvation_multiplier:.2f}")
    print(f"    care_weight={cfg.care_weight}  forage_weight={cfg.forage_weight}  self_weight={cfg.self_weight}")
    print(f"  Run: max_ticks={cfg.max_ticks}  init_mothers={cfg.init_mothers}  seeds={args.seeds}")

    if not args.no_trace:
        trace_one_seed(seed=args.trace_seed, n_ticks=args.trace_ticks)

    run_summary(seeds=list(range(42, 42 + args.seeds)))


if __name__ == "__main__":
    main()
