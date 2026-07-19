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


SECONDARY_ROLES = {"Chair", "Side Table", "Floor Lamp", "Storage"}


def _overlaps(a: PlacedItem, b: PlacedItem) -> bool:
    return (
        a.x_cm < b.x_cm + b.width_cm and a.x_cm + a.width_cm > b.x_cm
        and a.y_cm < b.y_cm + b.depth_cm and a.y_cm + a.depth_cm > b.y_cm
    )


def _find_clear_position(item: PlacedItem, others: list[PlacedItem], room_l: float, room_w: float, step: float = 10.0) -> tuple[float, float] | None:
    max_x = room_l - item.width_cm
    max_y = room_w - item.depth_cm
    if max_x < 0 or max_y < 0:
        return None
    candidates: list[tuple[float, float]] = []
    x = 0.0
    while x <= max_x + 1e-6:
        y = 0.0
        while y <= max_y + 1e-6:
            candidates.append((x, y))
            y += step
        x += step
    candidates.sort(key=lambda pos: (pos[0] - item.x_cm) ** 2 + (pos[1] - item.y_cm) ** 2)
    for cx, cy in candidates:
        probe = PlacedItem(item_id=item.item_id, name=item.name, category=item.category, role=item.role, x_cm=cx, y_cm=cy, width_cm=item.width_cm, depth_cm=item.depth_cm)
        if not any(_overlaps(probe, other) for other in others):
            return cx, cy
    return None


def _resolve_collisions(result: LayoutResult) -> None:
    secondary_items = [item for item in result.placed_items if item.role in SECONDARY_ROLES]
    for item in secondary_items:
        others = [other for other in result.placed_items if other.role != "Rug" and other is not item]
        if not any(_overlaps(item, other) for other in others):
            continue
        new_position = _find_clear_position(item, others, result.room_length_cm, result.room_width_cm)
        if new_position is None:
            result.placed_items.remove(item)
            result.unplaced_item_ids.append(item.item_id)
            result.warnings.append(f"{item.item_id} could not be placed without overlapping other furniture and was omitted from the layout.")
            continue
        item.x_cm, item.y_cm = round(new_position[0], 1), round(new_position[1], 1)


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

    _resolve_collisions(result)
    return result


def _walkway_gap(layout: LayoutResult) -> tuple[Any, Any, float] | None:
    by_role: dict[str, list[Any]] = {}
    for item in layout.placed_items:
        by_role.setdefault(item.role, []).append(item)
    tv_items = by_role.get("TV Unit")
    sofa_items = by_role.get("Sofa")
    if not tv_items or not sofa_items:
        return None
    tv, sofa = tv_items[0], sofa_items[0]
    gap_cm = sofa.y_cm - (tv.y_cm + tv.depth_cm)
    if gap_cm <= 0:
        return None
    return tv, sofa, gap_cm


def render_layout_svg(layout: LayoutResult, *, max_px: int = 520, min_width: int = 260, min_height: int = 220, show_walkway: bool = False) -> str:
    scale = max_px / max(layout.room_length_cm, layout.room_width_cm, 1)
    width_px = max(min_width, layout.room_length_cm * scale)
    height_px = max(min_height, layout.room_width_cm * scale)

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

    walkway = _walkway_gap(layout) if show_walkway else None
    right_margin = 64 if walkway else 0

    parts = [
        f'<svg viewBox="0 0 {width_px + 40 + right_margin:.0f} {height_px + 56:.0f}" width="100%" role="img" aria-label="Conceptual room layout">',
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

    if walkway:
        tv, sofa, gap_cm = walkway
        x_line = 20 + width_px + 24
        y1 = 20 + (tv.y_cm + tv.depth_cm) * scale
        y2 = 20 + sofa.y_cm * scale
        mid_y = (y1 + y2) / 2
        parts.append(f'<line x1="{x_line:.1f}" y1="{y1:.1f}" x2="{x_line:.1f}" y2="{y2:.1f}" stroke="#5d544a" stroke-width="1.5"/>')
        parts.append(f'<polygon points="{x_line - 4:.1f},{y1 + 7:.1f} {x_line + 4:.1f},{y1 + 7:.1f} {x_line:.1f},{y1:.1f}" fill="#5d544a"/>')
        parts.append(f'<polygon points="{x_line - 4:.1f},{y2 - 7:.1f} {x_line + 4:.1f},{y2 - 7:.1f} {x_line:.1f},{y2:.1f}" fill="#5d544a"/>')
        parts.append(
            f'<text x="{x_line + 8:.1f}" y="{mid_y:.1f}" text-anchor="start" dominant-baseline="middle" '
            f'font-family="Inter, Arial" font-size="11" fill="#5d544a">{gap_cm:.0f} cm walk</text>'
        )

    parts.append('<text x="20" y="{:.1f}" font-family="Inter, Arial" font-size="11" fill="#7d746b">Conceptual empty-room layout; verify site conditions before purchase.</text>'.format(height_px + 44))
    parts.append("</svg>")
    return "".join(parts)
