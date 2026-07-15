"""Behavior tests for the User Settings ownership compliance audit."""

from __future__ import annotations

from pathlib import Path

from tools.user_settings_ownership.check import audit_repository


def test_audit_rejects_raw_user_settings_interpretation_outside_owner(
    tmp_path: Path,
) -> None:
    """A production adapter cannot interpret a first-party raw settings path."""

    source = tmp_path / "node-bindings/classic-node/src/bad.rs"
    source.parent.mkdir(parents=True)
    source.write_text(
        'let value = yaml.get("CLASSIC_Settings.FCX Mode");\n',
        encoding="utf-8",
    )

    findings = audit_repository(tmp_path)

    assert len(findings) == 1
    assert findings[0].rule == "raw-user-settings-key"


def test_audit_allows_the_deep_owner_and_non_production_evidence(tmp_path: Path) -> None:
    """The canonical owner, tests, and comments may document legacy shapes."""

    allowed = tmp_path / "business-logic/classic-user-settings-core/src/document.rs"
    allowed.parent.mkdir(parents=True)
    allowed.write_text('let key = "CLASSIC_Settings";\n', encoding="utf-8")
    test_file = tmp_path / "node-bindings/classic-node/__test__/settings.spec.ts"
    test_file.parent.mkdir(parents=True)
    test_file.write_text('const fixture = "CLASSIC_Settings";\n', encoding="utf-8")
    comment_only = tmp_path / "business-logic/example/src/lib.rs"
    comment_only.parent.mkdir(parents=True)
    comment_only.write_text("// ClassicConfig was retired.\n", encoding="utf-8")

    assert audit_repository(tmp_path) == []


def test_audit_rejects_runtime_default_mirror_use(tmp_path: Path) -> None:
    """Maintained runtime code cannot bootstrap from the compatibility mirror."""

    source = tmp_path / "classic-cli/src/bootstrap.cpp"
    source.parent.mkdir(parents=True)
    source.write_text('auto defaults = yaml["default_settings"];\n', encoding="utf-8")

    findings = audit_repository(tmp_path)

    assert len(findings) == 1
    assert findings[0].rule == "compatibility-mirror-runtime-use"


def test_audit_rejects_runtime_default_mirror_use_inside_owner(tmp_path: Path) -> None:
    """The deep owner cannot bypass its Rust registry to bootstrap from the mirror."""

    source = tmp_path / "business-logic/classic-user-settings-core/src/bootstrap.rs"
    source.parent.mkdir(parents=True)
    source.write_text('let defaults = yaml["default_settings"].clone();\n', encoding="utf-8")

    findings = audit_repository(tmp_path)

    assert len(findings) == 1
    assert findings[0].rule == "compatibility-mirror-runtime-use"


def test_audit_allows_the_compatibility_mirror_generator(tmp_path: Path) -> None:
    """The one-way generator may inspect the mirror it verifies and replaces."""

    source = (
        tmp_path
        / "business-logic/classic-user-settings-core/src/bin/"
        "generate-user-settings-default-mirror/mirror.rs"
    )
    source.parent.mkdir(parents=True)
    source.write_text('let defaults = yaml["default_settings"].clone();\n', encoding="utf-8")

    assert audit_repository(tmp_path) == []


def test_audit_ignores_inline_python_comments(tmp_path: Path) -> None:
    """Forbidden historical names in inline Python comments are not code ownership."""

    source = tmp_path / "python-bindings/example/src/module.py"
    source.parent.mkdir(parents=True)
    source.write_text(
        'label = "safe # text"  # ClassicConfig was retired here\n',
        encoding="utf-8",
    )

    assert audit_repository(tmp_path) == []


def test_audit_rejects_legacy_model_declaration_inside_owner(tmp_path: Path) -> None:
    """The owner may diagnose legacy input but cannot restore the retired facade."""

    source = tmp_path / "business-logic/classic-user-settings-core/src/legacy.rs"
    source.parent.mkdir(parents=True)
    source.write_text("pub struct ClassicConfig;\n", encoding="utf-8")

    findings = audit_repository(tmp_path)

    assert len(findings) == 1
    assert findings[0].rule == "legacy-user-settings-type"


def test_audit_rejects_generic_settings_variant_declaration(tmp_path: Path) -> None:
    """A generic YAML enum cannot regain a User Settings variant."""

    source = tmp_path / "business-logic/example/src/yaml_source.rs"
    source.parent.mkdir(parents=True)
    source.write_text(
        "pub enum YamlSource {\n    Main,\n    Settings,\n}\n",
        encoding="utf-8",
    )

    findings = audit_repository(tmp_path)

    assert len(findings) == 1
    assert findings[0].rule == "legacy-generic-settings-owner"
