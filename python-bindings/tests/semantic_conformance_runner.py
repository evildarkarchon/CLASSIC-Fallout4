"""Execute input-only semantic conformance plans through public PyO3 handles."""

from __future__ import annotations

import asyncio
import json
import os
import re
import sys
import uuid
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any

FAMILIES = {
    "settings-load",
    "settings-yaml",
    "settings-validation",
    "settings-cached-docs",
    "version-registry-details",
    "xse-operations",
    "installation-paths",
    "game-identity",
    "runtime-access",
    "file-fingerprint",
    "performance",
    "performance-timers",
    "message-logging",
    "update-rejection",
    "update-decisions",
    "update-services",
    "string-operations",
    "registry-operations",
    "registry-game",
    "registry-gui",
    "registry-context",
    "registry-keys",
    "game-version-parse",
    "game-version-distance",
    "game-version-order",
    "fallout4-identity",
    "fallout4-paths",
    "fallout4-metadata",
    "version-registry-values",
    "registry-paths",
    "web-operations",
    "resource-operations",
    "version-operations",
    "version-extraction",
    "version-f4se",
    "version-pe",
    "version-pe-path",
    "crash-suspect",
    "crashgen-settings",
    "mod-guidance",
    "formid-lookup",
    "named-record",
    "plugin-evidence",
    "installed-yaml-data",
    "config-vocabulary",
    "scan-run-vocabulary",
    "config-operations",
    "yaml-source-values",
    "xse-plugin-validation",
    "path-backups",
    "game-integrity",
    "game-orchestration",
    "game-setup-intake",
    "file-operations",
    "file-generation",
    "mod-ini",
    "wrye-report",
    "log-collection",
    "crash-pattern",
    "formid-finding",
    "ba2-scan",
    "unpacked-scan",
    "crashgen-check",
    "path-operations",
    "path-normalization",
    "message-operations",
    "database-operations",
    "version-registry",
    "scan-game",
    "dds-header",
    "yaml-file-values",
    "shared-performance",
    "log-parsing",
    "papyrus-monitor",
}


class RunnerContractError(RuntimeError):
    """Identify invalid infrastructure separately from typed domain failures."""


def _mapping(value: object, label: str) -> Mapping[str, Any]:
    """Require a JSON object and retain its location in any failure."""
    if not isinstance(value, Mapping):
        raise RunnerContractError(f"{label} must be an object")
    return value


def _string(value: object, label: str) -> str:
    """Require a nonempty identity without coercing malformed input."""
    if not isinstance(value, str) or not value:
        raise RunnerContractError(f"{label} must be a non-empty string")
    return value


def _array(value: object, label: str) -> list[Any]:
    """Require a JSON array while excluding mapping and string values."""
    if not isinstance(value, list):
        raise RunnerContractError(f"{label} must be an array")
    return value


