from __future__ import annotations

from typing import Any

from interior_agent.schemas import BOQLine, ValidatedPlan


SAMPLE_NAMES = {
    "BR-01": "Calm Scandinavian Living Room",
    "BR-02": "Compact Family Living Room",
    "BR-05": "Warm Bohemian Living Room",
    "BR-06": "Budget-Friendly Starter Living Room",
    "BR-07": "Industrial Open-Plan Living Room",
    "BR-08": "Designer-Inspired Living Room",
    "BR-09": "Small Studio Stress Test",
    "BR-14": "Premium Statement Living Room",
}


def format_inr(value: int | float | None) -> str:
    if value is None:
        return "Price on request"
    amount = int(value)
    sign = "-" if amount < 0 else ""
    text = str(abs(amount))
    if len(text) <= 3:
        grouped = text
    else:
        grouped = text[-3:]
        text = text[:-3]
        while text:
            grouped = text[-2:] + "," + grouped
            text = text[:-2]
    return f"{sign}₹{grouped}"


def sample_display_name(brief: dict[str, Any]) -> str:
    brief_id = str(brief.get("brief_id") or "")
    return SAMPLE_NAMES.get(brief_id, f"{brief.get('style_preference', 'Practical')} Living Room")


def dimensions_label(length_cm: int | None, width_cm: int | None) -> str:
    if not length_cm or not width_cm:
        return "Room size not set"
    return f"{length_cm} × {width_cm} cm"


def brief_summary(brief: Any) -> list[tuple[str, str]]:
    return [
        ("Room", "Living room"),
        ("Size", dimensions_label(brief.length_cm, brief.width_cm)),
        ("Budget", format_inr(brief.budget_inr)),
        ("Style", brief.style_preference or "Not selected"),
        ("Must-haves", ", ".join(brief.must_haves) if brief.must_haves else "None selected"),
        ("Constraints", ", ".join(brief.constraints) if brief.constraints else "None"),
    ]


def status_label(validated: ValidatedPlan, converged: bool = True) -> tuple[str, str]:
    if not converged:
        return "Review required", "The planning loop did not fully converge."
    if validated.is_valid and validated.plan.status.value == "complete":
        return "Complete plan", "Ready for customer review."
    if validated.is_valid:
        return "Honest partial plan", "The plan is usable but includes stated limits."
    return "Review required", "Some items need review before purchase."


def price_copy(line: BOQLine) -> str:
    if line.unit_price_inr is None:
        return "Price on request — not included in the estimated total."
    return format_inr(line.unit_price_inr)


def line_total_copy(line: BOQLine) -> str:
    if line.line_total_inr is None:
        return "Price on request"
    return format_inr(line.line_total_inr)


def availability_copy(line: BOQLine) -> str:
    stock = "In stock" if line.in_stock else "Unavailable"
    lead = "Lead time unknown" if line.lead_time_days is None else f"{line.lead_time_days} days"
    return f"{stock} • {lead}"


def normal_result_text(validated: ValidatedPlan) -> dict[str, Any]:
    return {
        "title": f"Your {validated.plan.room_type}",
        "summary": validated.plan.design_summary,
        "estimated_cost": format_inr(validated.known_total_inr),
        "remaining": format_inr(validated.remaining_inr),
        "remaining_label": "Known-price budget left" if validated.has_unknown_prices else "Budget left",
        "product_count": sum(line.quantity for line in validated.boq),
        "things_to_review": [issue.message for issue in validated.issues],
    }
