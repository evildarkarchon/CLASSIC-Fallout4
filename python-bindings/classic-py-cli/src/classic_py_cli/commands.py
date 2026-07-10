"""Command handlers for binding diagnostics, compliance, and product workflows."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from .binding_loader import list_bindings, require_binding
from .context import CommandContext
from .exit_codes import ExitCode, worst_exit_code
from .output import CommandResult, binding_exception, failure, success
from .scenarios import Scenario, all_scenarios, get_scenario, scenarios_for_profile


class _ComplianceExplainArgs(Protocol):
    """Arguments supplied by the `compliance explain` parser."""

    scenario_id: str


class _ComplianceRunArgs(Protocol):
    """Arguments supplied by the `compliance run` parser."""

    profile: str


class _VersionParseArgs(Protocol):
    """Arguments supplied by the `version parse` parser."""

    version: str


class _PathArg(Protocol):
    """Arguments supplied by parser commands that require a path."""

    path: str


class _OptionalPathArg(Protocol):
    """Arguments supplied by parser commands that accept an optional path."""

    path: str | None


class _XseParseTypeArgs(Protocol):
    """Arguments supplied by the `xse parse-type` parser."""

    type_name: str


class _UpdateValidateUrlArgs(Protocol):
    """Arguments supplied by the `update validate-url` parser."""

    url: str


@dataclass
class _VersionParseCommandArgs:
    """Synthetic args for catalog-dispatched version scenarios."""

    version: str


@dataclass
class _PathCommandArgs:
    """Synthetic args for catalog-dispatched path scenarios."""

    path: str


@dataclass
class _OptionalPathCommandArgs:
    """Synthetic args for catalog-dispatched commands with optional paths."""

    path: str | None = None


def _relative_or_absolute(path: Path, root: Path) -> str:
    """Return a readable path relative to the repo root when possible."""

    try:
        return str(path.resolve().relative_to(root.resolve()))
    except ValueError:
        return str(path)


def bindings_list(args: object, context: CommandContext) -> CommandResult:
    """List maintained Python binding modules and import diagnostics."""

    diagnostics = [diagnostic.to_dict() for diagnostic in list_bindings()]
    missing = [item for item in diagnostics if not item["importable"]]
    lines = ["CLASSIC Python bindings:"]
    lines.extend(f"  {'OK' if item['importable'] else 'MISSING'} {item['module']}" for item in diagnostics)
    return success(
        "bindings list",
        f"{len(diagnostics) - len(missing)}/{len(diagnostics)} bindings importable",
        {"bindings": diagnostics, "missing": missing},
        text_lines=lines,
    )


def bindings_smoke(args: object, context: CommandContext) -> CommandResult:
    """Run cheap import smoke checks over the maintained binding inventory."""

    diagnostics = [diagnostic.to_dict() for diagnostic in list_bindings()]
    missing = [item for item in diagnostics if not item["importable"]]
    if missing:
        return failure(
            "bindings smoke",
            f"{len(missing)} binding modules failed to import",
            int(ExitCode.BINDING_IMPORT),
            data={"bindings": diagnostics, "missing": missing},
            text_lines=[f"Binding smoke failed: {item['module']} ({item['error_type']})" for item in missing],
        )
    return success("bindings smoke", "All maintained bindings imported", {"bindings": diagnostics})


def doctor(args: object, context: CommandContext) -> CommandResult:
    """Check local Python binding environment readiness."""

    python_bindings = context.repo_root / "python-bindings"
    venv = python_bindings / ".venv"
    checks = [
        {"id": "repo-root", "ok": (context.repo_root / "Cargo.toml").exists(), "path": str(context.repo_root)},
        {"id": "python-bindings", "ok": python_bindings.exists(), "path": str(python_bindings)},
        {"id": "uv-venv", "ok": venv.exists(), "path": str(venv)},
        {"id": "fixture-root", "ok": context.fixture_root.exists(), "path": str(context.fixture_root)},
        {"id": "maturin", "ok": _tool_available("maturin"), "path": "maturin"},
        {"id": "uv", "ok": _tool_available("uv"), "path": "uv"},
    ]
    binding_diagnostics = [diagnostic.to_dict() for diagnostic in list_bindings()]
    missing = [item for item in binding_diagnostics if not item["importable"]]
    checks.append({"id": "rebuilt-bindings", "ok": not missing, "missing": [item["module"] for item in missing]})
    failed = [check for check in checks if not check["ok"]]
    data = {"checks": checks, "bindings": binding_diagnostics, "python": sys.executable}
    if failed:
        code = int(ExitCode.BINDING_IMPORT) if missing else int(ExitCode.USAGE)
        return failure("doctor", f"{len(failed)} readiness checks failed", code, data=data, text_lines=[f"FAIL {check['id']}" for check in failed])
    return success("doctor", "Python binding environment is ready", data, text_lines=["Python binding environment is ready"])


def _tool_available(tool: str) -> bool:
    """Return whether a tool can be launched from the current environment."""

    try:
        subprocess.run([tool, "--version"], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=10)
    except (OSError, subprocess.TimeoutExpired):
        return False
    return True


def compliance_list(args: object, context: CommandContext) -> CommandResult:
    """List compliance scenarios from the data-backed catalog."""

    scenarios = [scenario.to_dict() for scenario in all_scenarios()]
    lines = ["CLASSIC Python CLI compliance scenarios:"]
    lines.extend(f"  {scenario['id']} [{', '.join(scenario['profiles'])}]" for scenario in scenarios)
    return success("compliance list", f"{len(scenarios)} scenarios", {"scenarios": scenarios}, text_lines=lines)


def compliance_explain(args: _ComplianceExplainArgs, context: CommandContext) -> CommandResult:
    """Explain one compliance scenario by stable ID."""

    scenario_id = args.scenario_id
    scenario = get_scenario(scenario_id)
    if scenario is None:
        return failure("compliance explain", f"Unknown scenario: {scenario_id}", int(ExitCode.USAGE))
    data = scenario.to_dict()
    lines = [
        f"{scenario.id}: {scenario.purpose}",
        f"Owner: {scenario.owner}",
        f"Covered exports: {', '.join(scenario.covered_exports)}",
        f"Command: classic-py {' '.join(scenario.command)}",
        f"Fixtures: {', '.join(scenario.fixture_requirements) if scenario.fixture_requirements else 'none'}",
        f"Expected exit: {scenario.expected_exit_code}",
        f"Failure classifications: {', '.join(scenario.failure_classifications)}",
    ]
    return success("compliance explain", scenario.purpose, {"scenario": data}, text_lines=lines)


def compliance_run(args: _ComplianceRunArgs, context: CommandContext) -> CommandResult:
    """Run a compliance profile and write JSON and Markdown reports."""

    profile = args.profile
    scenarios = scenarios_for_profile(profile)
    if not scenarios:
        return failure("compliance run", f"No scenarios match profile {profile!r}", int(ExitCode.USAGE))
    scenario_results = [_run_scenario(scenario, context) for scenario in scenarios]
    delegated = _run_python_ci_delegates(context) if profile == "python-ci" else []
    aggregate_codes = [result["exitCode"] for result in scenario_results] + [gate["exitCode"] for gate in delegated]
    aggregate_codes.extend(int(ExitCode.PRODUCT_FAILURE) for result in scenario_results if result["status"] != "passed")
    exit_code = worst_exit_code(aggregate_codes)
    report = {
        "schemaVersion": "1.0",
        "profile": profile,
        "environment": {"repoRoot": str(context.repo_root), "fixtureRoot": str(context.fixture_root), "python": sys.executable},
        "scenarioResults": scenario_results,
        "delegatedGates": delegated,
        "coveredExports": sorted({export for scenario in scenarios for export in scenario.covered_exports}),
        "failureClassifications": sorted({classification for scenario in scenarios for classification in scenario.failure_classifications}),
    }
    artifacts = _write_reports(report, context)
    summary = f"Compliance profile {profile} {'passed' if exit_code == 0 else 'failed'}"
    lines = [summary, *(f"  {item['id']}: {item['status']}" for item in scenario_results)]
    if exit_code == 0:
        return success("compliance run", summary, {"report": report}, artifacts=artifacts, text_lines=lines)
    return failure("compliance run", summary, exit_code, data={"report": report}, artifacts=artifacts, text_lines=lines)


def _run_scenario(scenario: Scenario, context: CommandContext) -> dict[str, Any]:
    """Execute one scenario through the same handler surface used by users."""

    result = dispatch_scenario_command(scenario.command, context)
    contract_failure = _scenario_contract_failure(scenario, result)
    passed = result.exit_code == scenario.expected_exit_code and contract_failure is None
    scenario_result = {
        "id": scenario.id,
        "owner": scenario.owner,
        "commandLine": ["classic-py", *scenario.command],
        "expectedExitCode": scenario.expected_exit_code,
        "exitCode": result.exit_code,
        "status": "passed" if passed else "failed",
        "summary": contract_failure or result.summary,
        "coveredExports": scenario.covered_exports,
        "failureClassifications": scenario.failure_classifications if not passed else [],
    }
    if contract_failure is not None:
        scenario_result["contractFailure"] = contract_failure
    report_data = _scenario_report_data(result)
    if report_data:
        scenario_result["data"] = report_data
    return scenario_result


def _scenario_contract_failure(scenario: Scenario, result: CommandResult) -> str | None:
    """Return a scenario-specific semantic failure not captured by exit status."""

    if scenario.id != "scanlog-addictol-newer-than-floor" or result.exit_code != int(ExitCode.SUCCESS):
        return None

    if result.data.get("processedLogs") != 1:
        return "Addictol scanlog scenario did not process exactly one log"
    if result.data.get("failedLogs") != 0:
        return "Addictol scanlog scenario reported failed logs"

    evidence = result.data.get("reportEvidence", [])
    if len(evidence) != 1:
        return "Addictol scanlog scenario did not capture exactly one report evidence item"
    if evidence[0].get("outdatedWarningPresent"):
        return "Addictol scanlog scenario produced an outdated-version warning"

    valid_line = str(evidence[0].get("validVersionLine", ""))
    if "you have a valid version of addictol" not in valid_line.lower():
        return "Addictol scanlog scenario did not prove a valid Addictol version"
    return None


def _scenario_report_data(result: CommandResult) -> dict[str, Any]:
    """Return compact command data worth preserving in compliance reports."""

    if result.command != "scan logs":
        return {}
    return {
        "scanPath": result.data.get("scanPath"),
        "processedLogs": result.data.get("processedLogs"),
        "successfulLogs": result.data.get("successfulLogs"),
        "failedLogs": result.data.get("failedLogs"),
        "failures": result.data.get("failures", []),
        "reportEvidence": result.data.get("reportEvidence", []),
    }


def _run_python_ci_delegates(context: CommandContext) -> list[dict[str, Any]]:
    """Run source-level gates delegated by the python-ci profile."""

    commands = [
        [sys.executable, "tools/python_api_parity/check_parity_gate.py", "--repo-root", "."],
        [sys.executable, "tools/binding_compliance/check_compliance.py", "--repo-root", ".", "--profile", "python-ci"],
    ]
    gates: list[dict[str, Any]] = []
    for command in commands:
        completed = subprocess.run(command, cwd=context.repo_root, check=False, text=True, capture_output=True)
        gates.append({"commandLine": command, "exitCode": completed.returncode, "stdout": completed.stdout[-4000:], "stderr": completed.stderr[-4000:]})
    return gates


def _write_reports(report: dict[str, Any], context: CommandContext) -> list[str]:
    """Write JSON and Markdown compliance reports from shared report data."""

    output_dir = context.output_path or context.repo_root / "python-bindings" / "parity-artifacts"
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "classic_python_cli_report.json"
    md_path = output_dir / "classic_python_cli_report.md"
    json_path.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    md_lines = ["# CLASSIC Python CLI Report", "", f"Profile: `{report['profile']}`", "", "## Scenarios"]
    md_lines.extend(f"- `{item['id']}`: {item['status']} (exit {item['exitCode']}) - {item['summary']}" for item in report["scenarioResults"])
    if report["delegatedGates"]:
        md_lines.extend(["", "## Delegated Gates"])
        md_lines.extend(f"- `{' '.join(item['commandLine'])}`: exit {item['exitCode']}" for item in report["delegatedGates"])
    md_path.write_text("\n".join(md_lines) + "\n", encoding="utf-8")
    return [_relative_or_absolute(json_path, context.repo_root), _relative_or_absolute(md_path, context.repo_root)]


def version_parse(args: _VersionParseArgs, context: CommandContext) -> CommandResult:
    """Parse and format a version through the classic_version binding."""

    try:
        module = require_binding("classic_version")
        parsed = module.parse_version(args.version)
        formatted = module.format_version(parsed)
    except ImportError as exc:
        return failure("version parse", str(exc), int(ExitCode.BINDING_IMPORT))
    except Exception as exc:  # noqa: BLE001 - preserve public binding exception detail.
        return binding_exception("version parse", "classic_version", exc)
    return success("version parse", f"{args.version} -> {formatted}", {"input": args.version, "parsed": list(parsed), "formatted": formatted})


def config_main_version(args: object, context: CommandContext) -> CommandResult:
    """Load the main CLASSIC YAML version through classic_config."""

    try:
        module = require_binding("classic_config")
        version = module.load_main_yaml_version(str(context.repo_root / "CLASSIC Data" / "databases"))
    except ImportError as exc:
        return failure("config main-version", str(exc), int(ExitCode.BINDING_IMPORT))
    except Exception as exc:  # noqa: BLE001 - preserve public binding exception detail.
        return binding_exception("config main-version", "classic_config", exc)
    return success("config main-version", f"CLASSIC main YAML version: {version}", {"version": version})


def config_inspect(args: _PathArg, context: CommandContext) -> CommandResult:
    """Inspect a CLASSIC config file through classic_config."""

    try:
        module = require_binding("classic_config")
        config = module.ClassicConfig.load_from_yaml(args.path)
        data = {"game": getattr(config, "game", None), "gameVersion": getattr(config, "game_version", None), "path": args.path}
    except ImportError as exc:
        return failure("config inspect", str(exc), int(ExitCode.BINDING_IMPORT))
    except Exception as exc:  # noqa: BLE001 - preserve public binding exception detail.
        return binding_exception("config inspect", "classic_config", exc)
    return success("config inspect", f"Loaded config {args.path}", data)


def path_validate(args: _PathArg, context: CommandContext) -> CommandResult:
    """Validate a path through classic_path.PathValidator."""

    target = Path(args.path)
    if not target.is_absolute():
        target = context.repo_root / target
    try:
        module = require_binding("classic_path")
        valid = module.PathValidator.is_valid_path(str(target))
    except ImportError as exc:
        return failure("path validate", str(exc), int(ExitCode.BINDING_IMPORT))
    except Exception as exc:  # noqa: BLE001 - preserve public binding exception detail.
        return binding_exception("path validate", "classic_path", exc)
    if not valid:
        return failure("path validate", f"Path is not valid: {target}", int(ExitCode.PRODUCT_FAILURE), data={"path": str(target), "valid": False})
    return success("path validate", f"Path is valid: {target}", {"path": str(target), "valid": True})


def file_hash(args: _PathArg, context: CommandContext) -> CommandResult:
    """Hash a file through classic_file_io.FileHasher."""

    target = Path(args.path)
    if not target.is_absolute():
        target = context.repo_root / target
    try:
        module = require_binding("classic_file_io")
        digest = module.FileHasher.hash_file(str(target))
    except ImportError as exc:
        return failure("file hash", str(exc), int(ExitCode.BINDING_IMPORT))
    except Exception as exc:  # noqa: BLE001 - preserve public binding exception detail.
        return binding_exception("file hash", "classic_file_io", exc)
    return success("file hash", f"{_relative_or_absolute(target, context.repo_root)} {digest}", {"path": str(target), "sha256": digest})


def database_info(args: object, context: CommandContext) -> CommandResult:
    """Report deterministic database binding constants when available."""

    try:
        module = require_binding("classic_database")
        data = {name: getattr(module, name) for name in ("DEFAULT_CACHE_TTL", "BATCH_CACHE_TTL", "MAX_CACHE_TTL") if hasattr(module, name)}
    except ImportError as exc:
        return failure("database info", str(exc), int(ExitCode.BINDING_IMPORT))
    return success("database info", "Database binding constants loaded", data)


def xse_parse_type(args: _XseParseTypeArgs, context: CommandContext) -> CommandResult:
    """Parse an XSE type through classic_xse when available."""

    try:
        module = require_binding("classic_xse")
        value = module.parse_xse_type(args.type_name)
    except ImportError as exc:
        return failure("xse parse-type", str(exc), int(ExitCode.BINDING_IMPORT))
    except Exception as exc:  # noqa: BLE001 - preserve public binding exception detail.
        return binding_exception("xse parse-type", "classic_xse", exc)
    return success("xse parse-type", f"Parsed XSE type: {value}", {"type": str(value)})


def update_validate_url(args: _UpdateValidateUrlArgs, context: CommandContext) -> CommandResult:
    """Validate update URL shape through classic_web to avoid live network access."""

    try:
        module = require_binding("classic_web")
        valid = module.is_valid_url(args.url)
    except ImportError as exc:
        return failure("update validate-url", str(exc), int(ExitCode.BINDING_IMPORT))
    except Exception as exc:  # noqa: BLE001 - preserve public binding exception detail.
        return binding_exception("update validate-url", "classic_web", exc)
    if not valid:
        return failure("update validate-url", f"URL is not valid: {args.url}", int(ExitCode.PRODUCT_FAILURE), data={"url": args.url, "valid": False})
    return success("update validate-url", f"URL valid: {valid}", {"url": args.url, "valid": valid})


def resource_detect(args: _PathArg, context: CommandContext) -> CommandResult:
    """Detect a resource type through classic_resource when available."""

    try:
        module = require_binding("classic_resource")
        resource_type = module.detect_resource_type(args.path)
    except ImportError as exc:
        return failure("resource detect", str(exc), int(ExitCode.BINDING_IMPORT))
    except Exception as exc:  # noqa: BLE001 - preserve public binding exception detail.
        return binding_exception("resource detect", "classic_resource", exc)
    return success("resource detect", f"Resource type: {resource_type}", {"path": args.path, "resourceType": str(resource_type)})


def _scan_result_success(result: object) -> bool:
    """Return the per-log success flag from a scanlog result-like object."""

    value = getattr(result, "success", False)
    if callable(value):
        value = value()
    return bool(value)


def _scan_failure_summary(result: object) -> dict[str, str]:
    """Return a JSON-safe summary for a failed per-log scan result."""

    log_path = getattr(result, "log_path", getattr(result, "logPath", ""))
    error = getattr(result, "error", None)
    summary = {"logPath": str(log_path)}
    if error is not None:
        summary["error"] = str(error)
    return summary


def _scan_report_text(result: object) -> str:
    """Return report text from a scanlog result-like object."""

    autoscan_report_path = getattr(result, "autoscan_report_path", None)
    if autoscan_report_path:
        report_path = Path(str(autoscan_report_path))
        if report_path.is_file():
            return report_path.read_text(encoding="utf-8")

    get_report_text = getattr(result, "get_report_text", None)
    if callable(get_report_text):
        return str(get_report_text())
    report_lines = getattr(result, "report_lines", [])
    return "".join(str(line) for line in report_lines)


def _scan_report_evidence(result: object) -> dict[str, Any]:
    """Summarize version-validation evidence from one successful scan report."""

    report_text = _scan_report_text(result)
    evidence: dict[str, Any] = {
        "logPath": str(getattr(result, "log_path", getattr(result, "logPath", ""))),
        "outdatedWarningPresent": "OUTDATED" in report_text.upper(),
    }
    for line in report_text.splitlines():
        stripped = line.strip()
        if "you have a valid version of" in stripped.lower():
            evidence["validVersionLine"] = stripped
            break
    return evidence


def _path_is_relative_to(path: Path, root: Path) -> bool:
    """Return whether path is under root without requiring either to exist."""

    try:
        path.resolve().relative_to(root.resolve())
    except ValueError:
        return False
    return True


def _fixture_yaml_root(scan_path: Path, context: CommandContext) -> Path | None:
    """Find a fixture-local YAML root for deterministic compliance scans."""

    for root in (context.fixture_root, context.repo_root / "python-bindings" / "tests" / "fixtures"):
        if _path_is_relative_to(scan_path, root) and (root / "CLASSIC Data").exists():
            return root.resolve()
    return None


@contextmanager
def _working_directory(path: Path):
    """Temporarily set CWD for bindings that discover fixture data relative to it."""

    previous = Path.cwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(previous)


def scan_logs(args: _OptionalPathArg, context: CommandContext) -> CommandResult:
    """Run a deterministic scanlog binding path over an explicit log directory."""

    scan_path = Path(args.path or context.fixture_root)
    if not scan_path.is_absolute():
        scan_path = context.repo_root / scan_path
    yaml_dir_root = _fixture_yaml_root(scan_path, context) or context.repo_root
    yaml_dir_data = yaml_dir_root / "CLASSIC Data"
    try:
        module = require_binding("classic_scanlog")
        paths = [str(path) for path in scan_path.glob("*.log")] if scan_path.is_dir() else [str(scan_path)]
        with _working_directory(yaml_dir_root):
            # Explicit CLI paths must select Targeted mode so Rust does not replace them with Standard discovery.
            result = module.scan_run_execute(
                str(yaml_dir_root),
                str(yaml_dir_data),
                "Fallout4",
                "auto",
                paths,
                targeted_mode=True,
            )
    except ImportError as exc:
        return failure("scan logs", str(exc), int(ExitCode.BINDING_IMPORT))
    except AttributeError:
        return failure("scan logs", "classic_scanlog does not expose scan_run_execute", int(ExitCode.BINDING_IMPORT))
    except Exception as exc:  # noqa: BLE001 - preserve public binding exception detail.
        return binding_exception("scan logs", "classic_scanlog", exc)
    results = list(getattr(result, "logs", result))
    failures = [_scan_failure_summary(item) for item in results if not _scan_result_success(item)]
    report_evidence = [_scan_report_evidence(item) for item in results if _scan_result_success(item)]
    successful_logs = len(results) - len(failures)
    return success(
        "scan logs",
        f"Scanlog binding completed: {successful_logs} succeeded, {len(failures)} failed",
        {
            "scanPath": str(scan_path),
            "yamlRoot": str(yaml_dir_root),
            "yamlData": str(yaml_dir_data),
            "processedLogs": len(results),
            "successfulLogs": successful_logs,
            "failedLogs": len(failures),
            "failures": failures,
            "reportEvidence": report_evidence,
            "result": str(result),
        },
    )


def scan_game(args: _OptionalPathArg, context: CommandContext) -> CommandResult:
    """Run fixture-backed game setup checks through classic_scangame when available."""

    root_path = Path(args.path or context.fixture_root)
    if not root_path.is_absolute():
        root_path = context.repo_root / root_path
    try:
        module = require_binding("classic_scangame")
        results = module.scan_all_ba2_archives(root_path)
    except ImportError as exc:
        return failure("scan game", str(exc), int(ExitCode.BINDING_IMPORT))
    except Exception as exc:  # noqa: BLE001 - preserve public binding exception detail.
        return binding_exception("scan game", "classic_scangame", exc)
    return success("scan game", f"Scanned {len(results)} archive entries", {"rootPath": str(root_path), "findings": [str(item) for item in results]})


def dispatch_scenario_command(command: list[str], context: CommandContext) -> CommandResult:
    """Dispatch catalog scenario commands directly to user-facing handlers."""

    if command[:2] == ["bindings", "list"]:
        return bindings_list(object(), context)
    if command[:2] == ["version", "parse"]:
        return version_parse(_VersionParseCommandArgs(command[2]), context)
    if command[:2] == ["config", "main-version"]:
        return config_main_version(object(), context)
    if command[:2] == ["path", "validate"]:
        return path_validate(_PathCommandArgs(command[2]), context)
    if command[:2] == ["file", "hash"]:
        return file_hash(_PathCommandArgs(command[2]), context)
    if command[:2] == ["scan", "logs"]:
        if "--path" in command:
            path_index = command.index("--path") + 1
            if path_index >= len(command):
                return failure(" ".join(command), "Scenario command is missing a --path value", int(ExitCode.USAGE))
            return scan_logs(_OptionalPathCommandArgs(command[path_index]), context)
        return scan_logs(_OptionalPathCommandArgs(), context)
    return failure(" ".join(command), "Scenario command is not implemented", int(ExitCode.USAGE))
