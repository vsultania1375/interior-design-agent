from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


class ConfigurationError(ValueError):
    """Friendly setup error for CLI, Streamlit, and eval entrypoints."""


@dataclass(frozen=True)
class Settings:
    db_path: Path
    anthropic_api_key: str | None
    anthropic_model: str
    max_iterations: int

    @classmethod
    def from_env(cls, project_root: Path | None = None) -> "Settings":
        root = project_root or Path(__file__).resolve().parents[2]
        raw_db_path = os.getenv("INTERIOR_DB_PATH", "data/interior_company_catalog.db")
        db_path = Path(raw_db_path)
        if not db_path.is_absolute():
            db_path = root / db_path

        raw_iterations = os.getenv("MAX_AGENT_ITERATIONS", "15")
        try:
            max_iterations = max(1, min(int(raw_iterations), 30))
        except ValueError as exc:
            raise ConfigurationError("MAX_AGENT_ITERATIONS must be an integer between 1 and 30.") from exc

        return cls(
            db_path=db_path.resolve(),
            anthropic_api_key=os.getenv("ANTHROPIC_API_KEY") or None,
            anthropic_model=os.getenv("ANTHROPIC_MODEL", "claude-sonnet-5"),
            max_iterations=max_iterations,
        )
