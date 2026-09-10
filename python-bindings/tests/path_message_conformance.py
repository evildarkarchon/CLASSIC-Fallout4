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
    # Canonicalized values and temporary roots can use different Windows spellings.
    portable_root = str(root).replace("\\", "/").removeprefix("//?/")
    portable_value = value.replace("\\", "/").removeprefix("//?/")
    return portable_value.replace("//?/" + portable_root + "/", "").replace(
        portable_root + "/", ""
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
        mutable = classic_message.Message("initial", classic_message.MessageType.Info)
        mutable.set_content(request["content"])
        mutable.set_msg_type(getattr(classic_message.MessageType, request["type"]))
        mutable.set_target(getattr(classic_message.MessageTarget, request["target"]))
        mutable.set_details(request["details"])
        mutable.set_title("owned-title")
        if mutable.title() != "owned-title":
            raise ValueError("message title setter lost supplied value")
        mutable.set_title(None)
        if (
            mutable.content(),
            mutable.msg_type(),
            mutable.target(),
            mutable.details(),
            mutable.title(),
        ) != (
            message.content(),
            message.msg_type(),
            message.target(),
            message.details(),
            message.title(),
        ):
            raise ValueError("message setters disagree with constructor/builders")
        titled = message.with_title(request["content"])
        if (
            titled.title() != request["content"]
            or titled.content() != message.content()
        ):
            raise ValueError("title builder changed unrelated message content")
        # Python's builder returns the same mutable wrapper, so restore its
        # title before comparing the shared construction/formatting observation.
        message.set_title(None)
        type_names = (
            "Info",
            "Warning",
            "Error",
            "Success",
            "Progress",
            "Debug",
            "Critical",
        )
        if int(message.msg_type()) != type_names.index(request["type"]):
            raise ValueError("message severity discriminant changed")
        target = message.target()
        if (
            target.should_display_in_gui(),
            target.should_display_in_cli(),
            target.should_display(),
        ) != (
            request["target"] in {"All", "Gui"},
            request["target"] in {"All", "Console"},
            request["target"] != "LogOnly",
        ):
            raise ValueError("native routing decisions disagree with requested target")
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
        # Windows temp paths can use 8.3 aliases; match native normalization's spelling.
        root = Path(directory).resolve(strict=True)
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
            validation = handler.validate_paths_batch(paths)
            if list(handler.validate_paths_batch_fast(paths)) != validation:
                raise ValueError("fast path validation disagrees with native batch")
            for path in [normalized, *paths]:
                native_path = Path(path)
                if handler.get_filename(path) != (native_path.name or None):
                    raise ValueError("filename observation disagrees with path")
                if handler.get_extension(path) != (
                    native_path.suffix.removeprefix(".") or None
                ):
                    raise ValueError("extension observation disagrees with path")
                if Path(handler.get_parent(path)) != native_path.parent:
                    raise ValueError("parent observation disagrees with path")
                parts = list(native_path.parts)
                # Rust's Windows components separate the drive prefix and root;
                # pathlib combines them into its first anchor component.
                if native_path.drive and native_path.root:
                    parts = [native_path.drive, native_path.root, *parts[1:]]
                if (
                    list(handler.split_path(path)) != parts
                    or list(handler.split_path_fast(path)) != parts
                ):
                    raise ValueError("native component splitting disagrees with path")
                if (
                    not handler.is_absolute(path)
                    or Path(handler.to_absolute(path, base)) != native_path
                ):
                    raise ValueError("absolute path identity was not preserved")
                if Path(handler.common_prefix([path, path])) != native_path:
                    raise ValueError("common prefix lost identical path input")
            hits, misses, _ = handler.cache_metrics()
            if handler.normalize_path(joined) != normalized:
                raise ValueError("cached normalization changed the path")
            later_hits, later_misses, rate = handler.cache_metrics()
            if (
                later_hits != hits + 1
                or later_misses != misses
                or rate != later_hits / (later_hits + later_misses)
            ):
                raise ValueError("cache counters do not reflect repeated normalization")
            if not all(handler.cache_stats()):
                raise ValueError("exercised path and validation caches are empty")
            handler.clear_cache()
            if handler.cache_stats() != (0, 0):
                raise ValueError("explicit cache clear retained entries")
            # Zero TTL makes expiry deterministic without sleeps or host clocks.
            expired = classic_shared.PathHandler(0)
            expired.normalize_path(joined)
            expired.validate_paths_batch(paths)
            expired.cleanup_cache()
            if expired.cache_stats() != (0, 0):
                raise ValueError("expired cache cleanup retained entries")
            return {
                "joinedPath": _portable(joined, root),
                "normalizedPath": _portable(normalized, root),
                "validation": [
                    {"path": _portable(path, root), "exists": exists}
                    for path, exists, _ in validation
                ],
            }
    raise ValueError("unsupported path/message family")
