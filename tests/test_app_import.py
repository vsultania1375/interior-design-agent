from __future__ import annotations

import pytest


def test_app_imports_without_api_key(monkeypatch) -> None:
    pytest.importorskip("streamlit")
    monkeypatch.setenv("INTERIOR_SKIP_DOTENV", "1")
    monkeypatch.setenv("INTERIOR_UI_DEMO_MODE", "1")
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    __import__("app")
