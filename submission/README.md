# Submission

This is a catalog-grounded interior design planning agent that searches a supplied SQLite
furniture catalog, builds a quantity-aware bill of quantities within budget, checks deterministic
room fit, and returns a structured plan via a Streamlit UI and CLI. The build scope was narrowed to
**Living Room only** as the primary depth slice: the catalog has the richest seating, tables, rugs,
lighting, and media-unit coverage there, and every later round of work (live agent integration, UI
rebuild, injection guardrails) was built and verified against Living Room first. Other room types
(Bedroom/Dining/Study/Kids) remain runnable but degrade honestly rather than claiming equal depth.
See `DECISION_LOG.md` in this folder for the full reasoning.

- Deployed app: [DEPLOYED_URL_HERE]
- GitHub repo: [REPO_URL_HERE]
- Video walkthrough: [VIDEO_URL_HERE]

## What's in this folder

- `DECISION_LOG.md` — scope, architecture, and tradeoff decisions made across the project
- `docs/EVAL_RESULTS.md` — offline and live evaluation results
- `docs/LIVE_TEST_RUNBOOK.md` — how the live (real API) evaluation runs are performed
- `screenshots/` — consultation-flow, trap-case, eval-results, and Details-tab screenshots
- `video/` — link to the recorded video walkthrough

For instructions on how to install, configure, and run the project itself, see the repo's own
`README.md` at the project root.