def _load_plan(path: Path) -> Mapping[str, Any]:
    """Read the input-only plan and validate participant and invocation identities."""
    plan = _mapping(json.loads(path.read_text(encoding="utf-8")), "run plan")
    if plan.get("schemaVersion") != 1 or plan.get("familyId") not in FAMILIES:
        raise RunnerContractError("unsupported semantic family or schema")
    if type(plan.get("familyVersion")) is not int or plan["familyVersion"] < 1:
        raise RunnerContractError("invalid familyVersion")
    _string(plan.get("expectationDigest"), "expectationDigest")
    _mapping(plan.get("fixtures"), "fixtures")
    if plan.get("participant") != {
        "id": "python",
        "role": "semantic-adapter",
        "executionInstanceId": "python",
    }:
        raise RunnerContractError("not a Python semantic-adapter invocation")
    invocation = _mapping(plan.get("invocation"), "invocation")
    for key in ("id", "sourceIdentity", "runPlanDigest"):
        _string(invocation.get(key), f"invocation.{key}")
    scenarios = _array(plan.get("scenarios"), "scenarios")
    if not scenarios:
        raise RunnerContractError("plan must contain scenarios")
    for raw in scenarios:
        scenario = _mapping(raw, "scenario")
        if "expected" in scenario:
            raise RunnerContractError("input-only plan contains expectations")
        _string(scenario.get("id"), "scenario.id")
        for key in ("capabilityIds", "fixtureRefs"):
            for item in _array(scenario.get(key), key):
                _string(item, key)
        actions = (
            {"installed-yaml-data.inspect", "installed-yaml-data.load"}
            if plan["familyId"] == "installed-yaml-data"
            else (
                {
                    "formid-lookup.lookup",
                }
                if plan["familyId"] == "formid-lookup"
                else {f"{plan['familyId']}.analyze"}
            )
        )
        if plan["familyId"] in {"config-vocabulary", "scan-run-vocabulary"}:
            actions = {"vocabulary.resolve"}
        actions = {
            "config-operations": {
                "config-operations.clear-cache",
                "config-operations.load-explicit",
                "config-operations.main-version",
                "config-operations.persist-local",
            },
            "yaml-source-values": {"yaml-source-values.matrix"},
            "xse-plugin-validation": {"xse-plugin-validation.check"},
            "path-backups": {"path-backups.versioned"},
            "game-integrity": {"game-integrity.basic", "game-integrity.options"},
            "game-orchestration": {"game-orchestration.composed"},
            "game-setup-intake": {
                "game-setup-intake.run",
                "game-setup-intake.normalize",
            },
            "file-operations": {
                "file-operations.read-text",
                "file-operations.write-text",
            },
            "path-operations": {"path-operations.validate"},
            "path-normalization": {"path-normalization.resolve"},
            "file-fingerprint": {"file-fingerprint.inspect"},
            "settings-load": {"settings-load.execute"},
            "settings-yaml": {"settings-yaml.execute"},
            "settings-validation": {"settings-validation.observe"},
            "settings-cached-docs": {"settings-cached-docs.observe"},
            "version-registry-details": {"version-registry-details.execute"},
            "xse-operations": {"xse-operations.inspect"},
            "installation-paths": {"installation-paths.inspect"},
            "game-identity": {
                "game-identity.observe",
                "game-identity.metadata",
                "game-identity.details",
            },
            "runtime-access": {"runtime-access.observe"},
            "update-rejection": {
                "update-rejection.latest",
                "update-rejection.all",
                "update-rejection.notification",
                "update-rejection.metadata",
            },
            "performance": {"performance.metrics"},
            "performance-timers": {"performance-timers.observe"},
            "message-logging": {
                "message-logging.basic",
                "message-logging.extended",
                "message-logging.format",
            },
            "update-decisions": {"update-decisions.compare"},
            "update-services": {"update-services.notification"},
            "string-operations": {"string-operations.execute"},
            "registry-operations": {"registry-operations.execute"},
            "registry-game": {"registry-game.observe"},
            "registry-gui": {"registry-gui.observe"},
            "registry-context": {"registry-context.observe"},
            "registry-keys": {"registry-keys.observe"},
            "version-registry-values": {"version-registry-values.execute"},
            "game-version-parse": {"game-version-parse.observe"},
            "game-version-distance": {"game-version-distance.observe"},
            "game-version-order": {"game-version-order.observe"},
            "fallout4-identity": {"fallout4-identity.observe"},
            "fallout4-paths": {"fallout4-paths.observe"},
            "fallout4-metadata": {"fallout4-metadata.observe"},
            "registry-paths": {"registry-paths.observe"},
            "web-operations": {"web-operations.observe"},
            "resource-operations": {"resource-operations.observe"},
            "version-operations": {"version-operations.observe"},
            "version-extraction": {"version-extraction.observe"},
            "version-f4se": {"version-f4se.observe"},
            "version-pe": {"version-pe.observe"},
            "version-pe-path": {"version-pe-path.observe"},
            "message-operations": {"message-operations.format"},
            "database-operations": {
                "database-operations.pool",
                "database-operations.cache-defaults",
            },
            "version-registry": {
                "version-registry.query",
                "version-registry.enumerate",
                "version-registry.crashgen",
                "version-registry.xse",
            },
            "scan-game": {
                "scan-game.validate-ini",
                "scan-game.validate-enb",
                "scan-game.process-logs",
                "scan-game.assemble-reports",
            },
            "dds-header": {"dds-header.parse", "dds-header.files"},
            "yaml-file-values": {"yaml-file-values.observe"},
            "shared-performance": {"shared-performance.observe"},
            "log-parsing": {
                "log-parsing.patterns",
                "log-parsing.parser",
                "log-parsing.formids",
                "log-parsing.plugins",
                "log-parsing.records",
                "log-parsing.gpu",
                "log-parsing.crashgen-version",
            },
            "papyrus-monitor": {"papyrus-monitor.observe"},
            "file-generation": {"file-generation.generate"},
            "mod-ini": {"mod-ini.cache", "mod-ini.scan", "mod-ini.duplicates"},
            "wrye-report": {"wrye-report.format"},
            "log-collection": {"log-collection.collect"},
            "crash-pattern": {"crash-pattern.classify", "crash-pattern.vr"},
            "formid-finding": {"formid-finding.analyze", "formid-finding.sqlite"},
            "ba2-scan": {"ba2-scan.full"},
            "unpacked-scan": {"unpacked-scan.scan"},
            "crashgen-check": {"crashgen-check.check"},
        }.get(plan["familyId"], actions)
        if scenario.get("action") not in actions:
            raise RunnerContractError("unsupported semantic action")
        _mapping(scenario.get("input"), "scenario.input")
    return plan


