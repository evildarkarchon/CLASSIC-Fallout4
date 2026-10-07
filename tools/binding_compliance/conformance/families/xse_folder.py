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

def _matches_log(log, error, observation):
    """Require the located log, its absence, or the typed operational failure."""
    return observation == {"log": log, "error": error}


#: XSE log facts (``xse-folder.log``): Fallout 4's and Fallout 4 VR's own logs
#: in the shared ``F4SE`` folder, the explicit folder winning precedence,
#: absence, and the typed operational failure.
_LOG_FACTS = (
    ("fallout4", "configured-docs/F4SE/f4se.log", None),
    ("vr", "configured-docs/F4SE/f4sevr.log", None),
    ("explicit", "explicit-xse/f4se.log", None),
    ("absent", None, None),
    ("uninspectable", None, "inspect"),
)

#: The YAML ``\0`` escape (backslash and zero, not a raw NUL byte) records an
#: XSE Folder no platform can inspect, which stands in for any operational
#: failure without touching host folders or permissions.
_UNINSPECTABLE_LOCAL_YAML = 'Game_Info:\n  Docs_Folder_XSE: "bad\\0xse"\n'

#: The only log files a log fixture may create under its owned root.
_CONTROLLED_LOG_FILES = frozenset(
    {
        "configured-docs/F4SE/f4se.log",
        "configured-docs/F4SE/f4sevr.log",
        "local-docs/F4SE/f4se.log",
        "explicit-xse/f4se.log",
    }
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
    )
    + tuple(
        CoveragePredicate(
            id=f"xse-folder.log-{name}",
            capability_id="xse-folder.log",
            action="xse-folder.log",
            observation_family="values",
            rust_symbols=("resolve_xse_log_for_scan",),
            runtime_operations=(
                None,
                "resolve_xse_log_for_scan",
                "resolveXseLogForScan",
            ),
            matches=partial(_matches_log, log, error),
        )
        for name, log, error in _LOG_FACTS
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
        # Log cases also name the empty log files to create under the owned root.
        is_log = case["action"] == "xse-folder.log"
        if set(fixture) != {
            "registryYaml",
            "game",
            "selectedVersion",
            source_key,
            "configuredDocs",
        } | ({"logFiles"} if is_log else set()):
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
        } | ({_UNINSPECTABLE_LOCAL_YAML} if is_log else set()):
            raise ValueError("XSE folder requires controlled local paths")
        if is_log:
            # Log cases observe only the located log or typed failure; the
            # runner creates the listed empty logs, so they must stay closed.
            log_files = fixture["logFiles"]
            if (
                not isinstance(log_files, list)
                or len(set(log_files)) != len(log_files)
                or not set(log_files) <= _CONTROLLED_LOG_FILES
            ):
                raise ValueError("XSE log requires controlled log files")
            if set(case["expected"]) != {"log", "error"}:
                raise ValueError("XSE log expectation must be a log or typed error")
            paths.append(path)
            continue
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
