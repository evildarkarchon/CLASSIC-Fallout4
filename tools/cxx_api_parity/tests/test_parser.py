"""Unit tests for tools/cxx_api_parity/generate_baseline.py parser helpers.

RED phase: these tests will fail until Task 2 implements the parser.
"""

from __future__ import annotations

import hashlib
import sys
from pathlib import Path

import pytest

# Make tools/cxx_api_parity/ importable as top-level during tests.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from generate_baseline import (  # noqa: E402
    parse_build_rs_file_list,
    parse_cxx_bridge_surface,
)


def _load_fixture(fixture_dir: Path, name: str) -> str:
    return (fixture_dir / name).read_text(encoding="utf-8")


def _rows_by_symbol(payload: dict) -> dict[tuple[str, str, str], dict]:
    """Index rows by (bridgeModule, kind, rustSymbol) for easy lookup."""
    return {
        (row["bridgeModule"], row["kind"], row["rustSymbol"]): row
        for row in payload["entries"]
    }


class TestParseExternRust:
    def test_parse_extern_rust_functions(self, fixture_dir: Path, tmp_path: Path):
        """CXXG-01: parse_cxx_bridge_surface extracts extern Rust functions."""
        # Build a synthetic bridge-crate tree under tmp_path
        crate = tmp_path / "bridge"
        (crate / "src").mkdir(parents=True)
        (crate / "build.rs").write_text(
            "#[cfg(windows)]\nfn main() {\n"
            '    cxx_build::bridges(["src/simple.rs"])\n'
            '        .compile("x");\n}\n',
            encoding="utf-8",
        )
        (crate / "src/simple.rs").write_text(
            _load_fixture(fixture_dir, "simple_ffi.rs"), encoding="utf-8"
        )

        payload = parse_cxx_bridge_surface(tmp_path, "bridge")
        rows = _rows_by_symbol(payload)

        assert ("simple", "function", "simple_hello") in rows
        hello = rows[("simple", "function", "simple_hello")]
        assert hello["blockOrigin"] == "Rust"
        assert hello["signature"]["args"] == [{"name": "name", "type": "&str"}]
        assert hello["signature"]["returnType"] == "String"

        assert ("simple", "function", "simple_add") in rows
        add = rows[("simple", "function", "simple_add")]
        assert add["signature"]["args"] == [
            {"name": "a", "type": "u32"},
            {"name": "b", "type": "u32"},
        ]
        assert add["signature"]["returnType"] == "u32"


class TestParseSharedStructs:
    def test_parse_shared_structs(self, fixture_dir: Path, tmp_path: Path):
        """CXXG-01: parser extracts shared structs with ordered (name, type) fields."""
        crate = tmp_path / "bridge"
        (crate / "src").mkdir(parents=True)
        (crate / "build.rs").write_text(
            'fn main() { cxx_build::bridges(["src/struct_ffi.rs"]).compile("x"); }\n',
            encoding="utf-8",
        )
        (crate / "src/struct_ffi.rs").write_text(
            _load_fixture(fixture_dir, "struct_ffi.rs"), encoding="utf-8"
        )

        payload = parse_cxx_bridge_surface(tmp_path, "bridge")
        rows = _rows_by_symbol(payload)

        assert ("struct_ffi", "struct", "PersonDto") in rows
        person = rows[("struct_ffi", "struct", "PersonDto")]
        assert person["fields"] == [
            {"name": "name", "type": "String"},
            {"name": "age", "type": "u32"},
            {"name": "tags", "type": "Vec<String>"},
        ]
        assert "signature" not in person
        assert "variants" not in person


class TestParseEnums:
    def test_parse_enums(self, fixture_dir: Path, tmp_path: Path):
        """CXXG-01: parser extracts enums, strips discriminants and #[derive] attrs."""
        crate = tmp_path / "bridge"
        (crate / "src").mkdir(parents=True)
        (crate / "build.rs").write_text(
            'fn main() { cxx_build::bridges(["src/enum_ffi.rs"]).compile("x"); }\n',
            encoding="utf-8",
        )
        (crate / "src/enum_ffi.rs").write_text(
            _load_fixture(fixture_dir, "enum_ffi.rs"), encoding="utf-8"
        )

        payload = parse_cxx_bridge_surface(tmp_path, "bridge")
        rows = _rows_by_symbol(payload)

        assert ("enum_ffi", "enum", "SimpleKind") in rows
        simple = rows[("enum_ffi", "enum", "SimpleKind")]
        assert simple["variants"] == ["A", "B", "C"]

        assert ("enum_ffi", "enum", "ProgressEventKind") in rows
        progress = rows[("enum_ffi", "enum", "ProgressEventKind")]
        assert progress["variants"] == ["Queued", "Started", "Completed"]

        # #[derive(...)] lines must not become contract rows
        assert not any(
            row["rustSymbol"] in {"Debug", "Clone", "Copy", "PartialEq", "Eq"}
            for row in payload["entries"]
        )


