"""Unit tests for the shared parity artifact timestamp-stability helpers.

These lock the contract that keeps the checked-in baselines under
``docs/implementation/*_api_parity/baseline/`` free of timestamp-only churn:
a rerun that finds no API change must reuse the committed ``generated_at_utc``
so the write is byte-identical, while a rerun that finds a real change must
stamp the current time.

Lives directly in ``tools/`` (like ``test_triple_gate_failure.py``) rather than
in a ``tools/tests/`` package, because each ``tools/*_api_parity/tests/``
directory already contributes a top-level ``tests.conftest`` module and adding
another would widen the existing collection collision.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

from parity_artifact_io import (
    artifacts_match,
    markdown_matches_ignoring_generated_at,
    payloads_match_ignoring_generated_at,
    preserve_baseline_generated_at,
    preserve_baseline_generated_at_all,
    stable_id_hash,
    sync_baseline_artifacts,
)
from parity_artifact_io import write_json as artifact_write_json

OLD_STAMP = "2026-01-01T00:00:00+00:00"
NEW_STAMP = "2026-08-04T23:38:52.839729+00:00"

# cxx stamps second-granularity strftime output while node/python stamp
# microsecond isoformat; the helpers must treat both as opaque strings.
CXX_STAMP = "2026-01-01T00:00:00Z"


def write_json(path: Path, payload: dict) -> None:
    """Write a payload using the same formatting the parity tools use."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


class TestPayloadsMatchIgnoringGeneratedAt:
    def test_identical_apart_from_timestamp_matches(self) -> None:
        assert payloads_match_ignoring_generated_at(
            {"generated_at_utc": OLD_STAMP, "entries": [1, 2]},
            {"generated_at_utc": NEW_STAMP, "entries": [1, 2]},
        )

    def test_differing_content_does_not_match(self) -> None:
        assert not payloads_match_ignoring_generated_at(
            {"generated_at_utc": OLD_STAMP, "entries": [1, 2]},
            {"generated_at_utc": OLD_STAMP, "entries": [1, 2, 3]},
        )

    def test_inputs_are_not_mutated(self) -> None:
        """The comparison must not strip the key from the caller's dicts."""
        expected = {"generated_at_utc": OLD_STAMP, "entries": []}
        actual = {"generated_at_utc": NEW_STAMP, "entries": []}
        payloads_match_ignoring_generated_at(expected, actual)
        assert expected["generated_at_utc"] == OLD_STAMP
        assert actual["generated_at_utc"] == NEW_STAMP

    def test_nested_difference_is_still_detected(self) -> None:
        """Only the top-level timestamp is ignored, not nested content."""
        assert not payloads_match_ignoring_generated_at(
            {"generated_at_utc": OLD_STAMP, "summary": {"total": 1}},
            {"generated_at_utc": OLD_STAMP, "summary": {"total": 2}},
        )


class TestMarkdownMatchesIgnoringGeneratedAt:
    def test_header_timestamp_is_ignored(self) -> None:
        assert markdown_matches_ignoring_generated_at(
            f"# Report\n\n- Generated: `{OLD_STAMP}`\n- Rows: **3**\n",
            f"# Report\n\n- Generated: `{NEW_STAMP}`\n- Rows: **3**\n",
        )

    def test_body_difference_is_detected(self) -> None:
        assert not markdown_matches_ignoring_generated_at(
            f"# Report\n\n- Generated: `{OLD_STAMP}`\n- Rows: **3**\n",
            f"# Report\n\n- Generated: `{OLD_STAMP}`\n- Rows: **4**\n",
        )


class TestArtifactsMatch:
    def test_json_ignores_timestamp(self, tmp_path: Path) -> None:
        write_json(tmp_path / "a.json", {"generated_at_utc": OLD_STAMP, "n": 1})
        write_json(tmp_path / "b.json", {"generated_at_utc": NEW_STAMP, "n": 1})
        assert artifacts_match(tmp_path / "a.json", tmp_path / "b.json")

    def test_json_detects_real_drift(self, tmp_path: Path) -> None:
        write_json(tmp_path / "a.json", {"generated_at_utc": OLD_STAMP, "n": 1})
        write_json(tmp_path / "b.json", {"generated_at_utc": OLD_STAMP, "n": 2})
        assert not artifacts_match(tmp_path / "a.json", tmp_path / "b.json")

    def test_markdown_ignores_generated_line(self, tmp_path: Path) -> None:
        (tmp_path / "a.md").write_text(
            f"# R\n- Generated: `{OLD_STAMP}`\n- Rows: **1**\n", encoding="utf-8"
        )
        (tmp_path / "b.md").write_text(
            f"# R\n- Generated: `{NEW_STAMP}`\n- Rows: **1**\n", encoding="utf-8"
        )
        assert artifacts_match(tmp_path / "a.md", tmp_path / "b.md")

    def test_missing_file_is_a_mismatch(self, tmp_path: Path) -> None:
        write_json(tmp_path / "a.json", {"n": 1})
        assert not artifacts_match(tmp_path / "a.json", tmp_path / "absent.json")
        assert not artifacts_match(tmp_path / "absent.json", tmp_path / "a.json")

    def test_corrupt_json_raises(self, tmp_path: Path) -> None:
        """A corrupt tracked baseline is a real problem and must surface loudly."""
        (tmp_path / "a.json").write_text("{not json", encoding="utf-8")
        write_json(tmp_path / "b.json", {"n": 1})
        with pytest.raises(json.JSONDecodeError):
            artifacts_match(tmp_path / "a.json", tmp_path / "b.json")


