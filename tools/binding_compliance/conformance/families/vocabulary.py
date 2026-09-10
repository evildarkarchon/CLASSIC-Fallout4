"""Source-derived Vocabulary inputs and predicates over public label observations.

Only tokens are read from Rust. Independently authored labels stay in the pack,
so changing Rust wording cannot silently regenerate a passing expectation.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from functools import partial
from pathlib import Path
from typing import Any

from ..coverage import CoveragePredicate, FamilyCoveragePolicy

_CONFIG = "business-logic/classic-config-core/src/installed_yaml_data.rs"
_SCAN = "business-logic/classic-scanlog-core/src/scan_run/contract.rs"
_PUBLICATION = "business-logic/classic-durable-publication/src/error.rs"
_UNKNOWN = "not_a_real_token"


@dataclass(frozen=True)
class VocabularyOperation:
    """Public resolver and its Rust owner, with an optional naming twin source."""

    operation: str
    symbol: str
    source: str
    delegate: tuple[str, str] | None = None


VOCABULARY_OPERATIONS = {
    "config-vocabulary": (
        VocabularyOperation(
            "installed_yaml_data_provenance_label",
            "InstalledYamlDataProvenance",
            _CONFIG,
        ),
        VocabularyOperation(
            "scan_run_installed_yaml_data_provenance_label",
            "InstalledYamlDataProvenance",
            _CONFIG,
        ),
        VocabularyOperation(
            "installed_yaml_data_diagnostic_kind_label",
            "InstalledYamlDataDiagnosticKind",
            _CONFIG,
        ),
        VocabularyOperation(
            "local_ignore_yaml_data_state_label", "LocalIgnoreYamlDataState", _CONFIG
        ),
    ),
    "scan-run-vocabulary": (
        VocabularyOperation(
            "scan_run_installed_yaml_data_diagnostic_kind_label",
            "InstalledYamlDataRunDiagnosticKind",
            _SCAN,
            (_CONFIG, "InstalledYamlDataDiagnosticKind"),
        ),
        VocabularyOperation(
            "scan_run_local_ignore_yaml_data_state_label",
            "LocalIgnoreRunState",
            _SCAN,
            (_CONFIG, "LocalIgnoreYamlDataState"),
        ),
        VocabularyOperation("scan_run_log_disposition_label", "LogDisposition", _SCAN),
        VocabularyOperation(
            "scan_run_log_failure_stage_label", "LogFailureStage", _SCAN
        ),
        VocabularyOperation(
            "scan_run_infrastructure_error_stage_label",
            "InfrastructureErrorStage",
            _SCAN,
        ),
        VocabularyOperation(
            "scan_run_local_ignore_reset_failure_stage_label",
            "LocalIgnoreResetFailureStage",
            _SCAN,
            (_PUBLICATION, "PublicationStage"),
        ),
    ),
}


def _body(source: str, pattern: str) -> str:
    """Extract one balanced owner block; unsupported source shapes fail closed."""
    match = re.search(pattern + r"\s*\{", source)
    if match is None:
        raise ValueError("Vocabulary source block was not found: " + pattern)
    start = match.end()
    depth = 1
    for index in range(start, len(source)):
        depth += (source[index] == "{") - (source[index] == "}")
        if depth == 0:
            return source[start:index]
    raise ValueError("Vocabulary source block is unbalanced")


def _source_tokens(root: Path, spec: VocabularyOperation) -> dict[str, str]:
    """Read literal owner tokens, following the three reviewed naming twins.

    Variant declarations, rather than VARIANTS acknowledgements, are the
    denominator. New or unrecognized arms cannot disappear from transport cases.
    """
    source = (root / spec.source).read_text(encoding="utf-8")
    source = re.sub(r"/\*.*?\*/|//[^\n]*", "", source, flags=re.DOTALL)
    enum = _body(source, rf"pub enum {spec.symbol}")
    variants = re.findall(r"\b([A-Z]\w*)\s*(?:,|$)", enum)
    implementation = _body(source, rf"impl Vocabulary for {spec.symbol}")
    token_body = _body(implementation, r"fn as_str\(self\)\s*->\s*&'static str")
    tokens = dict(re.findall(r'Self::(\w+)\s*=>\s*"([^"\\]+)"', token_body))
    if spec.delegate:
        path, symbol = spec.delegate
        delegated = _source_tokens(
            root, VocabularyOperation(spec.operation, symbol, path)
        )
        # Twin conformance at the Rust owner proves the delegation itself. Here
        # we expand only known counterpart variants and the twin's literal arms.
        tokens = {
            **{key: value for key, value in delegated.items() if key in variants},
            **tokens,
        }
        unpaired = set(variants) - tokens.keys()
        fallback = re.search(r"None\s*=>\s*([A-Z_]+)", token_body)
        if len(unpaired) == 1 and fallback:
            constant = re.search(
                rf'const {fallback[1]}:\s*&str\s*=\s*"([^"\\]+)"', source
            )
            if constant:
                tokens[next(iter(unpaired))] = constant[1]
    if (
        not variants
        or set(tokens) != set(variants)
        or len(tokens.values()) != len(set(tokens.values()))
    ):
        raise ValueError(
            f"Vocabulary {spec.symbol} variants lack complete unique source tokens"
        )
    return {variant: tokens[variant] for variant in variants}


def validate_vocabulary_pack(
    document: Mapping[str, Any], root: Path
) -> tuple[Path, ...]:
    """Require source-complete inputs while keeping authored wording independent."""
    specs = VOCABULARY_OPERATIONS[document["familyId"]]
    scenarios = document["scenarios"]
    by_operation = {
        scenario["input"].get("operation"): scenario for scenario in scenarios
    }
    if len(by_operation) != len(scenarios) or set(by_operation) != {
        spec.operation for spec in specs
    }:
        raise ValueError(
            "Vocabulary pack must exercise every public resolver exactly once"
        )
    sources: set[Path] = set()
    for spec in specs:
        tokens = list(_source_tokens(root, spec).values())
        scenario = by_operation[spec.operation]
        wanted = tokens + [_UNKNOWN]
        if scenario["input"] != {"operation": spec.operation, "tokens": wanted}:
            raise ValueError(
                f"Vocabulary {spec.symbol} input differs from source-derived tokens"
            )
        if not _observed(spec.operation, tuple(tokens), scenario["expected"]):
            raise ValueError(
                f"Vocabulary {spec.symbol} oracle lacks complete labels and unknown behavior"
            )
        sources.add(root / spec.source)
        if spec.delegate:
            sources.add(root / spec.delegate[0])
    return tuple(sorted(sources))


def _observed(
    operation: str, tokens: tuple[str, ...], observation: Mapping[str, Any]
) -> bool:
    """Require each actual label and the rejected unknown input, in source order."""
    if (
        set(observation) != {"operation", "entries"}
        or observation["operation"] != operation
    ):
        return False
    entries = observation["entries"]
    if not isinstance(entries, list) or len(entries) != len(tokens) + 1:
        return False
    for token, entry in zip((*tokens, _UNKNOWN), entries, strict=True):
        if not isinstance(entry, Mapping) or set(entry) != {
            "token",
            "label",
            "rejected",
        }:
            return False
        if entry["token"] != token:
            return False
        if token == _UNKNOWN:
            if entry["label"] is not None or entry["rejected"] is not True:
                return False
        elif (
            not isinstance(entry["label"], str)
            or not entry["label"]
            or entry["rejected"] is not False
        ):
            return False
    return True


def vocabulary_coverage_policies(root: Path) -> dict[str, FamilyCoveragePolicy]:
    """Bind central predicates to current Rust tokens, never adapter token lists."""
    return {
        family: FamilyCoveragePolicy(
            family,
            tuple(
                CoveragePredicate(
                    id=spec.operation.replace("_", "-"),
                    capability_id="vocabulary.resolve",
                    action="vocabulary.resolve",
                    observation_family="vocabulary",
                    rust_symbols=(spec.symbol,),
                    matches=partial(
                        _observed,
                        spec.operation,
                        tuple(_source_tokens(root, spec).values()),
                    ),
                    runtime_operations=(None, spec.operation),
                )
                for spec in specs
            ),
        )
        for family, specs in VOCABULARY_OPERATIONS.items()
    }
