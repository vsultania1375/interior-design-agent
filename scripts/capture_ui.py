"""Dev-only Playwright screenshot capture for manual UI QA.

Not part of the app's runtime import path. Run against a locally running
demo-mode Streamlit server (see README / task notes for the launch command).
Never clicks "Create my room plan" or anything that could trigger a live
Anthropic call.
"""

from __future__ import annotations

from pathlib import Path

from playwright.sync_api import Page, sync_playwright

BASE_URL = "http://127.0.0.1:8900"
OUTPUT_DIR = Path(__file__).resolve().parent.parent / ".local-screenshots"
VIEWPORTS = [(1440, 900), (1366, 768)]

ACTIVE_CARD = '[class*="st-key-active_card_"]'


def _first_button(page: Page, text: str):
    return page.locator(f'{ACTIVE_CARD} div[data-testid="stButton"] button', has_text=text).first


def _first_choice_button(page: Page):
    return page.locator(f'{ACTIVE_CARD} div[data-testid="stButton"] button').first


def _wait_settled(page: Page) -> None:
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(250)


def _shot(page: Page, name: str, width: int, height: int) -> None:
    path = OUTPUT_DIR / f"{name}_{width}x{height}.png"
    page.screenshot(path=str(path))
    print(f"captured {path}")


def _custom_path(page: Page, width: int, height: int) -> None:
    page.goto(BASE_URL)
    _wait_settled(page)
    _shot(page, "welcome", width, height)

    _first_button(page, "Design my own room").click()
    _wait_settled(page)
    _shot(page, "custom_room_size", width, height)

    _first_choice_button(page).click()
    _wait_settled(page)
    _shot(page, "custom_budget", width, height)

    _first_choice_button(page).click()  # budget choice -> style step (not captured)
    _wait_settled(page)
    _first_choice_button(page).click()  # style choice -> requirements step
    _wait_settled(page)
    _shot(page, "custom_requirements", width, height)

    _first_choice_button(page).click()  # select a requirement
    _wait_settled(page)
    page.locator(f'{ACTIVE_CARD} div[data-testid="stButton"] button', has_text="Continue").click()
    _wait_settled(page)  # -> context/constraints step (not captured)
    page.locator(f'{ACTIVE_CARD} div[data-testid="stButton"] button', has_text="No special constraint").click()
    _wait_settled(page)
    page.locator(f'{ACTIVE_CARD} div[data-testid="stButton"] button', has_text="Review my answers").click()
    _wait_settled(page)
    _shot(page, "custom_review", width, height)


def _demo_path(page: Page, width: int, height: int) -> None:
    page.goto(BASE_URL)
    _wait_settled(page)

    _first_button(page, "Try a demo room").click()
    _wait_settled(page)
    _shot(page, "demo_select_sample", width, height)

    _first_choice_button(page).click()
    _wait_settled(page)
    _shot(page, "demo_result", width, height)


def main() -> None:
    OUTPUT_DIR.mkdir(exist_ok=True)
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        for width, height in VIEWPORTS:
            for flow in (_custom_path, _demo_path):
                context = browser.new_context(viewport={"width": width, "height": height})
                page = context.new_page()
                flow(page, width, height)
                context.close()
        browser.close()


if __name__ == "__main__":
    main()
