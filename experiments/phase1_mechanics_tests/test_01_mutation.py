"""
Test 01: Mutation works correctly
- Mutated genome differs from parent
- Values stay in [0,1]
- Distribution is reasonable
"""
import sys
import os
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, PROJECT_ROOT)

from evolution.genome import Genome
import statistics
import random
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy import stats as scipy_stats

MODULE_NUM = "01"
DEFAULT_SEED = 42
RUN_NUM = 1
TAG = f"test{MODULE_NUM}_{DEFAULT_SEED}_{RUN_NUM}"

FIELDS = ["care_weight", "forage_weight", "self_weight", "learning_rate", "learning_cost"]

# ── Canonical sigma — must match Genome.mutate() default and EXPERIMENTAL_DESIGN.md ──
CANONICAL_SIGMA = 0.05

_results = []


def _seed():
    random.seed(DEFAULT_SEED)
    np.random.seed(DEFAULT_SEED)


def _log(name: str, detail: str = "") -> None:
    _results.append({"test_name": name, "status": "PASS", "detail": detail})
    print(f"✓ {name} PASSED")


def test_mutation_changes_values():
    """Mutated genome should differ from parent — verified across all 5 fields."""
    _seed()
    parent = Genome(
        care_weight=0.5,
        forage_weight=0.5,
        self_weight=0.5,
        learning_rate=0.1,
        learning_cost=0.05
    )

    trials = 100
    field_changes = {f: 0 for f in FIELDS}

    for _ in range(trials):
        child = parent.mutate(mutation_rate=1.0)
        for f in FIELDS:
            if getattr(child, f) != getattr(parent, f):
                field_changes[f] += 1

    detail = "; ".join(f"{f}={field_changes[f]}/{trials}" for f in FIELDS)
    print(f"Mutations per field: {detail}")
    for f in FIELDS:
        assert field_changes[f] > 90, \
            f"{f}: only {field_changes[f]}/{trials} mutations (expected >90)"
    _log("test_mutation_changes_values", detail)


def test_mutation_stays_in_bounds():
    """All five fields must stay in [0,1] across 1000 mutations."""
    _seed()
    genome = Genome(care_weight=0.99, forage_weight=0.01)

    for _ in range(1000):
        genome = genome.mutate(mutation_rate=1.0)
        for f in FIELDS:
            v = getattr(genome, f)
            assert 0.0 <= v <= 1.0, f"{f} out of bounds: {v}"

    _log("test_mutation_stays_in_bounds", "1000 mutations, all 5 fields in [0,1]")


def test_mutation_rate_zero():
    """mutation_rate=0.0 must leave all 5 fields exactly unchanged."""
    _seed()
    parent = Genome(care_weight=0.3, forage_weight=0.6, self_weight=0.4,
                    learning_rate=0.2, learning_cost=0.1)
    for _ in range(100):
        child = parent.mutate(mutation_rate=0.0)
        for f in FIELDS:
            assert getattr(child, f) == getattr(parent, f), \
                f"mutation_rate=0.0 changed {f}: {getattr(parent, f)} → {getattr(child, f)}"
    _log("test_mutation_rate_zero", "100 trials, all 5 fields unchanged")


def test_mutation_partial_rate():
    """mutation_rate=0.5 should mutate ~50% of genes per field independently."""
    _seed()
    parent = Genome(care_weight=0.5, forage_weight=0.5, self_weight=0.5,
                    learning_rate=0.5, learning_cost=0.5)
    trials = 2000
    field_changes = {f: 0 for f in FIELDS}
    for _ in range(trials):
        child = parent.mutate(mutation_rate=0.5)
        for f in FIELDS:
            if getattr(child, f) != getattr(parent, f):
                field_changes[f] += 1
    detail_parts = []
    for f in FIELDS:
        rate = field_changes[f] / trials
        detail_parts.append(f"{f}={rate:.3f}")
        print(f"  {f}: mutated {field_changes[f]}/{trials} = {rate:.3f}")
        assert 0.40 < rate < 0.60, \
            f"{f}: observed mutation rate {rate:.3f} not near 0.50 (±0.10 tolerance)"
    _log("test_mutation_partial_rate", "; ".join(detail_parts))


