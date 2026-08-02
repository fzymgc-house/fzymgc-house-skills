"""Tests for the nudge-rg-failure PostToolUse hook."""

from __future__ import annotations

from grepping.hooks.tests.conftest import context, run_hook


def test_parses_string_response_and_nudges_inline(isolated_env: dict[str, str]) -> None:
    result = run_hook(
        "nudge-rg-failure",
        "cd src && rg 'Foo{'",
        env=isolated_env,
        response="Exit code 2\nregex parse error: repetition quantifier expects a valid decimal",
    )
    message = context(result) or ""
    assert "Use `-F`" in message
    assert "load" not in message.lower()
    assert "skill" not in message.lower()


def test_parses_dict_response(isolated_env: dict[str, str]) -> None:
    result = run_hook(
        "nudge-rg-failure",
        "rg -t madeup needle",
        env=isolated_env,
        response={
            "exit_code": 2,
            "stdout": "",
            "stderr": "unrecognized file type: madeup",
        },
    )
    assert "known `-t` type" in (context(result) or "")


def test_nudges_corrupted_success_with_nonempty_output(
    isolated_env: dict[str, str],
) -> None:
    result = run_hook(
        "nudge-rg-failure",
        "printf input | rg -rn ProcessEvent",
        env=isolated_env,
        response="file.go:n(e Event)",
    )
    message = context(result) or ""
    assert "rg -n ProcessEvent" in message
    assert "--replace" in message


def test_empty_filtered_result_warns_about_ignores(
    isolated_env: dict[str, str],
) -> None:
    result = run_hook(
        "nudge-rg-failure",
        "rg -t go needle",
        env=isolated_env,
        response="Exit code 1\n",
    )
    assert "--no-ignore --hidden" in (context(result) or "")


def test_clean_success_is_silent(isolated_env: dict[str, str]) -> None:
    result = run_hook(
        "nudge-rg-failure",
        "cd src && rg -n needle",
        env=isolated_env,
        response={"exit_code": 0, "stdout": "x.go:1:needle", "stderr": ""},
    )
    assert context(result) is None
