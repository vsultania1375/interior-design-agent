# Build Status

## Completed and Verified

- Read-only SQLite catalog access verified: 72 catalog rows and 14 room briefs.
- Anthropic client dependency injection added; offline tests use scripted fake clients and make no API calls.
- Quantity-aware budget math, fit checks, stock, lead time, unknown-price handling, deadline flags, duplicate merging, final trace consistency, and required refusals are deterministically validated.
- Golden set has 25 cases with explicit machine-readable expectations.
- Case-aware scorers, aggregate ship gate, and offline fixture mode are implemented and pass (25/25 harness executions, zero API cost).
- 119/119 offline pytest tests pass, including UI container-nesting regression tests, conversational Q&A pairing tests, and free-text guardrail tests.
- Conversational UI rebuilt: full-height dual-pane layout (chat + room preview), user-resizable panel divider (JS-driven, verified via real mouse-drag simulation), richer result-screen room visualization, and the container-nesting bug (empty styled boxes from `st.markdown` div pairs that don't nest across Streamlit widget calls) fixed and verified via mandatory Playwright screenshot capture at three viewports — see `DECISION_LOG.md` for how that bug shipped silently through source-review-only checks and what changed.
- Question-and-answer conversational pairing fixed: each deterministic question is now persisted to the chat transcript as an assistant turn before the user answers, so the scrollback reads as an alternating conversation, not a cluster of disconnected user answers.
- Free-text injection guardrails implemented in four layers: 300-character cap (UI + defensive), a deterministic regex pre-screen (`screen_free_text`) that strips flagged text before it reaches the brief, an additive system-prompt hardening instruction, and confirmation that no free-text input surface exists once a plan has been generated.
- Streamlit loads into a no-key setup state and keeps keys server-side.
- CLI supports brief listing, model/iteration overrides, JSON output, output file writing, and readable setup errors.
- Offline checks run locally: compileall, pytest, offline fixture eval, CLI help, brief list, and database integrity checks.
- Live-eval cost controls are implemented: full runs require explicit `--all --confirm-full-live`, multi-case live runs require confirmation, judge calls require `--confirm-judge-cost`, and usage/cost-guard reporting is wired into eval reports.
- Existing saved live artifacts were preserved and summarized without regenerating results.

## Honest Current Gap: Live Evaluation

- A real-key BR-01 baseline run and a 7-case no-judge trap-set run completed successfully in an earlier
  session (see `docs/EVAL_RESULTS.md`). One case-level issue (`db-br-06`, a stale final-budget-check
  trace entry) was found and documented, not hidden.
- **The full 25-case live run and the judged run have still not been completed**, as of this session.
  This session was scoped to run the full judged evaluation, but the user reported no available
  Anthropic API credit budget and asked to skip all live/paid calls. No live API calls were made this
  session. This is the true, current state — not a stale placeholder.
- No live model quality or ship-gate success is claimed beyond the small documented sample above.

## Next Steps Requiring an Anthropic Key And Available Budget

- Run the full judged evaluation: `python evals/run_evals.py --all --confirm-full-live --confirm-judge-cost` (see `docs/LIVE_TEST_RUNBOOK.md`).
- Update `docs/EVAL_RESULTS.md` with the real results once that run completes.
- Resume with one affected case at a time if failures are found; use `--resume-from` / `--failed-only` rather than rerunning passed cases.

## Awaiting User-Owned Deployment/Recording Actions

- Connect the repo to Streamlit Community Cloud and set the `ANTHROPIC_API_KEY` secret (see README "Deploy" section).
- Record the demo.
- Once the full judged run above completes, attach the report and disclose any failed cases.
