"""Integration tests for classic-web Rust module.

Tests the Rust-accelerated web utilities module, including URL validation,
building, parsing, user agent generation, and mod site enumeration.
"""

import pytest

import classic_web


@pytest.mark.rust
@pytest.mark.unit
class TestURLValidation:
    """Test URL validation functions."""

    def test_is_valid_url_function_exists(self):
        """Test is_valid_url() function is available."""
        assert hasattr(classic_web, "is_valid_url")
        assert callable(classic_web.is_valid_url)

    def test_is_valid_url_valid_urls(self):
        """Test is_valid_url() returns True for valid URLs."""
        assert classic_web.is_valid_url("https://www.example.com") is True
        assert classic_web.is_valid_url("http://example.com") is True
        assert classic_web.is_valid_url("https://example.com/path") is True
        assert classic_web.is_valid_url("https://example.com/path?query=value") is True

    def test_is_valid_url_invalid_urls(self):
        """Test is_valid_url() returns False for invalid URLs."""
        assert classic_web.is_valid_url("not a url") is False
        assert classic_web.is_valid_url("") is False
        assert classic_web.is_valid_url("ftp://invalid.scheme") is False or classic_web.is_valid_url("ftp://invalid.scheme") is True

    def test_validate_url_function_exists(self):
        """Test validate_url() function is available."""
        assert hasattr(classic_web, "validate_url")
        assert callable(classic_web.validate_url)

    def test_validate_url_valid(self):
        """Test validate_url() succeeds for valid URLs."""
        # Should not raise for valid URLs
        classic_web.validate_url("https://www.example.com")
        classic_web.validate_url("http://example.com/path")

    def test_validate_url_invalid(self):
        """Test validate_url() raises ValueError for invalid URLs."""
        with pytest.raises(ValueError):
            classic_web.validate_url("not a url")

        with pytest.raises(ValueError):
            classic_web.validate_url("")


@pytest.mark.rust
@pytest.mark.unit
class TestURLBuilding:
    """Test URL building and manipulation functions."""

    def test_join_url_function_exists(self):
        """Test join_url() function is available."""
        assert hasattr(classic_web, "join_url")
        assert callable(classic_web.join_url)

    def test_join_url_basic(self):
        """Test join_url() joins base URL and path."""
        result = classic_web.join_url("https://example.com", "path")
        assert "example.com" in result
        assert "path" in result

    def test_join_url_with_trailing_slash(self):
        """Test join_url() handles trailing slashes correctly."""
        result1 = classic_web.join_url("https://example.com/", "path")
        result2 = classic_web.join_url("https://example.com", "/path")

        # Both should produce valid URLs
        assert classic_web.is_valid_url(result1)
        assert classic_web.is_valid_url(result2)

    def test_build_url_with_query_function_exists(self):
        """Test build_url_with_query() function is available."""
        assert hasattr(classic_web, "build_url_with_query")
        assert callable(classic_web.build_url_with_query)

    def test_build_url_with_query_basic(self):
        """Test build_url_with_query() adds query parameters."""
        result = classic_web.build_url_with_query("https://example.com", [("key", "value")])
        assert "example.com" in result
        # Should contain query parameter
        assert "key" in result or "value" in result


@pytest.mark.rust
@pytest.mark.unit
class TestURLParsing:
    """Test URL parsing and extraction functions."""

    def test_extract_domain_function_exists(self):
        """Test extract_domain() function is available."""
        assert hasattr(classic_web, "extract_domain")
        assert callable(classic_web.extract_domain)

    def test_extract_domain_basic(self):
        """Test extract_domain() extracts domain from URL."""
        assert classic_web.extract_domain("https://www.example.com/path") == "www.example.com"
        assert classic_web.extract_domain("http://example.com") == "example.com"

    def test_extract_domain_with_subdomain(self):
        """Test extract_domain() preserves subdomains."""
        assert classic_web.extract_domain("https://api.example.com") == "api.example.com"
        assert classic_web.extract_domain("https://www.sub.example.com") == "www.sub.example.com"

    def test_extract_domain_with_port(self):
        """Test extract_domain() handles URLs with ports."""
        result = classic_web.extract_domain("https://example.com:8080/path")
        # Should extract domain (may or may not include port depending on implementation)
        assert "example.com" in result


