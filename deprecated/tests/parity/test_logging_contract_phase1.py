"""Phase-1 logging contract parity and redaction tests."""

from __future__ import annotations

import json
import subprocess
import sys
import textwrap
from pathlib import Path
from unittest.mock import patch

import pytest

from ClassicLib.integration import factory
from ClassicLib.integration.exceptions import RustBindingImportError
from ClassicLib.integration.factory_internal.logging_contract import (
    EVENT_STARTUP_ACCELERATION_STATUS,
    EVENT_STARTUP_BINDING_CONTRACT_FAILED,
    EVENT_STARTUP_BINDING_CONTRACT_VALIDATED,
)
from ClassicLib.messaging.core.enums import MessageType
from ClassicLib.support.setup import SetupCoordinator


def _load_contract() -> dict[str, object]:
    path = Path("docs/implementation/logging_contract_phase1.json")
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.mark.unit
def test_contract_file_defines_phase1_required_fields() -> None:
    contract = _load_contract()
    assert contract["version"] == "phase1-v1"
    assert contract["required_fields"] == ["event", "severity", "component", "outcome"]
    assert "canonical_events" in contract


@pytest.mark.unit
def test_python_message_type_mapping_matches_contract() -> None:
    contract = _load_contract()
    expected = {
        "Info": "info",
        "Success": "info",
        "Warning": "warning",
        "Error": "error",
        "Critical": "error",
        "Debug": "debug",
        "Progress": "debug",
    }
    assert contract["severity_map"] == expected

    mapped = {
        MessageType.INFO.to_rust().name(): "info",
        MessageType.SUCCESS.to_rust().name(): "info",
        MessageType.WARNING.to_rust().name(): "warning",
        MessageType.ERROR.to_rust().name(): "error",
        MessageType.CRITICAL.to_rust().name(): "error",
        MessageType.DEBUG.to_rust().name(): "debug",
        MessageType.PROGRESS.to_rust().name(): "debug",
    }
    assert mapped == expected


@pytest.mark.unit
def test_rust_contract_formatter_required_fields_and_event_taxonomy() -> None:
    import classic_message

    contract = _load_contract()
    canonical = contract["canonical_events"]
    assert isinstance(canonical, dict)

    formatted = classic_message.format_contract_event(
        "integration.startup",
        canonical["startup_binding_contract_validated"],
        "info",
        "success",
        {"contract": "startup_all", "checked_bindings": "29"},
    )

    assert f"event={canonical['startup_binding_contract_validated']}" in formatted
    assert "severity=info" in formatted
    assert "component=integration.startup" in formatted
    assert "outcome=success" in formatted
    assert "contract=startup_all" in formatted
    assert "checked_bindings=29" in formatted


@pytest.mark.unit
def test_rust_contract_formatter_redacts_secret_and_path_values() -> None:
    import classic_message

    formatted = classic_message.format_contract_event(
        "integration.startup",
        EVENT_STARTUP_BINDING_CONTRACT_FAILED,
        "error",
        "failure",
        {
            "api_key": "secret-value",
            "install_path": r"C:\Users\alice\Documents\My Games\Fallout4",
        },
    )

    assert "api_key=[REDACTED]" in formatted
    assert "install_path=<path-redacted>" in formatted


@pytest.mark.unit
def test_factory_validate_rust_modules_success_emits_contract_event() -> None:
    with (
        patch("ClassicLib.integration.factory._validate_rust_modules"),
        patch("ClassicLib.integration.factory._get_binding_contract", return_value=[("classic_yaml", "YamlOperations")]),
        patch("ClassicLib.integration.factory.logger") as mock_logger,
    ):
        factory.validate_rust_modules("startup_all")
        message = mock_logger.info.call_args.args[0]

    assert f"event={EVENT_STARTUP_BINDING_CONTRACT_VALIDATED}" in message
    assert "severity=info" in message
    assert "outcome=success" in message
    assert "contract=startup_all" in message


