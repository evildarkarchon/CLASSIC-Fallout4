"""Observe public setting validation and cache retrieval without live settings."""

import math
from decimal import Decimal
from pathlib import Path
from tempfile import TemporaryDirectory


def _float_text(value: float) -> str:
    """Preserve shortest round-trip digits using Rust's scientific exponent spelling."""
    if math.isnan(value):
        return "NaN"
    if math.isinf(value):
        return "-inf" if value < 0 else "inf"
    # repr supplies the shortest round-trip digits; Decimal only moves the decimal point.
    sign, raw_digits, exponent = Decimal(repr(value)).as_tuple()
    digits = list(raw_digits)
    while len(digits) > 1 and digits[-1] == 0:
        digits.pop()
        exponent += 1
    if digits == [0]:
        exponent = 0
    mantissa = str(digits[0]) + (
        "." + "".join(map(str, digits[1:])) if len(digits) > 1 else ""
    )
    return ("-" if sign else "") + mantissa + "e" + str(exponent + len(digits) - 1)


def observe_settings_extended(family, fixture):
    """Preserve native coercion errors and cached documents across on-disk mutation."""
    import classic_settings as settings

    if family == "settings-validation":
        results = []
        for item in fixture["cases"]:
            valid = settings.validate_setting_value(item["value"], item["type"])
            try:
                value = settings.coerce_setting_value(item["value"], item["type"])
                if type(value) is float:
                    value = {"float": _float_text(value)}
                error = None
            except ValueError as failure:
                value = None
                error = str(failure)
            results.append({"valid": valid, "value": value, "error": error})
        return {"results": results}
    with TemporaryDirectory(prefix="classic-cached-docs-") as directory:
        path = Path(directory) / "input.yaml"
        key = "conformance.cached-docs"
        settings.clear_cache()
        try:
            before = settings.get_cached(key)
            path.write_text(fixture["content"], encoding="utf-8", newline="")
            settings.load_settings_sync(key, str(path))
            cached = settings.get_cached(key)
            path.write_text(fixture["replacement"], encoding="utf-8", newline="")
            after = settings.get_cached(key)
            settings.invalidate(key)
            after_invalidate = settings.get_cached(key)
            # Inventory after the last public read to expose forbidden stale writeback.
            files = {
                item.relative_to(directory).as_posix(): item.read_bytes().decode(
                    "utf-8"
                )
                for item in Path(directory).rglob("*")
                if item.is_file()
            }
            return {
                "before": before,
                "cached": cached,
                "afterFileChange": after,
                "afterInvalidate": after_invalidate,
                "files": files,
            }
        finally:
            settings.clear_cache()
