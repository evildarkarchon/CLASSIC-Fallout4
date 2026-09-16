"""Observe Installed YAML Data through public bindings in isolated file trees."""

from __future__ import annotations

import hashlib
import os
import tempfile
from collections.abc import Mapping
from pathlib import Path
from typing import Any

CACHE_ENVIRONMENT = ("LOCALAPPDATA", "APPDATA", "XDG_CACHE_HOME", "HOME")
IGNORE_PATH = "installation/CLASSIC Data/CLASSIC Ignore.yaml"


def _owned_path(root: Path, path: str) -> Path:
    """Reject fixture paths outside the disposable scenario workspace."""
    target = (root / path).resolve()
    if Path(path).is_absolute() or target == root or not target.is_relative_to(root):
        raise ValueError(f"fixture path is outside its workspace: {path}")
    return target


def _path(root: Path, value: str | Path | None) -> str | None:
    """Reduce native absolute paths to portable scenario-relative attribution."""
    return None if value is None else Path(value).relative_to(root).as_posix()


def _materialize(root: Path, files: Mapping[str, str]) -> None:
    """Write exact UTF-8 input bytes without consulting host YAML data or expectations."""
    for path, content in files.items():
        if not isinstance(content, str):
            raise TypeError("fixture file content must be UTF-8 text")
        target = _owned_path(root, path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content.encode("utf-8"))


def _identity(value: Any, path: str, length: str = "byte_len") -> dict[str, Any]:
    """Project the public DTO's exact hash and byte length with source attribution."""
    return {"path": path, "sha256": value.sha256, "byteLength": getattr(value, length)}


def _selected_file(value: Any) -> dict[str, Any]:
    """Attribute native selected-file identity using its public role and provenance."""
    name = "CLASSIC Main.yaml" if value.role == "main" else "CLASSIC Fallout4.yaml"
    if value.provenance == "bundled":
        path = f"installation/CLASSIC Data/databases/{name}"
    else:
        suffix = ".prev" if value.provenance == "previous" else ""
        path = f"cache/CLASSIC/yaml-cache/{name}{suffix}"
    return {
        "role": value.role,
        "provenance": value.provenance,
        "schemaVersion": f"{value.schema_major}.{value.schema_minor}",
        "identity": _identity(value, path, "byte_length"),
    }


def _diagnostics(root: Path, values: Any) -> list[dict[str, Any]]:
    """Preserve ordered structured attribution independently of diagnostic prose."""
    return [
        {
            "role": item.role,
            "candidate": item.candidate,
            "path": _path(root, item.path),
            "kind": item.kind,
        }
        for item in values
    ]


def _files(root: Path) -> list[dict[str, Any]]:
    """Re-read durable regular files after native execution and explicit mutations."""
    result = []
    for path in root.rglob("*"):
        if path.is_symlink():
            raise ValueError("unexpected symbolic link in scenario workspace")
        if path.is_dir():
            continue
        content = path.read_bytes()
        result.append(
            {
                "path": _path(root, path),
                "sha256": hashlib.sha256(content).hexdigest(),
                "byteLength": len(content),
            }
        )
    return sorted(result, key=lambda item: item["path"])


