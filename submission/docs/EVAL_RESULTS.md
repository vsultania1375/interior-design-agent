# Evaluation Results

## Current Status (honest summary)

**A full 25-case live judged run has not been executed.** This session was explicitly scoped to run
it (`python evals/run_evals.py --all --confirm-full-live --confirm-judge-cost`), but the user reported
no Anthropic API credit budget was available and asked to skip all live/paid API calls. No live
Anthropic API calls were made in this session. This section reports, honestly, what can be verified
right now from what actually exists, and clearly labels what is missing.

## What Was Verified This Session (zero API cost)

- Date/time: 2026-07-19, offline-only verification pass.
- Agent model configured: `claude-sonnet-5` (via `ANTHROPIC_MODEL`, not called this session).
- Judge model configured: `claude-sonnet-5` (not called this session).
- `pytest -q`: 119/119 passed.
- `python evals/run_evals.py --offline-fixtures`: 25/25 cases executed without error (`eval_results/offline/results.json`, generated `2026-07-19T12:56:19Z`).

### What the offline fixture run actually proves — and what it does not

The offline harness (`evals/offline_fixtures.py`) exercises the scorer, validator, and ship-gate code
paths using **scripted stand-in plans**, not live model output. Six cases (`db-br-06`, `db-br-07`,
`db-br-13`, `db-br-09`, the prompt-injection case, and the out-of-stock case) have a purpose-built
fixture plan matching their trap scenario. **Every other case — including all non-Living-Room briefs
(bedroom, dining, study, kids) — is scripted to return the same generic Living Room stand-in plan**
(sofa, coffee table, TV unit, rug, floor lamp), regardless of what that brief actually asked for.

That means the offline fixture run's own ship-gate table shows 17 of 25 cases "failing" checks like
`must_have_coverage` and `required_category:Bed` / `required_category:Wardrobe` / `required_category:Desk`
— **this is expected and by design, not a real agent quality signal.** The fixture's job is to prove the
scoring code runs correctly end to end, not to prove the agent is good at bedrooms. Reporting these
numbers as if they were live-model ship-gate results would be actively misleading, so this document does
not do that. The only thing the offline run certifies is: the harness itself works, does not crash, and
computes metrics as designed, on all 25 golden-set cases.

## Historical Live Data (from an earlier session, before this conversation — not re-run, not re-verified)

The only real API-backed evaluation data that exists in this repository is from a prior calibration
session, documented in full in `docs/LIVE_RUN_COST_INCIDENT.md`. Summarized here for completeness,
unchanged from that record:

- BR-01 baseline: passed deterministic validation (`eval_results/live/manual/br-01-after-cache-fix.json`).
- A 7-case ("trap-set") no-judge live run: `eval_results/live/trap-set-final-no-judge.json`, generated
  `2026-07-19T06:44:53Z`.
  - Cases run: `db-br-06`, `db-br-07`, `db-br-08`, `db-br-09`, `db-br-10`, `db-br-13`, `db-br-14`.
  - No-judge ship gate (aggregate, 7/7 cases unless noted):

    | Metric | Result | Threshold | Pass/Fail |
    |---|---|---|---|
    | Real catalog items | 7/7 (100%) | 100% | Pass |
    | Zero silent budget violations | 7/7 (100%) | 100% | Pass |
    | Required scope/guarantee refusals | 7/7 (100%) | 100% | Pass |
    | Fit violations caught or flagged | 7/7 (100%) | 100% | Pass |
    | Catalog search + budget check used | 7/7 (100%) | 100% | Pass |
    | Fit checked before finalisation | 7/7 (100%) | 100% | Pass |
    | Judge score ≥4/5 | Not evaluated | ≥90% | Not evaluated |

  - Overall no-judge gate: **Pass**, with one case-level issue documented below.
  - Case-level failure: `db-br-06` — `final_budget_checked` flagged. Diagnosis: in that specific
    stochastic run, the agent's final trace retained a stale/incomplete budget-check entry rather than
    a fresh check on the exact final item set. This is a real, documented agent-behavior gap (re-check
    discipline after the last edit to the item list), not a scorer bug — it was not reclassified or
    hidden to make the gate pass.
  - Judge-scored run: **not completed** for this trap set.
- An earlier attempt at a full 25-case no-judge live run was started and interrupted by the user before
  completion; no complete 25-case live report exists from it.

## Full Judged Result

**Not run.** No full 25-case live run and no judge-scored run exist anywhere in this project's history.
The subjective judge gate (score ≥4/5 on ≥90% of judged cases) has never been evaluated.

## Ship Gate — Overall Status

**Not certified.** The project cannot claim full live ship-gate success. What is true:
- The harness, scorers, and ship-gate aggregation logic are implemented and verified to run correctly
  (pytest + offline fixtures, zero cost).
- A small, real, live sample (7 cases, no judge) passed the no-judge gate with one documented case-level
  issue.
- The full 25-case live run and the judged run remain outstanding, blocked on available API budget.

## Remaining Risks

- Live outcomes can vary due to model stochasticity — a passing case in one run is not a guarantee of
  the same result in another run.
- Full 25-case deterministic (no-judge) live results remain unverified beyond the 7-case sample above.
- Judge-scored rationale/style quality remains completely unverified.
- The `db-br-06` final-budget-recheck gap observed in the 7-case sample has not been re-tested after any
  subsequent prompt changes.

## Known Local Artifacts (not committed)

- `eval_results/live/manual/br-01-after-cache-fix.json`
- `eval_results/live/trap-set-no-judge.json`
- `eval_results/live/trap-set-final-no-judge.json`
- `eval_results/offline/results.json`, `eval_results/offline/results.md`

No API keys, raw authorization headers, full hidden prompts, or raw customer/database dumps are
included in this document or in the artifacts above.
