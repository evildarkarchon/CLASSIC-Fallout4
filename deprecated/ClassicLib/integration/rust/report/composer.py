"""Rust-only ReportComposer wrapper."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast

from ClassicLib.integration.factory import get_component

if TYPE_CHECKING:
    from classic_scanlog import ReportComposer as RustReportComposer
    from classic_scanlog import ReportFragment as RustReportFragment
else:
    RustReportComposer = get_component("classic_scanlog", "ReportComposer")
    RustReportFragment = get_component("classic_scanlog", "ReportFragment")


def _get_fragment_class() -> type:
    from ClassicLib.integration.rust.report.fragment import RustAcceleratedReportFragment

    return RustAcceleratedReportFragment


class RustAcceleratedReportComposer:
    """Wrapper for Rust ReportComposer."""

    def __init__(self, _parallel_threshold: int = 10) -> None:
        _ = _parallel_threshold
        self._use_rust = True
        self._composer = RustReportComposer()

    def add(self, fragment: Any) -> RustAcceleratedReportComposer:
        if hasattr(fragment, "_fragment"):
            rust_fragment = fragment._fragment
        elif hasattr(fragment, "to_list"):
            rust_fragment = RustReportFragment.from_lines(list(fragment.to_list()))
        else:
            rust_fragment = fragment
        self._composer.add(rust_fragment)
        return self

    def compose(self) -> Any:
        RustAcceleratedReportFragment = _get_fragment_class()
        lines = cast("list[str]", self._composer.compose_optimized())
        fragment = RustReportFragment.from_lines(lines)
        return RustAcceleratedReportFragment.wrap_fragment(fragment, use_rust=True)

    def build(self) -> Any:
        return self.compose()

    def to_list(self) -> list[str]:
        return cast("list[str]", self._composer.compose_optimized())

    def build_string(self) -> str:
        return cast("str", self._composer.build_string())

    @property
    def pool_stats(self) -> tuple[int, int, int, int] | None:
        return cast("tuple[int, int, int, int]", self._composer.pool_stats())


__all__ = ["RustAcceleratedReportComposer"]
