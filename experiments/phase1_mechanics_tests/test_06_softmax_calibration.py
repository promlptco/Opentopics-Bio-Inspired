"""
Test 06: Softmax Calibration

Verifies that the Softmax (Gibbs) action selection is correctly implemented:
  (a) Mathematical correctness — softmax_probs() output matches the Boltzmann equation.
  (b) Empirical proportionality — sampling from softmax_probs() at a fixed seed
      selects the highest-utility action at a rate consistent with Softmax(τ=0.1).
  (c) Temperature sensitivity — higher τ flattens distribution; lower τ sharpens it.
  (d) Boundary robustness — handles equal scores, zero-score vectors, and a single option.

Design reference: EXPERIMENT_DESIGN.md Phase 1, Test 06 (amended 2026-04-14).
"""
import sys
import os
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, PROJECT_ROOT)

import math
import numpy as np
import matplotlib
matplotlib.use("Agg")  # headless — no display needed
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from agents.mother import softmax_probs, SOFTMAX_TAU

MODULE_NUM = "06"
DEFAULT_SEED = 42
RUN_NUM = 1
TAG = f"test{MODULE_NUM}_{DEFAULT_SEED}_{RUN_NUM}"

_results = []


def _seed():
    np.random.seed(DEFAULT_SEED)


def _log(name: str, detail: str = "") -> None:
    _results.append({"test_name": name, "status": "PASS", "detail": detail})
    print(f"✓ {name} PASSED")


# ---------------------------------------------------------------------------
# Sub-test A: Mathematical correctness
# ---------------------------------------------------------------------------

def test_softmax_math_correct():
    """softmax_probs() must exactly reproduce the Boltzmann equation.

    P(a) = exp(u_a / τ) / Σ exp(u_i / τ)

    We compute the gold-standard probability for a known 3-action input
    and verify the function output matches to 8 decimal places.
    """
    scores = {"care": 0.7, "forage": 0.4, "self": 0.2}
    tau = SOFTMAX_TAU  # 0.1

    # Gold-standard manual calculation
    raw = {k: math.exp(v / tau) for k, v in scores.items()}
    total = sum(raw.values())
    expected = {k: raw[k] / total for k in raw}

    got = softmax_probs(scores, tau=tau)

    for action in scores:
        diff = abs(got[action] - expected[action])
        print(f"  {action}: expected={expected[action]:.8f}, got={got[action]:.8f}, diff={diff:.2e}")
        assert diff < 1e-8, (
            f"{action}: softmax_probs differs from Boltzmann equation by {diff:.2e}"
        )

    # Probabilities must sum to 1.0
    total_prob = sum(got.values())
    assert abs(total_prob - 1.0) < 1e-9, f"Probabilities do not sum to 1: {total_prob}"

    _log(
        "test_softmax_math_correct",
        f"tau={tau};care={got['care']:.6f};forage={got['forage']:.6f};self={got['self']:.6f}"
    )


# ---------------------------------------------------------------------------
# Sub-test B: Empirical proportionality (sampling distribution)
# ---------------------------------------------------------------------------

def test_empirical_selection_rate():
    """Sampling repeatedly from softmax_probs must converge to the expected probabilities.

    Setup: scores = {high: 0.9, low: 0.1} with τ=0.1.
    The Softmax probability of 'high' is extremely close to 1 at τ=0.1.
    We verify:
      - 'high' is selected at a rate ≥ 99% (consistent with Softmax(τ=0.1))
      - The empirical rate is within 1% of the theoretical Softmax probability.
    """
    _seed()
    scores = {"high": 0.9, "low": 0.1}
    tau = SOFTMAX_TAU  # 0.1

    probs = softmax_probs(scores, tau=tau)
    p_high_theoretical = probs["high"]
    print(f"  Theoretical P(high) at τ={tau}: {p_high_theoretical:.6f}")

    # Sample N times
    N = 5_000
    keys = list(probs.keys())
    weights = [probs[k] for k in keys]
    counts = {k: 0 for k in keys}
    for _ in range(N):
        chosen = np.random.choice(len(keys), p=weights)
        counts[keys[chosen]] += 1

    p_high_empirical = counts["high"] / N
    print(f"  Empirical  P(high) over {N} samples: {p_high_empirical:.6f}")
    print(f"  |empirical - theoretical| = {abs(p_high_empirical - p_high_theoretical):.6f}")

    # Must select 'high' at ≥ 99% rate (theoretical is > 0.9999 at these parameters)
    assert p_high_empirical >= 0.99, (
        f"Expected 'high' to dominate (≥99%) at τ={tau}, got {p_high_empirical:.4f}"
    )

    # Empirical rate must be within 1% of theory
    assert abs(p_high_empirical - p_high_theoretical) < 0.01, (
        f"Empirical rate {p_high_empirical:.4f} deviates from "
        f"theoretical {p_high_theoretical:.4f} by more than 1%"
    )

    _log(
        "test_empirical_selection_rate",
        f"tau={tau};N={N};p_high_theory={p_high_theoretical:.6f};"
        f"p_high_empirical={p_high_empirical:.6f};"
        f"delta={abs(p_high_empirical - p_high_theoretical):.6f}"
    )