@pytest.mark.unit
def test_factory_validate_rust_modules_failure_emits_contract_event() -> None:
    with (
        patch(
            "ClassicLib.integration.factory._validate_rust_modules",
            side_effect=RustBindingImportError("classic_yaml.YamlOperations", "No module named 'classic_yaml'"),
        ),
        patch("ClassicLib.integration.factory.logger") as mock_logger,
    ):
        with pytest.raises(RustBindingImportError):
            factory.validate_rust_modules("startup_all")
        message = mock_logger.error.call_args.args[0]

    assert f"event={EVENT_STARTUP_BINDING_CONTRACT_FAILED}" in message
    assert "severity=error" in message
    assert "outcome=failure" in message
    assert "missing_binding=classic_yaml.YamlOperations" in message
    assert "failure_type=import" in message


@pytest.mark.unit
def test_setup_helpers_emit_contract_events() -> None:
    status = {
        "active_count": 5,
        "total_count": 5,
        "percentage": 100.0,
        "acceleration_level": "MANDATORY",
        "performance_gains": {},
    }

    with (
        patch("ClassicLib.support.setup.logger") as mock_logger,
        patch.object(SetupCoordinator, "_display_status_message"),
    ):
        SetupCoordinator._log_active_acceleration(status, debug_enabled=True, is_gui=False)
        SetupCoordinator._log_binding_failure(RuntimeError("binding failed"), debug_enabled=True, is_gui=False)

    info_messages = [call.args[0] for call in mock_logger.info.call_args_list]
    error_messages = [call.args[0] for call in mock_logger.error.call_args_list]

    assert any(f"event={EVENT_STARTUP_ACCELERATION_STATUS}" in message for message in info_messages)
    assert any(f"event={EVENT_STARTUP_BINDING_CONTRACT_FAILED}" in message for message in error_messages)


def _run_missing_classic_message_script(script_body: str) -> subprocess.CompletedProcess[str]:
    """Run a Python snippet with classic_message import forcibly unavailable."""
    prelude = textwrap.dedent(
        """
        import builtins
        import importlib

        real_import = builtins.__import__

        def fake_import(name, globals=None, locals=None, fromlist=(), level=0):
            if name == "classic_message":
                raise ModuleNotFoundError("No module named classic_message")
            return real_import(name, globals, locals, fromlist, level)

        builtins.__import__ = fake_import
        """
    )
    full_script = f"{prelude}\n{textwrap.dedent(script_body)}"
    return subprocess.run(
        [sys.executable, "-c", full_script],
        capture_output=True,
        text=True,
        check=False,
    )


@pytest.mark.unit
def test_classiclib_package_import_is_lazy_for_classic_message() -> None:
    result = _run_missing_classic_message_script(
        """
        import ClassicLib
        print("imported", ClassicLib.__name__)
        """
    )
    assert result.returncode == 0, result.stderr
    assert "imported ClassicLib" in result.stdout


@pytest.mark.unit
def test_logging_contract_fallback_reachable_when_classic_message_missing() -> None:
    result = _run_missing_classic_message_script(
        """
        from ClassicLib.integration.factory_internal.logging_contract import format_contract_event

        print(
            format_contract_event(
                component="integration.startup",
                event="evt",
                severity="info",
                outcome="ok",
                context={"contract": "startup_all"},
            )
        )
        """
    )
    assert result.returncode == 0, result.stderr
    assert "event=evt" in result.stdout
    assert "contract=startup_all" in result.stdout


@pytest.mark.unit
@pytest.mark.parametrize("module_name", ["CLASSIC_Interface", "CLASSIC_ScanLogs", "ClassicLib.TUI"])
def test_entrypoints_raise_typed_binding_error_when_classic_message_missing(module_name: str) -> None:
    result = _run_missing_classic_message_script(
        f"""
        try:
            importlib.import_module("{module_name}")
        except Exception as exc:
            print(type(exc).__name__)
            print(str(exc))
            raise SystemExit(0 if type(exc).__name__ == "RustBindingImportError" else 2)
        raise SystemExit(3)
        """
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "RustBindingImportError" in result.stdout
    assert "rebuild_rust.ps1" in result.stdout
