"""File-generation facts require actual creation flags and unchanged existing bytes."""

from collections.abc import Mapping
from typing import Any

from ..coverage import CoveragePredicate, FamilyCoveragePolicy
from .file_operations import _files


def _observed(observation: Mapping[str, Any]) -> bool:
    """Require complete durable inventory and idempotent object/free-function calls."""
    if set(observation) != {
        "paths",
        "before",
        "generated",
        "existing",
        "standalone",
        "files",
    }:
        return False
    paths = observation["paths"]
    if (
        not isinstance(paths, list)
        or len(paths) != 2
        or paths[0] != "CLASSIC Ignore.yaml"
        or paths[1]
        not in {
            "CLASSIC Data/CLASSIC Fallout4 Local.yaml",
            "CLASSIC Data/CLASSIC Fallout4VR Local.yaml",
        }
    ):
        return False
    if not _files(observation["before"]) or not _files(observation["files"]):
        return False
    before = {item["path"]: item["content"] for item in observation["before"]}
    after = {item["path"]: item["content"] for item in observation["files"]}
    return (
        observation["generated"] == [path not in before for path in paths]
        and all(type(value) is bool for value in observation["generated"])
        and observation["existing"] == observation["standalone"] == [False, False]
        and set(after) == set(before) | set(paths)
        and all(after[path] == content for path, content in before.items())
    )


FILE_GENERATION_COVERAGE_POLICY = FamilyCoveragePolicy(
    "file-generation",
    (
        CoveragePredicate(
            "generated-and-preserved",
            "file-generation.generate",
            "file-generation.generate",
            "generated-files",
            (
                "FileGenerator",
                "FileGeneratorConfig",
                "generate_ignore_file",
                "generate_local_yaml",
            ),
            _observed,
            runtime_operations=(
                None,
                "__init__",
                "config",
                "generate_all_files_async",
                "generate_ignore_file_async",
                "generate_local_yaml_async",
                "ignore_file_path",
                "local_yaml_path",
                "generateIgnoreFile",
                "generateLocalYaml",
            ),
        ),
    ),
)