# ---------------------------------------------------------------------------
# Sub-test B2: Weaker contrast — intermediate τ stays proportional
# ---------------------------------------------------------------------------

def test_moderate_contrast_proportional():
    """At τ=0.5 (looser), selection should be clearly proportional — not dominated.

    scores = {A: 0.6, B: 0.4} at τ=0.5.
    A should win more often than B, but not overwhelmingly.
    Verify the Softmax probabilities reflect the relative utilities correctly.
    """
    _seed()
    scores = {"A": 0.6, "B": 0.4}
    tau = 0.5  # Wider distribution — both actions have real probability

    probs = softmax_probs(scores, tau=tau)
    p_A = probs["A"]
    p_B = probs["B"]
    print(f"  τ={tau}: P(A=0.6)={p_A:.4f}, P(B=0.4)={p_B:.4f}")

    # A must be more probable than B
    assert p_A > p_B, f"Higher utility action must have higher probability: P(A)={p_A} ≤ P(B)={p_B}"

    # Both must have non-trivial probability (neither is negligible at τ=0.5)
    assert p_B > 0.01, f"Lower action should still have non-trivial probability at τ=0.5, got {p_B:.4f}"

    # Gold-standard check
    exp_A = math.exp(0.6 / tau)
    exp_B = math.exp(0.4 / tau)
    expected_p_A = exp_A / (exp_A + exp_B)
    assert abs(p_A - expected_p_A) < 1e-10, (
        f"P(A) mismatch: expected {expected_p_A:.8f}, got {p_A:.8f}"
    )

    _log(
        "test_moderate_contrast_proportional",
        f"tau={tau};p_A={p_A:.6f};p_B={p_B:.6f};expected_p_A={expected_p_A:.6f}"
    )


# ---------------------------------------------------------------------------
# Sub-test C: Temperature sensitivity
# ---------------------------------------------------------------------------

def test_temperature_sensitivity():
    """Lower τ must produce a sharper (more argmax-like) distribution.
    Higher τ must produce a flatter (more uniform) distribution.

    We use a fixed asymmetric score vector and compare entropy across τ values.
    Lower τ → lower entropy (more deterministic).
    Higher τ → higher entropy (more uniform).
    """
    scores = {"care": 0.8, "forage": 0.5, "self": 0.2}
    taus = [0.05, 0.1, 0.5, 1.0]
    entropies = {}

    for tau in taus:
        probs = softmax_probs(scores, tau=tau)
        # Shannon entropy H = -Σ p·log(p)
        H = -sum(p * math.log(p) for p in probs.values() if p > 1e-300)
        entropies[tau] = H
        top_action = max(probs, key=probs.get)
        print(f"  τ={tau:.2f}: entropy={H:.4f}, top={top_action}({probs[top_action]:.4f})")

    # Entropy must be monotonically increasing with τ
    sorted_taus = sorted(taus)
    for i in range(len(sorted_taus) - 1):
        t_low, t_high = sorted_taus[i], sorted_taus[i + 1]
        assert entropies[t_low] < entropies[t_high], (
            f"Entropy not monotonic: τ={t_low} H={entropies[t_low]:.4f} "
            f"≥ τ={t_high} H={entropies[t_high]:.4f}"
        )

    # At the canonical τ=0.1, the highest-utility action (care=0.8) must dominate
    probs_canonical = softmax_probs(scores, tau=SOFTMAX_TAU)
    assert probs_canonical["care"] > 0.95, (
        f"At τ={SOFTMAX_TAU}, care (score=0.8) should dominate (>95%), "
        f"got {probs_canonical['care']:.4f}"
    )

    detail = ";".join(f"tau={t}:H={entropies[t]:.4f}" for t in sorted_taus)
    _log("test_temperature_sensitivity", detail)


