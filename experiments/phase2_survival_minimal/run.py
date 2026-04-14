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

            nearest = self._nearest_food(mother.pos)
            dist_to_food = 30.0

            if nearest:
                dist_to_food = self.world.get_distance(mother.pos, nearest)

                # Perceptual noise prevents the foraging policy from being perfectly deterministic.
                dist_to_food += random.gauss(0.0, self.perceptual_noise)
                dist_to_food = max(0.0, dist_to_food)

            u_forage = max(0.0, 1.0 - (dist_to_food / 30.0))

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
                # Foraging variance keeps food reward stochastic but bounded.
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
    cfg.init_mothers = 15
    cfg.initial_energy = 0.75
    cfg.hunger_rate = params["hunger_rate"]
    cfg.move_cost = params["move_cost"]
    cfg.eat_gain = params["eat_gain"]
    cfg.init_food = params["init_food"]
    cfg.rest_recovery = params["rest_recovery"]
    return cfg


def candidate_configs(mode="sweep"):
    if mode == "single":
        return [{
            "hunger_rate": 0.005,
            "move_cost": 0.0025,
            "eat_gain": 0.075,
            "init_food": 60,
            "rest_recovery": 0.04,
            "name": "single_test",
        }]

    grid = {
        "hunger_rate":   [0.004, 0.005, 0.012],
        "move_cost":     [0.002, 0.0018, 0.008],
        "eat_gain":      [0.15, 0.07, 0.25],
        "init_food":     [30, 55, 90],
        "rest_recovery": [0.02, 0.05, 0.10],
    }

    configs = []
    keys = list(grid.keys())

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
    arr[:min(duration, len(x))] = x[:duration]
    return arr


def summarize_repeats(repeat_results, duration, tail_window=200):
    """
    Summarize repeated runs for one config.

    Important change:
    We use tail_mean_energy instead of whole-episode mean_energy for selection.
    Whole-episode mean can be misleading because initial_energy = 0.75 can bias the average.
    Tail mean better reflects whether the ecology stabilizes near the target energy.
    """
    final_pops = np.array([r["final_pop"] for r in repeat_results], dtype=float)
    mean_es = np.array([r["mean_energy"] for r in repeat_results], dtype=float)
    final_es = np.array([r["final_energy"] for r in repeat_results], dtype=float)

    tail_means = []
    for r in repeat_results:
        e = pad(r["energy_history"], duration)
        tail_e = e[-tail_window:]
        tail_means.append(np.nanmean(tail_e))

    tail_means = np.array(tail_means, dtype=float)

    return {
        "final_pop": float(np.mean(final_pops)),
        "final_pop_sd": float(np.std(final_pops)),
        "mean_energy": float(np.mean(mean_es)),
        "final_energy": float(np.mean(final_es)),
        "tail_mean_energy": float(np.mean(tail_means)),
        "tail_energy_sd": float(np.std(tail_means)),
    }


