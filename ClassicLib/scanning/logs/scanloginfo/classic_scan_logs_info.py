"""Thin wrapper over Rust YamlData for backward compatibility.

This module defines `ClassicScanLogsInfo` as a thin adapter over the Rust
`YamlData` class (from classic_config). All YAML loading and parsing is
handled by Rust -- this class just delegates property access.
"""

from __future__ import annotations

from typing import Any


class ClassicScanLogsInfo:
    """Thin wrapper over Rust YamlData providing backward-compatible access.

    Replaces the former 345-line dataclass that batch-loaded 30 YAML attributes
    via the Python YAML cache. Now all data comes from Rust's YamlDataCore,
    which loads YAML 15-30x faster via yaml-rust2 and Tokio async I/O.

    All properties are read-only delegates to the underlying Rust object.
    VR-aware accessor methods provide per-log field selection.
    """

    def __init__(self) -> None:
        """Create a ClassicScanLogsInfo backed by Rust YamlData.

        Loads YAML configuration using the same directory/game/vr_mode
        resolution as ``get_yamldata()`` in the factory module.

        Raises:
            ImportError: If classic_config Rust module is not available.
            FileNotFoundError: If required YAML files are missing.
            ValueError: If YAML data is malformed.

        """
        from classic_config import YamlData

        from ClassicLib.core.registry import get_game, get_vr
        from ClassicLib.support.resources import ResourceLoader

        data_dir = ResourceLoader.get_data_directory()
        yaml_dirs = [str(data_dir.parent), str(data_dir)]

        self._game = get_game()
        self._vr_mode = get_vr() == "VR"
        self._rust = YamlData(yaml_dirs=yaml_dirs, game=self._game, vr_mode=self._vr_mode)

    @classmethod
    async def create_async(cls) -> ClassicScanLogsInfo:
        """Async factory method (Rust loading is ~20ms, no async overhead needed).

        Returns:
            ClassicScanLogsInfo: Initialized instance with all settings loaded.

        """
        return cls()

    # ── CLASSIC metadata ──────────────────────────────────────────────

    @property
    def classic_game_hints(self) -> list[str]:
        return self._rust.classic_game_hints

    @property
    def classic_records_list(self) -> list[str]:
        return self._rust.classic_records_list

    @property
    def classic_version(self) -> str:
        return self._rust.classic_version

    @property
    def classic_version_date(self) -> str:
        return self._rust.classic_version_date

    # ── Crash generator ───────────────────────────────────────────────

    @property
    def crashgen_name(self) -> str:
        return self._rust.crashgen_name

    @property
    def crashgen_name_vr(self) -> str:
        return self._rust.crashgen_name_vr

    @property
    def crashgen_latest_og(self) -> str:
        return self._rust.crashgen_latest_og

    @property
    def crashgen_latest_vr(self) -> str:
        return self._rust.crashgen_latest_vr

    @property
    def crashgen_ignore(self) -> set[str]:
        return self._rust.crashgen_ignore

    @property
    def crashgen_ignore_vr(self) -> set[str]:
        return self._rust.crashgen_ignore_vr

    # ── Warnings ──────────────────────────────────────────────────────

    @property
    def warn_noplugins(self) -> str:
        return self._rust.warn_noplugins

    @property
    def warn_outdated(self) -> str:
        return self._rust.warn_outdated

    # ── Script extender ───────────────────────────────────────────────

    @property
    def xse_acronym(self) -> str:
        return self._rust.xse_acronym

    # ── Ignore lists ──────────────────────────────────────────────────

    @property
    def game_ignore_plugins(self) -> list[str]:
        return self._rust.game_ignore_plugins

    @property
    def game_ignore_records(self) -> list[str]:
        return self._rust.game_ignore_records

    @property
    def ignore_list(self) -> list[str]:
        return self._rust.ignore_list

    # ── Suspect patterns ──────────────────────────────────────────────

    @property
    def suspects_error_list(self) -> dict[str, Any]:
        return self._rust.suspects_error_list

    @property
    def suspects_stack_list(self) -> dict[str, list[str]]:
        return self._rust.suspects_stack_list

    # ── Mod databases ─────────────────────────────────────────────────

    @property
    def game_mods_conf(self) -> dict[str, Any]:
        return self._rust.game_mods_conf

    @property
    def game_mods_core(self) -> dict[str, Any]:
        return self._rust.game_mods_core

    @property
    def game_mods_core_folon(self) -> dict[str, Any]:
        return self._rust.game_mods_core_folon

    @property
    def game_mods_freq(self) -> dict[str, Any]:
        return self._rust.game_mods_freq

    @property
    def game_mods_opc2(self) -> dict[str, Any]:
        return self._rust.game_mods_opc2

    @property
    def game_mods_solu(self) -> dict[str, Any]:
        return self._rust.game_mods_solu

    # ── Game versions (str, not packaging.version.Version) ────────────

    @property
    def game_version(self) -> str:
        return self._rust.game_version

    @property
    def game_version_new(self) -> str:
        return self._rust.game_version_new

    @property
    def game_version_vr(self) -> str:
        return self._rust.game_version_vr

    # ── Game root names ───────────────────────────────────────────────

    @property
    def game_root_name(self) -> str:
        return self._rust.game_root_name

    @property
    def game_root_name_vr(self) -> str:
        return self._rust.game_root_name_vr

    # ── UI text ───────────────────────────────────────────────────────

    @property
    def autoscan_text(self) -> str:
        return self._rust.autoscan_text

    # ── VR-aware accessor methods ─────────────────────────────────────

    def get_crashgen_name(self, is_vr: bool) -> str:
        """Get crash generator name based on VR mode."""
        return self._rust.crashgen_name_vr if is_vr else self._rust.crashgen_name

    def get_crashgen_ignore(self, is_vr: bool) -> set[str]:
        """Get crash generator ignore set based on VR mode."""
        return self._rust.crashgen_ignore_vr if is_vr else self._rust.crashgen_ignore

    def get_game_root_name(self, is_vr: bool) -> str:
        """Get game root name based on VR mode."""
        return self._rust.game_root_name_vr if is_vr else self._rust.game_root_name

    # ── Bridge to Rust AnalysisConfig ─────────────────────────────────

    def to_rust_config(self) -> Any:
        """Create a Rust AnalysisConfig from the underlying YamlData.

        Uses the stored Rust YamlData directly (no second YAML load).

        Returns:
            AnalysisConfig: Rust analysis configuration for the Orchestrator.

        """
        from classic_scanlog import AnalysisConfig

        return AnalysisConfig.from_yamldata(self._rust, self._game, self._vr_mode)
