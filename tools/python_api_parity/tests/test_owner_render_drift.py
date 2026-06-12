"""LOW drift guard: _OWNER_RENDER_ORDER must derive from RUST_OWNER_BY_CRATE + aux, not a hard-coded tuple."""
from __future__ import annotations

# sys.path bootstrap handled by conftest.py
from generate_baseline import (  # noqa: E402
    RUST_OWNER_BY_CRATE,
    _OWNER_RENDER_ORDER,
)


def test_owner_render_order_matches_rust_owner_by_crate_values() -> None:
    """The rendering order must be a superset of owners derived from RUST_OWNER_BY_CRATE.

    Hard-coding the tuple (as at line 682 originally) invites drift when
    RUST_OWNER_BY_CRATE grows. This test enforces: every key in
    RUST_OWNER_BY_CRATE.values() must appear in _OWNER_RENDER_ORDER, plus
    the special 'aux' label for the file_io aux entry.
    """
    expected_owners = set(RUST_OWNER_BY_CRATE.values()) | {"aux"}
    actual_owners = set(_OWNER_RENDER_ORDER)
    missing = expected_owners - actual_owners
    extra = actual_owners - expected_owners
    assert not missing, f"_OWNER_RENDER_ORDER is missing owners: {missing}"
    # Extras are allowed if intentional, but flag them for review:
    assert not extra, (
        f"_OWNER_RENDER_ORDER has extra owners not in RUST_OWNER_BY_CRATE: {extra}"
    )
