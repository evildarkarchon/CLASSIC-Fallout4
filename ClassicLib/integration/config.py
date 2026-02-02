"""Integration Configuration Module.

Contains the environment variable name for disabling Rust acceleration.
The canonical constant now lives in factory.py; this module exists for
backward compatibility with any remaining imports.
"""

# Environment variable to disable Rust acceleration
DISABLE_RUST_ENV_VAR = "CLASSIC_DISABLE_RUST"
