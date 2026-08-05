#!/usr/bin/env python3
"""Resolve each Node export to the core Rust symbol its NAPI wrapper actually uses.

The Tier-1 contract pairs a ``nodeExport`` with a ``rustSymbol``, but the gate
only ever checked that the named Rust symbol *exists somewhere* in the parsed
surface -- not that it has anything to do with the export. That let placeholder
rows accumulate: at one point 82 unrelated exports all claimed the Rust module
``path_core`` as their counterpart, and the gate still reported 913/913 matched.

This module derives the real counterpart from the binding source instead of
trusting the contract. For each ``#[napi]`` item in
``node-bindings/classic-node/src/*.rs`` it reads the wrapper body and collects
the core-crate symbols it references, via:

* crate-qualified paths -- ``classic_resource_core::detect_resource_type(...)``
* names brought in by ``use classic_*_core::{...}`` at the top of the file
* ``impl From<CoreType> for JsWrapper`` conversions, which is how the DTO
  structs name the core type they mirror

Candidates are then ranked, strongest evidence first, and cross-checked against
the parsed Rust surface so a resolution can never invent a symbol that does not
exist. Anything that stays ambiguous is reported rather than guessed -- a wrong
mapping is exactly the failure mode this is meant to end.
"""

from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

sys.path.append(str(Path(__file__).resolve().parents[1]))

from parity_rust_surface import parse_rust_surface

NODE_SRC_REL = "node-bindings/classic-node/src"

#: ``classic_foo_core::Bar`` / ``classic_shared_core::Baz``
#:
#: Intermediate module segments are consumed so the FINAL identifier is
#: captured: ``classic_version_core::pe_version::is_valid_executable_path``
#: must yield ``is_valid_executable_path``, not the module ``pe_version``.
_QUALIFIED_RE = re.compile(
    r"\b(classic_[a-z0-9_]+?_core)::(?:[a-z0-9_]+::)*([A-Za-z0-9_]+)"
)
#: ``use classic_foo_core::{A, B as C};`` (single or braced)
_USE_RE = re.compile(r"(?m)^\s*use\s+(classic_[a-z0-9_]+?_core)::([^;]+);")
#: ``impl From<CoreType> for JsWrapper``
_FROM_IMPL_RE = re.compile(
    r"impl\s+From\s*<\s*([A-Za-z0-9_:]+)\s*>\s*for\s+([A-Za-z0-9_]+)"
)

#: A conversion helper, which pairs a core type with the DTO that mirrors it:
#:
#:     fn result_to_js(result: CrashSuspectAnalysisResult) -> JsCrashSuspectAnalysisResult
#:
#: ``#[napi(object)]`` DTOs hold only plain JS-compatible fields, so they never
#: name their core counterpart directly. The converter is the only place the
#: correspondence is written down.
_CONVERSION_FN_RE = re.compile(
    r"(?m)^(?:pub(?:\([^)]*\))?\s+)?fn\s+[A-Za-z0-9_]+\s*\(\s*"
    r"[A-Za-z0-9_]+\s*:\s*&?(?:mut\s+)?([A-Za-z][A-Za-z0-9_]*)"
    r"[^)]*\)\s*->\s*(Js[A-Za-z0-9_]+)"
)
#: A ``#[napi...]`` attribute followed by the item it decorates.
#:
#: ``between`` absorbs any attributes sitting between the two -- DTO structs are
#: routinely written as ``#[napi(object)]`` + ``#[derive(Clone)]`` + ``pub
#: struct``, and requiring them to be adjacent silently skipped every such
#: wrapper (``JsGithubAsset``, ``JsGithubRelease``, ``JsUpdateCheckResult`` ...).
#: ``between`` also absorbs comments, not just attributes. Real declarations
#: carry trailing rationale on the intervening attribute line:
#:
#:     #[napi]
#:     #[allow(deprecated)] // compat wrapper over GithubClient (design D-08).
#:     pub async fn check_for_updates(...)
#:
#: Requiring pure whitespace after the attribute skipped those entirely.
_NAPI_ITEM_RE = re.compile(
    r"#\[napi(?P<args>\((?:[^()]|\([^()]*\))*\))?\]"
    r"(?P<between>(?:\s*(?:#\[[^\]]*\]|//[^\n]*))*)\s*"
    r"(?:pub(?:\([^)]*\))?\s+)?(?:async\s+)?(?P<kind>fn|struct|enum|impl)\s+"
    r"(?P<name>[A-Za-z0-9_]+)"
)

