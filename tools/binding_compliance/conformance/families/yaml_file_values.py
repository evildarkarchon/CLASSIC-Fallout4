"""Executable names and descriptions for the six Rust-owned YAML file kinds."""

from collections.abc import Mapping
from typing import Any

from ..coverage import CoveragePredicate, FamilyCoveragePolicy


def _observed(value: Mapping[str, Any]) -> bool:
    """Require a complete unique inventory with both native string projections."""
    kinds = value.get("kinds")
    return (
        set(value) == {"kinds"}
        and isinstance(kinds, list)
        and len(kinds) == 6
        and all(
            isinstance(item, dict)
            and set(item) == {"token", "description"}
            and all(isinstance(text, str) and text for text in item.values())
            for item in kinds
        )
        and len({item["token"] for item in kinds}) == 6
    )


YAML_FILE_VALUES_COVERAGE_POLICY = FamilyCoveragePolicy(
    "yaml-file-values",
    (
        CoveragePredicate(
            id="yaml-file-values.observed",
            capability_id="yaml-file-values.observe",
            action="yaml-file-values.observe",
            observation_family="values",
            rust_symbols=("YamlSource", "as_str", "description"),
            matches=_observed,
            # The file identity is config's `YamlSource` (#246), which the
            # yaml-source-values family also covers. Python `YamlFile` methods
            # therefore surface under their full export path (their class name
            # differs from the Rust symbol); naming them, not bare `__eq__` or
            # `as_str`, keeps this family from crediting `classic_config.
            # YamlSource` methods it never executes. Node and CXX keep their
            # distinct export names.
            runtime_operations=(
                None,
                "YamlFile.as_str",
                "YamlFile.description",
                "YamlFile.__repr__",
                "YamlFile.__str__",
                "YamlFile.__eq__",
                "YamlFile.__hash__",
                "yaml_file_as_str",
                "yaml_file_description",
                "getAllYamlFiles",
                "getYamlFileDescription",
            ),
        ),
    ),
)
