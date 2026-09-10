"""Executable DDS byte parsing and complete public header validation facts."""

from collections.abc import Mapping
from functools import partial
from typing import Any

from ..coverage import CoveragePredicate, FamilyCoveragePolicy


def _observed(parsed: bool, observation: Mapping[str, Any]) -> bool:
    """Require native header fields and every query result to agree with raw bytes."""
    if set(observation) != {"bytes", "header"}:
        return False
    raw = observation["bytes"]
    if not isinstance(raw, list) or not all(
        type(value) is int and 0 <= value <= 255 for value in raw
    ):
        return False
    header = observation["header"]
    if not parsed:
        return header is None and (len(raw) < 128 or raw[:4] != [68, 68, 83, 32])
    if len(raw) < 128 or raw[:4] != [68, 68, 83, 32] or not isinstance(header, Mapping):
        return False
    if set(header) != {
        "width",
        "height",
        "depth",
        "mipmaps",
        "format",
        "powerOfTwo",
        "validBcDimensions",
        "reasonableSize",
        "hasMipmaps",
        "bcCompressed",
    }:
        return False
    width, height, mipmaps = (
        int.from_bytes(bytes(raw[offset : offset + 4]), "little")
        for offset in (16, 12, 28)
    )
    if any(
        type(header[key]) is not int for key in ("width", "height", "depth", "mipmaps")
    ):
        return False
    return (
        header["width"] == width
        and header["height"] == height
        and header["depth"] == 1
        and header["mipmaps"] == max(1, mipmaps)
        and header["format"] == "BC3_UNorm_sRGB"
        and header["powerOfTwo"]
        is (
            width > 0
            and height > 0
            and width & (width - 1) == 0
            and height & (height - 1) == 0
        )
        and header["validBcDimensions"] is (width % 4 == 0 and height % 4 == 0)
        and header["reasonableSize"] is (0 < width <= 16384 and 0 < height <= 16384)
        and header["hasMipmaps"] is (mipmaps > 1)
        and header["bcCompressed"] is True
    )


def _file_observed(observation: Mapping[str, Any]) -> bool:
    """Require single/batch dimensions, preserved raw bytes and a typed missing-file failure."""
    if set(observation) != {"dimensions", "batch", "missingError", "bytes"}:
        return False
    dimensions = observation["dimensions"]
    return (
        (
            dimensions is None
            or isinstance(dimensions, list)
            and len(dimensions) == 2
            and all(type(value) is int and value >= 0 for value in dimensions)
        )
        and observation["batch"] == [["texture.dds", dimensions], ["missing.dds", None]]
        and observation["missingError"] == "io_error"
        and isinstance(observation["bytes"], list)
        and all(
            type(value) is int and 0 <= value <= 255 for value in observation["bytes"]
        )
    )


def _validation(observation: Mapping[str, Any]) -> bool:
    """Require actual issue strings and batch filtering to agree with single-file validation."""
    if set(observation) != {"issues", "batch", "dimensionIssues", "bytes"}:
        return False
    return (
        all(
            isinstance(observation[key], list)
            and all(
                isinstance(message, str) and message for message in observation[key]
            )
            for key in ("issues", "dimensionIssues")
        )
        and observation["batch"]
        == ([["texture.dds", observation["issues"]]] if observation["issues"] else [])
        + [["missing.dds", ["Unable to read DDS file"]]]
        and isinstance(observation["bytes"], list)
        and all(
            type(value) is int and 0 <= value <= 255 for value in observation["bytes"]
        )
    )


DDS_HEADER_COVERAGE_POLICY = FamilyCoveragePolicy(
    "dds-header",
    tuple(
        CoveragePredicate(
            id="parsed-header" if parsed else "rejected-header",
            capability_id="dds-header.parse",
            action="dds-header.parse",
            observation_family="header",
            rust_symbols=("DDSHeader",),
            matches=partial(_observed, parsed),
            runtime_operations=(
                None,
                "from_bytes",
                "has_power_of_2_dimensions",
                "has_valid_bc_dimensions",
                "is_reasonable_size",
                "has_mipmaps",
                "is_bc_compressed",
            )
            if parsed
            else ("from_bytes",),
        )
        for parsed in (True, False)
    )
    + (
        CoveragePredicate(
            "file-readers",
            "dds-header.files",
            "dds-header.files",
            "file-headers",
            ("FileIOCore",),
            _file_observed,
            runtime_operations=("read_dds_header", "read_dds_headers_batch"),
        ),
        CoveragePredicate(
            "dds-validation",
            "dds-header.validate",
            "dds-header.validate",
            "dds-issues",
            ("DDSAnalyzer",),
            _validation,
            runtime_operations=(None,),
        ),
    ),
)