#: ``js_name = "foo"`` overrides the auto-generated camelCase export name.
_JS_NAME_RE = re.compile(r'js_name\s*=\s*"([A-Za-z0-9_]+)"')

#: A file-local (non-``#[napi]``) helper function, used to follow one level of
#: indirection: ``parse_resource_type`` calls the local ``string_to_resource_type``,
#: and only that helper names the core symbol.
_LOCAL_FN_RE = re.compile(
    r"(?m)^(?:pub(?:\([^)]*\))?\s+)?(?:async\s+)?fn\s+([A-Za-z0-9_]+)\s*[(<]"
)

#: Core symbols that appear in almost every wrapper body as plumbing rather
#: than as the thing being wrapped. Resolving onto one of these produces
#: mappings like ``loadMainYamlVersion -> get_runtime``, which is precisely the
#: kind of meaningless pairing this module exists to eliminate, so they are
#: never accepted as a counterpart.
_INFRASTRUCTURE_SYMBOLS = frozenset(
    {
        "get_runtime",
        "block_on",
        "runtime",
        "Runtime",
        "to_napi_err",
        "init_logging",
    }
)

#: Suffixes marking error/result plumbing types, likewise never a counterpart.
_INFRASTRUCTURE_SUFFIXES = ("Error", "Result")

#: Method names too ubiquitous to identify anything. Almost every crate defines
#: a ``new`` or an ``as_str``, so matching one says only "this wrapper called a
#: constructor" -- it produced mappings like ``checkForUpdates -> new`` and
#: ``getAllGameIds -> all``, which are precisely as meaningless as the module
#: matches this resolver exists to replace. Blocked from the method tiers only;
#: an exact name match against the export is still honoured.
_UBIQUITOUS_METHODS = frozenset(
    {
        "new",
        "all",
        "default",
        "from",
        "into",
        "get",
        "set",
        "len",
        "is_empty",
        "as_str",
        "as_ref",
        "to_string",
        "clone",
        "iter",
        "parse",
        "build",
        "push",
        "insert",
        "contains",
        "value",
        "name",
        "kind",
        "with_capacity",
    }
)


def camel_case(snake: str) -> str:
    """Convert a Rust snake_case name to the camelCase NAPI emits."""
    head, *tail = snake.split("_")
    return head + "".join(part[:1].upper() + part[1:] for part in tail if part)


def _balanced_body(text: str, open_idx: int) -> str:
    """Return the brace-balanced block starting at the first ``{`` after ``open_idx``."""
    start = text.find("{", open_idx)
    if start == -1:
        return ""
    depth = 0
    for idx in range(start, len(text)):
        if text[idx] == "{":
            depth += 1
        elif text[idx] == "}":
            depth -= 1
            if depth == 0:
                return text[start : idx + 1]
    return text[start:]


@dataclass
class Resolution:
    """One Node export and the core Rust symbol it was resolved to."""

    node_export: str
    rust_symbol: str | None = None
    rust_crate: str | None = None
    confidence: str = "unresolved"
    evidence: str = ""
    candidates: list[str] = field(default_factory=list)


def _crate_name_to_package(crate_ident: str) -> str:
    """``classic_resource_core`` -> ``classic-resource-core``."""
    return crate_ident.replace("_", "-")


