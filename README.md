# Interior Design AI Agent

Catalog-grounded AI Interior Design Agent for the confidential APM build challenge. It turns a single room brief into a structured design plan and quantity-aware BOQ using the supplied SQLite catalog, deterministic budget math, and a transparent empty-rectangle fit heuristic.

Live design quality is not claimed until an Anthropic key is supplied and the live eval run is recorded.

## Project Status

- **What's built and working:** the full agent loop (catalog search, budget check, fit check,
  re-planning, structured JSON output), a deterministic validator that recomputes every guardrail in
  code rather than trusting the model, a conversational Streamlit UI (full-height dual-pane layout with
  a resizable panel, alternating assistant/user chat log, a 2D room-layout visualization), and four
  layers of free-text injection guardrails on customer notes. 119/119 offline tests pass and the 25-case
  offline fixture harness runs clean. Proof and honest caveats: [`docs/EVAL_RESULTS.md`](docs/EVAL_RESULTS.md).
- **Eval harness — how to reproduce:** offline (free, no API key): `pytest -q` then
  `python evals/run_evals.py --offline-fixtures`. Live (costs real API credits, requires
  `ANTHROPIC_API_KEY`): see [`docs/LIVE_TEST_RUNBOOK.md`](docs/LIVE_TEST_RUNBOOK.md) for the exact,
  safety-gated commands — start with one case (`--case db-br-01 --skip-judge`) before anything larger.
- **Decisions and the full project arc:** [`DECISION_LOG.md`](DECISION_LOG.md) — scope choice, live
  integration, the UI rebuild arc (including a container-nesting bug that shipped silently through
  several rounds until mandatory screenshot verification caught it), the injection guardrail layers and
  their honest limits, and what's next.
