"""Rust-only ReportFragment wrapper."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast

from ClassicLib.integration.factory import get_component

if TYPE_CHECKING:
    from classic_scanlog import ReportFragment as RustReportFragment
else:
    RustReportFragment = get_component("classic_scanlog", "ReportFragment")


class RustAcceleratedReportFragment:
    """Wrapper for Rust ReportFragment."""

    def __init__(self, lines: list[str] | tuple[str, ...] | None = None, check_content: bool = True, use_rust: bool = True) -> None:
        if not use_rust:
            raise RuntimeError("Python fallback for report fragments is no longer supported.")
        _ = check_content
        self._use_rust = True
        if lines is None:
            self._fragment = RustReportFragment.empty()
        else:
            self._fragment = RustReportFragment.from_lines(list(lines))

    @classmethod
    def empty(cls) -> RustAcceleratedReportFragment:
        instance = cls.__new__(cls)
        instance._use_rust = True
        instance._fragment = RustReportFragment.empty()
        return instance

    @classmethod
    def from_lines(cls, lines: list[str] | tuple[str, ...], check_content: bool = True) -> RustAcceleratedReportFragment:
        return cls(lines, check_content=check_content, use_rust=True)

    @classmethod
    def wrap_fragment(cls, fragment: Any, use_rust: bool) -> RustAcceleratedReportFragment:
        if not use_rust:
            raise RuntimeError("Python fallback for report fragments is no longer supported.")
        instance = cls.__new__(cls)
        instance._use_rust = True
        instance._fragment = fragment
        return instance

    def with_header(self, header_lines: list[str] | tuple[str, ...]) -> RustAcceleratedReportFragment:
        result = RustAcceleratedReportFragment.__new__(RustAcceleratedReportFragment)
        result._use_rust = True
        result._fragment = self._fragment.with_header(list(header_lines))
        return result

    def __add__(self, other: Any) -> RustAcceleratedReportFragment:
        other_fragment = other._fragment if hasattr(other, "_fragment") else other
        result = RustAcceleratedReportFragment.__new__(RustAcceleratedReportFragment)
        result._use_rust = True
        result._fragment = self._fragment.combine(other_fragment)
        return result

    def to_list(self) -> list[str]:
        return cast("list[str]", self._fragment.to_list())

    @property
    def content(self) -> tuple[str, ...]:
        return tuple(self._fragment.to_list())

    @property
    def has_content(self) -> bool:
        return not self._fragment.is_empty()

    def __len__(self) -> int:
        return cast("int", self._fragment.len())

    def __bool__(self) -> bool:
        return not self._fragment.is_empty()


__all__ = ["RustAcceleratedReportFragment"]
