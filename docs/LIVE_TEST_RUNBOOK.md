# Live Test Runbook

## 1. Setup

```bash
cp .env.example .env
```

Add the Anthropic API key manually:

```text
ANTHROPIC_API_KEY=<your-key>
```

## 2. Baseline

```bash
python cli.py BR-01
```

Inspect the trace for catalog search, budget check, fit check, convergence, and validator issues.

## 3. Trap Cases

```bash
python evals/run_evals.py --case db-br-06 --case db-br-07 --case db-br-08 --case db-br-09 --case db-br-10 --case db-br-13 --case db-br-14 --skip-judge
```

## 4. Full Deterministic/Trace Calibration Run

```bash
python evals/run_evals.py --skip-judge
```

## 5. Full Run With Judge

```bash
python evals/run_evals.py
```

## 6. Inspect Failures

Open:

```bash
less eval_results/results.md
```

Check case-level scores, validator issues, trace length, iteration count, convergence state, and failure diagnosis.

## 7. What May Be Tuned

- System prompt.
- Tool descriptions.
- Deterministic thresholds when evidence justifies the change.

## 8. What Must Not Be Tuned Merely To Hide A Failure

- Catalog facts.
- Expected guardrails.
- Budget math.
- Item IDs.
- Golden-set outcomes after seeing outputs without documenting the change.

## 9. Calibration Log Template

```text
Case:
Observed failure:
Root cause:
Intervention:
Before/after result:
General or case-specific:
```
