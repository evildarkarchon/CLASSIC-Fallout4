"""Permanent family boundaries for operations exercised through sibling packs.

These selectors never grant evidence or remove a row from the full repository
inventory. Sibling executable packs or permanent analyzers must prove each row.
"""

from __future__ import annotations

from ..coverage import SourceParityRow


def is_retained_operation(family_id: str, row: SourceParityRow) -> bool:
    """Exclude a sibling-owned operation from this family without granting credit."""
    # These exact existing carriers belong to different bridge operations;
    # a shared::GameId token read must not claim config/scanner/web execution.
    if (
        family_id == "game-identity"
        and row.rust_crate == "classic-shared-core"
        and row.obligation_id
        in {
            "parity:cxx:0f1ce653765981f0",
            "parity:cxx:17a9ae976a21c5f7",
            "parity:cxx:7aefe345782399f3",
        }
    ):
        return True
    return False
