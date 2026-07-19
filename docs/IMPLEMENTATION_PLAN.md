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

## Live Calibration Phase

1. Add `ANTHROPIC_API_KEY` locally.
2. Run BR-01 and inspect actual tool behavior.
3. Run trap cases BR-06, BR-07, BR-08, BR-09, BR-10, BR-13, and BR-14.
4. Apply only general prompt/tool/threshold changes backed by observed failures.
5. Run all 25 cases without judge.
6. Run all 25 cases with judge.
7. Record the demo from the calibrated version.

## Locked Non-Goals

No auth, multi-user state, vector DB, MCP, 3D rendering, moodboards, delivery guarantees, negotiated-price guarantees, structural/electrical/plumbing advice, or database mutation.