def _snake(name: str) -> str:
    """Translate field spelling only; domain values remain unchanged."""
    return re.sub(r"(?<!^)(?=[A-Z])", "_", name).lower()


def _fields(value: Any, names: tuple[str, ...]) -> dict[str, Any]:
    """Read the complete declared public fields and unwrap typed enum values."""
    output = {}
    for name in names:
        item = getattr(value, _snake(name))
        output[name] = getattr(item, "value", item)
    return output


def _solution_rule(api: Any, rule: Mapping[str, Any]) -> Any:
    """Construct the typed criteria enum at the public binding boundary."""
    kinds = {
        "any": api.ModGuidanceCriteriaKind.Any,
        "all": api.ModGuidanceCriteriaKind.All,
    }
    return api.ModGuidanceSolutionRule(
        rule["id"],
        kinds[rule["criteriaKind"]],
        rule["criteria"],
        rule["exceptions"],
        rule["name"],
        rule["description"],
    )


def _create_analyzer(
        api: Any, family: str, config: Mapping[str, Any]
) -> tuple[Any, Callable[[Mapping[str, Any]], Any]]:
    """Construct real public analyzers and convert only their input carrier shapes."""
    if family == "crash-suspect":
        main = [
            api.CrashSuspectMainErrorRule(
                rule["id"], rule["name"], rule["severity"], rule["mainErrorContainsAny"]
            )
            for rule in config["mainErrorRules"]
        ]
        stack = [
            api.CrashSuspectStackRule(
                rule["id"],
                rule["name"],
                rule["severity"],
                rule["mainErrorRequiredAny"],
                rule["mainErrorOptionalAny"],
                rule["stackContainsAny"],
                rule["excludeIfStackContainsAny"],
                [
                    api.CrashSuspectStackCountRule(item["substring"], item["count"])
                    for item in rule["stackContainsAtLeast"]
                ],
            )
            for rule in config["stackRules"]
        ]
        return api.CrashSuspectAnalyzer(
            main, stack
        ), lambda request: api.CrashSuspectAnalysisInput(
            request["mainError"], request["callStack"]
        )
    if family == "crashgen-settings":

        def convert(request: Mapping[str, Any]) -> Any:
            """Represent central version facts as the Python API's owned tuple."""
            version = request.get("crashgenVersion")
            if isinstance(version, Mapping):
                version = tuple(version[key] for key in ("major", "minor", "patch"))
            elif version is not None:
                version = tuple(version)
            return api.CrashgenSettingsAnalysisInput(
                request["settings"],
                set(request["installedPlugins"]),
                version,
                request["configLayout"],
            )

        return api.CrashgenSettingsAnalyzer(
            config["crashgenName"], config["entry"]
        ), convert
    if family == "mod-guidance":
        conflicts = [
            api.ModGuidanceConflictRule(
                rule["modA"],
                rule["modB"],
                rule["nameA"],
                rule["nameB"],
                rule["description"],
                rule.get("fix"),
                rule.get("link"),
            )
            for rule in config["conflicts"]
        ]
        important = [
            api.ModGuidanceImportantModRule(
                rule["detect"],
                rule["name"],
                rule["description"],
                rule.get("gpu"),
                rule.get("gpuMismatchWarning"),
                rule.get("excludeWhenPluginAny", rule.get("exclude")),
            )
            for rule in config["importantMods"]
        ]
        return api.ModGuidanceAnalyzer(
            conflicts,
            [_solution_rule(api, rule) for rule in config["frequentCrashes"]],
            [_solution_rule(api, rule) for rule in config["solutions"]],
            important,
        ), lambda request: api.ModGuidanceAnalysisInput(
            {plugin["name"]: plugin["id"] for plugin in request["plugins"]},
            request.get("userGpu"),
            set(request["xseModules"]),
        )
    if family == "named-record":
        return api.NamedRecordFindingAnalyzer(
            config["targetRecords"], config["ignoreRecords"]
        ), lambda request: api.NamedRecordFindingAnalysisInput(request["crashLines"])
    if family == "plugin-evidence":
        return api.PluginEvidenceAnalyzer(
            config["ignoredPlugins"]
        ), lambda request: api.PluginEvidenceAnalysisInput(
            request["crashLines"], request["plugins"]
        )
    raise RunnerContractError("unsupported analyzer family")


