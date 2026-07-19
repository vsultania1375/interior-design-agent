from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any, Callable, Protocol

from .prompts import SYSTEM_PROMPT, brief_to_text
from .schemas import DesignPlan, TraceEntry, ValidatedPlan
from .tools import AgentTools, TOOL_SCHEMAS
from .validator import PlanValidator


TraceCallback = Callable[[TraceEntry], None]


class MessagesClient(Protocol):
    def create(self, **kwargs: Any) -> Any: ...


@dataclass
class AgentRunResult:
    raw_plan: DesignPlan
    validated: ValidatedPlan
    trace: list[TraceEntry]
    iterations: int
    converged: bool
    loop_issues: list[str]


class InteriorDesignAgent:
    def __init__(
        self,
        *,
        tools: AgentTools,
        validator: PlanValidator,
        api_key: str,
        model: str,
        max_iterations: int = 15,
        client: Any | None = None,
    ):
        if client is None and not api_key:
            raise ValueError("ANTHROPIC_API_KEY is required to run the live agent.")
        self.tools = tools
        self.validator = validator
        self.model = model
        self.max_iterations = max_iterations
        if client is None:
            try:
                from anthropic import Anthropic
            except ImportError as exc:
                raise RuntimeError("Install requirements.txt before running the live agent.") from exc
            self.client = Anthropic(api_key=api_key)
        else:
            self.client = client

    @staticmethod
    def _parse_json(text: str) -> dict[str, Any]:
        cleaned = text.strip()
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
            cleaned = re.sub(r"\s*```$", "", cleaned)
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            start = cleaned.find("{")
            end = cleaned.rfind("}")
            if start >= 0 and end > start:
                return json.loads(cleaned[start : end + 1])
            raise

    @staticmethod
    def _partial_plan_from_trace(brief: dict[str, Any], trace: list[TraceEntry], issues: list[str]) -> DesignPlan:
        last_items: list[dict[str, Any]] = []
        for entry in reversed(trace):
            if entry.tool in {"check_budget", "check_fit"}:
                last_items = entry.input.get("items", [])
                if isinstance(last_items, list) and last_items:
                    break
                last_items = []
        return DesignPlan.model_validate({
            "brief_id": brief.get("brief_id"),
            "room_type": brief.get("room_type", "Unknown"),
            "status": "partial",
            "design_summary": "The agent did not produce a fully validated complete plan.",
            "budget_inr": int(brief.get("budget_inr", 0)),
            "items": [
                {
                    "item_id": item["item_id"],
                    "quantity": item.get("quantity", 1),
                    "rationale": "Candidate retained from the last tool-checked selection; manual review required.",
                    "placement_note": None,
                }
                for item in last_items
            ],
            "tradeoffs": ["Returned the latest tool-checked candidate set rather than a raw error."],
            "flags": issues or ["Agent did not fully converge within the iteration cap."],
            "assumptions": ["Room treated as an empty rectangle."],
            "style_relaxations": [],
            "declined_scope": [],
        })

    def run(self, brief: dict[str, Any], on_trace: TraceCallback | None = None) -> AgentRunResult:
        messages: list[dict[str, Any]] = [{
            "role": "user",
            "content": [{
                "type": "text",
                "text": brief_to_text(brief),
            }],
        }]
        trace: list[TraceEntry] = []
        final_plan: DesignPlan | None = None
        converged = False
        iterations = 0
        loop_issues: list[str] = []

        for iteration in range(1, self.max_iterations + 1):
            iterations = iteration
            response = self.client.messages.create(
                model=self.model,
                max_tokens=2600,
                system=[{
                    "type": "text",
                    "text": SYSTEM_PROMPT,
                    "cache_control": {"type": "ephemeral"},
                }],
                tools=TOOL_SCHEMAS,
                messages=messages,
            )
            messages.append({"role": "assistant", "content": response.content})

            tool_blocks = [block for block in response.content if getattr(block, "type", None) == "tool_use"]
            if tool_blocks:
                tool_results = []
                for block in tool_blocks:
                    result = self.tools.execute(block.name, dict(block.input))
                    entry = TraceEntry(iteration=iteration, tool=block.name, input=dict(block.input), result=result)
                    trace.append(entry)
                    if on_trace:
                        on_trace(entry)
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": json.dumps(result, ensure_ascii=False),
                    })
                messages.append({"role": "user", "content": tool_results})
                continue

            text = "".join(getattr(block, "text", "") for block in response.content if getattr(block, "type", None) == "text")
            if text:
                try:
                    final_plan = DesignPlan.model_validate(self._parse_json(text))
                    if not trace:
                        loop_issues.append("Terminal answer contained zero tool calls; plan requires validator review.")
                    converged = bool(trace)
                    break
                except Exception as exc:
                    loop_issues.append(f"Terminal JSON parse/validation failed: {exc}")
            break

        if final_plan is None:
            if not loop_issues and iterations >= self.max_iterations:
                loop_issues.append("Agent reached the iteration cap before final JSON.")
            final_plan = self._partial_plan_from_trace(brief, trace, loop_issues)

        brief_text = json.dumps(brief, ensure_ascii=False)
        validated = self.validator.validate(
            final_plan,
            room_length_cm=int(brief.get("length_cm", 0)),
            room_width_cm=int(brief.get("width_cm", 0)),
            must_haves=str(brief.get("must_haves", "")),
            brief_text=brief_text,
            trace=trace,
            loop_issues=loop_issues,
        )
        return AgentRunResult(
            raw_plan=final_plan,
            validated=validated,
            trace=trace,
            iterations=iterations,
            converged=converged,
            loop_issues=loop_issues,
        )
