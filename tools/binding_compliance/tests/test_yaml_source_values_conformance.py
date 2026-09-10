"""Generic YAML source observations must retain VR role and identity semantics."""

from pathlib import Path


def test_yaml_source_pack_preserves_vr_role_distinction() -> None:
    """Game databases share the flat role while game-local paths preserve VR identity."""
    from conformance.packs import load_and_validate_pack

    root = Path(__file__).resolve().parents[3]
    path = Path("tests/conformance/packs/yaml_source_values/v1.json")
    assert (root / path).is_file()
    document = load_and_validate_pack(root, path).document()
    sources = {
        row["id"]: row for row in document["scenarios"][0]["expected"]["sources"]
    }
    assert sources["GAME"]["path"] == "CLASSIC Data/databases/CLASSIC Fallout4.yaml"
    assert sources["GAME_LOCAL"]["path"] == "CLASSIC Data/CLASSIC Fallout4VR Local.yaml"
