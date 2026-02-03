"""Parity tests for Rust-Python output validation.

This package contains tests that validate Rust implementations produce
identical output to the golden files captured from Python implementations.

Markers used:
- @pytest.mark.parity: Parity validation test
- @pytest.mark.integration: Integration test (accesses real files/modules)
"""
