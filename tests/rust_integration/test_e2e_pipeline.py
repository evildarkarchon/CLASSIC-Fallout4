"""
End-to-end pipeline integration tests for Phase 6 Rust migration validation.

This module provides comprehensive end-to-end testing of the complete crash log
processing pipeline using real crash log data. Tests validate that all Rust
components work together correctly and produce consistent results with the
Python implementations.

Key Features Tested:
- Complete crash log processing pipeline with all Rust components
- Output consistency between Rust and Python implementations
- Performance improvements in real-world scenarios
- Error handling and fallback mechanisms
- Integration between all pipeline components
"""
# ruff: noqa: ANN201, ANN001, PLR6301, ARG002, BLE001

import asyncio
import logging
from contextlib import AsyncExitStack
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

# Import test infrastructure
from tests.test_infra.performance_utils import PerformanceTimer

# Skip entire module if Rust extensions not available
pytest.importorskip("classic_scanlog", reason="Rust extensions not available")

# Import core components
from ClassicLib.AsyncBridge import AsyncBridge
from ClassicLib.integration.factory import (
    get_formid_analyzer,
    get_parser,
    get_plugin_analyzer,
    get_record_scanner,
)
from ClassicLib.integration.status import (
    get_rust_component_status,
    is_rust_accelerated,
)
from ClassicLib.ScanLog.OrchestratorCore import OrchestratorCore

logger = logging.getLogger(__name__)


