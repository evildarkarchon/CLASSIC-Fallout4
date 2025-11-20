"""
Mock data factory for creating test doubles and mock objects.

This module provides factories for creating comprehensive mock objects
used in Rust integration testing, including YAML data, settings,
and other configuration objects.
"""

from typing import Any
from unittest.mock import MagicMock, Mock


class MockDataFactory:
    """
    Factory for creating mock objects used in Rust integration testing.

    This factory provides pre-configured mock objects that simulate
    the various configuration and data objects used by CLASSIC components.
    """

    @staticmethod
    def create_fallout4_yamldata(
        problematic_plugins: dict[str, str] | None = None,
        record_patterns: list[str] | None = None,
        formid_db_enabled: bool = True,
        show_formid_values: bool = True,
    ) -> Mock:
        """
        Create a comprehensive mock YAML data object for Fallout 4.

        Args:
            problematic_plugins: Dictionary of problematic plugins to include
            record_patterns: List of record patterns to scan for
            formid_db_enabled: Whether FormID database is enabled
            show_formid_values: Whether to show FormID values in output

        Returns:
            Mock object configured with Fallout 4 YAML data structure
        """
        mock_yaml = Mock()

        # Basic game configuration
        mock_yaml.game_type = "fallout4"
        mock_yaml.crashgen_name = "Buffout 4"
        mock_yaml.xse_acronym = "F4SE"
        mock_yaml.game_root_name = "Fallout 4"
        mock_yaml.game_executable = "Fallout4.exe"

        # Game version patterns
        mock_yaml.version_patterns = {"game": r"Fallout 4 v(\d+\.\d+\.\d+)", "crashgen": r"Buffout 4 v(\d+\.\d+\.\d+)"}

        # Default problematic plugins
        if problematic_plugins is None:
            problematic_plugins = {
                "MoreSpawns.esp": "Causes excessive spawning leading to CTD",
                "Arbitration.esp": "Combat overhaul with script conflicts",
                "ChildrenOfAtom.esp": "Faction conflicts with base game",
                "CompanionsGoneWild.esp": "Companion system conflicts",
                "DiamondCityExpansion.esp": "Cell conflicts in Diamond City",
                "EveryonesBestFriend.esp": "Companion limit bypassing issues",
                "FogOut.esp": "Weather system conflicts",
                "GlowingAnimals.esp": "Animation script issues",
                "HudFramework.esp": "HUD conflicts with other mods",
                "ImmersiveFallout.esp": "Large overhaul causing instability",
                "PlaceEverywhere.esp": "Workshop placement conflicts",
                "ScrapEverything.esp": "Precombine conflicts",
                "Settlement_limit_patch.esp": "Settlement system conflicts",
            }

        mock_yaml.problematic_plugins = problematic_plugins

        # Default record patterns for scanning
        if record_patterns is None:
            record_patterns = [
                "TESForm",
                "BGSKeyword",
                "TESObjectSTAT",
                "TESObjectREFR",
                "BGSConstructibleObject",
                "TESQuest",
                "BGSScene",
                "BGSStoryManagerBranchNode",
                "BGSStoryManagerQuestNode",
                "BGSStoryManagerEventNode",
                "TESFaction",
                "TESRace",
                "TESClass",
                "TESNPC",
                "TESObjectWEAP",
                "TESObjectARMO",
                "TESObjectMISC",
                "TESAmmo",
                "BGSNote",
                "TESKey",
                "AlchemyItem",
                "BGSIdleMarker",
                "BGSHeadPart",
                "TESEyes",
                "TESPackage",
                "BGSPerk",
                "BGSBodyPartData",
                "BGSAddonNode",
                "ActorValueInfo",
                "BGSRadiationStage",
                "BGSCameraShot",
                "BGSCameraPath",
                "BGSVoiceType",
                "BGSImpactData",
                "BGSImpactDataSet",
                "TESObjectACTI",
                "TESFlora",
                "TESFurniture",
                "TESObjectCONT",
                "TESObjectDOOR",
                "TESObjectLIGH",
                "BGSProjectile",
                "TESObjectTREE",
            ]

        mock_yaml.record_patterns = record_patterns

        # FormID database configuration
        mock_yaml.formid_database_enabled = formid_db_enabled
        mock_yaml.show_formid_values = show_formid_values
        mock_yaml.formid_database_path = "FormID_Database.json"

        # Plugin limits configuration
        mock_yaml.plugin_limits = {"esp_limit": 255, "esl_limit": 2048, "warn_at_esp": 200, "warn_at_esl": 1500}

        # Segment configuration for parsing
        mock_yaml.log_segments = {
            "compatibility": {"start_marker": "\t[Compatibility]", "end_marker": "SYSTEM SPECS:"},
            "system_specs": {"start_marker": "SYSTEM SPECS:", "end_marker": "PROBABLE CALL STACK:"},
            "call_stack": {"start_marker": "PROBABLE CALL STACK:", "end_marker": "MODULES:"},
            "modules": {"start_marker": "MODULES:", "end_marker": "F4SE PLUGINS:"},
            "f4se_plugins": {"start_marker": "F4SE PLUGINS:", "end_marker": "PLUGINS:"},
            "plugins": {"start_marker": "PLUGINS:", "end_marker": "EOF"},
        }

        # Output formatting configuration
        mock_yaml.output_format = {
            "include_formid_values": show_formid_values,
            "group_by_plugin": True,
            "show_load_order": True,
            "highlight_problematic": True,
        }

        # Performance configuration
        mock_yaml.performance = {"parallel_processing": True, "max_worker_threads": 4, "chunk_size": 1000, "enable_caching": True}

        return mock_yaml

    @staticmethod
    def create_skyrim_yamldata() -> Mock:
        """
        Create a mock YAML data object for Skyrim.

        Returns:
            Mock object configured with Skyrim-specific data
        """
        mock_yaml = Mock()

        # Basic game configuration
        mock_yaml.game_type = "skyrim"
        mock_yaml.crashgen_name = "Crash Logger SSE"
        mock_yaml.xse_acronym = "SKSE"
        mock_yaml.game_root_name = "The Elder Scrolls V: Skyrim Special Edition"
        mock_yaml.game_executable = "SkyrimSE.exe"

        # Skyrim-specific problematic plugins
        mock_yaml.problematic_plugins = {
            "SkyUI.esp": "Interface conflicts",
            "FNIS.esp": "Animation conflicts",
            "RaceMenu.esp": "Character creation conflicts",
        }

        # Similar record patterns (many overlap with Fallout 4)
        mock_yaml.record_patterns = [
            "TESForm",
            "BGSKeyword",
            "TESObjectSTAT",
            "TESObjectREFR",
            "TESQuest",
            "TESFaction",
            "TESRace",
            "TESNPC",
        ]

        mock_yaml.formid_database_enabled = True
        mock_yaml.show_formid_values = True

        return mock_yaml

    @staticmethod
    def create_settings_cache_mock() -> Mock:
        """
        Create a mock YamlSettingsCache object.

        Returns:
            Mock object that simulates YAML settings cache functionality
        """
        cache_mock = Mock()

        # Mock batch_get_settings method
        def mock_batch_get_settings(settings_requests):
            """Mock implementation of batch_get_settings."""
            results = []
            for _type_class, _yaml_enum, key in settings_requests:
                if key == "show_formid_values" or key == "formid_database_enabled":
                    results.append(True)
                elif key == "problematic_plugins":
                    results.append({"TestMod.esp": "Test problematic plugin"})
                elif key == "record_patterns":
                    results.append(["TESForm", "BGSKeyword"])
                else:
                    results.append(None)
            return results

        cache_mock.batch_get_settings = mock_batch_get_settings
        cache_mock.get_setting = Mock(return_value=True)
        cache_mock.clear_cache = Mock()

        return cache_mock

    @staticmethod
    def create_message_handler_mock() -> Mock:
        """
        Create a mock MessageHandler object.

        Returns:
            Mock object that simulates message handling functionality
        """
        handler_mock = Mock()

        # Mock message methods
        handler_mock.msg_info = Mock()
        handler_mock.msg_warning = Mock()
        handler_mock.msg_error = Mock()
        handler_mock.msg_debug = Mock()
        handler_mock.msg_verbose = Mock()

        # Mock state management
        handler_mock.clear_instance = Mock()
        handler_mock.get_instance = Mock(return_value=handler_mock)

        # Mock configuration
        handler_mock.set_verbosity = Mock()
        handler_mock.enable_file_logging = Mock()
        handler_mock.disable_file_logging = Mock()

        return handler_mock

    @staticmethod
    def create_async_bridge_mock() -> Mock:
        """
        Create a mock AsyncBridge object.

        Returns:
            Mock object that simulates async bridge functionality
        """
        bridge_mock = Mock()

        # Mock async execution
        def mock_run_async(coro):
            """Mock implementation that returns a simple result."""
            return MagicMock()

        bridge_mock.run_async = mock_run_async
        bridge_mock.get_instance = Mock(return_value=bridge_mock)
        bridge_mock.shutdown = Mock()

        return bridge_mock

    @staticmethod
    def create_file_io_mock() -> Mock:
        """
        Create a mock FileIOCore object.

        Returns:
            Mock object that simulates file I/O operations
        """
        io_mock = Mock()

        # Mock file operations
        io_mock.read_file = Mock(return_value="Mock file content")
        io_mock.write_file = Mock(return_value=True)
        io_mock.exists = Mock(return_value=True)
        io_mock.get_file_size = Mock(return_value=1024)

        # Mock async operations
        async def mock_read_file_async(path):
            return "Mock async file content"

        async def mock_write_file_async(path, content):
            return True

        io_mock.read_file_async = mock_read_file_async
        io_mock.write_file_async = mock_write_file_async

        # Mock batch operations
        io_mock.read_files_batch = Mock(return_value=["content1", "content2"])
        io_mock.process_directory = Mock(return_value=["file1.txt", "file2.txt"])

        return io_mock

    @staticmethod
    def create_orchestrator_mock() -> Mock:
        """
        Create a mock OrchestratorCore object.

        Returns:
            Mock object that simulates orchestrator functionality
        """
        orchestrator_mock = Mock()

        # Mock processing methods
        async def mock_process_crash_log_async(*args, **kwargs):
            return {
                "game_version": "Fallout 4 v1.10.163",
                "crashgen_version": "Buffout 4 v1.28.6",
                "main_error": "EXCEPTION_ACCESS_VIOLATION",
                "segments": [[], [], ["mock_callstack"], [], [], ["mock_plugins"]],
                "formids": ["0x12345678", "0xABCDEF01"],
                "plugins": {"00": "Fallout4.esm", "01": "TestMod.esp"},
                "problematic_plugins": ["TestMod.esp"],
                "records": ["TESForm", "BGSKeyword"],
            }

        orchestrator_mock.process_crash_log_async = mock_process_crash_log_async

        # Mock synchronous processing
        orchestrator_mock.process_crash_log = Mock(
            return_value={
                "game_version": "Fallout 4 v1.10.163",
                "crashgen_version": "Buffout 4 v1.28.6",
                "segments": [[], [], [], [], [], []],
            }
        )

        # Mock component initialization
        orchestrator_mock.initialize_components = Mock()
        orchestrator_mock.shutdown = Mock()

        return orchestrator_mock

    @staticmethod
    def create_performance_monitor_mock() -> Mock:
        """
        Create a mock performance monitoring object.

        Returns:
            Mock object that simulates performance monitoring
        """
        monitor_mock = Mock()

        # Mock timing methods
        monitor_mock.start_timer = Mock()
        monitor_mock.end_timer = Mock(return_value=0.123)  # Mock 123ms
        monitor_mock.get_elapsed_time = Mock(return_value=0.123)

        # Mock memory monitoring
        monitor_mock.get_memory_usage = Mock(
            return_value={
                "rss": 50 * 1024 * 1024,  # 50MB
                "vms": 100 * 1024 * 1024,  # 100MB
                "peak_rss": 60 * 1024 * 1024,  # 60MB peak
            }
        )

        # Mock statistics
        monitor_mock.get_statistics = Mock(
            return_value={"total_operations": 100, "average_time": 0.050, "min_time": 0.001, "max_time": 0.200, "total_time": 5.0}
        )

        monitor_mock.reset_statistics = Mock()

        return monitor_mock

    @classmethod
    def create_complete_test_environment(cls, game_type: str = "fallout4", rust_available: bool = True) -> dict[str, Any]:
        """
        Create a complete test environment with all necessary mocks.

        Args:
            game_type: Type of game to configure for ("fallout4" or "skyrim")
            rust_available: Whether Rust components should be available

        Returns:
            Dictionary containing all configured mock objects
        """
        if game_type == "fallout4":
            yamldata = cls.create_fallout4_yamldata()
        elif game_type == "skyrim":
            yamldata = cls.create_skyrim_yamldata()
        else:
            raise ValueError(f"Unsupported game type: {game_type}")

        environment = {
            "yamldata": yamldata,
            "settings_cache": cls.create_settings_cache_mock(),
            "message_handler": cls.create_message_handler_mock(),
            "async_bridge": cls.create_async_bridge_mock(),
            "file_io": cls.create_file_io_mock(),
            "orchestrator": cls.create_orchestrator_mock(),
            "performance_monitor": cls.create_performance_monitor_mock(),
            "rust_available": rust_available,
            "game_type": game_type,
        }

        return environment

    @staticmethod
    def create_rust_status_mock(components_available: list[str]) -> dict[str, Any]:
        """
        Create a mock Rust status dictionary.

        Args:
            components_available: List of component names that should be available

        Returns:
            Dictionary simulating Rust component status
        """
        all_components = [
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

        available = {}
        initialized = {}
        failed = {}
        performance_gains = {}

        for component in all_components:
            if component in components_available:
                available[component] = True
                initialized[component] = f"{component} initialized successfully"

                # Mock performance gains
                if component == "parser":
                    performance_gains[component] = "150x"
                elif component == "formid_analyzer":
                    performance_gains[component] = "50x"
                elif component == "plugin_analyzer":
                    performance_gains[component] = "30x"
                elif component == "record_scanner":
                    performance_gains[component] = "40x"
                else:
                    performance_gains[component] = "20x"
            else:
                available[component] = False
                failed[component] = f"{component} not available"

        return {
            "available": available,
            "initialized": initialized,
            "failed": failed,
            "performance_gains": performance_gains,
            "active_count": len(components_available),
            "total_count": len(all_components),
            "acceleration_active": len(components_available) > 0,
            "mode": "TEST_MODE",
        }
