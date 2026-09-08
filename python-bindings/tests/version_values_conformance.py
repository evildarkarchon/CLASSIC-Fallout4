"""Public game-version values and Fallout 4 variants from controlled registry bytes."""

import os
from pathlib import Path
from tempfile import TemporaryDirectory


def observe_version_values(family, fixture):
    """Observe public values; each dedicated process initializes the singleton from inputs."""
    import classic_version_registry as versions

    request = fixture["request"]
    if family == "game-version-parse":
        try:
            native = versions.GameVersion(request["version"])
            return {"parsed": str(native)}
        except ValueError:
            # CXX exposes only valid=false, so error text is outside this common fact.
            return {"parsed": None}
    if family in {"game-version-distance", "game-version-order"}:
        a, b = versions.GameVersion(request["a"]), versions.GameVersion(request["b"])
        if family == "game-version-distance":
            return {"distance": a.semantic_distance(b)}
        return {
            "equal": a == b,
            "less": a < b,
            "lessEqual": a <= b,
            "greater": a > b,
            "greaterEqual": a >= b,
            "sameMajor": a.same_major(b),
            "hashEqualCopy": hash(a) == hash(versions.GameVersion(request["a"])),
        }
    with TemporaryDirectory(prefix="classic-version-values-") as directory:
        root = Path(directory)
        previous = Path.cwd()
        try:
            (root / "CLASSIC Main.yaml").write_text(
                fixture["registryYaml"], encoding="utf-8", newline=""
            )
            os.chdir(root)
            variants = versions.Fallout4Version.all()
            if family == "fallout4-identity":
                result = {
                    "variants": [
                        {
                            "isVr": v.is_vr(),
                            "exeName": v.exe_name(),
                            "steamAppId": v.steam_app_id(),
                        }
                        for v in variants
                    ]
                }
            elif family == "fallout4-paths":
                result = {
                    "variants": [
                        {
                            "token": v.as_str(),
                            "docsName": v.docs_folder_name(),
                            "standard": v.is_standard(),
                            "registryId": v.registry_id(),
                        }
                        for v in variants
                    ]
                }
            else:
                aliases = []
                for alias in request["aliases"]:
                    try:
                        aliases.append(
                            versions.Fallout4Version.from_str(alias).as_str()
                        )
                    except ValueError:
                        aliases.append(None)
                copies = [
                    versions.Fallout4Version.Original,
                    versions.Fallout4Version.NextGen,
                    versions.Fallout4Version.AnniversaryEdition,
                    versions.Fallout4Version.Vr,
                ]
                result = {
                    "variants": [
                        {
                            "version": v.version(),
                            "shortName": v.short_name(),
                            "xse": v.xse_acronym(),
                            "displayName": v.display_name(),
                            "repr": repr(v),
                            "text": str(v),
                            "equalCopy": v == copies[i],
                            "hashEqualCopy": hash(v) == hash(copies[i]),
                        }
                        for i, v in enumerate(variants)
                    ],
                    "aliases": aliases,
                }
            result["files"] = [
                {"path": p.name, "content": p.read_text(encoding="utf-8")}
                for p in sorted(root.iterdir())
            ]
            return result
        finally:
            # Restore cwd before temporary-directory disposal, including public call failures.
            os.chdir(previous)
