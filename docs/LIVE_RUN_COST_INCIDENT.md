# Live Run Cost Incident

Date/time: 2026-07-19, Asia/Kolkata

No API keys, raw authorization headers, or confidential prompt dumps are included in this note.

## Summary

During live calibration, several API-backed eval commands were run before strong cost-safety controls existed. A full 25-case no-judge run was started and then interrupted by the user. No additional live Anthropic calls were made during the subsequent repair task that added cost safeguards.

## Inferred Chronology From Local Reports

- BR-01 live baseline completed successfully and was saved at `eval_results/live/manual/br-01-after-cache-fix.json`.
- A first 7-case trap-set no-judge report was saved at `eval_results/live/trap-set-no-judge.json`.
- A final 7-case trap-set no-judge report was saved at `eval_results/live/trap-set-final-no-judge.json`.
- `eval_results/results.json` currently mirrors the final completed 7-case trap-set report, not a completed full 25-case report.
- The attempted 25-case no-judge run was interrupted. No complete 25-case live report is present in `eval_results/`.

## Completed API-Backed Cases In Saved Reports

- BR-01 baseline.
- Trap-set cases: `db-br-06`, `db-br-07`, `db-br-08`, `db-br-09`, `db-br-10`, `db-br-13`, `db-br-14`.

Some cases were executed more than once during calibration. Based on saved reports and console history, the approximate total live case executions before this repair was more than the minimum eight unique cases and included repeated trap-case attempts. No dollar cost or token cost is estimated here because pricing and complete usage logs were not available.

## Known Results From Saved Reports

- BR-01 baseline: passed deterministic validation.
- Final saved trap-set aggregate guardrail metrics: passed aggregate no-judge ship-gate metrics.
- Final saved trap-set case-level failure: `db-br-06` retained a stale final budget-check issue in that stochastic run.
- Judge evaluation: not run.
- Full 25-case live evaluation: interrupted and not available as a completed report.

## Safeguards Added After The Incident

- Full live evals no longer run by default.
- Multi-case live evals require explicit confirmation.
- Full live evals require `--all --confirm-full-live`.
- Judge calls require `--confirm-judge-cost`.
- Live runs print a pre-flight summary before API calls.
- Multi-case/full/judge live runs include a countdown.
- Model-call and token usage are captured when returned by the API.
- Optional `LIVE_EVAL_MAX_OUTPUT_TOKENS` stops before starting another case once the aggregate output-token guard is reached.
- `--resume-from` and `--failed-only` avoid rerunning passed cases.

## Repair-Task Guarantee

No Anthropic API calls were made during the repair task that produced this document and the cost-safety controls.
