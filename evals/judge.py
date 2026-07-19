from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any


JUDGE_SYSTEM_PROMPT = """You are an evaluation judge for a catalog-grounded interior design agent.
Score only the quality of the final explanation and design coherence. Do not repair the plan, add products, or reward violations that deterministic validators should catch.

Use this written rubric, each dimension from 1 to 5:
1. style_coherence: the selected finishes and forms respond coherently to the requested style; any relaxation is disclosed.
2. rationale_quality: the reasoning connects major choices to room, customer context, budget, and practical constraints instead of merely repeating names.
3. tradeoff_honesty: omissions, uncertainty, unavailable products, impossible asks, and scope limits are plainly stated.
4. actionability: the customer can understand the concept and placement notes, while the empty-rectangle layout limitation remains clear.

Return only JSON:
{
  "style_coherence": 1,
  "rationale_quality": 1,
  "tradeoff_honesty": 1,
  "actionability": 1,
  "overall": 1.0,
  "rationale": "brief evidence-based explanation"
}
The overall score must be the arithmetic mean of the four dimensions, rounded to one decimal place.
"""


@dataclass
class JudgeScore:
    style_coherence: int
    rationale_quality: int
    tradeoff_honesty: int
    actionability: int
    overall: float
    rationale: str

    @property
    def passed(self) -> bool:
        return self.overall >= 4.0


def _parse_json(text: str) -> dict[str, Any]:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        start, end = cleaned.find("{"), cleaned.rfind("}")
        if start >= 0 and end > start:
            return json.loads(cleaned[start : end + 1])
        raise


def score_with_anthropic(*, api_key: str, model: str, brief: dict[str, Any], validated_plan: dict[str, Any]) -> JudgeScore:
    try:
        from anthropic import Anthropic
    except ImportError as exc:
        raise RuntimeError("Install requirements.txt before running the judgement scorer.") from exc

    payload = {
        "brief": brief,
        "final_plan": validated_plan.get("plan"),
        "boq": validated_plan.get("boq"),
        "validator_issues": validated_plan.get("issues"),
        "fit_summary": {
            "fits": validated_plan.get("fit_result", {}).get("fits"),
            "assumption": validated_plan.get("fit_result", {}).get("assumption"),
        },
    }
    client = Anthropic(api_key=api_key)
    response = client.messages.create(
        model=model,
        max_tokens=700,
        system=JUDGE_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": json.dumps(payload, ensure_ascii=False)}],
    )
    text = "".join(getattr(block, "text", "") for block in response.content if getattr(block, "type", None) == "text")
    raw = _parse_json(text)
    dimensions = {
        key: max(1, min(5, int(raw[key])))
        for key in ("style_coherence", "rationale_quality", "tradeoff_honesty", "actionability")
    }
    computed_overall = round(sum(dimensions.values()) / 4, 1)
    return JudgeScore(
        **dimensions,
        overall=computed_overall,
        rationale=str(raw.get("rationale", ""))[:1200],
    )
