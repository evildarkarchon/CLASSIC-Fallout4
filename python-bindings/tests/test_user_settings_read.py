"""Runtime coverage for the typed, read-only User Settings Python adapter."""

from pathlib import Path

import classic_user_settings


def test_user_settings_read_only_open(tmp_path: Path) -> None:
    """Expose safe typed preferences and retain unknown source content without writing."""
    fixture_root = (
        Path(__file__).parents[2]
        / "tests"
        / "fixtures"
        / "user_settings_compatibility"
    )
    content = (fixture_root / "invalid_known_values.yaml").read_bytes()
    settings_path = tmp_path / "CLASSIC Settings.yaml"
    settings_path.write_bytes(content)

    snapshot = classic_user_settings.open_user_settings(str(tmp_path))

    assert snapshot.update_preferences.update_check is False
    assert snapshot.update_preferences.origin == "degraded_fallback"
    assert snapshot.source_location == "canonical"
    assert snapshot.source_path == str(settings_path)
    assert snapshot.classification == "current"
    assert snapshot.schema_major == 1
    assert snapshot.schema_minor == 0
    assert snapshot.commit_eligibility == "eligible"
    assert [diagnostic.code for diagnostic in snapshot.diagnostics] == [
        "invalid_type_update_check"
    ]
    assert snapshot.diagnostics[0].message
    assert snapshot.revision.startswith("sha256:")
    assert snapshot.original_content == content
    assert settings_path.read_bytes() == content

    variants = [
        ("canonical_current_nested.yaml", "current", True, "document", "eligible"),
        ("flat_classic_config.yaml", "legacy_flat", False, "document", "requires_migration"),
        (
            "newer_major_schema.yaml",
            "future_major",
            False,
            "degraded_fallback",
            "blocked_untrusted",
        ),
        (
            "malformed.yaml",
            "malformed",
            False,
            "degraded_fallback",
            "blocked_untrusted",
        ),
    ]
    for index, (name, classification, update_check, origin, eligibility) in enumerate(
        variants
    ):
        case_root = tmp_path / f"case-{index}"
        case_root.mkdir()
        (case_root / "CLASSIC Settings.yaml").write_bytes(
            (fixture_root / name).read_bytes()
        )
        case_snapshot = classic_user_settings.open_user_settings(str(case_root))
        assert case_snapshot.classification == classification
        assert case_snapshot.update_preferences.update_check is update_check
        assert case_snapshot.update_preferences.origin == origin
        assert case_snapshot.commit_eligibility == eligibility

    legacy_root = tmp_path / "legacy"
    legacy_path = legacy_root / "CLASSIC Data" / "CLASSIC Settings.yaml"
    legacy_path.parent.mkdir(parents=True)
    legacy_path.write_bytes((fixture_root / "previous_location_nested.yaml").read_bytes())
    legacy = classic_user_settings.open_user_settings(str(legacy_root))
    assert legacy.source_location == "legacy"
    assert legacy.commit_eligibility == "requires_migration"

    missing_root = tmp_path / "missing"
    missing_root.mkdir()
    missing = classic_user_settings.open_user_settings(str(missing_root))
    assert missing.source_location == "missing"
    assert missing.source_path is None
    assert missing.classification == "missing"
    assert missing.schema_major is None
    assert missing.schema_minor is None
    assert missing.revision == "missing"
    assert missing.update_preferences.update_check is True
    assert missing.update_preferences.origin == "default"
    assert missing.original_content is None

    invalid_bytes_root = tmp_path / "invalid-bytes"
    invalid_bytes_root.mkdir()
    invalid_bytes = b"\xff\xfe\xfd"
    (invalid_bytes_root / "CLASSIC Settings.yaml").write_bytes(invalid_bytes)
    invalid_bytes_snapshot = classic_user_settings.open_user_settings(
        str(invalid_bytes_root)
    )
    assert invalid_bytes_snapshot.classification == "malformed"
    assert invalid_bytes_snapshot.original_content == invalid_bytes