def collect_node_wrappers(repo_root: Path) -> dict[str, dict[str, Any]]:
    """Map each Node export name to facts about its ``#[napi]`` wrapper."""
    src_dir = repo_root / NODE_SRC_REL
    wrappers: dict[str, dict[str, Any]] = {}

    for path in sorted(src_dir.glob("*.rs")):
        if path.name.endswith("_tests.rs"):
            continue
        text = path.read_text(encoding="utf-8")

        # File-level imports: which core crate does each bare name come from?
        import_map: dict[str, str] = {}
        for crate, body in _USE_RE.findall(text):
            inner = body
            if "{" in inner:
                inner = inner[inner.find("{") + 1 : inner.rfind("}")]
            for part in inner.split(","):
                part = part.strip()
                if not part:
                    continue
                name = part.split(" as ")[-1].strip() if " as " in part else part
                name = name.split("::")[-1].strip()
                if name and name != "*":
                    import_map[name] = crate

        # From<CoreType> for JsWrapper conversions.
        from_impls: dict[str, str] = {}
        for core_type, js_type in _FROM_IMPL_RE.findall(text):
            from_impls.setdefault(js_type, core_type.split("::")[-1])

        # DTO <- core pairings declared by conversion helpers.
        conversions: dict[str, str] = {}
        for core_type, js_type in _CONVERSION_FN_RE.findall(text):
            if not core_type.startswith("Js"):
                conversions.setdefault(js_type, core_type)

        # File-local helper bodies, so one level of indirection can be followed.
        napi_spans = [(m.start(), m.end()) for m in _NAPI_ITEM_RE.finditer(text)]
        local_helpers: dict[str, str] = {}
        for match in _LOCAL_FN_RE.finditer(text):
            # Skip functions that are themselves #[napi] items.
            if any(start <= match.start() <= end for start, end in napi_spans):
                continue
            local_helpers[match.group(1)] = _balanced_body(text, match.end())

        for match in _NAPI_ITEM_RE.finditer(text):
            kind = match.group("kind")
            name = match.group("name")
            if kind == "impl":
                continue
            args = match.group("args") or ""
            between = match.group("between") or ""
            explicit = _JS_NAME_RE.search(args) or _JS_NAME_RE.search(between)
            if explicit:
                export = explicit.group(1)
            else:
                export = camel_case(name) if kind == "fn" else name

            decl_body = _balanced_body(text, match.end())
            wrappers[export] = {
                "kind": kind,
                "rust_name": name,
                "source_file": f"{NODE_SRC_REL}/{path.name}",
                # The declaration alone: a field naming a wrapped core type
                # lives here, not in any called helper.
                "decl_body": decl_body,
                "body": decl_body,
                "import_map": import_map,
                "from_impls": from_impls,
                "conversions": conversions,
                "local_helpers": local_helpers,
            }

    return wrappers


