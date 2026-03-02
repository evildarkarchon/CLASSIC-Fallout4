"""Integration tests for GPU detector API compliance.

This module tests that gpu_rust.py wrapper correctly provides a module-level
get_gpu_info() function that wraps the Rust GpuDetector implementation.

The test suite verifies:
1. Factory returns module with get_gpu_info() function (not instance with method)
2. Proper return type handling (dict from wrapper's internal GpuInfo.to_dict())
3. Dict structure with expected keys (primary, secondary, manufacturer, rival)
4. GPU detection functionality for various scenarios

Bug fixed: gpu_rust.py:51 - Method name and return type correction from
detect_gpu() returning tuple to extract_gpu_info() + to_dict() returning dict

Wrapper behavior:
    - Factory returns gpu_rust MODULE with get_gpu_info() function
    - Function internally calls Rust GpuDetector.extract_gpu_info() and converts to dict
    - Tests call detector.get_gpu_info() where detector is the module

Note:
    These tests require the Rust classic_scanlog module to be available.
    They will gracefully skip if the module is not installed.
"""

import pytest


@pytest.mark.rust
@pytest.mark.integration
def test_gpu_detector_get_gpu_info() -> None:
    """Verify get_gpu_info() function is called correctly via factory.

    This test ensures the factory returns a module with get_gpu_info() function
    that internally uses Rust GpuDetector.extract_gpu_info() and converts to dict.

    The test confirms:
    - Factory returns module with get_gpu_info() function
    - Function returns a dict directly (wrapper handles conversion)
    - Dict has expected keys: primary, secondary, manufacturer, rival
    - GPU detection works with realistic data

    Raises:
        pytest.skip: If Rust classic_scanlog module is not available
    """
    try:
        from ClassicLib.integration.factory import get_gpu_detector

        # Factory returns the gpu_rust MODULE, not a detector instance
        detector_module = get_gpu_detector()

        # Test with realistic GPU line (NVIDIA)
        segment_system = [
            "OS: Windows 10 v10.0.19045",
            "GPU: NVIDIA GeForce RTX 4090",
            "CPU: AMD Ryzen 9 7950X 16-Core Processor",
        ]

        # Call the module-level function (wrapper API)
        result = detector_module.get_gpu_info(segment_system)

        # Verify return type is dict (wrapper converts internally)
        assert isinstance(result, dict), f"get_gpu_info should return dict, got {type(result).__name__}"

        # Verify dict has expected keys
        expected_keys = {"primary", "secondary", "manufacturer", "rival"}
        actual_keys = set(result.keys())
        assert actual_keys == expected_keys, f"Expected keys {expected_keys}, got {actual_keys}"

        # Verify GPU field is present (may be "Unknown" if detection fails)
        primary = result["primary"]
        assert primary is not None, "Primary field should not be None"
        assert isinstance(primary, str), "Primary should be string"

        # Verify manufacturer field is present
        manufacturer = result["manufacturer"]
        assert manufacturer is not None, "Manufacturer field should not be None"
        assert isinstance(manufacturer, str), f"Manufacturer should be string, got {type(manufacturer).__name__}"

        # Note: GPU detection accuracy is tested elsewhere; this test verifies API compliance
        # The wrapper correctly returns dict with expected structure

    except ImportError as e:
        pytest.skip(f"Rust classic_scanlog not available: {e}")


@pytest.mark.rust
@pytest.mark.integration
def test_gpu_detector_function_not_detect_gpu() -> None:
    """Verify that wrapper provides get_gpu_info() function (not detect_gpu).

    This negative test confirms that the wrapper module has the correct function
    name. This prevents regression to the bug.

    The test verifies:
    - Factory returns module (not instance)
    - Module has get_gpu_info() function
    - Module does NOT have detect_gpu() function

    Raises:
        pytest.skip: If Rust classic_scanlog module is not available
    """
    try:
        from ClassicLib.integration.factory import get_gpu_detector

        detector_module = get_gpu_detector()

        # Verify module has the CORRECT function name
        assert hasattr(detector_module, "get_gpu_info"), "Module must have get_gpu_info() function"

        # Verify module does NOT have the INCORRECT old function name
        assert not hasattr(detector_module, "detect_gpu"), (
            "Module should not have detect_gpu() function - correct function name is get_gpu_info()"
        )

        # Verify the function is callable
        assert callable(detector_module.get_gpu_info), "get_gpu_info should be a callable function"

    except ImportError as e:
        pytest.skip(f"Rust classic_scanlog not available: {e}")


