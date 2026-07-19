# Implementation Plan and Current Status

## Completed No-Key Phase

- Audited the supplied code, docs, tests, golden set, and SQLite database.
- Preserved the existing architecture rather than rewriting the project.
- Hardened agent-loop testability with dependency injection and scripted fake clients.
- Added structured tool errors, stricter schemas, quantity caps, positive room dimensions, and catalog search limits.
- Added deterministic validation for final budget/room integrity, duplicate item IDs, unknown-price claims, stock disclosure, deadline conflicts, final trace consistency, zero-tool terminal answers, and partial/impossible honesty.
- Converted the golden set into a case-aware specification.
- Replaced generic eval scoring with expectation-aware scoring and aggregate ship-gate reporting.
- Added offline fixture replay as a harness verification mode, clearly labelled as not live model results.
- Improved Streamlit and CLI setup paths.
- Added project metadata, CI workflow, runbooks, and submission checklist.
- Added live-eval cost safeguards after an over-broad calibration session: max output token configuration, explicit live confirmation flags, pre-flight summaries, usage aggregation, an aggregate output-token guard, and resume/failed-only support.

## Live Calibration Phase

1. Add `ANTHROPIC_API_KEY` locally.
2. Run one explicit case and inspect actual tool behavior.
3. Run up to three trap cases with `--confirm-multi-case-live` when batching is intentional.
4. Apply only general prompt/tool/threshold changes backed by observed failures.
5. Resume or rerun failed cases instead of rerunning passed cases.
6. Run all 25 cases without judge only with `--all --skip-judge --confirm-full-live`.
7. Run all 25 cases with judge only with `--all --confirm-full-live --confirm-judge-cost`.
8. Record the demo from the calibrated version.

## Current Live Evidence

- BR-01 completed successfully with a real key in a prior session.
- Seven-case trap reports exist from prior calibration attempts.
- A full 25-case live run was interrupted and is not a completed result.
- Judge-enabled ship-gate quality remains unverified.

## Locked Non-Goals

No auth, multi-user state, vector DB, MCP, 3D rendering, moodboards, delivery guarantees, negotiated-price guarantees, structural/electrical/plumbing advice, or database mutation.
