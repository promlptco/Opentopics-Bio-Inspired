import sys, os, argparse, random, json
import numpy as np
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from datetime import datetime
from itertools import product

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, PROJECT_ROOT)

from config import Config
from simulation.world import GridWorld
from agents.mother import MotherAgent, softmax_probs
from evolution.genome import Genome
from utils.experiment import set_seed


# ============================================================
# Easy-to-edit experiment constants
# ============================================================

INIT_MOTHERS = 15
INITIAL_ENERGY = 0.75
VALIDATION_SEEDS = list(range(42, 47))

DEFAULT_PERCEPTION_RADIUS = 30
DEFAULT_SWEEP_SEED_BASE = 42000

TAIL_WINDOW = 200

SELECTION_TARGETS = {
    "balanced": {
        "min_final_pop": 14.0,
        "energy_low": 0.70,
        "energy_high": 0.78,
        "target_energy": 0.725,
        "max_tail_sd": 0.08,
    },
    "easy": {
        "min_final_pop": 14.5,
        "min_energy": 0.90,
        "sd_penalty": 0.20,
    },
    "harsh": {
        "min_final_pop": 1.0,
        "max_final_pop": 5.0,
        "energy_low": 0.05,
        "energy_high": 0.40,
        "target_pop": 3.0,
        "target_energy": 0.25,
        "sd_penalty": 0.25,
    },
}


