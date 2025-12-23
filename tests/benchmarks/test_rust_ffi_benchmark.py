
import pytest
import os
from pathlib import Path

# Import the Rust modules when available
try:
    import classic_scanlog
    import classic_yaml
    RUST_AVAILABLE = True
except ImportError:
    classic_scanlog = None
    classic_yaml = None
    RUST_AVAILABLE = False

@pytest.fixture
def complex_crash_log_path():
    """Return path to complex crash log."""
    return Path("tests/test_data/sample_crash_logs/complex_crash.log")

@pytest.fixture
def complex_crash_log_lines(complex_crash_log_path):
    """Return lines of complex crash log."""
    if not complex_crash_log_path.exists():
        pytest.skip("Complex crash log not found")
    lines = complex_crash_log_path.read_text(encoding="utf-8").splitlines()
    # Ensure [Compatibility] exists for default parser boundaries
    return ["[Compatibility]"] + lines

@pytest.fixture
def test_settings_yaml_path():
    """Return path to test settings yaml."""
    return Path("tests/test_data/sample_yaml/test_settings.yaml")

@pytest.mark.benchmark
@pytest.mark.skipif(not RUST_AVAILABLE, reason="Rust extensions not built")
def test_benchmark_scanlog_parse_segments(benchmark, complex_crash_log_lines):
    """Benchmark the parse_segments function."""
    parser = classic_scanlog.LogParser()
    
    # Benchmark the FFI call
    result = benchmark(parser.parse_segments, complex_crash_log_lines)
    
    assert len(result) > 0

@pytest.mark.benchmark
@pytest.mark.skipif(not RUST_AVAILABLE, reason="Rust extensions not built")
def test_benchmark_scanlog_extract_formids(benchmark, complex_crash_log_lines):
    """Benchmark extract_formids."""
    parser = classic_scanlog.LogParser()
    
    result = benchmark(parser.extract_formids, complex_crash_log_lines)
    
    # Just ensure it ran
    assert isinstance(result, list)

@pytest.mark.benchmark
@pytest.mark.skipif(not RUST_AVAILABLE, reason="Rust extensions not built")
def test_benchmark_yaml_load_file(benchmark, test_settings_yaml_path):
    """Benchmark loading a YAML file."""
    if not test_settings_yaml_path.exists():
        pytest.skip("Test settings yaml not found")
        
    ops = classic_yaml.YamlOperations()
    
    # Benchmark loading from file
    result = benchmark(ops.load_yaml_file, test_settings_yaml_path)
    
    assert isinstance(result, dict)

@pytest.mark.benchmark
@pytest.mark.skipif(not RUST_AVAILABLE, reason="Rust extensions not built")
def test_benchmark_yaml_parse_string(benchmark, test_settings_yaml_path):
    """Benchmark parsing YAML from string."""
    if not test_settings_yaml_path.exists():
        pytest.skip("Test settings yaml not found")
        
    content = test_settings_yaml_path.read_text(encoding="utf-8")
    ops = classic_yaml.YamlOperations()
    
    result = benchmark(ops.parse_yaml, content)
    
    assert isinstance(result, dict)
