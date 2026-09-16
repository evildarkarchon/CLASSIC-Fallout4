"""Transport central vocabulary inputs through public binding label resolvers."""

from __future__ import annotations

import importlib
from collections.abc import Mapping
from typing import Any

OPERATIONS = {
    "config-vocabulary": (
        "classic_config",
        {
            "installed_yaml_data_provenance_label",
            "scan_run_installed_yaml_data_provenance_label",
            "installed_yaml_data_diagnostic_kind_label",
            "local_ignore_yaml_data_state_label",
        },
    ),
    "scan-run-vocabulary": (
        "classic_scanlog",
        {
            "scan_run_installed_yaml_data_diagnostic_kind_label",
            "scan_run_local_ignore_yaml_data_state_label",
            "scan_run_log_disposition_label",
            "scan_run_log_failure_stage_label",
            "scan_run_infrastructure_error_stage_label",
            "scan_run_local_ignore_reset_failure_stage_label",
        },
    ),
}


def observe_vocabulary(family: str, request: Mapping[str, Any]) -> dict[str, Any]:
    """Preserve ordered public results and observe invalid tokens via native ValueError."""
    operation = request.get("operation")
    if family not in OPERATIONS:
        raise ValueError("unsupported vocabulary family")
    module, allowed = OPERATIONS[family]
    if not isinstance(operation, str) or operation not in allowed:
        raise ValueError("unsupported vocabulary operation for family")
    tokens = request.get("tokens")
    if not isinstance(tokens, list) or any(
            not isinstance(token, str) or not token for token in tokens
    ):
        raise ValueError("vocabulary tokens must be non-empty strings")
    # Python shares the config resolver for provenance carried by scan-run observations.
    public_operation = (
        "installed_yaml_data_provenance_label"
        if operation == "scan_run_installed_yaml_data_provenance_label"
        else operation
    )
    resolve = getattr(importlib.import_module(module), public_operation)
    entries = []
    for token in tokens:
        try:
            label = resolve(token)
        except ValueError:
            # Only public token rejection counts as domain evidence; adapter errors propagate.
            entries.append({"token": token, "label": None, "rejected": True})
        else:
            entries.append({"token": token, "label": label, "rejected": False})
    return {"operation": operation, "entries": entries}
