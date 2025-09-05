"""
Tests to verify that the fragment-based report generation produces identical output.

This test suite ensures that the migration from mutable list-based report generation
to fragment-based composition maintains identical markdown output.
"""
# ruff: noqa: ANN001, ANN002, ANN003, RUF100, ANN201, ANN204, ANN202, ARG001, PT011, ARG002
import pytest

from ClassicLib.ScanLog.DetectMods import detect_mods_double, detect_mods_important, detect_mods_single
from ClassicLib.ScanLog.ReportComposition import ConditionalSection, ReportComposer
from ClassicLib.ScanLog.ReportFragment import ReportFragment
from ClassicLib.ScanLog.ReportGenerator import ReportGeneratorFragments


class TestFragmentMigration:
    """Test suite for fragment-based report generation migration."""

    @pytest.fixture
    def sample_plugins(self):
        """Sample plugin data for testing."""
        return {
            "ProblematicMod.esp": "[01]",
            "ConflictMod1.esp": "[02]",
            "ConflictMod2.esp": "[03]",
            "NormalMod.esp": "[04]",
        }

    @pytest.fixture
    def sample_yaml_single(self):
        """Sample YAML data for single mod detection."""
        return {
            "ProblematicMod": "This mod frequently causes crashes!",
            "AnotherBadMod": "This mod is known to be unstable.",
        }

    @pytest.fixture
    def sample_yaml_double(self):
        """Sample YAML data for conflicting mod detection."""
        return {
            "ConflictMod1 | ConflictMod2": "These mods conflict with each other!",
        }

    def test_detect_mods_single_returns_fragment(self, sample_yaml_single, sample_plugins):
        """Test that detect_mods_single now returns a ReportFragment."""
        result = detect_mods_single(sample_yaml_single, sample_plugins)

        assert isinstance(result, ReportFragment)
        assert result.has_content
        assert "[!] FOUND : [01]" in result.content[0]
        assert "This mod frequently causes crashes!" in result.content[0]

    def test_detect_mods_double_returns_fragment(self, sample_yaml_double, sample_plugins):
        """Test that detect_mods_double now returns a ReportFragment."""
        result = detect_mods_double(sample_yaml_double, sample_plugins)

        assert isinstance(result, ReportFragment)
        assert result.has_content
        assert "[!] CAUTION : Conflicting mods detected" in result.content[0]

    def test_empty_detection_returns_empty_fragment(self):
        """Test that no matches return an empty fragment."""
        result = detect_mods_single({"NoMatchMod": "Warning"}, {"OtherMod.esp": "[01]"})

        assert isinstance(result, ReportFragment)
        assert not result.has_content
        assert result.content == ()

    def test_conditional_header_only_when_content_exists(self, sample_yaml_single, sample_plugins):
        """Test that conditional headers are only added when content exists."""
        # Test with content
        with_content = ConditionalSection.with_header(lambda: detect_mods_single(sample_yaml_single, sample_plugins), "FREQUENTLY CRASH")

        assert with_content.has_content
        assert "### Checking For Mods That FREQUENTLY CRASH" in with_content.content[0]
        assert "[!] FOUND" in "".join(with_content.to_list())

        # Test without content
        without_content = ConditionalSection.with_header(
            lambda: detect_mods_single({"NoMatch": "Warning"}, sample_plugins), "FREQUENTLY CRASH"
        )

        assert not without_content.has_content
        assert without_content.content == ()

    def test_report_composer_combines_fragments(self, sample_yaml_single, sample_yaml_double, sample_plugins):
        """Test that ReportComposer correctly combines multiple fragments."""
        composer = ReportComposer()

        # Add header
        header = ReportGeneratorFragments(None).generate_header("test.log")
        composer.add(header)

        # Add conditional sections
        composer.add_conditional(lambda: detect_mods_single(sample_yaml_single, sample_plugins), "FREQUENTLY CRASH")

        composer.add_conditional(lambda: detect_mods_double(sample_yaml_double, sample_plugins), "CONFLICT (TOGETHER)")

        # Compose and convert to list
        result = composer.to_list()

        assert isinstance(result, list)
        assert "# test.log" in result[0]
        assert any("### Checking For Mods That FREQUENTLY CRASH" in line for line in result)
        assert any("### Checking For Mods That CONFLICT (TOGETHER)" in line for line in result)

    def test_fragment_composition_is_immutable(self):
        """Test that fragments are immutable and composition creates new fragments."""
        fragment1 = ReportFragment.from_lines(["Line 1\n"])
        fragment2 = ReportFragment.from_lines(["Line 2\n"])

        combined = fragment1 + fragment2

        # Original fragments should be unchanged
        assert fragment1.content == ("Line 1\n",)
        assert fragment2.content == ("Line 2\n",)

        # Combined should be a new fragment
        assert combined.content == ("Line 1\n", "Line 2\n")
        assert combined is not fragment1
        assert combined is not fragment2

    def test_detect_mods_important_fragment(self, sample_plugins):
        """Test detect_mods_important returns proper fragment."""
        yaml_important = {
            "ProblematicMod | Important Mod": "This is an important mod for stability",
        }

        result = detect_mods_important(yaml_important, sample_plugins, gpu_rival=None)

        assert isinstance(result, ReportFragment)
        # Important mods can return content even when empty
        assert "✔️ Important Mod is installed!" in "".join(result.to_list())

    def test_output_format_unchanged(self, sample_yaml_single, sample_plugins):
        """Test that the markdown output format remains unchanged."""
        fragment = detect_mods_single(sample_yaml_single, sample_plugins)
        output = "".join(fragment.to_list())

        # Verify the exact format matches the original
        assert "[!] FOUND : [01] This mod frequently causes crashes!" in output
        assert output.endswith("\n\n")  # Should have double newline at end

    @pytest.mark.parametrize(
        "check_type,expected_header",
        [
            ("FREQUENTLY CRASH", "### Checking For Mods That FREQUENTLY CRASH\n\n"),
            ("CONFLICT (TOGETHER)", "### Checking For Mods That CONFLICT (TOGETHER)\n\n"),
            ("HAVE SOLUTIONS", "### Checking For Mods That HAVE SOLUTIONS\n\n"),
        ],
    )
    def test_header_generation(self, check_type, expected_header):
        """Test that headers are generated correctly."""
        gen = ReportGeneratorFragments(None)
        header_fragment = gen.generate_mod_check_header(check_type)

        assert header_fragment.content[0] == expected_header
