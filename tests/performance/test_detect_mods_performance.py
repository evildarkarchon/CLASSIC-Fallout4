"""Performance tests for DetectMods optimization."""

# ruff: noqa: ANN001, ANN002, ANN003, RUF100, ANN201, ANN204, ANN202, ARG001, PT011, ARG002
import time

import pytest

from ClassicLib.scanning.logs.detect_mods import detect_mods_double, detect_mods_important, detect_mods_single


@pytest.mark.performance
@pytest.mark.slow
def test_detect_mods_single_performance():
    """Test performance of detect_mods_single with large datasets."""
    # Create a large dataset of mods (100 mods)
    yaml_dict = {f"mod_{i:03d}": f"Warning for mod {i}" for i in range(100)}

    # Create a large dataset of plugins (200 plugins with various mod names)
    crashlog_plugins = {}
    for i in range(200):
        # Mix of plugins: some match mods, some don't
        if i % 3 == 0:
            plugin_name = f"someprefix_mod_{i % 100:03d}_suffix.esp"
        elif i % 3 == 1:
            plugin_name = f"other_mod_{(i + 50) % 100:03d}_plugin.esm"
        else:
            plugin_name = f"nomatch_plugin_{i}.esp"
        crashlog_plugins[plugin_name] = f"[{i:02X}]"

    # Measure execution time
    start_time = time.perf_counter()
    result = detect_mods_single(yaml_dict, crashlog_plugins)
    elapsed_time = time.perf_counter() - start_time

    # Performance assertion: should complete in under 50ms for this dataset
    assert elapsed_time < 0.05, f"detect_mods_single took {elapsed_time:.3f}s, expected < 0.05s"

    # Verify correctness
    assert result.has_content  # Should find some mods


@pytest.mark.performance
@pytest.mark.slow
def test_detect_mods_double_performance():
    """Test performance of detect_mods_double with large datasets."""
    # Create mod pairs (50 pairs)
    yaml_dict = {f"mod_a_{i:02d} | mod_b_{i:02d}": f"Conflict warning {i}" for i in range(50)}

    # Create plugins that include both mods from some pairs
    crashlog_plugins = {}
    for i in range(150):
        if i < 25:
            # These will have both mods from a pair
            plugin_name = f"has_mod_a_{i:02d}_and_mod_b_{i:02d}.esp"
        elif i < 50:
            # These will have only one mod from a pair
            plugin_name = f"has_only_mod_a_{i:02d}.esp"
        elif i < 75:
            # These will have only the other mod
            plugin_name = f"has_only_mod_b_{i % 25:02d}.esp"
        else:
            # These won't match any mod
            plugin_name = f"unrelated_plugin_{i}.esp"
        crashlog_plugins[plugin_name] = f"[{i:02X}]"

    # Measure execution time
    start_time = time.perf_counter()
    result = detect_mods_double(yaml_dict, crashlog_plugins)
    elapsed_time = time.perf_counter() - start_time

    # Performance assertion: should complete in under 50ms
    assert elapsed_time < 0.05, f"detect_mods_double took {elapsed_time:.3f}s, expected < 0.05s"

    # Verify correctness
    assert result.has_content  # Should find some conflicts


@pytest.mark.performance
@pytest.mark.slow
def test_detect_mods_important_performance():
    """Test performance of detect_mods_important with large datasets."""
    # Create important mods (50 mods)
    yaml_dict = {}
    for i in range(50):
        if i % 3 == 0:
            warning = "This mod requires an NVIDIA GPU"
        elif i % 3 == 1:
            warning = "This mod requires an AMD GPU"
        else:
            warning = "General mod information"
        yaml_dict[f"important_mod_{i:02d} | Important Mod {i}"] = warning

    # Create plugins
    crashlog_plugins = {}
    for i in range(100):
        plugin_name = f"has_important_mod_{i % 50:02d}.esp" if i < 30 else f"regular_plugin_{i}.esp"
        crashlog_plugins[plugin_name] = f"[{i:02X}]"

    # Test with NVIDIA GPU
    start_time = time.perf_counter()
    result = detect_mods_important(yaml_dict, crashlog_plugins, "nvidia", set())
    elapsed_time = time.perf_counter() - start_time

    # Performance assertion: should complete in under 30ms
    assert elapsed_time < 0.03, f"detect_mods_important took {elapsed_time:.3f}s, expected < 0.03s"

    # Verify output was generated
    assert result.has_content

if __name__ == "__main__":
    # Run performance tests directly
    print("Running DetectMods performance tests...")

    print("\n1. Testing detect_mods_single performance...")
    test_detect_mods_single_performance()
    print("   ✓ Passed")

    print("\n2. Testing detect_mods_double performance...")
    test_detect_mods_double_performance()
    print("   ✓ Passed")

    print("\n3. Testing detect_mods_important performance...")
    test_detect_mods_important_performance()
    print("   ✓ Passed")

    print("\n✅ All performance tests passed!")
