"""CI topology checks for the single pinned native Corrosion source artifact."""

import re
from pathlib import Path


WORKFLOW = Path(__file__).resolve().parents[3] / ".github/workflows/ci-cpp.yml"
CORROSION_COMMIT = "1499b14e4906a2890f5cee1547c8848db261753d"


def _job_block(source: str, job_name: str) -> str:
    """Return one workflow job so its steps can be checked independently."""
    match = re.search(rf"(?m)^  {re.escape(job_name)}:\s*$", source)
    assert match is not None
    next_job = re.search(r"(?m)^  [a-zA-Z0-9_-]+:\s*$", source[match.end():])
    end = match.end() + next_job.start() if next_job is not None else len(source)
    return source[match.start():end]


def test_native_jobs_share_one_verified_corrosion_source_artifact() -> None:
    """Both compiler matrices consume the source verified by one fetch job."""
    source = WORKFLOW.read_text(encoding="utf-8")
    fetch_job = _job_block(source, "corrosion-source")
    assert "matrix:" not in fetch_job
    assert "git clone" in fetch_job
    assert CORROSION_COMMIT in fetch_job
    assert re.search(r"\bgit\s+-C\s+\$sourceDir\s+archive\b", fetch_job)
    assert "uses: actions/upload-artifact@v6" in fetch_job
    assert "name: corrosion-source-v0.6.1" in fetch_job
    assert "overwrite: true" in fetch_job

    for job_name, build_name in (("cli-tests", "Build and test CLI"), ("gui-tests", "Build and test GUI")):
        job = _job_block(source, job_name)
        assert "needs: [cxx-parity-gate, corrosion-source]" in job
        assert "uses: actions/download-artifact@v8" in job
        assert "name: corrosion-source-v0.6.1" in job
        assert "Expand-Archive" in job
        assert "CLASSIC_CORROSION_SOURCE_DIR" in job
        assert job.index("Expand-Archive") < job.index(build_name)
