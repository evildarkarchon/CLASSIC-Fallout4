"""
Shared constants for TUI module.

This module contains commonly used constants across TUI components
to avoid duplication and improve performance.
"""

# Terminal types that typically support Unicode/UTF-8
# Using a set for O(1) lookup performance
UNICODE_TERMINAL_TYPES: set[str] = {"xterm", "vt100", "linux", "screen", "tmux"}
