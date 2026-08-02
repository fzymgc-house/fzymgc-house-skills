"""Shared shell/rg parsing and telemetry for the grepping hooks."""

from __future__ import annotations

import codecs
import json
import os
import re
import shlex
import subprocess
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Iterator


_ENV_ASSIGNMENT = re.compile(r"^[A-Za-z_]\w*=", re.ASCII)
_SHELL_PREFIXES = {"!", "if", "then", "while", "until", "do", "{"}
_VALUE_SHORT_OPTIONS = set("ABCEefgjMmrtT") | {"d"}
_VALUE_LONG_OPTIONS = {
    "--after-context",
    "--before-context",
    "--context",
    "--context-separator",
    "--dfa-size-limit",
    "--encoding",
    "--engine",
    "--file",
    "--glob",
    "--iglob",
    "--max-columns",
    "--max-count",
    "--max-depth",
    "--max-filesize",
    "--path-separator",
    "--pre",
    "--pre-glob",
    "--regexp",
    "--regex-size-limit",
    "--replace",
    "--sort",
    "--sortr",
    "--type",
    "--type-add",
    "--type-clear",
    "--type-not",
}
_SHORT_NAMES = {
    "E": "encoding",
    "F": "fixed-strings",
    "P": "pcre2",
    "U": "multiline",
    "e": "regexp",
    "f": "file",
    "g": "glob",
    "h": "help",
    "o": "only-matching",
    "r": "replace",
    "t": "type",
    "T": "type-not",
}
_LONG_NAMES = {
    "--encoding": "encoding",
    "--fixed-strings": "fixed-strings",
    "--glob": "glob",
    "--help": "help",
    "--iglob": "glob",
    "--multiline": "multiline",
    "--only-matching": "only-matching",
    "--pcre2": "pcre2",
    "--regexp": "regexp",
    "--replace": "replace",
    "--type": "type",
    "--type-not": "type-not",
}
# Word characters adjacent to `\|` signal BRE-style alternation (`foo\|bar`).
# A bare `\|` between non-word characters (e.g. `rg '^\| x \|'` searching a
# markdown table for literal pipes) is legitimate and must not be rewritten.
_BRE_ALTERNATION = re.compile(r"\w\\\||\\\|\w")
_PCRE_ONLY = re.compile(r"\(\?(?:[=!]|<[=!])|\\K|\\[1-9][0-9]*")
_RG_IN_REMOTE_COMMAND = re.compile(r"(?:^|[\s;&|])(?:[^\s;&|]*/)?rg(?:\s|$)")


@dataclass(frozen=True)
class ShellStage:
    text: str
    separator: str | None


@dataclass(frozen=True)
class RgInvocation:
    stage: ShellStage
    tokens: tuple[str, ...]
    rg_index: int

    @property
    def args(self) -> tuple[str, ...]:
        return self.tokens[self.rg_index + 1 :]


@dataclass(frozen=True)
class Option:
    name: str
    token_index: int
    value: str | None = None
    attached: bool = False
    short_index: int | None = None


@dataclass(frozen=True)
class Pattern:
    value: str
    token_index: int


@dataclass(frozen=True)
class RgScan:
    options: tuple[Option, ...]
    patterns: tuple[Pattern, ...]

    def has(self, name: str) -> bool:
        return any(option.name == name for option in self.options)


@dataclass(frozen=True)
class GuardIssue:
    rule: str
    message: str
    corrected: str


def shell_stages(command: str) -> list[ShellStage]:
    """Split at unquoted shell command/pipeline separators."""
    stages: list[ShellStage] = []
    start = 0
    quote: str | None = None
    escaped = False
    i = 0
    preceding: str | None = None
    while i < len(command):
        char = command[i]
        if escaped:
            escaped = False
            i += 1
            continue
        if char == "\\" and quote != "'":
            escaped = True
            i += 1
            continue
        if quote:
            if char == quote:
                quote = None
            i += 1
            continue
        if char in {"'", '"'}:
            quote = char
            i += 1
            continue

        separator: str | None = None
        width = 1
        if command.startswith("&&", i) or command.startswith("||", i):
            separator = command[i : i + 2]
            width = 2
        elif char in {";", "|", "\n"}:
            separator = char
        if separator is None:
            i += 1
            continue

        text = command[start:i].strip()
        if text:
            stages.append(ShellStage(text=text, separator=preceding))
        preceding = separator
        start = i + width
        i += width

    text = command[start:].strip()
    if text:
        stages.append(ShellStage(text=text, separator=preceding))
    return stages


