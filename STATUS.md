# Build Status

## Completed and Verified Offline

- Read-only SQLite catalog access verified: 72 catalog rows and 14 room briefs.
- Anthropic client dependency injection added; offline tests use scripted fake clients and make no API calls.
- Quantity-aware budget math, fit checks, stock, lead time, unknown-price handling, deadline flags, duplicate merging, final trace consistency, and required refusals are deterministically validated.
- Golden set has 25 cases with explicit machine-readable expectations.
- Case-aware scorers, aggregate ship gate, and offline fixture mode are implemented.
- Streamlit loads into a no-key setup state and keeps keys server-side.
- CLI supports brief listing, model/iteration overrides, JSON output, output file writing, and readable setup errors.
- Offline checks run locally: compileall, pytest, offline fixture eval, CLI help, brief list, and database integrity checks.
- Live-eval cost controls are implemented: full runs require explicit `--all --confirm-full-live`, multi-case live runs require confirmation, judge calls require `--confirm-judge-cost`, and usage/cost-guard reporting is wired into eval reports.
- Existing saved live artifacts were preserved and summarized without regenerating results.

## Live Calibration Observed So Far

- A real-key BR-01 baseline run completed successfully in an earlier session.
- Two seven-case no-judge trap reports exist from calibration attempts.
- A later full 25-case live run was interrupted and must not be described as a completed eval.
- No judge-enabled full evaluation has been completed.
- No live model quality or ship-gate success is claimed beyond the saved completed reports.

## Awaiting Anthropic Key/Live Calibration

- Resume with one affected case at a time.
- Use `--confirm-multi-case-live` only for intentional two- or three-case calibration batches.
- Use `--all --confirm-full-live` only when ready for a deliberate full deterministic run.
- Add `--confirm-judge-cost` only for a deliberate judged run.
- Tune only prompt text, tool descriptions, parsing robustness, or evidence-backed deterministic thresholds from observed live failures.

## Awaiting User-Owned Deployment/Recording Actions

- Configure deployment secrets in Streamlit Cloud or the chosen private deployment target.
- Deploy the app.
- Record the demo.
- Attach the completed live eval report and disclose any failed cases.