class SurvivalSimulation:
    def __init__(self, config, tau=0.1, food_mult=1.0, perceptual_noise=0.1):
        self.config = config
        self.tau = tau
        self.food_mult = food_mult
        self.perceptual_noise = perceptual_noise
        self.world = GridWorld(config.width, config.height)
        self.mothers = []
        self.tick = 0
        self.energy_history = []
        self.population_history = []
        self.action_counts = {"MOVE": 0, "EAT": 0, "REST": 0, "PICK": 0}

    def initialize(self):
        food_count = int(self.config.init_food * self.food_mult)

        for i in range(self.config.init_mothers):
            x, y = self._random_free_pos()
            genome = Genome(
                care_weight=0.0,
                forage_weight=0.85,
                self_weight=0.15,
                learning_rate=0.0,
                learning_cost=0.0,
            )
            mother = MotherAgent(x, y, lineage_id=i, generation=0, genome=genome)
            mother.energy = self.config.initial_energy
            self.mothers.append(mother)
            self.world.place_entity(mother)

        self._spawn_food(food_count)

    def _random_free_pos(self):
        for _ in range(200):
            x = random.randint(0, self.config.width - 1)
            y = random.randint(0, self.config.height - 1)
            if self.world.is_free((x, y)):
                return x, y
        return 0, 0

    def _spawn_food(self, count):
        spawned = 0
        for _ in range(count * 5):
            if spawned >= count:
                break
            x = random.randint(0, self.config.width - 1)
            y = random.randint(0, self.config.height - 1)
            if (x, y) not in self.world.food_positions:
                self.world.place_food(x, y)
                spawned += 1

    def _nearest_food(self, pos):
        if not self.world.food_positions:
            return None
        return min(self.world.food_positions, key=lambda f: self.world.get_distance(pos, f))

    def step(self):
        alive_mothers = [m for m in self.mothers if m.alive]
        random.shuffle(alive_mothers)

        for mother in alive_mothers:
            mother.tick_age()
            mother.energy = max(0.0, mother.energy - self.config.hunger_rate)

            perception_radius = getattr(self.config, "perception_radius", DEFAULT_PERCEPTION_RADIUS)

            nearest = self._nearest_food(mother.pos)
            dist_to_food = perception_radius

            if nearest:
                true_dist = self.world.get_distance(mother.pos, nearest)
                noisy_dist = max(0.0, true_dist + random.gauss(0.0, self.perceptual_noise))

                if noisy_dist <= perception_radius:
                    dist_to_food = noisy_dist
                else:
                    nearest = None

            u_forage = max(0.0, 1.0 - (dist_to_food / perception_radius))

            if mother.pos in self.world.food_positions:
                u_forage = 1.5

            if mother.held_food > 0:
                u_forage *= 0.1

            u_eat = 0.0
            if mother.held_food > 0:
                u_eat = 1.5 * (1.0 - mother.energy)

            u_rest = 0.8 * mother.fatigue

            scores = {"FORAGE": u_forage, "REST": u_rest, "EAT": u_eat}
            probs = softmax_probs(scores, tau=self.tau)
            selection = np.random.choice(list(probs.keys()), p=list(probs.values()))

            if selection == "EAT" and mother.held_food > 0:
                variance = random.uniform(0.8, 1.2)
                mother.energy = min(1.0, mother.energy + self.config.eat_gain * variance)
                mother.held_food -= 1
                self.action_counts["EAT"] += 1

            elif selection == "REST":
                mother.fatigue = max(0.0, mother.fatigue - self.config.rest_recovery)
                self.action_counts["REST"] += 1

            elif selection == "FORAGE":
                if mother.pos in self.world.food_positions:
                    self.world.remove_food(*mother.pos)
                    mother.held_food += 1
                    self.action_counts["PICK"] += 1
                elif nearest:
                    new_pos = self.world.get_step_toward(mother.pos, nearest)
                    if self.world.update_position(mother, new_pos):
                        mother.energy = max(0.0, mother.energy - self.config.move_cost)
                        mother.fatigue = min(1.0, mother.fatigue + self.config.fatigue_rate)
                        self.action_counts["MOVE"] += 1

            if mother.energy <= 0:
                mother.die()
                self.world.remove_entity(mother.id)

        target = int(self.config.init_food * self.food_mult)
        if len(self.world.food_positions) < max(1, target // 3):
            self._spawn_food(3)

        alive_now = [m for m in self.mothers if m.alive]
        self.population_history.append(len(alive_now))

        avg_e = sum(m.energy for m in alive_now) / len(alive_now) if alive_now else 0.0
        self.energy_history.append(avg_e)

    def run(self):
        self.initialize()

        for t in range(self.config.max_ticks):
            self.tick = t
            self.step()
            if not any(m.alive for m in self.mothers):
                break

        final_pop = sum(1 for m in self.mothers if m.alive)
        mean_energy = float(np.mean(self.energy_history)) if self.energy_history else 0.0
        final_energy = float(self.energy_history[-1]) if self.energy_history else 0.0

        return {
            "final_pop": final_pop,
            "mean_energy": mean_energy,
            "final_energy": final_energy,
            "energy_history": self.energy_history,
            "population_history": self.population_history,
            "actions": self.action_counts,
        }


def make_config(params, duration):
    cfg = Config()
    cfg.max_ticks = duration
    cfg.init_mothers = INIT_MOTHERS
    cfg.initial_energy = INITIAL_ENERGY

    cfg.perception_radius = params.get("perception_radius", DEFAULT_PERCEPTION_RADIUS)
    cfg.hunger_rate = params["hunger_rate"]
    cfg.move_cost = params["move_cost"]
    cfg.eat_gain = params["eat_gain"]
    cfg.init_food = params["init_food"]
    cfg.rest_recovery = params["rest_recovery"]

    return cfg


def candidate_configs(mode="sweep"):
    if mode == "single":
        return [
            {
                "perception_radius": DEFAULT_PERCEPTION_RADIUS,
                "hunger_rate": 0.005,
                "move_cost": 0.001,
                "eat_gain": 0.07,
                "init_food": 60,
                "rest_recovery": 0.005,
                "name": "single_test",
            }
        ]

    grid = {
        "perception_radius": [DEFAULT_PERCEPTION_RADIUS],
        "hunger_rate": [0.005],
        "move_cost": [0.001],
        "eat_gain": [0.07],
        "init_food": [20, 25, 30, 35, 40, 43, 45, 48, 50, 53, 55, 60, 65, 70, 75, 80],
        "rest_recovery": [0.005, 0.01, 0.015, 0.02, 0.025, 0.03, 0.035, 0.04, 0.045, 0.05, 0.06, 0.08, 0.10],
    }

    keys = list(grid.keys())
    configs = []

    for values in product(*[grid[k] for k in keys]):
        params = dict(zip(keys, values))
        params["name"] = "candidate"
        configs.append(params)

    return configs


def run_one(params, seed, duration, tau, noise):
    set_seed(seed)
    cfg = make_config(params, duration)
    sim = SurvivalSimulation(cfg, tau=tau, perceptual_noise=noise)
    return sim.run()


def pad(x, duration):
    arr = np.full(duration, np.nan)
    x = np.asarray(x, dtype=float)
    arr[: min(duration, len(x))] = x[:duration]
    return arr


def summarize_repeats(repeat_results, duration, tail_window=TAIL_WINDOW):
    final_pops = np.array([r["final_pop"] for r in repeat_results], dtype=float)
    mean_es = np.array([r["mean_energy"] for r in repeat_results], dtype=float)
    final_es = np.array([r["final_energy"] for r in repeat_results], dtype=float)

    tail_means = []
    for r in repeat_results:
        e = pad(r["energy_history"], duration)
        e = np.nan_to_num(e, nan=0.0)
        tail_means.append(np.mean(e[-tail_window:]))

    tail_means = np.array(tail_means, dtype=float)

    return {
        "final_pop": float(np.mean(final_pops)),
        "final_pop_sd": float(np.std(final_pops)),
        "mean_energy": float(np.mean(mean_es)),
        "final_energy": float(np.mean(final_es)),
        "tail_mean_energy": float(np.mean(tail_means)),
        "tail_energy_sd": float(np.std(tail_means)),
    }


def _safe(value, nan=0.0):
    return float(np.nan_to_num(value, nan=nan))


def _config_title(params):
    return (
        f"perception={params.get('perception_radius', DEFAULT_PERCEPTION_RADIUS)} | "
        f"hunger={params['hunger_rate']} | move={params['move_cost']} | "
        f"eat={params['eat_gain']} | food={params['init_food']} | rest={params['rest_recovery']}"
    )


def is_balanced_valid(summary_result):
    b = SELECTION_TARGETS["balanced"]
    return (
        summary_result["final_pop"] >= b["min_final_pop"]
        and b["energy_low"] <= _safe(summary_result["tail_mean_energy"]) <= b["energy_high"]
        and _safe(summary_result["tail_energy_sd"], nan=1.0) <= b["max_tail_sd"]
    )


def balanced_validation_sort_key(record):
    b = SELECTION_TARGETS["balanced"]
    result = record["result"]
    params = record["params"]

    return (
        params["init_food"],
        abs(_safe(result["tail_mean_energy"]) - b["target_energy"]),
        _safe(result["tail_energy_sd"], nan=1.0),
        abs(result["final_pop"] - INIT_MOTHERS),
        params["rest_recovery"],
    )


def balanced_fallback_sort_key(record):
    b = SELECTION_TARGETS["balanced"]
    result = record["result"]
    params = record["params"]

    pop_gap = max(0.0, b["min_final_pop"] - result["final_pop"])

    return (
        pop_gap,
        params["init_food"],
        abs(_safe(result["tail_mean_energy"]) - b["target_energy"]),
        _safe(result["tail_energy_sd"], nan=1.0),
        abs(result["final_pop"] - INIT_MOTHERS),
    )


def validate_condition(params, args):
    results = []
    result_tags = []

    for seed in VALIDATION_SEEDS:
        for rep in range(args.repeats):
            run_seed = seed * 1000 + rep

            result = run_one(
                params,
                run_seed,
                args.duration,
                args.tau,
                args.perceptual_noise,
            )

            result["base_seed"] = seed
            result["repeat"] = rep + 1
            result["run_seed"] = run_seed

            results.append(result)
            result_tags.append(f"{seed}-r{rep + 1}")

    validation_summary = summarize_repeats(results, args.duration)

    return results, result_tags, validation_summary


def select_easy_and_harsh_from_sweep(sweep_records):
    e = SELECTION_TARGETS["easy"]
    h = SELECTION_TARGETS["harsh"]

    easy_pool = [
        r
        for r in sweep_records
        if r["result"]["final_pop"] >= e["min_final_pop"]
        and _safe(r["result"]["tail_mean_energy"]) >= e["min_energy"]
    ]

    if easy_pool:
        easy = max(
            easy_pool,
            key=lambda r: (
                _safe(r["result"]["tail_mean_energy"])
                - _safe(r["result"]["tail_energy_sd"]) * e["sd_penalty"],
                r["params"]["init_food"],
            ),
        )
    else:
        easy = min(
            sweep_records,
            key=lambda r: (
                abs(_safe(r["result"]["tail_mean_energy"]) - 0.95),
                abs(r["result"]["final_pop"] - INIT_MOTHERS) * 0.20,
            ),
        )

    harsh_pool = [
        r
        for r in sweep_records
        if h["min_final_pop"] <= r["result"]["final_pop"] <= h["max_final_pop"]
        and h["energy_low"] <= _safe(r["result"]["tail_mean_energy"]) <= h["energy_high"]
    ]

    if harsh_pool:
        harsh = min(
            harsh_pool,
            key=lambda r: (
                abs(r["result"]["final_pop"] - h["target_pop"]),
                abs(_safe(r["result"]["tail_mean_energy"]) - h["target_energy"]),
                _safe(r["result"]["tail_energy_sd"], nan=1.0) * h["sd_penalty"],
                r["params"]["init_food"],
            ),
        )
    else:
        non_extinct_pool = [r for r in sweep_records if r["result"]["final_pop"] > 0.0]
        pool = non_extinct_pool if non_extinct_pool else sweep_records

        harsh = min(
            pool,
            key=lambda r: (
                abs(r["result"]["final_pop"] - h["target_pop"]),
                abs(_safe(r["result"]["tail_mean_energy"]) - h["target_energy"]),
                r["params"]["init_food"],
            ),
        )

    harsh["params"]["name"] = "harsh"
    easy["params"]["name"] = "easy"

    return {"harsh": harsh, "easy": easy}


def build_balanced_validation_pool(sweep_records):
    """
    Balanced is intentionally selected by validation, not by sweep only.

    Policy:
    1. Candidate must first look plausible in sweep.
    2. Then each candidate is re-tested using validation seeds.
    3. The first validation-passing candidate after sorting is selected.

    Sort order:
    - lowest init_food first
    - then closest energy target
    - then lower energy SD
    - then closer final population to 15
    """
    b = SELECTION_TARGETS["balanced"]

    strict_pool = [
        r
        for r in sweep_records
        if r["result"]["final_pop"] >= b["min_final_pop"]
        and b["energy_low"] <= _safe(r["result"]["tail_mean_energy"]) <= b["energy_high"]
        and _safe(r["result"]["tail_energy_sd"], nan=1.0) <= b["max_tail_sd"]
    ]

    if strict_pool:
        return sorted(strict_pool, key=balanced_validation_sort_key)

    relaxed_pool = [
        r
        for r in sweep_records
        if r["result"]["final_pop"] >= b["min_final_pop"] - 1.0
        and b["energy_low"] - 0.05 <= _safe(r["result"]["tail_mean_energy"]) <= b["energy_high"] + 0.05
    ]

    if relaxed_pool:
        return sorted(relaxed_pool, key=balanced_validation_sort_key)

    return sorted(sweep_records, key=balanced_fallback_sort_key)


def select_balanced_by_validation(sweep_records, args):
    validation_pool = build_balanced_validation_pool(sweep_records)

    print("\nSelecting BALANCED using validation-first rule:")
    print("Rule: final_pop >= 14/15 first, then lowest init_food.")

    best_fallback = None
    validated_records = []

    for idx, rec in enumerate(validation_pool, start=1):
        params = dict(rec["params"])
        params["name"] = "balanced"

        results, tags, validation_summary = validate_condition(params, args)

        candidate_record = {
            "params": params,
            "result": validation_summary,
            "sweep_summary": rec["result"],
            "full_result": results[0],
            "validation_results": results,
            "validation_tags": tags,
            "selection_status": "validated_pass" if is_balanced_valid(validation_summary) else "validated_fail",
        }

        validated_records.append(candidate_record)

        print(
            f"  BALANCED candidate {idx:03d}/{len(validation_pool)} | "
            f"food={params['init_food']} | rest={params['rest_recovery']} | "
            f"val_pop={validation_summary['final_pop']:.2f}/15 | "
            f"tailE={validation_summary['tail_mean_energy']:.3f} ± {validation_summary['tail_energy_sd']:.3f}"
        )

        if best_fallback is None or balanced_fallback_sort_key(candidate_record) < balanced_fallback_sort_key(best_fallback):
            best_fallback = candidate_record

        if is_balanced_valid(validation_summary):
            print("  -> BALANCED selected from validation PASS.")
            return candidate_record, validated_records

    print("\nWARNING: No BALANCED candidate passed strict validation.")
    print("Fallback selected by closest validation result. Check summary JSON before reporting.")

    best_fallback["params"]["name"] = "balanced"
    best_fallback["selection_status"] = "fallback_no_strict_validation_pass"

    return best_fallback, validated_records


def plot_single_condition(name, result, params, seed, duration, out_dir):
    ticks = np.arange(duration)
    e = np.nan_to_num(pad(result["energy_history"], duration), nan=0.0)
    p = np.nan_to_num(pad(result["population_history"], duration), nan=0.0)

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(13, 7), sharex=True)

    fig.suptitle(
        f"Phase 2 Baseline Sweep — {name.upper()}\n"
        f"Seed {seed} | {_config_title(params)}",
        fontsize=14,
        fontweight="bold",
    )

    ax1.plot(ticks, e, color="black", linewidth=2, label="Mean energy")
    ax1.axhline(0.70, color="gray", linestyle=":", label="Target 0.70")
    ax1.axhline(0.75, color="gray", linestyle="--", alpha=0.6, label="Target 0.75")
    ax1.axhline(0.0, color="red", linestyle="--", alpha=0.5, label="Death")
    ax1.set_ylabel("Mean energy")
    ax1.set_ylim(-0.05, 1.05)
    ax1.set_title("Energy Trajectory")

    ax2.step(ticks, p, where="post", color="black", linewidth=2, label="Alive population")
    ax2.axhline(0.0, color="red", linestyle="--", alpha=0.5, label="Extinction")
    ax2.axhline(INIT_MOTHERS, color="gray", linestyle=":", label="Initial count")
    ax2.set_ylabel("# alive mothers")
    ax2.set_xlabel("Tick")
    ax2.set_ylim(-0.5, INIT_MOTHERS + 1.5)
    ax2.set_title("Alive Population")

    for ax in (ax1, ax2):
        ax.grid(True, linestyle="--", alpha=0.25)
        ax.legend(loc="lower right", fontsize=8)

    plt.tight_layout()
    fig.savefig(os.path.join(out_dir, f"sweep_{name}.png"), dpi=200, bbox_inches="tight")
    plt.close(fig)