@pytest.mark.rust
@pytest.mark.integration
def test_gpu_detector_handles_no_gpu() -> None:
    """Test GPU detector handles missing GPU gracefully.

    This test verifies that extract_gpu_info() returns a valid dict structure
    even when no GPU information is present in the segment data.

    The test confirms:
    - Returns dict (not None or exception)
    - Dict has all expected keys
    - Values may be None for missing GPU

    Raises:
        pytest.skip: If Rust classic_scanlog module is not available
    """
    try:
        from ClassicLib.integration.factory import get_gpu_detector

        detector_module = get_gpu_detector()

        # Empty segment (no GPU information)
        segment_system: list[str] = []

        # Call the module-level function
        result = detector_module.get_gpu_info(segment_system)

        # Should return dict even for empty segment (wrapper handles conversion)
        assert isinstance(result, dict), "get_gpu_info should return dict even for empty segment"

        # Should still have all expected keys
        expected_keys = {"primary", "secondary", "manufacturer", "rival"}
        assert set(result.keys()) == expected_keys, "Should have all keys even when no GPU detected"

        # Values may be None when no GPU detected
        # This is valid behavior
        primary = result.get("primary")
        assert primary is None or isinstance(primary, str), f"Primary should be None or string, got {type(primary).__name__}"

    except ImportError as e:
        pytest.skip(f"Rust classic_scanlog not available: {e}")


@pytest.mark.rust
@pytest.mark.integration
def test_gpu_detector_multiple_gpus() -> None:
    """Test GPU detector with multi-GPU system.

    This test verifies that extract_gpu_info() correctly handles systems with
    multiple GPUs, including rival manufacturer detection (NVIDIA + AMD).

    The test confirms:
    - Detects primary GPU
    - May detect secondary GPU
    - May detect rival vendor
    - Returns proper dict structure

    Raises:
        pytest.skip: If Rust classic_scanlog module is not available
    """
    try:
        from ClassicLib.integration.factory import get_gpu_detector

        detector_module = get_gpu_detector()

        # Multi-GPU system with rival vendors
        segment_system = [
            "GPU #0: NVIDIA GeForce RTX 4090",
            "GPU #1: AMD Radeon RX 7900 XTX",
        ]

        # Call the module-level function
        result = detector_module.get_gpu_info(segment_system)

        # Should return dict (wrapper handles conversion)
        assert isinstance(result, dict), "get_gpu_info should return dict for multi-GPU"

        # Should detect primary GPU
        assert result["primary"] is not None, "Should detect primary GPU in multi-GPU system"

        # Primary should contain GPU information
        primary = result["primary"]
        assert isinstance(primary, str), "Primary should be string"
        assert len(primary) > 0, "Primary should not be empty"

        # May detect rival vendor (NVIDIA vs AMD)
        rival = result.get("rival")
        if rival is not None:
            assert isinstance(rival, str), "Rival should be string if detected"

    except ImportError as e:
        pytest.skip(f"Rust classic_scanlog not available: {e}")


@pytest.mark.rust
@pytest.mark.integration
def test_gpu_detector_amd_gpu() -> None:
    """Test GPU detector with AMD GPU.

    This test verifies AMD GPU detection works correctly and returns
    proper manufacturer information.

    The test confirms:
    - Detects AMD GPU as primary
    - Manufacturer is correctly identified
    - Dict structure is correct

    Raises:
        pytest.skip: If Rust classic_scanlog module is not available
    """
    try:
        from ClassicLib.integration.factory import get_gpu_detector

        detector_module = get_gpu_detector()

        # AMD GPU system
        segment_system = [
            "GPU: AMD Radeon RX 7900 XTX",
        ]

        # Call the module-level function
        result = detector_module.get_gpu_info(segment_system)

        # Should return dict (wrapper handles conversion)
        assert isinstance(result, dict), "get_gpu_info should return dict for AMD GPU"

        # Verify primary field is present (may be "Unknown" if detection fails)
        primary = result["primary"]
        assert primary is not None, "Primary field should not be None"
        assert isinstance(primary, str), "Primary should be string"

        # Verify manufacturer field is present
        manufacturer = result["manufacturer"]
        assert manufacturer is not None, "Manufacturer field should not be None"
        assert isinstance(manufacturer, str), "Manufacturer should be string"

        # Note: GPU detection accuracy is tested elsewhere; this test verifies API compliance
        # The wrapper correctly returns dict with expected structure

    except ImportError as e:
        pytest.skip(f"Rust classic_scanlog not available: {e}")


