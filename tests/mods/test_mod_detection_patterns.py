"""Test mod detection patterns with mock mod structures.

This module tests mod detection logic using synthetic data based on
real crash log patterns observed in actual Fallout 4 logs.
"""

import random

import pytest

# Mark all tests in this module
pytestmark = [pytest.mark.unit]


class SyntheticModGenerator:
    """Generate synthetic mod data based on real patterns."""

    @staticmethod
    def generate_plugin_entry(index: int, is_light: bool = False) -> str:
        """Generate a plugin entry like those in real crash logs.

        Examples from real logs:
        [FE:104] [SS2 Addon] BloodMoonRaiders.esp
        [FE:105] [SS2] BBVault 88.esp
        """
        if is_light:
            # Light plugin format [FE:XXX]
            hex_index = f"FE:{index:03X}"
        else:
            # Regular plugin [XX]
            hex_index = f"{index:02X}"

        # Generate realistic mod names based on patterns seen
        prefixes = ["SS2", "SS2 Addon", "SS2-", "PRP", "ELFX", "NAC", "PACE", "PANPC"]
        names = [
            "Settlement_Pack", "Faction_Pack", "City_Plan", "Patch", "Fix",
            "Overhaul", "Textures", "Sounds", "Animations", "Weapons"
        ]

        prefix = random.choice(prefixes) if random.random() > 0.3 else ""
        name = random.choice(names)
        suffix = random.choice(["", "_v2", "_Final", "_Tweaks", "_Compatibility"])

        if prefix:
            plugin_name = f"[{prefix}] {name}{suffix}.esp"
        else:
            plugin_name = f"{name}{suffix}.esp"

        return f"[{hex_index}] {plugin_name}"

    @staticmethod
    def generate_stack_trace_entry(address: int, dll_name: str = "Fallout4.exe") -> str:
        """Generate stack trace entries like in real crash logs.

        Example from real log:
        [0] 0x7FF6EF4C3512 Fallout4.exe+0733512 -> 703355+0x72
        """
        base_address = 0x7FF600000000 + random.randint(0, 0x10000000)
        offset = random.randint(0x100000, 0x2000000)
        function_id = random.randint(100000, 999999)
        function_offset = random.randint(0x0, 0xFF)

        return f"[{address:2d}] 0x{base_address + offset:016X} {dll_name}+{offset:07X} -> {function_id}+0x{function_offset:X}"

    @staticmethod
    def generate_formid_reference(plugin_index: str, local_id: int) -> str:
        """Generate FormID reference as it appears in logs."""
        # FormIDs appear in memory dumps, not explicitly labeled
        # But we can generate the hex pattern
        if plugin_index.startswith("FE"):
            # Light plugin FormID
            return f"FE{local_id:06X}"
        # Regular plugin FormID
        return f"{plugin_index}{local_id:06X}"

    @staticmethod
    def generate_ba2_reference(mod_name: str) -> str:
        """Generate BA2 archive reference as seen in logs.

        Example: "WCLINS_PRP_Patch - Main.ba2"
        """
        archive_types = ["Main", "Textures", "Meshes", "Sounds", "Voices", "Misc"]
        archive_type = random.choice(archive_types)
        return f"{mod_name} - {archive_type}.ba2"


