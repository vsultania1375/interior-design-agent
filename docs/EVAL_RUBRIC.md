# Judgement Scorer Rubric

Use one LLM-as-judge call per completed case after deterministic checks. The judge receives only the customer brief, validated catalog facts for selected items, and the final rationale. It must not repair the answer.

Score 1–5 on:

1. **Style coherence** — selections and finishes form a recognisable response to the requested style; any style relaxation is disclosed.
2. **Rationale quality** — explains why the major choices fit the customer context instead of repeating product names.
3. **Trade-off honesty** — clearly states what was omitted, relaxed, unavailable, or uncertain.
4. **Actionability** — plan and placement notes are understandable enough for a customer to act on, within the stated empty-rectangle limitation.

Overall score is the rounded mean. Ship gate: overall score at least 4/5 on at least 90% of cases.

Risks to disclose:

- A judge from the same model family may share biases with the agent.
- Subjective style scoring is less stable than catalog, budget, fit, and trace checks.
- Run trap cases more than once and report variance rather than presenting one lucky pass.
