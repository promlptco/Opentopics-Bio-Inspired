# experiments/phase2_survival_minimal/run.py
"""
Phase 2: Survival Minimal - Stochastic Stress Test

Verifies the stability of the foraging loop under stochastic decision making (Softmax)
and environmental pressure (Food Scarcity).

Required Plots:
  - Energy Trajectory: Mean ± SD band for Normal vs Stress groups.
  - Survival Curves: Kaplan-Meier style % alive over time.
  - Action Distribution: Verification of Softmax behavior.
  - Energy Histogram: Snapshot at T=500 to check centering around 0.70.
"""
import sys
import os
import argparse
import csv
import json
import random
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from datetime import datetime
from scipy.stats import norm

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, PROJECT_ROOT)

from config import Config
from simulation.world import GridWorld
from agents.mother import MotherAgent, softmax_probs
from evolution.genome import Genome
from utils.experiment import set_seed

# ── Simulation ──────────────────────────────────────────────────────────────

class SurvivalSimulation:
    def __init__(self, config: Config, tau: float = 0.1, food_mult: float = 1.0):
        self.config = config
        self.tau = tau
        self.food_mult = food_mult
        self.world = GridWorld(config.width, config.height)
        self.mothers: list[MotherAgent] = []
        self.tick = 0

        # Histories
        self.energy_history = []
        self.population_history = []
        self.action_counts = {"MOVE": 0, "EAT": 0, "REST": 0, "PICK": 0}
        self.snapshot_energy_t500 = []

    def initialize(self):
        # Scale food density
        food_count = int(self.config.init_food * self.food_mult)
        
        for i in range(self.config.init_mothers):
            x, y = self._random_free_pos()
            # Fixed genome for survival test
            genome = Genome(care_weight=0.0, forage_weight=0.85, self_weight=0.15, learning_rate=0.0, learning_cost=0.0)
            mother = MotherAgent(x, y, lineage_id=i, generation=0, genome=genome)
            mother.energy = self.config.initial_energy
            self.mothers.append(mother)
            self.world.place_entity(mother)
        
        self._spawn_food(food_count)

    def _random_free_pos(self):
        for _ in range(200):
            x, y = random.randint(0, self.config.width-1), random.randint(0, self.config.height-1)
            if self.world.is_free((x, y)): return x, y
        return 0, 0

    def _spawn_food(self, count):
        spawned = 0
        for _ in range(count * 4):
            if spawned >= count: break
            x, y = random.randint(0, self.config.width-1), random.randint(0, self.config.height-1)
            if (x, y) not in self.world.food_positions:
                self.world.place_food(x, y)
                spawned += 1

    def step(self):
        alive_mothers = [m for m in self.mothers if m.alive]
        random.shuffle(alive_mothers)

        for mother in alive_mothers:
            mother.tick_age()
            mother.energy = max(0.0, mother.energy - self.config.hunger_rate)

            # --- Softmax Action Selection ---
            dist_to_food = 30.0
            nearest = self._nearest_food(mother.pos)
            if nearest:
                dist_to_food = self.world.get_distance(mother.pos, nearest)
            
            # If on food, FORAGE is extremely high (PICK action)
            # If not on food, FORAGE utility scales with proximity
            u_forage = 1.0 - (dist_to_food / 30.0)
            if mother.pos in self.world.food_positions:
                u_forage = 1.5 # Extra incentive to pick up what's right there
            
            # If already carrying food, forage utility drops significantly
            if mother.held_food > 0:
                u_forage *= 0.1

            # Eat utility scales with hunger and is only available if holding food
            u_eat = 0.0
            if mother.held_food > 0:
                u_eat = 1.5 * (1.0 - mother.energy) # High priority when energy is low
            
            # Rest utility scales with fatigue
            u_rest = 0.8 * mother.fatigue

            scores = {"FORAGE": u_forage, "REST": u_rest, "EAT": u_eat}
            probs = softmax_probs(scores, tau=self.tau)
            
            selection = np.random.choice(list(probs.keys()), p=list(probs.values()))
            
            # Execute
            if selection == "EAT" and mother.held_food > 0:
                # Foraging Variance: +/- 20%
                variance = random.uniform(0.8, 1.2)
                mother.energy = min(1.0, mother.energy + (self.config.eat_gain * variance))
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
                        mother.energy -= self.config.move_cost
                        mother.fatigue = min(1.0, mother.fatigue + self.config.fatigue_rate)
                        self.action_counts["MOVE"] += 1

            if mother.energy <= 0:
                mother.die()
                self.world.remove_entity(mother.id)

        # Replenish food
        food_target = int(self.config.init_food * self.food_mult)
        if len(self.world.food_positions) < food_target // 2:
            self._spawn_food(5)

        # Recording
        alive_now = [m for m in self.mothers if m.alive]
        self.population_history.append(len(alive_now))
        avg_e = sum(m.energy for m in alive_now) / len(alive_now) if alive_now else 0.0
        self.energy_history.append(avg_e)
        
        if self.tick == 500:
            self.snapshot_energy_t500 = [m.energy for m in alive_now]

    def _nearest_food(self, pos):
        if not self.world.food_positions: return None
        return min(self.world.food_positions, key=lambda f: self.world.get_distance(pos, f))

    def run(self):
        self.initialize()
        for t in range(self.config.max_ticks):
            self.tick = t
            self.step()
            if not any(m.alive for m in self.mothers): break
        return {
            "passed": any(m.alive for m in self.mothers),
            "final_pop": sum(1 for m in self.mothers if m.alive),
            "avg_energy": np.mean(self.energy_history),
            "actions": self.action_counts
        }

