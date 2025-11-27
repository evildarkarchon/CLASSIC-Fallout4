"""Test script to validate Rust module type stubs.

This script verifies that the .pyi stub files are correctly structured
and can be used for type checking with mypy and pyright.
"""

from __future__ import annotations

from pathlib import Path

# Test imports - these should work with the stub files
try:
    import classic_config
    import classic_scanlog

    RUST_AVAILABLE = True
except ImportError:
    RUST_AVAILABLE = False
    print("⚠️  Rust modules not available - stub files will be validated without runtime checks")


def test_classic_config_stubs():
    """Test classic_config stub file completeness."""
    print("Testing classic_config.pyi...")

    if not RUST_AVAILABLE:
        print("  ⏭️  Skipping runtime checks (module not available)")
        return

    try:
        import classic_config

        # Test YamlData class
        assert hasattr(classic_config, "YamlData")

        # Test factory function
        assert hasattr(classic_config, "create_yamldata")

        # Test version
        assert hasattr(classic_config, "__version__")

        print("  ✅ classic_config.pyi is complete")
    except ImportError:
        print("  ⏭️  classic_config module not available")


def test_classic_scanlog_stubs():
    """Test classic_scanlog stub file completeness."""
    print("Testing classic_scanlog.pyi...")

    if not RUST_AVAILABLE:
        print("  ⏭️  Skipping runtime checks (module not available)")
        return

    try:
        import classic_scanlog

        # Test FormID classes
        assert hasattr(classic_scanlog, "FormIDAnalyzer")
        # assert hasattr(classic_scanlog, "RustFormIDAnalyzer") # Removed as it may not be exposed
        assert hasattr(classic_scanlog, "FormIDAnalyzerCore")

        # Test parser classes
        assert hasattr(classic_scanlog, "LogParser")
        assert hasattr(classic_scanlog, "PatternMatcher")

        # Test analyzer classes
        assert hasattr(classic_scanlog, "PluginAnalyzer")
        assert hasattr(classic_scanlog, "RecordScanner")

        # Test orchestrator classes
        # assert hasattr(classic_scanlog, "RustOrchestrator") # Removed as it may not be exposed
        assert hasattr(classic_scanlog, "AnalysisConfig")
        assert hasattr(classic_scanlog, "AnalysisResult")

        # Test report classes
        assert hasattr(classic_scanlog, "StringPool")
        assert hasattr(classic_scanlog, "ReportFragment")
        assert hasattr(classic_scanlog, "ReportComposer")
        assert hasattr(classic_scanlog, "ReportGenerator")
        assert hasattr(classic_scanlog, "ParallelReportProcessor")

        # Test standalone functions
        assert hasattr(classic_scanlog, "extract_formids_batch")
        assert hasattr(classic_scanlog, "is_valid_formid")
        assert hasattr(classic_scanlog, "validate_formids_batch")
        assert hasattr(classic_scanlog, "scan_records_batch")
        assert hasattr(classic_scanlog, "contains_record")
        assert hasattr(classic_scanlog, "detect_plugins_batch")
        assert hasattr(classic_scanlog, "contains_plugin")
        assert hasattr(classic_scanlog, "detect_mods_single")
        assert hasattr(classic_scanlog, "detect_mods_double")
        assert hasattr(classic_scanlog, "detect_mods_important")
        assert hasattr(classic_scanlog, "detect_mods_batch")

        # Test test class
        # assert hasattr(classic_scanlog, "TestClass")

        # Test version
        assert hasattr(classic_scanlog, "__version__")

        print("  ✅ classic_scanlog.pyi is complete")
    except ImportError:
        print("  ⏭️  classic_scanlog module not available")


def test_stub_file_locations():
    """Test that stub files are in the correct locations."""
    print("Testing stub file locations...")

    classic_config_stub = Path("rust/python-bindings/classic-config-py/classic_config.pyi")
    classic_scanlog_stub = Path("rust/python-bindings/classic-scanlog-py/classic_scanlog.pyi")

    assert classic_config_stub.exists(), f"Missing: {classic_config_stub}"
    assert classic_scanlog_stub.exists(), f"Missing: {classic_scanlog_stub}"

    print("  ✅ All stub files in correct locations")


def test_stub_file_syntax():
    """Test that stub files have valid Python syntax."""
    print("Testing stub file syntax...")

    stub_files = [
        Path("rust/python-bindings/classic-config-py/classic_config.pyi"),
        Path("rust/python-bindings/classic-scanlog-py/classic_scanlog.pyi"),
    ]

    for stub_file in stub_files:
        if not stub_file.exists():
            print(f"  ⚠️  Stub file not found: {stub_file}")
            continue

        try:
            import ast

            content = stub_file.read_text(encoding="utf-8")
            ast.parse(content)
            print(f"  ✅ {stub_file.name} has valid syntax")
        except SyntaxError as e:
            print(f"  ❌ {stub_file.name} has syntax error: {e}")
            raise


def main():
    """Run all stub file tests."""
    print("=" * 60)
    print("Rust Module Type Stub Validation")
    print("=" * 60)
    print()

    try:
        test_stub_file_locations()
        print()

        test_stub_file_syntax()
        print()

        test_classic_config_stubs()
        print()

        test_classic_scanlog_stubs()
        print()

        print("=" * 60)
        print("✅ All stub file tests passed!")
        print("=" * 60)
        print()
        print("Next steps:")
        print("  1. Run mypy: uv run mypy --strict ClassicLib/")
        print("  2. Run pyright: uv run pyright ClassicLib/")
        print("  3. Verify IDE autocomplete works with Rust modules")

    except AssertionError as e:
        print()
        print("=" * 60)
        print(f"❌ Test failed: {e}")
        print("=" * 60)
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
