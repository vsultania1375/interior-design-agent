from __future__ import annotations

from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


class PlanStatus(str, Enum):
    complete = "complete"
    partial = "partial"
    impossible = "impossible"


class SelectedItem(BaseModel):
    item_id: str = Field(min_length=1)
    quantity: int = Field(default=1, ge=1, le=20)
    rationale: str = Field(min_length=1)
    placement_note: str | None = None

    @field_validator("item_id")
    @classmethod
    def normalize_item_id(cls, value: str) -> str:
        return value.strip().upper()


class ScopeDecline(BaseModel):
    category: Literal["structural", "electrical", "plumbing", "delivery_guarantee", "price_guarantee", "other"]
    message: str
    referral: str | None = None


class DesignPlan(BaseModel):
    brief_id: str | None = None
    room_type: str
    status: PlanStatus = PlanStatus.complete
    design_summary: str
    budget_inr: int = Field(ge=0)
    items: list[SelectedItem] = Field(default_factory=list)
    tradeoffs: list[str] = Field(default_factory=list)
    flags: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    style_relaxations: list[str] = Field(default_factory=list)
    declined_scope: list[ScopeDecline] = Field(default_factory=list)


class TraceEntry(BaseModel):
    iteration: int
    tool: str
    input: dict[str, Any]
    result: dict[str, Any]


class BOQLine(BaseModel):
    item_id: str
    category: str
    name: str
    quantity: int
    unit_price_inr: int | None
    line_total_inr: int | None
    in_stock: bool
    lead_time_days: int | None
    dimensions_cm: str
    rationale: str
    placement_note: str | None = None


class ValidationIssue(BaseModel):
    code: str
    severity: Literal["error", "warning", "info"]
    message: str


class ValidatedPlan(BaseModel):
    plan: DesignPlan
    boq: list[BOQLine]
    known_total_inr: int
    remaining_inr: int
    has_unknown_prices: bool
    over_budget: bool
    fit_result: dict[str, Any]
    must_have_result: dict[str, Any]
    issues: list[ValidationIssue]
    is_valid: bool
