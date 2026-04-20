"""Smoke tests for the yaml-update-delivery PyO3 surface.

These tests verify that the ``check_yaml_update`` / ``apply_yaml_update`` /
``rollback_yaml_update`` surface exists, accepts valid inputs, and honors
the ``Update Check: false`` short-circuit without requiring network access
or a populated yaml-cache directory.

If the compiled ``classic_update`` extension hasn't been built yet (cold
clone / fresh CI), these tests skip gracefully so ``pytest`` collection
still works.
"""

from __future__ import annotations

import pytest


classic_update = pytest.importorskip(
    "classic_update",
    reason="classic_update extension not built; run `maturin develop` first",
)


def _main_entry() -> "classic_update.YamlClientSchemaEntry":
    """Canonical entry for ``CLASSIC Main.yaml`` matching the client_schemas
    constants in ``classic-config-core::client_schemas::MAIN_YAML``."""
    return classic_update.YamlClientSchemaEntry(
        name="CLASSIC Main.yaml",
        accepted_major=1,
        accepted_minimum_minor=0,
    )


def test_yaml_client_schema_entry_defaults() -> None:
    entry = _main_entry()
    assert entry.name == "CLASSIC Main.yaml"
    assert entry.accepted_major == 1
    assert entry.accepted_minimum_minor == 0
    # When has_installed is not set, installed_major/installed_minor are 0
    # but ignored by the orchestrator.
    assert entry.has_installed is False
    assert entry.installed_major == 0
    assert entry.installed_minor == 0


def test_check_yaml_update_disabled_short_circuits() -> None:
    # Unroutable Pages URL — if the short-circuit regresses, this would
    # hang on connect or come back with ``tag != "disabled"``.
    status = classic_update.check_yaml_update(
        "http://127.0.0.1:1/manifest-latest.json",
        "yaml-data-v",
        [_main_entry()],
        False,  # enabled
    )
    assert status.tag == "disabled"
    assert status.compatible_files == []
    assert status.incompatible_files == []
    assert status.unknown_reason == ""


def test_check_yaml_update_accepts_bundled_yaml_dir_kwarg() -> None:
    # Regression for Codex adversarial review finding:
    #   "Bundled-version enrichment is tied to current_exe(), so Node/Python
    #    clean installs will false-positive forever."
    #
    # Python hosts running inside ``python.exe`` cannot rely on the bridge's
    # ``current_exe()`` fallback — that would resolve the interpreter
    # directory, not the CLASSIC install. The PyO3 surface MUST accept an
    # explicit ``bundled_yaml_dir`` so clean installs whose packaged bytes
    # already match the manifest can be classified as ``upToDate`` instead
    # of false-positive ``updateAvailable``.
    #
    # This smoke test verifies the parameter is accepted by the binding. A
    # full end-to-end classification test (bundled_yaml_dir populated with
    # bytes matching a mocked manifest → status "upToDate") lives in the
    # Rust integration test suite at
    # ``business-logic/classic-update-core/tests/yaml_update_tests.rs``
    # (``check_yaml_update_uses_explicit_bundled_dir_for_clean_install``),
    # where mockito is already wired up.
    status = classic_update.check_yaml_update(
        "http://127.0.0.1:1/manifest-latest.json",
        "yaml-data-v",
        [_main_entry()],
        False,  # enabled → short-circuits regardless of bundled_yaml_dir
        bundled_yaml_dir="/nonexistent/path",
    )
    assert status.tag == "disabled"


def test_rollback_yaml_update_unknown_file_is_no_previous_version() -> None:
    # No file by this name exists in the yaml-cache; rollback must succeed
    # with rolled_back=False. Accept either outcome:
    # - Normal steady state: rolled_back=False with a valid file_name.
    # - Cache-dir unresolvable (no LOCALAPPDATA/HOME): RuntimeError.
    try:
        outcome = classic_update.rollback_yaml_update(
            "__pytest_definitely_nonexistent_file_xyzzy__.yaml",
        )
    except RuntimeError:
        # Acceptable on a machine with no cache root — the binding
        # surfaced it as RuntimeError rather than panicking.
        return
    assert outcome.rolled_back is False
    assert outcome.file_name == "__pytest_definitely_nonexistent_file_xyzzy__.yaml"
