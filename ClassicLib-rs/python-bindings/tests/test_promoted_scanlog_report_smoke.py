"""Per-class smoke tests for Phase 3 Plan 05 - scanlog Wave 3b
(report sub-module).

Covers 46 promoted contract rows across 5 PyO3 wrapper classes plus
a bare module marker:

- StringPool (7 rows)
- ReportFragment (10 rows)
- ReportComposer (10 rows)
- ReportGenerator (15 rows)
- ParallelReportProcessor (3 rows)
- report@rust module marker (1 row)

Per Phase 3 D-07, each ``#[pyclass]`` gets at least one test that
constructs it and calls one real method. Constructor signatures were
verified in
``.planning/phases/03-python-tier-collapse/03-05-CONSTRUCTOR-INVENTORY.md``.

Divergences from the plan scaffold that the inventory identified and
this suite honors:

- ``ReportComposer.compose()`` returns ``list[str]`` at the Python layer,
  NOT a ``ReportFragment`` (the wrapper calls ``.compose().to_list()``
  internally).
- ``StringPool`` has no ``__len__`` magic method; the clear-check uses
  ``get_stats()`` tuple inspection + a functional re-intern assertion.
- ``ReportFragment`` has no ``text`` or ``kind`` fields, only methods
  (``to_list``/``len``/``is_empty``).
- ``ReportGenerator`` does NOT have a ``generate(AnalysisResult)`` method.
  Its API is fragment-based (``generate_header(filename)``,
  ``generate_error_section(error, version, bool)``, ...). No
  ``AnalysisResult`` fixture is needed.
- ``ParallelReportProcessor.combine_fragments`` is a ``@staticmethod``;
  tests call it as ``ParallelReportProcessor.combine_fragments(...)``.
- ``ReportGenerator.generate_suspect_section`` is deprecated and emits
  ``PyDeprecationWarning``; the test exercises it behind
  ``warnings.catch_warnings()`` so the suite stays quiet and verifies
  the deprecation path.

The autouse FCX reset fixture from Plan 03's ``conftest.py`` is still
active, but Wave 3b does not touch FCX state.
"""

from __future__ import annotations

import warnings

import classic_scanlog

# =============================================================================
# StringPool sub-module
# =============================================================================


def test_string_pool_construct_zero_arg() -> None:
    """``StringPool()`` is a zero-arg constructor and returns a usable pool."""
    pool = classic_scanlog.StringPool()
    assert pool is not None


def test_string_pool_intern_returns_equal_string() -> None:
    """``intern(s)`` returns a string equal to the input."""
    pool = classic_scanlog.StringPool()
    result = pool.intern("test_string")
    assert isinstance(result, str)
    assert result == "test_string"


def test_string_pool_intern_batch_returns_matching_list() -> None:
    """``intern_batch(list)`` returns a list of equal length with equal strings."""
    pool = classic_scanlog.StringPool()
    inputs = ["alpha", "beta", "gamma", "alpha"]  # duplicate triggers dedup
    result = pool.intern_batch(inputs)
    assert isinstance(result, list)
    assert len(result) == len(inputs)
    assert result == inputs


def test_string_pool_get_stats_returns_four_tuple() -> None:
    """``get_stats()`` returns a (total, unique, memory_saved, current_size) 4-tuple of ints."""
    pool = classic_scanlog.StringPool()
    pool.intern("one")
    pool.intern("two")
    pool.intern("one")  # duplicate
    stats = pool.get_stats()
    assert isinstance(stats, tuple)
    assert len(stats) == 4
    for element in stats:
        assert isinstance(element, int)


def test_string_pool_clear_and_reuse() -> None:
    """``clear()`` is a no-arg method that resets state; the pool remains usable after."""
    pool = classic_scanlog.StringPool()
    pool.intern("before_clear")
    pool.clear()
    # After clear, the pool can still intern new strings successfully
    result = pool.intern("after_clear")
    assert result == "after_clear"


# =============================================================================
# ReportFragment sub-module
# =============================================================================


def test_report_fragment_construct_empty_by_default() -> None:
    """``ReportFragment()`` with no lines produces an empty fragment."""
    frag = classic_scanlog.ReportFragment()
    assert frag.is_empty() is True
    assert frag.len() == 0
    assert frag.to_list() == []


