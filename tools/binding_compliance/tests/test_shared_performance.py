"""Foundation metric wrappers need their own executable state-transition evidence."""

from pathlib import Path


def test_shared_performance_has_a_scoped_native_contract() -> None:
    """The Python monitor delegates to foundation metrics, not the separate perf crate."""
    from conformance.coverage import load_source_parity_rows

    root = Path(__file__).resolve().parents[3]
    rows = [
        row
        for row in load_source_parity_rows(root)
        if "shared.performance.RustPerformanceMonitor" in row.obligation_id
    ]
    assert rows
    assert all(
        row.rust_crate == "classic-shared-core"
        and row.rust_symbol == "PerformanceMetrics"
        for row in rows
    )
    from conformance.command import FAMILY_COVERAGE_POLICIES

    policy = FAMILY_COVERAGE_POLICIES["shared-performance"]
    assert all(
        any(
            predicate.covers_runtime_operation(row.runtime_operation)
            for predicate in policy.predicates
        )
        for row in rows
    )
