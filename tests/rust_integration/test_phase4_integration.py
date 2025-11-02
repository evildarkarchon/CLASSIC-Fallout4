"""Integration tests for Phase 4 Rust components.

This module tests the integration and functionality of Phase 4 Rust utility
modules including constants, version parsing, resource management, XSE utilities,
and web utilities.
"""

from __future__ import annotations

import pytest

# Import factory functions
from ClassicLib.integration.factory import (
    get_constants,
    get_version_utils,
    get_resource_mgmt,
    get_xse_utils,
    get_web_utils,
)


pytestmark = [
    pytest.mark.rust,
    pytest.mark.integration,
]


class TestConstantsIntegration:
    """Tests for classic_constants module integration."""

    def test_constants_available(self):
        """Test that constants module is available."""
        constants = get_constants()
        if constants is None:
            pytest.skip("classic_constants module not available")

        # Module should have version
        assert hasattr(constants, "__version__")
        assert isinstance(constants.__version__, str)

    def test_game_id_enum(self):
        """Test GameId enumeration."""
        constants = get_constants()
        if constants is None:
            pytest.skip("classic_constants module not available")

        # Test GameId variants (use uppercase method names)
        assert hasattr(constants, "GameId")
        fallout4 = constants.GameId.Fallout4
        assert fallout4.as_str() == "Fallout4"

        fallout4vr = constants.GameId.Fallout4VR
        assert fallout4vr.as_str() == "Fallout4VR"

        skyrim = constants.GameId.Skyrim
        assert skyrim.as_str() == "Skyrim"

        starfield = constants.GameId.Starfield
        assert starfield.as_str() == "Starfield"

    def test_game_id_equality(self):
        """Test GameId equality comparison."""
        constants = get_constants()
        if constants is None:
            pytest.skip("classic_constants module not available")

        # Test equality
        fallout4_1 = constants.GameId.Fallout4
        fallout4_2 = constants.GameId.Fallout4
        assert fallout4_1 == fallout4_2

        # Test inequality
        fallout4 = constants.GameId.Fallout4
        skyrim = constants.GameId.Skyrim
        assert fallout4 != skyrim


class TestVersionUtilsIntegration:
    """Tests for classic_version module integration."""

    def test_version_utils_available(self):
        """Test that version utilities module is available."""
        version = get_version_utils()
        if version is None:
            pytest.skip("classic_version module not available")

        assert hasattr(version, "__version__")
        assert isinstance(version.__version__, str)

    def test_parse_version(self):
        """Test version parsing."""
        version = get_version_utils()
        if version is None:
            pytest.skip("classic_version module not available")

        # Parse standard version
        v = version.parse_version("1.10.163")
        assert v == (1, 10, 163)

        # Parse version with prefix
        v = version.parse_version("v2.0.1")
        assert v == (2, 0, 1)

    def test_try_parse_version(self):
        """Test optional version parsing."""
        version = get_version_utils()
        if version is None:
            pytest.skip("classic_version module not available")

        # Valid version
        v = version.try_parse_version("1.10.163")
        assert v == (1, 10, 163)

        # Invalid version
        v = version.try_parse_version("not a version")
        assert v is None

    def test_compare_versions(self):
        """Test version comparison."""
        version = get_version_utils()
        if version is None:
            pytest.skip("classic_version module not available")

        # Compare equal versions (returns 0 for equal)
        cmp = version.compare_versions((1, 10, 163), (1, 10, 163))
        assert cmp == 0

        # Compare less than (returns -1 for less)
        cmp = version.compare_versions((1, 10, 162), (1, 10, 163))
        assert cmp == -1

        # Compare greater than (returns 1 for greater)
        cmp = version.compare_versions((1, 10, 164), (1, 10, 163))
        assert cmp == 1

    def test_format_version(self):
        """Test version formatting."""
        version = get_version_utils()
        if version is None:
            pytest.skip("classic_version module not available")

        # Default format (with prefix)
        formatted = version.format_version((1, 10, 163))
        assert formatted == "v1.10.163"

        # Without prefix
        formatted = version.format_version((1, 10, 163), prefix="")
        assert formatted == "1.10.163"

        # Custom prefix
        formatted = version.format_version((1, 10, 163), prefix="version ")
        assert formatted == "version 1.10.163"


