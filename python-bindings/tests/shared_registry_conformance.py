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
        observation = {
            "interned": [processor.intern(value) for value in values],
            "normalized": [processor.normalize(value) for value in values],
            "batch": processor.process_batch(values, "normalize"),
        }
        if list(processor.intern_batch(values)) != observation["interned"]:
            raise ValueError("batch interning disagrees with scalar observations")
        if (
                list(processor.process_batch_fast(values, "normalize"))
                != observation["batch"]
        ):
            raise ValueError("fast processing disagrees with native batch observation")
        for value in ["", *values]:
            lines = value.splitlines()
            if (
                    list(processor.split_lines(value)) != lines
                    or list(processor.split_lines_fast(value)) != lines
            ):
                raise ValueError("native line splitting disagrees with fixture text")
            if processor.common_prefix([value, value]) != value:
                raise ValueError("common prefix does not preserve identical inputs")
        if processor.join_lines(values, "|") != "|".join(values):
            raise ValueError("native joining does not preserve ordered input")
        if processor.pool_stats() != len(set(values)):
            raise ValueError("intern pool does not deduplicate input")
        # The public clear method is deliberately a no-op for append-only
        # ThreadedRodeo storage; exercise and verify that documented contract.
        processor.clear_pool()
        if processor.pool_stats() != len(set(values)):
            raise ValueError("append-only pool changed after clear request")
        return observation
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
        registry.register(registry.Keys.GAME_VERSION, request["gameVersion"])
        game_version = registry.get(registry.Keys.GAME_VERSION)
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
            "gameVersion": game_version,
        }
    finally:
        registry.clear_all()
