"""Runtime coverage for side-effect-free User Settings migration planning."""

from pathlib import Path

import classic_user_settings
import pytest


def user_settings_fixture_root() -> Path:
    """Return the repository-level User Settings compatibility corpus."""
    return (
        Path(__file__).parents[2]
        / "tests"
        / "fixtures"
        / "user_settings_compatibility"
    )


def test_flat_user_settings_migration_plan_is_reviewable_and_reversible(
    tmp_path: Path,
) -> None:
    """Expose every flat-shape transition and its exact in-memory inverse."""
    source = (user_settings_fixture_root() / "flat_classic_config.yaml").read_bytes()
    settings_path = tmp_path / "CLASSIC Settings.yaml"
    settings_path.write_bytes(source)
    snapshot = classic_user_settings.open_user_settings(str(tmp_path))

    outcome = snapshot.plan_migration()

    assert outcome.status == "planned"
    assert outcome.diagnostics == []
    assert isinstance(outcome.plan, classic_user_settings.UserSettingsMigrationPlan)
    plan = outcome.plan
    assert plan.required is True
    assert plan.base_revision == snapshot.revision
    assert plan.source.location == "canonical"
    assert plan.source.schema_version is None
    assert plan.target.location == "canonical"
    assert plan.target.schema_version.major == 1
    assert plan.target.schema_version.minor == 0
    assert plan.original_content == source
    assert b'schema_version: "1.0"' in plan.proposed_content
    assert len(plan.changes) == 18
    assert plan.changes[0].kind == "schema_version_transition"
    assert plan.changes[0].target_path == "/schema_version"
    assert plan.changes[1].source_path == "/fcx_mode"
    assert plan.changes[1].target_path == "/CLASSIC_Settings/FCX Mode"

    reversed_plan = plan.reverse_in_memory()
    assert reversed_plan.original_content == plan.proposed_content
    assert reversed_plan.proposed_content == source
    assert reversed_plan.source.location == plan.target.location
    assert reversed_plan.target.location == plan.source.location
    assert reversed_plan.reverse_in_memory().proposed_content == plan.proposed_content
    assert settings_path.read_bytes() == source


def test_current_and_unsupported_documents_return_structured_planning_outcomes(
    tmp_path: Path,
) -> None:
    """Distinguish a current no-op from an unsupported version gap without writes."""
    fixture_root = user_settings_fixture_root()
    current_root = tmp_path / "current"
    current_root.mkdir()
    current_path = current_root / "CLASSIC Settings.yaml"
    current_bytes = (fixture_root / "canonical_current_nested.yaml").read_bytes()
    current_path.write_bytes(current_bytes)

    current = classic_user_settings.open_user_settings(str(current_root)).plan_migration()

    assert current.status == "not_required"
    assert current.plan is None
    assert current.diagnostics == []
    assert current_path.read_bytes() == current_bytes

    older_root = tmp_path / "older"
    older_root.mkdir()
    older_path = older_root / "CLASSIC Settings.yaml"
    older_bytes = b'schema_version: "0.9"\nCLASSIC_Settings:\n  Update Check: true\n'
    older_path.write_bytes(older_bytes)

    unsupported = classic_user_settings.open_user_settings(
        str(older_root)
    ).plan_migration()

    assert unsupported.status == "unsupported"
    assert unsupported.plan is None
    assert len(unsupported.diagnostics) == 1
    assert isinstance(
        unsupported.diagnostics[0],
        classic_user_settings.UserSettingsMigrationDiagnostic,
    )
    assert unsupported.diagnostics[0].code == "unsupported_schema_version_gap"
    assert "0.9" in unsupported.diagnostics[0].message
    assert older_path.read_bytes() == older_bytes


