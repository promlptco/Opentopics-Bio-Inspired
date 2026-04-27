"""Phase 4 -- Step 1: Floor-Bounce Artefact (INVALIDATED)

PURPOSE
-------
Original Phase 4 multi-seed run. Initialised all mothers with
care_weight ~ U(0, 1). This produced a spurious positive Pearson r
(mean r = +0.0593) that appeared to show care was NOT eroding.

WHY IT IS AN ARTEFACT
---------------------
The simulation enforces a lethal floor: mothers with care_weight < ~0.30
die too quickly to appear in the birth_log. This censors low-care genomes
from the regression, pushing the observed mean upward.

  Init:   care ~ U(0, 1)  -- mean 0.50
  Result: r = +0.059       -- spurious floor effect
  Grid:   30x30, N=12, food=45, seeds 42-51, 10,000 ticks

OUTPUTS (archived)
------------------
  outputs/phase4_neutral_drift_baseline/01_floor_bounce_artefact/
    phase4_care_weight_trajectory.png   -- care stays near 0.5 (artefact)
    phase4_pearson_r_distribution.png   -- r near zero, some positive (artefact)
    phase4_motivation_weights.png       -- all weights near midpoint (artefact)
    statistical_results.json            -- mean r = +0.059

NOTE
----
The original run_multi_seed.py script has been deleted as it produced
invalid results. The archived outputs are retained for documentation only.
Proceed to 02_run_ceiling_drop_erosion.py for the corrected experiment.
"""