class TestResourceMgmtIntegration:
    """Tests for classic_resource module integration."""

    def test_resource_mgmt_available(self):
        """Test that resource management module is available."""
        resource = get_resource_mgmt()
        if resource is None:
            pytest.skip("classic_resource module not available")

        assert hasattr(resource, "__version__")
        assert isinstance(resource.__version__, str)

    def test_resource_type_enum(self):
        """Test ResourceType enumeration."""
        resource = get_resource_mgmt()
        if resource is None:
            pytest.skip("classic_resource module not available")

        # Test ResourceType variants
        assert hasattr(resource, "ResourceType")
        texture = resource.ResourceType.texture()
        assert texture.as_str() == "texture"

        mesh = resource.ResourceType.mesh()
        assert mesh.as_str() == "mesh"

        script = resource.ResourceType.script()
        assert script.as_str() == "script"

        plugin = resource.ResourceType.plugin()
        assert plugin.as_str() == "plugin"

    def test_detect_resource_type(self):
        """Test resource type detection."""
        resource = get_resource_mgmt()
        if resource is None:
            pytest.skip("classic_resource module not available")

        # Detect texture
        rt = resource.detect_resource_type("textures/armor.dds")
        assert rt.as_str() == "texture"

        # Detect mesh
        rt = resource.detect_resource_type("meshes/weapons/sword.nif")
        assert rt.as_str() == "mesh"

        # Detect script
        rt = resource.detect_resource_type("scripts/myquest.pex")
        assert rt.as_str() == "script"

        # Detect plugin
        rt = resource.detect_resource_type("myplugin.esp")
        assert rt.as_str() == "plugin"

    def test_is_supported_resource(self):
        """Test resource support checking."""
        resource = get_resource_mgmt()
        if resource is None:
            pytest.skip("classic_resource module not available")

        # Supported resources
        assert resource.is_supported_resource("texture.dds")
        assert resource.is_supported_resource("mesh.nif")
        assert resource.is_supported_resource("plugin.esp")

        # Unsupported resources
        assert not resource.is_supported_resource("readme.txt")
        assert not resource.is_supported_resource("document.pdf")


class TestXseUtilsIntegration:
    """Tests for classic_xse module integration."""

    def test_xse_utils_available(self):
        """Test that XSE utilities module is available."""
        xse = get_xse_utils()
        if xse is None:
            pytest.skip("classic_xse module not available")

        assert hasattr(xse, "__version__")
        assert isinstance(xse.__version__, str)

    def test_xse_type_enum(self):
        """Test XseType enumeration."""
        xse = get_xse_utils()
        if xse is None:
            pytest.skip("classic_xse module not available")

        # Test XseType variants
        assert hasattr(xse, "XseType")

        f4se = xse.XseType.f4se()
        assert f4se.as_str() == "F4SE"
        assert f4se.loader_name() == "f4se_loader.exe"
        assert f4se.dll_prefix() == "f4se_"

        f4sevr = xse.XseType.f4sevr()
        assert f4sevr.as_str() == "F4SEVR"

        skse = xse.XseType.skse()
        assert skse.as_str() == "SKSE"

        skse64 = xse.XseType.skse64()
        assert skse64.as_str() == "SKSE64"

        sksevr = xse.XseType.sksevr()
        assert sksevr.as_str() == "SKSEVR"

        sfse = xse.XseType.sfse()
        assert sfse.as_str() == "SFSE"

    def test_parse_xse_type(self):
        """Test XSE type parsing."""
        xse = get_xse_utils()
        if xse is None:
            pytest.skip("classic_xse module not available")

        # Parse valid types
        f4se = xse.parse_xse_type("f4se")
        assert f4se.as_str() == "F4SE"

        skse64 = xse.parse_xse_type("SKSE64")
        assert skse64.as_str() == "SKSE64"

        # Parse invalid type should raise
        with pytest.raises(ValueError):
            xse.parse_xse_type("invalid")

    def test_is_xse_installed(self):
        """Test XSE installation checking."""
        xse = get_xse_utils()
        if xse is None:
            pytest.skip("classic_xse module not available")

        # Test with non-existent path
        f4se = xse.XseType.f4se()
        installed = xse.is_xse_installed("C:/NonExistent", f4se)
        assert isinstance(installed, bool)

    def test_get_xse_info(self):
        """Test getting XSE information."""
        xse = get_xse_utils()
        if xse is None:
            pytest.skip("classic_xse module not available")

        # Get info for non-existent path
        f4se = xse.XseType.f4se()
        info = xse.get_xse_info("C:/NonExistent", f4se)

        assert hasattr(info, "xse_type")
        assert hasattr(info, "path")
        assert hasattr(info, "installed")

        # XSE type should match
        assert info.xse_type() == f4se

        # Path should match
        assert "NonExistent" in info.path()

        # Should not be installed
        assert not info.installed()


