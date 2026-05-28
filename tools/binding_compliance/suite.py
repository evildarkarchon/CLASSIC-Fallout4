"""Execution and reporting for the binding compliance suite."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
import json
import os
from pathlib import Path
import subprocess
from typing import Any, Iterable

from catalog import ComplianceRequirement, requirements_for_profile  # type: ignore


@dataclass
class RequirementResult:
    """Structured outcome for one compliance requirement."""

    id: str
    surface: str
    classification: str
    status: str
    blocking: bool
    summary: str
    title: str = ""
    evidence: list[str] = field(default_factory=list)
    gaps: list[str] = field(default_factory=list)
    failure_kind: str | None = None
    stdout: str = ""
    stderr: str = ""


def _combined_output(result: RequirementResult) -> str:
    return "\n".join(part for part in (result.stdout, result.stderr) if part)


def classify_failure(output: str, *, command_missing: bool = False) -> str:
    """Classify a failing check into the prompt's compliance failure buckets."""

    lowered = output.lower()
    if command_missing:
        return "local_environment_failure"
    if "stale" in lowered and "artifact" in lowered:
        return "stale_generated_artifact"
    if "baseline" in lowered and ("stale" in lowered or "refresh" in lowered):
        return "stale_baseline"
    if "runtime coverage" in lowered or "missing runtime" in lowered:
        return "missing_runtime_coverage"
    if "contradict" in lowered or "unsupported" in lowered:
        return "policy_source_contradiction"
    if "not found" in lowered or "no such file" in lowered:
        return "local_environment_failure"
    return "true_binding_compliance_gap"


def build_summary(
    results: Iterable[RequirementResult], *, fail_on_gaps: bool = False
) -> dict[str, Any]:
    """Build the top-level pass/fail summary from requirement results."""

    result_list = list(results)
    failed = [result for result in result_list if result.status == "failed"]
    blocking_failed = [result for result in failed if result.blocking]
    coverage_gaps = [result for result in result_list if result.status == "gap"]
    skipped = [result for result in result_list if result.status == "skipped"]
    passed = [result for result in result_list if result.status == "passed"]

    top_level = (
        "fail" if blocking_failed or (fail_on_gaps and coverage_gaps) else "pass"
    )
    return {
        "result": top_level,
        "total": len(result_list),
        "passed": len(passed),
        "failed": len(failed),
        "blocking_failed": len(blocking_failed),
        "coverage_gaps": len(coverage_gaps),
        "skipped": len(skipped),
    }


