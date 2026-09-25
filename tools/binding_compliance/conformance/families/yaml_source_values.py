"""Generic YAML source paths and display labels from real public adapters."""

from collections.abc import Mapping

from ..coverage import CoveragePredicate, FamilyCoveragePolicy


def matches_sources(observation: Mapping) -> bool:
    """Require a complete ordered source matrix and observed identity distinctions."""
    rows = observation.get("sources")
    return (
        set(observation) == {"sources", "equal", "different", "distinct"}
        and observation["equal"] is True
        and observation["different"] is True
        and observation["distinct"] == 5
        and isinstance(rows, list)
        and [row.get("id") for row in rows if isinstance(row, Mapping)]
        == ["MAIN", "IGNORE", "GAME", "GAME_LOCAL", "TEST"]
        and all(
            set(row) == {"id", "path", "name", "gameName"}
            and all(isinstance(value, str) and value for value in row.values())
            for row in rows
        )
        and rows[2]["path"] == "CLASSIC Data/databases/CLASSIC Fallout4.yaml"
        and rows[3]["path"] == "CLASSIC Data/CLASSIC Fallout4VR Local.yaml"
    )


YAML_SOURCE_VALUES_COVERAGE_POLICY = FamilyCoveragePolicy(
    "yaml-source-values",
    (
        CoveragePredicate(
            "yaml-source-values.matrix",
            "yaml-source-values.matrix",
            "yaml-source-values.matrix",
            "values",
            ("YamlSource",),
            matches_sources,
            runtime_operations=(
                None,
                "path",
                "display_name",
                "display_name_with_game",
                "__eq__",
                "__hash__",
                "__repr__",
                "__str__",
                "getYamlSourcePath",
                "getYamlSourceDisplayName",
                "getYamlSourceDisplayNameWithGame",
            ),
        ),
    ),
)