class TestWebUtilsIntegration:
    """Tests for classic_web module integration."""

    def test_web_utils_available(self):
        """Test that web utilities module is available."""
        web = get_web_utils()
        if web is None:
            pytest.skip("classic_web module not available")

        assert hasattr(web, "__version__")
        assert isinstance(web.__version__, str)

    def test_user_agent(self):
        """Test user agent generation."""
        web = get_web_utils()
        if web is None:
            pytest.skip("classic_web module not available")

        # Get user agent
        ua = web.get_user_agent()
        assert ua.startswith("CLASSIC/")
        assert "8.0.0" in ua

        # Get user agent with suffix
        ua = web.get_user_agent_with_suffix("Windows")
        assert "CLASSIC/" in ua
        assert "Windows" in ua

    def test_url_validation(self):
        """Test URL validation."""
        web = get_web_utils()
        if web is None:
            pytest.skip("classic_web module not available")

        # Valid URLs
        assert web.is_valid_url("https://www.nexusmods.com")
        assert web.is_valid_url("http://example.com")

        # Invalid URLs
        assert not web.is_valid_url("not a url")
        assert not web.is_valid_url("ftp://example.com")

        # Validate and get URL
        url = web.validate_url("https://www.nexusmods.com")
        assert url.startswith("https://www.nexusmods.com")

    def test_extract_domain(self):
        """Test domain extraction."""
        web = get_web_utils()
        if web is None:
            pytest.skip("classic_web module not available")

        # Extract domain from URL
        domain = web.extract_domain("https://www.nexusmods.com/fallout4/mods/123")
        assert domain == "www.nexusmods.com"

        domain = web.extract_domain("http://example.com:8080/path")
        assert domain == "example.com"

    def test_url_building(self):
        """Test URL building functions."""
        web = get_web_utils()
        if web is None:
            pytest.skip("classic_web module not available")

        # Join URL
        url = web.join_url("https://www.nexusmods.com", "fallout4/mods")
        assert "nexusmods.com" in url
        assert "fallout4/mods" in url

        # Build with query parameters
        url = web.build_url_with_query(
            "https://www.nexusmods.com/fallout4/mods",
            [("game_id", "1151"), ("adult", "false")]
        )
        assert "game_id=1151" in url
        assert "adult=false" in url

    def test_mod_site_enum(self):
        """Test ModSite enumeration."""
        web = get_web_utils()
        if web is None:
            pytest.skip("classic_web module not available")

        # Test ModSite variants
        assert hasattr(web, "ModSite")

        nexus = web.ModSite.nexus_mods()
        assert nexus.name() == "Nexus Mods"
        assert nexus.base_url() == "https://www.nexusmods.com"

        bethesda = web.ModSite.bethesda_net()
        assert bethesda.name() == "Bethesda.net"
        assert bethesda.base_url() == "https://bethesda.net"

        moddb = web.ModSite.mod_db()
        assert moddb.name() == "ModDB"
        assert moddb.base_url() == "https://www.moddb.com"

        # Test equality
        nexus2 = web.ModSite.nexus_mods()
        assert nexus == nexus2

    def test_constants(self):
        """Test module constants."""
        web = get_web_utils()
        if web is None:
            pytest.skip("classic_web module not available")

        # Check constants
        assert hasattr(web, "CLASSIC_VERSION")
        assert web.CLASSIC_VERSION == "8.0.0"

        assert hasattr(web, "USER_AGENT_PREFIX")
        assert web.USER_AGENT_PREFIX == "CLASSIC"


class TestPhase4Factory:
    """Tests for Phase 4 factory function integration."""

    def test_all_phase4_modules(self):
        """Test that all Phase 4 modules can be loaded via factory."""
        # Try to load all modules
        constants = get_constants()
        version = get_version_utils()
        resource = get_resource_mgmt()
        xse = get_xse_utils()
        web = get_web_utils()

        # Count available modules
        available_count = sum([
            constants is not None,
            version is not None,
            resource is not None,
            xse is not None,
            web is not None,
        ])

        # At least log what's available
        print(f"\nPhase 4 modules available: {available_count}/5")
        if constants:
            print(f"  - classic_constants: {constants.__version__}")
        if version:
            print(f"  - classic_version: {version.__version__}")
        if resource:
            print(f"  - classic_resource: {resource.__version__}")
        if xse:
            print(f"  - classic_xse: {xse.__version__}")
        if web:
            print(f"  - classic_web: {web.__version__}")

        # If at least one module is available, test passed
        assert available_count > 0, "At least one Phase 4 module should be available"
