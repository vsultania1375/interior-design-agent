# Decision Log

## Scope In/Out

The build is a single-room, catalog-grounded planning agent. It searches the supplied SQLite catalog, computes a quantity-aware BOQ, checks deterministic fit, refuses unsafe/out-of-scope advice, and returns structured JSON for a Streamlit UI and CLI.

Out of scope: auth, multi-user support, vector DB/RAG, MCP, 3D rendering, moodboards, construction guidance, live inventory reservation, taxes, discounts, delivery promises, and negotiated prices.

## Primary Slice

Living Room is the primary quality slice because the catalog has the richest seating, tables, rugs, lighting, and media-unit coverage. Bedroom, Dining, Study, and Kids briefs remain runnable and are expected to degrade honestly when catalog coverage or room constraints are weak.

## Tooling Choice

Plain Python tools were used instead of MCP or RAG because the challenge data is a small structured SQLite catalog. SQL queries, deterministic budget math, and deterministic fit checks are simpler, auditable, and private-repo safe.

## Code Overrides Model Behavior

Catalog membership, quantities, budget totals, unknown prices, stock, lead time, fit, final trace consistency, must-have coverage, duplicate item IDs, and required refusals are recomputed in code. The model is not trusted to self-certify those guardrails.

Live integration added SDK compatibility handling for tool-schema/cache behavior and confirmed BR-01 can complete with a real Anthropic key. Cost controls now prevent accidental full live runs: one explicit case is allowed, multi-case and full runs require explicit confirmation flags, judge calls require a separate confirmation, and usage totals are reported when Anthropic returns them.

## Fit and Data Limits

Fit is an empty-rectangle heuristic with category clearances and occupancy thresholds. It is not a floor plan and does not know doors, windows, columns, services, exact placement, accessibility, or installation constraints. Unknown prices stay price-on-request and cannot support a guaranteed complete within-budget plan. Out-of-stock products must be omitted or clearly described as unavailable references.

## Prompt Injection

Customer notes are included as data inside the brief. System instructions and validator checks continue to enforce catalog grounding, budget, fit, refusals, and no guarantees even if the note asks the model to ignore them.

## Still Unverified

Live BR-01 passed in an earlier calibration session, and saved trap-set reports exist, but the full 25-case run was interrupted and no judged run has completed. The project does not yet claim full live ship-gate success. Remaining uncertainty is live tool selection across all cases, prompt adherence, JSON reliability, re-planning consistency, and judge-scored style/rationale quality.

## Next

With a key: run one affected case, use explicit confirmation flags for intentional calibration batches, run the full deterministic eval only with `--all --confirm-full-live`, run the judge eval only with `--confirm-judge-cost`, deploy privately, and record the demo.
