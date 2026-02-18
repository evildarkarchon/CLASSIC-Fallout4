"""Unit tests for crashgen checker logic using synthetic data only.

These tests avoid coupling to production VersionRegistry YAML content. Registry-backed
contract checks live in test_crashgen_checker_integration.py.
"""

from __future__ import annotations

from dataclasses import dataclass

import pytest
from packaging.version import Version

from ClassicLib.support.versions import (
    CrashgenConfig,
    CrashgenVersionResult,
    CrashgenVersionStatus,
    check_crashgen_version,
    check_crashgen_version_for_detected_game,
    get_matching_crashgen_config,
)
from ClassicLib.support.versions.models import CompatibleRange, VersionInfo

pytestmark = pytest.mark.unit


@dataclass
class _StubMatchResult:
    version_info: VersionInfo | None


class _StubVersionInfo:
    def __init__(self, crashgen_versions: tuple[CrashgenConfig, ...]) -> None:
        self.crashgen_versions = crashgen_versions

    def get_crashgen_for_version(self, crashgen_version: str) -> CrashgenConfig | None:
        for config in self.crashgen_versions:
            if config.version == crashgen_version:
                return config
        return None


class _StubRegistry:
    def __init__(self, by_id: dict[str, tuple[CrashgenConfig, ...]], match_version_info: VersionInfo | None = None) -> None:
        self._by_id = by_id
        self._match_version_info = match_version_info

    def get_crashgen_configs(self, version_id: str) -> tuple[CrashgenConfig, ...]:
        return self._by_id.get(version_id, ())

    def get_by_id(self, version_id: str) -> _StubVersionInfo | None:
        configs = self._by_id.get(version_id)
        if configs is None:
            return None
        return _StubVersionInfo(configs)

    def match_version(self, detected: Version, game: str = "Fallout4", is_vr: bool = False) -> _StubMatchResult:  # noqa: ARG002
        return _StubMatchResult(version_info=self._match_version_info)


class TestCrashgenVersionStatusAndResult:
    def test_status_enum_values(self):
        assert CrashgenVersionStatus.VALID.value == "valid"
        assert CrashgenVersionStatus.OUTDATED.value == "outdated"
        assert CrashgenVersionStatus.NEWER_THAN_KNOWN.value == "newer_than_known"
        assert CrashgenVersionStatus.NO_SUPPORTED_VERSION.value == "no_supported_version"
        assert CrashgenVersionStatus.UNKNOWN_GAME_VERSION.value == "unknown_game_version"

    def test_result_properties(self):
        valid_result = CrashgenVersionResult(
            status=CrashgenVersionStatus.VALID,
            detected_version=Version("1.7.1"),
            valid_versions=("1.7.1",),
            game_version_id="TEST_GAME",
            message="ok",
        )
        assert valid_result.is_valid is True
        assert valid_result.needs_update is False

        outdated_result = CrashgenVersionResult(
            status=CrashgenVersionStatus.OUTDATED,
            detected_version=Version("1.0.0"),
            valid_versions=("1.7.1",),
            game_version_id="TEST_GAME",
            message="old",
        )
        assert outdated_result.is_valid is False
        assert outdated_result.needs_update is True


class TestCheckCrashgenVersionWithSyntheticRegistry:
    def test_valid_status(self, monkeypatch: pytest.MonkeyPatch):
        stub_registry = _StubRegistry({"TEST_GAME": (CrashgenConfig(version="1.7.1", name="Test Logger"),)})
        monkeypatch.setattr("ClassicLib.support.versions.core.get_version_registry", lambda: stub_registry)

        result = check_crashgen_version(Version("1.7.1"), "TEST_GAME")
        assert result.status == CrashgenVersionStatus.VALID
        assert result.matched_config is not None
        assert result.matched_config.version == "1.7.1"

    def test_outdated_status(self, monkeypatch: pytest.MonkeyPatch):
        stub_registry = _StubRegistry({"TEST_GAME": (CrashgenConfig(version="1.7.1"),)})
        monkeypatch.setattr("ClassicLib.support.versions.core.get_version_registry", lambda: stub_registry)

        result = check_crashgen_version(Version("1.0.0"), "TEST_GAME")
        assert result.status == CrashgenVersionStatus.OUTDATED

    def test_newer_than_known_status(self, monkeypatch: pytest.MonkeyPatch):
        stub_registry = _StubRegistry({"TEST_GAME": (CrashgenConfig(version="1.7.1"), CrashgenConfig(version="1.0.0"))})
        monkeypatch.setattr("ClassicLib.support.versions.core.get_version_registry", lambda: stub_registry)

        result = check_crashgen_version(Version("2.0.0"), "TEST_GAME")
        assert result.status == CrashgenVersionStatus.NEWER_THAN_KNOWN
        assert result.valid_versions == ("1.7.1", "1.0.0")

    def test_no_supported_version_status(self, monkeypatch: pytest.MonkeyPatch):
        stub_registry = _StubRegistry({})
        monkeypatch.setattr("ClassicLib.support.versions.core.get_version_registry", lambda: stub_registry)

        result = check_crashgen_version(Version("1.0.0"), "UNKNOWN_GAME")
        assert result.status == CrashgenVersionStatus.NO_SUPPORTED_VERSION

    def test_get_matching_config_uses_registry_lookup(self, monkeypatch: pytest.MonkeyPatch):
        configs = (CrashgenConfig(version="1.7.1", name="Test Logger"),)
        stub_registry = _StubRegistry({"TEST_GAME": configs})
        monkeypatch.setattr("ClassicLib.support.versions.core.get_version_registry", lambda: stub_registry)

        config = get_matching_crashgen_config(Version("1.7.1"), "TEST_GAME")
        assert config is not None
        assert config.version == "1.7.1"


