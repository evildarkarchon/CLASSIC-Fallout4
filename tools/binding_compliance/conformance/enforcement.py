"""Trusted per-family conformance migration states."""

from __future__ import annotations

from types import MappingProxyType

FAMILY_ENFORCEMENT = MappingProxyType(
    {
        "crash-log-scan-run": "blocking",
    }
)


def enforcement_for_family(family_id: str) -> str:
    """Return the trusted enforcement state for one conformance family.

    Families begin in shadow unless their promotion has been reviewed and
    registered here with the corresponding CI topology ratchet.
    """

    return FAMILY_ENFORCEMENT.get(family_id, "shadow")
