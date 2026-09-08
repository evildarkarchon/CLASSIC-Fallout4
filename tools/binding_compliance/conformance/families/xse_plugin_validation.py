"""Address Library validation from public metadata, checker results and owned bytes."""

from collections.abc import Mapping

from ..coverage import CoveragePredicate, FamilyCoveragePolicy


def matches_plugins(value: Mapping) -> bool:
    """Require a successful native result and exact unchanged plugin inventory."""
    info = value.get("info")
    return (
        set(value) == {"info", "result", "message", "beforeFiles", "files"}
        and isinstance(info, Mapping)
        and set(info) == {"version", "filename", "description", "url"}
        and info["version"] in {"Original", "NextGen", "Vr"}
        and all(isinstance(item, str) and item for item in info.values())
        and value["result"] == "CorrectVersion"
        and value["message"]
        == "✔️ You have the correct version of the Address Library file!\n-----\n"
        and value["beforeFiles"]
        == value["files"]
        == {info["filename"]: "fixture bytes\n", "sentinel.txt": "keep\n"}
    )


XSE_PLUGIN_VALIDATION_COVERAGE_POLICY = FamilyCoveragePolicy(
    "xse-plugin-validation",
    (
        CoveragePredicate(
            "xse-plugin-validation.check",
            "xse-plugin-validation.check",
            "xse-plugin-validation.check",
            "values",
            ("XseChecker", "AddressLibInfo"),
            matches_plugins,
            runtime_operations=(
                None,
                "__init__",
                "check",
                "validate",
                "checkXsePlugins",
                "check_xse_plugins",
                "getAddressLibInfo",
                "vr",
                "original",
                "next_gen",
            ),
        ),
    ),
)