- **Known limitations:** see "What Would Break In Production" in [`DECISION_LOG.md`](DECISION_LOG.md#what-would-break-in-production) —
  in short, no door/window-aware layout, no Vastu rules, no delivery/GST pricing, snapshot-only stock
  data, and a ship gate that scores budget safety but not budget-utilization quality.

## Scope

In scope: single-room catalog plans, budget checks, fit checks, stock/lead-time disclosure, unknown-price handling, re-planning after rejected tool calls, and refusals for structural/electrical/plumbing or delivery/price guarantees.

Out of scope: authentication, multi-user state, vector search, MCP, 3D rendering, moodboards, delivery promises, negotiated prices, construction advice, and CAD-grade layouts.

## Architecture

- `src/interior_agent/db.py`: read-only SQLite access.
- `src/interior_agent/tools.py`: catalog search, budget check, fit check.
- `src/interior_agent/agent.py`: Anthropic tool-calling loop with injectable client for offline tests.
- `src/interior_agent/validator.py`: deterministic post-generation guardrails.
- `evals/`: golden set, case-aware scorers, offline fixtures, ship gate.
- `app.py`: Streamlit customer consultation UI.
- `src/interior_agent/ui/`: Streamlit state, customer presenters, offline demo result, and deterministic 2D layout helpers.
- `cli.py`: terminal runner.

The system is agentic because the model must call tools, inspect tool results, re-plan when rejected, then emit final JSON that is independently revalidated.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

For local development (adds Playwright, used only by the dev-only `scripts/capture_ui.py` screenshot
tool — not required to run the app itself and not installed on Streamlit Cloud):

```bash
python -m pip install -r requirements-dev.txt
python3 -m playwright install chromium
```

For live runs:

```bash
cp .env.example .env
# Add ANTHROPIC_API_KEY manually.
```

For Streamlit Cloud, use `.streamlit/secrets.toml.example` as the shape for Secrets. Do not commit real keys or `.streamlit/secrets.toml`.

## CLI

```bash
python cli.py --list-briefs
python cli.py BR-01
python cli.py BR-01 --model "$ANTHROPIC_MODEL" --max-iterations 15
python cli.py BR-01 --json --output local_result.json
```

`python cli.py BR-01` remains the simple live command. It requires `ANTHROPIC_API_KEY`.

## Streamlit

```bash
streamlit run app.py
```

The default Streamlit experience is a living-room consultation: one question at a time, clickable answer cards, optional free text, a review step before any live model call, a customer-facing result screen, and a deterministic 2D room map. Developer Mode keeps raw trace, tool inputs/outputs, validator codes, usage totals, and structured JSON hidden unless explicitly enabled.

Zero-credit UI preview:

```bash
ANTHROPIC_API_KEY= \
INTERIOR_UI_DEMO_MODE=1 \
python3 -m streamlit run app.py \
  --server.headless true \
  --server.address 127.0.0.1 \
  --server.port 8900
```

In demo mode the result is generated from real catalog rows and deterministic validation, but no Anthropic client is constructed. In normal mode the live agent is available only after the user reaches review and clicks the primary create-plan action.

## Deploy (Streamlit Community Cloud)

The repo is deploy-ready as-is; nothing further needs to change in the code. These are the exact
clicks to connect it, to be done by whoever owns the Streamlit Cloud account:

1. Go to [share.streamlit.io](https://share.streamlit.io) and sign in (GitHub login is simplest, since
   this repo is private).
2. Click **"New app"**.
3. Under **"Deploy a public app from GitHub"** (or "From existing repo"), pick:
   - Repository: `vsultania1375/interior-design-agent`
   - Branch: `main`
   - Main file path: `app.py`
4. Click **"Advanced settings..."** before deploying, and under **Secrets**, paste:

   ```toml
   ANTHROPIC_API_KEY = "your-real-key-here"
   ANTHROPIC_MODEL = "your-configured-model-id"
   ```

   Use `.streamlit/secrets.toml.example` as the shape reference — never commit a real
   `.streamlit/secrets.toml` file.
5. Click **"Deploy"**. Streamlit Cloud installs `requirements.txt` (production dependencies only —
   `playwright` and other dev/screenshot-testing tools live in `requirements-dev.txt` and are not
   installed on the deployed app).
6. The app will be live at a URL of the form `https://<app-name>-<random-suffix>.streamlit.app` (or a
   custom subdomain if one is claimed during setup). Streamlit Cloud shows the exact URL once the build
   finishes.
7. Once live, run the welcome screen and the demo path first (`INTERIOR_UI_DEMO_MODE` is a local-only
   env var for zero-credit preview — the deployed app runs in normal live mode). Then run one live CLI
   case (`python cli.py BR-01`, from a local shell with the same key) before running the full eval
   harness against production, to confirm the deployed key/model combination works end to end.

## Offline Tests

```bash
python -m compileall src app.py cli.py evals
pytest -q
python evals/run_evals.py --offline-fixtures
python cli.py --help
python cli.py --list-briefs
```

Offline fixture reports are written to `eval_results/offline/` and labelled `OFFLINE FIXTURE RUN — NOT LIVE MODEL RESULTS`.

## Live Evals

Full live runs can consume significant credits because one case may involve many model calls, and judge runs add more calls. Run offline tests first, then run one affected case after each change. Do not rerun already passing cases; use `--resume-from` or `--failed-only` when continuing from a saved report.

Single case:

```bash
python evals/run_evals.py --case db-br-01 --skip-judge
```

Safe three-case calibration:

```bash
python evals/run_evals.py \
  --case db-br-06 \
  --case db-br-09 \
  --case db-br-13 \
  --skip-judge \
  --confirm-multi-case-live
```

Full deterministic/trace run:

```bash
python evals/run_evals.py \
  --all \
  --skip-judge \
  --confirm-full-live
```

Full run with judge:

```bash
python evals/run_evals.py \
  --all \
  --confirm-full-live \
  --confirm-judge-cost
```

Resume or failed-only:

```bash
python evals/run_evals.py --resume-from eval_results/results.json --skip-judge --confirm-multi-case-live
python evals/run_evals.py --failed-only eval_results/results.json --skip-judge --confirm-multi-case-live
```

Reports go to `eval_results/results.json` and `eval_results/results.md` unless `--output-dir` is supplied.

## Ship Gate

The ship gate evaluates aggregate thresholds independently:

- 100% real catalog items.
- Zero silent budget violations.
- 100% required scope/guarantee refusals.
- 100% fit violations caught or explicitly flagged.
- 100% runs use catalog search and budget checking.
- Fit checked before finalisation.
- Judge score >= 4/5 on at least 90% of judged cases.

When `--skip-judge` is used, the judge gate is `NOT EVALUATED`, not passed.

## Five-Minute Run

1. `source .venv/bin/activate`
2. `pytest -q`
3. `python evals/run_evals.py --offline-fixtures`
4. Add key to `.env`.
5. `python cli.py BR-01`
6. `python evals/run_evals.py --case db-br-06 --skip-judge`
7. `streamlit run app.py`

## Limitations

The layout checker assumes an empty rectangle and cannot account for doors, windows, columns, electrical points, plumbing, exact placement geometry, delivery geography, taxes, installation, discounts, or live inventory reservation. Stock and lead times are catalog snapshots. Unknown catalog prices remain price-on-request and are never counted as zero.

## Confidentiality

Keep the repository private. The dataset is confidential. Do not commit secrets, eval outputs with sensitive data, local virtual environments, or the original confidential challenge PDF unless explicitly required.
