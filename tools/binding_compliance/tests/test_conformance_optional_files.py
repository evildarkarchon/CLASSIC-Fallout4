"""Exact scenario declarations bound optional empty coordination-file evidence."""

import copy
import re

import pytest
from conformance.compare import (
    NormalizationError,
    exact_differences,
    normalize_observations,
)
from conformance.packs import PackValidationError, load_and_validate_pack
from conformance.schema import ConformanceSchemaError, _validate_normalization_envelope
from test_conformance_packs import _valid_pack, _write_pack
from test_conformance_schema import _schema


def _normalization():
    """Declare one optional file at one exact durable tree checkpoint."""
    return {
        "rootRelativePaths": False,
        "excludedPaths": [],
        "unorderedPaths": [],
        "optionalEmptyFiles": [
            {
                "path": "$.tree",
                "relativePath": "settings.lock",
                "rationale": "Some public preflights stop before coordination.",
            }
        ],
    }


def _empty_file():
    """Return the sole removable regular-file representation."""
    return {"path": {"path": "settings.lock"}, "kind": "file", "bytesHex": ""}


@pytest.mark.parametrize(
    "expected_present,actual_present",
    [(False, False), (False, True), (True, False), (True, True)],
)
def test_optional_empty_file_presence_is_normalized(
    tmp_path, expected_present, actual_present
):
    """Optional presence compares equally without mutating either input observation."""
    expected = {"tree": [_empty_file()] if expected_present else []}
    actual = {"tree": [_empty_file()] if actual_present else []}
    saved = copy.deepcopy((expected, actual))
    pair = normalize_observations(
        expected, actual, _normalization(), fixture_root=tmp_path
    )
    assert not exact_differences(*pair)
    assert (expected, actual) == saved


@pytest.mark.parametrize(
    "tree",
    [
        None,
        {},
        [_empty_file(), _empty_file()],
        [{**_empty_file(), "bytesHex": "00"}],
        [{**_empty_file(), "kind": "directory"}],
        [{**_empty_file(), "extra": True}],
        [{"path": "settings.lock"}],
        [None],
        [{**_empty_file(), "path": {"path": "settings.lock", "extra": True}}],
    ],
)
def test_optional_empty_file_rejects_malformed_evidence_before_exclusion(
    tmp_path, tree
):
    """Exclusion cannot conceal malformed or duplicate optional-file evidence."""
    rules = _normalization()
    rules["excludedPaths"] = [
        {"path": "$.tree", "rationale": "Test transform ordering."}
    ]
    with pytest.raises(NormalizationError):
        normalize_observations(
            {"tree": []}, {"tree": tree}, rules, fixture_root=tmp_path
        )


def test_optional_file_requires_declared_tree_and_preserves_other_files(tmp_path):
    """Missing checkpoints fail, while nonselected files remain exact evidence."""
    with pytest.raises(NormalizationError):
        normalize_observations(
            {"tree": []}, {}, _normalization(), fixture_root=tmp_path
        )
    other = {**_empty_file(), "path": {"path": "other.lock"}}
    pair = normalize_observations(
        {"tree": []}, {"tree": [other]}, _normalization(), fixture_root=tmp_path
    )
    assert exact_differences(*pair)


@pytest.mark.parametrize(
    "field,value",
    [
        ("path", "$"),
        ("path", "$.tree[*]"),
        ("relativePath", "../settings.lock"),
        ("relativePath", "./settings.lock"),
        ("relativePath", "/settings.lock"),
        ("relativePath", "a//b"),
        ("relativePath", "C:settings.lock"),
        ("relativePath", "a\\b"),
        ("rationale", " "),
        ("extra", True),
    ],
)
def test_optional_file_schema_rejects_broad_or_unexplained_declarations(
    tmp_path, field, value
):
    """Both shared envelopes and loaded packs enforce exact, explained declarations."""
    rules = _normalization()
    rules["optionalEmptyFiles"][0][field] = value
    with pytest.raises(ConformanceSchemaError):
        _validate_normalization_envelope(rules, "normalization")
    pack = _valid_pack()
    pack["scenarios"][0]["normalization"] = rules
    path = _write_pack(tmp_path, pack)
    with pytest.raises(PackValidationError):
        load_and_validate_pack(tmp_path, path)


def test_optional_file_declarations_are_unique_and_schema_owned():
    """Packs and run plans share an optional closed declaration without allowing duplicate selectors."""
    rules = _normalization()
    _validate_normalization_envelope(rules, "normalization")
    rules["optionalEmptyFiles"].append(
        {**rules["optionalEmptyFiles"][0], "rationale": "Duplicate selector."}
    )
    with pytest.raises(ConformanceSchemaError):
        _validate_normalization_envelope(rules, "normalization")
    for name in ("scenario-pack-v1.schema.json", "run-plan-v1.schema.json"):
        normalization = _schema(name)["$defs"]["normalization"]
        declaration = normalization["properties"]["optionalEmptyFiles"]["items"]
        assert declaration["additionalProperties"] is False
        assert set(declaration["required"]) == {"path", "relativePath", "rationale"}
        assert "optionalEmptyFiles" not in normalization["required"]
        pattern = declaration["properties"]["relativePath"]["pattern"]
        assert re.fullmatch(pattern, "CLASSIC Settings.yaml.commit.lock")
        for invalid in ("../file", "./file", "/file", "a//b", "C:file", "a\\b"):
            assert re.fullmatch(pattern, invalid) is None


def test_optional_file_declarations_are_accepted_by_pack_validation(tmp_path):
    """An exact scenario declaration survives the pack loader unchanged."""
    pack = _valid_pack()
    pack["scenarios"][0]["normalization"] = _normalization()
    path = _write_pack(tmp_path, pack)
    loaded = load_and_validate_pack(tmp_path, path)
    assert loaded.document()["scenarios"][0]["normalization"] == _normalization()
