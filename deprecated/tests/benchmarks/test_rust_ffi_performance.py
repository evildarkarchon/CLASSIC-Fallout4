import pytest

# Import the Rust modules when available
try:
    import classic_scanlog
    import classic_yaml

    RUST_AVAILABLE = True
except ImportError:
    classic_scanlog = None
    classic_yaml = None
    RUST_AVAILABLE = False

# Note: complex_crash_log_path, complex_crash_log_lines, and test_settings_yaml_path
# fixtures are provided by tests/fixtures/performance_fixtures.py via the root conftest.py


@pytest.mark.benchmark
@pytest.mark.skipif(not RUST_AVAILABLE, reason="Rust extensions not built")
def test_benchmark_scanlog_parse_segments(benchmark, complex_crash_log_lines):
    """Benchmark the parse_segments function."""
    assert classic_scanlog is not None
    parser = classic_scanlog.LogParser()

    # Benchmark the FFI call
    result = benchmark(parser.parse_segments, complex_crash_log_lines)

    assert len(result) > 0


@pytest.mark.benchmark
@pytest.mark.skipif(not RUST_AVAILABLE, reason="Rust extensions not built")
def test_benchmark_scanlog_extract_formids(benchmark, complex_crash_log_lines):
    """Benchmark extract_formids."""
    assert classic_scanlog is not None
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

    assert classic_yaml is not None
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

    assert classic_yaml is not None
    content = test_settings_yaml_path.read_text(encoding="utf-8")
    ops = classic_yaml.YamlOperations()

    result = benchmark(ops.parse_yaml, content)

    assert isinstance(result, dict)
