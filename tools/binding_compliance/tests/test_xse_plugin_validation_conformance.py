"""XSE plugin facts require real typed results and unchanged plugin bytes."""

from pathlib import Path

from conformance.families.xse_plugin_validation import matches_plugins
from conformance.packs import load_and_validate_pack


def test_xse_plugin_fact_rejects_constructor_only_observations():
    """Address metadata or a successful constructor cannot donate validation facts."""
    assert not matches_plugins({})
    assert not matches_plugins({"result": "CorrectVersion"})


def test_xse_facts_require_unchanged_files_and_native_metadata():
    """Each authored variant proves its own fields and rejects deleted evidence."""
    root = Path(__file__).resolve().parents[3]
    pack = load_and_validate_pack(
        root, Path("tests/conformance/packs/xse_plugin_validation/v1.json")
    )
    for case in pack.document()["scenarios"]:
        assert matches_plugins(case["expected"])
        for key in case["expected"]:
            changed = dict(case["expected"])
            changed.pop(key)
            assert not matches_plugins(changed)


def test_embedded_registry_bytes_invalidate_prepared_execution(tmp_path):
    """Changing an include_str input invalidates an otherwise unchanged run plan."""
    import pytest
    import run_semantic_conformance as launcher
    from conformance.packs import (
        MaterializationError,
        load_prepared_run,
        materialize_run_plan,
    )
    from test_conformance_packs import _commit_repository, _valid_pack, _write_pack

    relative = Path("CLASSIC Data/databases/CLASSIC Main.yaml")
    assert launcher.REPO_ROOT / relative in launcher._COMMON_SOURCES
    path = tmp_path / relative
    path.parent.mkdir(parents=True)
    path.write_bytes((launcher.REPO_ROOT / relative).read_bytes())
    pack_path = _write_pack(tmp_path, _valid_pack())
    _commit_repository(tmp_path)
    pack = load_and_validate_pack(tmp_path, pack_path)
    run = materialize_run_plan(
        pack,
        participant_id="rust",
        participant_role="semantic-adapter",
        execution_instance_id="rust",
        source_paths=(path,),
    )
    path.write_bytes(path.read_bytes() + b"\n# changed embedded registry input\n")
    with pytest.raises(MaterializationError, match="source identity"):
        load_prepared_run(pack, run.run_plan_path)
