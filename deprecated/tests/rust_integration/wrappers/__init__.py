"""Rust wrapper unit tests.

This package contains tests for Python wrappers around Rust FFI modules.
These tests verify that the wrapper classes correctly:
- Initialize with both Rust and Python fallback implementations
- Convert types between Python and Rust correctly
- Fall back gracefully when Rust is unavailable
- Handle errors appropriately
"""