def test_previous_location_plan_reports_location_and_version_transitions(
    tmp_path: Path,
) -> None:
    """Describe both legacy-location and unversioned transitions without relocating files."""
    source = (
        user_settings_fixture_root() / "previous_location_nested.yaml"
    ).read_bytes()
    legacy_path = tmp_path / "CLASSIC Data" / "CLASSIC Settings.yaml"
    legacy_path.parent.mkdir()
    legacy_path.write_bytes(source)

    outcome = classic_user_settings.open_user_settings(str(tmp_path)).plan_migration()

    assert outcome.status == "planned"
    assert outcome.plan.required is True
    assert outcome.plan.source.location == "legacy"
    assert outcome.plan.source.schema_version is None
    assert outcome.plan.target.location == "canonical"
    assert (
        outcome.plan.target.schema_version.major,
        outcome.plan.target.schema_version.minor,
    ) == (1, 0)
    assert [change.kind for change in outcome.plan.changes[:2]] == [
        "location_transition",
        "schema_version_transition",
    ]
    assert legacy_path.read_bytes() == source
    assert not (tmp_path / "CLASSIC Settings.yaml").exists()


def test_approved_migration_applies_and_restores_through_an_opaque_receipt(
    tmp_path: Path,
) -> None:
    """Publish an approved plan, report its verified backup, and restore it explicitly."""
    source = (user_settings_fixture_root() / "flat_classic_config.yaml").read_bytes()
    settings_path = tmp_path / "CLASSIC Settings.yaml"
    settings_path.write_bytes(source)
    snapshot = classic_user_settings.open_user_settings(str(tmp_path))
    plan = snapshot.plan_migration().plan

    outcome = plan.apply(str(tmp_path))

    assert outcome.status == "applied"
    assert outcome.expected_revision is None
    assert outcome.actual_revision is None
    assert isinstance(
        outcome.receipt,
        classic_user_settings.UserSettingsMigrationReceipt,
    )
    receipt = outcome.receipt
    assert Path(receipt.source_path) == settings_path
    assert Path(receipt.destination_path) == settings_path
    assert Path(receipt.backup_path).read_bytes() == source
    assert receipt.source.location == "canonical"
    assert receipt.source.schema_version is None
    assert receipt.target.location == "canonical"
    assert (
        receipt.target.schema_version.major,
        receipt.target.schema_version.minor,
    ) == (1, 0)
    assert receipt.backup_revision == snapshot.revision
    assert receipt.published_revision == classic_user_settings.open_user_settings(
        str(tmp_path)
    ).revision

    restored = receipt.restore(str(tmp_path))

    assert restored.status == "restored"
    assert restored.revision == receipt.backup_revision
    assert restored.expected_revision is None
    assert restored.actual_revision is None
    assert settings_path.read_bytes() == source
    assert Path(receipt.backup_path).read_bytes() == source


def test_migration_conflicts_are_data_and_operational_failures_raise(
    tmp_path: Path,
) -> None:
    """Preserve newer documents on apply/restore conflicts and type operational failures."""
    source = (user_settings_fixture_root() / "flat_classic_config.yaml").read_bytes()
    settings_path = tmp_path / "CLASSIC Settings.yaml"
    settings_path.write_bytes(source)
    snapshot = classic_user_settings.open_user_settings(str(tmp_path))
    stale_plan = snapshot.plan_migration().plan
    external_edit = source + b"\nExternalOwner:\n  generation: 2\n"
    settings_path.write_bytes(external_edit)

    apply_conflict = stale_plan.apply(str(tmp_path))

    assert apply_conflict.status == "conflict"
    assert apply_conflict.receipt is None
    assert apply_conflict.expected_revision == snapshot.revision
    assert apply_conflict.actual_revision not in (None, snapshot.revision)
    assert settings_path.read_bytes() == external_edit

    settings_path.write_bytes(source)
    plan = classic_user_settings.open_user_settings(str(tmp_path)).plan_migration().plan
    receipt = plan.apply(str(tmp_path)).receipt
    newer_migrated = settings_path.read_bytes() + b"\nExternalOwner:\n  generation: 3\n"
    settings_path.write_bytes(newer_migrated)

    restore_conflict = receipt.restore(str(tmp_path))

    assert restore_conflict.status == "conflict"
    assert restore_conflict.revision is None
    assert restore_conflict.expected_revision == receipt.published_revision
    assert restore_conflict.actual_revision not in (
        None,
        receipt.published_revision,
    )
    assert settings_path.read_bytes() == newer_migrated

    with pytest.raises(
        classic_user_settings.UserSettingsMigrationError,
        match="migration_restore_root_mismatch",
    ):
        receipt.restore(str(tmp_path / "different-root"))