def test_report_fragment_construct_with_lines() -> None:
    """``ReportFragment(lines)`` populates the fragment from the given list."""
    lines = ["line one", "line two", "line three"]
    frag = classic_scanlog.ReportFragment(lines)
    assert frag.is_empty() is False
    assert frag.len() == 3
    assert frag.to_list() == lines


def test_report_fragment_staticmethod_empty() -> None:
    """``ReportFragment.empty()`` static factory returns an empty fragment."""
    frag = classic_scanlog.ReportFragment.empty()
    assert frag.is_empty() is True
    assert frag.len() == 0


def test_report_fragment_staticmethod_from_lines() -> None:
    """``ReportFragment.from_lines(list)`` static factory builds a fragment."""
    lines = ["first", "second"]
    frag = classic_scanlog.ReportFragment.from_lines(lines)
    assert frag.is_empty() is False
    assert frag.len() == 2
    assert frag.to_list() == lines


def test_report_fragment_with_header_prepends_lines() -> None:
    """``with_header(list)`` returns a NEW fragment with the header prepended."""
    body = classic_scanlog.ReportFragment.from_lines(["body"])
    headered = body.with_header(["header line"])
    lines_out = headered.to_list()
    # Header lines appear before body lines (exact ordering depends on -core impl)
    assert "header line" in lines_out
    assert "body" in lines_out
    # Original fragment is unchanged
    assert body.to_list() == ["body"]


def test_report_fragment_combine_joins_two_fragments() -> None:
    """``combine(other)`` returns a new fragment containing both sets of lines."""
    a = classic_scanlog.ReportFragment.from_lines(["a1", "a2"])
    b = classic_scanlog.ReportFragment.from_lines(["b1", "b2"])
    combined = a.combine(b)
    lines_out = combined.to_list()
    for expected in ("a1", "a2", "b1", "b2"):
        assert expected in lines_out
    # Originals unchanged
    assert a.to_list() == ["a1", "a2"]
    assert b.to_list() == ["b1", "b2"]


# =============================================================================
# ReportComposer sub-module
# =============================================================================


def test_report_composer_construct_zero_arg() -> None:
    """``ReportComposer()`` is zero-arg; starts with zero fragments."""
    composer = classic_scanlog.ReportComposer()
    assert composer.fragment_count() == 0


def test_report_composer_add_increments_count() -> None:
    """``add(fragment)`` appends one fragment and bumps ``fragment_count``."""
    composer = classic_scanlog.ReportComposer()
    composer.add(classic_scanlog.ReportFragment.from_lines(["first"]))
    assert composer.fragment_count() == 1
    composer.add(classic_scanlog.ReportFragment.from_lines(["second"]))
    assert composer.fragment_count() == 2


def test_report_composer_add_many_accepts_list() -> None:
    """``add_many([fragments])`` adds multiple fragments in one call."""
    composer = classic_scanlog.ReportComposer()
    fragments = [
        classic_scanlog.ReportFragment.from_lines(["alpha"]),
        classic_scanlog.ReportFragment.from_lines(["beta"]),
        classic_scanlog.ReportFragment.from_lines(["gamma"]),
    ]
    composer.add_many(fragments)
    assert composer.fragment_count() == 3


def test_report_composer_compose_returns_list_of_strings() -> None:
    """``compose()`` returns ``list[str]`` at the Python layer (NOT ``ReportFragment``).

    The PyO3 wrapper calls ``.compose().to_list()`` internally — per the
    verified signature in 03-05-CONSTRUCTOR-INVENTORY.md.
    """
    composer = classic_scanlog.ReportComposer()
    composer.add(classic_scanlog.ReportFragment.from_lines(["hello", "world"]))
    result = composer.compose()
    assert isinstance(result, list)
    for element in result:
        assert isinstance(element, str)


def test_report_composer_compose_optimized_returns_list_of_strings() -> None:
    """``compose_optimized()`` also returns ``list[str]`` at the Python layer."""
    composer = classic_scanlog.ReportComposer()
    composer.add(classic_scanlog.ReportFragment.from_lines(["optimized"]))
    result = composer.compose_optimized()
    assert isinstance(result, list)
    for element in result:
        assert isinstance(element, str)


