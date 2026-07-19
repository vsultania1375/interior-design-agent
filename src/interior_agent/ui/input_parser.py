from __future__ import annotations

import re

from .state import feet_to_cm


SUPPORTED_STYLES = {
    "scandinavian": "Scandinavian",
    "modern": "Modern",
    "minimal": "Minimal",
    "mid-century": "Mid-Century",
    "mid century": "Mid-Century",
    "bohemian": "Bohemian",
    "industrial": "Industrial",
}


def parse_dimensions(text: str) -> tuple[int, int, int | None] | None:
    lowered = text.lower().replace("×", "x").replace("by", "x")
    unit_is_cm = "cm" in lowered
    numbers = [float(match) for match in re.findall(r"\d+(?:\.\d+)?", lowered)]
    if len(numbers) < 2:
        return None
    length, width = numbers[0], numbers[1]
    ceiling = numbers[2] if len(numbers) >= 3 else None
    if unit_is_cm:
        return int(round(length)), int(round(width)), None if ceiling is None else int(round(ceiling))
    return feet_to_cm(length), feet_to_cm(width), None if ceiling is None else feet_to_cm(ceiling)


def parse_budget(text: str) -> int | None:
    lowered = text.lower().replace(",", "").replace("₹", "").strip()
    match = re.search(r"\d+(?:\.\d+)?", lowered)
    if not match:
        return None
    value = float(match.group(0))
    if "lakh" in lowered or "lac" in lowered:
        value *= 100000
    elif "k" in lowered:
        value *= 1000
    return int(round(value))


def parse_style(text: str) -> str | None:
    lowered = text.strip().lower()
    if lowered in {"not sure", "suggest", "suggest one"}:
        return "Scandinavian"
    for key, value in SUPPORTED_STYLES.items():
        if key in lowered:
            return value
    return None


def parse_multi_value_text(text: str) -> list[str]:
    values = [part.strip().capitalize() for part in re.split(r",| and |\n", text) if part.strip()]
    return list(dict.fromkeys(values))


INJECTION_PATTERNS = [
    r"ignore (all |previous |your )?instructions",
    r"system prompt",
    r"you are now",
    r"act as (a|an)",
    r"pretend (to be|you are)",
    r"disregard (all |previous )?",
    r"new instructions",
    r"reveal your (prompt|instructions|rules)",
]

_INJECTION_RE = re.compile("|".join(INJECTION_PATTERNS), re.IGNORECASE)


def screen_free_text(text: str) -> tuple[str, bool]:
    """Returns (cleaned_text, was_flagged). If flagged, cleaned_text is empty —
    the rest of the brief still proceeds without this note."""
    if _INJECTION_RE.search(text):
        return "", True
    return text, False