# ── Experiment Runner ────────────────────────────────────────────────────────

def run_experiment(args):
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir = os.path.join(PROJECT_ROOT, "outputs", "phase2_survival_minimal", f"{ts}_stress_test")
    os.makedirs(out_dir, exist_ok=True)

    def parse_seeds(s):
        if "-" in s:
            start, end = map(int, s.split("-"))
            return list(range(start, end + 1))
        return [int(s)]

    normal_seeds = parse_seeds(args.seeds)
    stress_seeds = parse_seeds(args.stress_seeds)

    groups = {
        "Normal": {"seeds": normal_seeds, "food_mult": 1.0, "histories": [], "pops": [], "actions": [], "t500": []},
        "Stress": {"seeds": stress_seeds, "food_mult": 0.5, "histories": [], "pops": [], "actions": [], "t500": []}
    }

    print(f"Starting Phase 2 Stress Test at {ts}")
    print(f"Duration: {args.duration} ticks | Tau: {args.tau}")

    for g_name, data in groups.items():
        print(f"\nGroup: {g_name} (Food Density x{data['food_mult']})")
        for seed in data["seeds"]:
            set_seed(seed)
            cfg = Config()
            cfg.max_ticks = args.duration
            cfg.initial_energy = 0.85
            cfg.hunger_rate = 0.008    # Slightly faster drain
            cfg.init_food = 70         # Slightly less food
            cfg.init_mothers = 15
            cfg.move_cost = 0.004      # Slightly more expensive
            cfg.eat_gain = 0.25        # Less gain
            cfg.rest_recovery = 0.05   # Faster recovery
            
            sim = SurvivalSimulation(cfg, tau=args.tau, food_mult=data["food_mult"])
            res = sim.run()
            
            data["histories"].append(sim.energy_history)
            data["pops"].append(sim.population_history)
            data["actions"].append(sim.action_counts)
            if sim.snapshot_energy_t500:
                data["t500"].extend(sim.snapshot_energy_t500)
            
            status = "PASS" if res["passed"] else "FAIL"
            print(f"  Seed {seed}: {status} | Pop: {res['final_pop']} | Energy: {res['avg_energy']:.3f}")

    if args.plot_all:
        plot_results(groups, args.duration, out_dir)

    print(f"\nOutputs saved to: {out_dir}")

