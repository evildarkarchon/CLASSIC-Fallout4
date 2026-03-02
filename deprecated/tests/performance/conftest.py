"""Performance test fixtures and configuration.

This module provides fixtures for performance tests.
"""

from pathlib import Path

import pytest


@pytest.fixture(scope="session", autouse=True)
def ensure_classic_ignore_yaml():
    """Ensure CLASSIC Ignore.yaml exists in the project root.

    The Rust YamlData constructor eagerly loads all YAML files from yaml_dirs
    (which includes the project root). If CLASSIC Ignore.yaml doesn't exist,
    it raises an OSError and prevents ClassicOrchestrator from initializing.

    This fixture creates a minimal valid CLASSIC Ignore.yaml if it doesn't
    exist, and removes it after the session only if we created it.
    """
    ignore_path = Path("CLASSIC Ignore.yaml")
    created_by_fixture = False

    if not ignore_path.exists():
        # Write a minimal valid YAML ignore file that matches the expected schema.
        # The Rust YamlData constructor requires a non-empty YAML document with
        # the CLASSIC_Ignore_* structure (plain comments produce an empty document
        # which causes a ValueError).
        ignore_path.write_text(
            "# This file contains plugin names that CLASSIC will IGNORE while scanning crash logs.\n"
            "# Created automatically for performance tests.\n\n"
            "CLASSIC_Ignore_Fallout4: []\n\n"
            "CLASSIC_Ignore_SkyrimSE: []\n",
            encoding="utf-8",
        )
        created_by_fixture = True

    yield

    if created_by_fixture and ignore_path.exists():
        ignore_path.unlink()
