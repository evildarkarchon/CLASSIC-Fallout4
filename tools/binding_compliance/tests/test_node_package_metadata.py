"""Only the precise compile-time Node package getter earns structural metadata ownership."""

from pathlib import Path

import pytest


@pytest.fixture
def metadata_repo(tmp_path: Path) -> Path:
    """Build the minimum actual source/declaration/Cargo metadata boundary."""
    package = tmp_path / "node-bindings/classic-node"
    (package / "src").mkdir(parents=True)
    (package / "src/lib.rs").write_text(
        '#[napi]\npub fn get_version() -> String { env!("CARGO_PKG_VERSION").to_string() }\n'
    )
    (package / "index.d.ts").write_text(
        "export declare function getVersion(): string\n"
    )
    (package / "Cargo.toml").write_text(
        '[package]\nname="classic-node"\nversion="9.1.0"\n'
    )
    (package / "package.json").write_text('{"version":"0.1.0"}')
    return tmp_path


def test_metadata_uses_rust_package_version_without_runtime_claim(metadata_repo: Path):
    """The npm package version cannot replace CARGO_PKG_VERSION evidence."""
    from node_package_metadata import validate_node_package_metadata

    assert validate_node_package_metadata(metadata_repo) == {
        "binding": "node",
        "export": "getVersion",
        "rustPackageVersion": "9.1.0",
        "evidenceKind": "structural",
    }


@pytest.mark.parametrize(
    "damage",
    (
        "body",
        "comment-spoof",
        "raw-string-spoof",
        "argument",
        "declaration",
        "union",
        "shadow-macro",
    ),
)
def test_metadata_rejects_behavior_and_declaration_changes(
    metadata_repo: Path, damage: str
):
    """Changed behavior or fake source markers must return to runtime obligations."""
    from node_package_metadata import validate_node_package_metadata

    package = metadata_repo / "node-bindings/classic-node"
    source = package / "src/lib.rs"
    original = source.read_text()
    changed = original.replace(
        'env!("CARGO_PKG_VERSION").to_string()', '"invented".to_string()'
    )
    if damage == "comment-spoof":
        changed = "/* outer /* nested */\n" + original + "*/\n" + changed
    elif damage == "raw-string-spoof":
        changed = 'const FAKE: &str = r#"' + original + '"#;\n' + changed
    elif damage == "argument":
        changed = original.replace("get_version()", "get_version(input: String)")
    elif damage == "declaration":
        (package / "index.d.ts").write_text(
            "export declare function getVersion(): number\n"
        )
        changed = original
    elif damage == "union":
        (package / "index.d.ts").write_text(
            "export declare function getVersion(): string | number\n"
        )
        changed = original
    elif damage == "shadow-macro":
        changed = 'macro_rules! env { ($name:literal) => { "invented" }; }\n' + original
    source.write_text(changed)
    with pytest.raises(ValueError):
        validate_node_package_metadata(metadata_repo)
