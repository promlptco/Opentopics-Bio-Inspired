# run_block2_correct.ps1
# Runs Block 2 correct (4 conditions) and Block 2b correct (2 conditions),
# then generates all plots into outputs/phase5_evolution/block2_correct/
#
# Params fixed vs original block2_main:
#   maturity_age    : 200   (was 80)
#   mother_max_age  : 400   (was 1000)
#   relax_ecology   : False (was True)
#   food_patch_prior: 0.12  (was 0.45)
#
# Usage: cd to project root, then: .\run_block2_correct.ps1

$ErrorActionPreference = "Stop"
$Seeds   = 30
$Workers = 4
$Ticks   = 40000
$Ckpt    = 50
$BASE    = "outputs/phase5_evolution"

function Run-Condition {
    param(
        [string]$Label,
        [string]$MutEnabled,
        [string]$PlastEnabled,
        [float]$LR,
        [float]$PC,
        [string]$OutDir
    )
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host "Running: $Label" -ForegroundColor Cyan
    Write-Host "  mut=$MutEnabled  plast=$PlastEnabled  lr=$LR  pc=$PC" -ForegroundColor Cyan
    Write-Host "  output -> $OutDir" -ForegroundColor Cyan
    Write-Host "========================================" -ForegroundColor Cyan

    python -m experiments.phase5_evolution.run `
        --mutation-enabled $MutEnabled `
        --plasticity-enabled $PlastEnabled `
        --learning-rate $LR `
        --plasticity-coefficient $PC `
        --mutation-rate 0.5 `
        --mutation-sigma 0.02 `
        --phenotype-retention 0.15 `
        --seeds $Seeds `
        --seed-start 42 `
        --workers $Workers `
        --max-ticks $Ticks `
        --checkpoint $Ckpt `
        --headless `
        --output-dir $OutDir

    if ($LASTEXITCODE -ne 0) {
        Write-Host "FAILED: $Label (exit $LASTEXITCODE)" -ForegroundColor Red
        exit 1
    }
    Write-Host "Done: $Label" -ForegroundColor Green
}

# Block 2 correct: 4 conditions
Run-Condition "Block2 correct: mut_on / plast_on"   "true"  "true"  1.0  1.0  "$BASE/block2_correct_mut_on_plast_on"
Run-Condition "Block2 correct: mut_on / plast_off"  "true"  "false" 1.0  1.0  "$BASE/block2_correct_mut_on_plast_off"
Run-Condition "Block2 correct: mut_off / plast_on"  "false" "true"  1.0  1.0  "$BASE/block2_correct_mut_off_plast_on"
Run-Condition "Block2 correct: mut_off / plast_off" "false" "false" 1.0  1.0  "$BASE/block2_correct_mut_off_plast_off"

# Block 2b correct: 2 conditions (softer plasticity lr=0.25, pc=0.25)
Run-Condition "Block2b correct: mut_on / plast_on"  "true"  "true"  0.25 0.25 "$BASE/block2b_correct_mut_on_plast_on"
Run-Condition "Block2b correct: mut_off / plast_on" "false" "true"  0.25 0.25 "$BASE/block2b_correct_mut_off_plast_on"

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "All runs complete. Generating plots..." -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

# cohort_analysis: Block 2 correct only (4 conditions)
Write-Host "`n[plot] Cohort analysis: Block 2 correct (4 conditions)" -ForegroundColor Yellow
python -m experiments.phase5_evolution.cohort_analysis --run-set correct
if ($LASTEXITCODE -ne 0) {
    Write-Host "cohort_analysis failed" -ForegroundColor Red
    exit 1
}

# cohort_analysis: Block 2 correct + 2b (all 6 conditions)
Write-Host "`n[plot] Cohort analysis: Block 2 correct + 2b (all 6 conditions)" -ForegroundColor Yellow
python -m experiments.phase5_evolution.cohort_analysis --run-set correct --include-2b `
    --output-dir "$BASE/block2_correct/cohort_plots_with2b"
if ($LASTEXITCODE -ne 0) {
    Write-Host "cohort_analysis with-2b failed" -ForegroundColor Red
    exit 1
}

# plot_dashboard_split: 01-09 per condition (block2 extended style)
$Conditions = @(
    "block2_correct_mut_on_plast_on",
    "block2_correct_mut_on_plast_off",
    "block2_correct_mut_off_plast_on",
    "block2_correct_mut_off_plast_off"
)

foreach ($cond in $Conditions) {
    $InDir  = "$BASE/$cond"
    $OutDir = "$BASE/block2_correct/$cond"
    Write-Host "`n[plot] Dashboard split: $cond" -ForegroundColor Yellow
    python -m experiments.phase5_evolution.plot_dashboard_split `
        --input-dir $InDir `
        --output-dir $OutDir
    if ($LASTEXITCODE -ne 0) {
        Write-Host "plot_dashboard_split failed for $cond" -ForegroundColor Red
        exit 1
    }
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "ALL DONE." -ForegroundColor Green
Write-Host "Plots saved to: $BASE/block2_correct/" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
