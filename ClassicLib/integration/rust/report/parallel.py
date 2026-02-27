"""Rust-only parallel report processing capabilities."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from ClassicLib.integration.factory import get_component

if TYPE_CHECKING:
    from classic_scanlog import ParallelReportProcessor as RustParallelProcessor
else:
    RustParallelProcessor = get_component("classic_scanlog", "ParallelReportProcessor")


def _get_fragment_class() -> type:
    from ClassicLib.integration.rust.report.fragment import RustAcceleratedReportFragment

    return RustAcceleratedReportFragment


class ParallelReportProcessor:
    """Parallel report processing backed by Rust."""

    def __init__(self) -> None:
        self._processor = RustParallelProcessor()

    def process_reports(self, reports: list[list[str]]) -> list[list[str]]:
        return self._processor.process_batch(reports, None)

    def combine_fragments_parallel(self, fragments: list[Any]) -> Any:
        RustAcceleratedReportFragment = _get_fragment_class()
        if not fragments:
            return RustAcceleratedReportFragment.empty()

        rust_fragments = [f._fragment if hasattr(f, "_fragment") else f for f in fragments]
        result_fragment = self._processor.combine_fragments(rust_fragments)
        return RustAcceleratedReportFragment.wrap_fragment(result_fragment, use_rust=True)


__all__ = ["ParallelReportProcessor"]
