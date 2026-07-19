from __future__ import annotations

import re
from datetime import date, timedelta
from typing import Iterable

from .db import CatalogRepository
from .must_haves import evaluate_must_haves
from .schemas import BOQLine, DesignPlan, TraceEntry, ValidatedPlan, ValidationIssue
from .tools import AgentTools


class PlanValidator:
    def __init__(self, repository: CatalogRepository):
        self.repository = repository
        self.tools = AgentTools(repository)

    @staticmethod
    def _required_declines(brief_text: str) -> set[str]:
        text = brief_text.lower()
        required: set[str] = set()
        if re.search(r"load[- ]?bearing|knock down|remove (?:this|the|a) wall|structural|civil advice", text):
            required.add("structural")
        if re.search(r"rewir|electrical|socket|circuit|power point", text):
            required.add("electrical")
        if re.search(r"plumb|pipe|drain|water line", text):
            required.add("plumbing")
        if re.search(r"guarantee.*deliver|delivery.*guarantee|promise.*deliver", text):
            required.add("delivery_guarantee")
        if re.search(r"lock.*price|guarantee.*price|final discounted price", text):
            required.add("price_guarantee")
        return required

    @staticmethod
    def _selection_key(items: Iterable[dict[str, object]]) -> tuple[tuple[str, int], ...]:
        totals: dict[str, int] = {}
        if not isinstance(items, list):
            return ()
        for item in items:
            if not isinstance(item, dict):
                continue
            item_id = str(item.get("item_id", "")).strip().upper()
            if item_id:
                totals[item_id] = totals.get(item_id, 0) + int(item.get("quantity", 1) or 1)
        return tuple(sorted(totals.items()))

    @staticmethod
    def _deadline_days(text: str) -> int | None:
        lowered = text.lower()
        match = re.search(r"\b(?:in|within|before)\s+(\d+)\s+days?\b", lowered)
        if match:
            return int(match.group(1))
        match = re.search(r"\b(?:in|within|before)\s+(\d+)\s+weeks?\b", lowered)
        if match:
            return int(match.group(1)) * 7
        match = re.search(r"\b(\d+)\s+days?\b", lowered)
        if match:
            return int(match.group(1))
        match = re.search(r"\b(\d+)\s+weeks?\b", lowered)
        if match:
            return int(match.group(1)) * 7
        match = re.search(r"\b(?:before|by)\s+the\s+(\d{1,2})(?:st|nd|rd|th)?\b", lowered)
        if match:
            target = date(date.today().year, date.today().month, int(match.group(1)))
            if target < date.today():
                target = date(target.year, target.month % 12 + 1, target.day)
            return max(0, (target - date.today()).days)
        return None

    def validate(
        self,
        plan: DesignPlan,
        *,
        room_length_cm: int,
        room_width_cm: int,
        must_haves: str,
        brief_text: str,
        trace: Iterable[TraceEntry] = (),
        loop_issues: Iterable[str] = (),
    ) -> ValidatedPlan:
        issues: list[ValidationIssue] = []
        disclosure_text = " ".join(
            [plan.design_summary, *plan.flags, *plan.tradeoffs, *plan.style_relaxations]
        ).lower()
        records = self.repository.get_items(item.item_id for item in plan.items)
        normalized_items = self._selection_key([item.model_dump() for item in plan.items])
        if len(normalized_items) != len(plan.items):
            issues.append(ValidationIssue(
                code="duplicate_item_id",
                severity="warning",
                message="Duplicate item IDs were found in the final plan; quantities are merged for deterministic checks.",
            ))
        brief_budget_match = re.search(r'"budget_inr":\s*(\d+)', brief_text)
        if brief_budget_match and int(brief_budget_match.group(1)) != plan.budget_inr:
            issues.append(ValidationIssue(
                code="budget_changed",
                severity="error",
                message="The final plan budget_inr does not match the source brief budget.",
            ))
        brief_room_match = re.search(r'"room_type":\s*"([^"]+)"', brief_text)
        if brief_room_match and brief_room_match.group(1).strip().lower() != plan.room_type.strip().lower():
            issues.append(ValidationIssue(
                code="room_type_changed",
                severity="warning",
                message="The final plan room_type differs from the source brief.",
            ))
        missing_ids = [item.item_id for item in plan.items if item.item_id not in records]
        for item_id in missing_ids:
            issues.append(ValidationIssue(code="invented_item", severity="error", message=f"{item_id} does not exist in the catalog."))

        selected_records = []
        boq: list[BOQLine] = []
        known_total = 0
        has_unknown_prices = False

        for selected in plan.items:
            item = records.get(selected.item_id)
            if not item:
                continue
            selected_records.append({"item": item, "quantity": selected.quantity})
            unit_price = item.get("price_inr")
            line_total = None if unit_price is None else unit_price * selected.quantity
            if line_total is None:
                has_unknown_prices = True
                item_is_named = item["item_id"].lower() in disclosure_text or item["name"].lower() in disclosure_text
                price_is_disclosed = item_is_named and any(
                    phrase in disclosure_text
                    for phrase in ("price on request", "unknown price", "price unavailable", "price is not loaded")
                )
                issues.append(ValidationIssue(
                    code="unknown_price" if price_is_disclosed else "undisclosed_unknown_price",
                    severity="warning" if price_is_disclosed else "error",
                    message=(
                        f"{item['item_id']} has price on request and is not counted as zero."
                        if price_is_disclosed
                        else f"{item['item_id']} has no catalog price, but the final plan does not clearly disclose that uncertainty."
                    ),
                ))
            else:
                known_total += line_total
            if not item.get("in_stock"):
                item_is_named = item["item_id"].lower() in disclosure_text or item["name"].lower() in disclosure_text
                stock_is_disclosed = item_is_named and any(
                    phrase in disclosure_text
                    for phrase in ("out of stock", "unavailable", "not in stock")
                )
                issues.append(ValidationIssue(
                    code="out_of_stock" if stock_is_disclosed else "undisclosed_out_of_stock",
                    severity="warning" if stock_is_disclosed else "error",
                    message=(
                        f"{item['item_id']} is out of stock and was explicitly disclosed."
                        if stock_is_disclosed
                        else f"{item['item_id']} is out of stock, but the final plan does not clearly disclose it."
                    ),
                ))
            dimensions = " x ".join(
                "?" if item.get(field) is None else str(item[field])
                for field in ("width_cm", "depth_cm", "height_cm")
            )
            boq.append(BOQLine(
                item_id=item["item_id"],
                category=item["category"],
                name=item["name"],
                quantity=selected.quantity,
                unit_price_inr=unit_price,
                line_total_inr=line_total,
                in_stock=item["in_stock"],
                lead_time_days=item.get("lead_time_days"),
                dimensions_cm=dimensions,
                rationale=selected.rationale,
                placement_note=selected.placement_note,
            ))

        remaining = plan.budget_inr - known_total
        over_budget = known_total > plan.budget_inr
        if over_budget:
            issues.append(ValidationIssue(
                code="over_budget",
                severity="error",
                message=f"Known BOQ total is INR {known_total:,}, exceeding the INR {plan.budget_inr:,} budget by INR {-remaining:,}.",
            ))
        if has_unknown_prices and plan.status.value == "complete":
            issues.append(ValidationIssue(
                code="unknown_price_complete",
                severity="error",
                message="A complete plan cannot claim a guaranteed within-budget result while committed items have unknown catalog prices.",
            ))

        fit_result = self.tools.check_fit(
            items=[{"item_id": item.item_id, "quantity": item.quantity} for item in plan.items],
            room_length_cm=room_length_cm,
            room_width_cm=room_width_cm,
            room_type=plan.room_type,
        )
        if not fit_result.get("fits"):
            issues.append(ValidationIssue(code="fit_failure", severity="error", message="The final selection fails the deterministic layout/fit heuristic."))

        deadline_days = self._deadline_days(brief_text)
        if deadline_days is not None:
            late_items = [
                f"{line.item_id} ({line.lead_time_days} days)"
                for line in boq
                if line.lead_time_days is not None and line.lead_time_days > deadline_days
            ]
            if late_items:
                disclosed = any(phrase in disclosure_text for phrase in ("lead time", "deadline", "delivery", "cannot guarantee"))
                issues.append(ValidationIssue(
                    code="lead_time_conflict" if disclosed else "undisclosed_lead_time_conflict",
                    severity="warning" if disclosed else "error",
                    message=f"Catalog lead time exceeds the requested deadline for: {', '.join(late_items)}.",
                ))

        must_have_result = evaluate_must_haves(must_haves, selected_records)
        if not must_have_result["all_scored_requirements_met"]:
            is_honest_partial = plan.status.value in {"partial", "impossible"} and bool(plan.tradeoffs or plan.flags)
            issues.append(ValidationIssue(
                code="missing_must_have",
                severity="warning" if is_honest_partial else "error",
                message=(
                    f"Missing scored must-haves: {', '.join(must_have_result['missing'])}. "
                    + ("The plan is explicitly partial/impossible and discloses trade-offs." if is_honest_partial else "A complete plan must cover these or change status and explain the trade-off.")
                ),
            ))

        if plan.status.value in {"partial", "impossible"} and not (plan.tradeoffs or plan.flags):
            issues.append(ValidationIssue(
                code="unexplained_partial",
                severity="error",
                message="A partial or impossible plan must explain the limiting constraint and the closest realistic alternative.",
            ))

        decline_categories = {decline.category for decline in plan.declined_scope}
        required_declines = self._required_declines(brief_text)
        missing_declines = sorted(required_declines - decline_categories)
        for category in missing_declines:
            issues.append(ValidationIssue(
                code="missing_decline",
                severity="error",
                message=f"The brief requires a {category} refusal/disclaimer, but none was included.",
            ))

        trace_entries = list(trace)
        trace_tools = {entry.tool for entry in trace_entries}
        for required_tool in ("search_catalog", "check_budget", "check_fit"):
            if required_tool not in trace_tools:
                issues.append(ValidationIssue(
                    code="missing_tool_use",
                    severity="error",
                    message=f"Required tool {required_tool} was not observed in the agent trace.",
                ))

        final_set = normalized_items
        last_budget_set = None
        last_fit_set = None
        for entry in trace_entries:
            if entry.tool == "check_budget":
                last_budget_set = self._selection_key(entry.input.get("items", []))
            if entry.tool == "check_fit":
                last_fit_set = self._selection_key(entry.input.get("items", []))
        if final_set and last_budget_set != final_set:
            issues.append(ValidationIssue(
                code="stale_budget_check",
                severity="error",
                message="The most recent budget check does not match the final selected item IDs and quantities.",
            ))
        if final_set and last_fit_set != final_set:
            issues.append(ValidationIssue(
                code="stale_fit_check",
                severity="error",
                message="The most recent fit check does not match the final selected item IDs and quantities.",
            ))
        if not trace_entries and plan.status.value == "complete":
            issues.append(ValidationIssue(
                code="zero_tool_complete",
                severity="error",
                message="A complete plan cannot be accepted when the agent used zero tools.",
            ))
        for issue in loop_issues:
            issues.append(ValidationIssue(code="agent_loop_issue", severity="error", message=str(issue)))

        error_count = sum(issue.severity == "error" for issue in issues)
        return ValidatedPlan(
            plan=plan,
            boq=boq,
            known_total_inr=known_total,
            remaining_inr=remaining,
            has_unknown_prices=has_unknown_prices,
            over_budget=over_budget,
            fit_result=fit_result,
            must_have_result=must_have_result,
            issues=issues,
            is_valid=error_count == 0,
        )