def plot_results(groups, duration, out_dir):
    plt.style.use("default")
    
    # 1. Energy Trajectory
    fig1, ax1 = plt.subplots(figsize=(10, 6))
    colors = {"Normal": "#2166AC", "Stress": "#D6604D"}
    
    for g_name, data in groups.items():
        # Pad histories to duration
        matrix = []
        for h in data["histories"]:
            matrix.append(h + [0.0] * (duration - len(h)))
        matrix = np.array(matrix)
        
        mean = np.mean(matrix, axis=0)
        std = np.std(matrix, axis=0)
        ticks = np.arange(duration)
        
        ax1.plot(ticks, mean, label=f"{g_name} Mean", color=colors[g_name], lw=2)
        ax1.fill_between(ticks, mean-std, mean+std, color=colors[g_name], alpha=0.2)
        
    ax1.set_title("Energy Trajectory (Mean ± SD)")
    ax1.set_xlabel("Ticks")
    ax1.set_ylabel("Mean Agent Energy")
    ax1.axhline(0.7, color="black", linestyle="--", alpha=0.5, label="Target (0.7)")
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    fig1.savefig(os.path.join(out_dir, "energy_trajectory.png"))

    # 2. Survival Curves (Kaplan-Meier style)
    fig2, ax2 = plt.subplots(figsize=(10, 6))
    for g_name, data in groups.items():
        matrix = []
        init_pop = 15 # cfg.init_mothers
        for p in data["pops"]:
            matrix.append(np.array(p) / init_pop * 100)
        
        # Mean survival %
        max_len = max(len(m) for m in matrix)
        mean_surv = np.zeros(max_len)
        counts = np.zeros(max_len)
        for m in matrix:
            mean_surv[:len(m)] += m
            counts[:len(m)] += 1
        mean_surv /= counts
        
        ax2.step(np.arange(len(mean_surv)), mean_surv, where="post", label=g_name, color=colors[g_name], lw=2)
        
    ax2.set_title("Survival Curves (% Population Alive)")
    ax2.set_xlabel("Ticks")
    ax2.set_ylabel("% Alive")
    ax2.set_ylim(-5, 105)
    ax2.legend()
    ax2.grid(True, alpha=0.3)
    fig2.savefig(os.path.join(out_dir, "survival_curves.png"))

    # 3. Action Distribution (Bar Chart)
    fig3, ax3 = plt.subplots(figsize=(10, 6))
    action_labels = ["MOVE", "EAT", "REST", "PICK"]
    x = np.arange(len(action_labels))
    width = 0.35

    for i, (g_name, data) in enumerate(groups.items()):
        total_actions = {k: 0 for k in action_labels}
        for a in data["actions"]:
            for k in action_labels: total_actions[k] += a[k]
        
        vals = [total_actions[k] for k in action_labels]
        sum_vals = sum(vals)
        shares = [v / sum_vals * 100 if sum_vals > 0 else 0 for v in vals]
        
        ax3.bar(x + (i*width) - width/2, shares, width, label=g_name, color=colors[g_name])

    ax3.set_title("Action Distribution (%)")
    ax3.set_xticks(x)
    ax3.set_xticklabels(action_labels)
    ax3.set_ylabel("% of Total Actions")
    ax3.legend()
    fig3.savefig(os.path.join(out_dir, "action_distribution.png"))

    # 4. Energy Histogram at T=500
    fig4, ax4 = plt.subplots(figsize=(10, 6))
    for g_name, data in groups.items():
        if data["t500"]:
            ax4.hist(data["t500"], bins=20, range=(0, 1), alpha=0.5, label=g_name, color=colors[g_name], density=True)
            
            # Fit Gaussian
            mu, std = norm.fit(data["t500"])
            xmin, xmax = ax4.get_xlim()
            x = np.linspace(0, 1, 100)
            p = norm.pdf(x, mu, std)
            ax4.plot(x, p, color=colors[g_name], linewidth=2)

    ax4.set_title("Energy Distribution at T=500")
    ax4.set_xlabel("Energy")
    ax4.set_ylabel("Density")
    ax4.axvline(0.7, color="black", linestyle="--", alpha=0.5)
    ax4.legend()
    fig4.savefig(os.path.join(out_dir, "energy_histogram_t500.png"))

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--duration", type=int, default=1000)
    parser.add_argument("--seeds", type=str, default="42-46")
    parser.add_argument("--stress_seeds", type=str, default="42-46")
    parser.add_argument("--tau", type=float, default=0.1)
    parser.add_argument("--target_energy", type=float, default=0.7)
    parser.add_argument("--plot_all", action="store_true")
    args = parser.parse_args()
    
    run_experiment(args)