"""Parity tests verifying Python GlobalRegistry and Rust classic_registry produce identical results.

This module ensures that the Python GlobalRegistry wrapper (ClassicLib.core.registry)
correctly delegates all operations to the Rust classic_registry backend, and that
both APIs agree on key constants, default values, and round-trip behavior.
"""

from typing import Any

import pytest

classic_registry = pytest.importorskip("classic_registry", reason="Rust classic_registry module not available")

from ClassicLib.core.registry import GlobalRegistry  # noqa: E402
from ClassicLib.core.registry import Keys as PyKeys  # noqa: E402


@pytest.fixture(autouse=True)
def clear_registry():
    """Clear registry before and after each test."""
    classic_registry.clear_all()
    yield
    classic_registry.clear_all()


@pytest.mark.rust
@pytest.mark.parity
class TestKeysParity:
    """Verify all Python Keys constants exist in Rust Keys with identical values."""

    def test_all_python_keys_exist_in_rust(self):
        """Every Python Keys attribute should exist in Rust Keys with same value."""
        rust_keys = classic_registry.Keys

        # Collect all public string attributes from Python Keys
        py_key_attrs = [attr for attr in dir(PyKeys) if not attr.startswith("_") and isinstance(getattr(PyKeys, attr), str)]

        assert len(py_key_attrs) > 0, "Python Keys should have at least some constants"

        for attr in py_key_attrs:
            py_value = getattr(PyKeys, attr)
            assert hasattr(rust_keys, attr), f"Rust Keys missing attribute: {attr}"
            rust_value = getattr(rust_keys, attr)
            assert py_value == rust_value, f"Key mismatch for {attr}: Python={py_value!r}, Rust={rust_value!r}"

    def test_specific_key_values(self):
        """Spot-check critical key values match between Python and Rust."""
        rust_keys = classic_registry.Keys

        assert PyKeys.YAML_CACHE == rust_keys.YAML_CACHE == "yaml_cache"
        assert PyKeys.GAME == rust_keys.GAME == "gamevars_game"
        assert PyKeys.IS_GUI_MODE == rust_keys.IS_GUI_MODE == "is_gui_mode"
        assert PyKeys.LOCAL_DIR == rust_keys.LOCAL_DIR == "local_dir"
        assert PyKeys.GAME_VERSION == rust_keys.GAME_VERSION == "gamevars_version"
        assert PyKeys.XSE_VALID == rust_keys.XSE_VALID == "xse_validation_passed"
        assert PyKeys.XSE_VERSION == rust_keys.XSE_VERSION == "xse_detected_version"
        assert PyKeys.ENB_PRESENT == rust_keys.ENB_PRESENT == "enb_binaries_present"
        assert PyKeys.GAME_VERSION_DETECTED == rust_keys.GAME_VERSION_DETECTED == "game_exe_version"


@pytest.mark.rust
@pytest.mark.parity
class TestCoreOpsParity:
    """Verify core operations produce identical results via Python and Rust."""

    def test_register_via_python_get_via_rust(self):
        """Value registered through Python wrapper is visible via Rust get()."""
        GlobalRegistry.register("parity_key", "parity_value")
        assert classic_registry.get("parity_key") == "parity_value"

    def test_register_via_rust_get_via_python(self):
        """Value registered via Rust is visible through Python wrapper."""
        classic_registry.register("rust_key", "rust_value")
        assert GlobalRegistry.get("rust_key") == "rust_value"

    def test_is_registered_agreement(self):
        """Both APIs agree on registration status."""
        assert not GlobalRegistry.is_registered("test_key")
        assert not classic_registry.is_registered("test_key")

        GlobalRegistry.register("test_key", 42)
        assert GlobalRegistry.is_registered("test_key")
        assert classic_registry.is_registered("test_key")

    def test_unregister_via_python_wrapper(self):
        """Unregister through Python wrapper removes from shared storage."""
        classic_registry.register("temp", "value")
        assert GlobalRegistry.is_registered("temp")

        result = GlobalRegistry.unregister("temp")
        assert result is True
        assert not classic_registry.is_registered("temp")

    def test_unregister_via_rust(self):
        """Unregister through Rust removes from shared storage."""
        GlobalRegistry.register("temp", "value")
        assert classic_registry.is_registered("temp")

        result = classic_registry.unregister("temp")
        assert result is True
        assert not GlobalRegistry.is_registered("temp")

    def test_unregister_nonexistent(self):
        """Both APIs agree on unregistering nonexistent key."""
        assert GlobalRegistry.unregister("nope") is False
        assert classic_registry.unregister("nope") is False

    def test_clear_via_python_clears_rust(self):
        """Python GlobalRegistry.clear() clears the Rust storage."""
        classic_registry.register("k1", "v1")
        classic_registry.register("k2", "v2")
        GlobalRegistry.clear()
        assert not classic_registry.is_registered("k1")
        assert not classic_registry.is_registered("k2")

    def test_round_trip_complex_types(self):
        """Complex Python types round-trip through Rust storage correctly."""
        test_cases: list[tuple[str, Any]] = [
            ("str_val", "hello"),
            ("int_val", 42),
            ("bool_val", True),
            ("list_val", [1, "two", 3.0]),
            ("dict_val", {"nested": {"key": "value"}}),
            ("none_val", None),
        ]

        for key, value in test_cases:
            GlobalRegistry.register(key, value)

        for key, expected in test_cases:
            py_result = GlobalRegistry.get(key)
            rust_result = classic_registry.get(key)

            if expected is None:
                assert py_result is None, f"Python get({key!r}) should be None"
                assert rust_result is None, f"Rust get({key!r}) should be None"
            else:
                assert py_result == expected, f"Python get({key!r}) = {py_result!r}, expected {expected!r}"
                assert rust_result == expected, f"Rust get({key!r}) = {rust_result!r}, expected {expected!r}"


