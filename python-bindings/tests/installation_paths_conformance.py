"""Observe cached paths and missing INI reports against an invocation-owned tree."""

import os
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
