"""Smoke tests for the app-notification PyO3 surface.

Verifies that ``check_app_notification`` + its DTO pyclasses +
exception hierarchy are reachable from Python after the
``classic_update`` extension is built. Network-dependent assertions
are tolerant — a fully-offline test runner is allowed to see the
check raise ``ClassicNotificationFetchFailed`` without failing the
test suite.
"""

from __future__ import annotations

import pytest


classic_update = pytest.importorskip(
    "classic_update",
    reason="classic_update extension not built; run `maturin develop` first",
)


def test_notification_dtos_and_function_exported() -> None:
    """All public names land on the `classic_update` module namespace."""
    assert hasattr(classic_update, "check_app_notification")
    assert hasattr(classic_update, "NotificationStatus")
    assert hasattr(classic_update, "AppNotificationDisplay")


def test_exception_hierarchy_is_exported_and_well_formed() -> None:
    """ClassicNotificationError subclasses ClassicUpdateError, and each
    variant-specific subclass is a ClassicNotificationError.
    """
    base = classic_update.ClassicUpdateError
    notif = classic_update.ClassicNotificationError
    fetch_failed = classic_update.ClassicNotificationFetchFailed
    decode = classic_update.ClassicNotificationDecodeError
    parse = classic_update.ClassicNotificationInstalledVersionParseError
    cache_io = classic_update.ClassicNotificationCacheIoError

    # Base chain.
    assert issubclass(base, Exception)
    assert issubclass(notif, base)

    # Each variant subclasses ClassicNotificationError...
    for variant in (fetch_failed, decode, parse, cache_io):
        assert issubclass(variant, notif)
        # ...and therefore also ClassicUpdateError, so a consumer
        # catching the base class catches everything.
        assert issubclass(variant, base)


def test_check_app_notification_rejects_unparseable_installed_version() -> None:
    """Unparseable ``installed_version`` must deterministically raise
    :class:`ClassicNotificationInstalledVersionParseError` before any
    network or cache I/O runs.

    The orchestrator validates caller input eagerly so this branch is
    independent of whether the test runner can reach GitHub — both the
    online and fully-offline runs take the same path. The previously
    loose assertion (either ``classification == "unknown"`` *or* any
    :class:`ClassicNotificationError`) left the typed variant
    unreachable in practice and masked the review finding that the
    binding contract advertised a surface the core never emitted.
    """
    with pytest.raises(
        classic_update.ClassicNotificationInstalledVersionParseError
    ) as excinfo:
        classic_update.check_app_notification(
            owner="nonexistent-owner-xyzzy",
            repo="nonexistent-repo-xyzzy",
            installed_version="not-a-semver",
        )

    # The Display rendering carries the offending input so consumers
    # can show the user *which* string failed.
    assert "not-a-semver" in str(excinfo.value)


def test_installed_version_parse_error_is_subclass_of_notification_base() -> None:
    """Consumers that catch :class:`ClassicNotificationError` (or the
    broader :class:`ClassicUpdateError`) must still catch the typed
    parse-error variant. This locks the exception hierarchy against
    a later refactor that hoists the variant out of the notification
    subtree.
    """
    with pytest.raises(classic_update.ClassicNotificationError):
        classic_update.check_app_notification(
            owner="nonexistent-owner-xyzzy",
            repo="nonexistent-repo-xyzzy",
            installed_version="not-a-semver",
        )
    with pytest.raises(classic_update.ClassicUpdateError):
        classic_update.check_app_notification(
            owner="nonexistent-owner-xyzzy",
            repo="nonexistent-repo-xyzzy",
            installed_version="not-a-semver",
        )