def test_mutation_distribution():
    """Mutation deltas (child − parent) across all fields should be ~N(0, sigma).

    Tests deltas, not final values, to avoid confounding with parent position or
    clamping artefacts. Normality verified with D'Agostino/Pearson test (p > 0.01).
    """
    _seed()
    parent = Genome(
        care_weight=0.5,
        forage_weight=0.5,
        self_weight=0.5,
        learning_rate=0.5,
        learning_cost=0.5,
    )

    deltas = {f: [] for f in FIELDS}

    for _ in range(1000):
        child = parent.mutate(mutation_rate=1.0, sigma=CANONICAL_SIGMA)
        for f in FIELDS:
            deltas[f].append(getattr(child, f) - getattr(parent, f))

    detail_parts = []
    for f in FIELDS:
        d     = deltas[f]
        mean  = statistics.mean(d)
        stdev = statistics.stdev(d)
        _, p_norm = scipy_stats.normaltest(d)
        detail_parts.append(f"{f}:mean={mean:.4f},stdev={stdev:.4f},p_norm={p_norm:.3f}")
        print(f"  {f}: delta mean={mean:.4f}, stdev={stdev:.4f}, normaltest p={p_norm:.3f}")
        assert abs(mean) < 0.01, f"{f} delta mean not near 0: {mean:.4f}"
        assert 0.04 < stdev < 0.10, f"{f} delta stdev not near {CANONICAL_SIGMA}: {stdev:.4f}"
        assert p_norm > 0.01, f"{f} deltas fail normality test (p={p_norm:.4f})"

    _log("test_mutation_distribution", "; ".join(detail_parts))


def test_mutation_rate_sensitivity():
    """Sweep sigma values to confirm CANONICAL_SIGMA is appropriate.

    Verifies:
    - Output stdev is monotonically increasing with sigma
    - CANONICAL_SIGMA output stdev lands in expected range
    - No sigma causes values to leave [0,1]
    """
    _seed()

    # Sweep range — adjust if exploring different sigma scales
    SIGMAS = [0.01, 0.03, 0.05, 0.07, 0.10]

    stdevs = {}

    for sigma in SIGMAS:
        parent = Genome(care_weight=0.5, forage_weight=0.5,
                        self_weight=0.5, learning_rate=0.5, learning_cost=0.5)
        samples = []
        for _ in range(1000):
            child = parent.mutate(mutation_rate=1.0, sigma=sigma)
            for f in FIELDS:
                v = getattr(child, f)
                assert 0.0 <= v <= 1.0, f"sigma={sigma}: {f} out of bounds: {v}"
            samples.append(child.care_weight)

        s = statistics.stdev(samples)
        stdevs[sigma] = s
        print(f"  sigma={sigma:.2f} → output stdev={s:.4f}")

    # Monotonic check across full sweep
    sigma_sorted = sorted(SIGMAS)
    for i in range(len(sigma_sorted) - 1):
        assert stdevs[sigma_sorted[i]] < stdevs[sigma_sorted[i + 1]], \
            f"Stdev not monotonic between sigma={sigma_sorted[i]} and sigma={sigma_sorted[i+1]}"

    # Canonical sigma must land in expected range — update bounds if CANONICAL_SIGMA changes
    assert 0.04 < stdevs[CANONICAL_SIGMA] < 0.06, \
        f"sigma={CANONICAL_SIGMA} stdev out of expected range: {stdevs[CANONICAL_SIGMA]:.4f}"

    detail = "; ".join(f"sigma={s}:stdev={stdevs[s]:.4f}" for s in SIGMAS)
    _log("test_mutation_rate_sensitivity", detail)


