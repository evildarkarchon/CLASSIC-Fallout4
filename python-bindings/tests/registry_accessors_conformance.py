"""Registry accessor observations from test-owned process state and paths."""

from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any


def _context(registry: Any) -> dict[str, Any]:
    """Read all optional references and preferences without replacing absent values."""
    return {
        "yamlCache": registry.get_yaml_cache(),
        "manualDocs": registry.get_manual_docs_gui(),
        "gamePath": registry.get_game_path_gui(),
        "autoDetected": registry.is_version_auto_detected(),
        "xseValid": registry.is_xse_valid(),
        "enbPresent": registry.is_enb_present(),
        "version": registry.get_game_version_string(),
    }


def observe_registry_accessors(family: str, fixture: dict[str, Any]) -> dict[str, Any]:
    """Invoke public accessors and always clear the dedicated process's registry."""
    import classic_registry as registry

    registry.clear_all()
    try:
        request = fixture["request"]
        if family == "registry-game":
            registry.set_game(request["game"])
            game = registry.get_game()
            registry.set_game(request["replacement"])
            replacement = registry.get_game()
            registry.clear_all()
            return {
                "key": registry.Keys.GAME,
                "game": game,
                "replacement": replacement,
                "afterClearPresent": registry.is_registered(registry.Keys.GAME),
            }
        if family == "registry-gui":
            default = registry.is_gui_mode()
            registry.register(registry.Keys.IS_GUI_MODE, True)
            enabled = registry.is_gui_mode()
            registry.register(registry.Keys.IS_GUI_MODE, False)
            disabled = registry.is_gui_mode()
            registry.clear_all()
            return {
                "key": registry.Keys.IS_GUI_MODE,
                "default": default,
                "enabled": enabled,
                "disabled": disabled,
                "afterClear": registry.is_gui_mode(),
            }
        with TemporaryDirectory(prefix="classic-registry-") as directory:
            root = Path(directory)
            if family == "registry-paths":
                initial = registry.get_application_dir()
                registry.set_application_dir(str(root / "first"))
                path = Path(registry.get_application_dir()).relative_to(root).as_posix()
                registry.set_application_dir(str(root / "second"))
                replacement = (
                    Path(registry.get_application_dir()).relative_to(root).as_posix()
                )
                registry.clear_all()
                return {
                    "initial": initial,
                    "path": path,
                    "replacement": replacement,
                    "afterClear": registry.get_application_dir(),
                    "files": sorted(p.name for p in root.iterdir()),
                }
            if family != "registry-context":
                raise ValueError("unknown registry accessor family")
            initial = _context(registry)
            for key in (
                registry.Keys.YAML_CACHE,
                registry.Keys.MANUAL_DOCS_GUI,
                registry.Keys.GAME_PATH_GUI,
            ):
                registry.register(key, request["value"])
            # Python treats an empty version as absent; use a separate nonempty input.
            registry.register(registry.Keys.GAME_VERSION, request["version"])
            for key in (
                registry.Keys.VERSION_AUTO_DETECTED,
                registry.Keys.XSE_VALID,
                registry.Keys.ENB_PRESENT,
            ):
                registry.register(key, True)
            registry.register(registry.Keys.LOCAL_DIR, str(root / "local"))
            local = Path(registry.get_local_dir()).relative_to(root).as_posix()
            stored = _context(registry)
            registry.clear_all()
            return {
                "initial": initial,
                "stored": stored,
                "afterClear": _context(registry),
                "localDir": local,
                "files": sorted(p.name for p in root.iterdir()),
            }
    finally:
        # Failure cleanup prevents a later scenario inheriting process-global values.
        registry.clear_all()
