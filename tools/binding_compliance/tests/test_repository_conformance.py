"""Repository conformance must account for all packs and source parity rows."""

from pathlib import Path

import pytest


def test_empty_receipts_report_missing_families_and_runtime_rows() -> None:
    """Source ownership can retain structural rows but never prove execution."""
    from conformance.repository import build_repository_report

    report = build_repository_report(Path(__file__).resolve().parents[3], ())
    assert report["result"] == "fail"
    assert report["repositoryComplete"] is False
    assert "xse-folder" in report["missingFamilies"]
    assert "crash-log-scan-run" in report["missingFamilies"]
    assert report["uncoveredRows"]
    assert report["retainedRows"]


def test_empty_repository_cannot_certify_itself(tmp_path: Path) -> None:
    """An absent pack catalog must not become vacuous full-profile success."""
    from conformance.command import ConformanceCommandError
    from conformance.repository import build_repository_report

    with pytest.raises(ConformanceCommandError):
        build_repository_report(tmp_path, ())


@pytest.mark.parametrize("failed_donor", [False, True])
def test_complete_family_list_cannot_hide_uncovered_runtime_rows(
    monkeypatch: pytest.MonkeyPatch, failed_donor: bool
) -> None:
    """Even all family responses cannot grant absent or failed row evidence."""
    from conformance import repository
    from conformance.coverage import load_source_parity_rows
    from conformance.packs import discover_pack_paths, load_and_validate_pack

    root = Path(__file__).resolve().parents[3]
    families = [
        load_and_validate_pack(root, path).document()["familyId"]
        for path in discover_pack_paths(root)
    ]
    runtime_ids = [
        row.obligation_id
        for row in load_source_parity_rows(root)
        if row.required_evidence_kind == "runtime"
    ]
    donor = families[0]

    def family_report(_root: Path, **kwargs: object) -> dict[str, object]:
        """Model the authenticated family validator's success/failure boundary."""
        family = kwargs["receipt_paths"][0].parent.name
        failed = failed_donor and family == donor
        return {
            "result": "fail" if failed else "pass",
            "enforcement": "blocking",
            "repositoryComplete": not failed,
            "coverage": {
                "rows": [{"obligationId": value} for value in runtime_ids]
                if failed
                else []
            },
        }

    monkeypatch.setattr(repository, "_run_plan_family", lambda path: path.parent.name)
    monkeypatch.setattr(
        repository, "build_conformance_report_from_receipts", family_report
    )
    report = repository.build_repository_report(
        root, [root / family / "receipt.json" for family in families]
    )
    assert report["missingFamilies"] == []
    assert report["uncoveredRows"] == sorted(runtime_ids)
    assert report["repositoryComplete"] is False
    assert report["result"] == "fail"
