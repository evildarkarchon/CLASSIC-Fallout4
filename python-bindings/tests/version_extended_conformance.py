"""Execute remaining public version operations against disposable input files."""

import tempfile
from pathlib import Path


def observe_version_extended(fixture):
    """Normalize public version tuples and documented PE failure loss only."""
    import classic_version as version

    request = fixture["request"]
    operation = request["operation"]

    def normalized(value):
        """Represent an optional public tuple as a common version string."""
        return None if value is None else ".".join(map(str, value))

    if operation == "extract":
        return {
            "filename": normalized(
                version.extract_version_from_filename(request["filename"])
            ),
            "log": normalized(version.extract_version_from_log(request["content"])),
            "all": [
                normalized(v) for v in version.extract_all_versions(request["content"])
            ],
        }
    if operation.startswith("known-"):
        native = version.parse_version(request["version"])
        return {
            operation: version.is_known_f4se_version(native)
            if operation == "known-f4se"
            else version.is_known_fallout4_version(native)
        }
    from aux_operations_conformance import _owned

    with tempfile.TemporaryDirectory(
        prefix="classic-version-conformance-"
    ) as directory:
        root = Path(directory)
        for path, content in fixture["files"].items():
            target = _owned(root, path)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(bytes.fromhex(content))
        target = _owned(root, request["path"])
        if operation == "pe-path":
            return {"validPath": version.is_valid_pe_path(str(target))}
        try:
            return {"peVersion": normalized(version.extract_pe_version(str(target)))}
        except (OSError, ValueError) as error:
            # CXX intentionally exposes an empty string for documented PE failures.
            if not str(error).startswith(
                (
                    "Invalid executable path:",
                    "Not a valid PE file:",
                    "No version information found in PE file:",
                    "Failed to read PE file",
                )
            ):
                raise
            return {"peVersion": ""}
