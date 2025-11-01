"""
Python integration tests for Rust mod detection functions.

This module provides Python-side integration tests that mirror the comprehensive
Rust tests in classic-rust/tests/test_mod_detector.rs to ensure Python-Rust parity.

Tests cover:
- Single mod detection with pattern matching
- Mod conflict detection (double mods)
- Important mod detection with GPU compatibility
- Batch processing capabilities
- Case sensitivity and pattern matching
- Edge cases and error handling
"""

import pytest

try:
    import classic_scanlog
    detect_mods_single = classic_scanlog.detect_mods_single
    detect_mods_double = classic_scanlog.detect_mods_double
    detect_mods_important = classic_scanlog.detect_mods_important
    detect_mods_batch = classic_scanlog.detect_mods_batch
    RUST_AVAILABLE = True
except (ImportError, AttributeError):
    RUST_AVAILABLE = False


# ============================================================================
# Test Data Helpers
# ============================================================================

def create_single_mods_db():
    """Create sample YAML dictionary for single mod detection."""
    return {
        "buffout4": "Buffout 4\n    Crash logging utility for Fallout 4\n    Required for crash analysis",
        "f4se": "Fallout 4 Script Extender (F4SE)\n    Essential script extender for many mods\n    Must match game version",
        "mcm": "Mod Configuration Menu (MCM)\n    Allows configuration of many mods\n    Requires F4SE",
        "place everywhere": "Place Everywhere\n    Advanced settlement building tool\n    May cause workshop crashes if overused",
        "workshop framework": "Workshop Framework\n    Framework for settlement mods\n    Check for conflicts with other workshop mods",
        "sim settlements": "Sim Settlements 2\n    Advanced settlement automation\n    Requires Workshop Framework",
        "classic holstered": "Classic Holstered Weapons\n    Shows weapons on character\n    Known to cause animation conflicts",
        "looksmenu": "LooksMenu\n    Character appearance customization\n    Requires F4EE compatibility in Buffout4.toml",
    }


def create_sample_crashlog_plugins():
    """Create sample crash log plugins for single mod detection."""
    return {
        "Fallout4.esm": "00",
        "DLCRobot.esm": "01",
        "DLCworkshop01.esm": "02",
        "DLCCoast.esm": "03",
        "Buffout4.dll": "FF",
        "F4SE.dll": "FE",
        "MCM.esp": "04",
        "WorkshopFramework.esm": "05",
        "SimSettlements2.esp": "06",
        "LooksMenu.esp": "07",
    }


def create_double_mods_db():
    """Create sample YAML dictionary for mod conflict detection."""
    return {
        "classicholstered | weaponsmithextended": (
            "CONFLICT: Classic Holstered Weapons and Weaponsmith Extended are incompatible\n"
            "    Use patches or choose one mod\n"
        ),
        "simsettlements | placeeverywhere": (
            "CAUTION: Sim Settlements and Place Everywhere may conflict\n"
            "    Avoid using both in same settlement\n"
        ),
        "bakascrapheap | buffout4": (
            "CONFLICT: Baka ScrapHeap conflicts with Buffout 4 memory manager\n"
            "    Disable MemoryManager in Buffout4.toml\n"
        ),
        "achievements | unlimitedsurvival": (
            "CONFLICT: Achievements mod conflicts with Unlimited Survival Mode\n"
            "    Disable Achievements parameter in Buffout4.toml\n"
        ),
    }


def create_conflicting_crashlog():
    """Create crash log with conflicting mods."""
    return {
        "ClassicHolsteredWeapons.esp": "10",
        "WeaponsmithExtended.esp": "11",
        "BakaScrapHeap.dll": "FF",
        "Buffout4.dll": "FE",
    }


def create_important_mods_db():
    """Create sample YAML dictionary for important mods."""
    return {
        "f4se | Fallout 4 Script Extender": (
            "Essential for most mods\n"
            "    Download from https://f4se.silverlock.org"
        ),
        "buffout4 | Buffout 4": (
            "Crash logging utility\n"
            "    Download from Nexus Mods"
        ),
        "address library | Address Library": (
            "Required for many F4SE plugins\n"
            "    Download from Nexus Mods"
        ),
        # Note: Patterns must match actual plugin names (use underscore or no space)
        "nvidia_reflex | NVIDIA Reflex": (
            "nvidia\n"
            "    NVIDIA GPU optimization plugin"
        ),
        "amd_fsr | AMD FidelityFX": (
            "amd\n"
            "    AMD GPU optimization plugin"
        ),
    }


