"""
Crash log factory for generating realistic test data.

This module provides factories for creating realistic crash log data for
testing Rust components. It generates various types of crash logs with
authentic structures, FormIDs, and plugin patterns found in real logs.
"""

import random
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple
from unittest.mock import Mock


class CrashLogType(Enum):
    """
    Enumeration of different crash log types for testing.

    Each type represents a different crash log generator or scenario
    commonly encountered in real-world usage.
    """
    BUFFOUT4_BASIC = "buffout4_basic"
    BUFFOUT4_LARGE = "buffout4_large"
    BUFFOUT4_MANY_MODS = "buffout4_many_mods"
    CRASH_LOGGER = "crash_logger"
    NETSCRIPTFRAMEWORK = "netscriptframework"
    CORRUPTED = "corrupted"
    MINIMAL = "minimal"
    STRESS_TEST = "stress_test"


class CrashLogFactory:
    """
    Factory class for generating realistic crash log data for testing.

    This factory can generate various types of crash logs with authentic
    content patterns, FormIDs, plugin structures, and other elements
    found in real Fallout 4 crash logs.
    """

    # Common Fallout 4 master files
    MASTER_FILES = [
        "Fallout4.esm",
        "DLCRobot.esm",
        "DLCworkshop01.esm",
        "DLCCoast.esm",
        "DLCworkshop02.esm",
        "DLCworkshop03.esm",
        "DLCNukaWorld.esm"
    ]

    # Common community fixes and frameworks
    COMMON_FRAMEWORKS = [
        "Unofficial Fallout 4 Patch.esp",
        "F4SE.dll",
        "ArmorKeywords.esm",
        "HUDFramework.esm",
        "WorkshopFramework.esm",
        "SettlementKeywords.esm",
        "XDI.esm"
    ]

    # Common problematic plugins for testing
    PROBLEMATIC_PLUGINS = [
        "MoreSpawns.esp",
        "Arbitration.esp",
        "CompanionsGoneWild.esp",
        "EveryonesBestFriend.esp",
        "ScrapEverything.esp",
        "PlaceEverywhere.esp"
    ]

    # Common record types found in crash logs
    RECORD_TYPES = [
        "TESForm", "BGSKeyword", "TESObjectSTAT", "TESObjectREFR",
        "BGSConstructibleObject", "TESQuest", "BGSScene", "TESFaction",
        "TESRace", "TESNPC", "TESObjectWEAP", "TESObjectARMO",
        "TESObjectMISC", "AlchemyItem", "BGSPerk", "ActorValueInfo"
    ]

    def __init__(self, seed: Optional[int] = None):
        """
        Initialize the crash log factory.

        Args:
            seed: Random seed for reproducible test data generation
        """
        if seed is not None:
            random.seed(seed)

        self._formid_counter = 0
        self._plugin_counter = 0

    def generate_crash_log(self, log_type: CrashLogType, **kwargs) -> List[str]:
        """
        Generate a crash log of the specified type.

        Args:
            log_type: Type of crash log to generate
            **kwargs: Additional parameters for customization

        Returns:
            List of strings representing the crash log lines
        """
        if log_type == CrashLogType.BUFFOUT4_BASIC:
            return self._generate_buffout4_basic(**kwargs)
        elif log_type == CrashLogType.BUFFOUT4_LARGE:
            return self._generate_buffout4_large(**kwargs)
        elif log_type == CrashLogType.BUFFOUT4_MANY_MODS:
            return self._generate_buffout4_many_mods(**kwargs)
        elif log_type == CrashLogType.CRASH_LOGGER:
            return self._generate_crash_logger(**kwargs)
        elif log_type == CrashLogType.NETSCRIPTFRAMEWORK:
            return self._generate_netscriptframework(**kwargs)
        elif log_type == CrashLogType.CORRUPTED:
            return self._generate_corrupted(**kwargs)
        elif log_type == CrashLogType.MINIMAL:
            return self._generate_minimal(**kwargs)
        elif log_type == CrashLogType.STRESS_TEST:
            return self._generate_stress_test(**kwargs)
        else:
            raise ValueError(f"Unsupported crash log type: {log_type}")

    def _generate_buffout4_basic(self,
                                formid_count: int = 20,
                                plugin_count: int = 50,
                                **kwargs) -> List[str]:
        """Generate a basic Buffout 4 crash log."""
        lines = [
            "Fallout 4 v1.10.163",
            "Buffout 4 v1.28.6",
            "",
            'Unhandled exception "EXCEPTION_ACCESS_VIOLATION" at 0x7FF66DF19300 Fallout4.exe+0DB9300',
            "",
            "\t[Compatibility]",
            "\t\tF4EE: false",
            "\t[Crashlog]",
            "\t\tAutoOpen: true",
            "\t\tPromptUpload: true",
            "\t[Fixes]",
            "\t\tActorIsHostileToActor: true",
            "\t\tCellInit: true",
            "\t\tCreateD3DAndSwapChain: true",
            "",
            "SYSTEM SPECS:",
            "\tOS: Microsoft Windows 11 Home v10.0.22621",
            "\tCPU: AMD Ryzen 5 5600X 6-Core Processor",
            "\tGPU #1: Nvidia GeForce RTX 3060 Ti",
            "\tPHYSICAL MEMORY: 16.00 GB/32.00 GB",
            "",
            "PROBABLE CALL STACK:"
        ]

        # Generate call stack with FormIDs
        lines.extend(self._generate_call_stack(formid_count))

        lines.extend([
            "",
            "MODULES:",
            "\tFallout4.exe",
            "\tf4se_1_6_353.dll",
            "\tbuffout4.dll",
            "",
            "F4SE PLUGINS:",
            "\tBuffout4 v1.28.6",
            "",
            "PLUGINS:"
        ])

        # Generate plugin list
        lines.extend(self._generate_plugin_list(plugin_count))

        return lines

    def _generate_buffout4_large(self,
                                formid_count: int = 100,
                                plugin_count: int = 200,
                                **kwargs) -> List[str]:
        """Generate a large Buffout 4 crash log."""
        # Start with basic structure
        lines = self._generate_buffout4_basic(formid_count=formid_count, plugin_count=plugin_count)

        # Insert additional sections for realism
        system_index = lines.index("SYSTEM SPECS:")
        additional_specs = [
            "\tRAM: DDR4-3200 32GB (2x16GB)",
            "\tSSD: NVMe PCIe 4.0 1TB",
            "\tMOBO: AMD X570 Chipset",
        ]

        for i, spec in enumerate(additional_specs):
            lines.insert(system_index + 6 + i, spec)

        return lines

    def _generate_buffout4_many_mods(self,
                                    formid_count: int = 200,
                                    plugin_count: int = 300,
                                    esl_count: int = 50,
                                    **kwargs) -> List[str]:
        """Generate a crash log with many mods (typical heavy load order)."""
        lines = self._generate_buffout4_basic(formid_count=formid_count, plugin_count=plugin_count)

        # Add ESL plugins to the list
        esl_plugins = self._generate_esl_plugins(esl_count)

        # Find the plugins section and add ESLs
        try:
            plugins_index = lines.index("PLUGINS:")
            # Insert ESL plugins after regular plugins
            lines.extend(esl_plugins)
        except ValueError:
            # If PLUGINS: not found, just append
            lines.extend(["", "PLUGINS:"] + esl_plugins)

        return lines

    def _generate_crash_logger(self, **kwargs) -> List[str]:
        """Generate a Crash Logger format crash log."""
        lines = [
            "Crash Logger SSE v1.0.0",
            "",
            "Fallout 4 v1.10.163.0",
            "",
            "EXCEPTION_ACCESS_VIOLATION (0xC0000005)",
            "Reading from 0x00000000",
            "",
            "STACK TRACE:",
        ]

        # Generate simpler call stack format
        for i in range(15):
            addr = 0x7FF66DF19300 + (i * 0x100)
            lines.append(f"\t[{i:2}] {addr:#018X} (Fallout4.exe+{addr - 0x7FF66C000000:#08X})")

        lines.extend([
            "",
            "LOADED MODULES:",
            "\tFallout4.exe",
            "\tKERNELBASE.dll",
            "\tntdll.dll",
        ])

        return lines

    def _generate_netscriptframework(self, **kwargs) -> List[str]:
        """Generate a .NET Script Framework format crash log."""
        lines = [
            ".NET Script Framework",
            "",
            "Application: Fallout 4",
            "Version: 1.10.163.0",
            "Framework: 4.0.0.0",
            "",
            "Unhandled .NET Framework exception",
            "",
            "STACK TRACE:",
        ]

        # Generate .NET-style call stack
        methods = [
            "ProcessCrash",
            "HandleException",
            "ExecuteScript",
            "UpdateGame",
            "MainLoop"
        ]

        for i, method in enumerate(methods):
            lines.append(f"\tat GameFramework.{method}() +0x{i*16:03X}")

        return lines

    def _generate_corrupted(self, **kwargs) -> List[str]:
        """Generate a corrupted/malformed crash log for error testing."""
        lines = [
            "CORRUPTED_HEADER",
            "Fallout 4 v1.10.CORRUPT",
            "",
            "INVALID_EXCEPTION_TYPE",
            "",
            "PROBABLE CALL STACK:",
            "\t[MALFORMED] 0xINVALID_ADDRESS -> FormID: NOT_A_FORMID",
            "\t[999] OVERFLOW_INDEX -> FormID: 0xGGGGGGGG",
            "",
            "MISSING_SECTION_MARKER",
            "PLUGINS:",
            "\t[XX] InvalidPlugin.INVALID",
            "\t[256] OutOfRange.esp",  # Invalid hex index
            "UNEXPECTED_EOF_MARKER"
        ]

        return lines

    def _generate_minimal(self, **kwargs) -> List[str]:
        """Generate a minimal crash log for basic testing."""
        return [
            "Fallout 4 v1.10.163",
            "Buffout 4 v1.28.6",
            "",
            "PROBABLE CALL STACK:",
            "\t[0] 0x7FF66DF19300 -> FormID: 0x00000014 (Fallout4.esm)",
            "",
            "PLUGINS:",
            "\t[00] Fallout4.esm"
        ]

    def _generate_stress_test(self,
                            formid_count: int = 5000,
                            plugin_count: int = 500,
                            **kwargs) -> List[str]:
        """Generate an extremely large crash log for stress testing."""
        lines = [
            "Fallout 4 v1.10.163",
            "Buffout 4 v1.28.6 - STRESS TEST",
            "",
            'Unhandled exception "EXCEPTION_ACCESS_VIOLATION" at 0x7FF66DF19300 Fallout4.exe+0DB9300',
            "",
            "PROBABLE CALL STACK:"
        ]

        # Generate massive call stack
        lines.extend(self._generate_call_stack(formid_count))

        lines.extend([
            "",
            "PLUGINS:"
        ])

        # Generate massive plugin list
        lines.extend(self._generate_plugin_list(plugin_count))

        return lines

    def _generate_call_stack(self, formid_count: int) -> List[str]:
        """Generate a realistic call stack with FormIDs."""
        lines = []

        for i in range(formid_count):
            # Generate realistic memory addresses
            base_addr = 0x7FF66DF19300
            addr = base_addr + (i * random.randint(0x10, 0x1000))

            # Generate FormID
            formid = self._generate_formid()

            # Occasionally add record type information
            if random.random() < 0.3:  # 30% chance
                record_type = random.choice(self.RECORD_TYPES)
                lines.append(f"\t[{i}] {addr:#018X} Fallout4.exe+{addr-0x7FF66C000000:#08X} -> {record_type} at {addr:#018X}")
            else:
                # Regular FormID entry
                plugin_name = self._get_plugin_for_formid(formid)
                lines.append(f"\t[{i}] {addr:#018X} Fallout4.exe+{addr-0x7FF66C000000:#08X} -> FormID: {formid} ({plugin_name})")

        return lines

    def _generate_plugin_list(self, plugin_count: int) -> List[str]:
        """Generate a realistic plugin list."""
        lines = []
        plugins_added = set()

        # Always include master files first
        for i, master in enumerate(self.MASTER_FILES):
            if i < plugin_count:
                lines.append(f"\t[{i:02X}] {master}")
                plugins_added.add(master)

        current_index = len(self.MASTER_FILES)

        # Add common frameworks
        for framework in self.COMMON_FRAMEWORKS:
            if current_index >= plugin_count:
                break
            if framework not in plugins_added:
                lines.append(f"\t[{current_index:02X}] {framework}")
                plugins_added.add(framework)
                current_index += 1

        # Add generated plugin names
        while current_index < plugin_count and current_index < 255:  # ESP limit
            plugin_name = self._generate_plugin_name()
            if plugin_name not in plugins_added:
                lines.append(f"\t[{current_index:02X}] {plugin_name}")
                plugins_added.add(plugin_name)
                current_index += 1

        return lines

    def _generate_esl_plugins(self, esl_count: int) -> List[str]:
        """Generate ESL (light) plugins."""
        lines = []

        for i in range(min(esl_count, 2048)):  # ESL limit
            plugin_name = self._generate_plugin_name(extension=".esl")
            lines.append(f"\t[FE:{i:03X}] {plugin_name}")

        return lines

    def _generate_formid(self) -> str:
        """Generate a realistic FormID."""
        # Different types of FormIDs based on their source
        formid_type = random.choice(["base_game", "dlc", "mod", "esl"])

        if formid_type == "base_game":
            # Base game FormIDs (00000000-00FFFFFF)
            formid = random.randint(0x00000001, 0x00FFFFFF)
        elif formid_type == "dlc":
            # DLC FormIDs (01000000-06FFFFFF for official DLCs)
            dlc_id = random.choice([0x01, 0x02, 0x03, 0x04, 0x05, 0x06])
            formid = (dlc_id << 24) | random.randint(0x000001, 0xFFFFFF)
        elif formid_type == "esl":
            # ESL FormIDs (FE000000-FEFFFFFF)
            esl_index = random.randint(0x000, 0x7FF)  # ESL index range
            local_formid = random.randint(0x001, 0xFFF)  # Local ID within ESL
            formid = 0xFE000000 | (esl_index << 12) | local_formid
        else:
            # Regular mod FormIDs
            mod_index = random.randint(0x07, 0xFD)  # Avoid reserved ranges
            formid = (mod_index << 24) | random.randint(0x000001, 0xFFFFFF)

        return f"0x{formid:08X}"

    def _get_plugin_for_formid(self, formid: str) -> str:
        """Get a realistic plugin name for a FormID."""
        formid_int = int(formid, 16)
        mod_index = (formid_int >> 24) & 0xFF

        if mod_index == 0x00:
            return "Fallout4.esm"
        elif mod_index == 0x01:
            return "DLCRobot.esm"
        elif mod_index == 0x02:
            return "DLCworkshop01.esm"
        elif mod_index == 0x03:
            return "DLCCoast.esm"
        elif mod_index == 0x04:
            return "DLCworkshop02.esm"
        elif mod_index == 0x05:
            return "DLCworkshop03.esm"
        elif mod_index == 0x06:
            return "DLCNukaWorld.esm"
        elif mod_index == 0xFE:
            return random.choice([f"ESLPlugin{random.randint(1,100):03d}.esl"])
        else:
            return self._generate_plugin_name()

    def _generate_plugin_name(self, extension: str = ".esp") -> str:
        """Generate a realistic plugin name."""
        prefixes = [
            "Sim", "Better", "Improved", "Enhanced", "More", "Super", "Ultra",
            "Realistic", "Immersive", "Advanced", "Ultimate", "Modern", "Classic"
        ]

        topics = [
            "Weapons", "Armor", "Settlements", "Graphics", "Weather", "NPCs",
            "Companions", "Quests", "Textures", "Lighting", "Combat", "Workshop",
            "Interface", "Sound", "Animation", "Dialogue", "Factions", "Creatures"
        ]

        suffixes = [
            "", "Redux", "Overhaul", "Pack", "Collection", "Mod", "Plus",
            "Extended", "Expansion", "Patch", "Fix", "Update", "Remastered"
        ]

        prefix = random.choice(prefixes)
        topic = random.choice(topics)
        suffix = random.choice(suffixes)

        if suffix:
            name = f"{prefix}{topic}{suffix}"
        else:
            name = f"{prefix}{topic}"

        return f"{name}{extension}"

    def create_crash_log_file(self,
                             log_type: CrashLogType,
                             output_path: Path,
                             **kwargs) -> Path:
        """
        Create a crash log file on disk for testing.

        Args:
            log_type: Type of crash log to generate
            output_path: Path where to write the crash log file
            **kwargs: Additional parameters for crash log generation

        Returns:
            Path to the created crash log file
        """
        crash_data = self.generate_crash_log(log_type, **kwargs)

        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, 'w', encoding='utf-8') as f:
            for line in crash_data:
                f.write(line + '\n')

        return output_path

    def get_expected_extraction_counts(self, log_type: CrashLogType, **kwargs) -> Dict[str, int]:
        """
        Get expected extraction counts for validation.

        Args:
            log_type: Type of crash log
            **kwargs: Parameters used for generation

        Returns:
            Dictionary with expected counts for FormIDs, plugins, etc.
        """
        if log_type == CrashLogType.BUFFOUT4_BASIC:
            formid_count = kwargs.get('formid_count', 20)
            plugin_count = kwargs.get('plugin_count', 50)
        elif log_type == CrashLogType.BUFFOUT4_LARGE:
            formid_count = kwargs.get('formid_count', 100)
            plugin_count = kwargs.get('plugin_count', 200)
        elif log_type == CrashLogType.BUFFOUT4_MANY_MODS:
            formid_count = kwargs.get('formid_count', 200)
            plugin_count = kwargs.get('plugin_count', 300) + kwargs.get('esl_count', 50)
        elif log_type == CrashLogType.MINIMAL:
            formid_count = 1
            plugin_count = 1
        elif log_type == CrashLogType.STRESS_TEST:
            formid_count = kwargs.get('formid_count', 5000)
            plugin_count = kwargs.get('plugin_count', 500)
        else:
            # Default estimates for other types
            formid_count = 10
            plugin_count = 10

        return {
            "expected_formids": formid_count,
            "expected_plugins": plugin_count,
            "expected_segments": 6,  # Standard Buffout 4 segments
        }
