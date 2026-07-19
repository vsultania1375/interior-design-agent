from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any, Callable, Protocol

from .prompts import SYSTEM_PROMPT, brief_to_text
from .schemas import DesignPlan, TraceEntry, ValidatedPlan
from .tools import AgentTools, TOOL_SCHEMAS
from .validator import PlanValidator


TraceCallback = Callable[[TraceEntry], None]


class MessagesClient(Protocol):
    def create(self, **kwargs: Any) -> Any: ...


@dataclass
class UsageTotals:
    model_calls: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
    cache_creation_tokens: int = 0
    unavailable: bool = False

    def add_response(self, response: Any) -> None:
        self.model_calls += 1
        usage = getattr(response, "usage", None)
        if usage is None:
            self.unavailable = True
            return
        self.input_tokens += int(getattr(usage, "input_tokens", 0) or 0)
        self.output_tokens += int(getattr(usage, "output_tokens", 0) or 0)
        self.cache_read_tokens += int(getattr(usage, "cache_read_input_tokens", 0) or 0)
        self.cache_creation_tokens += int(getattr(usage, "cache_creation_input_tokens", 0) or 0)

    def as_dict(self) -> dict[str, Any]:
        return {
            "model_calls": self.model_calls,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "cache_read_tokens": self.cache_read_tokens,
            "cache_creation_tokens": self.cache_creation_tokens,
            "usage_unavailable": self.unavailable,
        }


@dataclass
class AgentRunResult:
    raw_plan: DesignPlan
    validated: ValidatedPlan
    trace: list[TraceEntry]
    iterations: int
    converged: bool
    loop_issues: list[str]
    usage: UsageTotals = field(default_factory=UsageTotals)


class InteriorDesignAgent:
    def __init__(
        self,
        *,
        tools: AgentTools,
        validator: PlanValidator,
        api_key: str,
        model: str,
        max_iterations: int = 15,
        max_tokens: int = 3000,
        client: Any | None = None,
    ):
        if client is None and not api_key:
            raise ValueError("ANTHROPIC_API_KEY is required to run the live agent.")
        self.tools = tools
        self.validator = validator
        self.model = model
        self.max_iterations = max_iterations
        self.max_tokens = max_tokens
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
        budget_checked: set[tuple[tuple[str, int], ...]] = set()
        fit_checked: set[tuple[tuple[str, int], ...]] = set()

        def key(raw_items: Any) -> tuple[tuple[str, int], ...]:
            if not isinstance(raw_items, list):
                return ()
            merged: dict[str, int] = {}
            for raw in raw_items:
                if not isinstance(raw, dict):
                    continue
                item_id = str(raw.get("item_id", "")).strip().upper()
                if item_id:
                    merged[item_id] = merged.get(item_id, 0) + int(raw.get("quantity", 1) or 1)
            return tuple(sorted(merged.items()))

        for entry in trace:
            candidate_key = key(entry.input.get("items", []))
            if entry.tool == "check_budget" and candidate_key:
                budget_checked.add(candidate_key)
            elif entry.tool == "check_fit" and candidate_key:
                fit_checked.add(candidate_key)

        for entry in reversed(trace):
            if entry.tool in {"check_budget", "check_fit"}:
                candidate_items = entry.input.get("items", [])
                candidate_key = key(candidate_items)
                if candidate_key and candidate_key in budget_checked and candidate_key in fit_checked:
                    last_items = candidate_items
                    break
        if not last_items:
            for entry in reversed(trace):
                if entry.tool in {"check_budget", "check_fit"}:
                    candidate_items = entry.input.get("items", [])
                    if isinstance(candidate_items, list) and candidate_items:
                        last_items = candidate_items
                        break
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
        usage = UsageTotals()

        for iteration in range(1, self.max_iterations + 1):
            iterations = iteration
            response = self.client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                system=[{
                    "type": "text",
                    "text": SYSTEM_PROMPT,
                    "cache_control": {"type": "ephemeral"},
                }],
                tools=TOOL_SCHEMAS,
                messages=messages,
            )
            usage.add_response(response)
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
            usage=usage,
        )