class TestModDetectionPatterns:
    """Test mod detection with realistic patterns."""

    def test_plugin_list_parsing(self):
        """Test parsing of plugin list from crash log."""
        from ClassicLib.ScanLog.Parser import parse_plugin_list

        generator = SyntheticModGenerator()

        # Generate synthetic plugin list like in real logs
        plugin_lines = []

        # Add base game plugins
        plugin_lines.append("[00] Fallout4.esm")
        plugin_lines.append("[01] DLCRobot.esm")
        plugin_lines.append("[02] DLCworkshop01.esm")

        # Add regular plugins
        for i in range(3, 50):
            plugin_lines.append(f"[{i:02X}] SyntheticMod_{i}.esp")

        # Add light plugins (FE format)
        for i in range(0x050):
            plugin_lines.append(generator.generate_plugin_entry(i, is_light=True))

        # Parse the list
        plugin_text = "\n".join(plugin_lines)
        parsed = parse_plugin_list(plugin_text)

        # Verify parsing
        assert len(parsed) > 0
        assert parsed[0]["index"] == "00"
        assert parsed[0]["name"] == "Fallout4.esm"

        # Check light plugin parsing
        light_plugins = [p for p in parsed if p["index"].startswith("FE:")]
        assert len(light_plugins) == 0x050

    def test_mod_conflict_detection_from_log(self):
        """Test detecting mod conflicts from crash log data."""
        from ClassicLib.ScanLog.ModAnalyzer import detect_conflicts

        # Create synthetic crash scenario with conflicting mods
        log_data = {
            "plugins": [
                {"index": "03", "name": "ModA.esp"},
                {"index": "04", "name": "ModB.esp"},
                {"index": "FE:001", "name": "PatchA.esp"},
            ],
            "stack_trace": [
                "0x7FF6EF4C3512 Fallout4.exe+0733512",
                "0x7FF6EF4C145E ModA.esp+000145E",  # ModA in stack
                "0x7FF6EEF11959 ModB.esp+0011959",  # ModB also in stack
            ]
        }

        conflicts = detect_conflicts(log_data)

        # Should detect potential conflict between ModA and ModB
        assert len(conflicts) > 0
        assert any("ModA" in str(c) and "ModB" in str(c) for c in conflicts)

    def test_light_plugin_formid_validation(self):
        """Test validation of light plugin FormID ranges."""
        from ClassicLib.ScanLog.FormIDAnalyzer import validate_light_plugin_formid

        generator = SyntheticModGenerator()

        # Valid light plugin FormIDs (FE000800-FE000FFF)
        valid_formids = [
            "FE000800",  # Minimum valid
            "FE000900",
            "FE000ABC",
            "FE000FFF",  # Maximum valid
        ]

        for formid in valid_formids:
            assert validate_light_plugin_formid(formid) == True

        # Invalid light plugin FormIDs
        invalid_formids = [
            "FE000000",  # Below range
            "FE001000",  # Above range
            "FE00FFFF",  # Way above range
            "FF000800",  # Wrong prefix
        ]

        for formid in invalid_formids:
            assert validate_light_plugin_formid(formid) == False

    def test_ba2_archive_detection(self):
        """Test detection of BA2 archives in crash logs."""
        from ClassicLib.ScanLog.Parser import find_ba2_references

        generator = SyntheticModGenerator()

        # Create log content with BA2 references like in real logs
        log_content = f"""
        Loading archive: Fallout4 - Main.ba2
        Loading archive: DLCRobot - Main.ba2
        Loading archive: {generator.generate_ba2_reference("SS2_Settlement")}
        Loading archive: {generator.generate_ba2_reference("PRP")}
        Error loading: {generator.generate_ba2_reference("CorruptedMod")}
        """

        ba2_files = find_ba2_references(log_content)

        assert len(ba2_files) >= 4
        assert any("Fallout4 - Main.ba2" in f for f in ba2_files)
        assert any("SS2_Settlement" in f for f in ba2_files)

    def test_stack_trace_mod_identification(self):
        """Test identifying mods from stack trace addresses."""
        from ClassicLib.ScanLog.StackAnalyzer import identify_mods_in_stack

        generator = SyntheticModGenerator()

        # Generate synthetic stack trace
        stack_lines = []
        for i in range(10):
            if i < 3:
                # Base game addresses
                stack_lines.append(generator.generate_stack_trace_entry(i, "Fallout4.exe"))
            elif i < 5:
                # F4SE addresses
                stack_lines.append(generator.generate_stack_trace_entry(i, "f4se_1_10_163.dll"))
            else:
                # Mod DLL addresses
                mod_dlls = ["Buffout4.dll", "HighFPSPhysicsFix.dll", "BakaScrapHeap.dll"]
                stack_lines.append(generator.generate_stack_trace_entry(i, random.choice(mod_dlls)))

        stack_text = "\n".join(stack_lines)
        identified_mods = identify_mods_in_stack(stack_text)

        assert "Fallout4.exe" in identified_mods
        assert "f4se_1_10_163.dll" in identified_mods
        assert any(mod in identified_mods for mod in ["Buffout4.dll", "HighFPSPhysicsFix.dll"])

    def test_plugin_load_order_validation(self):
        """Test validation of plugin load order."""
        from ClassicLib.ScanLog.LoadOrderValidator import validate_load_order

        # Create realistic load order
        load_order = [
            {"index": "00", "name": "Fallout4.esm", "type": "master"},
            {"index": "01", "name": "DLCRobot.esm", "type": "master"},
            {"index": "02", "name": "DLCworkshop01.esm", "type": "master"},
            {"index": "03", "name": "RegularMod.esp", "type": "plugin"},
            {"index": "FE:000", "name": "LightPlugin.esl", "type": "light"},
            {"index": "04", "name": "Patch.esp", "type": "plugin"},
        ]

        issues = validate_load_order(load_order)

        # Should pass basic validation
        assert len(issues) == 0 or all("warning" in i.lower() for i in issues)

        # Test invalid order (ESP before ESM)
        invalid_order = [
            {"index": "00", "name": "RegularMod.esp", "type": "plugin"},
            {"index": "01", "name": "Fallout4.esm", "type": "master"},
        ]

        issues = validate_load_order(invalid_order)
        assert len(issues) > 0
        assert any("master" in i.lower() for i in issues)

    def test_mod_version_detection(self):
        """Test detection of mod versions from naming patterns."""
        from ClassicLib.ScanLog.ModVersionDetector import extract_version

        test_cases = [
            ("SS2_v3.0.0.esp", "3.0.0"),
            ("PRP_2.0.esp", "2.0"),
            ("ModName_v1.2.3_Final.esp", "1.2.3"),
            ("SimpleModNoVersion.esp", None),
            ("[FE:001] SS2_Addon_v2.1.esp", "2.1"),
        ]

        for mod_name, expected_version in test_cases:
            detected = extract_version(mod_name)
            assert detected == expected_version

    def test_ss2_mod_family_detection(self):
        """Test detection of Sim Settlements 2 mod family."""
        from ClassicLib.ScanLog.ModFamilyDetector import detect_mod_families

        # Plugin list with SS2 mods like in real logs
        plugins = [
            "[03] SS2.esm",
            "[04] SS2_XPAC_Chapter2.esm",
            "[FE:001] SS2_Addon_ShazbotsCots.esp",
            "[FE:002] SS2-AUR-HangmansAlleyCityPlan.esp",
            "[FE:003] SS2_RobotMod.esp",
            "[05] UnrelatedMod.esp",
            "[FE:004] SS2_XDI Patch.esp",
        ]

        families = detect_mod_families(plugins)

        assert "SS2" in families
        assert len(families["SS2"]) >= 6
        assert all("SS2" in mod for mod in families["SS2"])

    def test_prp_compatibility_detection(self):
        """Test detection of PRP (Previsibines Repair Pack) compatibility."""
        from ClassicLib.ScanLog.PRPCompatibilityChecker import check_prp_compatibility

        # Plugins with PRP patches like in real logs
        plugins = [
            "[FE:121] PRP.esp",
            "[FE:125] PRP-Compat-JSRS-Regions.esp",
            "[FE:12A] PRP-Compat-VNW-CR.esp",
            "[FE:12B] PRP-Compat-NWR-CR.esp",
            "[05] SomeSettlementMod.esp",  # Might need PRP patch
        ]

        compatibility = check_prp_compatibility(plugins)

        assert compatibility["has_prp"] == True
        assert len(compatibility["patches"]) >= 3
        assert compatibility["potential_conflicts"] is not None

    def test_memory_address_pattern_extraction(self):
        """Test extraction of memory address patterns from crash."""
        from ClassicLib.ScanLog.MemoryAnalyzer import extract_address_patterns

        # Real crash log memory section
        memory_dump = """
        RAX 0x463FBF           (size_t)
        RCX 0x22FC9E18080      (void*)
        RDX 0x13EE6            (size_t)
        RBX 0x80ECFDFA90       (void*)
        RSP 0x80ECFDF940       (void*)
        [RSP+58 ] 0x7FF6EF4C145E     (void* -> Fallout4.exe+073145E)
        [RSP+60 ] 0x2302DDAB040      (BSGeometrySegmentData*)
        """

        patterns = extract_address_patterns(memory_dump)

        assert len(patterns["registers"]) >= 5
        assert len(patterns["stack"]) >= 2
        assert patterns["registers"]["RAX"] == 0x463FBF
        assert "Fallout4.exe" in patterns["modules"]

    def test_crash_cause_inference(self):
        """Test inference of crash cause from patterns."""
        from ClassicLib.ScanLog.CrashAnalyzer import infer_crash_cause

        # Synthetic crash with null pointer pattern
        crash_data = {
            "exception": "EXCEPTION_ACCESS_VIOLATION",
            "address": "0x00000000",
            "registers": {"RAX": 0x0, "RCX": 0x0},
            "last_plugin": "ProblematicMod.esp",
        }

        cause = infer_crash_cause(crash_data)

        assert "null pointer" in cause.lower()
        assert "ProblematicMod" in cause

    def test_buffout4_log_format(self):
        """Test parsing of Buffout 4 specific log format."""
        from ClassicLib.ScanLog.Buffout4Parser import parse_buffout_log

        # Buffout 4 header from real log
        buffout_header = """
        Fallout 4 v1.10.163
        Buffout 4 v1.28.6

        Unhandled exception "EXCEPTION_ACCESS_VIOLATION" at 0x7FF6EF4C3512 Fallout4.exe+0733512
        """

        parsed = parse_buffout_log(buffout_header)

        assert parsed["game_version"] == "1.10.163"
        assert parsed["buffout_version"] == "1.28.6"
        assert parsed["exception_type"] == "EXCEPTION_ACCESS_VIOLATION"
        assert parsed["crash_address"] == "0x7FF6EF4C3512"

    def test_mod_dependency_chain(self):
        """Test building mod dependency chains."""
        from ClassicLib.ScanLog.DependencyAnalyzer import build_dependency_chain

        # Mods with dependencies
        mod_data = {
            "PatchMod.esp": ["BaseGame.esm", "RequiredMod.esp"],
            "RequiredMod.esp": ["BaseGame.esm"],
            "BaseGame.esm": [],
            "OptionalAddon.esp": ["BaseGame.esm", "PatchMod.esp"],
        }

        chain = build_dependency_chain("OptionalAddon.esp", mod_data)

        assert len(chain) == 4
        assert chain[0] == "BaseGame.esm"  # Root dependency
        assert chain[-1] == "OptionalAddon.esp"  # Target mod