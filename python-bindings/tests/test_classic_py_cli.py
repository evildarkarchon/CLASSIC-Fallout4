"""Process and unit coverage for the CLASSIC Python binding CLI."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import types
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]
CLI_SRC = REPO_ROOT / "python-bindings" / "classic-py-cli" / "src"


def _install_user_settings_fake(
    monkeypatch: pytest.MonkeyPatch,
    *,
    fcx_mode: bool = False,
) -> None:
    """Install a typed User Settings projection for scan CLI tests."""

    scan = types.SimpleNamespace(
        fcx_mode=fcx_mode,
        simplify_logs=True,
        formid_value_lookup=True,
        formid_databases={"Fallout4": ["formids.db"]},
        unsolved_logs_destination="Unsolved Logs",
        game_version_selection="1.10.984",
        max_concurrent_scans=3,
    )
    setup = types.SimpleNamespace(
        managed_game="Fallout4",
        game_root="game-root",
        documents_root="documents-root",
        game_executable="Fallout4.exe",
    )
    module = types.ModuleType("classic_user_settings")
    module.open_user_settings = lambda _root: types.SimpleNamespace(
        crash_log_scan_settings=scan,
        game_setup_settings=setup,
    )
    monkeypatch.setitem(sys.modules, "classic_user_settings", module)


def _install_final_scan_run_fake(
    fake: types.ModuleType,
    make_logs: object,
    *,
    status: str = "completed",
    message: str | None = None,
) -> None:
    """Attach a selectable final request/execution result to a fake scanlog module."""

    class ScanRunConfiguration:
        def __init__(self, **values: object) -> None:
            self.values = values

    class ScanRunTargetedSource:
        def __init__(self, *, inputs: list[str]) -> None:
            self.inputs = inputs

    class ScanRunRequest:
        @staticmethod
        def targeted(configuration: object, source: object) -> object:
            return types.SimpleNamespace(
                intent="targeted",
                configuration=configuration,
                source=source,
            )

    class ScanRunCancellation:
        pass

    def scan_run_execute(
        request: object,
        cancellation: object,
        observer: object | None = None,
        cancel_on_observer_error: bool = False,
    ) -> object:
        assert getattr(request, "intent") == "targeted"
        assert isinstance(cancellation, ScanRunCancellation)
        assert callable(make_logs)
        logs = make_logs(request.configuration.values, request.source.inputs)
        succeeded = sum(item.disposition == "succeeded" for item in logs)
        cancelled = sum(item.disposition == "cancelled_before_start" for item in logs)
        result = types.SimpleNamespace(
            status=status,
            message=message,
            effective_concurrency=1,
            total=len(logs),
            succeeded=succeeded,
            failed=len(logs) - succeeded - cancelled,
            cancelled=cancelled,
            logs=logs,
        )
        return types.SimpleNamespace(result=result, error=None, observer_error=None)

    fake.ScanRunConfiguration = ScanRunConfiguration
    fake.ScanRunTargetedSource = ScanRunTargetedSource
    fake.ScanRunRequest = ScanRunRequest
    fake.ScanRunCancellation = ScanRunCancellation
    fake.scan_run_execute = scan_run_execute


def _env() -> dict[str, str]:
    """Return an environment that can import the local CLI package."""

    env = os.environ.copy()
    env["PYTHONPATH"] = str(CLI_SRC) + os.pathsep + env.get("PYTHONPATH", "")
    return env


def _run_module(*args: str) -> subprocess.CompletedProcess[str]:
    """Run the module entry point as a subprocess."""

    return subprocess.run([sys.executable, "-m", "classic_py_cli", *args], cwd=REPO_ROOT, env=_env(), check=False, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)


def test_console_script_help() -> None:
    """The installed console script exposes the maintained command groups."""

    script = shutil.which("classic-py")
    if script is None:
        pytest.skip("classic-py console script is installed by uv sync")
    completed = subprocess.run([script, "--help"], cwd=REPO_ROOT, check=False, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    assert completed.returncode == 0
    assert "bindings" in completed.stdout
    assert "compliance" in completed.stdout


def test_module_help() -> None:
    """The module entry point uses the same application parser."""

    completed = _run_module("--help")
    assert completed.returncode == 0
    assert "bindings" in completed.stdout
    assert "compliance" in completed.stdout


def test_json_stdout_is_parseable_for_bindings_list() -> None:
    """JSON mode writes one parseable envelope to stdout and keeps stderr clean."""

    completed = _run_module("--json", "bindings", "list")
    assert completed.returncode == 0
    payload = json.loads(completed.stdout)
    assert payload["schemaVersion"] == "1.0"
    assert payload["command"] == "bindings list"
    assert completed.stderr == ""


def test_json_invalid_command_returns_failure_envelope() -> None:
    """JSON mode maps argparse failures to a structured envelope on stdout."""

    completed = _run_module("--json", "no-such-command")
    assert completed.returncode == 2
    payload = json.loads(completed.stdout)
    assert payload["schemaVersion"] == "1.0"
    assert payload["success"] is False
    assert payload["exitCode"] == 2
    assert payload["command"] == "usage"
    assert payload["error"]["classification"] == "parse-error"
    assert "no-such-command" in payload["error"]["message"]
    assert completed.stderr == ""


def test_json_invalid_command_accepts_global_flag_after_subcommand() -> None:
    """Global --json after an invalid token still produces JSON output."""

    completed = _run_module("no-such-command", "--json")
    assert completed.returncode == 2
    payload = json.loads(completed.stdout)
    assert payload["success"] is False
    assert payload["exitCode"] == 2
    assert payload["error"]["classification"] == "parse-error"
    assert completed.stderr == ""


def test_invalid_global_path_returns_configuration_exit_status(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    """Invalid global path options map to exit status 2 with a JSON failure envelope."""

    sys.path.insert(0, str(CLI_SRC))
    from classic_py_cli import app as app_module

    def _raise_on_resolve(_args: object) -> None:
        raise OSError(22, "Invalid argument", "Z:\\definitely\\missing\\repo")

    monkeypatch.setattr(app_module, "resolve_context", _raise_on_resolve)
    code = app_module.main(["--json", "--repo-root", "Z:\\definitely\\missing\\repo", "bindings", "list"])
    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert code == 2
    assert payload["success"] is False
    assert payload["exitCode"] == 2
    assert payload["error"]["type"] == "OSError"


def test_missing_binding_simulation_returns_import_status(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    """A required missing binding maps to exit status 3 and structured JSON."""

    sys.path.insert(0, str(CLI_SRC))
    from classic_py_cli.app import main
    from classic_py_cli import binding_loader

    monkeypatch.setattr(binding_loader, "EXPECTED_BINDINGS", ["classic_missing_test"])
    code = main(["--json", "bindings", "smoke"])
    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert code == 3
    assert payload["error"]["message"] == "1 binding modules failed to import"
    assert payload["data"]["missing"][0]["module"] == "classic_missing_test"


def test_fake_version_binding_command(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    """Representative utility commands route through public binding modules."""

    sys.path.insert(0, str(CLI_SRC))
    from classic_py_cli.app import main

    fake = types.ModuleType("classic_version")
    fake.__version__ = "test"
    fake.parse_version = lambda value: (1, 2, 3)
    fake.format_version = lambda version: "v" + ".".join(str(part) for part in version)
    monkeypatch.setitem(sys.modules, "classic_version", fake)

    code = main(["--json", "version", "parse", "1.2.3.0"])
    payload = json.loads(capsys.readouterr().out)
    assert code == 0
    assert payload["data"]["parsed"] == [1, 2, 3]
    assert payload["data"]["formatted"] == "v1.2.3"


def test_update_validate_url_returns_product_failure_for_invalid_url(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    """Invalid update URLs are validation findings, not successful commands."""

    sys.path.insert(0, str(CLI_SRC))
    from classic_py_cli.app import main

    fake = types.ModuleType("classic_web")
    fake.__version__ = "test"
    fake.is_valid_url = lambda url: False
    monkeypatch.setitem(sys.modules, "classic_web", fake)

    code = main(["--json", "update", "validate-url", "not-a-url"])
    payload = json.loads(capsys.readouterr().out)

    assert code == 1
    assert payload["success"] is False
    assert payload["exitCode"] == 1
    assert payload["data"] == {"url": "not-a-url", "valid": False}


def test_scan_logs_reports_fail_soft_result_counts(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """Per-log scan failures are visible in JSON without failing the completed batch."""

    sys.path.insert(0, str(CLI_SRC))
    from classic_py_cli.app import main

    scan_dir = tmp_path / "logs"
    scan_dir.mkdir()
    (scan_dir / "good.log").write_text("good log\n", encoding="utf-8")
    (scan_dir / "bad.log").write_text("bad log\n", encoding="utf-8")

    fake = types.ModuleType("classic_scanlog")
    fake.__version__ = "test"

    def make_logs(
        configuration: dict[str, object],
        paths: list[str],
    ) -> list[types.SimpleNamespace]:
        assert configuration["yaml_dir_root"] == str(REPO_ROOT)
        assert configuration["yaml_dir_data"] == str(REPO_ROOT / "CLASSIC Data")
        assert paths == [str(scan_dir)]
        return [
            types.SimpleNamespace(
                crash_log=path,
                disposition=(
                    "failed" if Path(path).name == "bad.log" else "succeeded"
                ),
                message="malformed log" if Path(path).name == "bad.log" else None,
                failures=[],
                autoscan_report=None,
            )
            for path in (str(scan_dir / "good.log"), str(scan_dir / "bad.log"))
        ]

    _install_final_scan_run_fake(fake, make_logs)
    monkeypatch.setitem(sys.modules, "classic_scanlog", fake)
    _install_user_settings_fake(monkeypatch)

    code = main(["--json", "scan", "logs", "--path", str(scan_dir)])
    payload = json.loads(capsys.readouterr().out)

    assert code == 0
    assert payload["success"] is True
    assert payload["data"]["processedLogs"] == 2
    assert payload["data"]["successfulLogs"] == 1
    assert payload["data"]["failedLogs"] == 1
    assert payload["data"]["failures"] == [{"logPath": str(scan_dir / "bad.log"), "error": "malformed log"}]


@pytest.mark.parametrize(
    ("status", "expected_exit_code"),
    [
        ("setup_failed", 1),
        ("cancelled_before_discovery", 4),
        ("cancelled", 4),
    ],
)
def test_scan_logs_reports_unsuccessful_terminal_statuses(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    status: str,
    expected_exit_code: int,
) -> None:
    """Terminal setup and cancellation outcomes must not render as successful scans."""

    sys.path.insert(0, str(CLI_SRC))
    from classic_py_cli.app import main

    fake = types.ModuleType("classic_scanlog")
    fake.__version__ = "test"
    _install_final_scan_run_fake(
        fake,
        lambda _configuration, _paths: [],
        status=status,
        message=f"terminal {status}",
    )
    monkeypatch.setitem(sys.modules, "classic_scanlog", fake)
    _install_user_settings_fake(monkeypatch)

    code = main(["--json", "scan", "logs", "--path", str(tmp_path)])
    payload = json.loads(capsys.readouterr().out)

    assert code == expected_exit_code
    assert payload["success"] is False
    assert payload["exitCode"] == expected_exit_code
    assert payload["error"] == {
        "classification": "scan-run-terminal",
        "status": status,
        "message": f"terminal {status}",
    }


def test_scan_logs_consumes_final_result_and_event_contract(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The binding-local CLI constructs a Targeted request and reads final events/results."""

    sys.path.insert(0, str(CLI_SRC))
    from classic_py_cli.app import main

    crash_log = tmp_path / "crash-final.log"
    crash_log.write_text("crash log\n", encoding="utf-8")
    observed: dict[str, object] = {}
    fake = types.ModuleType("classic_scanlog")
    fake.__version__ = "test"

    class ScanRunConfiguration:
        def __init__(self, **values: object) -> None:
            observed["configuration"] = values

    class ScanRunTargetedSource:
        def __init__(self, *, inputs: list[str]) -> None:
            self.inputs = inputs

    class ScanRunRequest:
        @staticmethod
        def targeted(
            configuration: ScanRunConfiguration,
            source: ScanRunTargetedSource,
        ) -> object:
            observed["targetedInputs"] = source.inputs
            return types.SimpleNamespace(intent="targeted")

        @staticmethod
        def targeted_with_fcx(
            configuration: ScanRunConfiguration,
            source: ScanRunTargetedSource,
            setup_context: object,
        ) -> object:
            observed["targetedInputs"] = source.inputs
            observed["setupContext"] = setup_context
            return types.SimpleNamespace(intent="targeted")

    class ScanRunSetupContext:
        def __init__(self, **values: object) -> None:
            self.values = values

    class ScanRunCancellation:
        pass

    def scan_run_execute(
        request: object,
        cancellation: ScanRunCancellation,
        observer: object | None = None,
        cancel_on_observer_error: bool = False,
    ) -> object:
        assert getattr(request, "intent") == "targeted"
        assert isinstance(cancellation, ScanRunCancellation)
        assert cancel_on_observer_error is True
        assert callable(observer)
        observer(
            types.SimpleNamespace(
                kind="discovery_completed",
                discovery=types.SimpleNamespace(
                    source="targeted",
                    accepted_logs=[str(crash_log)],
                    rejected_inputs=[
                        types.SimpleNamespace(
                            path="ignored.txt",
                            reason="not a Crash Log",
                        )
                    ],
                    searched_locations=[str(tmp_path)],
                ),
            )
        )
        observer(
            types.SimpleNamespace(
                kind="effective_concurrency_selected",
                effective_concurrency=1,
            )
        )
        result = types.SimpleNamespace(
            status="completed",
            effective_concurrency=1,
            total=1,
            succeeded=1,
            failed=0,
            cancelled=0,
            logs=[
                types.SimpleNamespace(
                    discovery_index=0,
                    crash_log=str(crash_log),
                    autoscan_report=None,
                    disposition="succeeded",
                    failures=[],
                    message=None,
                )
            ],
        )
        return types.SimpleNamespace(
            result=result,
            error=None,
            observer_error=None,
        )

    fake.ScanRunConfiguration = ScanRunConfiguration
    fake.ScanRunTargetedSource = ScanRunTargetedSource
    fake.ScanRunRequest = ScanRunRequest
    fake.ScanRunSetupContext = ScanRunSetupContext
    fake.ScanRunCancellation = ScanRunCancellation
    fake.scan_run_execute = scan_run_execute
    monkeypatch.setitem(sys.modules, "classic_scanlog", fake)
    _install_user_settings_fake(monkeypatch, fcx_mode=True)

    code = main(["--json", "scan", "logs", "--path", str(crash_log)])
    payload = json.loads(capsys.readouterr().out)

    assert code == 0
    assert observed["targetedInputs"] == [str(crash_log)]
    assert observed["configuration"] == {
        "yaml_dir_root": str(REPO_ROOT),
        "yaml_dir_data": str(REPO_ROOT / "CLASSIC Data"),
        "game": "Fallout4",
        "game_version": "1.10.984",
        "show_formid_values": True,
        "simplify_logs": True,
        "formid_database_paths": ["formids.db"],
        "unsolved_logs_destination": "Unsolved Logs",
        "max_concurrent": 3,
    }
    assert observed["setupContext"].values == {
        "game_root": "game-root",
        "docs_root": "documents-root",
        "game_exe_path": "Fallout4.exe",
    }
    assert payload["data"]["status"] == "completed"
    assert payload["data"]["effectiveConcurrency"] == 1
    assert payload["data"]["events"] == [
        {
            "kind": "discovery_completed",
            "discovery": {
                "source": "targeted",
                "acceptedLogs": [str(crash_log)],
                "rejectedInputs": [
                    {"path": "ignored.txt", "reason": "not a Crash Log"}
                ],
                "searchedLocations": [str(tmp_path)],
            },
        },
        {
            "kind": "effective_concurrency_selected",
            "effectiveConcurrency": 1,
        }
    ]