def create_xse_modules():
    """Create XSE modules set."""
    return {
        "f4se_loader.exe",
        "f4se_1_10_163.dll",
        "f4se_steam_loader.dll",
        "buffout4.dll",
        "mcm.dll",
    }


# ============================================================================
# Single Mod Detection Tests
# ============================================================================

@pytest.mark.rust
@pytest.mark.skipif(not RUST_AVAILABLE, reason="Rust mod detector not available")
class TestDetectModsSingle:
    """Test single mod detection."""

    def test_detect_mods_single_basic(self):
        """Test basic single mod detection."""
        yaml_dict = create_single_mods_db()
        crashlog_plugins = create_sample_crashlog_plugins()

        result = detect_mods_single(yaml_dict, crashlog_plugins)

        # Should detect multiple mods
        assert len(result) > 0

        # Should contain Buffout 4
        assert any("Buffout 4" in line for line in result)

        # Should contain F4SE
        assert any("F4SE" in line for line in result)

        # Should contain MCM
        assert any("MCM" in line for line in result)

        # Should have FOUND headers
        assert any("**[!] FOUND :" in line for line in result)

    def test_detect_mods_single_case_insensitive(self):
        """Test case-insensitive pattern matching."""
        yaml_dict = {
            "buffout4": "Buffout 4\n    Test mod",
        }
        crashlog_plugins = {
            # Different case variations
            "BUFFOUT4.DLL": "FF",
            "BuFfOuT4.dll": "FE",
        }

        result = detect_mods_single(yaml_dict, crashlog_plugins)

        # Should detect despite case differences
        assert len(result) > 0
        assert any("Buffout 4" in line for line in result)

    def test_detect_mods_single_empty_crashlog(self):
        """Test with empty crash log."""
        yaml_dict = create_single_mods_db()
        crashlog_plugins = {}

        result = detect_mods_single(yaml_dict, crashlog_plugins)

        # Should return empty result
        assert len(result) == 0

    def test_detect_mods_single_empty_yaml(self):
        """Test with empty YAML dictionary."""
        yaml_dict = {}
        crashlog_plugins = create_sample_crashlog_plugins()

        result = detect_mods_single(yaml_dict, crashlog_plugins)

        # Should return empty result
        assert len(result) == 0

    def test_detect_mods_single_missing_warning(self):
        """Test error handling with missing warning text."""
        yaml_dict = {
            "testmod": "",  # Empty warning should cause error
        }
        crashlog_plugins = {
            "testmod.esp": "01",
        }

        # Should raise error for missing warning
        with pytest.raises(Exception) as exc_info:
            detect_mods_single(yaml_dict, crashlog_plugins)

        assert "no warning" in str(exc_info.value).lower()

    def test_detect_mods_single_formatting(self):
        """Test output formatting."""
        yaml_dict = {
            "testmod": (
                "Test Mod Name\n"
                "    First description line\n"
                "    Second description line\n"
                "\n"
                "    Third line after blank"
            ),
        }
        crashlog_plugins = {
            "TestMod.esp": "42",
        }

        result = detect_mods_single(yaml_dict, crashlog_plugins)

        # Check formatting
        assert any("**[!] FOUND : [42] Test Mod Name**" in line for line in result)
        assert any("First description line" in line for line in result)
        assert any("Second description line" in line for line in result)


# ============================================================================
# Double Mod Detection (Conflicts) Tests
# ============================================================================

