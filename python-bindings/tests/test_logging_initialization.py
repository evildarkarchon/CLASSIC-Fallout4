"""Explicit Python initialization must activate the Rust logger without duplicate sinks."""

import os
import subprocess
import sys


def test_explicit_logging_initialization_emits_one_record_per_call():
    """The public initializer is idempotent and honors the caller's log filter."""
    process = subprocess.run(
        [
            sys.executable,
            "-c",
            "import classic_message as m; m.init_logging(); m.init_logging(); m.Logger().info('classic-init-record')",
        ],
        capture_output=True,
        text=True,
        check=False,
        env={**os.environ, "RUST_LOG": "trace", "RUST_LOG_STYLE": "never"},
    )
    assert process.returncode == 0, process.stderr
    assert process.stderr.count("classic-init-record") == 1
    assert "INFO" in process.stderr