class TestParseOpaqueTypes:
    def test_parse_opaque_types(self, fixture_dir: Path, tmp_path: Path):
        """CXXG-01: parser extracts opaque types (type Foo;) from extern Rust."""
        crate = tmp_path / "bridge"
        (crate / "src").mkdir(parents=True)
        (crate / "build.rs").write_text(
            'fn main() { cxx_build::bridges(["src/opaque_ffi.rs"]).compile("x"); }\n',
            encoding="utf-8",
        )
        (crate / "src/opaque_ffi.rs").write_text(
            _load_fixture(fixture_dir, "opaque_ffi.rs"), encoding="utf-8"
        )

        payload = parse_cxx_bridge_surface(tmp_path, "bridge")
        rows = _rows_by_symbol(payload)

        assert ("opaque_ffi", "opaque", "DataStore") in rows
        datastore = rows[("opaque_ffi", "opaque", "DataStore")]
        assert datastore["blockOrigin"] == "Rust"
        assert "signature" not in datastore
        assert "fields" not in datastore
        assert "variants" not in datastore


class TestParseExternCpp:
    def test_parse_extern_cpp(self, fixture_dir: Path, tmp_path: Path):
        """CXXG-01: parser extracts items from `unsafe extern "C++"` blocks
        and marks them with blockOrigin="C++". include!() is skipped."""
        crate = tmp_path / "bridge"
        (crate / "src").mkdir(parents=True)
        # Install the mixed_ffi.rs fixture as src/mixed.rs so the bridgeModule
        # filename stem matches the namespace last segment ("mixed").
        (crate / "build.rs").write_text(
            'fn main() { cxx_build::bridges(["src/mixed.rs"]).compile("x"); }\n',
            encoding="utf-8",
        )
        (crate / "src/mixed.rs").write_text(
            _load_fixture(fixture_dir, "mixed_ffi.rs"), encoding="utf-8"
        )

        payload = parse_cxx_bridge_surface(tmp_path, "bridge")
        rows = _rows_by_symbol(payload)

        # C++ opaque type
        assert ("mixed", "opaque", "ScanProgressCallback") in rows
        cpp_type = rows[("mixed", "opaque", "ScanProgressCallback")]
        assert cpp_type["blockOrigin"] == "C++"

        # C++ function
        assert ("mixed", "function", "on_progress") in rows
        cpp_fn = rows[("mixed", "function", "on_progress")]
        assert cpp_fn["blockOrigin"] == "C++"
        assert cpp_fn["signature"]["returnType"] in (None, "")

        # include!() must NOT become a row
        assert not any(
            "fake_header" in row["rustSymbol"] or "include" in row["rustSymbol"]
            for row in payload["entries"]
        )


class TestParseBuildRs:
    def test_parse_build_rs(self, fake_build_rs_text: str):
        """CXXG-01: parse_build_rs_file_list extracts multi-line file list."""
        files = parse_build_rs_file_list(fake_build_rs_text)
        assert files == [
            "src/simple.rs",
            "src/struct_ffi.rs",
            "src/enum_ffi.rs",
            "src/opaque_ffi.rs",
            "src/mixed_ffi.rs",
        ]

    def test_build_rs_missing_bridges(self):
        """CXXG-01 / D-07: parser MUST raise on missing cxx_build::bridges() — no hardcoded fallback."""
        with pytest.raises(ValueError, match="cxx_build::bridges"):
            parse_build_rs_file_list('fn main() { println!("noop"); }\n')


