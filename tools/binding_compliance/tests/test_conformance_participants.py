"""Behavior tests for the central semantic participant catalog (participants.json)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from conformance.applicability import (
    PolicyException,
    PolicyExceptionError,
    derive_applicability,
    derive_semantic_participants,
)
from conformance.packs import MaterializationError, _semantic_scenarios
from conformance.participants import (
    DEFAULT_PARTICIPANTS_PATH,
    ParticipantCatalogError,
    load_participants,
)

REPO_ROOT = Path(__file__).resolve().parents[3]


def _pack() -> dict[str, object]:
    """Return one minimal validated pack with two capabilities and three scenarios."""

    return {
        "familyId": "example-family",
        "domainOwner": {"rustCrate": "classic-example-core"},
        "capabilities": [
            {"id": "example.read", "rustSymbols": ["read"]},
            {"id": "example.write", "rustSymbols": ["write"]},
        ],
        "scenarios": [
            {"id": "read-one", "action": "example.read"},
            {"id": "write-one", "action": "example.write"},
            {"id": "read-two", "action": "example.read"},
        ],
        "consumerObligations": [],
    }


def _write(root: Path, document: object) -> Path:
    """Write one participants catalog beneath a temporary repository root."""

    path = root / DEFAULT_PARTICIPANTS_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(document), encoding="utf-8")
    return path


def _catalog(root: Path, families: list[dict[str, object]]):
    """Load a trusted catalog holding exactly ``families``."""

    _write(root, {"schemaVersion": 1, "families": families})
    return load_participants(root)


def test_unlisted_family_is_rust_only_with_every_scenario(tmp_path: Path) -> None:
    """Families are Rust-only by default; Rust owns every capability."""

    matrix = derive_applicability(_pack(), _catalog(tmp_path, []))

    assert [participant.document() for participant in matrix.participants] == [
        {
            "id": "rust",
            "role": "semantic-adapter",
            "executionInstanceIds": ["rust"],
            "capabilityIds": ["example.read", "example.write"],
            "scenarioIds": ["read-one", "write-one", "read-two"],
        }
    ]


def test_cxx_enrolment_selects_scenarios_by_action(tmp_path: Path) -> None:
    """CXX runs exactly the scenarios whose action is an enrolled capability."""

    catalog = _catalog(
        tmp_path,
        [{"familyId": "example-family", "cxx": {"capabilityIds": ["example.read"]}}],
    )

    matrix = derive_applicability(_pack(), catalog)

    cxx = next(item for item in matrix.participants if item.id == "cxx")
    assert cxx.document() == {
        "id": "cxx",
        "role": "semantic-adapter",
        "executionInstanceIds": ["windows-clang-cl", "windows-msvc"],
        "capabilityIds": ["example.read"],
        "scenarioIds": ["read-one", "read-two"],
    }


def test_scenario_with_an_unenrolled_extra_capability_still_follows_its_action(
    tmp_path: Path,
) -> None:
    """The action rule, not an all-capabilities rule, decides membership (T1 snapshot)."""

    pack = _pack()
    pack["scenarios"] = [
        {
            "id": "read-then-write",
            "action": "example.read",
            "capabilityIds": ["example.read", "example.write"],
        }
    ]
    catalog = _catalog(
        tmp_path,
        [{"familyId": "example-family", "cxx": {"capabilityIds": ["example.read"]}}],
    )

    matrix = derive_applicability(pack, catalog)

    cxx = next(item for item in matrix.participants if item.id == "cxx")
    assert cxx.scenario_ids == ("read-then-write",)


def test_enrolment_naming_an_unknown_capability_fails_closed(tmp_path: Path) -> None:
    """A catalog entry cannot silently enrol nothing because of a typo."""

    catalog = _catalog(
        tmp_path,
        [{"familyId": "example-family", "cxx": {"capabilityIds": ["example.delete"]}}],
    )

    with pytest.raises(ParticipantCatalogError, match="unknown capability"):
        derive_applicability(_pack(), catalog)


def test_enrolment_that_selects_no_scenario_fails_closed(tmp_path: Path) -> None:
    """An enrolled participant with an empty denominator is an authoring error."""

    pack = _pack()
    pack["capabilities"].append({"id": "example.idle", "rustSymbols": ["idle"]})
    catalog = _catalog(
        tmp_path,
        [{"familyId": "example-family", "cxx": {"capabilityIds": ["example.idle"]}}],
    )

    with pytest.raises(ParticipantCatalogError, match="selects no scenario"):
        derive_applicability(pack, catalog)


def test_consumer_obligations_fail_closed_without_a_source_registry(
    tmp_path: Path,
) -> None:
    """An undeclared consumer denominator cannot yield repository completeness."""

    pack = _pack()
    pack["consumerObligations"] = [{"id": "example-rendering"}]

    with pytest.raises(PolicyExceptionError, match="consumer obligation registry"):
        derive_applicability(pack, _catalog(tmp_path, []))


def test_applicability_rejects_dangling_or_duplicate_exception_scopes(
    tmp_path: Path,
) -> None:
    """Reviewed exceptions must bind one known participant/capability scope."""

    exception = PolicyException(
        id="example-exception",
        capability_id="example.read",
        participant_id="cxx",
        rationale="The public capability is intentionally absent.",
        policy_page="docs/api/binding-parity-policy.md",
    )
    duplicate_scope = PolicyException(
        id="same-scope-second-id",
        capability_id="example.read",
        participant_id="cxx",
        rationale="A duplicate review must not create ambiguous ownership.",
        policy_page="docs/api/binding-parity-policy.md",
    )
    dangling = PolicyException(
        id="dangling-capability",
        capability_id="example.missing",
        participant_id="cxx",
        rationale="This capability does not exist.",
        policy_page="docs/api/binding-parity-policy.md",
    )
    catalog = _catalog(tmp_path, [])

    with pytest.raises(PolicyExceptionError, match="duplicate policy exception scope"):
        derive_applicability(
            _pack(), catalog, policy_exceptions=(exception, duplicate_scope)
        )
    with pytest.raises(PolicyExceptionError, match="unknown capability"):
        derive_applicability(_pack(), catalog, policy_exceptions=(dangling,))


def test_semantic_participants_need_no_consumer_registry(tmp_path: Path) -> None:
    """Plan projection reads only participants.json, never consumer obligations."""

    pack = _pack()
    pack["consumerObligations"] = [{"id": "example-rendering"}]
    catalog = _catalog(
        tmp_path,
        [{"familyId": "example-family", "cxx": {"capabilityIds": ["example.write"]}}],
    )

    semantic = derive_semantic_participants(pack, catalog)

    assert [(item.id, item.scenario_ids) for item in semantic] == [
        ("cxx", ("write-one",)),
        ("rust", ("read-one", "write-one", "read-two")),
    ]


def test_plan_projection_follows_the_catalog_and_rederives_after_it_changes(
    tmp_path: Path,
) -> None:
    """Immutable plans omit unenrolled actions and track the current catalog."""

    pack = _pack()
    _catalog(tmp_path, [])
    with pytest.raises(MaterializationError, match="not applicable"):
        _semantic_scenarios(tmp_path, pack, "cxx")
    assert [case["id"] for case in _semantic_scenarios(tmp_path, pack, "rust")] == [
        "read-one",
        "write-one",
        "read-two",
    ]

    _catalog(
        tmp_path,
        [{"familyId": "example-family", "cxx": {"capabilityIds": ["example.read"]}}],
    )

    assert [case["id"] for case in _semantic_scenarios(tmp_path, pack, "cxx")] == [
        "read-one",
        "read-two",
    ]


def test_applicability_requires_the_central_catalog() -> None:
    """Packs never choose participants, so a caller-built value is rejected."""

    with pytest.raises(ParticipantCatalogError, match="repository participant catalog"):
        derive_applicability(_pack(), {"example-family": {"cxx": ["example.read"]}})


@pytest.mark.parametrize(
    ("document", "message"),
    [
        ({"schemaVersion": 1}, "only schemaVersion and families"),
        ({"schemaVersion": 2, "families": []}, "schemaVersion must be 1"),
        ({"schemaVersion": 1, "families": {}}, "families must be an array"),
        (
            {"schemaVersion": 1, "families": [{"familyId": "a"}]},
            "must enrol at least one participant",
        ),
        (
            {
                "schemaVersion": 1,
                "families": [{"familyId": "a", "rust": {"capabilityIds": ["a.x"]}}],
            },
            "unknown participant rust",
        ),
        (
            {
                "schemaVersion": 1,
                "families": [{"familyId": "a", "cxx": {"capabilityIds": []}}],
            },
            "capabilityIds must be non-empty",
        ),
        (
            {
                "schemaVersion": 1,
                "families": [
                    {"familyId": "a", "cxx": {"capabilityIds": ["a.y", "a.x"]}}
                ],
            },
            "sorted and unique",
        ),
        (
            {
                "schemaVersion": 1,
                "families": [
                    {"familyId": "b", "cxx": {"capabilityIds": ["b.x"]}},
                    {"familyId": "a", "cxx": {"capabilityIds": ["a.x"]}},
                ],
            },
            "sorted and unique",
        ),
        (
            {
                "schemaVersion": 1,
                "families": [{"familyId": "a", "cxx": {"capabilityIds": ["A.x"]}}],
            },
            "stable machine identifier",
        ),
        (
            {
                "schemaVersion": 1,
                "families": [
                    {"familyId": "a", "cxx": {"capabilityIds": ["a.x"], "why": "x"}}
                ],
            },
            "only capabilityIds",
        ),
    ],
)
def test_loader_rejects_malformed_catalogs(
    tmp_path: Path, document: object, message: str
) -> None:
    """The catalog is closed and canonical, so review diffs stay exact."""

    _write(tmp_path, document)

    with pytest.raises(ParticipantCatalogError, match=message):
        load_participants(tmp_path)


def test_loader_rejects_duplicate_keys(tmp_path: Path) -> None:
    """Strict JSON parsing keeps one reading of every enrolment."""

    path = tmp_path / DEFAULT_PARTICIPANTS_PATH
    path.parent.mkdir(parents=True)
    path.write_text(
        '{"schemaVersion": 1, "schemaVersion": 1, "families": []}', encoding="utf-8"
    )

    with pytest.raises(ParticipantCatalogError, match="cannot read"):
        load_participants(tmp_path)


def test_loader_rejects_a_catalog_outside_the_repository(tmp_path: Path) -> None:
    """Only the repository-owned catalog can define participation."""

    outside = tmp_path / "outside.json"
    outside.write_text('{"schemaVersion": 1, "families": []}', encoding="utf-8")
    root = tmp_path / "repo"
    root.mkdir()

    with pytest.raises(ParticipantCatalogError, match="repository-owned"):
        load_participants(root, outside)


def test_repository_catalog_enrols_only_tracked_cxx_families() -> None:
    """The tracked catalog loads and enrols CXX in its 48 remaining families.

    T1 snapshotted 56; #307 dropped the eight served only by the removed
    database, version_registry, game and perf bridge modules.
    """

    catalog = load_participants(REPO_ROOT)

    assert catalog.has_trusted_provenance
    assert len(catalog.family_ids) == 48
    assert all(
        set(catalog.enrolments(family_id)) == {"cxx"}
        for family_id in catalog.family_ids
    )
