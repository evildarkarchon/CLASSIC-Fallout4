"""Tests for the runtime/GIL pattern source guard.

The guard intentionally starts with a hard ban on new runtime constructors while
raw call-site pattern drift remains report-only unless strict mode is requested.
"""

from __future__ import annotations

from pathlib import Path

import check_runtime_gil_patterns as guard


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_runtime_constructor_outside_allowlist_fails(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    _write(
        repo / "business-logic" / "classic-demo-core" / "src" / "lib.rs",
        "pub fn bad() { let _rt = tokio::runtime::Runtime::new().unwrap(); }\n",
    )

    report = guard.scan_repo(repo)

    assert report.constructor_violations
    assert report.exit_code(strict_call_sites=False) == 1


def test_shared_runtime_and_test_constructors_are_allowed(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    _write(
        repo / "foundation" / "classic-shared-core" / "src" / "lib.rs",
        "fn owner() { let _ = tokio::runtime::Builder::new_multi_thread(); }\n",
    )
    _write(
        repo / "business-logic" / "classic-demo-core" / "src" / "lib_tests.rs",
        "fn test_runtime() { let _rt = tokio::runtime::Runtime::new().unwrap(); }\n",
    )
    _write(
        repo / "business-logic" / "classic-demo-core" / "benches" / "bench.rs",
        "fn bench_runtime() { let _rt = tokio::runtime::Runtime::new().unwrap(); }\n",
    )

    report = guard.scan_repo(repo)

    assert report.constructor_violations == []
    assert len(report.allowed_constructor_hits) == 3
    assert report.exit_code(strict_call_sites=False) == 0


def test_raw_call_sites_are_report_only_by_default_and_strict_failures(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "repo"
    _write(
        repo / "cpp-bindings" / "classic-cpp-bridge" / "src" / "files.rs",
        "fn bridge() { classic_shared_core::get_runtime().block_on(async {}); }\n",
    )
    _write(
        repo / "python-bindings" / "classic-file-io-py" / "src" / "core.rs",
        "fn py(py: Python<'_>) { pyo3_async_runtimes::tokio::future_into_py(py, async {}); }\n",
    )

    report = guard.scan_repo(repo)

    assert {hit.pattern for hit in report.call_site_hits} == {
        "shared-runtime-block-on",
        "future-into-py",
    }
    assert report.exit_code(strict_call_sites=False) == 0
    assert report.exit_code(strict_call_sites=True) == 1


def test_comments_and_legacy_tree_are_ignored(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    _write(
        repo / "business-logic" / "classic-demo-core" / "src" / "lib.rs",
        "// tokio::runtime::Runtime::new() in a comment is documentation only\n"
        "/// classic_shared_core::get_runtime().block_on(async {}) docs only\n"
        "fn ok() {}\n",
    )
    _write(
        repo / "ClassicLib-rs" / "business-logic" / "legacy" / "src" / "lib.rs",
        "fn legacy() { let _rt = tokio::runtime::Runtime::new().unwrap(); }\n",
    )

    report = guard.scan_repo(repo)

    assert report.constructor_violations == []
    assert report.call_site_hits == []
    assert report.exit_code(strict_call_sites=True) == 0