@pytest.mark.rust
@pytest.mark.parity
class TestConvenienceFunctionDefaults:
    """Verify convenience function defaults match between Python wrapper and Rust."""

    def test_get_game_default(self):
        """Both return 'Fallout4' when no game registered."""
        assert GlobalRegistry.get_game() == "Fallout4"
        assert classic_registry.get_game() == "Fallout4"

    def test_get_game_after_set(self):
        """Both return same value after set_game()."""
        GlobalRegistry.set_game("Skyrim")
        assert GlobalRegistry.get_game() == "Skyrim"
        assert classic_registry.get_game() == "Skyrim"

    def test_is_gui_mode_default(self):
        """Both return False when not set."""
        assert GlobalRegistry.is_gui_mode() is False
        assert classic_registry.is_gui_mode() is False

    def test_get_vr_default(self):
        """Rust returns empty string when VR not set."""
        assert classic_registry.get_vr() == ""

    def test_get_local_dir_not_empty(self):
        """Both return a non-empty string for local dir."""
        py_dir = GlobalRegistry.get_local_dir(as_string=True)
        rust_dir = classic_registry.get_local_dir()
        assert py_dir  # Not empty
        assert rust_dir  # Not empty

    def test_get_game_version_string_default(self):
        """Rust returns 'auto' when no version registered."""
        assert classic_registry.get_game_version_string() == "auto"

    def test_get_config_suffix_default(self):
        """Rust returns empty string when no VR configured."""
        assert classic_registry.get_config_suffix() == ""

    def test_is_vr_version_default(self):
        """Rust returns False when no VR configured."""
        assert classic_registry.is_vr_version() is False

    def test_is_xse_valid_default(self):
        """Both return False when XSE not validated."""
        assert GlobalRegistry.is_xse_valid() is False
        assert classic_registry.is_xse_valid() is False

    def test_is_enb_present_default(self):
        """Both return False when ENB not detected."""
        assert GlobalRegistry.is_enb_present() is False
        assert classic_registry.is_enb_present() is False


@pytest.mark.rust
@pytest.mark.parity
class TestConvenienceFunctionSetValues:
    """Verify convenience functions return correct values after registration."""

    def test_is_xse_valid_after_set(self):
        """Both return True after XSE_VALID is registered."""
        GlobalRegistry.register(PyKeys.XSE_VALID, True)
        assert GlobalRegistry.is_xse_valid() is True
        assert classic_registry.is_xse_valid() is True

    def test_is_enb_present_after_set(self):
        """Both return True after ENB_PRESENT is registered."""
        GlobalRegistry.register(PyKeys.ENB_PRESENT, True)
        assert GlobalRegistry.is_enb_present() is True
        assert classic_registry.is_enb_present() is True

    def test_game_version_string_after_set(self):
        """Rust returns registered value."""
        classic_registry.register(classic_registry.Keys.GAME_VERSION, "NextGen")
        assert classic_registry.get_game_version_string() == "NextGen"

    def test_config_suffix_vr(self):
        """Rust returns 'VR' when version is VR."""
        classic_registry.register(classic_registry.Keys.GAME_VERSION, "VR")
        assert classic_registry.get_config_suffix() == "VR"
        assert classic_registry.is_vr_version() is True

    def test_set_game_cross_api(self):
        """set_game via Rust, get_game via Python (and vice versa)."""
        classic_registry.set_game("Skyrim")
        assert GlobalRegistry.get_game() == "Skyrim"

        GlobalRegistry.set_game("Fallout4")
        assert classic_registry.get_game() == "Fallout4"

    def test_gui_mode_cross_api(self):
        """Register GUI mode via one API, check via the other."""
        GlobalRegistry.register(PyKeys.IS_GUI_MODE, True)
        assert classic_registry.is_gui_mode() is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