@pytest.mark.rust
@pytest.mark.skipif(not RUST_AVAILABLE, reason="Rust mod detector not available")
class TestDetectModsDouble:
    """Test mod conflict detection."""

    def test_detect_mods_double_basic(self):
        """Test basic conflict detection."""
        yaml_dict = create_double_mods_db()
        crashlog_plugins = create_conflicting_crashlog()

        result = detect_mods_double(yaml_dict, crashlog_plugins)

        # Should detect conflicts
        assert len(result) > 0

        # Should contain caution message
        assert any("[!] CAUTION" in line for line in result)

        # Should mention the specific conflicts
        assert any(
            "Classic Holstered" in line or "Baka ScrapHeap" in line
            for line in result
        )

    def test_detect_mods_double_no_conflicts(self):
        """Test with no conflicts present."""
        yaml_dict = create_double_mods_db()
        crashlog_plugins = {
            # Only one mod from each pair
            "ClassicHolsteredWeapons.esp": "10",
            "Buffout4.dll": "FE",
        }

        result = detect_mods_double(yaml_dict, crashlog_plugins)

        # Should return empty (no conflicts detected)
        assert len(result) == 0

    def test_detect_mods_double_case_insensitive(self):
        """Test case-insensitive conflict detection."""
        yaml_dict = {
            "mod1 | mod2": "CONFLICT: Mod1 and Mod2 are incompatible\n",
        }
        crashlog_plugins = {
            "MOD1.ESP": "01",
            "mod2.esp": "02",
        }

        result = detect_mods_double(yaml_dict, crashlog_plugins)

        # Should detect conflict despite case differences
        assert len(result) > 0
        assert any("CONFLICT" in line for line in result)

    def test_detect_mods_double_empty_yaml(self):
        """Test with empty YAML dictionary."""
        yaml_dict = {}
        crashlog_plugins = create_conflicting_crashlog()

        result = detect_mods_double(yaml_dict, crashlog_plugins)

        assert len(result) == 0

    def test_detect_mods_double_multiple_conflicts(self):
        """Test detection of multiple conflicts."""
        yaml_dict = create_double_mods_db()
        crashlog_plugins = {
            # Add both pairs
            "ClassicHolsteredWeapons.esp": "10",
            "WeaponsmithExtended.esp": "11",
            "BakaScrapHeap.dll": "FF",
            "Buffout4.dll": "FE",
        }

        result = detect_mods_double(yaml_dict, crashlog_plugins)

        # Should detect multiple conflicts
        caution_count = sum(1 for line in result if "[!] CAUTION" in line)
        assert caution_count >= 2


# ============================================================================
# Important Mod Detection Tests
# ============================================================================

