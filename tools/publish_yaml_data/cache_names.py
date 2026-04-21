"""Shared cache-basename validation for YAML publish tooling.

These helpers intentionally mirror the Rust client contract in
``classic-update-core::yaml_update`` so publish-time acceptance matches what a
Windows client can actually install into its yaml-cache directory.
"""

from __future__ import annotations

_ASCII_UPPER_TO_LOWER = str.maketrans(
    {chr(code): chr(code + 32) for code in range(ord("A"), ord("Z") + 1)}
)
_ASCII_LOWER_TO_UPPER = str.maketrans(
    {chr(code): chr(code - 32) for code in range(ord("a"), ord("z") + 1)}
)
_RESERVED_WINDOWS_DEVICE_BASENAMES = frozenset(
    {
        "CON",
        "PRN",
        "AUX",
        "NUL",
        "COM1",
        "COM2",
        "COM3",
        "COM4",
        "COM5",
        "COM6",
        "COM7",
        "COM8",
        "COM9",
        "LPT1",
        "LPT2",
        "LPT3",
        "LPT4",
        "LPT5",
        "LPT6",
        "LPT7",
        "LPT8",
        "LPT9",
    }
)


def windows_normalized_cache_file_key(name: str) -> str:
    """Mirror the client-side Windows cache-basename collision key.

    Windows treats trailing spaces/dots as insignificant during path lookup
    and compares file names case-insensitively. Keep this helper ASCII-only so
    it matches Rust's ``to_ascii_lowercase()`` exactly.
    """

    return name.rstrip(" .").translate(_ASCII_UPPER_TO_LOWER)


def is_reserved_windows_device_basename(name: str) -> bool:
    """Return whether ``name`` resolves to a Windows reserved device stem."""

    stem = name.split(".", 1)[0].rstrip(" ")
    if not stem:
        return False
    upper = stem.translate(_ASCII_LOWER_TO_UPPER)
    return upper in _RESERVED_WINDOWS_DEVICE_BASENAMES


def is_valid_cache_file_name(name: str) -> bool:
    """Return whether ``name`` is a plain installable cache basename.

    This stays string-based and host-independent on purpose: the same publish
    metadata is validated on Linux CI and then consumed by Windows clients.
    Rejecting separators/ADS characters here also rejects rooted, drive, and
    multi-component path forms without depending on host ``Path`` semantics.
    """

    if not name or name in {".", ".."}:
        return False
    if any(ch in "/\\:" or ch == "\0" for ch in name):
        return False
    if name.endswith((" ", ".")):
        return False
    if is_reserved_windows_device_basename(name):
        return False
    return True
