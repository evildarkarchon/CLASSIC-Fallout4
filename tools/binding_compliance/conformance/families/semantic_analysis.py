"""Typed semantic facts for six executable analysis families.

Pack expectations own exact authored values. These predicates independently
recognize meaningful typed variants; they never read the oracle or runner labels.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from functools import partial
from typing import Any

from ..coverage import CoveragePredicate, FamilyCoveragePolicy


def _object(value: object, fields: tuple[str, ...]) -> bool:
    """Require a complete object shape without extra or omitted optional fields."""
    return isinstance(value, Mapping) and set(value) == set(fields)


def _text(value: object) -> bool:
    """Recognize nonblank semantic text while preserving its exact value centrally."""
    return isinstance(value, str) and bool(value.strip())


def _optional_text(value: object) -> bool:
    """Recognize an explicitly absent or nonblank authored optional field."""
    return value is None or _text(value)


def _success(
    kind: str | None,
    result_matches: Callable[[Any], bool],
    observation: Mapping[str, Any],
) -> bool:
    """Require a successful typed result, separate from the structured error arm."""
    return (
        _object(observation, ("analyzerKind", "result", "error"))
        and observation["analyzerKind"] == kind
        and observation["error"] is None
        and result_matches(observation["result"])
    )


def _error(
    kind: str | None,
    code: str,
    observation: Mapping[str, Any],
    *,
    lookup_context: str | None = None,
) -> bool:
    """Recognize a complete shared error, retaining lookup attribution when present."""
    if not (
        _object(observation, ("analyzerKind", "result", "error"))
        and observation["analyzerKind"] == kind
        and observation["result"] is None
    ):
        return False
    error = observation["error"]
    fields: tuple[str, ...] = ("analyzerKind", "code", "message")
    if kind is None:
        fields += ("formid", "plugin")
    if not (
        _object(error, fields)
        and error["analyzerKind"] == kind
        and error["code"] == code
        and _text(error["message"])
    ):
        return False
    if kind is not None:
        return True
    if lookup_context == "initialization":
        return error["formid"] is None and error["plugin"] is None
    if not (_text(error["formid"]) and _text(error["plugin"])):
        return False
    uninitialized = (
        "no initialized database exposes active game table" in error["message"]
    )
    return uninitialized if lookup_context == "shared-pool" else not uninitialized


def _empty(fields: tuple[str, ...], result: Any) -> bool:
    """Recognize explicit successful empty collections, never missing data."""
    return _object(result, fields) and all(result[field] == [] for field in fields)


def _crash_findings(result: Any) -> bool:
    """Recognize ordered main-error, stack, and DLL findings with typed optionals."""
    if not _object(result, ("findings",)) or not isinstance(result["findings"], list):
        return False
    findings = result["findings"]
    if len(findings) != 3:
        return False
    for finding, kind in zip(
        findings, ("main_error_rule", "stack_rule", "dll_involvement"), strict=True
    ):
        if (
            not _object(finding, ("kind", "ruleId", "name", "severity"))
            or finding["kind"] != kind
        ):
            return False
        if kind == "dll_involvement":
            if any(
                finding[field] is not None for field in ("ruleId", "name", "severity")
            ):
                return False
        elif not (
            _text(finding["ruleId"])
            and _text(finding["name"])
            and type(finding["severity"]) is int
        ):
            return False
    return True


def _crashgen_guidance(result: Any) -> bool:
    """Recognize authored expectation guidance and a distinct disabled-setting notice."""
    if not _object(result, ("expectationOutcomes", "disabledSettingNotices")):
        return False
    outcomes, notices = result["expectationOutcomes"], result["disabledSettingNotices"]
    if not (
        isinstance(outcomes, list)
        and len(outcomes) == 1
        and isinstance(notices, list)
        and len(notices) == 1
    ):
        return False
    outcome = outcomes[0]
    return (
        _object(
            outcome,
            (
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
        )
        and outcome["kind"] == "notice"
        and outcome["severity"] == "warning"
        and outcome["placement"] == "error_information"
        and all(_text(outcome[field]) for field in ("ruleId", "message", "fix"))
        and all(
            outcome[field] is None
            for field in ("section", "setting", "expected", "actual")
        )
        and _object(notices[0], ("settingName",))
        and _text(notices[0]["settingName"])
    )


def _crashgen_check(result: Any, *, successful: bool) -> bool:
    """Recognize nonempty setting targets, values, and authored check outcomes."""
    if not _object(result, ("expectationOutcomes", "disabledSettingNotices")):
        return False
    outcomes = result["expectationOutcomes"]
    if not isinstance(outcomes, list) or len(outcomes) != 1:
        return False
    outcome = outcomes[0]
    if not (
        _object(
            outcome,
            (
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
        )
        and outcome["kind"] == ("success" if successful else "issue")
        and outcome["severity"] == ("info" if successful else "error")
        and outcome["placement"] == "settings"
        and all(
            _text(outcome[field])
            for field in (
                "ruleId",
                "message",
                "section",
                "setting",
                "expected",
                "actual",
            )
        )
    ):
        return False
    if successful:
        notices = result["disabledSettingNotices"]
        return (
            outcome["fix"] is None
            and outcome["expected"] == outcome["actual"]
            and isinstance(notices, list)
            and len(notices) == 1
            and _object(notices[0], ("settingName",))
            and notices[0]["settingName"] == outcome["setting"]
        )
    return (
        _text(outcome["fix"])
        and outcome["expected"] != outcome["actual"]
        and result["disabledSettingNotices"] == []
    )


def _conflict(value: Any, *, remediation: bool) -> bool:
    """Recognize complete authored conflict guidance, including absent remediation."""
    return (
        _object(
            value,
            ("state", "modA", "modB", "nameA", "nameB", "description", "fix", "link"),
        )
        and value["state"] == "matched"
        and all(
            _text(value[field])
            for field in ("modA", "modB", "nameA", "nameB", "description")
        )
        and (
            _text(value["fix"]) and _text(value["link"])
            if remediation
            else value["fix"] is None and value["link"] is None
        )
    )


def _solution(value: Any) -> bool:
    """Recognize authored solution text with ordered matched plugin identities."""
    return (
        _object(value, ("state", "id", "name", "description", "matchedPluginIds"))
        and value["state"] == "matched"
        and all(_text(value[field]) for field in ("id", "name", "description"))
        and isinstance(value["matchedPluginIds"], list)
        and bool(value["matchedPluginIds"])
        and all(_text(item) for item in value["matchedPluginIds"])
    )


def _mod_guidance(result: Any, *, remediation: bool = True) -> bool:
    """Recognize the aggregate authored guidance and its three important-mod states."""
    fields = ("conflicts", "frequentCrashes", "solutions", "importantMods")
    if not (
        _object(result, fields)
        and all(isinstance(result[field], list) for field in fields)
    ):
        return False
    if len(result["conflicts"]) != 1 or not _conflict(
        result["conflicts"][0], remediation=remediation
    ):
        return False
    if not remediation:
        return all(result[field] == [] for field in fields[1:])
    if not all(
        len(result[field]) == 1 and _solution(result[field][0])
        for field in ("frequentCrashes", "solutions")
    ):
        return False
    important = result["importantMods"]
    if len(important) != 3:
        return False
    for item, state in zip(
        important, ("matched", "missing", "gpu_mismatch"), strict=True
    ):
        if not (
            _object(
                item,
                ("state", "detect", "name", "description", "gpu", "gpuMismatchWarning"),
            )
            and item["state"] == state
            and all(_text(item[field]) for field in ("detect", "name", "description"))
            and _optional_text(item["gpu"])
            and _optional_text(item["gpuMismatchWarning"])
        ):
            return False
    return True


def _counted(collection: str, identity: str, result: Any) -> bool:
    """Recognize typed nonempty findings with positive integer occurrence counts."""
    if (
        not _object(result, (collection,))
        or not isinstance(result[collection], list)
        or not result[collection]
    ):
        return False
    return all(
        _object(item, (identity, "occurrences"))
        and _text(item[identity])
        and type(item["occurrences"]) is int
        and item["occurrences"] > 0
        for item in result[collection]
    )


def _lookup_outcome(kind: str, result: Any) -> bool:
    """Keep found, successful missing, and explicitly disabled as separate states."""
    return (
        _object(result, ("kind", "value"))
        and result["kind"] == kind
        and (_text(result["value"]) if kind == "found" else result["value"] is None)
    )


def _lookup_batch(result: Any) -> bool:
    """Recognize positional hit/miss batch outcomes from the public batch operation."""
    return (
        _object(result, ("outcomes",))
        and isinstance(result["outcomes"], list)
        and len(result["outcomes"]) == 2
        and _lookup_outcome("found", result["outcomes"][0])
        and _lookup_outcome("missing", result["outcomes"][1])
    )


_SYMBOLS = {
    "crash-suspect": (
        "CrashSuspectAnalyzer",
        "CrashSuspectAnalysisInput",
        "CrashSuspectAnalysisResult",
        "CrashSuspectFinding",
        "CrashSuspectFindingKind",
    ),
    "crashgen-settings": (
        "CrashgenSettingsAnalyzer",
        "CrashgenSettingsAnalysisInput",
        "CrashgenSettingsAnalysisResult",
        "CrashgenExpectationOutcome",
        "DisabledSettingNotice",
    ),
    "mod-guidance": (
        "ModGuidanceAnalyzer",
        "ModGuidanceAnalysisInput",
        "ModGuidanceAnalysisResult",
        "ModGuidanceMatchState",
        "ModConflictGuidance",
        "ModSolutionGuidance",
        "ImportantModGuidance",
    ),
    "named-record": (
        "NamedRecordFindingAnalyzer",
        "NamedRecordFindingAnalysisInput",
        "NamedRecordFindingAnalysisResult",
        "NamedRecordFinding",
    ),
    "plugin-evidence": (
        "PluginEvidenceAnalyzer",
        "PluginEvidenceAnalysisInput",
        "PluginEvidenceAnalysisResult",
        "PluginEvidence",
    ),
    "formid-lookup": (
        "FormIdValueLookupEntry",
        "FormIdValueLookupInMemoryReply",
        "FormIdValueLookup",
        "FormIdValueLookupOutcome",
        "FormIdValueLookupError",
        "disabled",
        "in_memory",
        "lookup",
        "lookup_batch",
        "shared_pool",
        "sqlite",
    ),
}


def _policy(family: str) -> FamilyCoveragePolicy:
    """Build operation-aware predicates without copying source-row IDs or oracle values."""
    kind = {"named-record": "named_record_finding", "formid-lookup": None}.get(
        family, family.replace("-", "_")
    )
    capability = family + (".lookup" if family == "formid-lookup" else ".analyze")
    entries: list[
        tuple[
            str,
            Callable[[Mapping[str, Any]], bool],
            bool,
            tuple[str | None, ...] | None,
        ]
    ] = []

    def success(
        name: str,
        match: Callable[[Any], bool],
        operations: tuple[str | None, ...] | None = None,
    ) -> None:
        """Register one complete successful semantic result variant."""
        entries.append((name, partial(_success, kind, match), False, operations))

    def failure(
        name: str,
        code: str,
        operations: tuple[str | None, ...] | None = None,
        context: str | None = None,
    ) -> None:
        """Register one typed failure without granting successful analyzer credit."""
        entries.append(
            (
                name,
                partial(_error, kind, code, lookup_context=context),
                True,
                operations,
            )
        )

    if family == "crash-suspect":
        success("findings", _crash_findings)
        success("empty-after-reuse", partial(_empty, ("findings",)))
    elif family == "crashgen-settings":
        success("authored-guidance", _crashgen_guidance)
        success("setting-issue", partial(_crashgen_check, successful=False))
        success("setting-success", partial(_crashgen_check, successful=True))
        success(
            "empty-after-reuse",
            partial(_empty, ("expectationOutcomes", "disabledSettingNotices")),
        )
    elif family == "mod-guidance":
        success("authored-guidance", _mod_guidance)
        success(
            "empty",
            partial(
                _empty, ("conflicts", "frequentCrashes", "solutions", "importantMods")
            ),
        )
        success("absent-remediation", partial(_mod_guidance, remediation=False))
    elif family == "named-record":
        success("counted-findings", partial(_counted, "findings", "record"))
        success("empty-after-reuse", partial(_empty, ("findings",)))
    elif family == "plugin-evidence":
        success("counted-evidence", partial(_counted, "evidence", "plugin"))
        success("empty-after-reuse", partial(_empty, ("evidence",)))
    else:
        success(
            "hit",
            partial(_lookup_outcome, "found"),
            (None, "construction_result", "in_memory", "lookup"),
        )
        success(
            "miss-after-reuse",
            partial(_lookup_outcome, "missing"),
            (None, "construction_result", "in_memory", "lookup"),
        )
        success(
            "disabled",
            partial(_lookup_outcome, "disabled"),
            (None, "construction_result", "disabled", "lookup"),
        )
        success(
            "batch-hit-miss",
            _lookup_batch,
            (None, "construction_result", "in_memory", "lookup_batch"),
        )
        failure(
            "blank-value",
            "malformed_result",
            (None, "construction_result", "in_memory", "lookup"),
        )
        failure(
            "operational-failure",
            "operational_failure",
            (None, "construction_result", "in_memory", "lookup"),
        )
        failure(
            "sqlite-missing",
            "operational_failure",
            (None, "construction_result", "sqlite"),
            "initialization",
        )
        failure(
            "shared-pool-uninitialized",
            "operational_failure",
            (None, "construction_result", "shared_pool", "lookup"),
            "shared-pool",
        )
    if family != "formid-lookup":
        failure(
            "unsupported-version"
            if family == "crashgen-settings"
            else "invalid-configuration",
            "unsupported_configuration_version"
            if family == "crashgen-settings"
            else "invalid_configuration",
        )
    predicates = []
    for name, matches, error, operations in entries:
        if family != "formid-lookup":
            operations = (None, "__init__", "new", "construction_result", "analyze")
        symbols = _SYMBOLS[family]
        if family == "formid-lookup":
            # Runtime operation selectors come from current source declarations,
            # so a class carrier does not imply its sqlite or batch method ran.
            symbols = (
                tuple(
                    symbol for symbol in symbols if symbol != "FormIdValueLookupOutcome"
                )
                if error
                else tuple(
                    symbol for symbol in symbols if symbol != "FormIdValueLookupError"
                )
            )
            # Entry carriers in other Python extensions share these Rust types
            # but require their own factory receipts; exact selectors follow below.
            symbols = tuple(
                symbol
                for symbol in symbols
                if symbol
                not in {"FormIdValueLookupEntry", "FormIdValueLookupInMemoryReply"}
            )
        elif error:
            symbols = ()
        elif name.startswith("empty"):
            symbols = tuple(
                symbol
                for symbol in symbols
                if symbol.endswith(("Analyzer", "AnalysisInput", "AnalysisResult"))
            )
        predicates.append(
            CoveragePredicate(
                id=f"{family}.{name}",
                capability_id=capability,
                action=capability,
                observation_family="structured-error" if error else "semantic-result",
                rust_symbols=symbols,
                matches=matches,
                runtime_operations=operations,
            )
        )
    if family == "formid-lookup":
        for name in ("hit", "batch-hit-miss"):
            source = next(
                predicate
                for predicate in predicates
                if predicate.id == f"formid-lookup.{name}"
            )
            predicates.append(
                CoveragePredicate(
                    id=f"formid-lookup.{name}.entries",
                    capability_id=capability,
                    action=capability,
                    observation_family="semantic-result",
                    rust_symbols=(
                        "FormIdValueLookupEntry",
                        "FormIdValueLookupInMemoryReply",
                    ),
                    matches=source.matches,
                    binding_obligation_ids=(
                        "parity:python:database.formid_value_lookup.FormIdValueLookupEntry",
                        "parity:python:database.formid_value_lookup.FormIdValueLookupEntry.__init__",
                    ),
                    runtime_operations=(None, "__init__"),
                )
            )
    supporting = {
        "crash-suspect": (
            "findings",
            "crash_suspect_analyzer",
            (
                ("CrashSuspectMainErrorRule", "SuspectErrorRule"),
                ("CrashSuspectStackRule", "SuspectStackRule"),
                ("CrashSuspectStackCountRule", "SuspectStackCountRule"),
            ),
        ),
        "mod-guidance": (
            "authored-guidance",
            "mod_guidance_analyzer",
            (
                ("ModGuidanceConflictRule", "ModConflictEntry"),
                ("ModGuidanceImportantModRule", "CoreModEntry"),
                ("ModGuidanceSolutionRule", "ModSolutionEntry"),
                ("ModGuidanceCriteriaKind", "ModSolutionCriteria"),
            ),
        ),
        "crashgen-settings": (
            "authored-guidance",
            "crashgen_settings_analyzer",
            (
                ("AnalyzerSeverity", "RuleSeverity"),
                ("AutoscanReportPlacement", "AutoscanReportPlacement"),
                ("CrashgenExpectationKind", "OutcomeKind"),
            ),
        ),
    }.get(family)
    if supporting is not None:
        scenario_name, module, carriers = supporting
        source = next(
            predicate
            for predicate in predicates
            if predicate.id == f"{family}.{scenario_name}"
        )
        constructors = {
            "CrashSuspectMainErrorRule",
            "CrashSuspectStackRule",
            "CrashSuspectStackCountRule",
            "ModGuidanceConflictRule",
            "ModGuidanceImportantModRule",
            "ModGuidanceSolutionRule",
        }
        # These config-owned wrappers are constructed by the input adapter or
        # projected from actual outcomes, but unrelated config exports are not.
        selectors = tuple(
            f"parity:python:scanlog.{module}.{export}{suffix}"
            for export, _ in carriers
            for suffix in (("", ".__init__") if export in constructors else ("",))
        )
        predicates.append(
            CoveragePredicate(
                id=f"{family}.config-carriers",
                capability_id=f"{family}.config-carriers",
                action=capability,
                observation_family=source.observation_family,
                rust_symbols=tuple(symbol for _, symbol in carriers),
                matches=source.matches,
                binding_obligation_ids=selectors,
                runtime_operations=(
                    None,
                    *(
                        f"{export}.__init__"
                        for export, _ in carriers
                        if export in constructors
                    ),
                ),
            )
        )
    return FamilyCoveragePolicy(family, tuple(predicates))


SEMANTIC_ANALYSIS_COVERAGE_POLICIES: Mapping[str, FamilyCoveragePolicy] = {
    family: _policy(family) for family in _SYMBOLS
}