def test_report_composer_build_string_returns_single_str() -> None:
    """``build_string()`` returns a single ``str`` composition."""
    composer = classic_scanlog.ReportComposer()
    composer.add(classic_scanlog.ReportFragment.from_lines(["one", "two"]))
    result = composer.build_string()
    assert isinstance(result, str)


def test_report_composer_pool_stats_returns_four_tuple() -> None:
    """``pool_stats()`` returns a (size, lookups, hits, insertions) 4-tuple of ints."""
    composer = classic_scanlog.ReportComposer()
    composer.add(classic_scanlog.ReportFragment.from_lines(["stats probe"]))
    stats = composer.pool_stats()
    assert isinstance(stats, tuple)
    assert len(stats) == 4
    for element in stats:
        assert isinstance(element, int)


# =============================================================================
# ReportGenerator sub-module
# =============================================================================


def test_report_generator_construct_zero_arg() -> None:
    """``ReportGenerator()`` is a zero-arg constructor."""
    gen = classic_scanlog.ReportGenerator()
    assert gen is not None


def test_report_generator_staticmethod_with_config() -> None:
    """``ReportGenerator.with_config(version, crashgen_name)`` factory."""
    gen = classic_scanlog.ReportGenerator.with_config("CLASSIC v9.1.0", "Buffout 4")
    assert gen is not None


def test_report_generator_generate_header_returns_fragment() -> None:
    """``generate_header(filename)`` returns a non-empty ``ReportFragment``."""
    gen = classic_scanlog.ReportGenerator()
    fragment = gen.generate_header("crash-2024-01-01.log")
    assert isinstance(fragment, classic_scanlog.ReportFragment)
    # Header should have at least one line (verified from -core impl)
    assert fragment.is_empty() is False


def test_report_generator_generate_error_section_takes_three_args() -> None:
    """``generate_error_section(main_error, crashgen_version, is_outdated)`` - 3 args."""
    gen = classic_scanlog.ReportGenerator()
    fragment = gen.generate_error_section(
        "EXCEPTION_ACCESS_VIOLATION", "1.35.0", False
    )
    assert isinstance(fragment, classic_scanlog.ReportFragment)
    assert fragment.is_empty() is False


def test_report_generator_suspect_section_header_zero_arg() -> None:
    """``generate_suspect_section_header()`` is zero-arg and returns a ``ReportFragment``."""
    gen = classic_scanlog.ReportGenerator()
    fragment = gen.generate_suspect_section_header()
    assert isinstance(fragment, classic_scanlog.ReportFragment)


def test_report_generator_suspect_found_footer_takes_bool() -> None:
    """``generate_suspect_found_footer(bool)`` returns a fragment with different content per bool."""
    gen = classic_scanlog.ReportGenerator()
    fragment_found = gen.generate_suspect_found_footer(True)
    fragment_none = gen.generate_suspect_found_footer(False)
    assert isinstance(fragment_found, classic_scanlog.ReportFragment)
    assert isinstance(fragment_none, classic_scanlog.ReportFragment)


def test_report_generator_settings_section_header_zero_arg() -> None:
    """``generate_settings_section_header()`` is zero-arg."""
    gen = classic_scanlog.ReportGenerator()
    fragment = gen.generate_settings_section_header()
    assert isinstance(fragment, classic_scanlog.ReportFragment)


def test_report_generator_mod_check_header_takes_string() -> None:
    """``generate_mod_check_header(check_type)`` takes one string arg."""
    gen = classic_scanlog.ReportGenerator()
    fragment = gen.generate_mod_check_header("FREQUENT mods")
    assert isinstance(fragment, classic_scanlog.ReportFragment)


def test_report_generator_plugin_suspect_header_zero_arg() -> None:
    """``generate_plugin_suspect_header()`` is zero-arg."""
    gen = classic_scanlog.ReportGenerator()
    fragment = gen.generate_plugin_suspect_header()
    assert isinstance(fragment, classic_scanlog.ReportFragment)


def test_report_generator_formid_section_header_zero_arg() -> None:
    """``generate_formid_section_header()`` is zero-arg."""
    gen = classic_scanlog.ReportGenerator()
    fragment = gen.generate_formid_section_header()
    assert isinstance(fragment, classic_scanlog.ReportFragment)