class TestDeterminism:
    def test_deterministic_output(self, fixture_dir: Path, tmp_path: Path):
        """CXXG-01: two runs against unchanged source produce byte-identical JSON (minus generated_at_utc)."""
        crate = tmp_path / "bridge"
        (crate / "src").mkdir(parents=True)
        (crate / "build.rs").write_text(
            "fn main() { cxx_build::bridges(["
            '"src/simple.rs","src/struct_ffi.rs","src/enum_ffi.rs",'
            '"src/opaque_ffi.rs","src/mixed_ffi.rs"'
            ']).compile("x"); }\n',
            encoding="utf-8",
        )
        # Map fixture filenames to the names referenced inside the synthetic build.rs.
        # simple_ffi.rs is referenced as src/simple.rs; the rest keep their _ffi.rs suffix.
        fixture_to_target = {
            "simple_ffi.rs": "simple.rs",
            "struct_ffi.rs": "struct_ffi.rs",
            "enum_ffi.rs": "enum_ffi.rs",
            "opaque_ffi.rs": "opaque_ffi.rs",
            "mixed_ffi.rs": "mixed_ffi.rs",
        }
        for fixture_name, target_name in fixture_to_target.items():
            (crate / "src" / target_name).write_text(
                _load_fixture(fixture_dir, fixture_name), encoding="utf-8"
            )

        payload_a = parse_cxx_bridge_surface(tmp_path, "bridge")
        payload_b = parse_cxx_bridge_surface(tmp_path, "bridge")
        payload_a.pop("generated_at_utc", None)
        payload_b.pop("generated_at_utc", None)
        assert payload_a == payload_b

        # Entry sort order: (bridgeModule, kind, rustSymbol)
        sort_keys = [
            (r["bridgeModule"], r["kind"], r["rustSymbol"])
            for r in payload_a["entries"]
        ]
        assert sort_keys == sorted(sort_keys)

        # id field recipe
        for row in payload_a["entries"]:
            expected = hashlib.sha256(
                f"{row['rustSymbol']}:{row['kind']}:{row['bridgeModule']}".encode()
            ).hexdigest()[:16]
            assert row["id"] == expected, f"bad id for {row['rustSymbol']}"


class TestMixedFfiInventory:
    def test_parse_mixed_ffi_complete_inventory(
        self, fixture_dir: Path, tmp_path: Path
    ):
        """CXXG-01: mixed_ffi.rs produces exactly the hand-counted 7 rows."""
        crate = tmp_path / "bridge"
        (crate / "src").mkdir(parents=True)
        # Install the mixed_ffi.rs fixture as src/mixed.rs so the bridgeModule
        # filename stem matches the namespace last segment ("mixed").
        (crate / "build.rs").write_text(
            'fn main() { cxx_build::bridges(["src/mixed.rs"]).compile("x"); }\n',
            encoding="utf-8",
        )
        (crate / "src/mixed.rs").write_text(
            _load_fixture(fixture_dir, "mixed_ffi.rs"), encoding="utf-8"
        )

        payload = parse_cxx_bridge_surface(tmp_path, "bridge")
        mixed_rows = [r for r in payload["entries"] if r["bridgeModule"] == "mixed"]
        assert len(mixed_rows) == 7, (
            f"expected 7 rows for mixed_ffi.rs, got {len(mixed_rows)}: "
            f"{[r['rustSymbol'] for r in mixed_rows]}"
        )

        symbols = {r["rustSymbol"] for r in mixed_rows}
        assert symbols == {
            "BatchProgressEventKind",  # enum
            "BatchProgressEvent",  # struct
            "ScanProgressCallback",  # C++ opaque
            "on_progress",  # C++ fn
            "MixedOrchestrator",  # Rust opaque
            "orchestrator_new",  # Rust fn
            "orchestrator_run",  # Rust fn
        }


def test_cxx_parser_rejects_legacy_bridge_root(tmp_path: Path):
    bridge = tmp_path / "cpp-bindings" / "classic-cpp-bridge"
    (bridge / "src").mkdir(parents=True)
    (bridge / "build.rs").write_text(
        'fn main() { cxx_build::bridges(["src/simple.rs"]).compile("x"); }\n',
        encoding="utf-8",
    )
    (bridge / "src" / "simple.rs").write_text(
        '#[cxx::bridge]\nmod ffi { extern "Rust" { fn hello() -> bool; } }\n',
        encoding="utf-8",
    )

    payload = parse_cxx_bridge_surface(tmp_path)
    assert payload["entries"][0]["sourceFile"].startswith(
        "cpp-bindings/classic-cpp-bridge/"
    )
    assert "ClassicLib-rs/cpp-bindings" not in payload["entries"][0]["sourceFile"]