def plot_multiseed_condition(name, results, params, run_labels, duration, out_dir):
    ticks = np.arange(duration)

    energy_matrix = np.asarray(
        [np.nan_to_num(pad(r["energy_history"], duration), nan=0.0) for r in results]
    )

    pop_matrix = np.asarray(
        [np.nan_to_num(pad(r["population_history"], duration), nan=0.0) for r in results]
    )

    mean_e = np.mean(energy_matrix, axis=0)
    std_e = np.std(energy_matrix, axis=0)

    mean_p = np.mean(pop_matrix, axis=0)
    std_p = np.std(pop_matrix, axis=0)

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(13, 7), sharex=True)

    fig.suptitle(
        f"Phase 2 Multi-Seed Validation — {name.upper()}\n"
        f"Runs: {len(results)} total | {_config_title(params)}",
        fontsize=14,
        fontweight="bold",
    )

    for i, _label in enumerate(run_labels):
        label = "Individual Runs" if i == 0 else "_nolegend_"
        ax1.plot(ticks, energy_matrix[i], alpha=0.15, linewidth=0.8, color="gray", label=label)
        ax2.step(ticks, pop_matrix[i], where="post", alpha=0.15, linewidth=0.8, color="gray", label=label)

    ax1.fill_between(ticks, mean_e - std_e, mean_e + std_e, color="blue", alpha=0.15, label="Mean ± SD")
    ax1.plot(ticks, mean_e, color="blue", linewidth=2.0, label="Group Mean")

    ax2.fill_between(ticks, mean_p - std_p, mean_p + std_p, color="green", alpha=0.15, label="Mean ± SD")
    ax2.plot(ticks, mean_p, color="green", linewidth=2.0, label="Group Mean")

    ax1.axhline(0.70, color="gray", linestyle=":", label="Target 0.70")
    ax1.axhline(0.75, color="gray", linestyle="--", alpha=0.6, label="Target 0.75")
    ax1.axhline(0.0, color="red", linestyle="--", alpha=0.5, label="Death")

    ax2.axhline(0.0, color="red", linestyle="--", alpha=0.5, label="Extinction")
    ax2.axhline(INIT_MOTHERS, color="gray", linestyle=":", label="Initial count")

    ax1.set_title("Energy Trajectory: Mean ± SD")
    ax1.set_ylabel("Mean energy")
    ax1.set_ylim(-0.05, 1.05)

    ax2.set_title("Alive Population: Mean ± SD")
    ax2.set_ylabel("# alive mothers")
    ax2.set_xlabel("Tick")
    ax2.set_ylim(-0.5, INIT_MOTHERS + 1.5)

    summary = (
        f"final alive mean = {np.mean(pop_matrix[:, -1]):.2f}/15\n"
        f"final energy mean = {mean_e[-1]:.3f}\n"
        f"final energy SD = {std_e[-1]:.3f}"
    )

    ax1.text(
        0.01,
        0.04,
        summary,
        transform=ax1.transAxes,
        fontsize=9,
        bbox=dict(facecolor="white", edgecolor="gray", alpha=0.85),
    )

    for ax in (ax1, ax2):
        ax.grid(True, linestyle="--", alpha=0.25)
        ax.legend(loc="lower right", fontsize=7)

    plt.tight_layout()
    fig.savefig(os.path.join(out_dir, f"validation_{name}.png"), dpi=200, bbox_inches="tight")
    plt.close(fig)


