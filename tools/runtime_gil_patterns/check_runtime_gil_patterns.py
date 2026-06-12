#!/usr/bin/env python3
"""Guard CLASSIC shared-runtime and PyO3 GIL call-site patterns.

Default mode is intentionally conservative: it fails only on unauthorized Tokio
runtime construction. Raw call-site patterns are reported so migration can be
incremental; pass ``--strict-call-sites`` to make those reports fail too.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Iterable

SCAN_SUFFIXES = {".rs"}
IGNORE_DIRS = {
    ".git",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".worktrees",
    "ClassicLib-rs",
    "graphify-out",
    "target",
    "__pycache__",
}
SCAN_ROOTS = (
    "foundation",
    "business-logic",
    "cpp-bindings",
    "node-bindings",
    "python-bindings",
    "ui-applications",
    "classic-cli",
    "classic-gui",
)

CONSTRUCTOR_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("runtime-new", re.compile(r"\b(?:tokio::runtime::)?Runtime::new\s*\(")),
    (
        "runtime-builder-new-multi-thread",
        re.compile(r"\b(?:tokio::runtime::)?Builder::new_multi_thread\s*\("),
    ),
    (
        "runtime-builder-new-current-thread",
        re.compile(r"\b(?:tokio::runtime::)?Builder::new_current_thread\s*\("),
    ),
    ("tokio-main", re.compile(r"#\s*\[\s*tokio::main")),
)

CALL_SITE_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    (
        "shared-runtime-block-on",
        re.compile(
            r"(?:\bclassic_shared_core::)?\bget_runtime\s*\(\s*\)\s*\.\s*block_on\s*\("
        ),
    ),
    ("python-detach", re.compile(r"\bpy\s*\.\s*detach\s*\(")),
    ("future-into-py", re.compile(r"\bfuture_into_py\s*\(")),
)

# The single runtime owner and approved helper modules may contain the raw
# patterns they encapsulate. Path strings are repo-relative with POSIX slashes.
CONSTRUCTOR_ALLOWLIST = {
    "foundation/classic-shared-core/src/lib.rs",
}
CALL_SITE_ALLOWLIST = {
    "cpp-bindings/classic-cpp-bridge/src/runtime_support.rs",
    "foundation/classic-shared-py/src/lib.rs",
    "node-bindings/classic-node/src/runtime.rs",
}


@dataclass(frozen=True)
class PatternHit:
    path: str
    line: int
    pattern: str
    text: str


@dataclass
class GuardReport:
    repo_root: str
    constructor_violations: list[PatternHit] = field(default_factory=list)
    allowed_constructor_hits: list[PatternHit] = field(default_factory=list)
    call_site_hits: list[PatternHit] = field(default_factory=list)

    def exit_code(self, *, strict_call_sites: bool) -> int:
        if self.constructor_violations:
            return 1
        if strict_call_sites and self.call_site_hits:
            return 1
        return 0

    def as_json(self) -> dict[str, object]:
        return {
            "repoRoot": self.repo_root,
            "constructorViolations": [asdict(hit) for hit in self.constructor_violations],
            "allowedConstructorHits": [asdict(hit) for hit in self.allowed_constructor_hits],
            "callSiteHits": [asdict(hit) for hit in self.call_site_hits],
            "summary": {
                "constructorViolationCount": len(self.constructor_violations),
                "allowedConstructorCount": len(self.allowed_constructor_hits),
                "callSiteHitCount": len(self.call_site_hits),
            },
        }


def _rel(path: Path, repo_root: Path) -> str:
    return path.relative_to(repo_root).as_posix()


def _is_ignored(path: Path, repo_root: Path) -> bool:
    try:
        parts = path.relative_to(repo_root).parts
    except ValueError:
        return True
    return any(part in IGNORE_DIRS for part in parts)


def _is_test_or_bench(rel_path: str) -> bool:
    parts = Path(rel_path).parts
    return (
        "/tests/" in f"/{rel_path}"
        or "/benches/" in f"/{rel_path}"
        or rel_path.endswith("_tests.rs")
        or Path(rel_path).name.startswith("test_")
        or "tests" in parts
        or "benches" in parts
    )


def _is_comment_only(line: str) -> bool:
    stripped = line.strip()
    if not stripped:
        return True
    return stripped.startswith(("//", "///", "//!", "*", "/*", "*/"))


def _iter_source_files(repo_root: Path) -> Iterable[Path]:
    for root_name in SCAN_ROOTS:
        root = repo_root / root_name
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if path.is_dir() or _is_ignored(path, repo_root):
                continue
            if path.suffix in SCAN_SUFFIXES:
                yield path


def _scan_file(path: Path, repo_root: Path, report: GuardReport) -> None:
    rel_path = _rel(path, repo_root)
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except UnicodeDecodeError:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()

    for line_no, line in enumerate(lines, start=1):
        if _is_comment_only(line):
            continue

        for pattern_name, pattern in CONSTRUCTOR_PATTERNS:
            if pattern.search(line):
                hit = PatternHit(rel_path, line_no, pattern_name, line.strip())
                if rel_path in CONSTRUCTOR_ALLOWLIST or _is_test_or_bench(rel_path):
                    report.allowed_constructor_hits.append(hit)
                else:
                    report.constructor_violations.append(hit)

        if rel_path in CALL_SITE_ALLOWLIST:
            continue

        for pattern_name, pattern in CALL_SITE_PATTERNS:
            if pattern.search(line):
                report.call_site_hits.append(
                    PatternHit(rel_path, line_no, pattern_name, line.strip())
                )


def scan_repo(repo_root: Path | str) -> GuardReport:
    """Scan a repository tree and return runtime/GIL pattern findings."""
    root = Path(repo_root).resolve()
    report = GuardReport(repo_root=str(root))
    for path in sorted(_iter_source_files(root)):
        _scan_file(path, root, report)
    return report


def _format_hits(title: str, hits: list[PatternHit], *, limit: int = 40) -> list[str]:
    if not hits:
        return [f"{title}: none"]

    lines = [f"{title}: {len(hits)}"]
    for hit in hits[:limit]:
        lines.append(f"  {hit.path}:{hit.line} [{hit.pattern}] {hit.text}")
    remaining = len(hits) - limit
    if remaining > 0:
        lines.append(f"  ... {remaining} more")
    return lines


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path.cwd(),
        help="Repository root to scan (default: current directory).",
    )
    parser.add_argument(
        "--strict-call-sites",
        action="store_true",
        help="Fail on raw block_on / py.detach / future_into_py call-site hits.",
    )
    parser.add_argument(
        "--json-out",
        type=Path,
        help="Optional path to write the full JSON report.",
    )
    args = parser.parse_args(argv)

    report = scan_repo(args.repo_root)
    payload = report.as_json()

    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    lines: list[str] = ["Runtime/GIL pattern guard"]
    lines.extend(_format_hits("Unauthorized runtime constructors", report.constructor_violations))
    lines.extend(_format_hits("Allowed runtime constructors", report.allowed_constructor_hits, limit=12))
    call_site_title = "Raw call-site pattern hits"
    if not args.strict_call_sites:
        call_site_title += " (report-only; pass --strict-call-sites to fail)"
    lines.extend(_format_hits(call_site_title, report.call_site_hits))
    print("\n".join(lines))

    return report.exit_code(strict_call_sites=args.strict_call_sites)


if __name__ == "__main__":
    sys.exit(main())
