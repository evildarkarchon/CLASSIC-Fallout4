"""
Test data generation module for realistic benchmarking scenarios.

This module provides comprehensive test data generation capabilities
to create realistic crash logs, plugin configurations, and system
scenarios that represent actual CLASSIC usage patterns.

Components:
- realistic_data_generator: Main data generation orchestrator
- crash_log_templates: Templates for different types of crash logs
- plugin_data_generator: Plugin load order and metadata generation
- formid_data_generator: FormID patterns and database entries
- system_scenario_generator: System-specific test scenarios

The generated data includes:
- Realistic crash log formats for different games (Fallout 4, Skyrim)
- Various crash types and error patterns
- Authentic plugin load orders and metadata
- FormID patterns matching real game data
- Edge cases and error conditions for robustness testing
"""

__all__ = [
    'realistic_data_generator',
]