# ---------------------------------------------------------------------------
# Plotting
# ---------------------------------------------------------------------------

_FIELD_COLORS = {
    "care_weight":   "#2166AC",
    "forage_weight": "#1A9850",
    "self_weight":   "#D6604D",
    "learning_rate": "#756BB1",
    "learning_cost": "#8C6D31",
}

# Sigma sweep colors — add entry here if SIGMAS list is extended
_SIGMA_COLORS = {
    0.01: "#92C5DE",
    0.03: "#4393C3",
    0.05: "#2166AC",
    0.07: "#D6604D",
    0.10: "#B2182B",
}


def plot_mutation_histogram(out_dir: str, n_samples: int = 1000) -> str:
    """Generate a mutation histogram figure and save to *out_dir*.

    Layout: 2 rows × 3 columns
      Row 1: care_weight | forage_weight | self_weight
      Row 2: learning_rate | learning_cost | sigma-sweep (care_weight)

    Returns the path of the saved image.
    """
    _seed()

    PARENT_VAL = 0.5
    SIGMAS     = [0.01, 0.03, 0.05, 0.07, 0.10]  # must match test_mutation_rate_sensitivity

    # ── Collect samples per field ─────────────────────────────────────────
    parent_full = Genome(
        care_weight=PARENT_VAL, forage_weight=PARENT_VAL,
        self_weight=PARENT_VAL, learning_rate=PARENT_VAL,
        learning_cost=PARENT_VAL,
    )
    samples: dict[str, list[float]] = {f: [] for f in FIELDS}
    for _ in range(n_samples):
        child = parent_full.mutate(mutation_rate=1.0, sigma=CANONICAL_SIGMA)
        for f in FIELDS:
            samples[f].append(getattr(child, f))

    # ── Collect sigma-sweep samples (care_weight only) ────────────────────
    sweep_samples: dict[float, list[float]] = {}
    for sig in SIGMAS:
        _seed()
        parent_sw = Genome(
            care_weight=PARENT_VAL, forage_weight=PARENT_VAL,
            self_weight=PARENT_VAL, learning_rate=PARENT_VAL,
            learning_cost=PARENT_VAL,
        )
        sw = []
        for _ in range(n_samples):
            child = parent_sw.mutate(mutation_rate=1.0, sigma=sig)
            sw.append(child.care_weight)
        sweep_samples[sig] = sw

    # ── Figure setup ──────────────────────────────────────────────────────
    plt.style.use("default")
    fig, axes = plt.subplots(2, 3, figsize=(15, 9), facecolor="#FFFFFF")
    fig.patch.set_facecolor("#FFFFFF")
    fig.suptitle(
        f"Mutation Distribution — Phase 1 Test 01  "
        f"|  N={n_samples} samples, σ={CANONICAL_SIGMA}, parent={PARENT_VAL}",
        fontsize=13, fontweight="bold", color="#1A1A1A", y=1.01,
    )

    ax_list = axes.flatten()
    x_fine  = np.linspace(0.0, 1.0, 400)

    def _styled_ax(ax, title: str) -> None:
        ax.set_facecolor("#FAFAFA")
        ax.set_title(title, fontsize=10, fontweight="bold", color="#1A1A1A", pad=6)
        ax.tick_params(colors="#333333", labelsize=8)
        for spine in ax.spines.values():
            spine.set_edgecolor("#CCCCCC")
            spine.set_linewidth(0.8)
        ax.set_xlabel("Mutated value", fontsize=8, color="#444444")
        ax.set_ylabel("Count",         fontsize=8, color="#444444")
        ax.set_xlim(0.0, 1.0)
        ax.grid(axis="y", color="#E0E0E0", linewidth=0.6, linestyle="--")
        ax.set_axisbelow(True)

    # ── Per-field subplots ────────────────────────────────────────────────
    for idx, field in enumerate(FIELDS):
        ax    = ax_list[idx]
        color = _FIELD_COLORS[field]
        data  = samples[field]

        _, bin_edges, _ = ax.hist(
            data, bins=35, range=(0.0, 1.0),
            color=color, alpha=0.55, edgecolor="#FFFFFF", linewidth=0.5,
            label="Sampled",
        )
        scale = len(data) * (bin_edges[1] - bin_edges[0])

        fit_mean, fit_std = np.mean(data), np.std(data, ddof=1)
        ax.plot(x_fine, scipy_stats.norm.pdf(x_fine, fit_mean, fit_std) * scale,
                color=color, linewidth=2.0,
                label=f"Fit N({fit_mean:.3f}, {fit_std:.3f})")

        ax.plot(x_fine, scipy_stats.norm.pdf(x_fine, PARENT_VAL, CANONICAL_SIGMA) * scale,
                color="#888888", linewidth=1.5, linestyle="--", alpha=0.85,
                label=f"Theory N({PARENT_VAL}, {CANONICAL_SIGMA})")

        ax.axvline(fit_mean,   color=color,    linewidth=1.0, linestyle=":")
        ax.axvline(PARENT_VAL, color="#888888", linewidth=1.0, linestyle=":")

        ax.text(0.97, 0.95, f"μ = {fit_mean:.4f}\nσ = {fit_std:.4f}",
                transform=ax.transAxes, fontsize=7.5,
                verticalalignment="top", horizontalalignment="right", color="#1A1A1A",
                bbox=dict(boxstyle="round,pad=0.35", facecolor="#FFFFFF",
                          edgecolor="#CCCCCC", alpha=0.95))

        _styled_ax(ax, field.replace("_", " ").title())
        ax.legend(fontsize=6.5, loc="upper left",
                  facecolor="#FFFFFF", edgecolor="#CCCCCC",
                  labelcolor="#333333", framealpha=0.95)

    # ── Sigma-sweep panel ─────────────────────────────────────────────────
    ax_sw = ax_list[5]
    _styled_ax(ax_sw, "Sigma Sweep — care_weight")

    for sig in SIGMAS:
        ax_sw.hist(
            sweep_samples[sig], bins=35, range=(0.0, 1.0),
            color=_SIGMA_COLORS[sig], alpha=0.55, edgecolor="#FFFFFF", linewidth=0.3,
            label=f"σ = {sig}  (std = {np.std(sweep_samples[sig], ddof=1):.3f})",
        )

    ax_sw.set_xlabel("Mutated care_weight", fontsize=8, color="#444444")
    ax_sw.legend(fontsize=7.5, loc="upper right",
                 facecolor="#FFFFFF", edgecolor="#CCCCCC",
                 labelcolor="#333333", framealpha=0.95)

    # ── Save ─────────────────────────────────────────────────────────────
    plt.tight_layout()
    save_path = os.path.join(out_dir, "mutation_histogram.png")
    fig.savefig(save_path, dpi=150, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)
    return save_path


if __name__ == "__main__":
    import csv

    test_mutation_changes_values()
    test_mutation_stays_in_bounds()
    test_mutation_rate_zero()
    test_mutation_partial_rate()
    test_mutation_distribution()
    test_mutation_rate_sensitivity()

    out_dir = os.path.join(PROJECT_ROOT, "outputs", "phase1_mechanics_tests", TAG)
    os.makedirs(out_dir, exist_ok=True)

    with open(os.path.join(out_dir, "logs.csv"), "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["test_name", "status", "detail"])
        writer.writeheader()
        writer.writerows(_results)

    plot_path = plot_mutation_histogram(out_dir, n_samples=1000)
    print(f"\n=== All mutation tests PASSED ===")
    print(f"Logs saved → outputs/phase1_mechanics_tests/{TAG}/logs.csv")
    print(f"Plot saved → {plot_path}")