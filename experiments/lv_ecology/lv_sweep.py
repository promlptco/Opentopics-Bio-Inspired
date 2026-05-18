"""LV Ecology -- Shannon Lotka-Volterra sweep.

Demonstrates the old-design Shannon food mechanism in a minimal standalone
simulation purpose-built for predator-prey dynamics:

    spawn_rate per empty cell = -alpha * p_global * log(p_global)

where p_global = N_food / N_cells  (global food density).

The Shannon entropy function -p*log(p) peaks at p = 1/e ≈ 0.368 and decays
to zero at both extremes (p→0 and p→1), giving logistic-like prey growth.
This couples food recovery to food density: when food is scarce it spawns
slowly, when food is dense it also spawns slowly, and the peak is in between.

Usage:
  python -m experiments.lv_ecology.lv_sweep
  python -m experiments.lv_ecology.lv_sweep --seeds 3 --ticks 5000 --workers 4
"""
from __future__ import annotations

import argparse
import csv
import math
import random
import sys
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import BoundaryNorm, ListedColormap

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

# ── Standalone simulation grid ──────────────────────────────────────────────
# A small grid concentrates agents relative to food, making consumption
# comparable to spawn and allowing LV coupling.  50×50 (Phase 5 arena) is
# too large: 15 agents on 2500 cells give per-agent food pressure ≈ 0.006,
# so spawn always exceeds consumption and food never drops.
# 30×30 = 900 cells keeps the ratio manageable.
SIM_WIDTH  = 30
SIM_HEIGHT = 30

# ── Sweep grid ───────────────────────────────────────────────────────────────
# alpha: Shannon spawn scale — larger → faster food recovery
# beta:  per-step hunger cost (energy loss per tick)
# gamma: reproduction energy threshold
ALPHA_VALUES = [0.01, 0.02, 0.05]   # spawn rate scale
BETA_VALUES  = [0.02, 0.05, 0.1, 0.2]  # kept as hunger_rate label for heatmap axes
GAMMA_VALUES = [0.002, 0.01, 0.05]  # kept as repro_cost label for heatmap axes

# ── Fixed simulation knobs ────────────────────────────────────────────────────
INIT_AGENTS      = 10      # starting population
INIT_FOOD_FRAC   = 0.368   # start at LV spawn-peak density (1/e)
EAT_GAIN         = 0.50    # energy gained per food item eaten
MOVE_COST        = 0.002   # energy cost per move step
PERCEPTION       = 6       # Chebyshev radius for food detection
REPRO_THRESH     = 0.80    # energy threshold to reproduce
REPRO_TRANSFER   = 0.35    # energy given to child (parent loses same amount)
REPRO_COOLDOWN   = 40      # ticks before an agent can reproduce again
RECORD_EVERY     = 10      # ticks between timeseries samples

# ── Classification thresholds ─────────────────────────────────────────────────
CV_OSC    = 0.10   # CV > this in tail 80%  → oscillating
CV_FLAT   = 0.04   # CV < this              → damped/flat
EXTINCT_N = 2      # agent count ≤ this     → extinction


# ══════════════════════════════════════════════════════════════════════════════
# Standalone minimal LV simulation
# ══════════════════════════════════════════════════════════════════════════════

class _Agent:
    __slots__ = ("x", "y", "energy", "cooldown")

    def __init__(self, x: int, y: int, energy: float = 1.0):
        self.x = x
        self.y = y
        self.energy  = energy
        self.cooldown = 0