def _project(family: str, result: Any) -> dict[str, Any]:
    """Serialize full typed domain observations without report text or oracle values."""
    schemas = {
        "crash-suspect": {"findings": ("kind", "ruleId", "name", "severity")},
        "crashgen-settings": {
            "expectationOutcomes": (
                "ruleId",
                "kind",
                "severity",
                "message",
                "fix",
                "placement",
                "section",
                "setting",
                "expected",
                "actual",
            ),
            "disabledSettingNotices": ("settingName",),
        },
        "mod-guidance": {
            "conflicts": (
                "state",
                "modA",
                "modB",
                "nameA",
                "nameB",
                "description",
                "fix",
                "link",
            ),
            "frequentCrashes": (
                "state",
                "id",
                "name",
                "description",
                "matchedPluginIds",
            ),
            "solutions": ("state", "id", "name", "description", "matchedPluginIds"),
            "importantMods": (
                "state",
                "detect",
                "name",
                "description",
                "gpu",
                "gpuMismatchWarning",
            ),
        },
        "named-record": {"findings": ("record", "occurrences")},
        "plugin-evidence": {"evidence": ("plugin", "occurrences")},
    }
    return {
        collection: [
            _fields(item, names) for item in getattr(result, _snake(collection))
        ]
        for collection, names in schemas[family].items()
    }


async def _lookup(fixture: Mapping[str, Any]) -> dict[str, Any]:
    """Preserve strict found, missing, disabled, and attributed failure outcomes."""
    import classic_database

    config = _mapping(fixture["configuration"], "configuration")
    request = _mapping(fixture["request"], "request")
    try:
        if config["mode"] == "disabled":
            lookup = classic_database.FormIdValueLookup.disabled()
        elif config["mode"] == "in-memory":
            lookup = classic_database.FormIdValueLookup.in_memory(
                [
                    classic_database.FormIdValueLookupEntry(
                        entry["formid"],
                        entry["plugin"],
                        value=entry.get("value"),
                        operational_failure=entry.get("operationalFailure"),
                    )
                    for entry in config["entries"]
                ]
            )
        elif config["mode"] == "sqlite-missing":
            lookup = await classic_database.FormIdValueLookup.sqlite(
                config["databasePath"], config["gameTable"]
            )
        elif config["mode"] == "shared-pool":
            lookup = classic_database.FormIdValueLookup.from_shared_pool(
                classic_database.DatabasePool(game_table=config["gameTable"])
            )
        else:
            raise RunnerContractError("unsupported lookup mode")
        if config["mode"] == "sqlite-missing":
            return {
                "analyzerKind": None,
                "result": {"constructed": True},
                "error": None,
            }
        if fixture.get("warmupRequest") is not None:
            warmup = fixture["warmupRequest"]
            await lookup.lookup(warmup["formid"], warmup["plugin"])
        if "pairs" in request:
            results = await lookup.lookup_batch(
                [(pair["formid"], pair["plugin"]) for pair in request["pairs"]]
            )
            return {
                "analyzerKind": None,
                "result": {
                    "outcomes": [
                        {"kind": result.kind, "value": result.value}
                        for result in results
                    ]
                },
                "error": None,
            }
        result = await lookup.lookup(request["formid"], request["plugin"])
        return {
            "analyzerKind": None,
            "result": {"kind": result.kind, "value": result.value},
            "error": None,
        }
    except classic_database.FormIdValueLookupError as error:
        return {
            "analyzerKind": None,
            "result": None,
            "error": {
                "analyzerKind": None,
                "code": error.code,
                "message": error.message,
                "formid": error.formid,
                "plugin": error.plugin,
            },
        }


