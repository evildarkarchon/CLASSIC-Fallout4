"""Public config aliases retain their actual core owner and executable duty."""

from conformance.families.database_operations import DATABASE_OPERATIONS_COVERAGE_POLICY
from conformance.families.settings_load import settings_yaml_coverage_policy


def test_node_cache_aliases_have_executed_predicates():
    """Aliases are credited only by the adapter that reads their native values."""
    for operation in (
        "DEFAULT_CACHE_CLEANUP_INTERVAL",
        "DEFAULT_CACHE_CLEANUP_THRESHOLD",
        "DEFAULT_QUERY_CACHE_CAPACITY",
    ):
        assert any(
            p.covers_runtime_operation(operation)
            for p in DATABASE_OPERATIONS_COVERAGE_POLICY.predicates
        )
    for operation in ("yamlClearCache", "yamlGetCacheStats", "clearYamlCache"):
        assert any(
            p.covers_runtime_operation(operation)
            for p in settings_yaml_coverage_policy().predicates
        )