class TestDetectedGameValidationWithSyntheticRegistry:
    def test_unknown_game_version(self, monkeypatch: pytest.MonkeyPatch):
        stub_registry = _StubRegistry({}, match_version_info=None)
        monkeypatch.setattr("ClassicLib.support.versions.core.get_version_registry", lambda: stub_registry)

        result = check_crashgen_version_for_detected_game(
            detected_crashgen=Version("1.7.1"),
            detected_game_version=Version("9.9.9.9"),
            is_vr=False,
        )
        assert result.status == CrashgenVersionStatus.UNKNOWN_GAME_VERSION

    def test_detected_game_valid(self, monkeypatch: pytest.MonkeyPatch):
        version_info = VersionInfo(
            id="TEST_GAME",
            game="Fallout4",
            is_vr=False,
            version=Version("1.0.0"),
            crashgen_versions=(CrashgenConfig(version="1.7.1", name="Test Logger"),),
        )
        stub_registry = _StubRegistry({}, match_version_info=version_info)
        monkeypatch.setattr("ClassicLib.support.versions.core.get_version_registry", lambda: stub_registry)

        result = check_crashgen_version_for_detected_game(
            detected_crashgen=Version("1.7.1"),
            detected_game_version=Version("1.0.0"),
            is_vr=False,
        )
        assert result.status == CrashgenVersionStatus.VALID
        assert result.game_version_id == "TEST_GAME"


class TestCrashgenAndVersionInfoModels:
    def test_crashgen_config_from_version_string(self):
        config = CrashgenConfig.from_version_string("1.7.1")
        assert config.version == "1.7.1"
        assert config.name == ""

    def test_crashgen_config_compatibility_with_range(self):
        version_range = CompatibleRange.from_strings("1.10.100.0", "1.10.200.0")
        config = CrashgenConfig(version="1.7.1", compatible_range=version_range)

        assert config.is_compatible_with(Version("1.10.150.0")) is True
        assert config.is_compatible_with(Version("1.10.300.0")) is False

    def test_version_info_crashgen_helpers(self):
        og_range = CompatibleRange.from_strings("1.10.163.0", "1.10.163.999")
        ng_range = CompatibleRange.from_strings("1.10.984.0", "1.10.999.999")
        version_info = VersionInfo(
            id="TEST",
            game="Fallout4",
            is_vr=False,
            version=Version("1.10.163.0"),
            crashgen_versions=(
                CrashgenConfig(version="1.28.6", compatible_range=og_range),
                CrashgenConfig(version="1.37.0", compatible_range=ng_range),
                CrashgenConfig(version="1.0.0"),
            ),
        )

        assert version_info.get_crashgen_version_strings() == ("1.28.6", "1.37.0", "1.0.0")
        assert version_info.get_crashgen_for_version("1.37.0") is not None
        assert version_info.get_crashgen_for_version("9.9.9") is None

        og_compatible = {c.version for c in version_info.get_compatible_crashgens(Version("1.10.163.0"))}
        ng_compatible = {c.version for c in version_info.get_compatible_crashgens(Version("1.10.984.0"))}

        assert og_compatible == {"1.28.6", "1.0.0"}
        assert ng_compatible == {"1.37.0", "1.0.0"}
