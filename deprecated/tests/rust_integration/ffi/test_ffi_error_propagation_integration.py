from pathlib import Path
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    import classic_config

    RUST_AVAILABLE = True
else:
    try:
        import classic_config

        RUST_AVAILABLE = True
    except ImportError:
        classic_config = None
        RUST_AVAILABLE = False


@pytest.mark.rust
@pytest.mark.skipif(not RUST_AVAILABLE, reason="Rust extensions not available")
class TestErrorPropagation:
    """Test that Rust errors are correctly propagated to Python exceptions."""

    def test_invalid_input_propagation(self):
        """Test propagation of InvalidInput error."""
        # Providing only 1 path should trigger InvalidInput in load_from_yaml_files
        with pytest.raises(ValueError) as excinfo:
            classic_config.create_yamldata([Path("only_one_path")], "Fallout4", False)

        # RustConfigParseError inherits from ValueError
        assert "Invalid input" in str(excinfo.value)

    def test_file_not_found_propagation(self):
        """Test propagation of IOError (FileNotFound)."""
        paths = [Path("non_existent_root"), Path("non_existent_data")]
        with pytest.raises(IOError) as excinfo:
            classic_config.create_yamldata(paths, "Fallout4", False)

        assert "not found" in str(excinfo.value) or "No such file" in str(excinfo.value)

    def test_parse_error_propagation(self, tmp_path):
        """Test propagation of ParseError."""
        # Create invalid YAML files
        d = tmp_path / "data"
        d.mkdir()
        (d / "databases").mkdir()

        main_yaml = d / "databases" / "CLASSIC Main.yaml"
        main_yaml.write_text("invalid: [ yaml: content")  # Invalid syntax

        game_yaml = d / "databases" / "CLASSIC Fallout4.yaml"
        game_yaml.write_text("valid: yaml")

        ignore_yaml = tmp_path / "CLASSIC Ignore.yaml"
        ignore_yaml.write_text("valid: yaml")

        paths = [tmp_path, d]

        with pytest.raises(ValueError) as excinfo:
            classic_config.create_yamldata(paths, "Fallout4", False)

        assert "Failed to parse" in str(excinfo.value)