def _execute_scenario(
        plan: Mapping[str, Any], scenario: Mapping[str, Any]
) -> dict[str, Any]:
    """Read only a declared fixture and invoke its real public operation."""
    if plan["familyId"] in {"config-vocabulary", "scan-run-vocabulary"}:
        from vocabulary_conformance import observe_vocabulary

        return observe_vocabulary(plan["familyId"], scenario["input"])
    reference = _string(scenario["input"].get("fixtureRef"), "fixtureRef")
    if reference not in scenario["fixtureRefs"]:
        raise RunnerContractError("fixtureRef is not declared by scenario")
    source = Path(_string(plan["fixtures"].get(reference), "fixture path"))
    fixture = _mapping(json.loads(source.read_text(encoding="utf-8")), "fixture")
    if "expected" in fixture:
        raise RunnerContractError("input fixture contains expectations")
    if plan["familyId"] == "installed-yaml-data":
        from installed_yaml_conformance import observe_installed_yaml

        if scenario["action"] != f"installed-yaml-data.{fixture['operation']}":
            raise RunnerContractError(
                "installed-data action disagrees with fixture operation"
            )
        return observe_installed_yaml(fixture)
    if plan["familyId"] == "database-operations":
        from database_operations_conformance import observe_database_operations

        return observe_database_operations(fixture)
    if plan["familyId"] in {
        "version-registry",
        "version-registry-details",
        "version-registry-values",
    }:
        from version_registry_conformance import observe_version_registry

        return observe_version_registry(fixture)
    if plan["familyId"] == "scan-game":
        from scan_game_conformance import observe_scan_game

        return observe_scan_game(fixture)
    if plan["familyId"] == "yaml-file-values":
        from yaml_file_values_conformance import observe_yaml_file_values

        return observe_yaml_file_values(fixture)
    if plan["familyId"] == "shared-performance":
        from shared_performance_conformance import observe_shared_performance

        return observe_shared_performance(fixture)
    if plan["familyId"] == "dds-header":
        from dds_header_conformance import observe_dds_header

        return observe_dds_header(fixture)
    if plan["familyId"] == "log-parsing":
        from log_parsing_conformance import observe_log_parsing

        return observe_log_parsing(fixture)
    if plan["familyId"] == "file-generation":
        from file_generation_conformance import observe_file_generation

        return observe_file_generation(fixture)
    if plan["familyId"] == "mod-ini":
        from mod_ini_conformance import observe_mod_ini

        return observe_mod_ini(fixture)
    if plan["familyId"] == "wrye-report":
        from wrye_report_conformance import observe_wrye_report

        return observe_wrye_report(fixture)
    if plan["familyId"] == "log-collection":
        from log_collection_conformance import observe_log_collection

        return observe_log_collection(fixture)
    if plan["familyId"] == "crash-pattern":
        from crash_pattern_conformance import observe_crash_pattern

        return observe_crash_pattern(fixture)
    if plan["familyId"] == "formid-finding":
        from formid_finding_conformance import observe_formid_finding

        return observe_formid_finding(fixture)
    if plan["familyId"] == "ba2-scan":
        from ba2_scan_conformance import observe_ba2_scan

        return observe_ba2_scan(fixture)
    if plan["familyId"] == "unpacked-scan":
        from unpacked_scan_conformance import observe_unpacked_scan

        return observe_unpacked_scan(fixture)
    if plan["familyId"] == "crashgen-check":
        from crashgen_check_conformance import observe_crashgen_check

        return observe_crashgen_check(fixture)
    if plan["familyId"] == "papyrus-monitor":
        from papyrus_monitor_conformance import observe_papyrus_monitor

        return observe_papyrus_monitor(fixture)
    if plan["familyId"] == "file-fingerprint":
        from file_fingerprint_conformance import observe_file_fingerprint

        return observe_file_fingerprint(fixture)
    if plan["familyId"] in {
        "registry-paths",
        "registry-context",
        "registry-gui",
        "registry-game",
    }:
        from registry_accessors_conformance import observe_registry_accessors

        return observe_registry_accessors(plan["familyId"], fixture)
    if plan["familyId"] in {
        "fallout4-paths",
        "game-version-parse",
        "fallout4-identity",
        "fallout4-metadata",
        "game-version-distance",
        "game-version-order",
    }:
        from version_values_conformance import observe_version_values

        return observe_version_values(plan["familyId"], fixture)
    if plan["familyId"] == "registry-keys":
        from registry_keys_conformance import observe_registry_keys

        return observe_registry_keys(fixture)
    if plan["familyId"] in {"settings-validation", "settings-cached-docs"}:
        from settings_extended_conformance import observe_settings_extended

        return observe_settings_extended(plan["familyId"], fixture)
    if plan["familyId"] in {"settings-load", "settings-yaml"}:
        from settings_load_conformance import observe_settings_load

        return observe_settings_load(fixture)
    if plan["familyId"] == "installation-paths":
        from installation_paths_conformance import observe_installation_paths

        return observe_installation_paths(fixture)
    if plan["familyId"] == "xse-operations":
        from xse_operations_conformance import observe_xse_operations

        return observe_xse_operations(fixture)
    if plan["familyId"] in {"game-identity", "runtime-access"}:
        from shared_identity_conformance import observe_shared_identity

        return observe_shared_identity(plan["familyId"], fixture)
    if plan["familyId"] == "performance":
        from performance_conformance import observe_performance

        return observe_performance(fixture)
    if plan["familyId"] == "performance-timers":
        from performance_conformance import observe_timers

        return observe_timers(fixture)
    if plan["familyId"] == "update-rejection":
        from update_rejection_conformance import observe_update_rejection

        return observe_update_rejection(fixture)
    if plan["familyId"] == "message-logging":
        from message_logging_conformance import observe_message_logging

        return observe_message_logging(fixture)
    if plan["familyId"] == "update-services":
        from update_services_conformance import observe_update_services

        return observe_update_services(fixture, scenario["id"])
    if plan["familyId"] == "update-decisions":
        from update_decisions_conformance import observe_update_decisions

        return observe_update_decisions(fixture)
    if plan["familyId"] in {"string-operations", "registry-operations"}:
        from shared_registry_conformance import observe_shared_registry

        return observe_shared_registry(plan["familyId"], fixture)
    if plan["familyId"] in {
        "web-operations",
        "resource-operations",
        "version-operations",
        "version-extraction",
        "version-f4se",
        "version-pe",
        "version-pe-path",
    }:
        from aux_operations_conformance import observe_aux_operations

        return observe_aux_operations(plan["familyId"], fixture)
    if plan["familyId"] == "config-operations":
        from config_operations_conformance import observe_config_operations

        return observe_config_operations(fixture)
    if plan["familyId"] == "yaml-source-values":
        from yaml_source_values_conformance import observe_yaml_sources

        return observe_yaml_sources(fixture)
    if plan["familyId"] == "xse-plugin-validation":
        from xse_plugin_validation_conformance import observe_xse_plugins

        return observe_xse_plugins(fixture)
    if plan["familyId"] == "path-backups":
        from path_backups_conformance import observe_path_backups

        return observe_path_backups(fixture)
    if plan["familyId"] == "game-integrity":
        from game_integrity_conformance import observe_integrity

        return observe_integrity(fixture)
    if plan["familyId"] == "game-orchestration":
        from game_orchestration_conformance import observe_orchestration

        return observe_orchestration(fixture)
    if plan["familyId"] == "game-setup-intake":
        from game_setup_intake_conformance import observe_setup

        return observe_setup(fixture)
    if plan["familyId"] == "file-operations":
        from file_operations_conformance import observe_file_operations

        if scenario["action"] != f"file-operations.{fixture['operation']}":
            raise RunnerContractError("file action disagrees with fixture operation")
        return observe_file_operations(fixture)
    if plan["familyId"] in {
        "path-operations",
        "path-normalization",
        "message-operations",
    }:
        from path_message_conformance import observe_path_message

        return observe_path_message(plan["familyId"], fixture)
    if plan["familyId"] == "formid-lookup":
        return asyncio.run(_lookup(fixture))
    import classic_scanlog

    try:
        analyzer, convert = _create_analyzer(
            classic_scanlog,
            plan["familyId"],
            _mapping(fixture["configuration"], "configuration"),
        )
        if fixture.get("warmupRequest") is not None:
            analyzer.analyze(convert(fixture["warmupRequest"]))
        result = analyzer.analyze(convert(_mapping(fixture["request"], "request")))
        return {
            "analyzerKind": analyzer.kind.code,
            "result": _project(plan["familyId"], result),
            "error": None,
        }
    except classic_scanlog.AnalyzerError as error:
        return {
            "analyzerKind": error.analyzer_kind.code,
            "result": None,
            "error": {
                "analyzerKind": error.analyzer_kind.code,
                "code": error.code,
                "message": error.message,
            },
        }