class ComplianceSuite:
    """Evaluate binding compliance requirements for one execution profile."""

    def __init__(
        self,
        *,
        repo_root: Path,
        profile: str,
        requirements: tuple[ComplianceRequirement, ...] | None = None,
        skip_commands: bool = False,
        fail_on_gaps: bool = False,
    ) -> None:
        """Create a suite runner bound to a repository root and profile."""

        self.repo_root = repo_root.resolve()
        self.profile = profile
        self.requirements = requirements or requirements_for_profile(profile)
        self.skip_commands = skip_commands
        self.fail_on_gaps = fail_on_gaps

    def run(self) -> dict[str, Any]:
        """Evaluate all selected requirements and return a structured report."""

        results = [
            self._evaluate_requirement(requirement) for requirement in self.requirements
        ]
        report = {
            "schemaVersion": 1,
            "profile": self.profile,
            "repoRoot": str(self.repo_root),
            "summary": build_summary(results, fail_on_gaps=self.fail_on_gaps),
            "requirements": [asdict(result) for result in results],
            "gaps": [
                {
                    "requirementId": result.id,
                    "surface": result.surface,
                    "classification": result.classification,
                    "message": gap,
                }
                for result in results
                for gap in result.gaps
            ],
        }
        return report

    def _evaluate_requirement(
        self, requirement: ComplianceRequirement
    ) -> RequirementResult:
        """Evaluate a single requirement via static evidence and optional command."""

        if requirement.classification == "coverage_gap":
            return RequirementResult(
                id=requirement.id,
                title=requirement.title,
                surface=requirement.surface,
                classification=requirement.classification,
                status="gap",
                blocking=requirement.blocking,
                summary=requirement.summary,
                gaps=list(requirement.gaps),
            )

        static_errors, evidence = self._check_static_evidence(requirement)
        if static_errors:
            return RequirementResult(
                id=requirement.id,
                title=requirement.title,
                surface=requirement.surface,
                classification=requirement.classification,
                status="failed",
                blocking=requirement.blocking,
                summary=requirement.summary,
                evidence=evidence,
                failure_kind=classify_failure("\n".join(static_errors)),
                stderr="\n".join(static_errors),
            )

        if requirement.command is None:
            return RequirementResult(
                id=requirement.id,
                title=requirement.title,
                surface=requirement.surface,
                classification=requirement.classification,
                status="passed",
                blocking=requirement.blocking,
                summary=requirement.summary,
                evidence=evidence,
            )

        if self.skip_commands:
            return RequirementResult(
                id=requirement.id,
                title=requirement.title,
                surface=requirement.surface,
                classification=requirement.classification,
                status="skipped",
                blocking=requirement.blocking,
                summary=requirement.summary,
                evidence=evidence + ["Command skipped by --skip-commands."],
            )

        return self._run_command_requirement(requirement, evidence)

    def _check_static_evidence(
        self, requirement: ComplianceRequirement
    ) -> tuple[list[str], list[str]]:
        """Check required files and text expectations for a requirement."""

        errors: list[str] = []
        evidence: list[str] = []

        for rel_path in requirement.paths:
            path = self.repo_root / rel_path
            if not path.exists():
                errors.append(f"Missing required path: {rel_path}")
            else:
                evidence.append(f"Found {rel_path}")

        for expectation in requirement.text_expectations:
            path = self.repo_root / expectation.path
            if not path.exists():
                errors.append(f"Missing text expectation file: {expectation.path}")
                continue
            content = path.read_text(encoding="utf-8")
            missing = [
                needle for needle in expectation.contains if needle not in content
            ]
            if missing:
                errors.append(
                    f"{expectation.path} is missing expected text: {', '.join(missing)}"
                )
            else:
                evidence.append(f"{expectation.path} contains expected policy text")

        return errors, evidence

    def _run_command_requirement(
        self, requirement: ComplianceRequirement, evidence: list[str]
    ) -> RequirementResult:
        """Run the command associated with a requirement and capture evidence."""

        assert requirement.command is not None
        command = requirement.command
        cwd = self.repo_root / command.cwd if command.cwd else self.repo_root
        env = os.environ.copy()
        for key, value in command.env:
            env[key] = value.format(repo_root=str(self.repo_root))

        try:
            completed = subprocess.run(
                list(command.argv),
                cwd=str(cwd),
                env=env,
                text=True,
                capture_output=True,
                stdin=subprocess.DEVNULL,
                timeout=command.timeout_seconds,
                check=False,
            )
        except FileNotFoundError as exc:
            return RequirementResult(
                id=requirement.id,
                title=requirement.title,
                surface=requirement.surface,
                classification=requirement.classification,
                status="failed",
                blocking=requirement.blocking,
                summary=requirement.summary,
                evidence=evidence,
                failure_kind=classify_failure(str(exc), command_missing=True),
                stderr=str(exc),
            )
        except subprocess.TimeoutExpired as exc:
            message = f"Command timed out after {command.timeout_seconds} seconds: {command.argv}"
            return RequirementResult(
                id=requirement.id,
                title=requirement.title,
                surface=requirement.surface,
                classification=requirement.classification,
                status="failed",
                blocking=requirement.blocking,
                summary=requirement.summary,
                evidence=evidence,
                failure_kind="local_environment_failure",
                stdout=str(exc.stdout) if exc.stdout else "",
                stderr=str(exc.stderr) if exc.stderr else message,
            )

        status = "passed" if completed.returncode == 0 else "failed"
        result = RequirementResult(
            id=requirement.id,
            title=requirement.title,
            surface=requirement.surface,
            classification=requirement.classification,
            status=status,
            blocking=requirement.blocking,
            summary=requirement.summary,
            evidence=evidence + [f"Ran: {' '.join(command.argv)}"],
            stdout=completed.stdout,
            stderr=completed.stderr,
        )
        if status == "failed":
            result.failure_kind = classify_failure(_combined_output(result))
        return result


def render_markdown(report: dict[str, Any]) -> str:
    """Render a human-readable compliance report from structured output."""

    summary = report["summary"]
    lines = [
        "# Binding Compliance Report",
        "",
        f"- Profile: `{report['profile']}`",
        f"- Result: **{summary['result'].upper()}**",
        f"- Requirements: **{summary['total']}**",
        f"- Passed: **{summary['passed']}**",
        f"- Failed: **{summary['failed']}**",
        f"- Coverage gaps: **{summary['coverage_gaps']}**",
        f"- Skipped: **{summary['skipped']}**",
        "",
        "## Requirements",
        "",
        "| ID | Surface | Classification | Status | Blocking | Failure Kind |",
        "|---|---|---|---|---:|---|",
    ]
    for requirement in report["requirements"]:
        lines.append(
            "| `{id}` | `{surface}` | `{classification}` | `{status}` | {blocking} | {failure_kind} |".format(
                id=requirement["id"],
                surface=requirement["surface"],
                classification=requirement["classification"],
                status=requirement["status"],
                blocking="yes" if requirement["blocking"] else "no",
                failure_kind=requirement.get("failure_kind") or "-",
            )
        )

    if report["gaps"]:
        lines.extend(("", "## Coverage Gaps", ""))
        for gap in report["gaps"]:
            lines.append("- `{requirementId}` ({surface}): {message}".format(**gap))

    lines.append("")
    return "\n".join(lines)


def write_report_files(report: dict[str, Any], output_dir: Path) -> tuple[Path, Path]:
    """Write JSON and markdown compliance reports and return their paths."""

    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "binding_compliance_report.json"
    markdown_path = output_dir / "binding_compliance_report.md"
    json_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    markdown_path.write_text(render_markdown(report), encoding="utf-8")
    return json_path, markdown_path
