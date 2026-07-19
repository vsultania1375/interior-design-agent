from __future__ import annotations

import re
from typing import Any


CATEGORY_PATTERNS: list[tuple[re.Pattern[str], set[str]]] = [
    (re.compile(r"\bsofa\b|\bsectional\b", re.I), {"Sofa"}),
    (re.compile(r"\bcoffee table\b", re.I), {"Coffee Table"}),
    (re.compile(r"\btv unit\b|\bmedia unit\b|\btv console\b", re.I), {"TV Unit"}),
    (re.compile(r"\brug\b", re.I), {"Rug"}),
    (re.compile(r"\bwardrobe\b", re.I), {"Wardrobe"}),
    (re.compile(r"\bnightstand\b|\bbedside table\b", re.I), {"Bedside Table"}),
    (re.compile(r"\bbed\b", re.I), {"Bed"}),
    (re.compile(r"\bconsole\b", re.I), {"Console"}),
    (re.compile(r"\bdesk\b", re.I), {"Desk"}),
    (re.compile(r"\bbookshelf\b|\bshelving\b", re.I), {"Bookshelf"}),
    (re.compile(r"\bplanter\b|\bplants?\b", re.I), {"Planter"}),
    (re.compile(r"\bcurtains?\b", re.I), {"Curtains"}),
]


def _seat_capacity(item: dict[str, Any], quantity: int) -> int:
    category = item.get("category")
    name = item.get("name", "")
    match = re.search(r"(\d+)\s*-?\s*seater", name, re.I)
    if match:
        return int(match.group(1)) * quantity
    if category == "Sofa":
        if "sectional" in name.lower() or "l-sofa" in name.lower():
            return 5 * quantity
        return 3 * quantity
    if category in {"Armchair", "Dining Chair", "Office Chair", "Bean Bag", "Ottoman"}:
        return quantity
    return 0


def evaluate_must_haves(must_haves: str, selected: list[dict[str, Any]]) -> dict[str, Any]:
    text = must_haves or ""
    category_quantities: dict[str, int] = {}
    for entry in selected:
        item = entry["item"]
        category_quantities[item["category"]] = category_quantities.get(item["category"], 0) + entry["quantity"]

    checks: list[dict[str, Any]] = []

    def add_check(requirement: str, satisfied: bool, detail: str) -> None:
        checks.append({"requirement": requirement, "satisfied": satisfied, "detail": detail})

    if re.search(r"\bno\s+tv\b|\bwithout\s+(a\s+)?tv\b", text, re.I):
        add_check("No TV", category_quantities.get("TV Unit", 0) == 0, "A TV Unit must not be selected.")

    if re.search(r"\blighting\b|\bsoft lighting\b", text, re.I):
        total = sum(category_quantities.get(cat, 0) for cat in {"Floor Lamp", "Table Lamp", "Pendant Light"})
        add_check("Lighting", total >= 1, "At least one floor, table, or pendant light is required.")

    if re.search(r"\btask lighting\b", text, re.I):
        total = category_quantities.get("Floor Lamp", 0) + category_quantities.get("Table Lamp", 0)
        add_check("Task lighting", total >= 1, "A floor or table lamp is required near the desk.")

    if re.search(r"\bstatement pendant\b", text, re.I):
        add_check("Statement pendant", category_quantities.get("Pendant Light", 0) >= 1, "A Pendant Light is specifically required.")

    if re.search(r"\breading corner\b", text, re.I):
        chair = category_quantities.get("Armchair", 0) >= 1
        lamp = category_quantities.get("Floor Lamp", 0) + category_quantities.get("Table Lamp", 0) >= 1
        add_check("Reading corner", chair and lamp, "Requires an Armchair plus a Floor Lamp or Table Lamp.")

    if re.search(r"\bstorage\b", text, re.I):
        storage = category_quantities.get("Wardrobe", 0) + category_quantities.get("Bookshelf", 0) >= 1
        storage_bed = any(
            entry["item"]["category"] == "Bed" and "storage" in entry["item"]["name"].lower()
            for entry in selected
        )
        add_check("Storage", storage or storage_bed, "Requires a Wardrobe, Bookshelf, or a bed explicitly described as storage.")

    seating_match = re.search(r"seating\s+for\s+(\d+)", text, re.I)
    if seating_match:
        required = int(seating_match.group(1))
        available = sum(_seat_capacity(entry["item"], entry["quantity"]) for entry in selected)
        add_check(f"Seating for {required}", available >= required, f"Estimated seating capacity is {available}.")

    dining_match = re.search(r"(\d+)\s*-?\s*seater\s+(?:banquet\s+)?dining", text, re.I)
    if dining_match:
        required = int(dining_match.group(1))
        table_capacity = max(
            [_seat_capacity(entry["item"], entry["quantity"]) for entry in selected if entry["item"]["category"] == "Dining Table"]
            or [0]
        )
        chair_count = category_quantities.get("Dining Chair", 0)
        add_check(
            f"{required}-seater dining table",
            table_capacity >= required,
            f"Selected table capacity is approximately {table_capacity}.",
        )
        add_check(
            f"{required} dining chairs",
            chair_count >= required,
            f"Selected Dining Chair quantity is {chair_count}.",
        )

    if re.search(r"\blayered rugs\b", text, re.I):
        add_check("Layered rugs", category_quantities.get("Rug", 0) >= 2, "Requires at least two rugs in the BOQ.")

    if re.search(r"\baccent seating\b", text, re.I):
        total = sum(category_quantities.get(cat, 0) for cat in {"Armchair", "Bean Bag", "Ottoman"})
        add_check("Accent seating", total >= 1, "Requires an Armchair, Bean Bag, or Ottoman.")

    for pattern, categories in CATEGORY_PATTERNS:
        if pattern.search(text):
            label = "/".join(sorted(categories))
            satisfied = any(category_quantities.get(category, 0) >= 1 for category in categories)
            if not any(check["requirement"].lower() == label.lower() for check in checks):
                add_check(label, satisfied, f"Expected at least one item from: {', '.join(sorted(categories))}.")

    missing = [check["requirement"] for check in checks if not check["satisfied"]]
    return {
        "all_scored_requirements_met": not missing,
        "checks": checks,
        "missing": missing,
        "note": "Only requirements covered by the deterministic synonym map are scored; subjective phrases remain for the judgement scorer.",
    }
