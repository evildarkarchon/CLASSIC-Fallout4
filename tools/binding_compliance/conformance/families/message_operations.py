"""Message-domain observations without timestamps, global logging or adapter oracles."""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from ..coverage import CoveragePredicate, FamilyCoveragePolicy

TYPES = {"Info", "Warning", "Error", "Success", "Progress", "Debug", "Critical"}
TARGETS = {"All", "Gui", "Console", "LogOnly"}


def _observed(value: Mapping[str, Any]) -> bool:
    """Retain complete stable message fields and exact formatter output."""
    return (
        set(value) == {"type", "target", "content", "title", "details", "formatted"}
        and isinstance(value["type"], str)
        and value["type"] in TYPES
        and isinstance(value["target"], str)
        and value["target"] in TARGETS
        and isinstance(value["content"], str)
        and value["title"] is None
        and (value["details"] is None or isinstance(value["details"], str))
        and isinstance(value["formatted"], str)
    )


def _details_observed(value: Mapping[str, Any]) -> bool:
    """A builder call receives credit only when a details value was exercised."""
    return _observed(value) and value["details"] is not None


def validate_message_operations_pack(
    document: Mapping[str, Any], root: Path
) -> tuple[Path, ...]:
    """Validate input shape and independent oracle shape without synthesizing values."""
    fixture_root = (root / document["fixtureRoot"]).resolve()
    paths = []
    for scenario in document["scenarios"]:
        reference = scenario["input"].get("fixtureRef")
        if (
            scenario["action"] != "message-operations.format"
            or scenario["input"] != {"fixtureRef": reference}
            or scenario["fixtureRefs"] != [reference]
        ):
            raise ValueError("message scenario must declare its sole input fixture")
        path = (fixture_root / document["fixtures"][reference]).resolve()
        if not path.is_relative_to(fixture_root):
            raise ValueError("message fixture escapes fixture root")
        fixture = json.loads(path.read_text(encoding="utf-8"))
        if set(fixture) != {"request"}:
            raise ValueError("message fixture has unexpected fields")
        request = fixture["request"]
        if (
            set(request) != {"type", "target", "content", "details"}
            or request["type"] not in TYPES
            or request["target"] not in TARGETS
            or not isinstance(request["content"], str)
            or not (request["details"] is None or isinstance(request["details"], str))
            or not _observed(scenario["expected"])
        ):
            raise ValueError("message request or expected observation is malformed")
        paths.append(path)
    return tuple(paths)


def message_operations_coverage_policy() -> FamilyCoveragePolicy:
    """Attribute creation/access/formatting only to public operations actually invoked."""
    return FamilyCoveragePolicy(
        "message-operations",
        (
            CoveragePredicate(
                id="message-created",
                capability_id="message-operations.format",
                action="message-operations.format",
                observation_family="message",
                rust_symbols=("Message", "create_message"),
                matches=_observed,
                runtime_operations=(
                    None,
                    "__init__",
                    "set_content",
                    "set_title",
                    "set_target",
                    "set_msg_type",
                    "set_details",
                    "with_title",
                    "with_target",
                    "create_message",
                    "createMessage",
                    "content",
                    "msg_type",
                    "target",
                    "title",
                    "details",
                ),
            ),
            CoveragePredicate(
                id="message-routing",
                capability_id="message-operations.format",
                action="message-operations.format",
                observation_family="message",
                rust_symbols=("MessageType", "MessageTarget"),
                matches=_observed,
                runtime_operations=(
                    None,
                    "name",
                    "__int__",
                    "should_display",
                    "should_display_in_cli",
                    "should_display_in_gui",
                ),
            ),
            CoveragePredicate(
                id="message-details",
                capability_id="message-operations.format",
                action="message-operations.format",
                observation_family="message",
                rust_symbols=("Message",),
                matches=_details_observed,
                runtime_operations=("with_details",),
            ),
            CoveragePredicate(
                id="message-formatted",
                capability_id="message-operations.format",
                action="message-operations.format",
                observation_family="message",
                rust_symbols=("format_log_message", "format_message"),
                matches=_observed,
                runtime_operations=(
                    None,
                    "format_log_message",
                    "format_message",
                    "formatMessage",
                ),
            ),
        ),
    )
