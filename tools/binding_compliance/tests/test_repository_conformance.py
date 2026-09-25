"""Repository conformance must account for all packs and source parity rows."""

import shutil
from pathlib import Path

import pytest


def test_downloaded_receipts_preserve_separate_immutable_plan_pairs(
        tmp_path: Path,
) -> None:
    """Artifact-name directories must not overwrite different participant runs."""
    from conformance.repository import discover_repository_receipts

    expected = []
    for artifact in ("rust-family-conformance", "node-family-conformance"):
        directory = tmp_path / "downloads" / artifact / "invocation"
        directory.mkdir(parents=True)
        (directory / "run_plan.json").write_text("{}", encoding="utf-8")
        receipt = directory / "receipt.json"
        receipt.write_text("{}", encoding="utf-8")
        expected.append(receipt)
    (tmp_path / "downloads" / "binding_compliance_report.json").write_text("{}")
    assert discover_repository_receipts(tmp_path, Path("downloads")) == tuple(
        sorted(expected)
    )


@pytest.mark.parametrize("damage", ("empty", "no-plan", "outside"))
def test_downloaded_receipt_discovery_fails_closed(tmp_path: Path, damage: str) -> None:
    """Empty, incomplete, or out-of-repository artifacts cannot become inputs."""
    from conformance.command import ConformanceCommandError
    from conformance.repository import discover_repository_receipts

    directory = tmp_path / "downloads"
    directory.mkdir()
    if damage == "no-plan":
        (directory / "receipt.json").write_text("{}", encoding="utf-8")
    if damage == "outside":
        directory = tmp_path.parent
    with pytest.raises(ConformanceCommandError):
        discover_repository_receipts(tmp_path, directory)


@pytest.mark.parametrize("changed_source", (False, True))
def test_downloaded_plan_remains_immutable_and_bound_to_source(
        tmp_path: Path, changed_source: bool
) -> None:
    """Artifact relocation preserves authenticatable plans but cannot hide source changes."""
    from conformance.packs import MaterializationError, load_prepared_run
    from conformance.receipts import validate_prepared_run
    from conformance.repository import discover_repository_receipts
    from receipt_test_support import prepare_receipt_case

    pack_path = Path("tests/conformance/packs/file_fingerprint/v1.json")
    pack, run, _ = prepare_receipt_case(
        Path(__file__).resolve().parents[3],
        tmp_path,
        pack_path,
        "node",
        runner_id="artifact-relocation-test",
    )
    original = run.run_plan_path.read_bytes()
    download = tmp_path / "downloaded" / "node-file-fingerprint-conformance"
    shutil.copytree(run.artifact_dir, download)
    (receipt,) = discover_repository_receipts(tmp_path, Path("downloaded"))
    if changed_source:
        with (tmp_path / pack_path).open("a", encoding="utf-8") as source:
            source.write("\n")
        with pytest.raises(MaterializationError, match="source identity"):
            load_prepared_run(
                pack, receipt.parent / "run_plan.json", receipt_path=receipt
            )
    else:
        moved = load_prepared_run(
            pack, receipt.parent / "run_plan.json", receipt_path=receipt
        )
        assert not validate_prepared_run(pack, moved).failures
    assert (receipt.parent / "run_plan.json").read_bytes() == original


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
