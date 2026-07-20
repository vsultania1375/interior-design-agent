from __future__ import annotations

from interior_agent.ui.layout import generate_living_room_layout, render_layout_svg, render_layout_warnings_html


def _items():
    return [
        {"item_id": "SOF-001", "category": "Sofa", "name": "Sofa", "width_cm": 210, "depth_cm": 90},
        {"item_id": "TVU-001", "category": "TV Unit", "name": "TV", "width_cm": 180, "depth_cm": 40},
        {"item_id": "RUG-002", "category": "Rug", "name": "Rug", "width_cm": 270, "depth_cm": 180},
        {"item_id": "CFT-001", "category": "Coffee Table", "name": "Coffee", "width_cm": 110, "depth_cm": 60},
    ]


def test_layout_uses_actual_room_dimensions() -> None:
    layout = generate_living_room_layout(480, 360, _items())
    assert layout.room_length_cm == 480
    assert layout.room_width_cm == 360


def test_sofa_and_tv_are_opposite_where_possible() -> None:
    layout = generate_living_room_layout(480, 360, _items())
    by_role = {item.role: item for item in layout.placed_items}
    assert by_role["TV Unit"].y_cm < by_role["Sofa"].y_cm


def test_coffee_table_is_central_and_rug_below() -> None:
    layout = generate_living_room_layout(480, 360, _items())
    by_role = {item.role: item for item in layout.placed_items}
    coffee = by_role["Coffee Table"]
    assert 150 <= coffee.x_cm <= 220
    assert 130 <= coffee.y_cm <= 180
    assert by_role["Rug"].z_index < coffee.z_index


def test_no_negative_coordinates_and_items_within_bounds() -> None:
    layout = generate_living_room_layout(480, 360, _items())
    for item in layout.placed_items:
        assert item.x_cm >= 0
        assert item.y_cm >= 0
        assert item.x_cm + item.width_cm <= layout.room_length_cm
        assert item.y_cm + item.depth_cm <= layout.room_width_cm


def test_missing_dimensions_do_not_invent_unless_fallback_exists() -> None:
    layout = generate_living_room_layout(480, 360, [{"item_id": "ART-001", "category": "Wall Art", "name": "Art"}])
    assert not layout.placed_items
    assert layout.unplaced_item_ids == ["ART-001"]


def test_svg_contains_disclaimer_not_json() -> None:
    svg = render_layout_svg(generate_living_room_layout(480, 360, _items()))
    assert "Conceptual empty-room layout" in svg
    assert "{" not in svg


def test_out_of_category_item_is_unplaced_with_explanatory_warning() -> None:
    # Real catalog category and dimensions for a Bed (BED-001): out of place in a Living Room layout,
    # but must never be silently dropped — it's still a real, priced item in the plan.
    items = _items() + [{"item_id": "BED-001", "category": "Bed", "name": "Bed", "width_cm": 160, "depth_cm": 210}]
    layout = generate_living_room_layout(480, 360, items)
    assert "BED-001" in layout.unplaced_item_ids
    assert not any(item.item_id == "BED-001" for item in layout.placed_items)
    matching = [warning for warning in layout.warnings if "BED-001" in warning]
    assert matching, "expected a warning message referencing BED-001"
    assert "isn't a typical living-room piece" in matching[0]
    assert "Bed" in matching[0]


def test_render_layout_warnings_html_includes_unplaced_item_warning() -> None:
    items = _items() + [{"item_id": "BED-001", "category": "Bed", "name": "Bed", "width_cm": 160, "depth_cm": 210}]
    layout = generate_living_room_layout(480, 360, items)
    html = render_layout_warnings_html(layout)
    assert "BED-001" in html
    assert "typical living-room piece" in html
    assert "compact-note" in html


def test_render_layout_warnings_html_empty_when_no_warnings() -> None:
    layout = generate_living_room_layout(480, 360, _items())
    assert layout.warnings == []
    assert render_layout_warnings_html(layout) == ""
