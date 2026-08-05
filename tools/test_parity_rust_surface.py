"""Unit tests for the shared Rust public-surface parser.

Two classes of defect are locked down here, both of which silently made the
parity gates less representative than their green output suggested:

* ``pub const fn foo(...)`` matched the type pattern and was recorded as a
  const *named* ``fn``. 131 declarations collapsed into one bogus symbol that
  contract rows could then "match" against.
* ``pub const fn`` and ``pub async fn`` were missed by the function pattern
  entirely -- 204 public functions, 73 of them async, invisible to both gates.

Lives directly in ``tools/`` for the same reason as
``test_parity_artifact_io.py``: each ``tools/*_api_parity/tests/`` directory
already contributes a top-level ``tests.conftest`` module.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from parity_rust_surface import (
    build_lookup,
    collect_crate_sources,
    count_rust_params,
    expand_pub_use_statement,
    extract_rust_symbols,
    normalize_whitespace,
    parse_rust_surface,
    split_top_level_items,
)


def symbols_of(source: str) -> list[dict]:
    """Run the extractor over one synthetic source file."""
    entries: list[dict] = []
    extract_rust_symbols(entries, source, "src/lib.rs", "test-crate", "test")
    return entries


def names_by_kind(entries: list[dict], kind: str) -> set[str]:
    return {e["symbol"] for e in entries if e["kind"] == kind}


class TestConstFnRegression:
    def test_pub_const_fn_is_not_recorded_as_a_const_named_fn(self) -> None:
        """The exact bug: `pub const fn` matched the const/static pattern."""
        entries = symbols_of("pub const fn as_str(&self) -> &str { }\n")
        assert "fn" not in {e["symbol"] for e in entries}
        assert names_by_kind(entries, "const") == set()

    def test_pub_const_fn_is_recorded_as_a_function(self) -> None:
        entries = symbols_of("pub const fn as_str(&self) -> &str { }\n")
        assert names_by_kind(entries, "function") == {"as_str"}

    def test_pub_async_fn_is_recorded(self) -> None:
        """73 public async functions were invisible before this."""
        entries = symbols_of("pub async fn analyze(path: &Path) -> Result<()> { }\n")
        assert names_by_kind(entries, "function") == {"analyze"}

    def test_unsafe_and_extern_fn_forms_are_recorded(self) -> None:
        entries = symbols_of(
            'pub unsafe fn raw(ptr: *const u8) { }\n'
            'pub extern "C" fn exported(a: i32) { }\n'
        )
        assert names_by_kind(entries, "function") == {"raw", "exported"}

    def test_combined_modifiers_are_recorded(self) -> None:
        """Rust permits combinations such as `pub const unsafe fn`."""
        entries = symbols_of("pub const unsafe fn tricky(x: u8) -> u8 { }\n")
        assert names_by_kind(entries, "function") == {"tricky"}

    def test_a_real_pub_const_is_still_recorded(self) -> None:
        """The `(?!fn\\b)` guard must not swallow ordinary consts."""
        entries = symbols_of("pub const MAX_CACHE_TTL: u64 = 300;\n")
        assert names_by_kind(entries, "const") == {"MAX_CACHE_TTL"}

    def test_a_const_named_with_an_fn_prefix_is_still_recorded(self) -> None:
        """`(?!fn\\b)` is word-bounded, so `fn_table` is not `fn`."""
        entries = symbols_of("pub const fn_table: u8 = 1;\n")
        assert names_by_kind(entries, "const") == {"fn_table"}


class TestTypeExtraction:
    def test_all_type_kinds_are_recorded(self) -> None:
        entries = symbols_of(
            "pub struct Alpha { }\n"
            "pub enum Beta { }\n"
            "pub type Gamma = u8;\n"
            "pub trait Delta { }\n"
            "pub static EPSILON: u8 = 1;\n"
        )
        assert names_by_kind(entries, "struct") == {"Alpha"}
        assert names_by_kind(entries, "enum") == {"Beta"}
        assert names_by_kind(entries, "type") == {"Gamma"}
        assert names_by_kind(entries, "trait") == {"Delta"}
        assert names_by_kind(entries, "static") == {"EPSILON"}

    def test_modules_are_recorded(self) -> None:
        entries = symbols_of("pub mod path_core;\n")
        assert names_by_kind(entries, "module") == {"path_core"}

    def test_private_items_are_ignored(self) -> None:
        entries = symbols_of("fn hidden() { }\nstruct Hidden { }\nconst X: u8 = 1;\n")
        assert entries == []

    def test_function_arity_counts_top_level_params(self) -> None:
        entries = symbols_of("pub fn f(a: HashMap<String, Vec<u8>>, b: u8) { }\n")
        fn = next(e for e in entries if e["symbol"] == "f")
        assert fn["arity"] == 2

    def test_self_counts_toward_arity(self) -> None:
        entries = symbols_of("pub fn method(&self, a: u8) { }\n")
        fn = next(e for e in entries if e["symbol"] == "method")
        assert fn["arity"] == 2


class TestSplitTopLevelItems:
    def test_nested_brackets_do_not_split(self) -> None:
        assert split_top_level_items("a: Map<K, V>, b: [u8; 2]") == [
            "a: Map<K, V>",
            "b: [u8; 2]",
        ]

    def test_empty_string_is_empty(self) -> None:
        assert split_top_level_items("") == []
        assert split_top_level_items("   ") == []

    def test_stray_commas_do_not_inflate_the_count(self) -> None:
        assert count_rust_params("a,,b") == 2

    def test_python_markers_are_not_filtered_here(self) -> None:
        """The `/` and `*` filter is Python-specific and lives in that tool."""
        assert split_top_level_items("a, /, b, *, c") == ["a", "/", "b", "*", "c"]


class TestExpandPubUseStatement:
    def test_simple_path(self) -> None:
        assert expand_pub_use_statement("foo::Bar") == [("Bar", "foo::Bar")]

    def test_brace_group(self) -> None:
        assert expand_pub_use_statement("foo::{A, B}") == [
            ("A", "foo::A"),
            ("B", "foo::B"),
        ]

    def test_alias_in_group(self) -> None:
        assert expand_pub_use_statement("foo::{A as Renamed}") == [
            ("Renamed", "foo::A")
        ]

    def test_self_in_group_reexports_the_module(self) -> None:
        assert expand_pub_use_statement("foo::bar::{self}") == [
            ("bar", "foo::bar")
        ]

    def test_empty_statement(self) -> None:
        assert expand_pub_use_statement("") == []
        assert expand_pub_use_statement("   ;") == []

    def test_line_comment_inside_a_group_is_stripped(self) -> None:
        """Comments must not be folded into the symbol name.

        This produced two real symbols literally named
        `// Permission and accessibility checks is_valid_executable_path`
        and `// Boolean convenience wrappers drive_exists`.
        """
        body = "path::{\n    // Permission and accessibility checks\n    is_valid_executable_path,\n}"
        assert expand_pub_use_statement(body) == [
            ("is_valid_executable_path", "path::is_valid_executable_path")
        ]

    def test_comment_stripping_does_not_eat_following_names(self) -> None:
        """Comments are stripped before whitespace collapse, not after.

        Stripping after the newlines were collapsed would let the `//` swallow
        every name that followed it on the joined line.
        """
        body = "path::{\n    // a comment\n    alpha,\n    beta,\n    gamma,\n}"
        assert [name for name, _ in expand_pub_use_statement(body)] == [
            "alpha",
            "beta",
            "gamma",
        ]

    def test_block_comment_is_stripped(self) -> None:
        body = "path::{ /* grouped helpers */ alpha, beta }"
        assert [name for name, _ in expand_pub_use_statement(body)] == ["alpha", "beta"]

    def test_trailing_line_comment_after_a_name_is_stripped(self) -> None:
        body = "path::{\n    alpha, // keep this one\n    beta,\n}"
        assert [name for name, _ in expand_pub_use_statement(body)] == ["alpha", "beta"]


class TestNormalizeWhitespace:
    def test_collapses_runs_and_trims(self) -> None:
        assert normalize_whitespace("  a \n\t b  ") == "a b"


class TestBuildLookup:
    def test_first_entry_wins(self) -> None:
        items = [{"symbol": "a", "n": 1}, {"symbol": "a", "n": 2}]
        assert build_lookup(items, "symbol")["a"]["n"] == 1


class TestParseRustSurface:
    def test_crate_config_is_taken_from_arguments(self, tmp_path: Path) -> None:
        """The crate list is per-binding, so it must be a parameter."""
        crate = tmp_path / "fixture" / "src"
        crate.mkdir(parents=True)
        (crate / "lib.rs").write_text("pub fn only_symbol() { }\n", encoding="utf-8")

        surface = parse_rust_surface(
            tmp_path,
            target_crates={"fixture-crate": "fixture/src/lib.rs"},
            owner_by_crate={"fixture-crate": "aux"},
        )

        assert [s["symbol"] for s in surface["symbols"]] == ["only_symbol"]
        assert surface["scope"]["target_crates"] == ["fixture-crate"]
        assert surface["symbols"][0]["owner_module"] == "aux"

    def test_missing_owner_entry_fails_loudly(self, tmp_path: Path) -> None:
        """A new crate must not silently default to the `aux` owner."""
        crate = tmp_path / "fixture" / "src"
        crate.mkdir(parents=True)
        (crate / "lib.rs").write_text("pub fn f() { }\n", encoding="utf-8")

        try:
            parse_rust_surface(
                tmp_path,
                target_crates={"fixture-crate": "fixture/src/lib.rs"},
                owner_by_crate={},
            )
        except KeyError:
            return
        raise AssertionError("expected KeyError for a crate with no owner entry")

    def test_child_modules_are_collected(self, tmp_path: Path) -> None:
        crate = tmp_path / "fixture" / "src"
        crate.mkdir(parents=True)
        (crate / "lib.rs").write_text("pub mod child;\n", encoding="utf-8")
        (crate / "child.rs").write_text("pub fn nested() { }\n", encoding="utf-8")

        collected = collect_crate_sources(tmp_path, "fixture/src/lib.rs")

        assert len(collected) == 2
        assert any("child.rs" in rel for rel, _ in collected)
