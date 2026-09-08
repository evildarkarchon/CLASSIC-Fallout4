"""Closed producer reachability never grants runtime behavior to unreachable map accessors."""

from pathlib import Path

import pytest


@pytest.fixture
def map_repo(tmp_path: Path) -> Path:
    """Use the actual opaque module while isolating the rest of the producer graph."""
    root = Path(__file__).resolve().parents[3]
    crate = tmp_path / "cpp-bindings/classic-cpp-bridge"
    (crate / "src").mkdir(parents=True)
    (crate / "src/types.rs").write_text(
        (root / "cpp-bindings/classic-cpp-bridge/src/types.rs").read_text()
    )
    (crate / "build.rs").write_text('fn main() { let bridges = ["src/types.rs"]; }')
    return tmp_path


def test_current_unconstructible_maps_have_eleven_negative_exports(map_repo: Path):
    """Only current opaque-reference consumers are retained by the negative analyzer."""
    from cxx_opaque_map_reachability import validate_cxx_opaque_map_reachability

    exports = validate_cxx_opaque_map_reachability(map_repo)
    assert len(exports) == 11
    assert "string_map_get" in exports
    assert "string_vec_map_get" in exports


@pytest.mark.parametrize(
    "change", ("factory", "alias", "callback", "outparam", "comment-spoof")
)
def test_new_producer_or_alias_revokes_negative_disposition(
    map_repo: Path, change: str
):
    """Any path that could hand CXX a map reference must reopen runtime obligations."""
    from cxx_opaque_map_reachability import validate_cxx_opaque_map_reachability

    source = map_repo / "cpp-bindings/classic-cpp-bridge/src/types.rs"
    original = source.read_text()
    changed = original
    if change in {"factory", "comment-spoof"}:
        changed = original.replace(
            "type StringMap;",
            "type StringMap;\n        fn make_map() -> Box<StringMap>;",
        )
        if change == "comment-spoof":
            changed = "/*" + original + "*/\n" + changed
    elif change == "alias":
        changed += "\ntype ReachableAlias = StringMap;\n"
    elif change == "outparam":
        changed = original.replace(
            "type StringMap;",
            "type StringMap;\n        fn fill_map(out: &mut Box<StringMap>);",
        )
    else:
        (source.parent / "callback.rs").write_text(
            '#[cxx::bridge] mod ffi { extern "C++" { fn observe(map: &StringMap); } }'
        )
    source.write_text(changed)
    with pytest.raises(ValueError):
        validate_cxx_opaque_map_reachability(map_repo)
