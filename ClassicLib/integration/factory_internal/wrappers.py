"""Factory wrapper adapters that normalize Rust API shapes."""

from __future__ import annotations

from typing import Any

from ClassicLib.integration.factory_internal.report_fragment import get_report_fragment_type


class SuspectScannerWrapper:
    """Convert Rust SuspectScanner outputs to ReportFragment."""

    def __init__(self, rust_scanner: Any) -> None:
        self._scanner = rust_scanner

    def suspect_scan_mainerror(self, crashlog_mainerror: str, max_warn_length: int) -> tuple[Any, bool]:
        report_fragment_type = get_report_fragment_type()
        rust_result = self._scanner.suspect_scan_mainerror(crashlog_mainerror, max_warn_length)
        return report_fragment_type.from_lines(rust_result[0]), rust_result[1]

    def suspect_scan_stack(self, crashlog_mainerror: str, segment_callstack_intact: str, max_warn_length: int) -> tuple[Any, bool]:
        report_fragment_type = get_report_fragment_type()
        rust_result = self._scanner.suspect_scan_stack(crashlog_mainerror, segment_callstack_intact, max_warn_length)
        return report_fragment_type.from_lines(rust_result[0]), rust_result[1]

    @staticmethod
    def check_dll_crash(crashlog_mainerror: str) -> Any:
        from classic_scanlog import SuspectScanner as RustSuspectScanner

        report_fragment_type = get_report_fragment_type()
        rust_result = RustSuspectScanner.check_dll_crash(crashlog_mainerror)
        return report_fragment_type.from_lines(rust_result)


class SettingsValidatorWrapper:
    """Convert between Python and Rust SettingsValidator APIs."""

    def __init__(self, rust_validator: Any) -> None:
        self._validator = rust_validator

    @staticmethod
    def _convert_crashgen(crashgen: dict[str, bool | int | str]) -> dict[str, str]:
        return {k: str(v).lower() if isinstance(v, bool) else str(v) for k, v in crashgen.items()}

    def scan_buffout_achievements_setting(self, xsemodules: set[str], crashgen: dict[str, bool | int | str]) -> Any:
        report_fragment_type = get_report_fragment_type()
        lines = self._validator.scan_buffout_achievements_setting(xsemodules, SettingsValidatorWrapper._convert_crashgen(crashgen))
        return report_fragment_type.from_lines(lines)

    def scan_buffout_memorymanagement_settings(
        self,
        crashgen: dict[str, bool | int | str],
        has_xcell: bool,
        has_old_xcell: bool,
        has_baka_scrapheap: bool,
    ) -> Any:
        report_fragment_type = get_report_fragment_type()
        lines = self._validator.scan_buffout_memorymanagement_settings(
            SettingsValidatorWrapper._convert_crashgen(crashgen), has_xcell, has_old_xcell, has_baka_scrapheap
        )
        return report_fragment_type.from_lines(lines)

    def scan_archivelimit_setting(self, crashgen: dict[str, bool | int | str], crashgen_version: Any = None) -> Any:
        report_fragment_type = get_report_fragment_type()
        lines = self._validator.scan_archivelimit_setting(SettingsValidatorWrapper._convert_crashgen(crashgen), crashgen_version)
        return report_fragment_type.from_lines(lines)

    def scan_buffout_looksmenu_setting(self, crashgen: dict[str, bool | int | str], xsemodules: set[str]) -> Any:
        report_fragment_type = get_report_fragment_type()
        lines = self._validator.scan_buffout_looksmenu_setting(SettingsValidatorWrapper._convert_crashgen(crashgen), xsemodules)
        return report_fragment_type.from_lines(lines)


class FcxHandlerWrapper:
    """Convert Rust FcxModeHandler API to Python-facing API."""

    def __init__(self, rust_handler: Any, fcx_mode: bool | None) -> None:
        self._handler = rust_handler
        self.fcx_mode = fcx_mode
        self.game_files_check: str | None = None
        self.main_files_check: str | None = None

    def check_fcx_mode(self) -> None:
        self._handler.check_fcx_mode()

    def get_fcx_messages(self) -> Any:
        report_fragment_type = get_report_fragment_type()
        lines = self._handler.get_fcx_messages()
        return report_fragment_type.from_lines(lines)

    @classmethod
    def reset_fcx_checks(cls) -> None:
        pass
