"""Python module for CLASSIC update checking.

This module provides Rust-accelerated update checking with:
- GitHub API integration for release monitoring
- Version comparison and change detection

Core Classes:
    GithubClient: Client for GitHub API access
    GithubRelease: GitHub release information
    GithubAsset: GitHub release asset (downloadable file)

Example:
    >>> import classic_update
    >>> import asyncio
    >>>
    >>> async def check_updates():
    ...     # Check GitHub
    ...     github = classic_update.GithubClient("evildarkarchon", "CLASSIC-Fallout4")
    ...     latest = await github.get_latest_release()
    ...     if github.has_update("v8.0.0", latest.tag_name):
    ...         print(f"Update to {latest.tag_name} available!")
    >>>
    >>> asyncio.run(check_updates())
"""

# Direct-import facade over the one CLASSIC native extension. Every name is
# the canonical native object, so values and exceptions created through any
# facade are the same Python types everywhere. Keep the import list and the
# literal ``__all__`` in step with ``__init__.pyi``: validate_stubs.py and the
# Python parity resolver read both.

from _classic_native._native.classic_update import (
    AppNotificationDisplay,
    ApprovedUpdate,
    ClassicNotificationCacheIoError,
    ClassicNotificationDecodeError,
    ClassicNotificationError,
    ClassicNotificationFetchFailed,
    ClassicNotificationInstalledVersionParseError,
    ClassicUpdateError,
    GithubAsset,
    GithubClient,
    GithubRelease,
    NotificationStatus,
    YamlApplyRequest,
    YamlClientSchemaEntry,
    YamlRejectedFile,
    YamlRollbackOutcome,
    YamlUpdateFile,
    YamlUpdateFileOutcome,
    YamlUpdateReport,
    YamlUpdateStatus,
    __debug_registered__,
    __version__,
    apply_yaml_update,
    check_app_notification,
    check_app_notification_configured,
    check_yaml_update,
    rollback_yaml_update,
)

__all__ = [
    "AppNotificationDisplay",
    "ApprovedUpdate",
    "ClassicNotificationCacheIoError",
    "ClassicNotificationDecodeError",
    "ClassicNotificationError",
    "ClassicNotificationFetchFailed",
    "ClassicNotificationInstalledVersionParseError",
    "ClassicUpdateError",
    "GithubAsset",
    "GithubClient",
    "GithubRelease",
    "NotificationStatus",
    "YamlApplyRequest",
    "YamlClientSchemaEntry",
    "YamlRejectedFile",
    "YamlRollbackOutcome",
    "YamlUpdateFile",
    "YamlUpdateFileOutcome",
    "YamlUpdateReport",
    "YamlUpdateStatus",
    "__debug_registered__",
    "__version__",
    "apply_yaml_update",
    "check_app_notification",
    "check_app_notification_configured",
    "check_yaml_update",
    "rollback_yaml_update",
]
