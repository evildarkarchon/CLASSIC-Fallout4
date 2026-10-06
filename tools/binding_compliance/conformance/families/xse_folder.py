"""Controlled public XSE folder resolution; platform discovery stays unclaimed."""

import hashlib
import json
from functools import partial

from ..coverage import CoveragePredicate, FamilyCoveragePolicy


def _matches(folder, observation):
    """Require the resolved path or absence and the actual preserved YAML inventory."""
    return (
        set(observation) == {"folder", "files"}
        and observation["folder"] == folder
        and isinstance(observation["files"], list)
        and bool(observation["files"])
        and all(
            isinstance(item, dict)
            and set(item) == {"path", "content"}
            and isinstance(item["path"], str)
            and isinstance(item["content"], str)
            for item in observation["files"]
        )
    )


#: Resolved-folder facts shared by both capabilities.
_FOLDER_FACTS = (
    ("explicit", "explicit-xse"),
    ("local-docs", "local-docs/F4SE"),
    ("configured-docs", "configured-docs/F4SE"),
    ("absent", None),
)

#: ``xse-folder.derive`` is XSE's own derivation from supplied Game Local facts
#: (the pack's domain owner, classic-xse-core). ``xse-folder.resolve`` is
#: scangame's composition that reads those facts from Local.yaml first; its
#: predicate IDs predate the split and stay stable.
XSE_FOLDER_COVERAGE_POLICY = FamilyCoveragePolicy(
    "xse-folder",
    tuple(
        CoveragePredicate(
            id=f"xse-folder.derive-{name}",
            capability_id="xse-folder.derive",
            action="xse-folder.derive",
            observation_family="values",
            rust_symbols=("resolve_xse_folder_from_game_local_facts",),
            runtime_operations=(None, "resolve_xse_folder_from_game_local_facts"),
            matches=partial(_matches, folder),
        )
        for name, folder in _FOLDER_FACTS
    )
    + tuple(
        CoveragePredicate(
            id=f"xse-folder.{name}",
            capability_id="xse-folder.resolve",
            action="xse-folder.resolve",
            observation_family="values",
            rust_symbols=("resolve_xse_folder_for_scan",),
            runtime_operations=(None, "resolve_xse_folder_for_scan"),
            matches=partial(_matches, folder),
        )
        for name, folder in _FOLDER_FACTS
    ),
)

#: The only Game Local facts a derivation fixture may supply. Relative,
#: already-trimmed strings (or absence) keep every case off host folders.
_CONTROLLED_FACTS = (
    {"docsFolderXse": "explicit-xse", "rootFolderDocs": "local-docs"},
    {"docsFolderXse": "", "rootFolderDocs": "local-docs"},
    {"docsFolderXse": None, "rootFolderDocs": None},
)


def validate_xse_folder_pack(document, root):
    """Reject inputs that could fall through to host game/documents discovery."""
    paths = []
    registry = None
    for case in document["scenarios"]:
        reference = case["input"].get("fixtureRef")
        if case["input"] != {"fixtureRef": reference} or case["fixtureRefs"] != [
            reference
        ]:
            raise ValueError("XSE folder requires one declared fixture")
        path = (
            root / document["fixtureRoot"] / document["fixtures"][reference]
        ).resolve()
        if not path.is_relative_to((root / document["fixtureRoot"]).resolve()):
            raise ValueError("XSE folder fixture escapes root")
        fixture = json.loads(path.read_text(encoding="utf-8"))
        # Composition cases seed Local.yaml; derivation cases hand XSE the
        # Game Local facts directly and must never carry a Local.yaml.
        source_key = (
            "gameLocalFacts" if case["action"] == "xse-folder.derive" else "localYaml"
        )
        if set(fixture) != {
            "registryYaml",
            "game",
            "selectedVersion",
            source_key,
            "configuredDocs",
        }:
            raise ValueError("unsupported XSE folder fixture")
        if registry is not None and fixture["registryYaml"] != registry:
            raise ValueError("XSE folder singleton requires identical registry bytes")
        registry = fixture["registryYaml"]
        # Freeze the injected OG/VR metadata: deleting either XSE record would
        # make a configured-docs request fall through to platform discovery.
        if (
            hashlib.sha256(registry.encode("utf-8")).hexdigest()
            != "16ac61af30e482084589c03c2aec12b4f8333cec22f2528a10189bad393e5299"
        ):
            raise ValueError("XSE folder requires the controlled registry metadata")
        # Known games always have a configured fallback. Unknown games return
        # before DocsPathFinder, including malformed/missing Local.yaml cases.
        if (
            fixture["game"],
            fixture["selectedVersion"],
            fixture["configuredDocs"],
        ) not in {
            ("Fallout4", "OG", "configured-docs"),
            ("Fallout4VR", "VR", "configured-docs"),
            ("Unknown", "auto", ""),
        }:
            raise ValueError("XSE folder input could consult host discovery")
        if source_key == "gameLocalFacts":
            if fixture["gameLocalFacts"] not in _CONTROLLED_FACTS:
                raise ValueError("XSE folder requires controlled Game Local facts")
        elif fixture["localYaml"] not in {
            None,
            "[invalid: yaml",
            'Game_Info:\n  Docs_Folder_XSE: " explicit-xse "\n  Root_Folder_Docs: local-docs\n',
            'Game_Info:\n  Docs_Folder_XSE: " "\n  Root_Folder_Docs: local-docs\n',
        }:
            raise ValueError("XSE folder requires controlled local paths")
        inventory = [{"path": "CLASSIC Main.yaml", "content": registry}]
        if fixture.get("localYaml") is not None:
            inventory.append(
                {
                    "path": f"CLASSIC {fixture['game']} Local.yaml",
                    "content": fixture["localYaml"],
                }
            )
        inventory.sort(key=lambda item: item["path"])
        if case["expected"].get("files") != inventory:
            raise ValueError("XSE folder inventory must preserve the fixture bytes")
        paths.append(path)
    return tuple(paths)
