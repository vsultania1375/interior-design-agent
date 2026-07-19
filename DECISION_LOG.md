# Decision Log

## Scope In/Out

The build is a single-room, catalog-grounded planning agent. It searches the supplied SQLite catalog, computes a quantity-aware BOQ, checks deterministic fit, refuses unsafe/out-of-scope advice, and returns structured JSON for a Streamlit UI and CLI. Out of scope: auth, multi-user support, vector DB/RAG, MCP, 3D rendering, moodboards, construction guidance, live inventory reservation, taxes, discounts, delivery promises, and negotiated prices.

**Living Room was chosen as the primary depth slice over broad shallow coverage** because the catalog has the richest seating, tables, rugs, lighting, and media-unit coverage there. This held up through the whole project: every later round (live integration, UI rebuild, guardrails) was built and verified against Living Room first. Bedroom/Dining/Study/Kids briefs remain runnable and degrade honestly rather than pretending equal depth.

## Live Agent Integration And Eval Calibration

Plain Python tools (catalog search, budget check, fit check) were used instead of MCP/RAG — the catalog is a small structured SQLite file, so deterministic SQL and code-side math are simpler, auditable, and safe for a private repo. Catalog membership, quantities, totals, unknown prices, stock, fit, and required refusals are all **recomputed in code**, not self-certified by the model. Live integration required SDK compatibility handling for tool-schema/cache behavior; a real-key BR-01 baseline and a 7-case no-judge trap-set both passed, with one honestly documented case-level gap (`db-br-06`: a stale final-budget-check trace entry in that run — a real agent-discipline issue, not a scorer bug). A full 25-case live run was started once and interrupted before completion; strict cost controls (`--confirm-full-live`, `--confirm-judge-cost`, multi-case confirmation, usage reporting) were added afterward specifically so that incident couldn't repeat silently. See `docs/LIVE_RUN_COST_INCIDENT.md` and `docs/EVAL_RESULTS.md`.

## The UI Rebuild Arc — And The Bug That Shipped Silently

The customer-facing Streamlit UI went through several iteration rounds (conversational flow, layout density, full-height dual-pane rebuild with a resizable panel divider). For multiple of those rounds, a real bug shipped and was reported as fixed based on **source review alone**: `st.markdown(html, unsafe_allow_html=True)` was used to open a styled `<div>` in one call and close it in a separate later call, with native Streamlit widgets rendered in between. Streamlit does not nest across separate `st.markdown` calls — each is an independent sibling — so the result was an empty styled box followed by the real widgets rendering unstyled below it. This is exactly the kind of thing that reads as correct in a diff and is wrong on screen, and it passed several rounds precisely because verification was "does the code look right," not "does the rendered page look right." The fix was mandatory Playwright screenshot verification at multiple real viewports before any round could be called done, plus real mouse-drag simulation to verify the resizable divider actually reflows (not just that the CSS property is present). This is the same "prove it, don't just claim it" discipline the challenge brief asks for applied to the agent's plans — applied here to the UI instead.

## Free-Text Injection Guardrails

Customer free text (the context-step note, custom "something else" requirements) flows into the brief sent to the live agent. Four layers were added: a 300-character cap (UI parameter plus defensive truncation in code, so a bypassed widget can't defeat it), a deterministic regex pre-screen (`screen_free_text`) that strips text matching known injection patterns before it ever reaches the brief, an additive system-prompt instruction that free-text fields are always descriptive customer input and never instructions, and confirmation that no free-text input surface exists once a plan has been generated. **Honest limitation:** the regex screen is a first-layer, pattern-based defense — it will not catch paraphrased or obfuscated injection attempts outside its known patterns. The prompt hardening is the intended second layer for anything that slips through the first. This is not claimed as complete protection.

## Final Eval Results

A full 25-case live judged run has not been completed — see `docs/EVAL_RESULTS.md` for the honest breakdown of what has and hasn't been verified (offline harness: 25/25 executed at zero cost; live: BR-01 + a 7-case no-judge sample only). The subjective judge gate (≥4/5 on ≥90% of judged cases) has never been evaluated.

## What Would Break In Production

Fit is an empty-rectangle heuristic — no doors, windows, columns, or services. The consultation is a single-shot brief with no revision loop once a plan is generated. No Vastu rules. No delivery cost or GST-inclusive pricing. Stock and lead times are catalog snapshots, not live inventory. Unknown prices stay price-on-request and are never treated as zero or as a guaranteed-complete-within-budget plan.

## What's Next, In Priority Order

1. **Multi-turn plan revision** — let the customer adjust an existing plan (swap an item, nudge budget) without restarting the whole brief; currently single-shot.
2. **Richer injection defense** — semantic/LLM-assisted screening layered on top of the current regex pre-screen, given its documented pattern-matching limitation above.
3. The remaining original roadmap items: door/window-aware fit, Vastu-aware placement rules, delivery/GST-inclusive pricing, live inventory sync.
4. The outstanding full judged evaluation run, once API budget is available (see `docs/LIVE_TEST_RUNBOOK.md`).

## AI Tooling Used

Both **Codex** and **Claude Code** were used across this project. Codex was used for the early backend build and live-integration calibration (catalog tools, agent loop, the SDK tool-schema/cache compatibility fix that let BR-01 complete live). Claude Code was used for the UI rebuild and the guardrail/eval-documentation work in this session. Concrete catch-and-correct examples:
- **Claude Code:** caught the container-nesting bug above via mandatory screenshot verification after it had shipped silently through prior source-review-only rounds, and fixed it by replacing the split `st.markdown` div pairs with real `st.container(key=...)` blocks.
- **Codex:** caught and fixed the live SDK tool-schema/cache compatibility issue during initial live calibration that was blocking BR-01 from completing against the real Anthropic API, before the eval cost-safety controls existed.