def resolve_export(
    export: str,
    info: dict[str, Any],
    surface_by_name: dict[str, list[dict[str, Any]]],
) -> Resolution:
    """Resolve one Node export to its core Rust symbol, strongest evidence first."""
    res = Resolution(node_export=export)
    body = info["body"]
    rust_name = info["rust_name"]
    import_map = info["import_map"]

    # Follow one level of indirection into file-local helpers. A thin wrapper
    # often delegates its real work:
    #
    #     pub fn parse_resource_type(name: String) -> String {
    #         let rt = string_to_resource_type(&name);   // local helper
    #         resource_type_to_string(rt)
    #     }
    #
    # Only the helper names the core symbol, so without this the wrapper looks
    # like it references nothing at all. One level is deliberate: deeper chains
    # drift far enough from the export that the evidence stops being credible.
    local_helpers: dict[str, str] = info.get("local_helpers", {})
    for helper_name, helper_body in local_helpers.items():
        if helper_name != rust_name and re.search(
            rf"\b{re.escape(helper_name)}\s*\(", body
        ):
            body += helper_body

    # Evidence 1: crate-qualified references inside the wrapper body.
    qualified = _QUALIFIED_RE.findall(body)
    qualified_names = [(sym, crate) for crate, sym in qualified]

    # `use classic_update_core::{self as core, ...}` makes `core::GithubClient`
    # an equally qualified reference, but under an alias the crate-path regex
    # cannot see. Resolve those aliases so aliased calls count as strong
    # evidence rather than falling through to the weak tiers.
    for alias, crate in import_map.items():
        if not alias.islower():
            continue
        for symbol in re.findall(
            rf"\b{re.escape(alias)}::(?:[a-z0-9_]+::)*([A-Za-z0-9_]+)", body
        ):
            qualified_names.append((symbol, crate))

    # Evidence 2: imported core names mentioned in the body.
    imported_hits = [
        (name, crate)
        for name, crate in import_map.items()
        if re.search(rf"\b{re.escape(name)}\b", body)
    ]

    # Evidence 3: DTO structs declare their core counterpart via From<Core>.
    from_core = info["from_impls"].get(export)

    def is_infrastructure(symbol: str) -> bool:
        return symbol in _INFRASTRUCTURE_SYMBOLS or symbol.endswith(
            _INFRASTRUCTURE_SUFFIXES
        )

    def accept(
        symbol: str,
        crate: str | None,
        confidence: str,
        evidence: str,
        allow_infrastructure: bool = False,
    ) -> bool:
        entries = surface_by_name.get(symbol)
        if not entries:
            return False
        if not allow_infrastructure and is_infrastructure(symbol):
            return False
        # Never resolve an export onto a Rust module -- that is the exact
        # placeholder shape this tool exists to eliminate.
        usable = [e for e in entries if e["kind"] != "module"]
        if not usable:
            return False
        chosen = next(
            (e for e in usable if crate and e["crate"] == crate), usable[0]
        )
        res.rust_symbol = symbol
        res.rust_crate = chosen["crate"]
        res.confidence = confidence
        res.evidence = evidence
        return True

    # Strongest: the wrapper calls a core symbol with the same name it exposes.
    # Infrastructure names are allowed here only because an exact name match
    # means the wrapper genuinely re-exports that symbol.
    for symbol, crate in qualified_names:
        if symbol == rust_name and accept(
            symbol,
            _crate_name_to_package(crate),
            "exact",
            f"{crate}::{symbol} called in wrapper body",
            allow_infrastructure=True,
        ):
            return res

    # Name-derived tiers below bypass the infrastructure filter. That filter
    # exists to stop incidental references (``get_runtime``, ``FileIOError``)
    # from being mistaken for a counterpart in the weak tiers; it must not veto
    # a match this strong, or legitimate domain types whose names merely end in
    # ``Result`` -- ``CheckResult``, ``ScanResult``, ``ValidationResult`` -- get
    # thrown away with the plumbing.
    if from_core and accept(
        from_core,
        None,
        "from_impl",
        f"impl From<{from_core}> for {export}",
        allow_infrastructure=True,
    ):
        return res

    # A conversion helper in the same file pairs this DTO with its core type.
    # For `#[napi(object)]` structs this is usually the only place the
    # correspondence is written down at all.
    converted = info.get("conversions", {}).get(export)
    if converted and accept(
        converted,
        None,
        "conversion_fn",
        f"conversion helper maps {converted} -> {export}",
        allow_infrastructure=True,
    ):
        return res

    # The newtype pattern: a wrapper struct holding a field of a core type
    # names its counterpart outright. Only the declaration is searched, so
    # incidental locals inside method bodies are not picked up.
    field_types = re.findall(
        r"(?m)^\s*(?:pub(?:\([^)]*\))?\s+)?[a-z_][A-Za-z0-9_]*\s*:\s*"
        r"(?:Option\s*<\s*|Arc\s*<\s*|Vec\s*<\s*)*([A-Za-z][A-Za-z0-9_]*)",
        info.get("decl_body", ""),
    )
    for field_type in field_types:
        entries = surface_by_name.get(field_type, [])
        if any(
            e["kind"] in {"struct", "enum", "type", "reexport"} for e in entries
        ) and accept(
            field_type,
            None,
            "inner_field",
            f"wrapper struct holds a field of core type {field_type}",
            allow_infrastructure=True,
        ):
            return res

    # The binding names DTO wrappers ``Js<CoreType>``. Verified against the
    # From-impl ground truth, so treat a core type that matches the export name
    # minus its ``Js`` prefix as strong evidence -- but only when the core name
    # resolves to an actual type rather than a function.
    #
    # The match falls back to case-insensitive because NAPI normalizes acronym
    # casing on the way to TypeScript: core ``BA2Scanner`` surfaces as
    # ``JsBa2Scanner``, and ``DDSAnalyzer`` as ``JsDdsAnalyzer``.
    # Applies to any type-shaped export, with or without the prefix: the
    # binding exposes some core types under their own name (``GithubClient``
    # for core ``GitHubClient``) rather than as ``Js*``.
    if export[:1].isupper():
        core_name = export[2:] if export.startswith("Js") and len(export) > 2 else export
        type_kinds = {"struct", "enum", "type", "trait", "reexport"}
        candidates = [core_name]
        if core_name not in surface_by_name:
            candidates += [
                name
                for name in surface_by_name
                if name.lower() == core_name.lower()
            ]
        for candidate in candidates:
            entries = surface_by_name.get(candidate, [])
            if any(e["kind"] in type_kinds for e in entries) and accept(
                candidate,
                None,
                "js_prefix",
                f"Js-prefix convention: {export} mirrors core type {candidate}",
                allow_infrastructure=True,
            ):
                return res

    # A very common wrapper shape is to construct a core type and immediately
    # call one method on it:
    #
    #     let ops = YamlOperations::new();
    #     let yaml = ops.parse_yaml(&content)?;
    #
    # The method is the real counterpart -- ``yamlParse`` maps to ``parse_yaml``,
    # not merely to ``YamlOperations``. Only methods that exist in the parsed
    # surface as functions are considered, which filters out std combinators
    # like ``map_err`` and ``unwrap`` without needing to enumerate them.
    referenced_crates = {
        _crate_name_to_package(crate) for _sym, crate in qualified_names
    } | {_crate_name_to_package(crate) for _name, crate in imported_hits}
    # Both `value.method(...)` and `CoreType::assoc(...)` count. The associated
    # form is how a bare core type gets used without ever being constructed --
    # `XseType::from_game_id(core_game)` -- and matching only the dotted form
    # left those wrappers resolving on the much weaker `imported` tier.
    method_calls = re.findall(r"[.:]:?([a-z_][A-Za-z0-9_]*)\s*\(", body)
    # Direct uses of a core type that are not method calls:
    #   XseType::from_game_id(..)   associated function
    #   GameId::Fallout4            enum variant, e.g. in a match arm
    #   .parse::<XseType>()         turbofish
    # All three name the core type as plainly as a call does, and matching only
    # the lowercase-after-`::` form left them on the much weaker `imported`
    # tier where an unrelated import could win instead.
    assoc_types = [
        type_name
        for type_name in re.findall(r"\b([A-Z][A-Za-z0-9_]*)::[A-Za-z_]", body)
        + re.findall(r"::<\s*([A-Z][A-Za-z0-9_]*)", body)
        if type_name in import_map or type_name in surface_by_name
    ]
    core_methods = [
        name
        for name in method_calls
        if name not in _UBIQUITOUS_METHODS
        and any(
            e["kind"] == "function" and (not referenced_crates or e["crate"] in referenced_crates)
            for e in surface_by_name.get(name, [])
        )
    ]
    # Prefer a method whose name shares the export's word set (``yaml_parse``
    # vs ``parse_yaml``), then fall back to the first core method called.
    export_words = set(rust_name.split("_"))
    for name in sorted(
        core_methods, key=lambda n: -len(export_words & set(n.split("_")))
    ):
        if accept(
            name,
            None,
            "core_method",
            f"{name}(...) called on a core type in wrapper body",
        ):
            return res

    # Fall back to the core type whose associated function was called.
    for type_name in assoc_types:
        if accept(
            type_name,
            None,
            "core_assoc",
            f"{type_name}::... called in wrapper body",
        ):
            return res

    # Next: any crate-qualified core symbol referenced by the wrapper.
    for symbol, crate in qualified_names:
        if accept(
            symbol,
            _crate_name_to_package(crate),
            "qualified",
            f"{crate}::{symbol} referenced in wrapper body",
        ):
            return res

    # Weakest accepted: an imported core name used in the body, same-name first.
    for name, crate in sorted(imported_hits, key=lambda kv: kv[0] != rust_name):
        if accept(
            name,
            _crate_name_to_package(crate),
            "imported" if name != rust_name else "imported_exact",
            f"use {crate}::{name}; referenced in wrapper body",
        ):
            return res

    res.candidates = sorted({s for s, _ in qualified_names} | {n for n, _ in imported_hits})
    return res


