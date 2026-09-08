"""Trusted per-family conformance migration states."""

from __future__ import annotations

from types import MappingProxyType

FAMILY_ENFORCEMENT = MappingProxyType(
    {
        "crash-log-scan-run": "blocking",
        "autoscan-report": "blocking",
        "user-settings": "blocking",
        "installed-yaml-data": "blocking",
        "crash-suspect": "blocking",
        "crashgen-settings": "blocking",
        "mod-guidance": "blocking",
        "formid-lookup": "blocking",
        "named-record": "blocking",
        "plugin-evidence": "blocking",
        "config-vocabulary": "blocking",
        "scan-run-vocabulary": "blocking",
        "config-operations": "blocking",
        "file-operations": "blocking",
        "database-operations": "blocking",
        "version-registry": "blocking",
        "scan-game": "blocking",
        "path-operations": "blocking",
        "path-normalization": "blocking",
        "message-operations": "blocking",
        "file-fingerprint": "blocking",
        "performance": "blocking",
        "update-decisions": "blocking",
        "update-services": "blocking",
        "string-operations": "blocking",
        "registry-operations": "blocking",
        "registry-game": "blocking",
        "registry-gui": "blocking",
        "registry-context": "blocking",
        "registry-keys": "blocking",
        "game-version-parse": "blocking",
        "game-version-distance": "blocking",
        "game-version-order": "blocking",
        "fallout4-identity": "blocking",
        "fallout4-paths": "blocking",
        "fallout4-metadata": "blocking",
        "version-registry-values": "blocking",
        "settings-yaml-batch": "blocking",
        "registry-paths": "blocking",
        "web-operations": "blocking",
        "resource-operations": "blocking",
        "version-operations": "blocking",
        "version-extraction": "blocking",
        "version-f4se": "blocking",
        "version-pe": "blocking",
        "version-pe-path": "blocking",
        "xse-operations": "blocking",
        "game-identity": "blocking",
        "runtime-access": "blocking",
        "settings-load": "blocking",
        "settings-yaml": "blocking",
        "settings-validation": "blocking",
        "settings-cached-docs": "blocking",
        "version-registry-details": "blocking",
    }
)


def enforcement_for_family(family_id: str) -> str:
    """Return the trusted enforcement state for one conformance family.

    Families begin in shadow unless their promotion has been reviewed and
    registered here with the corresponding CI topology ratchet.
    """

    return FAMILY_ENFORCEMENT.get(family_id, "shadow")