class TestPreserveBaselineGeneratedAt:
    def test_unchanged_content_reuses_baseline_timestamp(self, tmp_path: Path) -> None:
        baseline = tmp_path / "surface.json"
        write_json(baseline, {"generated_at_utc": OLD_STAMP, "entries": [1, 2]})

        generated = {"generated_at_utc": NEW_STAMP, "entries": [1, 2]}
        preserve_baseline_generated_at(baseline, generated)

        assert generated["generated_at_utc"] == OLD_STAMP

    def test_changed_content_keeps_fresh_timestamp(self, tmp_path: Path) -> None:
        """A real API change must record when it was actually observed."""
        baseline = tmp_path / "surface.json"
        write_json(baseline, {"generated_at_utc": OLD_STAMP, "entries": [1, 2]})

        generated = {"generated_at_utc": NEW_STAMP, "entries": [1, 2, 3]}
        preserve_baseline_generated_at(baseline, generated)

        assert generated["generated_at_utc"] == NEW_STAMP

    def test_opaque_timestamp_formats_are_preserved_verbatim(
        self, tmp_path: Path
    ) -> None:
        """cxx second-granularity stamps survive alongside isoformat ones."""
        baseline = tmp_path / "surface.json"
        write_json(baseline, {"generated_at_utc": CXX_STAMP, "entries": []})

        generated = {"generated_at_utc": NEW_STAMP, "entries": []}
        preserve_baseline_generated_at(baseline, generated)

        assert generated["generated_at_utc"] == CXX_STAMP

    def test_missing_baseline_is_a_noop(self, tmp_path: Path) -> None:
        generated = {"generated_at_utc": NEW_STAMP, "entries": []}
        preserve_baseline_generated_at(tmp_path / "absent.json", generated)
        assert generated["generated_at_utc"] == NEW_STAMP

    def test_corrupt_baseline_is_a_noop(self, tmp_path: Path) -> None:
        """Preservation is an optimization; it must never introduce a failure."""
        baseline = tmp_path / "surface.json"
        baseline.write_text("{ this is not json", encoding="utf-8")

        generated = {"generated_at_utc": NEW_STAMP, "entries": []}
        preserve_baseline_generated_at(baseline, generated)

        assert generated["generated_at_utc"] == NEW_STAMP

    def test_non_dict_baseline_is_a_noop(self, tmp_path: Path) -> None:
        baseline = tmp_path / "surface.json"
        baseline.write_text('["a", "list"]', encoding="utf-8")

        generated = {"generated_at_utc": NEW_STAMP, "entries": []}
        preserve_baseline_generated_at(baseline, generated)

        assert generated["generated_at_utc"] == NEW_STAMP

    def test_non_string_baseline_timestamp_is_ignored(self, tmp_path: Path) -> None:
        baseline = tmp_path / "surface.json"
        write_json(baseline, {"generated_at_utc": 12345, "entries": []})

        generated = {"generated_at_utc": NEW_STAMP, "entries": []}
        preserve_baseline_generated_at(baseline, generated)

        assert generated["generated_at_utc"] == NEW_STAMP

    def test_baseline_without_timestamp_key_is_a_noop(self, tmp_path: Path) -> None:
        baseline = tmp_path / "surface.json"
        write_json(baseline, {"entries": []})

        generated = {"generated_at_utc": NEW_STAMP, "entries": []}
        preserve_baseline_generated_at(baseline, generated)

        assert generated["generated_at_utc"] == NEW_STAMP

    def test_baseline_file_is_not_written(self, tmp_path: Path) -> None:
        """Preservation only reads; the caller owns every write."""
        baseline = tmp_path / "surface.json"
        write_json(baseline, {"generated_at_utc": OLD_STAMP, "entries": []})
        before = baseline.read_bytes()

        preserve_baseline_generated_at(
            baseline, {"generated_at_utc": NEW_STAMP, "entries": []}
        )

        assert baseline.read_bytes() == before

    def test_write_after_preserve_is_byte_identical(self, tmp_path: Path) -> None:
        """The end-to-end property: a no-op rerun leaves the file untouched."""
        baseline = tmp_path / "surface.json"
        payload = {"generated_at_utc": OLD_STAMP, "entries": [{"symbol": "foo"}]}
        write_json(baseline, payload)
        before = baseline.read_bytes()

        regenerated = {"generated_at_utc": NEW_STAMP, "entries": [{"symbol": "foo"}]}
        preserve_baseline_generated_at(baseline, regenerated)
        write_json(baseline, regenerated)

        assert baseline.read_bytes() == before


