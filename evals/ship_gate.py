from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class GateMetric:
    name: str
    numerator: int
    denominator: int
    threshold: float
    not_evaluated: bool = False

    @property
    def rate(self) -> float:
        return 0.0 if self.denominator == 0 else self.numerator / self.denominator

    @property
    def passed(self) -> bool:
        return (not self.not_evaluated) and self.denominator > 0 and self.rate >= self.threshold

    def as_dict(self) -> dict[str, Any]:
        return {
            "passed": self.passed,
            "numerator": self.numerator,
            "denominator": self.denominator,
            "rate": self.rate,
            "threshold": self.threshold,
            "not_evaluated": self.not_evaluated,
        }


SCORE_TO_GATE = {
    "real_items": "real_catalog_items",
    "no_silent_budget_overflow": "zero_silent_budget_violations",
    "required_declines": "required_scope_guarantee_refusals",
    "fit_outcome": "fit_violations_caught_or_flagged",
    "all_required_tools_used": "catalog_search_and_budget_used",
    "final_fit_checked": "fit_checked_before_finalisation",
}

THRESHOLDS = {
    "real_catalog_items": 1.0,
    "zero_silent_budget_violations": 1.0,
    "required_scope_guarantee_refusals": 1.0,
    "fit_violations_caught_or_flagged": 1.0,
    "catalog_search_and_budget_used": 1.0,
    "fit_checked_before_finalisation": 1.0,
    "judge_overall_4_plus": 0.9,
}


def aggregate_ship_gate(cases: list[dict[str, Any]], *, judge_skipped: bool) -> dict[str, Any]:
    buckets = {name: {"num": 0, "den": 0} for name in THRESHOLDS}
    for case in cases:
        by_name = {score["name"]: score for score in case.get("scores", [])}
        for score_name, gate_name in SCORE_TO_GATE.items():
            if score_name in by_name:
                buckets[gate_name]["den"] += 1
                buckets[gate_name]["num"] += int(bool(by_name[score_name]["passed"]))
        judge = case.get("judge")
        if judge is not None:
            buckets["judge_overall_4_plus"]["den"] += 1
            buckets["judge_overall_4_plus"]["num"] += int(float(judge.get("overall", 0)) >= 4.0)

    metrics: dict[str, GateMetric] = {}
    for name, threshold in THRESHOLDS.items():
        metrics[name] = GateMetric(
            name=name,
            numerator=buckets[name]["num"],
            denominator=buckets[name]["den"],
            threshold=threshold,
            not_evaluated=(name == "judge_overall_4_plus" and judge_skipped),
        )
    applicable = [metric for metric in metrics.values() if not metric.not_evaluated]
    return {
        "metrics": {name: metric.as_dict() for name, metric in metrics.items()},
        "overall_passed": all(metric.passed for metric in applicable),
        "failed_cases": [
            {"id": case["id"], "diagnosis": case.get("failure_diagnosis", "")}
            for case in cases
            if not case.get("passed", False)
        ],
    }