def build_surface_index(repo_root: Path) -> dict[str, list[dict[str, Any]]]:
    """Index the parsed Rust surface by symbol name."""
    # Imported lazily so this module can be used without the node generator's
    # crate config when a caller supplies its own index.
    sys.path.append(str(Path(__file__).resolve().parent))
    import generate_baseline as gb

    surface = parse_rust_surface(
        repo_root,
        target_crates=gb.RUST_TARGET_CRATES,
        owner_by_crate=gb.RUST_OWNER_BY_CRATE,
    )
    index: dict[str, list[dict[str, Any]]] = {}
    for entry in surface["symbols"]:
        index.setdefault(entry["symbol"], []).append(entry)
    return index


def resolve_all(repo_root: Path) -> dict[str, Resolution]:
    """Resolve every Node export found in the binding source."""
    surface_by_name = build_surface_index(repo_root)
    wrappers = collect_node_wrappers(repo_root)
    return {
        export: resolve_export(export, info, surface_by_name)
        for export, info in wrappers.items()
    }


def main() -> int:
    """Print resolutions as JSON for inspection or downstream rewriting."""
    repo_root = Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
    resolutions = resolve_all(repo_root)
    payload = {
        export: {
            "rust_symbol": r.rust_symbol,
            "rust_crate": r.rust_crate,
            "confidence": r.confidence,
            "evidence": r.evidence,
            "candidates": r.candidates,
        }
        for export, r in sorted(resolutions.items())
    }
    print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
