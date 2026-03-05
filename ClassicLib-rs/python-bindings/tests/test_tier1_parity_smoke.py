"""Tier-1 parity smoke tests for maintained Python bindings."""

from __future__ import annotations

from .fixtures.tier1_parity_fixtures import (
    PARITY_GAME_YAML,
    PARITY_IGNORE_YAML,
    PARITY_MAIN_YAML,
)


def test_imports_and_versions() -> None:
    import classic_config
    import classic_pybridge
    import classic_scanlog
    import classic_version_registry

    assert isinstance(classic_config.__version__, str)
    assert isinstance(classic_pybridge.__version__, str)
    assert isinstance(classic_scanlog.__version__, str)
    assert isinstance(classic_version_registry.__version__, str)


def test_config_smoke() -> None:
    import classic_config

    data = classic_config.YamlData.from_yaml_content(
        PARITY_MAIN_YAML,
        PARITY_GAME_YAML,
        PARITY_IGNORE_YAML,
        "Fallout4",
        "auto",
    )
    assert data.classic_version == "9.0.0"
    assert data.xse_acronym == "F4SE"
    assert data.crashgen_name == "Buffout 4"
    classic_config.clear_yaml_cache()


def test_scanlog_smoke() -> None:
    import classic_scanlog

    parser = classic_scanlog.LogParser()
    assert parser.detect_vr_log("Fallout4VR.exe") is True
    assert isinstance(
        classic_scanlog.extract_formids_batch([["Form ID: FF001234"]]), list
    )


def test_version_registry_smoke() -> None:
    import classic_version_registry

    registry = classic_version_registry.get_version_registry()
    assert registry is not None

    info = registry.get_by_id("FO4_OG")
    assert info is not None
    assert info.short_name == "OG"

    result = classic_version_registry.match_version_string(
        "1.10.163.0", "Fallout4", False
    )
    assert result.is_valid is True


def test_pybridge_smoke() -> None:
    import classic_pybridge

    classic_pybridge.clear_metrics()
    classic_pybridge.record_operation(
        classic_pybridge.BridgeOperationType.RunAsync, 0.01, True
    )
    metrics = classic_pybridge.get_metrics()
    assert metrics.run_async_count >= 1

    info = classic_pybridge.get_runtime_info()
    assert info.available is True
