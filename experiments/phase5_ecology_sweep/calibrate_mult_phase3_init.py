# experiments/phase5_ecology_sweep/calibrate_mult_phase3_init.py
"""
Find minimum viable infant_starvation_multiplier for care to emerge
starting from Phase 3 canonical genome (care=0.30, forage=1.0, self=0.70).

Sweeps mult in [1.30, 1.35, 1.40, 1.45, 1.50, 1.55, 1.60] x seeds [42,43,44].
Runs 5,000 ticks per seed — enough to detect survival vs extinction and
care direction (rising vs eroding).

Reports per-mult:
  - pass_rate    : fraction of seeds where final_pop >= 10
  - mean_final_cw: mean care_weight at tick 5000 (0.0 = extinct)
  - mean_grad_r  : mean Pearson r (care_weight vs generation)
  - verdict      : CANDIDATE if pop survives AND final_cw > 0.30
"""
import sys, os, csv, math, random as _random

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, PROJECT_ROOT)

from config import Config
from simulation.simulation import Simulation
from evolution.genome import Genome
from utils.experiment import set_seed

MULTS  = [1.30, 1.35, 1.40, 1.45, 1.50, 1.55, 1.60]
SEEDS  = [42, 43, 44]
TICKS  = 5000
INIT_CARE    = 0.30
INIT_FORAGE  = 1.0
INIT_SELF    = 0.70
SURVIVAL_MIN = 10   # mothers at tick 5000
EMERGENCE_THRESHOLD = INIT_CARE  # care must exceed starting value


def _make_genomes(n):
    return [Genome(care_weight=INIT_CARE, forage_weight=INIT_FORAGE, self_weight=INIT_SELF)
            for _ in range(n)]


def _pearson_r(birth_log_path):
    if not os.path.exists(birth_log_path):
        return None
    with open(birth_log_path) as f:
        rows = list(csv.DictReader(f))
    if len(rows) < 10:
        return None
    cw   = [float(r["mother_care_weight"]) for r in rows]
    gens = [float(r["mother_generation"])  for r in rows]
    n = len(cw)
    mc, mg = sum(cw)/n, sum(gens)/n
    num = sum((cw[i]-mc)*(gens[i]-mg) for i in range(n))
    dc  = sum((x-mc)**2 for x in cw)**0.5
    dg  = sum((x-mg)**2 for x in gens)**0.5
    return num/(dc*dg) if dc and dg else None


def run_one(mult, seed):
    config = Config()
    config.seed    = seed
    config.width   = 50
    config.height  = 50
    config.init_mothers = 40
    config.init_food    = 120
    config.infant_starvation_multiplier = mult
    config.birth_scatter_radius         = 2
    config.plasticity_enabled           = False
    config.plasticity_kin_conditional   = False
    config.children_enabled             = True
    config.care_enabled                 = True
    config.reproduction_enabled         = True
    config.mutation_enabled             = True
    config.max_ticks = TICKS

    set_seed(seed)
    output_dir = os.path.join(
        PROJECT_ROOT, "outputs", "phase5_ecology_sweep",
        f"calib_mult{mult:.2f}_seed{seed}"
    )
    os.makedirs(output_dir, exist_ok=True)

    genomes = _make_genomes(config.init_mothers)
    sim = Simulation(config)
    sim.initialize(genomes)

    while sim.tick < config.max_ticks:
        sim.step()
        sim.tick += 1

    sim.logger.save_all(output_dir)

    alive = [m for m in sim.mothers if m.alive]
    final_pop = len(alive)
    final_cw  = sum(m.genome.care_weight for m in alive) / final_pop if final_pop else 0.0
    grad_r    = _pearson_r(os.path.join(output_dir, "birth_log.csv"))
    return final_pop, final_cw, grad_r


def main():
    print(f"\nPhase 5 mult calibration — care=0.30 init, {TICKS} ticks, seeds {SEEDS}")
    print(f"{'Mult':>6}  {'Seed':>5}  {'FinalPop':>9}  {'FinalCW':>8}  {'GradR':>8}  {'Status'}")
    print("-" * 65)

    results = {}
    for mult in MULTS:
        pops, cws, grads = [], [], []
        for seed in SEEDS:
            final_pop, final_cw, grad_r = run_one(mult, seed)
            survived = final_pop >= SURVIVAL_MIN
            status = "PASS" if survived else "FAIL"
            grad_str = f"{grad_r:+.4f}" if grad_r is not None else "   N/A"
            print(f"{mult:>6.2f}  {seed:>5}  {final_pop:>9}  {final_cw:>8.4f}  {grad_str:>8}  {status}")
            pops.append(final_pop)
            cws.append(final_cw)
            if grad_r is not None:
                grads.append(grad_r)

        pass_rate  = sum(1 for p in pops if p >= SURVIVAL_MIN) / len(SEEDS)
        mean_cw    = sum(cws) / len(cws)
        mean_grad  = sum(grads) / len(grads) if grads else None
        pop_viable = pass_rate >= 2/3          # >=2/3 seeds survive
        cw_rising  = mean_cw > EMERGENCE_THRESHOLD
        verdict    = "CANDIDATE" if pop_viable and cw_rising else (
                     "SURVIVE_ONLY" if pop_viable else (
                     "EXTINCT" if pass_rate == 0 else "MARGINAL"))
        grad_str   = f"{mean_grad:+.4f}" if mean_grad is not None else "   N/A"
        print(f"  -> pass={pass_rate:.0%}  mean_cw={mean_cw:.4f}  mean_r={grad_str}  [{verdict}]")
        print()
        results[mult] = {
            "pass_rate": pass_rate, "mean_cw": mean_cw,
            "mean_grad": mean_grad, "verdict": verdict,
        }

    print("=" * 65)
    print("Summary — minimum viable mult for care emergence from 0.30:")
    candidates = [(m, r) for m, r in results.items() if r["verdict"] == "CANDIDATE"]
    if candidates:
        best_mult, best = candidates[0]
        print(f"  MINIMUM CANDIDATE: mult={best_mult:.2f}")
        print(f"    pass_rate={best['pass_rate']:.0%}  mean_cw={best['mean_cw']:.4f}  mean_r={best['mean_grad']:+.4f}")
        print(f"\n  -> Use mult={best_mult:.2f} as INFANT_STARVATION_MULT in Phase 5 full run.")
    else:
        print("  No candidate found in sweep range. Consider lowering mult below 1.30")
        print("  or accept that care cannot emerge from care=0.30 under mult<=1.60.")


if __name__ == "__main__":
    main()
