"""Input-only path and message transports through the public Python bindings."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path, PurePosixPath
from tempfile import TemporaryDirectory
from typing import Any


def _owned(root: Path, path: str) -> Path:
    """Contain fixture paths before materializing any scenario-owned bytes."""
    if (
        not path
        or "\\" in path
        or ":" in path
        or any(part in {"", ".", ".."} for part in path.split("/"))
        or PurePosixPath(path).is_absolute()
    ):
        raise ValueError("fixture path must be a contained relative path")
    return root / path


def _portable(value: str, root: Path) -> str:
    """Remove only this scenario's absolute root and native path separators."""
    return (
        value.removeprefix("\\\\?\\")
        .replace(str(root) + "\\", "")
        .replace(str(root) + "/", "")
        .replace("\\", "/")
    )


def observe_path_message(family: str, fixture: Mapping[str, Any]) -> dict[str, Any]:
    """Return observed domain values, preserving misses and native error text."""
    request = fixture["request"]
    if family == "message-operations":
        import classic_message

        message = classic_message.Message.with_target(
            request["content"],
            getattr(classic_message.MessageType, request["type"]),
            getattr(classic_message.MessageTarget, request["target"]),
        )
        if request["details"] is not None:
            message = message.with_details(request["details"])
        return {
            "type": message.msg_type().name(),
            "target": repr(message.target()).removeprefix("MessageTarget."),
            "content": message.content(),
            "title": message.title(),
            "details": message.details(),
            "formatted": classic_message.format_log_message(
                message.content(), message.details()
            ),
        }
    with TemporaryDirectory(prefix="classic-path-conformance-") as directory:
        root = Path(directory)
        for relative in fixture["directories"]:
            _owned(root, relative).mkdir(parents=True, exist_ok=True)
        for relative, content in fixture["files"].items():
            path = _owned(root, relative)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8", newline="")
        if family == "path-operations":
            import classic_path

            path = _owned(root, request["path"])
            exists = classic_path.PathValidator.is_valid_path(str(path))
            error = None
            try:
                classic_path.PathValidator.validate_required_files(
                    str(path), request["requiredFiles"]
                )
            except FileNotFoundError as failure:
                # Only the public binding's declared domain exception is projected.
                error = _portable(str(failure), root)
            return {
                "path": request["path"],
                "exists": exists,
                "requiredFiles": {"accepted": error is None, "error": error},
            }
        if family == "path-normalization":
            import classic_shared

            handler = classic_shared.PathHandler()
            base = str(_owned(root, request["base"]))
            joined = handler.join_paths(base, request["components"])
            normalized = handler.normalize_path(joined)
            paths = [str(_owned(root, item)) for item in request["validatePaths"]]
            return {
                "joinedPath": _portable(joined, root),
                "normalizedPath": _portable(normalized, root),
                "validation": [
                    {"path": _portable(path, root), "exists": exists}
                    for path, exists, _ in handler.validate_paths_batch(paths)
                ],
            }
    raise ValueError("unsupported path/message family")