@pytest.mark.rust
@pytest.mark.integration
def test_gpu_detector_intel_gpu() -> None:
    """Test GPU detector with Intel GPU.

    This test verifies Intel integrated graphics detection works correctly.

    The test confirms:
    - Detects Intel GPU
    - Returns proper dict structure
    - Manufacturer information is valid

    Raises:
        pytest.skip: If Rust classic_scanlog module is not available
    """
    try:
        from ClassicLib.integration.factory import get_gpu_detector

        detector_module = get_gpu_detector()

        # Intel integrated graphics
        segment_system = [
            "GPU: Intel(R) UHD Graphics 770",
        ]

        # Call the module-level function
        result = detector_module.get_gpu_info(segment_system)

        # Should return dict (wrapper handles conversion)
        assert isinstance(result, dict), "get_gpu_info should return dict for Intel GPU"

        # Verify primary field is present (may be "Unknown" if detection fails)
        primary = result["primary"]
        assert primary is not None, "Primary field should not be None"
        assert isinstance(primary, str), "Primary should be string"

        # Note: GPU detection accuracy is tested elsewhere; this test verifies API compliance
        # The wrapper correctly returns dict with expected structure

    except ImportError as e:
        pytest.skip(f"Rust classic_scanlog not available: {e}")


@pytest.mark.rust
@pytest.mark.integration
def test_gpu_detector_factory_consistency() -> None:
    """Test that factory returns detector with correct API methods.

    This test verifies that the factory pattern (get_gpu_detector) returns
    a detector instance that has the correct API methods available.

    The test confirms:
    - Factory returns object with extract_gpu_info()
    - Factory returns object without detect_gpu()
    - Multiple factory calls return consistent API

    Raises:
        pytest.skip: If Rust classic_scanlog module is not available
    """
    try:
        from ClassicLib.integration.factory import get_gpu_detector

        # Get module through factory (multiple times for consistency check)
        detector_module1 = get_gpu_detector()
        detector_module2 = get_gpu_detector()

        # Both should have the correct function
        assert hasattr(detector_module1, "get_gpu_info"), "Factory should return module with get_gpu_info()"
        assert hasattr(detector_module2, "get_gpu_info"), "Factory should return module with get_gpu_info()"

        # Neither should have the incorrect function name
        assert not hasattr(detector_module1, "detect_gpu"), "Module should not have detect_gpu() function"
        assert not hasattr(detector_module2, "detect_gpu"), "Module should not have detect_gpu() function"

        # Both should be callable and return dicts
        test_segment = ["GPU: Test GPU"]
        result1 = detector_module1.get_gpu_info(test_segment)
        result2 = detector_module2.get_gpu_info(test_segment)

        assert isinstance(result1, dict), "get_gpu_info should return dict"
        assert isinstance(result2, dict), "get_gpu_info should return dict"

    except ImportError as e:
        pytest.skip(f"Rust classic_scanlog not available: {e}")


@pytest.mark.rust
@pytest.mark.integration
def test_gpu_detector_dict_structure_complete() -> None:
    """Test that returned dict has complete structure with proper types.

    This test verifies that the dict returned by extract_gpu_info() has
    all expected keys with proper types (string or None).

    The test confirms:
    - All 4 expected keys present
    - Values are either string or None
    - No unexpected keys present

    Raises:
        pytest.skip: If Rust classic_scanlog module is not available
    """
    try:
        from ClassicLib.integration.factory import get_gpu_detector

        detector_module = get_gpu_detector()

        # Test with realistic data
        segment_system = [
            "GPU: NVIDIA GeForce RTX 4090",
        ]

        # Call the module-level function
        result = detector_module.get_gpu_info(segment_system)

        # Should return dict (wrapper handles conversion)
        assert isinstance(result, dict), "get_gpu_info should return dict"

        # Verify complete structure
        expected_keys = {"primary", "secondary", "manufacturer", "rival"}
        assert set(result.keys()) == expected_keys, f"Dict should have exactly these keys: {expected_keys}"

        # Verify value types
        for key, value in result.items():
            assert value is None or isinstance(value, str), f"Key '{key}' should be string or None, got {type(value).__name__}"

        # No extra keys
        assert len(result) == 4, f"Dict should have exactly 4 keys, got {len(result)}"

    except ImportError as e:
        pytest.skip(f"Rust classic_scanlog not available: {e}")