def select_auto_conditions(sweep_records):
    """
    Automatically select Harsh, Balanced, and Easy configs.

    Important change:
    Selection is based mainly on tail_mean_energy and repeat stability,
    not only on mean_energy across the full episode.
    """

    balanced_pool = [
        r for r in sweep_records
        if r["result"]["final_pop"] >= 14.5
        and 0.70 <= r["result"]["tail_mean_energy"] <= 0.75
        and r["result"]["tail_energy_sd"] <= 0.08
    ]

    if balanced_pool:
        balanced = min(
            balanced_pool,
            key=lambda r: (
                abs(r["result"]["tail_mean_energy"] - 0.725)
                + r["result"]["tail_energy_sd"]
                + r["result"]["final_pop_sd"] * 0.05
            )
        )
    else:
        balanced = min(
            sweep_records,
            key=lambda r: (
                abs(r["result"]["tail_mean_energy"] - 0.725)
                + abs(r["result"]["final_pop"] - 15.0) * 0.2
                + r["result"]["tail_energy_sd"]
            )
        )

    easy_pool = [
        r for r in sweep_records
        if r["result"]["final_pop"] >= 14.5
        and r["result"]["tail_mean_energy"] >= 0.90
    ]

    if easy_pool:
        easy = max(
            easy_pool,
            key=lambda r: (
                r["result"]["tail_mean_energy"]
                - r["result"]["tail_energy_sd"] * 0.2
            )
        )
    else:
        easy = min(
            sweep_records,
            key=lambda r: (
                abs(r["result"]["tail_mean_energy"] - 0.95)
                + abs(r["result"]["final_pop"] - 15.0) * 0.2
            )
        )

    harsh_pool = [
        r for r in sweep_records
        if r["result"]["final_pop"] <= 2.0
        or r["result"]["tail_mean_energy"] <= 0.10
    ]

    if harsh_pool:
        harsh = min(
            harsh_pool,
            key=lambda r: (
                r["result"]["final_pop"]
                + r["result"]["tail_mean_energy"]
            )
        )
    else:
        harsh = min(
            sweep_records,
            key=lambda r: (
                r["result"]["final_pop"]
                + r["result"]["tail_mean_energy"]
            )
        )

    harsh["params"]["name"] = "harsh"
    balanced["params"]["name"] = "balanced"
    easy["params"]["name"] = "easy"

    return {
        "harsh": harsh,
        "balanced": balanced,
        "easy": easy,
    }


