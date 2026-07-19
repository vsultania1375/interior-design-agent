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
