"""YAML file kind values remain Rust-owned across all binding surfaces."""

from pathlib import Path


def test_yaml_file_values_are_a_shared_executable_family() -> None:
    """Every exported reader participates; incomplete kind inventories fail."""
    from conformance.applicability import derive_applicability
    from conformance.coverage import load_source_parity_rows
    from conformance.packs import load_and_validate_pack

    root = Path(__file__).resolve().parents[3]
    path = root / "tests/conformance/packs/yaml_file_values/v1.json"
    assert path.is_file()
    from conformance.families.yaml_file_values import YAML_FILE_VALUES_COVERAGE_POLICY

    pack = load_and_validate_pack(root, path).document()
    assert {
               p.id
               for p in derive_applicability(pack, load_source_parity_rows(root)).participants
           } == {"rust", "cxx", "node", "python"}
    expected = pack["scenarios"][0]["expected"]
    predicate = YAML_FILE_VALUES_COVERAGE_POLICY.predicates[0]
    assert predicate.matches(expected)
    assert not predicate.matches({"kinds": expected["kinds"][:-1]})
    assert not predicate.covers_runtime_operation("future_yaml_operation")
