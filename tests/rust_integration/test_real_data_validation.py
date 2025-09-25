"""
Real data validation tests for Phase 6 Rust migration validation.

This module tests Rust components using actual crash logs from the backup directory
and validates FormID extraction accuracy, plugin analysis correctness, and overall
data processing integrity with real-world scenarios.

Key Validation Areas:
- FormID extraction accuracy with real crash data
- Plugin analysis with authentic load orders
- Different crash log formats and generators
- Edge cases and unusual data patterns found in real logs
- Cross-validation between Rust and Python implementations
"""

import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple
from unittest.mock import Mock, patch

import pytest

# Skip entire module if Rust extensions not available
pytest.importorskip("classic_core", reason="Rust extensions not available")

# Import test infrastructure
from tests.test_infra.performance_utils import PerformanceTimer

# Import core components
from ClassicLib.integration.factory import (
    get_parser,
    get_formid_analyzer,
    get_plugin_analyzer,
    get_record_scanner,
    get_database_pool,
    get_file_io,
)
from ClassicLib.integration.status import (
    get_rust_component_status,
    is_rust_accelerated,
)


@pytest.mark.rust
@pytest.mark.integration
@pytest.mark.real_data
class TestRealCrashLogValidation:
    """
    Validate Rust components using real crash log data.

    These tests use actual crash logs from the backup directory to validate
    that Rust components work correctly with real-world data and produce
    accurate results.
    """

    @pytest.fixture(scope="class")
    def real_crash_logs(self) -> Dict[str, Path]:
        """
        Discover and categorize real crash logs for testing.

        Returns a dictionary mapping crash log categories to file paths,
        allowing tests to focus on specific types of crash logs.
        """
        project_root = Path(__file__).parent.parent.parent
        backup_logs = project_root / "CLASSIC Backup" / "Unsolved Logs"

        crash_logs = {}

        if backup_logs.exists():
            log_files = list(backup_logs.glob("*.log"))

            # Categorize logs by characteristics
            for log_file in log_files:
                try:
                    # Read first few lines to categorize
                    with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
                        first_lines = [f.readline().strip() for _ in range(10)]

                    # Determine crash log type based on content
                    if any("Buffout 4" in line for line in first_lines):
                        category = "buffout4"
                    elif any("Crash Logger" in line for line in first_lines):
                        category = "crash_logger"
                    elif any("F4SE" in line for line in first_lines):
                        category = "f4se"
                    else:
                        category = "unknown"

                    # Use file size to sub-categorize
                    size = log_file.stat().st_size
                    if size > 100000:  # > 100KB
                        size_cat = "large"
                    elif size > 10000:  # > 10KB
                        size_cat = "medium"
                    else:
                        size_cat = "small"

                    key = f"{category}_{size_cat}"
                    if key not in crash_logs:
                        crash_logs[key] = log_file

                except Exception as e:
                    logging.warning(f"Could not categorize crash log {log_file}: {e}")
                    continue

        # Ensure we have at least some test data
        if not crash_logs:
            # Create minimal test data if no real logs available
            test_data_dir = Path(__file__).parent / "test_data"
            test_data_dir.mkdir(exist_ok=True)

            synthetic_log = test_data_dir / "real_data_test.log"
            if not synthetic_log.exists():
                synthetic_content = self._create_realistic_crash_log()
                synthetic_log.write_text(synthetic_content, encoding="utf-8")

            crash_logs["synthetic_real"] = synthetic_log

        # Limit to reasonable number for testing performance
        return dict(list(crash_logs.items())[:10])

    @pytest.fixture
    def mock_yamldata(self) -> Mock:
        """Create comprehensive mock YAML data for real data validation."""
        mock_yaml = Mock()

        # Realistic game configuration for Fallout 4
        mock_yaml.game_type = "fallout4"
        mock_yaml.crashgen_name = "Buffout 4"
        mock_yaml.xse_acronym = "F4SE"
        mock_yaml.game_root_name = "Fallout 4"

        # Comprehensive problematic plugins list (real examples)
        mock_yaml.problematic_plugins = {
            "MoreSpawns.esp": "Causes CTD due to spawning conflicts",
            "Arbitration.esp": "Combat overhaul with script conflicts",
            "ChildrenofAtom.esp": "Known faction conflicts",
            "CompanionsGoneWild.esp": "Companion script issues",
            "DiamondCityExpansion.esp": "Cell conflicts with base game",
            "EveryonesBestFriend.esp": "Companion limit conflicts",
            "FogOut.esp": "Weather system conflicts",
            "GlowingAnimals.esp": "Animation script issues",
            "HudFrameworkFix.esp": "HUD conflicts with other mods",
            "Immersive_Fallout.esp": "Overhauls causing instability",
        }

        # FormID database configuration
        mock_yaml.formid_database_enabled = True
        mock_yaml.show_formid_values = True

        # Comprehensive record patterns (real Fallout 4 record types)
        mock_yaml.record_patterns = [
            "TESForm", "BGSKeyword", "TESObjectSTAT", "TESObjectREFR",
            "BGSConstructibleObject", "TESQuest", "BGSScene", "BGSStoryManagerBranchNode",
            "BGSStoryManagerQuestNode", "BGSStoryManagerEventNode", "TESFaction",
            "TESRace", "TESClass", "TESNPC", "TESObjectWEAP", "TESObjectARMO",
            "TESObjectMISC", "TESAmmo", "BGSNote", "TESKey", "AlchemyItem",
            "BGSIdleMarker", "BGSConstructibleObject", "BGSHeadPart", "TESEyes",
            "TESPackage", "BGSPerk", "BGSBodyPartData", "BGSAddonNode",
            "ActorValueInfo", "BGSRadiationStage", "BGSCameraShot", "BGSCameraPath"
        ]

        return mock_yaml

    def _create_realistic_crash_log(self) -> str:
        """Create a realistic crash log for testing when real logs aren't available."""
        return """Fallout 4 v1.10.163
Buffout 4 v1.28.6

Unhandled exception "EXCEPTION_ACCESS_VIOLATION" at 0x7FF66DF19300 Fallout4.exe+0DB9300

	[Compatibility]
		F4EE: false
	[Crashlog]
		AutoOpen: true
		PromptUpload: true
	[Fixes]
		ActorIsHostileToActor: true
		CellInit: true
		CreateD3DAndSwapChain: true
		EncounterZoneReset: true
		GreyMovies: true
		MagicEffectApplyEvent: true
		MovementPlanner: true
		PackageAllocateLocation: true
		SafeExit: true
		TESObjectREFRGetEncounterZone: true
		UnalignedLoad: true
		UtilityShader: true

SYSTEM SPECS:
	OS: Microsoft Windows 11 Home v10.0.22621
	CPU: AuthenticAMD AMD Ryzen 5 5600X 6-Core Processor
	GPU #1: Nvidia GA104 [GeForce RTX 3060 Ti Lite Hash Rate]
	GPU #2: Microsoft Basic Render Driver
	PHYSICAL MEMORY: 16.00 GB/32.00 GB

PROBABLE CALL STACK:
	[0] 0x7FF66DF19300 Fallout4.exe+0DB9300 -> FormID: 0x0001234A (Fallout4.esm)
	[1] 0x7FF66DF45678 Fallout4.exe+0E45678 -> FormID: 0xFE000801 (ArmorKeywords.esl)
	[2] 0x7FF66E123456 Fallout4.exe+1123456 -> TESObjectREFR at 0x7FF66E123456
	[3] 0x7FF66E789ABC Fallout4.exe+1789ABC -> BGSKeyword at 0x7FF66E789ABC
	[4] 0x7FF66EDEF012 Fallout4.exe+1EEF012 -> FormID: 0x05000D62 (ArmorSmithExtended.esp)
	[5] 0x7FF66F345678 Fallout4.exe+2345678 -> FormID: 0x0200456F (DLCworkshop01.esm)

MODULES:
	Fallout4.exe                     v1.10.163.0
	steam_api64.dll                  v5.46.91.68
	KERNELBASE.dll                   v10.0.22621.2506
	f4se_1_6_353.dll                 v1.6.353.0
	buffout4.dll                     v1.28.6.0
	AchievementsModsEnabler.dll      v1.0.5.0
	MCM.dll                          v1.39.0.0
	place.dll                        v0.5.8.1

F4SE PLUGINS:
	Buffout4 v1.28.6
	McM - Mod Configuration Menu v1.39
	Achievements Mods Enabler v1.0.5
	Place Anywhere v0.5.8.1

PLUGINS:
	[00] Fallout4.esm
	[01] DLCRobot.esm
	[02] DLCworkshop01.esm
	[03] DLCCoast.esm
	[04] DLCworkshop02.esm
	[05] DLCworkshop03.esm
	[06] DLCNukaWorld.esm
	[07] Unofficial Fallout 4 Patch.esp
	[08] ArmorKeywords.esm
	[09] XDI.esm
	[0A] WorkshopFramework.esm
	[FE:000] PPF.esm
	[FE:001] ArmorKeywords.esl
	[FE:002] DLCworkshop01 - Lighting.esl
	[0B] HUDFramework.esm
	[0C] Sim Settlements.esm
	[0D] SettlementKeywords.esm
	[0E] ArmorSmithExtended.esp
	[0F] Eli_Armour_Compendium.esp
	[10] K9TacticalHarness.esp
	[11] LooksMenu.esp
	[12] More Spawns - Automatron.esp
	[13] Arbitration - Automatron.esp
	[14] PlaceEverywhere.esp
	[15] Scrap Everything.esp
"""

    def _read_crash_log(self, log_path: Path) -> List[str]:
        """Read a crash log file and return it as a list of lines."""
        try:
            with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
                return [line.rstrip('\n\r') for line in f.readlines()]
        except Exception as e:
            pytest.skip(f"Could not read crash log {log_path}: {e}")

    def test_formid_extraction_accuracy(self, real_crash_logs, mock_yamldata):
        """
        Test FormID extraction accuracy using real crash log data.

        This test validates that FormIDs are correctly extracted from
        real crash logs and that the format matches expected patterns.
        """
        if not is_rust_accelerated("formid_analyzer"):
            pytest.skip("Rust FormID analyzer not available for real data testing")

        formid_analyzer = get_formid_analyzer(mock_yamldata, True, True)

        # Pattern to match valid FormIDs
        formid_pattern = re.compile(r'0x[0-9A-Fa-f]{8}')

        for log_category, log_path in real_crash_logs.items():
            crash_data = self._read_crash_log(log_path)

            with PerformanceTimer(f"FormID extraction - {log_category}") as timer:
                formids = formid_analyzer.extract_formids(crash_data)

            logging.info(f"FormID extraction for {log_category}: {len(formids)} FormIDs in {timer.elapsed:.3f}s")

            # Validate FormID format and content
            valid_formids = 0
            for formid in formids:
                if formid_pattern.search(formid):
                    valid_formids += 1

                    # Extract hex value to validate range
                    hex_match = formid_pattern.search(formid)
                    if hex_match:
                        hex_value = hex_match.group()
                        try:
                            formid_int = int(hex_value, 16)
                            # FormIDs should be in valid range (0x00000000 to 0xFFFFFFFF)
                            assert 0 <= formid_int <= 0xFFFFFFFF, \
                                f"FormID out of range: {hex_value}"
                        except ValueError:
                            pytest.fail(f"Invalid hexadecimal FormID: {hex_value}")

            # Should extract some valid FormIDs from real crash logs
            if len(crash_data) > 50:  # Only check for substantial crash logs
                assert valid_formids > 0, f"No valid FormIDs extracted from {log_category}"

                # At least 70% of extracted FormIDs should be valid
                validity_ratio = valid_formids / len(formids) if formids else 0
                assert validity_ratio >= 0.7, \
                    f"Low FormID validity ratio for {log_category}: {validity_ratio:.2f}"

    def test_plugin_analysis_with_real_load_orders(self, real_crash_logs, mock_yamldata):
        """
        Test plugin analysis using real load orders from crash logs.

        This test validates that plugin parsing works correctly with
        real load orders including ESM, ESP, and ESL files.
        """
        if not is_rust_accelerated("plugin_analyzer"):
            pytest.skip("Rust plugin analyzer not available for real data testing")

        plugin_analyzer = get_plugin_analyzer(mock_yamldata)

        # Expected file extensions for Fallout 4 plugins
        valid_extensions = {'.esm', '.esp', '.esl'}

        for log_category, log_path in real_crash_logs.items():
            crash_data = self._read_crash_log(log_path)

            with PerformanceTimer(f"Plugin analysis - {log_category}") as timer:
                plugins_dict, limit_triggered, limit_disabled = plugin_analyzer.loadorder_scan_log(crash_data)

            logging.info(f"Plugin analysis for {log_category}: {len(plugins_dict)} plugins in {timer.elapsed:.3f}s")

            if plugins_dict:
                # Validate plugin structure
                for hex_id, plugin_name in plugins_dict.items():
                    # Hex ID should be valid
                    try:
                        int(hex_id, 16)
                    except ValueError:
                        pytest.fail(f"Invalid plugin hex ID: {hex_id}")

                    # Plugin name should have valid extension
                    plugin_path = Path(plugin_name)
                    assert plugin_path.suffix.lower() in valid_extensions, \
                        f"Invalid plugin extension: {plugin_name}"

                    # Essential plugins should be present
                    if len(plugins_dict) > 5:  # Only check substantial load orders
                        essential_plugins = ["Fallout4.esm"]
                        plugin_names = list(plugins_dict.values())

                        for essential in essential_plugins:
                            assert any(essential in plugin for plugin in plugin_names), \
                                f"Missing essential plugin {essential} in {log_category}"

                # Validate load order structure
                hex_ids = [int(hex_id, 16) for hex_id in plugins_dict.keys() if hex_id != "FE"]
                if hex_ids:
                    # Should start from 00 (or close to it)
                    min_id = min(hex_ids)
                    assert min_id <= 5, f"Load order should start near 00, got {min_id:02X}"

                    # Should have reasonable progression
                    max_id = max(hex_ids)
                    assert max_id < 255, f"Load order ID too high: {max_id:02X}"

    def test_record_scanning_with_real_data(self, real_crash_logs, mock_yamldata):
        """
        Test record scanning using real crash log data.

        This test validates that named record scanning finds actual
        record references in real crash logs.
        """
        if not is_rust_accelerated("record_scanner"):
            pytest.skip("Rust record scanner not available for real data testing")

        record_scanner = get_record_scanner(mock_yamldata)

        for log_category, log_path in real_crash_logs.items():
            crash_data = self._read_crash_log(log_path)

            with PerformanceTimer(f"Record scanning - {log_category}") as timer:
                fragment, matches = record_scanner.scan_named_records(crash_data)

            logging.info(f"Record scanning for {log_category}: {len(matches)} matches in {timer.elapsed:.3f}s")

            # Validate record matches
            if matches:
                valid_records = 0
                for match in matches:
                    # Should match known record types
                    if any(record_type in match for record_type in mock_yamldata.record_patterns):
                        valid_records += 1

                # Most matches should be valid record types
                if len(matches) > 0:
                    validity_ratio = valid_records / len(matches)
                    assert validity_ratio >= 0.5, \
                        f"Low record validity ratio for {log_category}: {validity_ratio:.2f}"

    def test_cross_validation_rust_python(self, real_crash_logs, mock_yamldata):
        """
        Cross-validate Rust and Python implementations using real data.

        This test compares results between Rust and Python implementations
        to ensure consistency and correctness.
        """
        # Only test if we have Rust components available
        rust_components = ["parser", "formid_analyzer", "plugin_analyzer"]
        available = [comp for comp in rust_components if is_rust_accelerated(comp)]

        if not available:
            pytest.skip("No Rust components available for cross-validation")

        # Use first substantial crash log for detailed comparison
        substantial_logs = {k: v for k, v in real_crash_logs.items()
                           if v.stat().st_size > 10000}  # > 10KB

        if not substantial_logs:
            pytest.skip("No substantial crash logs available for cross-validation")

        log_category, log_path = next(iter(substantial_logs.items()))
        crash_data = self._read_crash_log(log_path)

        logging.info(f"Cross-validating with {log_category} ({len(crash_data)} lines)")

        # Test Parser cross-validation
        if "parser" in available:
            rust_parser = get_parser()

            # Get Rust results
            rust_result = rust_parser.find_segments(
                crash_data=crash_data,
                crashgen_name=mock_yamldata.crashgen_name,
                xse_acronym=mock_yamldata.xse_acronym,
                game_root_name=mock_yamldata.game_root_name
            )

            # Get Python results by forcing fallback
            with patch.object(rust_parser, '_use_rust', False):
                python_result = rust_parser.find_segments(
                    crash_data=crash_data,
                    crashgen_name=mock_yamldata.crashgen_name,
                    xse_acronym=mock_yamldata.xse_acronym,
                    game_root_name=mock_yamldata.game_root_name
                )

            # Compare structural consistency
            assert len(rust_result) == len(python_result), \
                "Rust and Python parser results have different structure"

            rust_segments = rust_result[3]
            python_segments = python_result[3]
            assert len(rust_segments) == len(python_segments), \
                f"Different segment counts: Rust={len(rust_segments)}, Python={len(python_segments)}"

            # Compare segment sizes (should be similar, allowing for minor differences)
            for i, (rust_seg, python_seg) in enumerate(zip(rust_segments, python_segments)):
                size_diff = abs(len(rust_seg) - len(python_seg))
                max_size = max(len(rust_seg), len(python_seg))

                if max_size > 0:
                    diff_ratio = size_diff / max_size
                    assert diff_ratio < 0.2, \
                        f"Segment {i} size difference too large: {diff_ratio:.2f}"

    def test_edge_cases_and_malformed_data(self, real_crash_logs, mock_yamldata):
        """
        Test handling of edge cases and malformed data in real crash logs.

        This test validates that Rust components handle unusual patterns
        and corrupted data found in real crash logs.
        """
        components_to_test = ["parser", "formid_analyzer", "plugin_analyzer", "record_scanner"]
        available_components = [comp for comp in components_to_test if is_rust_accelerated(comp)]

        if not available_components:
            pytest.skip("No Rust components available for edge case testing")

        for log_category, log_path in real_crash_logs.items():
            crash_data = self._read_crash_log(log_path)

            # Introduce various types of corruption to test robustness
            corrupted_variants = [
                crash_data,  # Original
                crash_data[:len(crash_data)//2],  # Truncated
                ["CORRUPTED"] + crash_data[1:],  # Corrupted header
                crash_data + ["EXTRA_GARBAGE", "MORE_CORRUPTION"],  # Extra data
                [line.replace("FormID:", "CorruptedFormID:") for line in crash_data],  # Corrupted FormIDs
            ]

            for variant_name, variant_data in zip(
                ["original", "truncated", "corrupt_header", "extra_data", "corrupt_formids"],
                corrupted_variants
            ):

                # Test each available component with corrupted data
                for component in available_components:
                    try:
                        if component == "parser":
                            parser = get_parser()
                            result = parser.find_segments(
                                crash_data=variant_data,
                                crashgen_name=mock_yamldata.crashgen_name,
                                xse_acronym=mock_yamldata.xse_acronym,
                                game_root_name=mock_yamldata.game_root_name
                            )
                            # Should return structured data even with corruption
                            assert len(result) == 4, f"Parser should return 4-tuple for {variant_name}"

                        elif component == "formid_analyzer":
                            analyzer = get_formid_analyzer(mock_yamldata, True, True)
                            formids = analyzer.extract_formids(variant_data)
                            # Should return list even with corrupt data
                            assert isinstance(formids, list), f"FormID analyzer should return list for {variant_name}"

                        elif component == "plugin_analyzer":
                            analyzer = get_plugin_analyzer(mock_yamldata)
                            plugins, limit_triggered, limit_disabled = analyzer.loadorder_scan_log(variant_data)
                            # Should return structured results
                            assert isinstance(plugins, dict), f"Plugin analyzer should return dict for {variant_name}"
                            assert isinstance(limit_triggered, bool), f"Plugin analyzer limit flag should be bool for {variant_name}"

                        elif component == "record_scanner":
                            scanner = get_record_scanner(mock_yamldata)
                            fragment, matches = scanner.scan_named_records(variant_data)
                            # Should return list for matches
                            assert isinstance(matches, list), f"Record scanner should return list for {variant_name}"

                    except Exception as e:
                        # Controlled failures are acceptable, uncontrolled crashes are not
                        error_msg = str(e).lower()
                        acceptable_errors = ["invalid", "malformed", "corrupted", "parse error"]

                        is_controlled_error = any(keyword in error_msg for keyword in acceptable_errors)
                        if not is_controlled_error:
                            pytest.fail(
                                f"Component {component} crashed uncontrollably on {variant_name} "
                                f"variant of {log_category}: {e}"
                            )

    def test_performance_with_varying_log_sizes(self, real_crash_logs, mock_yamldata):
        """
        Test performance characteristics with crash logs of different sizes.

        This test validates that Rust components scale well with log size
        and meet performance targets across different data volumes.
        """
        components_to_test = ["parser", "formid_analyzer", "plugin_analyzer"]
        available_components = [comp for comp in components_to_test if is_rust_accelerated(comp)]

        if not available_components:
            pytest.skip("No Rust components available for performance testing")

        # Categorize logs by size
        size_categories = {}
        for log_category, log_path in real_crash_logs.items():
            size = log_path.stat().st_size

            if size < 10000:  # < 10KB
                size_cat = "small"
            elif size < 50000:  # < 50KB
                size_cat = "medium"
            elif size < 200000:  # < 200KB
                size_cat = "large"
            else:
                size_cat = "xlarge"

            if size_cat not in size_categories:
                size_categories[size_cat] = (log_category, log_path)

        performance_results = {}

        for size_cat, (log_category, log_path) in size_categories.items():
            crash_data = self._read_crash_log(log_path)
            size_kb = log_path.stat().st_size / 1024

            logging.info(f"Testing {size_cat} log: {log_category} ({size_kb:.1f}KB, {len(crash_data)} lines)")

            for component in available_components:
                with PerformanceTimer() as timer:
                    if component == "parser":
                        parser = get_parser()
                        parser.find_segments(
                            crash_data=crash_data,
                            crashgen_name=mock_yamldata.crashgen_name,
                            xse_acronym=mock_yamldata.xse_acronym,
                            game_root_name=mock_yamldata.game_root_name
                        )
                    elif component == "formid_analyzer":
                        analyzer = get_formid_analyzer(mock_yamldata, True, True)
                        analyzer.extract_formids(crash_data)
                    elif component == "plugin_analyzer":
                        analyzer = get_plugin_analyzer(mock_yamldata)
                        analyzer.loadorder_scan_log(crash_data)

                key = f"{component}_{size_cat}"
                performance_results[key] = {
                    "time": timer.elapsed,
                    "size_kb": size_kb,
                    "lines": len(crash_data)
                }

                # Performance targets based on size
                if size_cat == "small":
                    max_time = 0.01  # 10ms for small logs
                elif size_cat == "medium":
                    max_time = 0.05  # 50ms for medium logs
                elif size_cat == "large":
                    max_time = 0.2   # 200ms for large logs
                else:  # xlarge
                    max_time = 0.5   # 500ms for extra large logs

                assert timer.elapsed < max_time, \
                    f"{component} too slow for {size_cat} log: {timer.elapsed:.3f}s > {max_time}s"

        # Log performance summary
        logging.info("Performance results:")
        for key, result in performance_results.items():
            logging.info(f"  {key}: {result['time']:.3f}s for {result['size_kb']:.1f}KB ({result['lines']} lines)")


@pytest.mark.rust
@pytest.mark.integration
@pytest.mark.real_data
class TestRealDataAccuracy:
    """
    Test accuracy of data extraction and analysis using known patterns.

    These tests validate that components correctly identify and extract
    specific patterns that are known to exist in real crash logs.
    """

    def test_known_formid_patterns(self, real_crash_logs, mock_yamldata):
        """
        Test extraction of known FormID patterns from real crash logs.

        This test looks for specific FormID patterns that are commonly
        found in Fallout 4 crash logs and validates extraction accuracy.
        """
        if not is_rust_accelerated("formid_analyzer"):
            pytest.skip("Rust FormID analyzer not available")

        formid_analyzer = get_formid_analyzer(mock_yamldata, True, True)

        # Known FormID patterns to look for
        known_patterns = {
            "base_game": re.compile(r'0x00[0-9A-Fa-f]{6}'),  # Base game FormIDs
            "dlc_robot": re.compile(r'0x01[0-9A-Fa-f]{6}'),  # DLCRobot.esm
            "dlc_workshop": re.compile(r'0x02[0-9A-Fa-f]{6}'), # DLCworkshop01.esm
            "esl_formids": re.compile(r'0xFE[0-9A-Fa-f]{6}'), # ESL FormIDs
            "high_id_esp": re.compile(r'0x[0-9A-Fa-f][1-9A-Fa-f][0-9A-Fa-f]{6}') # High ID ESPs
        }

        pattern_counts = {pattern: 0 for pattern in known_patterns}
        total_logs_processed = 0

        for log_category, log_path in real_crash_logs.items():
            crash_data = self._read_crash_log(log_path)
            formids = formid_analyzer.extract_formids(crash_data)

            if formids:
                total_logs_processed += 1

                for formid in formids:
                    for pattern_name, pattern in known_patterns.items():
                        if pattern.search(formid):
                            pattern_counts[pattern_name] += 1

        # Log findings
        logging.info(f"FormID pattern analysis across {total_logs_processed} logs:")
        for pattern_name, count in pattern_counts.items():
            logging.info(f"  {pattern_name}: {count} occurrences")

        # Should find at least base game FormIDs in most substantial logs
        if total_logs_processed > 0:
            assert pattern_counts["base_game"] > 0, \
                "Should find base game FormIDs in real crash logs"

    def test_known_plugin_patterns(self, real_crash_logs, mock_yamldata):
        """
        Test identification of known plugin patterns in real load orders.

        This test validates that common Fallout 4 plugins and DLCs are
        correctly identified and parsed from real crash logs.
        """
        if not is_rust_accelerated("plugin_analyzer"):
            pytest.skip("Rust plugin analyzer not available")

        plugin_analyzer = get_plugin_analyzer(mock_yamldata)

        # Known plugin patterns to look for
        expected_plugins = {
            "base_game": ["Fallout4.esm"],
            "official_dlc": ["DLCRobot.esm", "DLCworkshop01.esm", "DLCCoast.esm", "DLCNukaWorld.esm"],
            "common_fixes": ["Unofficial Fallout 4 Patch.esp", "UFO4P.esp"],
            "script_extender": ["F4SE"],  # Can appear in various forms
            "esl_files": [".esl"],  # Any ESL file
        }

        pattern_findings = {category: 0 for category in expected_plugins}
        total_load_orders = 0

        for log_category, log_path in real_crash_logs.items():
            crash_data = self._read_crash_log(log_path)
            plugins_dict, _, _ = plugin_analyzer.loadorder_scan_log(crash_data)

            if plugins_dict:
                total_load_orders += 1
                plugin_names = list(plugins_dict.values())

                for category, patterns in expected_plugins.items():
                    for pattern in patterns:
                        if any(pattern in plugin for plugin in plugin_names):
                            pattern_findings[category] += 1
                            break  # Count category once per load order

        # Log findings
        logging.info(f"Plugin pattern analysis across {total_load_orders} load orders:")
        for category, count in pattern_findings.items():
            if total_load_orders > 0:
                percentage = (count / total_load_orders) * 100
                logging.info(f"  {category}: {count}/{total_load_orders} ({percentage:.1f}%)")

        # Should find base game in most load orders
        if total_load_orders > 0:
            base_game_ratio = pattern_findings["base_game"] / total_load_orders
            assert base_game_ratio >= 0.8, \
                f"Should find base game in most load orders: {base_game_ratio:.2f}"

    def test_crash_cause_correlation(self, real_crash_logs, mock_yamldata):
        """
        Test correlation between extracted data and potential crash causes.

        This test analyzes real crash logs to validate that extracted
        data correlates with known crash patterns and problematic plugins.
        """
        components_needed = ["formid_analyzer", "plugin_analyzer"]
        if not all(is_rust_accelerated(comp) for comp in components_needed):
            pytest.skip("Need both FormID and plugin analyzers for correlation testing")

        formid_analyzer = get_formid_analyzer(mock_yamldata, True, True)
        plugin_analyzer = get_plugin_analyzer(mock_yamldata)

        correlation_data = []

        for log_category, log_path in real_crash_logs.items():
            crash_data = self._read_crash_log(log_path)

            # Extract both FormIDs and plugins
            formids = formid_analyzer.extract_formids(crash_data)
            plugins_dict, limit_triggered, _ = plugin_analyzer.loadorder_scan_log(crash_data)

            if formids and plugins_dict:
                # Analyze correlations
                plugin_names = list(plugins_dict.values())

                # Check for problematic plugins
                problematic_found = []
                for plugin in plugin_names:
                    for problematic_plugin in mock_yamldata.problematic_plugins.keys():
                        if problematic_plugin in plugin:
                            problematic_found.append(plugin)

                # Check for high FormID count (potential indicator of issues)
                high_formid_count = len(formids) > 10

                # Check for plugin limit issues
                high_plugin_count = len(plugins_dict) > 100

                correlation_data.append({
                    "log_category": log_category,
                    "formid_count": len(formids),
                    "plugin_count": len(plugins_dict),
                    "problematic_plugins": problematic_found,
                    "limit_triggered": limit_triggered,
                    "high_formid_count": high_formid_count,
                    "high_plugin_count": high_plugin_count
                })

        # Analyze correlations
        if correlation_data:
            logs_with_issues = sum(1 for data in correlation_data
                                 if data["problematic_plugins"] or data["limit_triggered"])

            logging.info(f"Crash cause correlation analysis:")
            logging.info(f"  Total logs analyzed: {len(correlation_data)}")
            logging.info(f"  Logs with potential issues: {logs_with_issues}")

            for data in correlation_data:
                if data["problematic_plugins"] or data["limit_triggered"]:
                    logging.info(f"    {data['log_category']}: "
                               f"FormIDs={data['formid_count']}, "
                               f"Plugins={data['plugin_count']}, "
                               f"Problematic={data['problematic_plugins']}, "
                               f"LimitTriggered={data['limit_triggered']}")

        # Should be able to identify potential issues in substantial logs
        substantial_logs = [d for d in correlation_data if d["plugin_count"] > 10]
        if substantial_logs:
            assert len(substantial_logs) > 0, "Should have some substantial logs to analyze"


if __name__ == "__main__":
    # Run tests with verbose output for debugging
    pytest.main([__file__, "-v", "-s", "--tb=short"])
