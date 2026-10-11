"""File fingerprint evidence is derived from complete public results."""

from pathlib import Path

from conformance.packs import load_and_validate_pack


ROOT = Path(__file__).resolve().parents[3]


def test_fingerprints_use_independent_standard_sha256_vectors() -> None:
    """A known SHA-256 vector and a missing-file result remain explicit."""
    pack = load_and_validate_pack(
        ROOT, Path("tests/conformance/packs/file_fingerprint/v1.json")
    ).document()
    cases = {case["id"]: case["expected"] for case in pack["scenarios"]}
    assert cases["ascii"]["hash"] == (
        "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
    )
    assert cases["missing"]["hash"] is None
    assert cases["missing"]["error"] == "not_found"

