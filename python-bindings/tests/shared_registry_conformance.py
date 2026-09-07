"""Public string and registry observations from input-only fixtures."""

from collections.abc import Mapping
from typing import Any


def observe_shared_registry(family: str, fixture: Mapping[str, Any]) -> dict[str, Any]:
    """Execute owned calls; registry cleanup also runs after a transport exception."""
    request = fixture["request"]
    if family == "string-operations":
        from classic_shared import StringProcessor

        processor = StringProcessor()
        values = request["values"]
        return {
            "interned": [processor.intern(value) for value in values],
            "normalized": [processor.normalize(value) for value in values],
            "batch": processor.process_batch(values, "normalize"),
        }
    if family != "registry-operations":
        raise ValueError("unsupported shared/registry family")
    import classic_registry as registry

    # The receipt runner is a dedicated process; clear global state at both ends
    # so later scenarios cannot inherit entries or leave state after failure.
    registry.clear_all()
    try:
        initially_present = registry.is_registered("conformance.stringValue")
        for name in ("stringValue", "boolValue", "intValue"):
            registry.register("conformance." + name, request[name])
        stored = {
            name: registry.get("conformance." + name)
            for name in ("stringValue", "boolValue", "intValue")
        }
        registry.register("conformance.stringValue", request["replacement"])
        replacement = registry.get("conformance.stringValue")
        registry.unregister("conformance.stringValue")
        after_remove = registry.is_registered("conformance.stringValue")
        registry.clear_all()
        after_clear = registry.is_registered(
            "conformance.boolValue"
        ) or registry.is_registered("conformance.intValue")
        return {
            "initiallyPresent": initially_present,
            "stored": stored,
            "replacement": replacement,
            "afterRemovePresent": after_remove,
            "afterClearPresent": after_clear,
        }
    finally:
        registry.clear_all()
