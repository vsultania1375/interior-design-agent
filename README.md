# Interior Design AI Agent

Catalog-grounded AI Interior Design Agent for the confidential APM build challenge. It turns a single room brief into a structured design plan and quantity-aware BOQ using the supplied SQLite catalog, deterministic budget math, and a transparent empty-rectangle fit heuristic.

Live design quality is not claimed until an Anthropic key is supplied and the live eval run is recorded.

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

## Streamlit Cloud deployment

1. Create a new Streamlit Community Cloud app.
2. Select private repository: `vsultania1375/interior-design-agent`
3. Branch: `main`
4. Main file: `app.py`
5. In Advanced settings -> Secrets, add:

   ```toml
   ANTHROPIC_API_KEY = "..."
   ANTHROPIC_MODEL = "..."
   ```

6. Deploy.
7. Run BR-01 before running the complete eval harness.

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
