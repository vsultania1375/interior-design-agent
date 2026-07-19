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
    anthropic_max_tokens: int
    live_eval_max_output_tokens: int | None

    @classmethod
    def from_env(cls, project_root: Path | None = None) -> "Settings":
        root = project_root or Path(__file__).resolve().parents[2]
        raw_db_path = os.getenv("INTERIOR_DB_PATH", "data/interior_company_catalog.db")
        db_path = Path(raw_db_path)
        if not db_path.is_absolute():
            db_path = root / db_path

        raw_iterations = os.getenv("MAX_AGENT_ITERATIONS", "8")
        try:
            max_iterations = max(1, min(int(raw_iterations), 15))
        except ValueError as exc:
            raise ConfigurationError("MAX_AGENT_ITERATIONS must be an integer between 1 and 15.") from exc

        raw_max_tokens = os.getenv("ANTHROPIC_MAX_TOKENS", "3000")
        try:
            anthropic_max_tokens = max(512, min(int(raw_max_tokens), 4096))
        except ValueError as exc:
            raise ConfigurationError("ANTHROPIC_MAX_TOKENS must be an integer between 512 and 4096.") from exc

        raw_guard = os.getenv("LIVE_EVAL_MAX_OUTPUT_TOKENS")
        live_eval_max_output_tokens = None
        if raw_guard:
            try:
                live_eval_max_output_tokens = int(raw_guard)
            except ValueError as exc:
                raise ConfigurationError("LIVE_EVAL_MAX_OUTPUT_TOKENS must be a positive integer when set.") from exc
            if live_eval_max_output_tokens <= 0:
                raise ConfigurationError("LIVE_EVAL_MAX_OUTPUT_TOKENS must be a positive integer when set.")

        return cls(
            db_path=db_path.resolve(),
            anthropic_api_key=os.getenv("ANTHROPIC_API_KEY") or None,
            anthropic_model=os.getenv("ANTHROPIC_MODEL", "claude-sonnet-5"),
            max_iterations=max_iterations,
            anthropic_max_tokens=anthropic_max_tokens,
            live_eval_max_output_tokens=live_eval_max_output_tokens,
        )
