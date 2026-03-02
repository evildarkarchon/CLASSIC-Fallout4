"""Protocol types for the integration layer factory functions.

These Protocol classes define the structural interfaces that both Rust and
Python implementations must satisfy. They enable static type checking
(pyright) at the factory boundary without requiring inheritance.

Each Protocol matches the ACTUAL methods of the returned classes from the
corresponding factory function. Only methods that are part of the public
API (used by callers of factory functions) are included.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Protocol

if TYPE_CHECKING:
    import types
    from collections.abc import AsyncIterator, Iterator
    from pathlib import Path

    from ClassicLib.scanning.logs.reporting import ReportFragment


class LogParserProtocol(Protocol):
    """Protocol for log parser implementations (get_parser).

    RustLogParser provides these methods. Rust is required.
    """

    def find_segments(
        self,
        crash_data: list[str],
        crashgen_name: str,
        xse_acronym: str,
        game_root_name: str,
    ) -> tuple[str, str, str, dict[str, list[str]]]: ...

    def extract_section(
        self,
        crash_data: list[str],
        start_marker: str,
        end_marker: str,
    ) -> list[str] | None: ...

    def get_stats(self) -> dict[str, int]: ...

    def detect_vr_log(self, content: str) -> bool: ...


class FileIOProtocol(Protocol):
    """Protocol for file I/O implementations (get_file_io).

    Both Rust FileIOCore and Python FileIOCore provide these methods.
    """

    default_encoding: str
    default_errors: str

    async def read_file(self, path: Path | str) -> str: ...
    async def read_lines(self, path: Path | str) -> list[str]: ...
    async def stream_lines(self, path: Path | str) -> AsyncIterator[str]: ...
    def stream_lines_sync(self, path: Path | str) -> Iterator[str]: ...
    async def read_bytes(self, path: Path | str) -> bytes: ...
    async def read_file_mmap(self, path: Path | str) -> str: ...
    async def read_file_with_encoding(self, path: Path | str, encoding: str) -> str: ...
    async def write_file(self, path: Path | str, content: str) -> None: ...
    async def write_lines(self, path: Path | str, lines: list[str]) -> None: ...
    async def write_bytes(self, path: Path | str, content: bytes) -> None: ...
    async def append_file(self, path: Path | str, content: str) -> None: ...
    def read_dds_header(self, path: Path | str) -> tuple[int, int] | None: ...
    def read_dds_headers_batch(self, paths: list[Path | str]) -> dict[str, tuple[int, int] | None]: ...
    def walk_directory(self, path: Path | str, pattern: str | None = ..., max_depth: int | None = ...) -> list[str]: ...
    async def read_multiple_files(self, paths: list[Path | str]) -> dict[str, str]: ...
    async def write_multiple_files(self, files: dict[Path | str, str]) -> None: ...
    def file_exists(self, path: Path | str) -> bool: ...
    def get_file_size(self, path: Path | str) -> int: ...
    def get_file_info(self, path: Path | str) -> dict[str, Any]: ...
    async def read_crash_log(self, path: Path | str) -> list[str]: ...
    async def write_crash_report(self, path: Path | str, report_lines: list[str]) -> None: ...
    def clear_cache(self) -> None: ...


class YamlOperationsProtocol(Protocol):
    """Protocol for YAML operations (get_yaml_operations).

    The Rust classic_yaml.YamlOperations class provides YAML parsing and
    writing. Returns None when Rust is not available, so factory return
    type is YamlOperationsProtocol | None.
    """

    def parse_yaml(self, content: str) -> Any: ...
    def dump_yaml(self, data: Any) -> str: ...
    def load_yaml_file(self, path: str | Path) -> dict[str, Any]: ...


class FormIDAnalyzerProtocol(Protocol):
    """Protocol for FormID analyzer implementations (get_formid_analyzer).

    Both RustFormIDAnalyzer and PythonFormIDAnalyzer provide these methods.
    """

    def extract_formids(self, segment_callstack: list[str]) -> list[str]: ...
    def formid_match(self, formids: list[str], plugins: dict[str, str], report: Any) -> None: ...


class PluginAnalyzerProtocol(Protocol):
    """Protocol for plugin analyzer implementations (get_plugin_analyzer).

    Both RustPluginAnalyzer and PythonPluginAnalyzer provide these methods.
    """

    def check_plugin_limit(self, segment_plugins: list[str], game_version: Any = ..., version_current: Any = ...) -> tuple[bool, bool]: ...
    def plugin_match(self, segment_callstack_lower: list[str], crashlog_plugins_lower: set[str]) -> Any: ...
    def filter_ignored_plugins(self, crashlog_plugins: dict[str, str]) -> dict[str, str]: ...


class RecordScannerProtocol(Protocol):
    """Protocol for record scanner implementations (get_record_scanner).

    Both RustRecordScanner and PythonRecordScanner provide these methods.
    """

    def scan_named_records(self, segment_callstack: list[str]) -> tuple[Any, list[str]]: ...
    def extract_records(self, segment_callstack: list[str]) -> list[str]: ...
    def clear_cache(self) -> None: ...


class SuspectScannerProtocol(Protocol):
    """Protocol for suspect scanner implementations (get_suspect_scanner).

    Both RustAcceleratedSuspectScanner and PythonSuspectScanner provide
    these methods.
    """

    def suspect_scan_mainerror(self, crashlog_mainerror: str, max_warn_length: int) -> tuple[ReportFragment, bool]: ...

    def suspect_scan_stack(
        self, crashlog_mainerror: str, segment_callstack_intact: str, max_warn_length: int
    ) -> tuple[ReportFragment, bool]: ...


class SettingsValidatorProtocol(Protocol):
    """Protocol for settings validator implementations (get_settings_validator).

    Both RustAcceleratedSettingsValidator and PythonSettingsScannerFragments
    provide these methods.
    """

    def scan_buffout_achievements_setting(self, xsemodules: set[str], crashgen: dict[str, bool | int | str]) -> ReportFragment: ...

    def scan_archivelimit_setting(self, crashgen: dict[str, bool | int | str], crashgen_version: Any = ...) -> ReportFragment: ...

    def scan_buffout_looksmenu_setting(self, crashgen: dict[str, bool | int | str], xsemodules: set[str]) -> ReportFragment: ...


class GpuDetectorProtocol(Protocol):
    """Protocol for GPU detector module (get_gpu_detector).

    The factory returns the gpu_rust module itself which provides
    a module-level function.
    """

    def get_gpu_info(self, segment_system: list[str]) -> dict[str, str | None]: ...


class DatabasePoolProtocol(Protocol):
    """Protocol for database pool implementations (get_database_pool).

    Both RustAsyncDatabasePool and AsyncDatabasePool provide these methods.
    """

    async def __aenter__(self) -> Any: ...
    async def __aexit__(
        self, exc_type: type[BaseException] | None, _exc_val: BaseException | None, _exc_tb: types.TracebackType | None
    ) -> None: ...
    async def initialize(self) -> None: ...
    async def close(self) -> None: ...
    async def get_entry(self, formid: str, plugin: str) -> Any: ...


class ReportGeneratorProtocol(Protocol):
    """Protocol for report generator implementations (get_report_generator).

    Both RustAcceleratedReportGenerator and PythonReportGenerator provide
    these methods.
    """

    def generate_header(self, crashlog_filename: str, version: str = ...) -> Any: ...


class ModDetectorResult(Protocol):
    """Protocol for mod detector result dict (get_mod_detector).

    The factory returns a dict with function values, not a class instance.
    This is typed as dict[str, Any] in the factory.
    """


class OrchestratorProtocol(Protocol):
    """Protocol for orchestrator implementations (get_orchestrator).

    Phase 9: Rust Orchestrator (via ClassicOrchestrator wrapper) provides these methods.
    Python OrchestratorCore has been removed.
    """

    def process_crash_log(self, log_path: Path) -> Any: ...  # Returns AnalysisResult
    def process_crash_logs_batch(self, log_paths: list[Path], max_concurrent: int | None = None) -> Any: ...  # Returns BatchAnalysisResult
    def is_feature_complete(self) -> bool: ...


class FCXHandlerProtocol(Protocol):
    """Protocol for FCX mode handler implementations (get_fcx_handler).

    Both RustAcceleratedFcxModeHandler and PythonFCXModeHandler provide
    these methods.
    """

    fcx_mode: bool | None

    def check_fcx_mode(self) -> None: ...
    async def check_fcx_mode_async(self) -> None: ...
    def get_fcx_messages(self) -> ReportFragment: ...


__all__ = [
    "DatabasePoolProtocol",
    "FCXHandlerProtocol",
    "FileIOProtocol",
    "FormIDAnalyzerProtocol",
    "GpuDetectorProtocol",
    "LogParserProtocol",
    "OrchestratorProtocol",
    "PluginAnalyzerProtocol",
    "RecordScannerProtocol",
    "ReportGeneratorProtocol",
    "SettingsValidatorProtocol",
    "SuspectScannerProtocol",
    "YamlOperationsProtocol",
]
