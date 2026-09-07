"""XSE metadata/detection facts with no discovery or typed-error overclaim."""

from functools import partial

from ..coverage import CoveragePredicate, FamilyCoveragePolicy

_EXPECTED = {
    "missing": {
        "typeName": "F4SE",
        "loaderName": "f4se_loader.exe",
        "dllPrefix": "f4se_",
        "installed": False,
        "version": None,
        "info": {"typeName": "F4SE", "installed": False, "version": None},
        "files": [],
    },
    "loader-only": {
        "typeName": "F4SE",
        "loaderName": "f4se_loader.exe",
        "dllPrefix": "f4se_",
        "installed": True,
        "version": None,
        "info": {"typeName": "F4SE", "installed": True, "version": None},
        "files": [{"path": "f4se_loader.exe", "hex": ""}],
    },
    "detected": {
        "typeName": "F4SE",
        "loaderName": "f4se_loader.exe",
        "dllPrefix": "f4se_",
        "installed": True,
        "version": "1.10.163",
        "info": {"typeName": "F4SE", "installed": True, "version": "1.10.163"},
        "files": [
            {"path": "f4se_1_10_163.dll", "hex": ""},
            {"path": "f4se_loader.exe", "hex": ""},
        ],
    },
}


def _matches(kind, observation):
    """Require exact metadata, absence/version values and unchanged fixture inventory."""
    return (
        observation == _EXPECTED[kind]
        and type(observation.get("installed")) is bool
        and type(observation.get("info", {}).get("installed")) is bool
    )


XSE_OPERATIONS_COVERAGE_POLICY = FamilyCoveragePolicy(
    "xse-operations",
    tuple(
        CoveragePredicate(
            id=f"xse-operations.{kind}",
            capability_id="xse-operations.inspect",
            action="xse-operations.inspect",
            observation_family="values",
            rust_symbols=(
                "XseType",
                "loader_name",
                "dll_prefix",
                "detect_xse_version",
                "is_xse_installed",
                "get_xse_info",
            ),
            matches=partial(_matches, kind),
            runtime_operations=(
                None,
                "parse_xse_type",
                "parseXseType",
                "f4se",
                "as_str",
                "loader_name",
                "dll_prefix",
                "detect_xse_version",
                "is_xse_installed",
                "get_xse_info",
                "xseLoaderName",
                "xseDllPrefix",
                "xseTypeName",
                "detectXseVersion",
                "isXseInstalled",
                "getXseInfo",
                "xse_get_loader_name",
                "xse_get_dll_prefix",
                "xse_get_info",
                "detect_xse_version_string",
                "is_xse_installed_check",
            ),
        )
        for kind in _EXPECTED
    ),
)


def validate_xse_operations_pack(document, root):
    """Restrict seeded filenames to the known hermetic F4SE fixture vocabulary."""
    import json

    paths = []
    for case in document["scenarios"]:
        reference = case["input"].get("fixtureRef")
        if (
            case["action"] != "xse-operations.inspect"
            or case["input"] != {"fixtureRef": reference}
            or case["fixtureRefs"] != [reference]
        ):
            raise ValueError("XSE scenario requires its sole file fixture")
        path = (
            root / document["fixtureRoot"] / document["fixtures"][reference]
        ).resolve()
        if not path.is_relative_to((root / document["fixtureRoot"]).resolve()):
            raise ValueError("XSE fixture escapes root")
        fixture = json.loads(path.read_text(encoding="utf-8"))
        if not any(_matches(kind, case["expected"]) for kind in _EXPECTED):
            raise ValueError(
                "XSE expectation requires exact metadata and byte inventory"
            )
        if (
            set(fixture) != {"files"}
            or not isinstance(fixture["files"], list)
            or any(
                name not in ("f4se_loader.exe", "f4se_1_10_163.dll")
                for name in fixture["files"]
            )
            or len(set(fixture["files"])) != len(fixture["files"])
        ):
            raise ValueError("XSE fixture contains unsupported filenames")
        paths.append(path)
    return tuple(paths)