class SimpleLVSim:
    """Minimal grid simulation with Shannon entropy food spawn.

    Food spawn rule (old design):
        rate = -alpha * p_global * log(p_global)   [per empty cell per tick]

    Agent rules:
      - lose `hunger` energy every tick (starvation pressure)
      - lose `move_cost` when taking a step toward food
      - gain `eat_gain` when eating (and remove that food cell)
      - reproduce when energy >= repro_thresh: new child appears nearby,
        parent and child each get repro_transfer energy
      - die when energy <= 0

    This is intentionally minimal so the Shannon coupling is the *only*
    ecological mechanism — no care weights, no learning, no maturity lag.
    """

    def __init__(
        self,
        seed: int,
        alpha: float,
        hunger: float,
        repro_cost: float,
        width: int = SIM_WIDTH,
        height: int = SIM_HEIGHT,
        init_agents: int = INIT_AGENTS,
        init_food_frac: float = INIT_FOOD_FRAC,
        eat_gain: float = EAT_GAIN,
        move_cost: float = MOVE_COST,
        perception: int = PERCEPTION,
        repro_thresh: float = REPRO_THRESH,
        repro_transfer: float = REPRO_TRANSFER,
        repro_cooldown: int = REPRO_COOLDOWN,
        record_every: int = RECORD_EVERY,
    ):
        random.seed(seed)
        self.W = width
        self.H = height
        self.N = width * height
        self.alpha        = alpha
        self.hunger       = hunger
        self.repro_cost   = repro_cost
        self.eat_gain     = eat_gain
        self.move_cost    = move_cost
        self.perception   = perception
        self.repro_thresh = repro_thresh
        self.repro_transfer = repro_transfer
        self.repro_cooldown = repro_cooldown
        self.record_every = record_every

        # Place food randomly at init_food_frac density
        n_food = max(1, round(init_food_frac * self.N))
        all_cells = [(x, y) for x in range(width) for y in range(height)]
        random.shuffle(all_cells)
        self.food: set[tuple[int, int]] = set(all_cells[:n_food])

        # Place agents at random positions
        self.agents: list[_Agent] = [
            _Agent(random.randint(0, width - 1), random.randint(0, height - 1))
            for _ in range(init_agents)
        ]

    # ── food spawn (Shannon LV formula) ───────────────────────────────────────
    def _spawn_food(self) -> None:
        p = len(self.food) / self.N
        p = max(1e-9, min(1.0 - 1e-9, p))
        rate = -self.alpha * p * math.log(p)
        for y in range(self.H):
            for x in range(self.W):
                if (x, y) not in self.food and random.random() < rate:
                    self.food.add((x, y))

    # ── agent step ────────────────────────────────────────────────────────────
    def _nearest_food(self, ax: int, ay: int) -> tuple[int, int] | None:
        best, best_d = None, float("inf")
        r = self.perception
        for fy in range(max(0, ay - r), min(self.H, ay + r + 1)):
            for fx in range(max(0, ax - r), min(self.W, ax + r + 1)):
                if (fx, fy) in self.food:
                    d = abs(fx - ax) + abs(fy - ay)
                    if d < best_d:
                        best_d, best = d, (fx, fy)
        return best

    def _step_toward(self, ax: int, ay: int, tx: int, ty: int) -> tuple[int, int]:
        dx, dy = tx - ax, ty - ay
        if abs(dx) >= abs(dy):
            ax += 1 if dx > 0 else -1
        else:
            ay += 1 if dy > 0 else -1
        return max(0, min(self.W - 1, ax)), max(0, min(self.H - 1, ay))

    def _update_agents(self) -> list[_Agent]:
        random.shuffle(self.agents)
        survivors: list[_Agent] = []
        new_children: list[_Agent] = []
        for ag in self.agents:
            # Passive energy drain
            ag.energy -= self.hunger
            if ag.cooldown > 0:
                ag.cooldown -= 1
            if ag.energy <= 0:
                continue  # died

            # Try to eat at current cell
            if (ag.x, ag.y) in self.food:
                self.food.discard((ag.x, ag.y))
                ag.energy = min(1.0, ag.energy + self.eat_gain)
            else:
                nearest = self._nearest_food(ag.x, ag.y)
                if nearest:
                    ag.x, ag.y = self._step_toward(ag.x, ag.y, *nearest)
                    ag.energy -= self.move_cost
                else:
                    # No food in range: random walk
                    dx, dy = random.choice([(1, 0), (-1, 0), (0, 1), (0, -1)])
                    ag.x = max(0, min(self.W - 1, ag.x + dx))
                    ag.y = max(0, min(self.H - 1, ag.y + dy))
                    ag.energy -= self.move_cost

            if ag.energy <= 0:
                continue  # died after moving

            # Reproduce
            if ag.energy >= self.repro_thresh and ag.cooldown == 0:
                cx = max(0, min(self.W - 1, ag.x + random.randint(-1, 1)))
                cy = max(0, min(self.H - 1, ag.y + random.randint(-1, 1)))
                child = _Agent(cx, cy, self.repro_transfer)
                ag.energy -= self.repro_transfer
                ag.cooldown = self.repro_cooldown
                new_children.append(child)

            survivors.append(ag)

        return survivors + new_children

    # ── run for max_ticks ─────────────────────────────────────────────────────
    def run(self, max_ticks: int) -> tuple[list[int], list[int]]:
        food_ts: list[int] = []
        agt_ts:  list[int] = []
        for t in range(max_ticks):
            self._spawn_food()
            self.agents = self._update_agents()
            if t % self.record_every == 0:
                food_ts.append(len(self.food))
                agt_ts.append(len(self.agents))
        return food_ts, agt_ts