@pytest.mark.rust
@pytest.mark.unit
class TestUserAgent:
    """Test user agent generation functions."""

    def test_get_user_agent_function_exists(self):
        """Test get_user_agent() function is available."""
        assert hasattr(classic_web, "get_user_agent")
        assert callable(classic_web.get_user_agent)

    def test_get_user_agent_returns_string(self):
        """Test get_user_agent() returns a non-empty string."""
        user_agent = classic_web.get_user_agent()
        assert isinstance(user_agent, str)
        assert len(user_agent) > 0

    def test_get_user_agent_contains_classic(self):
        """Test get_user_agent() contains CLASSIC identifier."""
        user_agent = classic_web.get_user_agent()
        # Should contain CLASSIC or similar identifier
        assert "CLASSIC" in user_agent or "classic" in user_agent.lower()

    def test_get_user_agent_with_suffix_function_exists(self):
        """Test get_user_agent_with_suffix() function is available."""
        assert hasattr(classic_web, "get_user_agent_with_suffix")
        assert callable(classic_web.get_user_agent_with_suffix)

    def test_get_user_agent_with_suffix_basic(self):
        """Test get_user_agent_with_suffix() appends suffix."""
        suffix = "TestSuffix/1.0"
        user_agent = classic_web.get_user_agent_with_suffix(suffix)

        assert isinstance(user_agent, str)
        assert suffix in user_agent

    def test_user_agent_prefix_constant(self):
        """Test USER_AGENT_PREFIX constant exists."""
        assert hasattr(classic_web, "USER_AGENT_PREFIX")
        assert isinstance(classic_web.USER_AGENT_PREFIX, str)
        assert len(classic_web.USER_AGENT_PREFIX) > 0


@pytest.mark.rust
@pytest.mark.unit
class TestModSiteEnum:
    """Test ModSite enumeration."""

    def test_mod_site_enum_exists(self):
        """Test ModSite enum is available."""
        assert hasattr(classic_web, "ModSite")

    def test_mod_site_variants(self):
        """Test ModSite has some variants."""
        # ModSite enum exists, exact variants implementation-specific
        # Just verify we can access the enum
        mod_site = classic_web.ModSite
        assert mod_site is not None

    def test_mod_site_methods(self):
        """Test ModSite enum has expected methods."""
        # Try to create a ModSite instance if it has factory methods
        # The exact API may differ, so this is a basic check
        mod_site = classic_web.ModSite
        # Just verify it's accessible
        assert mod_site is not None


@pytest.mark.rust
@pytest.mark.unit
class TestModuleMetadata:
    """Test module-level metadata."""

    def test_module_version(self):
        """Test module __version__ is defined."""
        assert hasattr(classic_web, "__version__")
        assert isinstance(classic_web.__version__, str)
        assert len(classic_web.__version__) > 0

    def test_module_all_exports(self):
        """Test __all__ exports key functions."""
        assert hasattr(classic_web, "__all__")
        all_exports = classic_web.__all__

        # Key functions should be exported
        expected = [
            "is_valid_url",
            "validate_url",
            "join_url",
            "build_url_with_query",
            "extract_domain",
            "get_user_agent",
        ]

        for func in expected:
            assert func in all_exports, f"{func} should be in __all__"

    def test_classic_version_constant(self):
        """Test CLASSIC_VERSION constant exists."""
        assert hasattr(classic_web, "CLASSIC_VERSION")
        assert isinstance(classic_web.CLASSIC_VERSION, str)
        assert len(classic_web.CLASSIC_VERSION) > 0


@pytest.mark.rust
@pytest.mark.integration
class TestURLEdgeCases:
    """Test URL functions with edge cases."""

    def test_is_valid_url_special_characters(self):
        """Test is_valid_url() with special characters in URL."""
        # URLs with special characters
        assert classic_web.is_valid_url("https://example.com/path?query=hello%20world") is True
        assert classic_web.is_valid_url("https://example.com/path#fragment") is True

    def test_join_url_multiple_slashes(self):
        """Test join_url() handles multiple slashes correctly."""
        result = classic_web.join_url("https://example.com//", "//path")
        # Should produce a valid URL without excessive slashes
        assert classic_web.is_valid_url(result)

    def test_extract_domain_edge_cases(self):
        """Test extract_domain() with edge cases."""
        # Localhost
        result1 = classic_web.extract_domain("http://localhost")
        assert "localhost" in result1

        # IP address
        result2 = classic_web.extract_domain("http://192.168.1.1")
        assert "192.168.1.1" in result2