_WRAPPERS = {"sudo", "nice", "nohup", "time", "stdbuf", "timeout", "xargs"}
_WRAPPER_VALUE_FLAGS = {
    "sudo": {"-u", "-g", "-p", "-C", "-D", "-R", "-T", "-U"},
    "xargs": {"-I", "-i", "-n", "-P", "-s", "-d", "-a", "-E", "-L", "-l"},
    "timeout": {"-k", "-s", "--kill-after", "--signal"},
    "nice": {"-n", "--adjustment"},
    "stdbuf": {"-i", "-o", "-e"},
}


def _command_index(tokens: list[str]) -> int | None:
    """Index of the effective command word, skipping shell/env/wrapper prefixes."""
    index = 0
    changed = True
    while changed and index < len(tokens):
        changed = False
        while index < len(tokens) and tokens[index] in _SHELL_PREFIXES:
            index += 1
            changed = True
        while index < len(tokens) and _ENV_ASSIGNMENT.match(tokens[index]):
            index += 1
            changed = True
        if index < len(tokens) and tokens[index] in {"command", "builtin"}:
            index += 1
            changed = True
            while index < len(tokens) and tokens[index].startswith("-"):
                index += 1
        if index < len(tokens) and tokens[index] == "env":
            index += 1
            changed = True
            while index < len(tokens):
                token = tokens[index]
                if _ENV_ASSIGNMENT.match(token) or token.startswith("-"):
                    index += 1
                else:
                    break
        if index < len(tokens):
            wrapper = os.path.basename(tokens[index])
            if wrapper in _WRAPPERS:
                index += 1
                changed = True
                value_flags = _WRAPPER_VALUE_FLAGS.get(wrapper, set())
                while index < len(tokens) and tokens[index].startswith("-"):
                    flag = tokens[index]
                    index += 1
                    if flag == "--":
                        break
                    if flag in value_flags and index < len(tokens):
                        index += 1
                if wrapper == "timeout" and index < len(tokens):
                    index += 1  # the DURATION positional precedes the command
    return index if index < len(tokens) else None


def iter_rg_invocations(command: str) -> Iterator[RgInvocation]:
    for stage in shell_stages(command):
        try:
            tokens = shlex.split(stage.text, comments=False, posix=True)
        except ValueError:
            continue
        index = _command_index(tokens)
        if index is None or os.path.basename(tokens[index]) != "rg":
            continue
        yield RgInvocation(stage=stage, tokens=tuple(tokens), rg_index=index)


def scan_rg(invocation: RgInvocation) -> RgScan:
    """Parse enough of rg's option grammar to locate risky flags and patterns."""
    args = invocation.args
    options: list[Option] = []
    patterns: list[Pattern] = []
    positional: list[Pattern] = []
    explicit_pattern = False
    after_options = False
    index = 0

    while index < len(args):
        token = args[index]
        absolute_index = invocation.rg_index + 1 + index
        if after_options:
            positional.append(Pattern(token, absolute_index))
            index += 1
            continue
        if token == "--":
            after_options = True
            index += 1
            continue
        if token.startswith("--") and token != "--":
            name, equals, attached_value = token.partition("=")
            normalized = _LONG_NAMES.get(name, name.removeprefix("--"))
            value: str | None = attached_value if equals else None
            attached = bool(equals)
            if name in _VALUE_LONG_OPTIONS and not equals and index + 1 < len(args):
                value = args[index + 1]
                index += 1
            options.append(Option(normalized, absolute_index, value, attached))
            if normalized == "regexp" and value is not None:
                explicit_pattern = True
                pattern_index = absolute_index if attached else absolute_index + 1
                patterns.append(Pattern(value, pattern_index))
            elif normalized == "file":
                explicit_pattern = True
            index += 1
            continue
        if token.startswith("-") and token != "-":
            chars = token[1:]
            short_index = 0
            while short_index < len(chars):
                char = chars[short_index]
                normalized = _SHORT_NAMES.get(char, char)
                value: str | None = None
                attached = False
                if char in _VALUE_SHORT_OPTIONS:
                    if short_index + 1 < len(chars):
                        value = chars[short_index + 1 :]
                        attached = True
                    elif index + 1 < len(args):
                        value = args[index + 1]
                        index += 1
                    options.append(
                        Option(normalized, absolute_index, value, attached, short_index)
                    )
                    if normalized == "regexp" and value is not None:
                        explicit_pattern = True
                        pattern_index = (
                            absolute_index if attached else absolute_index + 1
                        )
                        patterns.append(Pattern(value, pattern_index))
                    elif normalized == "file":
                        explicit_pattern = True
                    break
                options.append(
                    Option(normalized, absolute_index, short_index=short_index)
                )
                short_index += 1
            index += 1
            continue
        positional.append(Pattern(token, absolute_index))
        index += 1

    if not explicit_pattern and positional:
        patterns.append(positional[0])
    return RgScan(options=tuple(options), patterns=tuple(patterns))