# ---------------------------------------------------------------------------
# Sub-test D: Boundary robustness
# ---------------------------------------------------------------------------

def test_boundary_equal_scores():
    """With all equal utility scores, Softmax must return uniform probabilities."""
    scores = {"care": 0.5, "forage": 0.5, "self": 0.5}
    probs = softmax_probs(scores)

    for action, p in probs.items():
        expected = 1.0 / 3.0
        assert abs(p - expected) < 1e-10, (
            f"Equal scores should give uniform probs. {action}: {p:.8f} ≠ {expected:.8f}"
        )
    print(f"  Equal scores → uniform: {list(probs.values())}")
    _log("test_boundary_equal_scores", f"p_each={list(probs.values())[0]:.6f}")


def test_boundary_zero_scores():
    """With all-zero utility scores, Softmax must still return uniform probabilities
    and must not crash (no division by zero, no NaN, no inf).
    """
    scores = {"care": 0.0, "forage": 0.0, "self": 0.0}
    probs = softmax_probs(scores)

    total = sum(probs.values())
    assert abs(total - 1.0) < 1e-9, f"Probabilities don't sum to 1: {total}"
    for action, p in probs.items():
        assert not math.isnan(p), f"NaN probability for {action}"
        assert not math.isinf(p), f"Inf probability for {action}"
    print(f"  Zero scores → probabilities: {probs}")
    _log("test_boundary_zero_scores", f"sum={total:.8f};no_nan=True;no_inf=True")


def test_boundary_single_action():
    """With a single action, Softmax must assign probability 1.0 to that action."""
    scores = {"care": 0.7}
    probs = softmax_probs(scores)

    assert abs(probs["care"] - 1.0) < 1e-10, (
        f"Single action must get probability 1.0, got {probs['care']}"
    )
    print(f"  Single action → P(care)={probs['care']:.8f}")
    _log("test_boundary_single_action", f"p_care={probs['care']:.8f}")


# ---------------------------------------------------------------------------
# Plotting
# ---------------------------------------------------------------------------

# Canonical scenarios (care, forage, self) used for bar chart panels
_SCENARIOS: list[dict] = [
    {
        "label": "High Contrast\n(care=0.9, forage=0.5, self=0.1)",
        "scores": {"care": 0.9, "forage": 0.5, "self": 0.1},
    },
    {
        "label": "Moderate\n(care=0.7, forage=0.4, self=0.2)",
        "scores": {"care": 0.7, "forage": 0.4, "self": 0.2},
    },
    {
        "label": "Near-Equal\n(care=0.5, forage=0.45, self=0.4)",
        "scores": {"care": 0.5, "forage": 0.45, "self": 0.4},
    },
]

_ACTION_COLORS = {
    "care":   "#2166AC",   # strong blue
    "forage": "#1A9850",   # strong green
    "self":   "#D6604D",   # warm red
}

# Temperature sensitivity panel uses this fixed scenario
_TEMP_SCENARIO = {"care": 0.7, "forage": 0.4, "self": 0.2}
_TEMP_TAUS     = [0.05, 0.1, 0.2, 0.5, 1.0]


def _sample_freqs(
    scores: dict[str, float],
    tau: float,
    n_trials: int,
    n_samples: int,
    base_seed: int,
) -> dict[str, np.ndarray]:
    """Return per-action arrays of shape (n_trials,) with observed frequency [0, 1].

    Each trial is seeded independently so the set of trials is reproducible
    but each trial is a different draw from the same distribution.
    """
    probs = softmax_probs(scores, tau=tau)
    keys  = list(probs.keys())
    weights = np.array([probs[k] for k in keys])

    freq: dict[str, list[float]] = {k: [] for k in keys}
    for t in range(n_trials):
        np.random.seed(base_seed + t)
        chosen = np.random.choice(len(keys), size=n_samples, p=weights)
        for i, k in enumerate(keys):
            freq[k].append(np.sum(chosen == i) / n_samples)

    return {k: np.array(freq[k]) for k in keys}


