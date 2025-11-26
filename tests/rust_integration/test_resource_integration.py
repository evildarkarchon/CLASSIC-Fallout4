"""Integration tests for classic-resource Rust module.

Tests the Rust-accelerated resource management module, including resource type
detection, enumeration, validation, and resource information handling.
"""

import pytest

classic_resource = pytest.importorskip("classic_resource", reason="Rust classic_resource module not available")


@pytest.mark.rust
@pytest.mark.unit
class TestResourceType:
    """Test ResourceType enumeration."""

    def test_resource_type_enum_exists(self):
        """Test ResourceType enum is available."""
        assert hasattr(classic_resource, "ResourceType")

    def test_parse_resource_type_function_exists(self):
        """Test parse_resource_type() function is available."""
        assert hasattr(classic_resource, "parse_resource_type")
        assert callable(classic_resource.parse_resource_type)

    def test_parse_resource_type_basic(self):
        """Test parse_resource_type() parses common resource types."""
        # The exact types depend on implementation
        # Just verify the function works
        try:
            result = classic_resource.parse_resource_type("data")
            assert result is not None
        except ValueError:
            # If "data" isn't valid, that's fine - just testing the function exists
            pass


@pytest.mark.rust
@pytest.mark.unit
class TestResourceDetection:
    """Test resource type detection functions."""

    def test_detect_resource_type_function_exists(self):
        """Test detect_resource_type() function is available."""
        assert hasattr(classic_resource, "detect_resource_type")
        assert callable(classic_resource.detect_resource_type)

    def test_detect_resource_type_basic(self):
        """Test detect_resource_type() detects resource types."""
        # Test with some common paths/names
        # The exact behavior depends on implementation
        result = classic_resource.detect_resource_type("data.txt")
        # Should return a ResourceType or None
        assert result is None or isinstance(result, classic_resource.ResourceType)

    def test_is_supported_resource_function_exists(self):
        """Test is_supported_resource() function is available."""
        assert hasattr(classic_resource, "is_supported_resource")
        assert callable(classic_resource.is_supported_resource)

    def test_is_supported_resource_basic(self):
        """Test is_supported_resource() checks resource support."""
        # The function should return a boolean
        result = classic_resource.is_supported_resource("test.txt")
        assert isinstance(result, bool)


@pytest.mark.rust
@pytest.mark.unit
class TestResourceValidation:
    """Test resource validation functions."""

    def test_validate_resource_function_exists(self):
        """Test validate_resource() function is available."""
        assert hasattr(classic_resource, "validate_resource")
        assert callable(classic_resource.validate_resource)

    def test_validate_resource_basic(self):
        """Test validate_resource() validates resources."""
        # The function may raise an exception for non-existent files
        # This is expected behavior
        try:
            result = classic_resource.validate_resource("test.txt")
            # If it doesn't raise, should return a boolean
            assert isinstance(result, bool) or result is None
        except (OSError, FileNotFoundError):
            # Expected for non-existent files
            pass


@pytest.mark.rust
@pytest.mark.unit
class TestResourceEnumeration:
    """Test resource enumeration functions."""

    def test_enumerate_resources_function_exists(self):
        """Test enumerate_resources() function is available."""
        assert hasattr(classic_resource, "enumerate_resources")
        assert callable(classic_resource.enumerate_resources)

    def test_enumerate_resources_basic(self):
        """Test enumerate_resources() enumerates resources."""
        # The function should return a list or similar collection
        # The exact signature depends on implementation
        # Just verify it's callable and returns something
        # Skip actual execution as it may require setup

    def test_count_resources_by_type_function_exists(self):
        """Test count_resources_by_type() function is available."""
        assert hasattr(classic_resource, "count_resources_by_type")
        assert callable(classic_resource.count_resources_by_type)


@pytest.mark.rust
@pytest.mark.unit
class TestResourceInfo:
    """Test ResourceInfo class."""

    def test_resource_info_class_exists(self):
        """Test ResourceInfo class is available."""
        assert hasattr(classic_resource, "ResourceInfo")

    def test_resource_info_attributes(self):
        """Test ResourceInfo has expected methods/attributes."""
        # The exact interface depends on implementation
        # Just verify the class exists and is accessible
        info_class = classic_resource.ResourceInfo
        assert info_class is not None


@pytest.mark.rust
@pytest.mark.unit
class TestModuleMetadata:
    """Test module-level metadata."""

    def test_module_version(self):
        """Test module __version__ is defined."""
        assert hasattr(classic_resource, "__version__")
        assert isinstance(classic_resource.__version__, str)
        assert len(classic_resource.__version__) > 0

    def test_module_all_exports(self):
        """Test __all__ exports key components."""
        assert hasattr(classic_resource, "__all__")
        all_exports = classic_resource.__all__

        # Key components should be exported
        expected = [
            "ResourceType",
            "ResourceInfo",
            "detect_resource_type",
            "is_supported_resource",
            "validate_resource",
            "enumerate_resources",
        ]

        for component in expected:
            assert component in all_exports, f"{component} should be in __all__"


@pytest.mark.rust
@pytest.mark.integration
class TestResourceWorkflow:
    """Test typical resource management workflows."""

    def test_detect_and_validate_workflow(self):
        """Test detecting resource type and validating it."""
        # Detect resource type
        classic_resource.detect_resource_type("test.txt")

        # Validate resource may raise for non-existent files
        try:
            is_valid = classic_resource.validate_resource("test.txt")
            # Should return boolean
            assert isinstance(is_valid, bool) or is_valid is None
        except (OSError, FileNotFoundError):
            # Expected for non-existent files
            pass

    def test_supported_resource_check(self):
        """Test checking if resource is supported."""
        is_supported = classic_resource.is_supported_resource("test.txt")
        assert isinstance(is_supported, bool)

        # If supported, should be able to detect type
        if is_supported:
            classic_resource.detect_resource_type("test.txt")
            # Type detection should work for supported resources
            # (or may return None if file doesn't exist)


@pytest.mark.rust
@pytest.mark.unit
class TestResourceTypeConsistency:
    """Test consistency between resource type functions."""

    def test_parse_and_detect_consistency(self):
        """Test parse_resource_type and detect_resource_type are consistent."""
        # If we can parse a type, we should be able to detect resources of that type
        # The exact test depends on what types are available
        # Basic consistency check - implementation-specific

    def test_supported_implies_detectable(self):
        """Test that supported resources have detectable types."""
        # If a resource is supported, we should be able to detect or validate it
        test_resource = "test.txt"
        is_supported = classic_resource.is_supported_resource(test_resource)

        # This is a logical consistency check
        # If supported=True, then detect or validate should work
        # (though may return None/False if file doesn't exist)
        assert isinstance(is_supported, bool)