def test_catalog_validation() -> None:
    """Every scenario carries the metadata required by reports and listing."""

    sys.path.insert(0, str(CLI_SRC))
    from classic_py_cli.scenarios import validate_catalog

    assert validate_catalog() == []


def test_smoke_report_generation_with_fake_bindings(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """Smoke compliance writes JSON and Markdown reports from shared report data."""

    sys.path.insert(0, str(CLI_SRC))
    from classic_py_cli.app import main

    scan_fixture = REPO_ROOT / "python-bindings" / "tests" / "fixtures" / "scanlogs" / "addictol-newer-than-floor.log"
    assert scan_fixture.exists()

    fake_version = types.ModuleType("classic_version")
    fake_version.__version__ = "test"
    fake_version.parse_version = lambda value: (1, 10, 163)
    fake_version.format_version = lambda version: "v1.10.163"
    fake_config = types.ModuleType("classic_config")
    fake_config.__version__ = "test"
    fake_config.load_main_yaml_version = lambda path: "9.1.0"
    fake_path = types.ModuleType("classic_path")
    fake_path.__version__ = "test"
    fake_path.PathValidator = type("PathValidator", (), {"is_valid_path": staticmethod(lambda path: True)})
    fake_file = types.ModuleType("classic_file_io")
    fake_file.__version__ = "test"
    fake_file.FileHasher = type("FileHasher", (), {"hash_file": staticmethod(lambda path: "a" * 64)})
    fake_scanlog = types.ModuleType("classic_scanlog")
    fake_scanlog.__version__ = "test"
    fixture_root = REPO_ROOT / "python-bindings" / "tests" / "fixtures"

    def make_logs(
        configuration: dict[str, object],
        paths: list[str],
    ) -> list[types.SimpleNamespace]:
        assert configuration["yaml_dir_root"] == str(fixture_root)
        assert configuration["yaml_dir_data"] == str(fixture_root / "CLASSIC Data")
        assert paths == [str(scan_fixture)]
        assert "Addictol v1.3.1" in scan_fixture.read_text(encoding="utf-8")
        report_path = tmp_path / "addictol-AUTOSCAN.md"
        report_path.write_text("*You have a valid version of Addictol!*\n", encoding="utf-8")
        return [
            types.SimpleNamespace(
                crash_log=str(scan_fixture),
                disposition="succeeded",
                message=None,
                failures=[],
                autoscan_report=str(report_path),
            )
        ]

    _install_final_scan_run_fake(fake_scanlog, make_logs)
    for name, module in {
        "classic_version": fake_version,
        "classic_config": fake_config,
        "classic_path": fake_path,
        "classic_file_io": fake_file,
        "classic_scanlog": fake_scanlog,
    }.items():
        monkeypatch.setitem(sys.modules, name, module)

    code = main(["--json", "--output", str(tmp_path), "compliance", "run", "--profile", "smoke"])
    payload = json.loads(capsys.readouterr().out)
    scenario_results = payload["data"]["report"]["scenarioResults"]
    scanlog_result = next(item for item in scenario_results if item["id"] == "scanlog-addictol-newer-than-floor")

    assert code == 0
    assert (tmp_path / "classic_python_cli_report.json").exists()
    assert (tmp_path / "classic_python_cli_report.md").exists()
    assert payload["data"]["report"]["profile"] == "smoke"
    assert scanlog_result["commandLine"] == [
        "classic-py",
        "scan",
        "logs",
        "--path",
        "python-bindings/tests/fixtures/scanlogs/addictol-newer-than-floor.log",
    ]
    assert scanlog_result["data"]["processedLogs"] == 1
    assert scanlog_result["data"]["reportEvidence"] == [
        {
            "logPath": str(scan_fixture),
            "validVersionLine": "*You have a valid version of Addictol!*",
            "outdatedWarningPresent": False,
        }
    ]


def test_smoke_scanlog_contract_rejects_outdated_warning(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """The Addictol smoke scenario fails if fixture evidence reports an outdated warning."""

    sys.path.insert(0, str(CLI_SRC))
    from classic_py_cli.app import main
    from classic_py_cli.scenarios import Scenario

    scan_fixture = REPO_ROOT / "python-bindings" / "tests" / "fixtures" / "scanlogs" / "addictol-newer-than-floor.log"
    report_path = tmp_path / "addictol-AUTOSCAN.md"
    report_path.write_text("*** WARNING: YOUR Addictol IS OUTDATED! PLEASE UPDATE TO A VALID VERSION!***\n", encoding="utf-8")
    fake_scanlog = types.ModuleType("classic_scanlog")

    def make_logs(
        configuration: dict[str, object],
        paths: list[str],
    ) -> list[types.SimpleNamespace]:
        return [
            types.SimpleNamespace(
                crash_log=str(scan_fixture),
                disposition="succeeded",
                message=None,
                failures=[],
                autoscan_report=str(report_path),
            )
        ]

    _install_final_scan_run_fake(fake_scanlog, make_logs)
    monkeypatch.setitem(sys.modules, "classic_scanlog", fake_scanlog)
    scenario = Scenario(
        "scanlog-addictol-newer-than-floor",
        "Scan an Addictol crash log newer than the configured floor and prove it remains valid.",
        "classic_scanlog",
            [
                "ScanRunRequest.targeted",
                "ScanRunCancellation",
                "scan_run_execute",
                "ScanRunLogResult.autoscan_report",
            ],
        ["scan", "logs", "--path", "python-bindings/tests/fixtures/scanlogs/addictol-newer-than-floor.log"],
        ["python-bindings/tests/fixtures/scanlogs/addictol-newer-than-floor.log"],
        0,
        ["contract-test"],
        ["missing-runtime-coverage", "true-binding-compliance-gap"],
    )
    monkeypatch.setattr(
        "classic_py_cli.commands.scenarios_for_profile",
        lambda profile: [scenario] if profile == "contract-test" else [],
    )

    code = main(["--json", "--output", str(tmp_path), "compliance", "run", "--profile", "contract-test"])
    payload = json.loads(capsys.readouterr().out)
    scanlog_result = payload["data"]["report"]["scenarioResults"][0]

    assert code == 1
    assert scanlog_result["status"] == "failed"
    assert scanlog_result["exitCode"] == 0
    assert scanlog_result["contractFailure"] == "Addictol scanlog scenario produced an outdated-version warning"
    assert "validVersionLine" not in scanlog_result["data"]["reportEvidence"][0]


def test_compliance_run_fails_when_scenario_expectation_missed(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """Compliance run fails when a handler exits 0 but the scenario expected a nonzero exit."""

    sys.path.insert(0, str(CLI_SRC))
    from classic_py_cli.app import main
    from classic_py_cli.scenarios import Scenario

    mismatched = Scenario(
        "expect-failure",
        "Expect a failure that did not occur.",
        "classic_py_cli",
        ["bindings.list"],
        ["bindings", "list"],
        [],
        1,
        ["mismatch-test"],
        ["true-binding-compliance-gap"],
    )
    monkeypatch.setattr(
        "classic_py_cli.commands.scenarios_for_profile",
        lambda profile: [mismatched] if profile == "mismatch-test" else [],
    )

    code = main(["--json", "--output", str(tmp_path), "compliance", "run", "--profile", "mismatch-test"])
    payload = json.loads(capsys.readouterr().out)
    scenario_results = payload["data"]["report"]["scenarioResults"]

    assert code != 0
    assert payload["success"] is False
    assert len(scenario_results) == 1
    assert scenario_results[0]["status"] == "failed"
    assert scenario_results[0]["exitCode"] == 0
    assert scenario_results[0]["expectedExitCode"] == 1


def test_product_stubs_and_scan_commands_are_registered() -> None:
    """Representative product command groups are available from help output."""

    completed = _run_module("scan", "--help")
    assert completed.returncode == 0
    assert "logs" in completed.stdout
    assert "game" in completed.stdout