class TestWriteJson:
    def test_formatting_matches_committed_baselines(self, tmp_path: Path) -> None:
        """indent=2, insertion order preserved, single trailing newline."""
        path = tmp_path / "out.json"
        artifact_write_json(path, {"b": 1, "a": {"nested": True}})

        assert path.read_text(encoding="utf-8") == (
            '{\n  "b": 1,\n  "a": {\n    "nested": true\n  }\n}\n'
        )

    def test_key_order_is_not_sorted(self, tmp_path: Path) -> None:
        """Sorting would rewrite every tracked baseline; insertion order is the contract."""
        path = tmp_path / "out.json"
        artifact_write_json(path, {"zebra": 1, "apple": 2})
        assert path.read_text(encoding="utf-8").index('"zebra"') < path.read_text(
            encoding="utf-8"
        ).index('"apple"')

    def test_creates_missing_parent_directories(self, tmp_path: Path) -> None:
        path = tmp_path / "deep" / "nested" / "out.json"
        artifact_write_json(path, {"n": 1})
        assert path.is_file()


class TestStableIdHash:
    def test_is_order_independent(self) -> None:
        assert stable_id_hash(["b", "a", "c"]) == stable_id_hash(["c", "b", "a"])

    def test_distinguishes_different_sets(self) -> None:
        assert stable_id_hash(["a", "b"]) != stable_id_hash(["a", "b", "c"])

    def test_empty_list_is_stable(self) -> None:
        assert stable_id_hash([]) == stable_id_hash([])


class TestSyncBaselineArtifacts:
    def test_copies_named_artifacts(self, tmp_path: Path) -> None:
        src, dst = tmp_path / "out", tmp_path / "baseline"
        src.mkdir()
        write_json(src / "a.json", {"n": 1})
        write_json(src / "b.json", {"n": 2})

        sync_baseline_artifacts(src, dst, ("a.json", "b.json"))

        assert (dst / "a.json").read_bytes() == (src / "a.json").read_bytes()
        assert (dst / "b.json").read_bytes() == (src / "b.json").read_bytes()

    def test_creates_the_baseline_directory(self, tmp_path: Path) -> None:
        src = tmp_path / "out"
        src.mkdir()
        write_json(src / "a.json", {"n": 1})

        sync_baseline_artifacts(src, tmp_path / "new" / "baseline", ("a.json",))

        assert (tmp_path / "new" / "baseline" / "a.json").is_file()

    def test_absent_source_artifact_is_skipped(self, tmp_path: Path) -> None:
        """Not every gate writes every tracked artifact on every path.

        The cxx gate leaves ``cxx_gate_report.md`` to a later step, so a refresh
        must not abort partway through. The staleness check that follows is what
        reports a genuinely missing file.
        """
        src, dst = tmp_path / "out", tmp_path / "baseline"
        src.mkdir()
        write_json(src / "present.json", {"n": 1})

        sync_baseline_artifacts(src, dst, ("present.json", "absent.json"))

        assert (dst / "present.json").is_file()
        assert not (dst / "absent.json").exists()


class TestPreserveBaselineGeneratedAtAll:
    def test_each_artifact_is_preserved_independently(self, tmp_path: Path) -> None:
        """One artifact drifting must not stop the others from being preserved."""
        write_json(tmp_path / "a.json", {"generated_at_utc": OLD_STAMP, "n": 1})
        write_json(tmp_path / "b.json", {"generated_at_utc": OLD_STAMP, "n": 1})

        unchanged = {"generated_at_utc": NEW_STAMP, "n": 1}
        drifted = {"generated_at_utc": NEW_STAMP, "n": 99}
        preserve_baseline_generated_at_all(
            tmp_path, {"a.json": unchanged, "b.json": drifted}
        )

        assert unchanged["generated_at_utc"] == OLD_STAMP
        assert drifted["generated_at_utc"] == NEW_STAMP

    def test_absent_baseline_directory_is_a_noop(self, tmp_path: Path) -> None:
        generated = {"generated_at_utc": NEW_STAMP, "n": 1}
        preserve_baseline_generated_at_all(
            tmp_path / "no-such-dir", {"a.json": generated}
        )
        assert generated["generated_at_utc"] == NEW_STAMP
