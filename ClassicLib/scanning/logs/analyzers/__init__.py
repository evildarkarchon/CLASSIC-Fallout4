"""Analyzers package - all implementations now in Rust.

This package previously contained Python analyzer implementations.
All analyzers are now provided by the classic_scanlog Rust module.

Access analyzers through ClassicLib.integration.factory:
- get_formid_analyzer()
- get_plugin_analyzer()
- get_record_scanner()
- get_suspect_scanner()
- get_settings_validator()
- get_gpu_detector()
"""
