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

## Awaiting Anthropic Key/Live Calibration

- Run `python cli.py BR-01` with a real key and inspect the trace.
- Run the trap-set eval without the judge.
- Tune only prompt text, tool descriptions, or evidence-backed deterministic thresholds from observed live failures.
- Run the full 25-case deterministic eval.
- Run the full judge-enabled eval and record honest pass/fail results.

## Awaiting User-Owned Deployment/Recording Actions

- Create or update the private repository.
- Configure deployment secrets in Streamlit Cloud or the chosen private deployment target.
- Deploy the app.
- Record the demo.
- Attach live eval report and disclose any failed cases.