def _scenario_receipt(
        plan: Mapping[str, Any], scenario: Mapping[str, Any]
) -> dict[str, Any]:
    """Keep adapter defects distinct from successfully observed domain errors."""
    receipt = {
        "id": scenario["id"],
        "capabilityIds": scenario["capabilityIds"],
        "executionStatus": "completed",
        "observation": {},
        "failure": None,
    }
    try:
        receipt["observation"] = _execute_scenario(plan, scenario)
    except Exception as error:  # noqa: BLE001 - every attempted case owes a fresh receipt.
        receipt["executionStatus"] = "failed"
        receipt["failure"] = {
            "kind": "python-runner-error",
            "message": f"{type(error).__name__}: {error}",
        }
    return receipt


def _build_receipt(plan: Mapping[str, Any]) -> dict[str, Any]:
    """Retain central identities verbatim and append independent observations."""
    return {
        **{
            key: plan[key]
            for key in (
                "schemaVersion",
                "familyId",
                "familyVersion",
                "expectationDigest",
                "invocation",
                "participant",
            )
        },
        "runner": {
            "id": "classic-python-semantic-conformance",
            "version": 1,
            "platform": {"win32": "windows", "darwin": "macos"}.get(
                sys.platform, "linux"
            ),
            "toolchain": sys.implementation.name,
        },
        "scenarios": [
            _scenario_receipt(plan, scenario) for scenario in plan["scenarios"]
        ],
    }


