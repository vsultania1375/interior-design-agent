from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP_SOURCE = (ROOT / "app.py").read_text(encoding="utf-8")
CHAT_SOURCE = (ROOT / "src" / "interior_agent" / "ui" / "chat.py").read_text(encoding="utf-8")

# Each of these previously opened a <div class="..."> via one st.markdown call and
# closed it via a separate st.markdown("</div>") call, with native widgets rendered
# in between. Streamlit does not nest across separate st.markdown calls, so the
# fix replaces every pair with a real st.container(key=...) block.
FIXED_CONTAINER_KEYS = [
    "top_action",
    "composer",
    "result_card",
    "side_panel",
    "chat_panel",
    "message_log",
]

RETIRED_DIV_OPEN_TAGS = [
    '<div class="top-action">',
    '<div class="composer">',
    '<div class="result-card">',
    '<div class="side-panel">',
    '<div class="chat-panel">',
    '<div class="product-card">',
    '<div class="active-card">',
]


def test_active_card_uses_keyed_container_with_border() -> None:
    assert 'st.container(key=f"active_card_{step.value}", border=True)' in CHAT_SOURCE
    assert '<div class="active-card">' not in CHAT_SOURCE


def test_active_card_container_is_entered_and_exited_around_question_body() -> None:
    assert "container.__enter__()" in CHAT_SOURCE
    assert "container.__exit__(None, None, None)" in CHAT_SOURCE


def test_app_fixed_regions_use_keyed_containers() -> None:
    for key in FIXED_CONTAINER_KEYS:
        assert f'st.container(key="{key}"' in APP_SOURCE, f"missing st.container(key={key!r}) in app.py"


def test_product_card_container_key_is_unique_per_loop_iteration() -> None:
    assert 'st.container(key=f"product_card_{index}")' in APP_SOURCE
    assert "for index, line in enumerate(validated.boq):" in APP_SOURCE


def test_retired_div_open_close_pairs_are_gone() -> None:
    for tag in RETIRED_DIV_OPEN_TAGS:
        assert tag not in APP_SOURCE, f"stale orphan div-open markup still present: {tag!r}"


def test_message_log_container_has_fixed_numeric_height() -> None:
    match = re.search(r'st\.container\(key="message_log",\s*height=(\d+),\s*border=False\)', APP_SOURCE)
    assert match is not None, "message_log container must set a fixed numeric height="
    assert int(match.group(1)) > 0


def test_viewport_lock_is_conditional_on_non_result_steps() -> None:
    assert "def _lock_viewport(" in APP_SOURCE
    assert "overflow:hidden !important" in APP_SOURCE
    assert "_lock_viewport(state.step != ConsultationStep.result)" in APP_SOURCE


def test_compact_preview_svg_is_width_capped_to_avoid_page_overflow() -> None:
    assert "compact-preview-svg" in APP_SOURCE
    assert ".compact-preview-svg { max-width:260px" in APP_SOURCE
