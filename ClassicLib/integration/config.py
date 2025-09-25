"""
Integration Configuration Module

Contains configuration constants and performance thresholds for the
Rust integration layer.
"""

# Environment variable to disable Rust acceleration
DISABLE_RUST_ENV_VAR = "CLASSIC_DISABLE_RUST"

# Component names
COMPONENT_PARSER = "parser"
COMPONENT_FORMID_ANALYZER = "formid_analyzer"
COMPONENT_PLUGIN_ANALYZER = "plugin_analyzer"
COMPONENT_RECORD_SCANNER = "record_scanner"
COMPONENT_REPORT_GENERATION = "report_generation"
COMPONENT_DATABASE = "database"
COMPONENT_DATABASE_POOL = "database_pool"
COMPONENT_FILE_IO = "file_io"
COMPONENT_FILE_IO_CORE = "file_io_core"
COMPONENT_MOD_DETECTOR = "mod_detector"

# All component names list
ALL_COMPONENTS = [
    COMPONENT_PARSER,
    COMPONENT_FORMID_ANALYZER,
    COMPONENT_PLUGIN_ANALYZER,
    COMPONENT_RECORD_SCANNER,
    COMPONENT_REPORT_GENERATION,
    COMPONENT_DATABASE,
    COMPONENT_DATABASE_POOL,
    COMPONENT_FILE_IO,
    COMPONENT_FILE_IO_CORE,
    COMPONENT_MOD_DETECTOR,
]

# Performance multipliers for each component
PERFORMANCE_MULTIPLIERS = {
    COMPONENT_PARSER: "150x",
    COMPONENT_FORMID_ANALYZER: "50x",
    COMPONENT_PLUGIN_ANALYZER: "30x",
    COMPONENT_RECORD_SCANNER: "40x",
    COMPONENT_REPORT_GENERATION: "75x",
    COMPONENT_DATABASE_POOL: "25x",
    COMPONENT_FILE_IO_CORE: "10-20x file ops, 30-40x DDS",
    COMPONENT_MOD_DETECTOR: "35x",
}

# Component categories for status display
COMPONENT_CATEGORIES = {
    "ScanLog Components": [
        COMPONENT_PARSER,
        COMPONENT_FORMID_ANALYZER,
        COMPONENT_PLUGIN_ANALYZER,
        COMPONENT_RECORD_SCANNER,
        COMPONENT_REPORT_GENERATION,
        COMPONENT_MOD_DETECTOR,
    ],
    "File I/O Components": [
        COMPONENT_FILE_IO,
        COMPONENT_FILE_IO_CORE,
    ],
    "Database Components": [
        COMPONENT_DATABASE,
        COMPONENT_DATABASE_POOL,
    ],
}

# Performance thresholds
PERFORMANCE_THRESHOLD_EXCELLENT = 0.9  # 90% components accelerated
PERFORMANCE_THRESHOLD_GOOD = 0.7       # 70% components accelerated
PERFORMANCE_THRESHOLD_PARTIAL = 0.3    # 30% components accelerated
