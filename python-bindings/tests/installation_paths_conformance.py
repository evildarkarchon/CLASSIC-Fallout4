"""Observe cached paths and missing INI reports against an invocation-owned tree."""

import os
import stat
import tempfile
from pathlib import Path


def observe_installation_paths(fixture):
    """Execute native public methods with valid caches, restoring cwd before cleanup."""
    import classic_path

    game, docs = fixture["gamePath"], fixture["docsPath"]
    if (game, docs) not in {("game", "docs"), ("Game Folder", "Docs Folder")}:
        raise ValueError("unsupported installation cache paths")
    with tempfile.TemporaryDirectory(
        prefix="classic-installation-conformance-"
    ) as directory:
        root = Path(directory)
        (root / game).mkdir()
        (root / docs).mkdir()
        (root / "CLASSIC Main.yaml").write_bytes(
            fixture["registryYaml"].encode("utf-8")
        )
        if fixture["files"] != {game + "/Fallout4.exe": "owned executable marker"}:
            raise ValueError("installation fixture needs a valid cached executable")
        (root / game / "Fallout4.exe").write_bytes(b"owned executable marker")
        previous = Path.cwd()
        try:
            # Relative inputs keep host parent names (for example OneDrive) out
            # of the public path checker. Receipt processes execute serially.
            os.chdir(root)
            game_finder = classic_path.GamePathFinder(
                "Fallout4.exe", None, "Fallout4", False
            )
            docs_finder = classic_path.DocsPathFinder("My Games/Fallout4")
            docs_finder.set_steam_app_id(12345)
            game_finder.validate_game_path(game)
            docs_finder.validate_docs_path(docs)
            result = {
                "gamePath": game_finder.find_game_path(
                    cached_path=game, xse_log_path=None
                ),
                "docsPath": docs_finder.find_docs_path(cached_path=docs),
                "checks": classic_path.DocumentsChecker("Fallout4").run_all_checks(
                    docs
                ),
            }
            checker = classic_path.DocumentsChecker("Fallout4")
            if checker.check_onedrive_in_path(docs) is not None:
                raise ValueError("owned documents path unexpectedly reports OneDrive")
            for index, name in enumerate(
                ("Fallout4.ini", "Fallout4Custom.ini", "Fallout4Prefs.ini")
            ):
                check = checker.validate_ini_file(docs, name)
                if (
                    check.exists
                    or check.is_valid
                    or not check.has_issue()
                    or check.ini_name != name
                    or check.message != result["checks"][index]
                ):
                    raise ValueError(
                        "per-file INI diagnosis disagrees with aggregate check"
                    )
            docs_finder.validate_ini_files(docs, [])
            try:
                docs_finder.validate_ini_files(docs, ["Fallout4.ini"])
            except (FileNotFoundError, ValueError) as failure:
                if "Fallout4.ini" not in str(failure):
                    raise
            else:
                raise ValueError("missing required INI was accepted")
            # Keep lexical restriction checks independent of host Temp folders
            # (which commonly include AppData) using an owned relative subtree.
            scan = Path("validation/owned/scan")
            scan.mkdir(parents=True)
            validator = classic_path.PathValidator
            validator.validate_custom_scan_path(str(scan))
            validator.validate_settings_path(game, "Game Path", ["Fallout4.exe"])
            validator.validate_settings_paths(game, docs, str(scan), "Fallout4.exe")
            validator.check_drive_exists(str(root))
            validator.check_read_permissions(game)
            validator.check_write_permissions(game)
            validator.validate_path_with_permissions(game, True, True)
            if not validator.is_valid_path(game) or validator.is_valid_path(
                "missing-path"
            ):
                raise ValueError("path existence alias disagrees with owned tree")
            validator.validate_required_files(game, ["Fallout4.exe"])
            try:
                validator.validate_required_files(game, ["missing.ini"])
            except FileNotFoundError as failure:
                if "missing.ini" not in str(failure):
                    raise
            else:
                raise ValueError("required-files alias accepted an absent file")
            readonly_file = scan / "readonly.txt"
            readonly_file.write_bytes(b"retained bytes")
            readonly_file.chmod(stat.S_IREAD)
            if readonly_file.stat().st_mode & stat.S_IWRITE:
                raise ValueError("readonly precondition was not established")
            classic_path.remove_readonly(str(readonly_file))
            if (
                not readonly_file.stat().st_mode & stat.S_IWRITE
                or readonly_file.read_bytes() != b"retained bytes"
            ):
                raise ValueError(
                    "readonly removal changed bytes or failed to restore write access"
                )
            readonly_file.unlink()
            if validator.is_restricted_path(
                str(scan)
            ) or not validator.is_restricted_path("Windows/System32/test"):
                raise ValueError(
                    "restricted-path classification disagrees with owned input"
                )
            if not validator.is_valid_executable_path(
                game + "/Fallout4.exe"
            ) or validator.is_valid_executable_path("CLASSIC Main.yaml"):
                raise ValueError(
                    "executable path classification lost file extension semantics"
                )
            scan.rmdir()
            scan.parent.rmdir()
            scan.parent.parent.rmdir()
            log_path = Path("path-detection.log")
            log_path.write_text(
                f'plugin directory = "{game}/Data/F4SE/Plugins"\n', encoding="utf-8"
            )
            if classic_path.GamePathFinder.parse_xse_log(str(log_path)) != game:
                raise ValueError("XSE log path extraction did not preserve game root")
            log_path.unlink()
            result["files"] = [
                {
                    "path": path.relative_to(root).as_posix(),
                    "content": path.read_bytes().decode("utf-8"),
                }
                for path in sorted(root.rglob("*"))
                if path.is_file()
            ]
            result["directories"] = sorted(
                path.relative_to(root).as_posix()
                for path in root.rglob("*")
                if path.is_dir()
            )
            return result
        finally:
            os.chdir(previous)
