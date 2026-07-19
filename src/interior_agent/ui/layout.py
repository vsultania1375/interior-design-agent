from __future__ import annotations

from dataclasses import dataclass, field
from html import escape
from typing import Any


@dataclass
class PlacedItem:
    item_id: str
    name: str
    category: str
    role: str
    x_cm: float
    y_cm: float
    width_cm: float
    depth_cm: float
    rotation: int = 0
    z_index: int = 10


@dataclass
class LayoutResult:
    room_length_cm: int
    room_width_cm: int
    placed_items: list[PlacedItem] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    unplaced_item_ids: list[str] = field(default_factory=list)


ROLE_CATEGORIES = {
    "Sofa": "Sofa",
    "TV Unit": "TV Unit",
    "Coffee Table": "Coffee Table",
    "Rug": "Rug",
    "Floor Lamp": "Floor Lamp",
    "Armchair": "Chair",
    "Accent Chair": "Chair",
    "Chair": "Chair",
    "Side Table": "Side Table",
    "Bookshelf": "Storage",
    "Console": "Storage",
    "Storage": "Storage",
}


FALLBACK_DIMENSIONS = {
    "Floor Lamp": (45, 45),
    "Side Table": (45, 45),
    "Planter": (35, 35),
}


def _dims(item: dict[str, Any]) -> tuple[float, float] | None:
    width = item.get("width_cm")
    depth = item.get("depth_cm")
    if width and depth:
        return float(width), float(depth)
    fallback = FALLBACK_DIMENSIONS.get(str(item.get("category") or ""))
    if fallback:
        return float(fallback[0]), float(fallback[1])
    return None


def _fits(x: float, y: float, width: float, depth: float, room_l: int, room_w: int) -> bool:
    return x >= 0 and y >= 0 and x + width <= room_l and y + depth <= room_w


def _add(result: LayoutResult, item: dict[str, Any], role: str, x: float, y: float, width: float, depth: float, *, z: int = 10) -> bool:
    if not _fits(x, y, width, depth, result.room_length_cm, result.room_width_cm):
        result.warnings.append(f"{item['item_id']} could not be drawn within the room bounds.")
        result.unplaced_item_ids.append(item["item_id"])
        return False
    result.placed_items.append(PlacedItem(
        item_id=item["item_id"],
        name=item.get("name", item["item_id"]),
        category=item.get("category", ""),
        role=role,
        x_cm=round(x, 1),
        y_cm=round(y, 1),
        width_cm=round(width, 1),
        depth_cm=round(depth, 1),
        z_index=z,
    ))
    return True


def generate_living_room_layout(room_length_cm: int, room_width_cm: int, catalog_items: list[dict[str, Any]]) -> LayoutResult:
    result = LayoutResult(room_length_cm=int(room_length_cm), room_width_cm=int(room_width_cm))
    if room_length_cm <= 0 or room_width_cm <= 0:
        result.warnings.append("Room dimensions are required before furniture can be visualised.")
        return result

    counts: dict[str, int] = {}
    for item in catalog_items:
        category = str(item.get("category") or "")
        role = ROLE_CATEGORIES.get(category)
        dims = _dims(item)
        if not role or not dims:
            result.unplaced_item_ids.append(str(item.get("item_id")))
            if not dims:
                result.warnings.append(f"{item.get('item_id')} has no catalog dimensions and was not visualised.")
            continue
        width, depth = dims
        counts[role] = counts.get(role, 0) + 1
        n = counts[role]

        if role == "Rug":
            _add(result, item, role, (room_length_cm - width) / 2, (room_width_cm - depth) / 2, width, depth, z=1)
        elif role == "Sofa":
            _add(result, item, role, (room_length_cm - width) / 2, room_width_cm - depth - 24, width, depth, z=20)
        elif role == "TV Unit":
            _add(result, item, role, (room_length_cm - width) / 2, 24, width, depth, z=20)
        elif role == "Coffee Table":
            _add(result, item, role, (room_length_cm - width) / 2, (room_width_cm - depth) / 2, width, depth, z=30)
        elif role == "Floor Lamp":
            _add(result, item, role, max(18, room_length_cm * 0.22 - width / 2), room_width_cm - depth - 18, width, depth, z=35)
        elif role == "Chair":
            x = 35 if n % 2 else room_length_cm - width - 35
            y = max(70, (room_width_cm - depth) / 2)
            _add(result, item, role, x, y, width, depth, z=25)
        elif role == "Side Table":
            x = room_length_cm * (0.28 if n % 2 else 0.72) - width / 2
            y = room_width_cm - depth - 28
            _add(result, item, role, x, y, width, depth, z=28)
        elif role == "Storage":
            _add(result, item, role, room_length_cm - width - 24, 24 + (n - 1) * (depth + 16), width, depth, z=18)

    return result


def render_layout_svg(layout: LayoutResult) -> str:
    max_px = 520
    scale = max_px / max(layout.room_length_cm, layout.room_width_cm, 1)
    width_px = max(260, layout.room_length_cm * scale)
    height_px = max(220, layout.room_width_cm * scale)

    palette = {
        "Rug": ("#d8b980", "#7a5a24"),
        "Sofa": ("#9fb7aa", "#2f5b4a"),
        "TV Unit": ("#c7b6a2", "#5f4b3b"),
        "Coffee Table": ("#f2dfb7", "#806531"),
        "Floor Lamp": ("#f6e7a8", "#776300"),
        "Chair": ("#b7c8de", "#35506e"),
        "Side Table": ("#d9c6ba", "#6b5143"),
        "Storage": ("#c8c7bd", "#59584e"),
    }
    parts = [
        f'<svg viewBox="0 0 {width_px + 40:.0f} {height_px + 56:.0f}" width="100%" role="img" aria-label="Conceptual room layout">',
        '<rect x="20" y="20" width="{:.1f}" height="{:.1f}" rx="10" fill="#fffdf9" stroke="#d7d1c8" stroke-width="2"/>'.format(width_px, height_px),
        f'<text x="{20 + width_px / 2:.1f}" y="14" text-anchor="middle" font-family="Inter, Arial" font-size="12" fill="#6f675e">{layout.room_length_cm} cm</text>',
        f'<text x="8" y="{20 + height_px / 2:.1f}" text-anchor="middle" transform="rotate(-90 8 {20 + height_px / 2:.1f})" font-family="Inter, Arial" font-size="12" fill="#6f675e">{layout.room_width_cm} cm</text>',
    ]
    for item in sorted(layout.placed_items, key=lambda placed: placed.z_index):
        fill, stroke = palette.get(item.role, ("#ddd", "#666"))
        x = 20 + item.x_cm * scale
        y = 20 + item.y_cm * scale
        w = max(10, item.width_cm * scale)
        d = max(10, item.depth_cm * scale)
        parts.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{d:.1f}" rx="7" fill="{fill}" stroke="{stroke}" stroke-width="1.5"/>')
        label = escape(item.role)
        parts.append(f'<text x="{x + w / 2:.1f}" y="{y + d / 2 + 4:.1f}" text-anchor="middle" font-family="Inter, Arial" font-size="11" fill="#2f2923">{label}</text>')
    parts.append('<text x="20" y="{:.1f}" font-family="Inter, Arial" font-size="11" fill="#7d746b">Conceptual empty-room layout; verify site conditions before purchase.</text>'.format(height_px + 44))
    parts.append("</svg>")
    return "".join(parts)