def _publish_receipt(path: Path, receipt: Mapping[str, Any]) -> None:
    """Publish canonical JSON atomically while refusing stale receipt destinations."""
    if path.exists():
        raise RunnerContractError("conformance receipt destination already exists")
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.parent / f".{path.name}.{uuid.uuid4().hex}.tmp"
    try:
        with temporary.open("xb") as output:
            output.write(
                json.dumps(
                    receipt, ensure_ascii=False, sort_keys=True, separators=(",", ":")
                ).encode("utf-8")
            )
            output.flush()
            os.fsync(output.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def main() -> int:
    """Use environment-only invocation paths and fail explicitly on infrastructure errors."""
    try:
        plan_path = Path(
            _string(
                os.environ.get("CLASSIC_CONFORMANCE_RUN_PLAN"),
                "CLASSIC_CONFORMANCE_RUN_PLAN",
            )
        ).resolve(strict=True)
        output_path = Path(
            _string(
                os.environ.get("CLASSIC_CONFORMANCE_OUTPUT"),
                "CLASSIC_CONFORMANCE_OUTPUT",
            )
        ).resolve()
        if plan_path.parent != output_path.parent:
            raise RunnerContractError("receipt must be a sibling of its run plan")
        _publish_receipt(output_path, _build_receipt(_load_plan(plan_path)))
    except (OSError, ValueError, RunnerContractError) as error:
        print(f"classic-python-semantic-conformance: {error}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