@pytest.mark.rust
@pytest.mark.skipif(not RUST_AVAILABLE, reason="Rust mod detector not available")
class TestDetectModsImportant:
    """Test important mod detection with GPU compatibility."""

    def test_detect_mods_important_basic(self):
        """Test basic important mod detection."""
        yaml_dict = create_important_mods_db()
        crashlog_plugins = {
            "F4SE.dll": "FF",
            "Buffout4.dll": "FE",
        }
        xse_modules = create_xse_modules()

        result = detect_mods_important(yaml_dict, crashlog_plugins, None, xse_modules)

        # Should contain header
        assert any("Checking for Important Mods" in line for line in result)

        # Should show installed mods
        assert any("✔️" in line for line in result)
        assert any("Fallout 4 Script Extender" in line for line in result)
        assert any("Buffout 4" in line for line in result)

    def test_detect_mods_important_missing_mods(self):
        """Test with missing important mods."""
        yaml_dict = create_important_mods_db()
        crashlog_plugins = {}  # Empty - no mods installed
        xse_modules = set()

        # Note: gpu_rival must be Some to show missing mods
        # Passing "amd" means user has NVIDIA, so non-GPU and NVIDIA mods will show as missing
        result = detect_mods_important(yaml_dict, crashlog_plugins, "amd", xse_modules)

        # Should show missing mods
        assert any("❌" in line for line in result)
        assert any("not installed" in line for line in result)

    def test_detect_mods_important_gpu_compatibility_nvidia(self):
        """Test GPU compatibility warning for NVIDIA."""
        yaml_dict = create_important_mods_db()
        crashlog_plugins = {
            # User has AMD GPU but NVIDIA Reflex installed
            # gpu_rival = "nvidia" means user doesn't have NVIDIA (has AMD)
            "NVIDIA_Reflex.dll": "FF",
        }
        xse_modules = set()

        result = detect_mods_important(
            yaml_dict,
            crashlog_plugins,
            "nvidia",  # Rival is NVIDIA (user has AMD)
            xse_modules
        )

        # Should warn about GPU mismatch
        assert any("❓" in line for line in result)
        assert any("DON'T HAVE AN NVIDIA GPU" in line for line in result)

    def test_detect_mods_important_gpu_compatibility_amd(self):
        """Test GPU compatibility warning for AMD."""
        yaml_dict = create_important_mods_db()
        crashlog_plugins = {
            # User has NVIDIA GPU but AMD FSR installed
            # gpu_rival = "amd" means user doesn't have AMD (has NVIDIA)
            "AMD_FSR.dll": "FF",
        }
        xse_modules = set()

        result = detect_mods_important(
            yaml_dict,
            crashlog_plugins,
            "amd",  # Rival is AMD (user has NVIDIA)
            xse_modules
        )

        # Should warn about GPU mismatch
        assert any("❓" in line for line in result)
        assert any("DON'T HAVE AN AMD GPU" in line for line in result)

    def test_detect_mods_important_gpu_compatibility_correct(self):
        """Test correct GPU compatibility."""
        yaml_dict = create_important_mods_db()
        crashlog_plugins = {
            # User has NVIDIA GPU with NVIDIA Reflex
            # gpu_rival = "amd" means user doesn't have AMD (has NVIDIA)
            "NVIDIA_Reflex.dll": "FF",
        }
        xse_modules = set()

        result = detect_mods_important(
            yaml_dict,
            crashlog_plugins,
            "amd",  # Rival is AMD (user has NVIDIA)
            xse_modules
        )

        # Should show as correctly installed
        assert any("✔️" in line for line in result)
        assert any("NVIDIA Reflex" in line for line in result)

    def test_detect_mods_important_xse_modules(self):
        """Test detection via XSE modules."""
        yaml_dict = create_important_mods_db()
        crashlog_plugins = {}

        # XSE modules contain F4SE DLLs
        xse_modules = {
            "f4se_1_10_163.dll",
            "buffout4.dll",
        }

        result = detect_mods_important(yaml_dict, crashlog_plugins, None, xse_modules)

        # Should detect mods from XSE modules
        assert any("✔️" in line for line in result)

    def test_detect_mods_important_empty_yaml(self):
        """Test with empty YAML dictionary."""
        yaml_dict = {}
        crashlog_plugins = create_sample_crashlog_plugins()
        xse_modules = create_xse_modules()

        result = detect_mods_important(yaml_dict, crashlog_plugins, None, xse_modules)

        # Should only contain header
        assert len(result) == 1
        assert "Checking for Important Mods" in result[0]


# ============================================================================
# Batch Processing Tests
# ============================================================================