def plot_single_condition(name, result, params, seed, duration, out_dir):
    ticks = np.arange(duration)
    e = pad(result["energy_history"], duration)
    p = pad(result["population_history"], duration)

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(13, 7), sharex=True)

    fig.suptitle(
        f"Phase 2 Baseline Sweep — {name.upper()}\n"
        f"Seed {seed} | hunger={params['hunger_rate']} | move={params['move_cost']} | "
        f"eat={params['eat_gain']} | food={params['init_food']} | rest={params['rest_recovery']}",
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
    ax2.axhline(15, color="gray", linestyle=":", label="Initial count")
    ax2.set_ylabel("# alive mothers")
    ax2.set_xlabel("Tick")
    ax2.set_ylim(-0.5, 16.5)
    ax2.set_title("Alive Population")

    for ax in (ax1, ax2):
        ax.grid(True, linestyle="--", alpha=0.25)
        ax.legend(loc="lower right", fontsize=8)

    plt.tight_layout()
    fig.savefig(os.path.join(out_dir, f"sweep_{name}.png"), dpi=200, bbox_inches="tight")
    plt.close(fig)


def plot_multiseed_condition(name, results, params, run_labels, duration, out_dir):
    ticks = np.arange(duration)

    energy_matrix = np.asarray([pad(r["energy_history"], duration) for r in results])
    pop_matrix = np.asarray([pad(r["population_history"], duration) for r in results])

    mean_e = np.nanmean(energy_matrix, axis=0)
    std_e = np.nanstd(energy_matrix, axis=0)

    mean_p = np.nanmean(pop_matrix, axis=0)
    std_p = np.nanstd(pop_matrix, axis=0)

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(13, 7), sharex=True)

    fig.suptitle(
        f"Phase 2 Multi-Seed Validation — {name.upper()}\n"
        f"Runs: {len(results)} total | hunger={params['hunger_rate']} | move={params['move_cost']} | "
        f"eat={params['eat_gain']} | food={params['init_food']} | rest={params['rest_recovery']}",
        fontsize=14,
        fontweight="bold",
    )

    for i, label in enumerate(run_labels):
        l = "Individual Runs" if i == 0 else "_nolegend_"
        ax1.plot(ticks, energy_matrix[i], alpha=0.15, linewidth=0.8, color="gray", label=l)
        ax2.step(ticks, pop_matrix[i], where="post", alpha=0.15, linewidth=0.8, color="gray", label=l)

    ax1.fill_between(ticks, mean_e - std_e, mean_e + std_e, color="blue", alpha=0.15, label="Mean ± SD")
    ax1.plot(ticks, mean_e, color="blue", linewidth=2.0, label="Group Mean")

    ax2.fill_between(ticks, mean_p - std_p, mean_p + std_p, color="green", alpha=0.15, label="Mean ± SD")
    ax2.plot(ticks, mean_p, color="green", linewidth=2.0, label="Group Mean")

    ax1.axhline(0.70, color="gray", linestyle=":", label="Target 0.70")
    ax1.axhline(0.75, color="gray", linestyle="--", alpha=0.6, label="Target 0.75")
    ax1.axhline(0.0, color="red", linestyle="--", alpha=0.5, label="Death")

    ax2.axhline(0.0, color="red", linestyle="--", alpha=0.5, label="Extinction")
    ax2.axhline(15, color="gray", linestyle=":", label="Initial count")

    ax1.set_title("Energy Trajectory: Mean ± SD")
    ax1.set_ylabel("Mean energy")
    ax1.set_ylim(-0.05, 1.05)

    ax2.set_title("Alive Population: Mean ± SD")
    ax2.set_ylabel("# alive mothers")
    ax2.set_xlabel("Tick")
    ax2.set_ylim(-0.5, 16.5)

    summary = (
        f"final alive mean = {np.nanmean(pop_matrix[:, -1]):.2f}/15\n"
        f"final energy mean = {mean_e[-1]:.3f}\n"
        f"final energy SD = {std_e[-1]:.3f}"
    )

    ax1.text(
        0.01, 0.04, summary,
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


def run_experiment(args):
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir = os.path.join(
        PROJECT_ROOT,
        "outputs",
        "phase2_survival_minimal",
        f"{ts}_auto_baseline_calibration"
    )
    os.makedirs(out_dir, exist_ok=True)

    validation_seeds = list(range(42, 47))

    print(f"Phase 2 Baseline Calibration - Mode: {args.mode}")
    print(f"Output dir: {out_dir}")
    print(f"Duration: {args.duration} | Tau: {args.tau}")
    print(f"Perceptual noise: {args.perceptual_noise}")
    print(f"Repeats: {args.repeats}")

    if args.mode == "sweep":
        configs = candidate_configs(mode="sweep")
        sweep_records = []
        print(f"\nStep 1: Auto sweep | Total configs: {len(configs)}")
        print(f"Total sweep runs: {len(configs) * args.repeats}")

        for idx, params in enumerate(configs, start=1):
            repeat_results = []

            for rep in range(args.repeats):
                # Repeat seeds are deterministic and reproducible.
                sweep_run_seed = 42000 + rep
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
                    f"tailE={summary_result['tail_mean_energy']:.3f} ± {summary_result['tail_energy_sd']:.3f}"
                )

        selected = select_auto_conditions(sweep_records)

        print("\nSelected conditions:")
        for name, rec in selected.items():
            print(f"{name.upper()}: {rec['result']} | config={rec['params']}")

            plot_single_condition(
                name,
                rec["full_result"],
                rec["params"],
                seed=42000,
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
            }
        }
        print(f"\nRunning single configuration: {single_config}")

    print("\nStep 2: Multi-seed validation")

    summary = {}

    for name, rec in selected.items():
        params = rec["params"]
        results = []
        result_tags = []

        for seed in validation_seeds:
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

                print(
                    f"{name.upper()} seed {seed} repeat {rep + 1}: "
                    f"run_seed={run_seed} | "
                    f"pop={result['final_pop']}/15 | "
                    f"meanE={result['mean_energy']:.3f} | "
                    f"finalE={result['final_energy']:.3f}"
                )

        plot_multiseed_condition(
            name,
            results,
            params,
            result_tags,
            args.duration,
            out_dir,
        )

        validation_summary = summarize_repeats(results, args.duration)

        summary[name] = {
            "selected_config": params,
            "sweep_summary": rec["result"],
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