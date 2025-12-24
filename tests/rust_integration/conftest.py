"""
Shared fixtures for Rust integration tests.

This module provides domain-specific fixtures for rust integration tests.
Common fixtures (mock_yamldata, crash_log_samples, rust_yaml_files, etc.)
are imported from tests/fixtures/ via the root conftest.py.

Available fixtures from root conftest.py:
- mock_yamldata, mock_yamldata_simple, mock_scanlog_info (from yamldata_fixtures)
- crash_log_samples, sample_crash_log_content (from crash_log_fixtures)
- rust_yaml_files, mock_rust_yaml_environment (from rust_fixtures)
- performance_timer, mock_formid_dataset, mock_plugin_dataset (from rust_fixtures)
- initialized_database_pool, mock_orchestrator (from rust_fixtures)
- parity_crash_generator, parity_mock_yaml_cache, etc. (from parity_fixtures)
"""

# ruff: noqa: ANN201, ANN001, ANN204, ANN202, ANN002

# Parity fixtures are now imported from tests/fixtures/ via root conftest.py
# No additional imports needed here
