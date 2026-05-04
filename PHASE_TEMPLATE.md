# PHASE_TEMPLATE.md

## Common Workflow Rules
- Implement only the approved phase.
- Do not proceed to later phases.
- Do not modify unrelated experiment logic.
- Keep code simple and readable.
- Use seed-controlled runs.
- Use timestamped output folders.
- Do not overwrite old outputs.
- Save raw CSV logs.
- Save config JSON.
- Save summary JSON.
- Save plots PNG.
- Append full results to REPORT.md.
- Update CURRENT_STATE.md.
- Do not paste full report in chat.
- Stop and wait for approval after completion.

## Common Output Summary Format
In chat, summarize only:
- files changed
- command run
- output path
- selected parameter if any
- pass/fail decision
- next recommended step

## Common Scientific Rules
- Do not claim global optimum.
- Frame calibrated parameters as the weakest tested sufficient condition.
- Keep no-care control whenever relevant.
- Distinguish motivation from realized action.
- Report limitations honestly.
- Do not claim maternal care emergence unless no-care fails, care helps, and care remains heritable or zero-shot in later phases.

## Common Required Outputs
Every phase should save:
- raw_logs.csv
- config.json
- summary.json
- plots/*.png
- REPORT.md section
- CURRENT_STATE.md update

## Common Report Section Format
Each REPORT.md phase section should include:
### Purpose
### Protocol
### Outputs
### Results
### Interpretation
### Failure / Limitation
### Decision
