"""Reject first-party User Settings interpretation outside its deep Rust owner."""

from __future__ import annotations

import argparse
import io
import re
import tokenize
from dataclasses import dataclass
from pathlib import Path


SOURCE_ROOTS = (
    "foundation",
    "business-logic",
    "cpp-bindings",
    "classic-cli",
    "classic-gui",
    "node-bindings",
    "python-bindings",
    "ui-applications",
)
SOURCE_SUFFIXES = {".rs", ".cpp", ".cc", ".cxx", ".h", ".hpp", ".py", ".ts", ".tsx", ".js", ".mjs"}
EXCLUDED_PARTS = {
    "target",
    "tests",
    "__test__",
    "__tests__",
    "parity-artifacts",
    "node_modules",
    ".venv",
    "build",
    "dist",
}
ALLOWED_OWNER = Path("business-logic/classic-user-settings-core")
MIRROR_TOOL = ALLOWED_OWNER / "src/bin/generate-user-settings-default-mirror"
INSTALL_PREFIXES = ("install", "build-", "install-")

RULES: tuple[tuple[str, re.Pattern[str]], ...] = (
    (
        "legacy-user-settings-type",
        re.compile(r"\b(?:ClassicConfig|PathConfig)\b"),
    ),
    (
        "legacy-generic-settings-owner",
        re.compile(
            r"(?:YamlSource|CoreYamlSource|YamlFile|CoreYamlFile)::Settings"
            r"|\bSETTINGS_IGNORE_NONE\b|\bmust_not_be_none\b"
        ),
    ),
    ("raw-user-settings-key", re.compile(r"\bCLASSIC_Settings\b")),
)
MIRROR_RULE = (
    "compatibility-mirror-runtime-use",
    re.compile(r'["\']default_settings["\']|\bCLASSIC_Info\.default_settings\b'),
)
LEGACY_MODEL_DECLARATION = re.compile(
    r"\b(?:struct|enum|type|trait)\s+(?:ClassicConfig|PathConfig)\b"
)
GENERIC_SETTINGS_ENUM = re.compile(
    r"\benum\s+(?:YamlSource|CoreYamlSource|YamlFile|CoreYamlFile)\b"
    r"[^\{]*\{[^\}]*\bSettings\b",
    re.DOTALL,
)


@dataclass(frozen=True)
class Finding:
    """One forbidden production-code ownership reference."""

    path: Path
    line: int
    rule: str
    snippet: str


def _is_excluded(path: Path) -> bool:
    """Return whether a source path is test, generated, or build output."""

    if any(part in EXCLUDED_PARTS for part in path.parts):
        return True
    return any(
        part.startswith(INSTALL_PREFIXES) for part in path.parts
    ) or path.name.endswith("_tests.rs")


def _production_sources(repo_root: Path) -> list[Path]:
    """Return deterministic first-party production source paths."""

    sources: list[Path] = []
    for root_name in SOURCE_ROOTS:
        root = repo_root / root_name
        if not root.is_dir():
            continue
        for path in root.rglob("*"):
            relative = path.relative_to(repo_root)
            if path.is_file() and path.suffix in SOURCE_SUFFIXES and not _is_excluded(relative):
                sources.append(path)
    return sorted(sources)


def _code_lines(path: Path) -> list[tuple[int, str]]:
    """Return source lines with ordinary line and block comments removed."""

    output: list[tuple[int, str]] = []
    in_block_comment = False
    text = path.read_text(encoding="utf-8", errors="replace")
    originals = text.splitlines()
    python_comment_columns: dict[int, int] = {}
    if path.suffix == ".py":
        try:
            for token in tokenize.generate_tokens(io.StringIO(text).readline):
                if token.type == tokenize.COMMENT:
                    python_comment_columns[token.start[0]] = token.start[1]
        except tokenize.TokenError:
            # An invalid Python source will fail its own parser; keep auditing the
            # recoverable lines instead of letting it disable this repository gate.
            python_comment_columns = {}

    for line_number, original in enumerate(originals, start=1):
        if line_number in python_comment_columns:
            original = original[: python_comment_columns[line_number]]
        line = original
        if in_block_comment:
            if "*/" not in line:
                continue
            line = line.split("*/", 1)[1]
            in_block_comment = False

        while "/*" in line:
            before, after = line.split("/*", 1)
            if "*/" in after:
                line = before + after.split("*/", 1)[1]
            else:
                line = before
                in_block_comment = True
                break

        stripped = line.lstrip()
        if stripped.startswith(("//", "#")):
            continue
        if "//" in line:
            line = line.split("//", 1)[0]
        if line.strip():
            output.append((line_number, line))
    return output


def audit_repository(repo_root: Path) -> list[Finding]:
    """Audit production sources and return every ownership violation."""

    repo_root = repo_root.resolve()
    findings: list[Finding] = []
    for path in _production_sources(repo_root):
        relative = path.relative_to(repo_root)
        code_lines = _code_lines(path)
        code = "\n".join(line for _, line in code_lines)
        structural_rules = (
            ("legacy-user-settings-type", LEGACY_MODEL_DECLARATION),
            ("legacy-generic-settings-owner", GENERIC_SETTINGS_ENUM),
        )
        for rule, pattern in structural_rules:
            for match in pattern.finditer(code):
                code_line = code[: match.start()].count("\n")
                line_number, line = code_lines[code_line]
                findings.append(
                    Finding(
                        path=relative,
                        line=line_number,
                        rule=rule,
                        snippet=line.strip(),
                    )
                )

        rules = [] if relative.is_relative_to(ALLOWED_OWNER) else list(RULES)
        # The generator is the sole production code allowed to inspect the checked-in
        # mirror. The deep owner must otherwise bootstrap from its Rust registry too.
        if not relative.is_relative_to(MIRROR_TOOL):
            rules.append(MIRROR_RULE)
        for line_number, line in code_lines:
            for rule, pattern in rules:
                if pattern.search(line):
                    findings.append(
                        Finding(
                            path=relative,
                            line=line_number,
                            rule=rule,
                            snippet=line.strip(),
                        )
                    )
    return findings


def main() -> int:
    """Run the ownership audit and return a process exit code."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    args = parser.parse_args()
    findings = audit_repository(args.repo_root)
    if not findings:
        print("User Settings ownership audit passed.")
        return 0

    for finding in findings:
        print(
            f"{finding.path}:{finding.line}: {finding.rule}: {finding.snippet}"
        )
    print(f"User Settings ownership audit failed with {len(findings)} finding(s).")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
