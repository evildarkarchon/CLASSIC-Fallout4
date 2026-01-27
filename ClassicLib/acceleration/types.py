"""Component type definitions for RustAcceleration.

This module provides the ComponentType enum for categorizing
different types of Rust-accelerated components.
"""

from __future__ import annotations

from enum import Enum


class ComponentType(Enum):
    """Represent various component types as an enumeration.

    This enumeration provides a set of predefined categories for categorizing
    different types of components in a system. Each member of the enumeration
    is a string constant that represents a specific component type.

    Attributes:
        PARSER (str): Represents components responsible for parsing activities.
        FORMID_ANALYZER (str): Represents components used for analyzing form IDs.
        PLUGIN_ANALYZER (str): Represents components designed to analyze plugins.
        RECORD_SCANNER (str): Represents components that scan and process records.
        REPORT_GENERATION (str): Represents components for generating reports.
        DATABASE_POOL (str): Represents components functioning as database pools.
        FILE_IO_CORE (str): Represents components handling core file I/O tasks.
        MOD_DETECTOR (str): Represents components detecting modifications or mods.

    """

    PARSER = "parser"
    FORMID_ANALYZER = "formid_analyzer"
    PLUGIN_ANALYZER = "plugin_analyzer"
    RECORD_SCANNER = "record_scanner"
    REPORT_GENERATION = "report_generation"
    DATABASE_POOL = "database_pool"
    FILE_IO_CORE = "file_io_core"
    MOD_DETECTOR = "mod_detector"


__all__ = ["ComponentType"]
