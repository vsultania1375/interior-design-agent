# Live Test Runbook

Full live runs can consume significant Anthropic credits. A single case may involve multiple model calls; judged runs add additional model calls. Run offline tests first, run one affected case after each change, and use `--resume-from` or `--failed-only` instead of rerunning passed cases.

## 1. Setup

```bash
cp .env.example .env
```

Add the Anthropic API key manually:

```text
ANTHROPIC_API_KEY=<your-key>
ANTHROPIC_MODEL=<configured-model-id>
MAX_AGENT_ITERATIONS=8
ANTHROPIC_MAX_TOKENS=3000
LIVE_EVAL_MAX_OUTPUT_TOKENS=20000
```

## 2. Baseline

```bash
python cli.py BR-01
```

## 2a. Browser UI — Live Mode Manual Test

Launch the Streamlit app itself in **live mode** (not demo mode) for manual, click-through testing in a
browser. This is different from the CLI/eval commands above — it starts the actual customer-facing
consultation UI, backed by the real agent.

```bash
python3 -m streamlit run app.py \
  --server.headless true \
  --server.address 127.0.0.1 \
  --server.port 8900
```

Notes:

- Do **not** set `INTERIOR_UI_DEMO_MODE=1` and do **not** set `INTERIOR_SKIP_DOTENV=1` for this command —
  leaving both unset is what lets `.env` load normally and the real `ANTHROPIC_API_KEY` resolve.
- **This mode makes real, billed Anthropic API calls the moment "Create my room plan" is clicked** in
  the browser, for a custom (non-sample) brief. There is no demo-mode safety net once this command is
  running with a real key loaded — treat every click of that button as a real spend.
- Verify health only with `curl -fsS http://127.0.0.1:8900/_stcore/health` before interacting — do not
  click through the consultation yourself if an agent is doing this handoff; leave the actual
  "Create my room plan" click to the human who owns the API budget.
- To go back to the zero-credit demo-mode preview instead, use the separate command documented in
  `README.md` (`INTERIOR_UI_DEMO_MODE=1`, which forces `api_key=""` and disables custom-brief
  generation regardless of any key present in `.env`).

## 3. One Trap Case

```bash
python evals/run_evals.py \
  --case db-br-06 \
  --skip-judge
```

## 4. Safe Three-Case Calibration

```bash
python evals/run_evals.py \
  --case db-br-06 \
  --case db-br-09 \
  --case db-br-13 \
  --skip-judge \
  --confirm-multi-case-live
```

## 5. Full No-Judge Run

```bash
python evals/run_evals.py \
  --all \
  --skip-judge \
  --confirm-full-live
```

## 6. Full Judged Run

```bash
python evals/run_evals.py \
  --all \
  --confirm-full-live \
  --confirm-judge-cost
```

## 7. Resume Without Rerunning Passed Cases

```bash
python evals/run_evals.py \
  --resume-from eval_results/results.json \
  --skip-judge \
  --confirm-multi-case-live

python evals/run_evals.py \
  --failed-only eval_results/results.json \
  --skip-judge \
  --confirm-multi-case-live
```

## 8. Inspect Failures

```bash
less eval_results/results.md
```

Check case-level scores, validator issues, trace length, iteration count, convergence state, failure diagnosis, and reported token usage. Do not treat skipped judge gates as passing.

## 9. What May Be Tuned

- System prompt.
- Tool descriptions.
- SDK compatibility.
- Parsing robustness.
- Deterministic thresholds only when evidence justifies the change.

## 10. What Must Not Be Tuned Merely To Hide A Failure

- Catalog facts.
- Expected guardrails.
- Budget math.
- Item IDs.
- Golden-set outcomes after seeing outputs without documenting the change.
- Fake trace entries.
- Required tool/validator checks.

## 11. Calibration Log Template

```text
Case:
Observed failure:
Root cause:
Intervention:
Before/after result:
General or case-specific:
```