def print_validation_runs(name, results):
    for result in results:
        print(
            f"{name.upper()} seed {result['base_seed']} repeat {result['repeat']}: "
            f"run_seed={result['run_seed']} | "
            f"pop={result['final_pop']}/15 | "
            f"meanE={result['mean_energy']:.3f} | "
            f"finalE={result['final_energy']:.3f}"
        )


def run_experiment(args):
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir = os.path.join(
        PROJECT_ROOT,
        "outputs",
        "phase2_survival_minimal",
        f"{ts}_auto_baseline_calibration",
    )
    os.makedirs(out_dir, exist_ok=True)

    print(f"Phase 2 Baseline Calibration - Mode: {args.mode}")
    print(f"Output dir: {out_dir}")
    print(f"Duration: {args.duration} | Tau: {args.tau}")
    print(f"Perceptual noise: {args.perceptual_noise}")
    print(f"Repeats: {args.repeats}")

    balanced_validated_records = []

    if args.mode == "sweep":
        configs = candidate_configs(mode="sweep")
        sweep_records = []

        print(f"\nStep 1: Auto sweep | Total configs: {len(configs)}")
        print(f"Total sweep runs: {len(configs) * args.repeats}")

        for idx, params in enumerate(configs, start=1):
            repeat_results = []

            for rep in range(args.repeats):
                sweep_run_seed = DEFAULT_SWEEP_SEED_BASE + rep
                res = run_one(params, sweep_run_seed, args.duration, args.tau, args.perceptual_noise)
                repeat_results.append(res)

            summary_result = summarize_repeats(repeat_results, args.duration)

            record = {
                "params": dict(params),
                "result": summary_result,
                "full_result": repeat_results[0],
            }
            sweep_records.append(record)

            if idx % 20 == 0 or idx == len(configs):
                print(
                    f"  [{idx:03d}/{len(configs)}] "
                    f"avg_pop={summary_result['final_pop']:4.1f}/15 | "
                    f"tailE={summary_result['tail_mean_energy']:.3f} ± "
                    f"{summary_result['tail_energy_sd']:.3f}"
                )

        selected = select_easy_and_harsh_from_sweep(sweep_records)

        balanced_rec, balanced_validated_records = select_balanced_by_validation(sweep_records, args)
        selected["balanced"] = balanced_rec

        print("\nSelected conditions:")
        for name, rec in selected.items():
            print(f"{name.upper()}: {rec['result']} | config={rec['params']}")

            if name != "balanced":
                plot_single_condition(
                    name,
                    rec["full_result"],
                    rec["params"],
                    seed=DEFAULT_SWEEP_SEED_BASE,
                    duration=args.duration,
                    out_dir=out_dir,
                )

    else:
        single_config = candidate_configs(mode="single")[0]
        selected = {
            "single": {
                "params": single_config,
                "result": {},
                "full_result": None,
                "selection_status": "single_mode",
            }
        }
        print(f"\nRunning single configuration: {single_config}")

    print("\nStep 2: Multi-seed validation")

    summary = {}

    for name, rec in selected.items():
        params = rec["params"]

        if name == "balanced" and "validation_results" in rec:
            results = rec["validation_results"]
            result_tags = rec["validation_tags"]
            validation_summary = rec["result"]
            print("\nBALANCED validation already completed during selection. Reusing cached validation results.")
            print_validation_runs(name, results)
        else:
            results, result_tags, validation_summary = validate_condition(params, args)
            print_validation_runs(name, results)

        plot_multiseed_condition(
            name,
            results,
            params,
            result_tags,
            args.duration,
            out_dir,
        )

        summary[name] = {
            "selected_config": params,
            "selection_status": rec.get("selection_status", "selected"),
            "sweep_summary": rec.get("sweep_summary", rec.get("result", {})),
            "validation_summary": validation_summary,
            "validation_42_46": [
                {
                    "seed": res["base_seed"],
                    "repeat": res["repeat"],
                    "run_seed": res["run_seed"],
                    "final_pop": res["final_pop"],
                    "mean_energy": res["mean_energy"],
                    "final_energy": res["final_energy"],
                }
                for res in results
            ],
        }

    if balanced_validated_records:
        summary["_balanced_candidate_validation_trace"] = [
            {
                "selected_config": rec["params"],
                "selection_status": rec["selection_status"],
                "sweep_summary": rec["sweep_summary"],
                "validation_summary": rec["result"],
            }
            for rec in balanced_validated_records
        ]

    with open(os.path.join(out_dir, "auto_baseline_summary.json"), "w") as f:
        json.dump(summary, f, indent=2)

    print(f"\nDone. Outputs saved to: {out_dir}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--duration", type=int, default=1000)
    parser.add_argument("--tau", type=float, default=0.1)
    parser.add_argument("--perceptual_noise", type=float, default=0.1)
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--mode", type=str, choices=["sweep", "single"], default="sweep")
    args = parser.parse_args()

    run_experiment(args)