def observe_installed_yaml(fixture: Mapping[str, Any]) -> dict[str, Any]:
    """Invoke public installed-data operations while owning every cache fallback path.

    Cases execute sequentially because the native resolver reads process environment.
    Environment restoration and disposable-tree cleanup also run on adapter failures.
    """
    import classic_config

    previous = {name: os.environ.get(name) for name in CACHE_ENVIRONMENT}
    with tempfile.TemporaryDirectory(
            prefix="classic-python-installed-conformance-"
    ) as temporary:
        root = Path(temporary).resolve()
        try:
            (root / "installation").mkdir()
            _materialize(root, fixture["files"])
            for name in CACHE_ENVIRONMENT:
                os.environ[name] = str(root / "cache")
            games = {
                "Fallout4": classic_config.ExplicitYamlDataGame.FALLOUT4,
                "Fallout4VR": classic_config.ExplicitYamlDataGame.FALLOUT4_VR,
                "Skyrim": classic_config.ExplicitYamlDataGame.SKYRIM,
                "Starfield": classic_config.ExplicitYamlDataGame.STARFIELD,
            }
            game = games[fixture["game"]]
            observation: dict[str, Any] = {
                "outcome": "error",
                "game": None,
                "gameDataRole": None,
                "main": None,
                "gameFile": None,
                "localIgnore": None,
                "recovery": None,
                "snapshot": None,
                "diagnostics": [],
                "error": None,
                "files": [],
            }
            selected = snapshot = recovery = None
            backup_alias = None
            try:
                if fixture["operation"] == "inspect":
                    selected = classic_config.inspect_installed_yaml_data(
                        root / "installation", game
                    )
                    observation["outcome"] = "inspected"
                elif fixture["operation"] == "load":
                    outcome = classic_config.load_installed_yaml_data(
                        root / "installation", game, fixture["selectedGameVersion"]
                    )
                    if isinstance(outcome, classic_config.InstalledYamlDataLoadOutcome):
                        selected = snapshot = outcome.snapshot
                        observation["outcome"] = outcome.status
                    elif isinstance(
                            outcome,
                            classic_config.InstalledYamlDataLocalIgnoreRecoveryRequiredOutcome,
                    ):
                        selected = recovery = outcome.recovery_plan
                        if outcome.status != "local_ignore_recovery_required":
                            raise ValueError(
                                "native recovery outcome has an unexpected status"
                            )
                        observation["outcome"] = "recovery_required"
                    else:
                        raise ValueError(
                            "native load outcome has no status-selected payload"
                        )
                else:
                    raise ValueError("unsupported installed-data operation")
            except (
                    classic_config.InstalledYamlDataInspectionError,
                    classic_config.InstalledYamlDataLoadError,
            ) as error:
                # Shared roles are update-eligible Main/game; Local Ignore is identified by code.
                observation["error"] = {
                    "code": error.code,
                    "role": error.yaml_role
                    if error.yaml_role in ("main", "game")
                    else None,
                }
                observation["diagnostics"] = _diagnostics(root, error.diagnostics)
            # Project after mutation so retained hashes and parsed data must come from the handle.
            _materialize(root, fixture.get("mutations", {}))
            if selected is not None:
                observation.update(
                    game=str(selected.game),
                    gameDataRole=selected.game_data_role,
                    main=_selected_file(selected.main),
                    gameFile=_selected_file(selected.game_file),
                    diagnostics=_diagnostics(root, selected.diagnostics),
                )
            if snapshot is not None:
                observation["localIgnore"] = {
                    "state": snapshot.local_ignore_state,
                    "identity": _identity(snapshot.local_ignore_identity, IGNORE_PATH),
                }
                observation["snapshot"] = {
                    "classicVersion": snapshot.yaml_data.classic_version,
                    "gameRootName": snapshot.yaml_data.game_root_name,
                    "ignoreList": snapshot.yaml_data.ignore_list,
                    "simplifyRemoveList": snapshot.simplify_remove_list,
                }
            if recovery is not None:
                defaults = recovery.default_local_ignore_identity
                observation["recovery"] = {
                    "localIgnorePath": _path(root, recovery.local_ignore_path),
                    "malformedIdentity": _identity(
                        recovery.malformed_local_ignore_identity, IGNORE_PATH
                    ),
                    "defaultIdentity": None
                    if defaults is None
                    else _identity(defaults, IGNORE_PATH),
                    "selectedGameVersion": recovery.selected_game_version,
                }
                if fixture.get("recoveryAction") == "proceed":
                    snapshot = recovery.proceed_without_ignore()
                    observation["outcome"] = "proceeded"
                    observation["localIgnore"] = {
                        "state": snapshot.local_ignore_state,
                        "identity": _identity(
                            snapshot.local_ignore_identity, IGNORE_PATH
                        ),
                    }
                    observation["snapshot"] = {
                        "classicVersion": snapshot.yaml_data.classic_version,
                        "gameRootName": snapshot.yaml_data.game_root_name,
                        "ignoreList": snapshot.yaml_data.ignore_list,
                        "simplifyRemoveList": snapshot.simplify_remove_list,
                    }
                elif fixture.get("recoveryAction") == "reset":
                    reset = recovery.reset_to_default()
                    if reset.status == "conflict":
                        observation["outcome"] = "reset_conflict"
                        observation["recovery"]["decision"] = {
                            "status": reset.status,
                            "expectedIdentity": _identity(
                                reset.expected_identity, IGNORE_PATH
                            ),
                            "actualIdentity": None
                            if reset.actual_identity is None
                            else _identity(reset.actual_identity, IGNORE_PATH),
                            "backupPath": None
                            if reset.backup_path is None
                            else _path(root, reset.backup_path),
                        }
                    elif reset.status == "reset":
                        # Normalize only the process-unique name, after validating ownership and content-addressed stem.
                        backup_alias = _path(root, reset.backup_path)
                        stem = (
                                "installation/CLASSIC Backup/YAML Data/Local Ignore/CLASSIC Ignore.yaml."
                                + reset.malformed_local_ignore_identity.sha256
                                + "."
                        )
                        if not backup_alias.startswith(
                                stem
                        ) or not backup_alias.endswith(".bak"):
                            raise ValueError(
                                "reset backup is outside its owned content-addressed namespace"
                            )
                        backup_name = "installation/CLASSIC Backup/YAML Data/Local Ignore/<backup>"
                        observation["outcome"] = "reset"
                        observation["recovery"]["decision"] = {
                            "status": reset.status,
                            "localIgnorePath": _path(root, reset.local_ignore_path),
                            "malformedIdentity": _identity(
                                reset.malformed_local_ignore_identity, IGNORE_PATH
                            ),
                            "backupIdentity": _identity(
                                reset.backup_identity, backup_name
                            ),
                            "replacementIdentity": _identity(
                                reset.replacement_identity, IGNORE_PATH
                            ),
                        }
                        observation["diagnostics"] = _diagnostics(
                            root, reset.diagnostics
                        )
                        snapshot = reset.snapshot
                        observation["localIgnore"] = {
                            "state": snapshot.local_ignore_state,
                            "identity": _identity(
                                snapshot.local_ignore_identity, IGNORE_PATH
                            ),
                        }
                        observation["snapshot"] = {
                            "classicVersion": snapshot.yaml_data.classic_version,
                            "gameRootName": snapshot.yaml_data.game_root_name,
                            "ignoreList": snapshot.yaml_data.ignore_list,
                            "simplifyRemoveList": snapshot.simplify_remove_list,
                        }
                    else:
                        raise ValueError("unsupported native reset status")
            observation["files"] = _files(root)
            if backup_alias is not None:
                for file in observation["files"]:
                    if file["path"] == backup_alias:
                        file["path"] = (
                            "installation/CLASSIC Backup/YAML Data/Local Ignore/<backup>"
                        )
                observation["files"].sort(key=lambda file: file["path"])
            return observation
        finally:
            for name, value in previous.items():
                if value is None:
                    os.environ.pop(name, None)
                else:
                    os.environ[name] = value
