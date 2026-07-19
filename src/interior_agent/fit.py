from __future__ import annotations

from typing import Any


OVERLAY_CATEGORIES = {"Rug", "Wall Art", "Curtains", "Pendant Light", "Table Lamp"}
ROOM_OCCUPANCY_LIMITS = {
    "living room": 0.48,
    "bedroom": 0.58,
    "dining": 0.48,
    "study": 0.50,
    "kids": 0.55,
}


def _effective_dimensions(item: dict[str, Any]) -> tuple[int | None, int | None, str]:
    width = item.get("width_cm")
    depth = item.get("depth_cm")
    if width is None or depth is None:
        return None, None, "Missing dimensions; treated as an unresolved fit risk."

    category = item.get("category", "")
    name = item.get("name", "")
    add_w, add_d, note = 20, 20, "Basic 10 cm edge tolerance on each side."

    if category == "Dining Table":
        add_w, add_d, note = 160, 160, "Includes about 80 cm around the table for chairs and circulation."
    elif category == "Bed":
        add_w, add_d, note = 90, 75, "Includes side access and foot clearance."
    elif category == "Sofa":
        add_w, add_d, note = 30, 90, "Includes side tolerance and front circulation."
    elif category == "Wardrobe":
        add_w = 20
        add_d = 60 if "sliding" in name.lower() else 100
        note = "Includes access/door-opening clearance."
    elif category in {"Desk"}:
        add_w, add_d, note = 60, 100, "Includes chair and working clearance."
    elif category in {"TV Unit", "Console", "Bookshelf"}:
        add_w, add_d, note = 20, 60, "Includes front access/circulation."
    elif category == "Coffee Table":
        add_w, add_d, note = 60, 60, "Includes roughly 30 cm circulation on all sides."
    elif category in {"Armchair", "Office Chair", "Dining Chair", "Bean Bag", "Ottoman"}:
        add_w, add_d, note = 30, 60, "Includes personal space and front access."
    elif category == "Floor Lamp":
        add_w, add_d, note = 20, 20, "Includes a small safety margin around the base."

    return width + add_w, depth + add_d, note


def check_fit(
    items: list[dict[str, Any]],
    *,
    room_length_cm: int,
    room_width_cm: int,
    room_type: str,
) -> dict[str, Any]:
    room_area = max(room_length_cm, 0) * max(room_width_cm, 0)
    hard_violations: list[dict[str, Any]] = []
    warnings: list[str] = []
    item_checks: list[dict[str, Any]] = []
    occupied_area = 0

    for selected in items:
        item = selected["item"]
        quantity = max(int(selected.get("quantity", 1)), 1)
        width = item.get("width_cm")
        depth = item.get("depth_cm")
        effective_w, effective_d, clearance_note = _effective_dimensions(item)

        if item.get("category") not in OVERLAY_CATEGORIES and width is not None and depth is not None:
            occupied_area += width * depth * quantity

        if effective_w is None or effective_d is None:
            warnings.append(f"{item['item_id']} has missing dimensions, so fit cannot be fully verified.")
            item_checks.append({
                "item_id": item["item_id"],
                "quantity": quantity,
                "fits_individually": None,
                "reason": clearance_note,
            })
            continue

        fits_normal = effective_w <= room_length_cm and effective_d <= room_width_cm
        fits_rotated = effective_d <= room_length_cm and effective_w <= room_width_cm
        fits = fits_normal or fits_rotated
        reason = (
            f"Effective footprint {effective_w} x {effective_d} cm; {clearance_note}"
            if fits
            else f"Effective footprint {effective_w} x {effective_d} cm cannot fit inside {room_length_cm} x {room_width_cm} cm in either orientation."
        )
        item_checks.append({
            "item_id": item["item_id"],
            "quantity": quantity,
            "fits_individually": fits,
            "effective_width_cm": effective_w,
            "effective_depth_cm": effective_d,
            "reason": reason,
        })
        if not fits:
            hard_violations.append({"item_id": item["item_id"], "reason": reason})

    occupancy_ratio = occupied_area / room_area if room_area else 1.0
    limit = ROOM_OCCUPANCY_LIMITS.get(room_type.strip().lower(), 0.50)
    if occupancy_ratio > limit:
        hard_violations.append({
            "item_id": None,
            "reason": (
                f"Non-overlapping furniture occupies {occupancy_ratio:.1%} of the room, "
                f"above the {limit:.0%} heuristic limit for {room_type}."
            ),
        })
    elif occupancy_ratio > limit * 0.85:
        warnings.append(
            f"Furniture occupancy is {occupancy_ratio:.1%}, close to the {limit:.0%} limit; circulation may feel tight."
        )

    return {
        "fits": not hard_violations,
        "room_dimensions_cm": {"length": room_length_cm, "width": room_width_cm},
        "room_area_sqm": round(room_area / 10_000, 2),
        "occupied_area_sqm": round(occupied_area / 10_000, 2),
        "occupancy_ratio": round(occupancy_ratio, 4),
        "occupancy_limit": limit,
        "hard_violations": hard_violations,
        "warnings": warnings,
        "item_checks": item_checks,
        "assumption": "The room is treated as an empty rectangle; doors, windows, columns, and electrical points are not represented in the dataset.",
    }