@pytest.mark.rust
@pytest.mark.skipif(not RUST_AVAILABLE, reason="Rust mod detector not available")
class TestDetectModsBatch:
    """Test batch processing of mod detection."""

    def test_detect_mods_batch_basic(self):
        """Test basic batch processing."""
        yaml_dict = create_single_mods_db()
        crashlog_list = [
            create_sample_crashlog_plugins(),
            create_conflicting_crashlog(),
            {},  # Empty crash log
        ]

        results = detect_mods_batch(yaml_dict, crashlog_list)

        assert len(results) == 3

        # First crash log should have detections
        assert len(results[0]) > 0

        # Second crash log should have detections
        assert len(results[1]) > 0

        # Third crash log (empty) should have no detections
        assert len(results[2]) == 0

    def test_detect_mods_batch_parallel_consistency(self):
        """Test that parallel batch processing is consistent."""
        yaml_dict = create_single_mods_db()
        crashlog = create_sample_crashlog_plugins()

        # Create identical crash logs
        crashlog_list = [crashlog.copy() for _ in range(10)]

        results = detect_mods_batch(yaml_dict, crashlog_list)

        # All results should have the same content (order may vary due to HashMap iteration)
        assert len(results) == 10

        first_result = results[0]
        for result in results[1:]:
            # Check same length
            assert len(result) == len(first_result)

            # Check same content (as sorted sets)
            sorted_result = sorted(result)
            sorted_first = sorted(first_result)

            assert sorted_result == sorted_first

    def test_detect_mods_batch_empty_list(self):
        """Test with empty crash log list."""
        yaml_dict = create_single_mods_db()
        crashlog_list = []

        results = detect_mods_batch(yaml_dict, crashlog_list)

        assert len(results) == 0

    def test_detect_mods_batch_empty_yaml(self):
        """Test batch with empty YAML dictionary."""
        yaml_dict = {}
        crashlog_list = [
            create_sample_crashlog_plugins(),
            create_conflicting_crashlog(),
        ]

        results = detect_mods_batch(yaml_dict, crashlog_list)

        # Should return empty results for each crash log
        assert len(results) == 2
        assert all(len(r) == 0 for r in results)

    def test_detect_mods_batch_error_propagation(self):
        """Test that errors are handled gracefully in batch processing.

        The Rust implementation logs errors to stderr and continues processing
        instead of raising exceptions, which is better for batch operations.

        Note: Rust writes directly to stderr, bypassing Python's capsys capture,
        so we only verify the function doesn't crash and returns appropriate results.
        """
        yaml_dict = {
            "badmod": "",  # Empty warning will cause error
        }
        crashlog = {
            "badmod.esp": "01",
        }
        crashlog_list = [crashlog]

        # Should handle error gracefully (not raise exception, return empty result)
        results = detect_mods_batch(yaml_dict, crashlog_list)

        # Should return empty result for the failed entry (error handled gracefully)
        assert len(results) == 1
        assert len(results[0]) == 0


# ============================================================================
# Edge Cases and Error Handling Tests
# ============================================================================

@pytest.mark.rust
@pytest.mark.skipif(not RUST_AVAILABLE, reason="Rust mod detector not available")
class TestEdgeCases:
    """Test edge cases and special scenarios."""

    def test_special_characters_in_mod_names(self):
        """Test mod names with special characters."""
        yaml_dict = {
            "mod (special)": "Special Mod\n    Has special characters",
        }
        crashlog_plugins = {
            "Mod (Special).esp": "01",
        }

        result = detect_mods_single(yaml_dict, crashlog_plugins)

        # Should handle special characters
        assert len(result) > 0
        assert any("Special Mod" in line for line in result)

    def test_unicode_in_mod_names(self):
        """Test mod names with unicode characters."""
        yaml_dict = {
            "модификация": "Unicode Mod\n    Supports unicode",  # Russian "modification"
        }
        crashlog_plugins = {
            "модификация.esp": "01",
        }

        result = detect_mods_single(yaml_dict, crashlog_plugins)

        # Should handle unicode
        assert len(result) > 0

    def test_very_long_mod_names(self):
        """Test with very long mod names."""
        long_name = "a" * 1000
        yaml_dict = {
            long_name: "Long Name Mod\n    Very long name",
        }
        crashlog_plugins = {
            f"{long_name}.esp": "01",
        }

        result = detect_mods_single(yaml_dict, crashlog_plugins)

        # Should handle very long names
        assert len(result) > 0

    def test_plugin_id_variations(self):
        """Test various plugin ID formats."""
        yaml_dict = {
            "testmod": "Test Mod\n    Test",
        }
        crashlog_plugins = {
            # Various plugin ID formats
            "TestMod1.esp": "00",
            "TestMod2.esp": "FF",
            "TestMod3.esp": "FE:001",
            "TestMod4.esp": "FE:ABC",
        }

        result = detect_mods_single(yaml_dict, crashlog_plugins)

        # Should handle all plugin ID formats
        assert len(result) > 0

        # Should only match once (first occurrence)
        found_count = sum(1 for line in result if "**[!] FOUND :" in line)
        assert found_count == 1

    def test_malformed_warning_text(self):
        """Test with malformed warning text."""
        yaml_dict = {
            # Warning with no newlines
            "mod1": "Single line warning without newline",
            # Warning with only newlines
            "mod2": "\n\n\n",
        }
        crashlog_plugins = {
            "Mod1.esp": "01",
            "Mod2.esp": "02",
        }

        result = detect_mods_single(yaml_dict, crashlog_plugins)

        # Should handle malformed warnings gracefully
        assert len(result) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
