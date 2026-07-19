# Live Evaluation Results

## Current Status

- Date/time: 2026-07-19, live calibration session in progress.
- Agent model: configured locally through `ANTHROPIC_MODEL`.
- Judge model: not run.
- API-backed cases executed: BR-01 baseline and prior seven-case trap calibration runs.
- Baseline result: BR-01 passed in the earlier live session.
- Trap-set result: saved calibration reports exist; they are not a substitute for a completed full eval.
- Full no-judge result: not completed. A full 25-case run was interrupted and must not be reported as a completed result.
- Full judged result: deferred.

## Ship Gate

The full live ship gate has not been claimed. The subjective judge gate is not evaluated until a deliberate judged run is executed with `--confirm-judge-cost`.

## Known Live Artifacts

- `eval_results/live/manual/br-01-after-cache-fix.json`
- `eval_results/live/trap-set-no-judge.json`
- `eval_results/live/trap-set-final-no-judge.json`

These files are local artifacts and are intentionally not committed. See `docs/LIVE_RUN_COST_INCIDENT.md` for the sanitized incident summary.

## Calibration Notes

- Live tool-schema/cache compatibility issues were handled generally.
- BR-13 re-planning expectation remains strict; it was not weakened to hide model behavior.
- New eval commands require explicit confirmation before multi-case, full, or judged live runs.

## Remaining Risks

- Live outcomes can vary due to model stochasticity.
- Full 25-case deterministic results remain unverified.
- Judge-scored rationale/style quality remains unverified.
