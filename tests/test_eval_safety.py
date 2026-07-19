from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

import pytest

from interior_agent.config import ConfigurationError, Settings
from run_evals import LiveSafetyError, build_parser, cost_guard_skip_case, load_cases, preflight_summary, select_cases, validate_live_plan


ROOT = Path(__file__).resolve().parents[1]


def parse_args(*args: str) -> argparse.Namespace:
    return build_parser().parse_args(list(args))


def cases():
    return load_cases(ROOT / "evals" / "golden_set.yaml")


def assert_plan_ok(args: argparse.Namespace) -> None:
    parser = build_parser()
    selected, _ = select_cases(cases(), args)
    validate_live_plan(args, selected)


def test_offline_fixtures_need_no_confirmation() -> None:
    assert_plan_ok(parse_args("--offline-fixtures"))


def test_one_explicit_case_is_permitted() -> None:
    assert_plan_ok(parse_args("--case", "db-br-06", "--skip-judge"))


def test_two_live_cases_require_confirmation() -> None:
    with pytest.raises(LiveSafetyError):
        assert_plan_ok(parse_args("--case", "db-br-06", "--case", "db-br-09", "--skip-judge"))


def test_full_run_requires_all_flag() -> None:
    with pytest.raises(LiveSafetyError):
        assert_plan_ok(parse_args("--skip-judge"))


def test_full_run_requires_full_confirmation() -> None:
    with pytest.raises(LiveSafetyError):
        assert_plan_ok(parse_args("--all", "--skip-judge"))


def test_judge_run_requires_confirmation() -> None:
    with pytest.raises(LiveSafetyError):
        assert_plan_ok(parse_args("--case", "db-br-06"))


def test_old_skip_judge_command_exits_before_api() -> None:
    env = {**os.environ, "ANTHROPIC_API_KEY": "", "LIVE_EVAL_COUNTDOWN_SECONDS": "0"}
    result = subprocess.run(
        [sys.executable, "evals/run_evals.py", "--skip-judge"],
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 1
    assert "Refusing to run all live cases by default" in result.stderr


def test_live_case_limit_defaults_to_three() -> None:
    args = parse_args("--case", "db-br-06", "--case", "db-br-07", "--case", "db-br-08", "--case", "db-br-09", "--skip-judge", "--confirm-multi-case-live")
    selected, _ = select_cases(cases(), args)
    with pytest.raises(LiveSafetyError, match="limited to 3"):
        validate_live_plan(args, selected)


def test_preflight_summary_contains_case_count() -> None:
    args = parse_args("--case", "db-br-06", "--skip-judge")
    selected, _ = select_cases(cases(), args)
    settings = Settings(ROOT / "data" / "interior_company_catalog.db", "configured", "model", 8, 3000, None)
    assert "selected_case_count: 1" in preflight_summary(args, selected, settings)


def test_output_token_configuration_accepts_3000(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ANTHROPIC_MAX_TOKENS", "3000")
    assert Settings.from_env(ROOT).anthropic_max_tokens == 3000


def test_output_token_configuration_clamps_over_4096(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ANTHROPIC_MAX_TOKENS", "9999")
    assert Settings.from_env(ROOT).anthropic_max_tokens == 4096


def test_invalid_token_configuration_fails_friendly(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ANTHROPIC_MAX_TOKENS", "bad")
    with pytest.raises(ConfigurationError, match="ANTHROPIC_MAX_TOKENS"):
        Settings.from_env(ROOT)


def test_token_guard_positive_integer(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LIVE_EVAL_MAX_OUTPUT_TOKENS", "20000")
    assert Settings.from_env(ROOT).live_eval_max_output_tokens == 20000


def test_token_guard_invalid_fails_friendly(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LIVE_EVAL_MAX_OUTPUT_TOKENS", "0")
    with pytest.raises(ConfigurationError, match="LIVE_EVAL_MAX_OUTPUT_TOKENS"):
        Settings.from_env(ROOT)


def test_cost_guard_skipped_case_is_marked_not_run() -> None:
    skipped = cost_guard_skip_case({"id": "db-br-06", "tags": ["budget"]})
    assert skipped["passed"] is False
    assert skipped["not_run_reason"] == "not_run_cost_guard"
    assert skipped["issues"][0]["code"] == "not_run_cost_guard"


def test_resume_skips_passed_cases(tmp_path: Path) -> None:
    prior = tmp_path / "results.json"
    prior.write_text('{"cases":[{"id":"db-br-06","passed":true},{"id":"db-br-07","passed":false}]}')
    selected, preserved = select_cases(cases(), parse_args("--resume-from", str(prior), "--skip-judge"))
    assert "db-br-06" not in {case["id"] for case in selected}
    assert {case["id"] for case in preserved} == {"db-br-06"}


def test_failed_only_runs_only_failed_cases(tmp_path: Path) -> None:
    prior = tmp_path / "results.json"
    prior.write_text('{"cases":[{"id":"db-br-06","passed":true},{"id":"db-br-07","passed":false}]}')
    selected, _ = select_cases(cases(), parse_args("--failed-only", str(prior), "--skip-judge"))
    assert [case["id"] for case in selected] == ["db-br-07"]