# ══════════════════════════════════════════════════════════════════════════════
# Worker (multiprocessing-safe)
# ══════════════════════════════════════════════════════════════════════════════

def _worker(args: tuple) -> dict:
    alpha, hunger, repro_cost, seed, max_ticks = args
    import sys as _sys
    from pathlib import Path as _P
    _sys.path.insert(0, str(_P(__file__).resolve().parents[2]))
    import random as _r, numpy as _np
    _r.seed(seed); _np.random.seed(seed)

    from experiments.lv_ecology.lv_sweep import SimpleLVSim
    sim = SimpleLVSim(seed=seed, alpha=alpha, hunger=hunger, repro_cost=repro_cost)
    food_ts, agt_ts = sim.run(max_ticks)
    return {
        "alpha": alpha, "hunger": hunger, "repro_cost": repro_cost,
        "seed": seed,
        "food_ts": food_ts, "agent_ts": agt_ts,
    }


# ══════════════════════════════════════════════════════════════════════════════
# Classification
# ══════════════════════════════════════════════════════════════════════════════

def classify(food_ts: list[int], agent_ts: list[int]) -> str:
    if not food_ts or not agent_ts:
        return "error"
    n    = len(agent_ts)
    tail = max(1, n * 4 // 5)
    ta   = agent_ts[tail:]
    tf   = food_ts[tail:]

    if max(ta) <= EXTINCT_N:
        return "extinction"
    if max(tf) < 3:
        return "food_collapse"

    cv_a = float(np.std(ta) / (np.mean(ta) + 1e-9))
    cv_f = float(np.std(tf) / (np.mean(tf) + 1e-9))

    if cv_a > CV_OSC and cv_f > CV_OSC:
        return "oscillating"
    if cv_a < CV_FLAT and cv_f < CV_FLAT:
        return "damped"
    return "partial"


# ══════════════════════════════════════════════════════════════════════════════
# Sweep runner
# ══════════════════════════════════════════════════════════════════════════════

def run_sweep(
    seeds: int = 2,
    max_ticks: int = 5000,
    workers: int = 4,
    out_dir: Path | None = None,
) -> tuple[list[dict], Path]:
    ts      = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir = out_dir or (PROJECT_ROOT / "outputs" / "lv_ecology" / f"exp_{ts}")
    out_dir.mkdir(parents=True, exist_ok=True)

    # Map old beta/gamma labels to hunger/repro_cost for backwards compat display
    jobs = [
        (a, b, g, seed, max_ticks)
        for a in ALPHA_VALUES
        for b in BETA_VALUES       # hunger_rate
        for g in GAMMA_VALUES      # repro_cost
        for seed in range(42, 42 + seeds)
    ]
    n = len(jobs)
    print(f"\n[lv_sweep]  {n} runs  |  alpha={ALPHA_VALUES}  beta={BETA_VALUES}  gamma={GAMMA_VALUES}")
    print(f"  seeds={seeds}  ticks={max_ticks}  workers={workers}")
    print(f"  output -> {out_dir}\n")

    results: list[dict] = []
    if workers <= 1:
        for i, job in enumerate(jobs, 1):
            print(f"  [{i}/{n}] a={job[0]:.3f} b={job[1]:.3f} g={job[2]:.3f} s={job[3]}")
            results.append(_worker(job))
            print(f"  [{i}/{n}]  ok")
    else:
        with ProcessPoolExecutor(max_workers=workers) as pool:
            futs = {pool.submit(_worker, j): j for j in jobs}
            done = 0
            for fut in as_completed(futs):
                done += 1
                j = futs[fut]
                try:
                    r = fut.result()
                    results.append(r)
                    print(f"  [{done}/{n}] a={j[0]:.3f} b={j[1]:.3f} g={j[2]:.3f} s={j[3]}  ok")
                except Exception as exc:
                    print(f"  [{done}/{n}] FAIL a={j[0]:.3f} b={j[1]:.3f} g={j[2]:.3f}: {exc}")

    for r in results:
        r["class"] = classify(r["food_ts"], r["agent_ts"])

    csv_path = out_dir / "sweep_summary.csv"
    with open(csv_path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=[
            "alpha", "beta", "gamma", "seed", "class",
            "mean_food", "mean_agents", "cv_food", "cv_agents",
        ])
        w.writeheader()
        for r in results:
            tail = max(1, len(r["agent_ts"]) * 4 // 5)
            tf   = r["food_ts"][tail:]  if r["food_ts"]  else [0]
            ta   = r["agent_ts"][tail:] if r["agent_ts"] else [0]
            w.writerow({
                "alpha": r["alpha"],
                "beta":  r["hunger"],
                "gamma": r["repro_cost"],
                "seed":  r["seed"],
                "class": r["class"],
                "mean_food":   round(float(np.mean(tf)), 1),
                "mean_agents": round(float(np.mean(ta)), 2),
                "cv_food":     round(float(np.std(tf) / (np.mean(tf) + 1e-9)), 3),
                "cv_agents":   round(float(np.std(ta) / (np.mean(ta) + 1e-9)), 3),
            })
    print(f"\nSummary CSV -> {csv_path}")
    return results, out_dir


# ══════════════════════════════════════════════════════════════════════════════
# Plotting
# ══════════════════════════════════════════════════════════════════════════════

_CLASS_ORDER  = ["oscillating", "partial", "damped", "extinction", "food_collapse", "error"]
_CLASS_COLORS = ["#2E7D32", "#8BC34A", "#90A4AE", "#B71C1C", "#E65100", "#9E9E9E"]
_CMAP         = ListedColormap(_CLASS_COLORS)


def _class_idx(c: str) -> int:
    try:
        return _CLASS_ORDER.index(c)
    except ValueError:
        return len(_CLASS_ORDER) - 1


def plot_results(results: list[dict], out_dir: Path, max_ticks: int) -> None:
    from collections import defaultdict, Counter

    agg: dict[tuple, list[str]] = defaultdict(list)
    for r in results:
        agg[(r["alpha"], r["hunger"], r["repro_cost"])].append(r["class"])

    def dominant(classes: list[str]) -> str:
        return Counter(classes).most_common(1)[0][0]

    # ── best oscillating run ──────────────────────────────────────────────────
    best_osc = None
    best_cv  = 0.0
    for r in results:
        if r["class"] == "oscillating":
            tail = max(1, len(r["agent_ts"]) * 4 // 5)
            cv_a = float(np.std(r["agent_ts"][tail:]) / (np.mean(r["agent_ts"][tail:]) + 1e-9))
            cv_f = float(np.std(r["food_ts"][tail:])  / (np.mean(r["food_ts"][tail:])  + 1e-9))
            if cv_a + cv_f > best_cv:
                best_cv, best_osc = cv_a + cv_f, r
    if best_osc is None:
        for cls in ("partial", "damped", "extinction"):
            for r in results:
                if r["class"] == cls:
                    best_osc = r
                    break
            if best_osc:
                break
    if best_osc is None:
        best_osc = results[0]

    tick_axis = np.arange(len(best_osc["food_ts"])) * RECORD_EVERY

    # ══ Figure 1: Stability heatmaps (alpha × hunger, one panel per repro_cost) ══
    n_gamma = len(GAMMA_VALUES)
    fig1, axes = plt.subplots(1, n_gamma, figsize=(5 * n_gamma, 5))
    fig1.patch.set_facecolor("white")
    fig1.suptitle(
        f"LV Shannon Stability  (alpha × hunger_rate, panels = repro_cost)  [{max_ticks} ticks]\n"
        "Green=oscillating  LightGreen=partial  Gray=damped  Red=extinction  Orange=food_collapse",
        fontsize=10, fontweight="bold",
    )
    norm = BoundaryNorm(np.arange(len(_CLASS_ORDER) + 1) - 0.5, len(_CLASS_ORDER))

    axes_list = axes if n_gamma > 1 else [axes]
    for gi, repro_cost in enumerate(GAMMA_VALUES):
        ax = axes_list[gi]
        mat = np.zeros((len(ALPHA_VALUES), len(BETA_VALUES)), dtype=int)
        for ai, alpha in enumerate(ALPHA_VALUES):
            for bi, hunger in enumerate(BETA_VALUES):
                key = (alpha, hunger, repro_cost)
                mat[ai, bi] = _class_idx(dominant(agg[key]))

        ax.imshow(mat, cmap=_CMAP, norm=norm, aspect="auto", origin="lower")
        ax.set_xticks(range(len(BETA_VALUES)))
        ax.set_xticklabels([f"h={b:.3f}" for b in BETA_VALUES], fontsize=8)
        ax.set_yticks(range(len(ALPHA_VALUES)))
        ax.set_yticklabels([f"a={a:.3f}" for a in ALPHA_VALUES], fontsize=8)
        ax.set_xlabel("hunger_rate (energy/tick)", fontsize=9)
        ax.set_ylabel("alpha (Shannon spawn scale)", fontsize=9)
        ax.set_title(f"repro_cost = {repro_cost:.3f}", fontsize=10, fontweight="bold")

        for ai in range(len(ALPHA_VALUES)):
            for bi in range(len(BETA_VALUES)):
                lbl = dominant(agg[(ALPHA_VALUES[ai], BETA_VALUES[bi], repro_cost)])[0:3].upper()
                ax.text(bi, ai, lbl, ha="center", va="center", fontsize=7,
                        fontweight="bold", color="white")

    fig1.tight_layout()
    p1 = out_dir / "fig1_stability_heatmap.png"
    fig1.savefig(str(p1), dpi=150, bbox_inches="tight")
    plt.close(fig1)
    print(f"Saved -> {p1}")

    # ══ Figure 2: Best oscillation time series ════════════════════════════════
    fig2, (ax_food, ax_agt) = plt.subplots(2, 1, figsize=(14, 7), sharex=True)
    fig2.patch.set_facecolor("white")
    fig2.suptitle(
        f"LV Shannon  --  Best Oscillating Run\n"
        f"alpha={best_osc['alpha']:.3f}  hunger={best_osc['hunger']:.3f}  "
        f"repro_cost={best_osc['repro_cost']:.3f}  seed={best_osc['seed']}  "
        f"[class={best_osc['class']}]",
        fontsize=12, fontweight="bold",
    )

    ax_food.plot(tick_axis, best_osc["food_ts"], color="#2E7D32", linewidth=1.5, label="Food count")
    ax_food.axhline(np.mean(best_osc["food_ts"]), color="#2E7D32", linestyle="--",
                    alpha=0.5, linewidth=1.0, label=f"Mean = {np.mean(best_osc['food_ts']):.0f}")
    ax_food.set_ylabel(f"Food count (/{SIM_WIDTH * SIM_HEIGHT} cells)", fontsize=11)
    ax_food.legend(fontsize=9, loc="upper right")
    ax_food.spines[["top", "right"]].set_visible(False)

    ax_agt.plot(tick_axis, best_osc["agent_ts"], color="#1565C0", linewidth=1.5, label="Agent count")
    ax_agt.axhline(np.mean(best_osc["agent_ts"]), color="#1565C0", linestyle="--",
                   alpha=0.5, linewidth=1.0, label=f"Mean = {np.mean(best_osc['agent_ts']):.1f}")
    ax_agt.set_ylabel("Agent count", fontsize=11)
    ax_agt.set_xlabel("Simulation tick", fontsize=11)
    ax_agt.legend(fontsize=9, loc="upper right")
    ax_agt.spines[["top", "right"]].set_visible(False)

    fig2.tight_layout()
    p2 = out_dir / "fig2_best_oscillation_timeseries.png"
    fig2.savefig(str(p2), dpi=150, bbox_inches="tight")
    plt.close(fig2)
    print(f"Saved -> {p2}")

    # ══ Figure 3: Phase portrait ══════════════════════════════════════════════
    fig3, ax = plt.subplots(figsize=(8, 7))
    fig3.patch.set_facecolor("white")
    food_arr = np.array(best_osc["food_ts"])
    agt_arr  = np.array(best_osc["agent_ts"])
    n_pts    = len(food_arr)
    colors   = plt.cm.plasma(np.linspace(0, 1, n_pts))

    for i in range(n_pts - 1):
        ax.plot(food_arr[i:i+2], agt_arr[i:i+2], color=colors[i], linewidth=1.2, alpha=0.85)

    ax.scatter(food_arr[0],  agt_arr[0],  s=120, color="green", zorder=5, label="Start", marker="o")
    ax.scatter(food_arr[-1], agt_arr[-1], s=120, color="red",   zorder=5, label="End",   marker="X")

    sm = plt.cm.ScalarMappable(cmap="plasma",
                               norm=plt.Normalize(vmin=0, vmax=max_ticks))
    sm.set_array([])
    plt.colorbar(sm, ax=ax, label="Simulation tick", shrink=0.85)

    ax.set_xlabel("Food count", fontsize=12)
    ax.set_ylabel("Agent count", fontsize=12)
    ax.set_title(
        f"Phase Portrait (Food vs Agents)  --  LV Shannon\n"
        f"alpha={best_osc['alpha']:.3f}  hunger={best_osc['hunger']:.3f}  "
        f"repro_cost={best_osc['repro_cost']:.3f}",
        fontsize=11, fontweight="bold",
    )
    ax.legend(fontsize=10)
    ax.spines[["top", "right"]].set_visible(False)

    fig3.tight_layout()
    p3 = out_dir / "fig3_phase_portrait.png"
    fig3.savefig(str(p3), dpi=150, bbox_inches="tight")
    plt.close(fig3)
    print(f"Saved -> {p3}")

    # ══ Figure 4: Shannon spawn rate vs food density ══════════════════════════
    p_vals    = np.linspace(0.001, 0.999, 500)
    alpha_ref = 0.05

    rate_lv   = -alpha_ref * p_vals * np.log(p_vals)
    rate_const = np.full_like(p_vals, alpha_ref * math.log(2))

    fig4, ax4 = plt.subplots(figsize=(10, 5))
    fig4.patch.set_facecolor("white")

    ax4.plot(p_vals, rate_lv, color="#E91E63", linewidth=2.5,
             label=f"Old LV: -alpha × p × log(p)   [alpha={alpha_ref}]")
    ax4.plot(p_vals, rate_const, color="#1565C0", linewidth=2.5, linestyle="--",
             label=f"Phase-5 constant: alpha × log(2)   [alpha={alpha_ref}]")

    peak_p = 1.0 / math.e
    peak_r = -alpha_ref * peak_p * math.log(peak_p)
    ax4.axvline(peak_p, color="#E91E63", linestyle=":", alpha=0.7, linewidth=1.2)
    ax4.annotate(
        f"LV peak\np=1/e≈{peak_p:.3f}",
        xy=(peak_p, peak_r), xytext=(peak_p + 0.08, peak_r + 0.004),
        fontsize=9, color="#E91E63",
        arrowprops=dict(arrowstyle="->", color="#E91E63", lw=1.2),
    )

    init_p = INIT_FOOD_FRAC
    ax4.axvline(init_p, color="gray", linestyle=":", alpha=0.7, linewidth=1.2)
    ax4.text(init_p + 0.01, max(rate_const) * 0.8, f"init p={init_p:.3f}",
             fontsize=9, color="gray", va="center")

    ax4.fill_between(p_vals, rate_lv, rate_const, alpha=0.10, color="#E91E63",
                     label="Density-dependent advantage of LV formula")

    ax4.set_xlabel("Global food density  p = N_food / N_cells", fontsize=11)
    ax4.set_ylabel("Spawn rate per empty cell per tick", fontsize=11)
    ax4.set_title(
        "Shannon Spawn Rate Comparison\n"
        "LV: rate = -alpha × p_global × log(p_global)  [density-dependent, drives oscillations]\n"
        "Phase-5: rate = alpha × log(2)  [constant = maximum entropy, no predator-prey coupling]",
        fontsize=11, fontweight="bold",
    )
    ax4.legend(fontsize=9, framealpha=0.9)
    ax4.spines[["top", "right"]].set_visible(False)

    fig4.tight_layout()
    p4 = out_dir / "fig4_spawn_rate_comparison.png"
    fig4.savefig(str(p4), dpi=150, bbox_inches="tight")
    plt.close(fig4)
    print(f"Saved -> {p4}")

    print(f"\nAll plots saved to: {out_dir}")
    print(f"Best: alpha={best_osc['alpha']:.3f}  hunger={best_osc['hunger']:.3f}  "
          f"repro_cost={best_osc['repro_cost']:.3f}  class={best_osc['class']}")


# ══════════════════════════════════════════════════════════════════════════════
# Entry point
# ══════════════════════════════════════════════════════════════════════════════

def main() -> None:
    parser = argparse.ArgumentParser(description="LV Shannon parameter sweep")
    parser.add_argument("--seeds",   type=int, default=2)
    parser.add_argument("--ticks",   type=int, default=5000)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--out",     type=str, default=None)
    args = parser.parse_args()

    out_dir = Path(args.out) if args.out else None
    results, out_dir = run_sweep(
        seeds=args.seeds,
        max_ticks=args.ticks,
        workers=args.workers,
        out_dir=out_dir,
    )
    plot_results(results, out_dir, max_ticks=args.ticks)


if __name__ == "__main__":
    main()
