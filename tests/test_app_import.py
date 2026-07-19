from __future__ import annotations

import pytest


def test_app_imports_without_api_key(monkeypatch) -> None:
    pytest.importorskip("streamlit")
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    __import__("app")