def plot_softmax_calibration(
    out_dir: str,
    n_trials: int = 30,
    n_samples: int = 5_000,
    base_seed: int = DEFAULT_SEED,
) -> str:
    """Generate a 2×2 Softmax calibration figure and save to *out_dir*.

    Layout:
      Row 1: scenario panels — High Contrast | Moderate | Near-Equal
      Row 2: Temperature sensitivity panel (full width)

    Bar chart design (panels 1–3):
      - Actions on X-axis: care / forage / self
      - Y-axis: frequency %
      - Two bars per action: Observed (mean over trials) and Theoretical
      - Error bars on Observed bar: ± 1 SD across trials

    Temperature panel:
      - X-axis: τ ∈ {0.05, 0.1, 0.5, 1.0}
      - Grouped bars per action, showing how theoretical probability shifts with τ

    Returns the path of the saved image.
    """
    ACTIONS = ["care", "forage", "self"]
    TAU     = SOFTMAX_TAU  # 0.1

    # ── Figure layout: 1×3 top panels + 1 bottom spanning panel ──────────
    plt.style.use("default")
    fig = plt.figure(figsize=(17, 10), facecolor="#FAFAFA")
    fig.patch.set_facecolor("#FAFAFA")

    # Grid: 2 rows, 3 columns. Bottom panel spans all 3 columns.
    gs = fig.add_gridspec(
        2, 3,
        height_ratios=[1.0, 0.85],
        hspace=0.45, wspace=0.35,
    )
    axes_top  = [fig.add_subplot(gs[0, c]) for c in range(3)]
    ax_bottom = fig.add_subplot(gs[1, :])

    fig.suptitle(
        f"Softmax Calibration — Test 06  │  τ={TAU}  │  "
        f"{n_trials} trials × {n_samples:,} samples each",
        fontsize=13, fontweight="bold", color="#1A1A1A", y=1.01,
    )

    # Shared bar geometry
    x       = np.arange(len(ACTIONS))  # 0, 1, 2
    bar_w   = 0.30
    gap     = 0.04

    def _style_ax(ax: plt.Axes, title: str) -> None:
        ax.set_facecolor("#FFFFFF")
        ax.set_title(title, fontsize=9.5, fontweight="bold",
                     color="#1A1A1A", pad=7)
        for spine in ax.spines.values():
            spine.set_edgecolor("#CCCCCC")
            spine.set_linewidth(0.8)
        ax.tick_params(colors="#333333", labelsize=8.5)
        ax.set_axisbelow(True)
        ax.grid(axis="y", color="#EBEBEB", linewidth=0.7, linestyle="--")

    # ── Panels 1–3: scenario bar charts ──────────────────────────────────
    for scenario, ax in zip(_SCENARIOS, axes_top):
        scores = scenario["scores"]

        # Theoretical probabilities
        theory = softmax_probs(scores, tau=TAU)

        # Observed frequencies across trials (per action)
        freq_data = _sample_freqs(scores, TAU, n_trials, n_samples, base_seed)

        # Draw bars: observed first, then theoretical, side by side
        for i, action in enumerate(ACTIONS):
            obs_arr   = freq_data[action] * 100.0  # → %
            obs_mean  = obs_arr.mean()
            obs_std   = obs_arr.std(ddof=1)
            theory_pct = theory[action] * 100.0
            color      = _ACTION_COLORS[action]

            # Observed bar (slightly left)
            ax.bar(
                x[i] - bar_w / 2 - gap / 2,
                obs_mean, bar_w,
                color=color, alpha=0.75,
                edgecolor="#FFFFFF", linewidth=0.6,
                yerr=obs_std, capsize=4,
                error_kw=dict(elinewidth=1.5, ecolor="#333333", capthick=1.5),
                label="Observed" if i == 0 else "",
            )

            # Theoretical bar (slightly right, hatched)
            ax.bar(
                x[i] + bar_w / 2 + gap / 2,
                theory_pct, bar_w,
                color=color, alpha=0.30,
                edgecolor=color, linewidth=1.2,
                hatch="//",
                label="Theoretical" if i == 0 else "",
            )

            # Annotate observed mean above bar
            ax.text(
                x[i] - bar_w / 2 - gap / 2,
                obs_mean + obs_std + 0.8,
                f"{obs_mean:.1f}%",
                ha="center", va="bottom", fontsize=7, color="#333333",
            )
            # Annotate theoretical value
            ax.text(
                x[i] + bar_w / 2 + gap / 2,
                theory_pct + 0.8,
                f"{theory_pct:.1f}%",
                ha="center", va="bottom", fontsize=7, color="#666666",
            )

        _style_ax(ax, scenario["label"])
        ax.set_xticks(x)
        ax.set_xticklabels([a.capitalize() for a in ACTIONS], fontsize=9)
        ax.set_ylabel("Frequency (%)", fontsize=8.5, color="#444444")
        ax.set_xlabel("Action (motivation)", fontsize=8.5, color="#444444")
        ax.set_ylim(0, 110)
        ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{v:.0f}%"))

        # Legend: first panel only (shared)
        if scenario is _SCENARIOS[0]:
            obs_patch    = mpatches.Patch(color="#888888", alpha=0.75, label="Observed (mean ± 1 SD)")
            theory_patch = mpatches.Patch(facecolor="#CCCCCC", edgecolor="#888888",
                                          hatch="//", label=f"Theoretical Softmax(τ={TAU})")
            ax.legend(
                handles=[obs_patch, theory_patch],
                fontsize=7.5, loc="upper right",
                facecolor="#FFFFFF", edgecolor="#CCCCCC", framealpha=0.95,
            )

    # ── Bottom panel: Temperature sensitivity ────────────────────────────
    tau_x   = np.arange(len(_TEMP_TAUS))
    bar_w_t = 0.18

    for j, action in enumerate(ACTIONS):
        color = _ACTION_COLORS[action]
        theory_vals = [
            softmax_probs(_TEMP_SCENARIO, tau=tau)[action] * 100.0
            for tau in _TEMP_TAUS
        ]
        offset = (j - 1) * (bar_w_t + 0.03)
        ax_bottom.bar(
            tau_x + offset, theory_vals, bar_w_t,
            color=color, alpha=0.75,
            edgecolor="#FFFFFF", linewidth=0.5,
            label=action.capitalize(),
        )
        # Value labels
        for xi, val in zip(tau_x + offset, theory_vals):
            ax_bottom.text(
                xi, val + 0.6, f"{val:.1f}%",
                ha="center", va="bottom", fontsize=6.8, color="#333333",
            )

    # Mark canonical τ
    canonical_idx = _TEMP_TAUS.index(TAU)
    ax_bottom.axvspan(
        tau_x[canonical_idx] - 0.40, tau_x[canonical_idx] + 0.40,
        color="#2166AC", alpha=0.08, zorder=0,
    )
    ax_bottom.text(
        tau_x[canonical_idx], -8,
        f"τ={TAU}\n(canonical)",
        ha="center", va="top", fontsize=7.5, color="#2166AC",
        fontweight="bold",
    )

    _style_ax(
        ax_bottom,
        f"Temperature Sensitivity  │  Theoretical Softmax(care=0.7, forage=0.4, self=0.2)",
    )
    ax_bottom.set_xticks(tau_x)
    ax_bottom.set_xticklabels([f"τ = {t}" for t in _TEMP_TAUS], fontsize=9)
    ax_bottom.set_ylabel("Theoretical Frequency (%)", fontsize=8.5, color="#444444")
    ax_bottom.set_xlabel("Softmax Temperature (τ)",    fontsize=8.5, color="#444444")
    ax_bottom.set_ylim(0, 115)
    ax_bottom.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{v:.0f}%"))
    ax_bottom.legend(
        fontsize=8.5, loc="upper right",
        facecolor="#FFFFFF", edgecolor="#CCCCCC", framealpha=0.95,
    )

    # ── Save ─────────────────────────────────────────────────────────────
    save_path = os.path.join(out_dir, "softmax_calibration.png")
    fig.savefig(save_path, dpi=150, bbox_inches="tight",
                facecolor=fig.get_facecolor())
    plt.close(fig)
    return save_path



if __name__ == "__main__":
    import csv

    # A: Mathematical correctness
    test_softmax_math_correct()

    # B: Empirical proportionality
    test_empirical_selection_rate()
    test_moderate_contrast_proportional()

    # C: Temperature sensitivity
    test_temperature_sensitivity()

    # D: Boundary robustness
    test_boundary_equal_scores()
    test_boundary_zero_scores()
    test_boundary_single_action()

    out_dir = os.path.join(PROJECT_ROOT, "outputs", "phase1_mechanics_tests", TAG)
    os.makedirs(out_dir, exist_ok=True)

    # Save test log
    with open(os.path.join(out_dir, "logs.csv"), "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["test_name", "status", "detail"])
        writer.writeheader()
        writer.writerows(_results)

    # Generate calibration plot
    plot_path = plot_softmax_calibration(out_dir)
    print(f"Plot saved  → {plot_path}")

    print(f"\n=== All Softmax calibration tests PASSED ===")
    print(f"Logs saved  → outputs/phase1_mechanics_tests/{TAG}/logs.csv")