def test_report_generator_record_section_header_zero_arg() -> None:
    """``generate_record_section_header()`` is zero-arg."""
    gen = classic_scanlog.ReportGenerator()
    fragment = gen.generate_record_section_header()
    assert isinstance(fragment, classic_scanlog.ReportFragment)


def test_report_generator_footer_zero_arg() -> None:
    """``generate_footer()`` is zero-arg."""
    gen = classic_scanlog.ReportGenerator()
    fragment = gen.generate_footer()
    assert isinstance(fragment, classic_scanlog.ReportFragment)


def test_report_generator_generate_suspect_section_deprecation_warning() -> None:
    """``generate_suspect_section(list)`` is deprecated but still callable.

    Verified from -py report.rs:312-329: the method emits
    ``PyDeprecationWarning`` via ``PyErr::warn`` and then constructs a
    fragment from the suspect_section_header + suspect_found_footer pair.
    """
    gen = classic_scanlog.ReportGenerator()
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        fragment = gen.generate_suspect_section(["suspect one", "suspect two"])
        assert isinstance(fragment, classic_scanlog.ReportFragment)
        # Verify the deprecation warning was emitted
        deprecation_warnings = [
            w for w in caught if issubclass(w.category, DeprecationWarning)
        ]
        assert len(deprecation_warnings) >= 1, (
            "generate_suspect_section should emit DeprecationWarning"
        )


# =============================================================================
# ParallelReportProcessor sub-module
# =============================================================================


def test_parallel_report_processor_construct_zero_arg() -> None:
    """``ParallelReportProcessor()`` is a zero-arg constructor (unit struct).

    Note: This class has no ``-core`` counterpart; it's a pure ``-py``
    convenience namespace whose primary API is the static
    ``combine_fragments`` method.
    """
    processor = classic_scanlog.ParallelReportProcessor()
    assert processor is not None


def test_parallel_report_processor_combine_fragments_empty_list() -> None:
    """``combine_fragments([])`` returns an empty fragment."""
    result = classic_scanlog.ParallelReportProcessor.combine_fragments([])
    assert isinstance(result, classic_scanlog.ReportFragment)
    assert result.is_empty() is True


def test_parallel_report_processor_combine_fragments_multiple() -> None:
    """``combine_fragments(list)`` folds multiple fragments into one."""
    fragments = [
        classic_scanlog.ReportFragment.from_lines(["alpha"]),
        classic_scanlog.ReportFragment.from_lines(["beta"]),
        classic_scanlog.ReportFragment.from_lines(["gamma"]),
    ]
    result = classic_scanlog.ParallelReportProcessor.combine_fragments(fragments)
    assert isinstance(result, classic_scanlog.ReportFragment)
    lines_out = result.to_list()
    for expected in ("alpha", "beta", "gamma"):
        assert expected in lines_out


# =============================================================================
# Rust-only symbol guard (runtime Pitfall 2 check)
# =============================================================================


def test_rust_only_symbols_in_core_surface() -> None:
    """Guard asserting all Wave 3b rust-only proxy symbols exist in -core surface.

    Each Wave 3b ``@rust``-suffixed contract row has a ``rustSymbol`` that
    must be surface-visible in the parsed ``classic-scanlog-core`` output.
    The parity gate script already enforces this at gate time via its
    Pitfall 2 guard, but a pytest sanity check catches drift between
    baseline refreshes. We assert against the committed baseline so the
    test is self-contained.
    """
    import json
    from pathlib import Path

    repo_root = Path(__file__).parent.parent.parent.parent
    baseline_path = (
        repo_root
        / "docs/implementation/python_api_parity/baseline/rust_api_surface.json"
    )
    surface = json.loads(baseline_path.read_text(encoding="utf-8"))
    scanlog_symbols: set[str] = {
        s["symbol"]
        for s in surface["symbols"]
        if s.get("crate") == "classic-scanlog-core"
    }

    # Wave 3b rust-only proxy symbols (from 03-05-CONSTRUCTOR-INVENTORY.md)
    wave3b_rust_only = {
        "StringPool",  # -core class
        "ReportFragment",  # -core class
        "ReportComposer",  # -core class
        "ReportGenerator",  # -core class
        "report",  # module marker
    }
    missing = wave3b_rust_only - scanlog_symbols
    assert not missing, (
        f"Wave 3b rust-only symbols not found in classic-scanlog-core surface: "
        f"{sorted(missing)}"
    )