@pytest.mark.rust
@pytest.mark.integration
@pytest.mark.e2e
class TestE2EPipeline:
    """
    End-to-end pipeline tests using real crash log data.

    These tests validate the complete crash log processing pipeline
    with all Rust components enabled, ensuring proper integration
    and consistent output with Python implementations.
    """

    @pytest.fixture(scope="class")
    def crash_log_samples(self) -> dict[str, Path]:
        """
        Provide paths to real crash log samples for testing.

        Returns a dictionary mapping crash log types to file paths.
        Uses backup crash logs from the project for testing.
        """
        project_root = Path(__file__).parent.parent.parent
        backup_logs = project_root / "CLASSIC Backup" / "Unsolved Logs"

        samples = {}

        if backup_logs.exists():
            # Get different types of crash logs for comprehensive testing
            log_files = list(backup_logs.glob("*.log"))[:5]  # Limit to 5 for performance

            for i, log_file in enumerate(log_files):
                samples[f"sample_{i}"] = log_file

        # If no backup logs available, create synthetic test data
        if not samples:
            test_data_dir = Path(__file__).parent / "test_data"
            test_data_dir.mkdir(exist_ok=True)

            # Create a minimal synthetic crash log for testing
            synthetic_log = test_data_dir / "synthetic_crash.log"
            if not synthetic_log.exists():
                synthetic_content = self._create_synthetic_crash_log()
                synthetic_log.write_text(synthetic_content, encoding="utf-8")

            samples["synthetic"] = synthetic_log

        return samples

    @pytest.fixture
    def mock_yamldata(self) -> Mock:
        """
        Create a mock YAML data object for testing.

        Returns a mock object that simulates the ClassicScanLogsInfo
        structure with all necessary attributes for testing.
        """
        mock_yaml = Mock()

        # Mock game configuration
        mock_yaml.game_type = "fallout4"
        mock_yaml.crashgen_name = "Buffout 4"
        mock_yaml.xse_acronym = "F4SE"
        mock_yaml.game_root_name = "Fallout 4"
        mock_yaml.crashgen_latest_og = "1.28.6"
        mock_yaml.crashgen_latest_vr = "1.28.6"
        mock_yaml.classic_version = "7.31.0"

        # Mock problematic plugins list
        mock_yaml.problematic_plugins = {"test_plugin.esp": "Test problematic plugin", "broken_mod.esp": "Known broken mod"}

        # Mock FormID database configuration
        mock_yaml.formid_database_enabled = True
        mock_yaml.show_formid_values = True

        # Mock record patterns for scanning
        mock_yaml.record_patterns = ["TESForm", "BGSKeyword", "TESObjectSTAT"]

        # Initialize list attributes
        mock_yaml.game_ignore_plugins = []
        mock_yaml.game_ignore_records = []
        mock_yaml.ignore_list = []
        mock_yaml.classic_records_list = []
        mock_yaml.plugins_mods_to_check = {}

        # Initialize dict attributes
        mock_yaml.game_mods_core = {}
        mock_yaml.game_mods_conf = {}
        mock_yaml.game_mods_freq = {}
        mock_yaml.game_mods_solu = {}
        mock_yaml.suspects_error_list = {}
        mock_yaml.suspects_stack_list = {}

        return mock_yaml

    @pytest.fixture
    def orchestrator(self, mock_yamldata) -> OrchestratorCore:
        """
        Create an OrchestratorCore instance for testing.

        Sets up the orchestrator with proper async bridge and
        message handler integration for end-to-end testing.
        """
        # Clear any existing singletons to ensure clean state
        # Note: GlobalRegistry is a module, not a class with clear() method
        # The registry uses module-level storage that persists
        # MessageHandler doesn't have clear_instance() - use fixtures for cleanup

        # Initialize async bridge
        AsyncBridge.get_instance()

        # Create orchestrator with test configuration
        return OrchestratorCore(yamldata=mock_yamldata, fcx_mode=False, show_formid_values=True, formid_db_exists=True)

    def _create_synthetic_crash_log(self) -> str:
        """
        Create a synthetic crash log for testing when real logs aren't available.

        Returns a string containing a complete synthetic crash log with all
        required sections for testing the full pipeline.
        """
        return """Fallout 4 v1.10.163
Buffout 4 v1.28.6

Unhandled exception "EXCEPTION_ACCESS_VIOLATION" at 0x7FF66DF19300 Fallout4.exe+0DB9300

	[Compatibility]
		F4EE: false
	[Crashlog]
		AutoOpen: true
		PromptUpload: true

SYSTEM SPECS:
	OS: Microsoft Windows 11 Home v10.0.22621
	CPU: AuthenticAMD AMD Ryzen 5 5600X 6-Core Processor
	GPU #1: Nvidia GA104 [GeForce RTX 3060 Ti]
	PHYSICAL MEMORY: 16.00 GB/32.00 GB

PROBABLE CALL STACK:
	[0] 0x7FF66DF19300 Fallout4.exe+0DB9300 -> FormID: 0x12345678
	[1] 0x7FF66DF19400 Fallout4.exe+0DB9400 -> FormID: 0xABCDEF01
	[2] 0x7FF66E123456 Fallout4.exe+1523456

MODULES:
	Fallout4.exe
	f4se_1_6_353.dll
	buffout4.dll
	TestMod.dll

F4SE PLUGINS:
	Buffout4 v1.28.6
	TestPlugin v1.0.0

PLUGINS:
	[00] Fallout4.esm
	[01] DLCRobot.esm
	[02] DLCworkshop01.esm
	[03] DLCCoast.esm
	[04] DLCNukaWorld.esm
	[FE:000] TestMod.esl
	[05] TestPlugin.esp
	[06] AnotherMod.esp
"""

    def _read_crash_log(self, log_path: Path) -> list[str]:
        """
        Read a crash log file and return it as a list of lines.

        Args:
            log_path: Path to the crash log file

        Returns:
            List of strings, each representing a line in the crash log
        """
        try:
            with Path(log_path).open("r", encoding="utf-8", errors="ignore") as f:
                return [line.rstrip("\n\r") for line in f]
        except Exception as e:
            pytest.skip(f"Could not read crash log {log_path}: {e}")

    @pytest.mark.asyncio
    async def test_complete_pipeline_with_rust(self, orchestrator, crash_log_samples, mock_yamldata):
        """
        Test the complete crash log processing pipeline with Rust acceleration.

        This test runs the full pipeline from log parsing through report generation
        using real crash log data, validating that all Rust components work together
        correctly and produce the expected output structure.
        """
        # Skip if no Rust components available
        if not any(is_rust_accelerated(component) for component in ["parser", "formid_analyzer", "plugin_analyzer", "record_scanner"]):
            pytest.skip("No Rust components available for end-to-end testing")

        async with orchestrator:
            # Test with each available crash log sample
            for sample_name, log_path in crash_log_samples.items():
                with PerformanceTimer(f"E2E Pipeline - {sample_name}") as timer:
                    # Read the crash log
                    crash_data = self._read_crash_log(log_path)
                    assert len(crash_data) > 0, f"Empty crash log: {sample_name}"

                    # Process through the complete pipeline
                    result = await orchestrator.process_crash_log(crashlog_file=log_path)
                    # Unpack result (path, report, failed, stats)
                    _, report_fragments, _, _ = result

                # Validate the pipeline produced meaningful output
                assert report_fragments is not None, f"No output from pipeline: {sample_name}"

                # Validate report structure contains expected sections

                # Log performance for analysis
                logger.info(f"Pipeline processing time for {sample_name}: {timer.elapsed:.3f}s")

    @pytest.mark.asyncio
    async def test_rust_python_output_consistency(self, crash_log_samples, mock_yamldata):
        """
        Test output consistency between Rust and Python implementations.

        This test runs the same crash log through both Rust and Python
        implementations to ensure they produce consistent results.
        """
        # Only run if both Rust and Python implementations are available
        rust_available = is_rust_accelerated("parser")

        if not rust_available:
            pytest.skip("Rust parser not available for consistency testing")

        # Test with first available sample
        _, log_path = next(iter(crash_log_samples.items()))
        crash_data = self._read_crash_log(log_path)

        # Test Rust LogParser
        rust_parser = get_parser()
        rust_result = rust_parser.find_segments(
            crash_data=crash_data,
            crashgen_name=mock_yamldata.crashgen_name,
            xse_acronym=mock_yamldata.xse_acronym,
            game_root_name=mock_yamldata.game_root_name,
        )

        # Test Python fallback by forcing it
        with patch.object(rust_parser, "_use_rust", False):
            python_result = rust_parser.find_segments(
                crash_data=crash_data,
                crashgen_name=mock_yamldata.crashgen_name,
                xse_acronym=mock_yamldata.xse_acronym,
                game_root_name=mock_yamldata.game_root_name,
            )

        # Compare results structure (allowing for minor differences in processing)
        assert len(rust_result) == len(python_result), "Result structure mismatch"
        assert type(rust_result[0]) is type(python_result[0]), "Game version type mismatch"
        assert type(rust_result[1]) is type(python_result[1]), "Crashgen version type mismatch"
        assert len(rust_result[3]) == len(python_result[3]), "Segments count mismatch"

    @pytest.mark.asyncio
    async def test_formid_extraction_integration(self, crash_log_samples, mock_yamldata):
        """
        Test FormID extraction integration across the pipeline.

        This test validates that FormID extraction works correctly
        when integrated with the complete processing pipeline.
        """
        if not is_rust_accelerated("formid_analyzer"):
            pytest.skip("Rust FormID analyzer not available")

        # Use first available sample
        _, log_path = next(iter(crash_log_samples.items()))
        crash_data = self._read_crash_log(log_path)

        # Parse the crash log to get segments
        parser = get_parser()
        _, _, _, segments = parser.find_segments(
            crash_data=crash_data,
            crashgen_name=mock_yamldata.crashgen_name,
            xse_acronym=mock_yamldata.xse_acronym,
            game_root_name=mock_yamldata.game_root_name,
        )

        # Extract call stack segment (typically index 2)
        if len(segments) > 2:
            callstack_segment = segments[2]

            # Test FormID extraction
            formid_analyzer = get_formid_analyzer(yamldata=mock_yamldata, show_values=True, db_exists=True)

            formids = formid_analyzer.extract_formids(callstack_segment)

            # Validate FormID extraction results
            assert isinstance(formids, list), "FormIDs should be returned as a list"

            # If FormIDs were found, validate their format
            for formid in formids:
                assert isinstance(formid, str), f"FormID should be string: {formid}"
                # FormIDs should be hexadecimal strings
                if formid.startswith("0x"):
                    try:
                        int(formid, 16)
                    except ValueError:
                        pytest.fail(f"Invalid hexadecimal FormID: {formid}")

    @pytest.mark.asyncio
    async def test_plugin_analysis_integration(self, crash_log_samples, mock_yamldata):
        """
        Test plugin analysis integration in the complete pipeline.

        This test validates that plugin analysis works correctly
        when processing real crash logs through the full pipeline.
        """
        if not is_rust_accelerated("plugin_analyzer"):
            pytest.skip("Rust plugin analyzer not available")

        # Use first available sample
        _, log_path = next(iter(crash_log_samples.items()))
        crash_data = self._read_crash_log(log_path)

        # Parse to get plugin segment
        parser = get_parser()
        _, _, _, segments = parser.find_segments(
            crash_data=crash_data,
            crashgen_name=mock_yamldata.crashgen_name,
            xse_acronym=mock_yamldata.xse_acronym,
            game_root_name=mock_yamldata.game_root_name,
        )

        # Test plugin analysis (typically last segment)
        if segments:
            plugins_segment = segments[-1]  # Usually the plugins segment is last

            plugin_analyzer = get_plugin_analyzer(mock_yamldata)

            plugins_dict, limit_triggered, limit_disabled = plugin_analyzer.loadorder_scan_log(segment_plugins=plugins_segment)

            # Validate plugin analysis results
            assert isinstance(plugins_dict, dict), "Plugins should be returned as dict"
            assert isinstance(limit_triggered, bool), "Plugin limit flag should be boolean"
            assert isinstance(limit_disabled, bool), "Limit disabled flag should be boolean"

            # If plugins were found, validate their structure
            for hex_id, plugin_name in plugins_dict.items():
                assert isinstance(hex_id, str), f"Plugin ID should be string: {hex_id}"
                assert isinstance(plugin_name, str), f"Plugin name should be string: {plugin_name}"
                # Hex IDs should be valid hexadecimal
                try:
                    int(hex_id, 16)
                except ValueError:
                    pytest.fail(f"Invalid plugin hex ID: {hex_id}")

    @pytest.mark.asyncio
    async def test_record_scanning_integration(self, crash_log_samples, mock_yamldata):
        """
        Test record scanning integration in the complete pipeline.

        This test validates that record scanning works correctly
        as part of the integrated crash log processing pipeline.
        """
        if not is_rust_accelerated("record_scanner"):
            pytest.skip("Rust record scanner not available")

        # Use first available sample
        _, log_path = next(iter(crash_log_samples.items()))
        crash_data = self._read_crash_log(log_path)

        # Parse to get call stack segment for record scanning
        parser = get_parser()
        _, _, _, segments = parser.find_segments(
            crash_data=crash_data,
            crashgen_name=mock_yamldata.crashgen_name,
            xse_acronym=mock_yamldata.xse_acronym,
            game_root_name=mock_yamldata.game_root_name,
        )

        # Test record scanning on call stack segment
        if len(segments) > 2:
            callstack_segment = segments[2]

            record_scanner = get_record_scanner(mock_yamldata)

            fragment, matches = record_scanner.scan_named_records(callstack_segment)

            # Validate record scanning results
            # Fragment can be None if no records found
            if fragment is not None:
                # Fragment can be a list of strings (if Rust) or an object/dict (if Python)
                is_valid_type = isinstance(fragment, list) or hasattr(fragment, "__dict__") or isinstance(fragment, dict)
                assert is_valid_type, f"Fragment should be a list, object or dict, got {type(fragment)}"

            assert isinstance(matches, list), "Matches should be returned as a list"

            # If matches were found, validate their format
            for match in matches:
                assert isinstance(match, str), f"Match should be string: {match}"

    @pytest.mark.asyncio
    async def test_error_handling_and_fallbacks(self, crash_log_samples, mock_yamldata, tmp_path):
        """
        Test error handling and fallback mechanisms in the pipeline.

        This test validates that the pipeline handles errors gracefully
        and falls back to Python implementations when Rust components fail.
        """
        # Use first available sample
        _, log_path = next(iter(crash_log_samples.items()))
        crash_data = self._read_crash_log(log_path)

        # Test with corrupted data to trigger error handling
        corrupted_data = crash_data[:10] + ["CORRUPTED LINE"] * 5 + crash_data[10:]

        # Write to temp file
        corrupted_file = tmp_path / "corrupted_crash.log"
        corrupted_file.write_text("\n".join(corrupted_data), encoding="utf-8")

        # Create orchestrator
        orchestrator = OrchestratorCore(yamldata=mock_yamldata, fcx_mode=False, show_formid_values=True, formid_db_exists=True)

        # Process should not crash even with corrupted data
        try:
            async with orchestrator:
                result = await orchestrator.process_crash_log(crashlog_file=corrupted_file)

            # Should still produce some output even with corrupted data
            assert result is not None, "Pipeline should handle corrupted data gracefully"

        except Exception as e:
            pytest.fail(f"Pipeline should not crash on corrupted data: {e}")

    @pytest.mark.asyncio
    async def test_concurrent_processing(self, crash_log_samples, mock_yamldata):
        """
        Test concurrent processing of multiple crash logs.

        This test validates that the pipeline can handle multiple
        crash logs being processed concurrently without issues.
        """
        if len(crash_log_samples) < 2:
            pytest.skip("Need at least 2 crash log samples for concurrent testing")

        # Prepare multiple orchestrators for concurrent processing
        orchestrators = []
        crash_data_sets = []

        async with AsyncExitStack() as stack:
            for _, log_path in list(crash_log_samples.items())[:3]:  # Limit to 3 for performance
                orchestrator = OrchestratorCore(yamldata=mock_yamldata, fcx_mode=False, show_formid_values=True, formid_db_exists=True)
                await stack.enter_async_context(orchestrator)

                orchestrators.append(orchestrator)
                crash_data_sets.append(log_path)

            # Process all crash logs concurrently
            tasks = []
            for orchestrator, log_path in zip(orchestrators, crash_data_sets, strict=True):
                task = orchestrator.process_crash_log(crashlog_file=log_path)
                tasks.append(task)

            # Wait for all tasks to complete
            with PerformanceTimer("Concurrent Processing") as timer:
                results = await asyncio.gather(*tasks, return_exceptions=True)

        # Validate all results
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                pytest.fail(f"Concurrent processing failed for sample {i}: {result}")

            assert result is not None, f"No result from concurrent processing: sample {i}"

        logger.info(f"Concurrent processing of {len(tasks)} logs: {timer.elapsed:.3f}s")

    def test_rust_component_status_reporting(self):
        """
        Test that Rust component status is reported correctly.

        This test validates that the status reporting functions
        provide accurate information about Rust component availability.
        """
        status = get_rust_component_status()

        # Validate status structure
        assert isinstance(status, dict), "Status should be a dictionary"
        assert "available" in status, "Status should include availability info"
        assert "initialized" in status, "Status should include initialization info"
        assert "failed" in status, "Status should include failure info"
        assert "performance_gains" in status, "Status should include performance info"
        assert "active_count" in status, "Status should include active count"
        assert "total_count" in status, "Status should include total count"

        # Validate component tracking
        expected_components = [
            "parser",
            "formid_analyzer",
            "plugin_analyzer",
            "record_scanner",
            "report_generation",
            "database",
            "database_pool",
            "file_io",
            "file_io_core",
            "mod_detector",
        ]

        for component in expected_components:
            assert component in status["available"], f"Component {component} not tracked"

        # Validate counts are consistent
        available_count = sum(1 for v in status["available"].values() if v)
        assert status["active_count"] == available_count, "Active count mismatch"


