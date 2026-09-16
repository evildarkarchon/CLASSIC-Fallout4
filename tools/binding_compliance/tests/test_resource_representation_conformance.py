"""Resource value facts cover only representations checked by the real adapter."""

from conformance.command import FAMILY_COVERAGE_POLICIES


def test_resource_facts_include_executed_representation_methods() -> None:
    """Each newly observed Python representation/equality method must have a predicate."""
    policy = FAMILY_COVERAGE_POLICIES["resource-operations"]
    for owner, operations in (
            ("ResourceType", ("__eq__", "__repr__", "__str__")),
            ("ResourceInfo", ("__repr__", "__str__")),
    ):
        for operation in operations:
            assert any(
                owner in predicate.rust_symbols
                and predicate.covers_runtime_operation(operation)
                for predicate in policy.predicates
            )
