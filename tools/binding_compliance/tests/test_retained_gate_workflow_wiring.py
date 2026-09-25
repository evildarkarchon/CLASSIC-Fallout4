"""Check that Node and Python CI publish retained-gate evidence for this run."""

from pathlib import Path

import pytest
from ruamel.yaml import YAML


REPO_ROOT = Path(__file__).resolve().parents[3]
ARTIFACT_ROOT = "tools/binding_compliance/artifacts/retained/"


def _job(workflow_name: str, job_id: str) -> dict:
    """Parse a tracked workflow and return one configured job."""

    path = REPO_ROOT / ".github" / "workflows" / workflow_name
    with path.open(encoding="utf-8") as source:
        workflow = YAML(typ="safe").load(source)
    return workflow["jobs"][job_id]


def _step(job: dict, name: str) -> dict:
    """Return the unique named step so a missing or duplicate gate fails."""

    matches = [step for step in job["steps"] if step.get("name") == name]
    assert len(matches) == 1, name
    return matches[0]


def _retained_upload(job: dict) -> dict:
    """Return the single retained-gate artifact upload in this job."""

    matches = [
        step
        for step in job["steps"]
        if "retained-gates" in step.get("with", {}).get("name", "")
    ]
    assert len(matches) == 1
    upload = matches[0]
    assert upload["uses"] == "actions/upload-artifact@v6"
    assert upload["if"] == "always()"
    assert upload["with"]["path"] == ARTIFACT_ROOT
    assert upload["with"]["overwrite"] is True
    assert upload["with"]["retention-days"] == 7
    return upload


@pytest.mark.parametrize(
    ("workflow_name", "step_name", "profile", "owner", "artifact_name"),
    (
        (
            "ci-typescript.yml",
            "Run Node binding compliance profile",
            "node-ci",
            "node-ci",
            "node-parity-retained-gates",
        ),
        (
            "ci-python-bindings.yml",
            "Run Python binding compliance profile",
            "python-ci",
            "python-ci",
            "python-parity-retained-gates",
        ),
    ),
)
def test_parity_jobs_publish_their_profile_gate_evidence(
    workflow_name: str,
    step_name: str,
    profile: str,
    owner: str,
    artifact_name: str,
) -> None:
    """Catch a parity profile that runs without exporting its retained gates."""

    job = _job(workflow_name, "parity-gates")
    assert _step(job, step_name)["run"] == (
        "python tools/binding_compliance/check_compliance.py --repo-root . "
        f"--profile {profile} --gate-evidence-out "
        f"{ARTIFACT_ROOT}{owner}/gate_evidence.json"
    )
    assert _retained_upload(job)["with"]["name"] == artifact_name


def test_cxx_parity_job_publishes_profile_gate_evidence() -> None:
    """Keep the native source gate available to the full receipt-only job."""
    job = _job("ci-cpp.yml", "cxx-parity-gate")
    assert _step(job, "Run CXX binding compliance profile")["run"] == (
        "python tools/binding_compliance/check_compliance.py --repo-root . "
        f"--profile cxx-ci --gate-evidence-out {ARTIFACT_ROOT}cxx-ci/gate_evidence.json"
    )
    assert _retained_upload(job)["with"]["name"] == "cxx-parity-retained-gates"


@pytest.mark.parametrize(
    ("workflow_name", "step_name", "condition", "gate_id", "artifact_name"),
    (
        (
            "ci-typescript.yml",
            "Run Bun tests",
            "matrix.runtime == 'bun'",
            "node-bun-runtime-tests",
            "node-runtime-retained-gates-${{ matrix.runtime }}",
        ),
        (
            "ci-typescript.yml",
            "Run Node runtime smoke tests",
            "matrix.runtime == 'node'",
            "node-node-runtime-tests",
            "node-runtime-retained-gates-${{ matrix.runtime }}",
        ),
        (
            "ci-python-bindings.yml",
            "Build and install Python bindings",
            None,
            "python-bindings-rebuild",
            "python-runtime-retained-gates",
        ),
        (
            "ci-python-bindings.yml",
            "Run Python bindings smoke tests",
            None,
            "python-runtime-smoke-tests",
            "python-runtime-retained-gates",
        ),
    ),
)
def test_runtime_jobs_run_the_catalog_gate_and_upload_evidence(
    workflow_name: str,
    step_name: str,
    condition: str | None,
    gate_id: str,
    artifact_name: str,
) -> None:
    """Catch a runtime test or rebuild that bypasses the evidence runner."""

    job = _job(workflow_name, "build-and-test")
    step = _step(job, step_name)
    assert step["run"] == (
        "python tools/binding_compliance/run_retained_gate.py --repo-root . "
        f"--gate-id {gate_id} --gate-evidence-out "
        f"{ARTIFACT_ROOT}{gate_id}/gate_evidence.json"
    )
    assert step.get("if") == condition
    assert "working-directory" not in step
    assert _retained_upload(job)["with"]["name"] == artifact_name


def test_both_node_runtime_matrix_jobs_have_python_for_the_evidence_runner() -> None:
    """Keep the Bun matrix branch able to run the Python evidence launcher."""

    job = _job("ci-typescript.yml", "build-and-test")
    setup = _step(job, "Set up Python for retained gates and scan conformance")
    assert setup["uses"] == "actions/setup-python@v6"
    assert setup["with"]["python-version"] == "3.12"
    assert "if" not in setup