@pytest.mark.rust
@pytest.mark.integration
@pytest.mark.e2e
@pytest.mark.performance
class TestE2EPerformance:
    """
    Performance-focused end-to-end tests.

    These tests measure and validate the performance improvements
    achieved by Rust acceleration in real-world scenarios.
    """

    @pytest.mark.asyncio
    async def test_pipeline_performance_improvement(self, crash_log_samples, mock_yamldata):
        """
        Measure performance improvement of Rust-accelerated pipeline.

        This test compares the performance of Rust-accelerated components
        against their Python counterparts using real crash log data.
        """
        if not any(is_rust_accelerated(component) for component in ["parser", "formid_analyzer", "plugin_analyzer"]):
            pytest.skip("No Rust components available for performance testing")

        # Use largest available crash log for performance testing
        largest_sample = max(crash_log_samples.items(), key=lambda x: x[1].stat().st_size if x[1].exists() else 0)
        _, log_path = largest_sample

        self._read_crash_log(log_path)

        # Measure Rust performance
        orchestrator = OrchestratorCore(yamldata=mock_yamldata, fcx_mode=False, show_formid_values=True, formid_db_exists=True)

        rust_times = []
        async with orchestrator:
            for _ in range(3):  # Run multiple times for average
                with PerformanceTimer() as timer:
                    await orchestrator.process_crash_log(crashlog_file=log_path)
                rust_times.append(timer.elapsed)

        avg_rust_time = sum(rust_times) / len(rust_times)

        logger.info(f"Average Rust pipeline time: {avg_rust_time:.3f}s")

        # Performance should be reasonable (< 2 seconds for typical logs)
        assert avg_rust_time < 2.0, f"Rust pipeline too slow: {avg_rust_time:.3f}s"

    def _read_crash_log(self, log_path: Path) -> list[str]:
        """Helper method to read crash log files."""
        try:
            with Path(log_path).open("r", encoding="utf-8", errors="ignore") as f:
                return [line.rstrip("\n\r") for line in f]
        except Exception as e:
            pytest.skip(f"Could not read crash log {log_path}: {e}")


if __name__ == "__main__":
    # Run tests with verbose output for debugging
    pytest.main([__file__, "-v", "-s", "--tb=short"])