def _known_encoding(value: str | None) -> bool:
    if not value:
        return False
    if value.lower() in {"auto", "none"}:
        return True
    try:
        codecs.lookup(value)
    except LookupError:
        # rg accepts the WHATWG Encoding Standard labels; Python's codec aliases
        # omit a few legitimate values such as x-user-defined. Ask rg only on
        # this rare slow path so valid encodings are never denied.
        try:
            result = subprocess.run(
                ["rg", f"--encoding={value}", "--version"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=1,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired):
            return False
        return result.returncode == 0
    return True


def _stage_command(tokens: list[str]) -> str:
    return shlex.join(tokens)


def _remove_short_char(
    token: str, char_index: int, *, preserve_tail: bool
) -> str | None:
    chars = token[1:]
    prefix = chars[:char_index]
    suffix = chars[char_index + 1 :] if preserve_tail else ""
    remainder = prefix + suffix
    return f"-{remainder}" if remainder else None


def _correct_replace(invocation: RgInvocation, replacements: list[Option]) -> str:
    tokens = list(invocation.tokens)
    for option in sorted(replacements, key=lambda item: item.token_index, reverse=True):
        token = tokens[option.token_index]
        if token.startswith("--replace"):
            tokens.pop(option.token_index)
        elif option.short_index is not None:
            preserve = bool(option.attached and (option.value or "").isalpha())
            updated = _remove_short_char(
                token, option.short_index, preserve_tail=preserve
            )
            if updated:
                tokens[option.token_index] = updated
            else:
                tokens.pop(option.token_index)
    return _stage_command(tokens)


def _correct_legacy(invocation: RgInvocation) -> str:
    tokens = list(invocation.tokens)
    corrected: list[str] = []
    index = 0
    while index < len(tokens):
        token = tokens[index]
        if index <= invocation.rg_index:
            corrected.append(token)
            index += 1
            continue
        if token in {"-R", "--recursive", "--no-pager"}:
            index += 1
            continue
        if token.startswith("-") and not token.startswith("--") and "R" in token[1:]:
            new_token = "-" + token[1:].replace("R", "")
            if new_token != "-":
                corrected.append(new_token)
            index += 1
            continue
        matched = False
        for name, exclude, directory in (
            ("--include", False, False),
            ("--exclude", True, False),
            ("--exclude-dir", True, True),
        ):
            if token == name or token.startswith(f"{name}="):
                if "=" in token:
                    value = token.split("=", 1)[1]
                elif index + 1 < len(tokens):
                    value = tokens[index + 1]
                    index += 1
                else:
                    value = "<glob>"
                if directory and not value.endswith("/**"):
                    value = f"{value.rstrip('/')}/**"
                if exclude and not value.startswith("!"):
                    value = f"!{value}"
                corrected.extend(["-g", value])
                matched = True
                break
        if not matched:
            corrected.append(token)
        index += 1
    return _stage_command(corrected)


def _correct_encoding(invocation: RgInvocation, option: Option) -> str:
    tokens = list(invocation.tokens)
    token = tokens[option.token_index]
    if option.short_index is None:
        return _stage_command(tokens)
    updated = _remove_short_char(token, option.short_index, preserve_tail=False)
    if updated:
        tokens[option.token_index] = updated
    else:
        tokens.pop(option.token_index)
    return _stage_command(tokens)


def _correct_patterns(invocation: RgInvocation, scan: RgScan) -> str:
    tokens = list(invocation.tokens)
    for pattern in scan.patterns:
        tokens[pattern.token_index] = tokens[pattern.token_index].replace("\\|", "|")
    return _stage_command(tokens)


def _add_pcre(invocation: RgInvocation) -> str:
    tokens = list(invocation.tokens)
    tokens.insert(invocation.rg_index + 1, "-P")
    return _stage_command(tokens)


def guard_issues(invocation: RgInvocation) -> list[GuardIssue]:
    scan = scan_rg(invocation)
    issues: list[GuardIssue] = []

    replacements = [option for option in scan.options if option.name == "replace"]
    if replacements and not scan.has("only-matching"):
        corrected = _correct_replace(invocation, replacements)
        issues.append(
            GuardIssue(
                "replace-without-only-matching",
                "rg -r is --replace; recursion is already the default. "
                f"Use: `{corrected}`. For a real replacement, use "
                "`rg -o --replace '$1' ...`.",
                corrected,
            )
        )

    has_legacy = any(
        token in {"-R", "--recursive", "--no-pager"}
        or token.startswith(("--include", "--exclude"))
        or (token.startswith("-") and not token.startswith("--") and "R" in token[1:])
        for token in invocation.args
    )
    if has_legacy:
        corrected = _correct_legacy(invocation)
        issues.append(
            GuardIssue(
                "grep-only-flag",
                "rg is recursive by default and uses `-g`/`-t` for file filters. "
                f"Use: `{corrected}`.",
                corrected,
            )
        )

    bad_encodings = [
        option
        for option in scan.options
        if option.name == "encoding"
        and option.short_index is not None
        and not _known_encoding(option.value)
    ]
    if bad_encodings:
        corrected = _correct_encoding(invocation, bad_encodings[0])
        issues.append(
            GuardIssue(
                "grep-ere-flag",
                "rg is ERE-like by default; `-E` selects an encoding. "
                f"Drop it: `{corrected}`.",
                corrected,
            )
        )

    patterns = [pattern.value for pattern in scan.patterns]
    if not scan.has("fixed-strings") and any(
        _BRE_ALTERNATION.search(p) for p in patterns
    ):
        corrected = _correct_patterns(invocation, scan)
        issues.append(
            GuardIssue(
                "bre-alternation",
                "In rg, `\\|` matches a literal pipe; alternation is bare `|`. "
                f"Use: `{corrected}`.",
                corrected,
            )
        )

    if (
        not scan.has("fixed-strings")
        and not scan.has("pcre2")
        and any(_PCRE_ONLY.search(pattern) for pattern in patterns)
    ):
        corrected = _add_pcre(invocation)
        issues.append(
            GuardIssue(
                "pcre2-required",
                "Lookaround, `\\K`, and backreferences require PCRE2. "
                f"Add `-P`: `{corrected}`.",
                corrected,
            )
        )
    return issues


def advisory_warnings(invocation: RgInvocation) -> list[str]:
    scan = scan_rg(invocation)
    warnings: list[str] = []
    if scan.has("help"):
        warnings.append(
            "rg `-h` means `--help`; if you meant grep's no-filename mode, use "
            "`--no-filename`."
        )
    if not scan.has("multiline") and any(
        "\\n" in pattern.value for pattern in scan.patterns
    ):
        warnings.append(
            "rg multiline search is off: a pattern containing `\\n` needs `-U` "
            "(or use a single-line pattern)."
        )
    return warnings


def has_filters(invocation: RgInvocation) -> bool:
    scan = scan_rg(invocation)
    return scan.has("glob") or scan.has("type") or scan.has("type-not")


def remote_rg_stages(command: str) -> list[str]:
    remote: list[str] = []
    for stage in shell_stages(command):
        try:
            tokens = shlex.split(stage.text, comments=False, posix=True)
        except ValueError:
            continue
        index = _command_index(tokens)
        if index is None or os.path.basename(tokens[index]) != "ssh":
            continue
        if any(_RG_IN_REMOTE_COMMAND.search(token) for token in tokens[index + 1 :]):
            remote.append(stage.text)
    return remote


def bypassed(command: str) -> bool:
    return bool(re.match(r"^\s*RG_GUARD_OK=1(?:\s|$)", command))


def log_decision(
    hook_input: dict[str, object],
    *,
    decision: str,
    rules: list[str],
    stage: str,
) -> None:
    """Best-effort JSONL telemetry; hook behavior never depends on logging."""
    record = {
        "timestamp": datetime.now(UTC).isoformat(),
        "decision": decision,
        "rules": rules,
        "stage": stage,
        "cwd": hook_input.get("cwd", ""),
        "session_id": hook_input.get("session_id", ""),
        "agent_id": hook_input.get("agent_id", ""),
    }
    path = Path(os.path.expanduser("~/.claude/logs/rg-guard.jsonl"))
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            json.dump(record, handle, sort_keys=True)
            handle.write("\n")
    except OSError:
        pass
