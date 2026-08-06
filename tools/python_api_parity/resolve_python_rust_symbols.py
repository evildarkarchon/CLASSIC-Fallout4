#!/usr/bin/env python3
"""Resolve each Python export to the core Rust symbol its PyO3 wrapper uses.

The Python counterpart to ``tools/node_api_parity/resolve_node_rust_symbols.py``,
and it exists for the same reason: the Tier-1 contract pairs a ``pythonExport``
with a ``rustSymbol``, but the gate only ever checked that the named symbol
*exists*, not that it relates to the export. Placeholder rows accumulated behind
that -- ``FileIOCore`` was mapped to the Rust modules ``core``, ``game_files``
and ``similarity`` in three separate rows, none of which verified anything.

For each ``#[pyclass]`` / ``#[pyfunction]`` in ``python-bindings/*-py/src/*.rs``
this reads the wrapper (struct definition plus every ``#[pymethods] impl`` block
for it) and collects the core symbols it references:

* crate-qualified paths -- ``classic_scanlog_core::LogParser``
* names imported by ``use classic_*_core::{...}``
* ``impl From<CoreType> for PyWrapper`` conversions
* the exported name itself matching a core type or function

PyO3 specifics the Node resolver does not need: the Python-visible name comes
from ``#[pyclass(name = "...")]`` when present (the Rust struct is then
conventionally ``Py<Name>``), and methods live in a separate ``#[pymethods]``
block rather than in the item body.

Candidates are ranked strongest-evidence-first and cross-checked against the
parsed Rust surface, so a resolution can never invent a symbol. Anything that
stays ambiguous is reported rather than guessed.
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

PY_BINDINGS_REL = "python-bindings"
FOUNDATION_PY_REL = "foundation"

#: ``classic_foo_core::Bar`` and the PyO3-side ``classic_shared_py::Baz``.
#:
#: Intermediate module segments are consumed so the FINAL identifier is
#: captured: ``classic_version_core::pe_version::is_valid_executable_path``
#: must yield ``is_valid_executable_path``, not the module ``pe_version``.
_QUALIFIED_RE = re.compile(
    r"\b(classic_[a-z0-9_]+?_(?:core|py))::(?:[a-z0-9_]+::)*([A-Za-z0-9_]+)"
)
#: ``use classic_foo_core::{A, B as C};``
_USE_RE = re.compile(r"(?m)^\s*use\s+(classic_[a-z0-9_]+?_(?:core|py))::([^;]+);")
#: ``impl From<CoreType> for PyWrapper``
_FROM_IMPL_RE = re.compile(
    r"impl\s+From\s*<\s*([A-Za-z0-9_:<>]+?)\s*>\s*for\s+([A-Za-z0-9_]+)"
)
#: ``#[pyclass(...)]`` / ``#[pyfunction(...)]`` and the item they decorate.
_PYITEM_RE = re.compile(
    r"#\[(?P<macro>pyclass|pyfunction)(?P<args>\((?:[^()]|\([^()]*\))*\))?\]"
    # `between` absorbs intervening attributes AND their trailing comments;
    # requiring pure whitespace skips declarations annotated with rationale.
    r"(?P<between>(?:\s*(?:#\[[^\]]*\]|//[^\n]*))*)\s*"
    r"(?:pub(?:\([^)]*\))?\s+)?(?:async\s+)?(?P<kind>struct|enum|fn)\s+"
    r"(?P<name>[A-Za-z0-9_]+)"
)
#: ``name = "Foo"`` inside a pyclass/pyfunction/pyo3 attribute.
_NAME_ATTR_RE = re.compile(r'name\s*=\s*"([A-Za-z0-9_]+)"')
#: ``impl PyFoo { ... }`` blocks, whether or not they carry ``#[pymethods]``.
_IMPL_RE = re.compile(r"(?m)^\s*(?:#\[pymethods\]\s*)?impl\s+([A-Za-z0-9_]+)\s*\{")

#: Plumbing that shows up in nearly every wrapper; never a counterpart.
_INFRASTRUCTURE_SYMBOLS = frozenset(
    {
        "get_runtime",
        "block_on",
        "runtime",
        "Runtime",
        "to_py_err",
        "init_logging",
    }
)
_INFRASTRUCTURE_SUFFIXES = ("Error",)


def _balanced_block(text: str, open_idx: int) -> str:
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
    """One Python export and the core Rust symbol it was resolved to."""

    python_export: str
    rust_symbol: str | None = None
    rust_crate: str | None = None
    confidence: str = "unresolved"
    evidence: str = ""
    candidates: list[str] = field(default_factory=list)


def _crate_ident_to_package(crate_ident: str) -> str:
    """``classic_scanlog_core`` -> ``classic-scanlog-core``."""
    return crate_ident.replace("_", "-")


def _binding_source_files(repo_root: Path) -> list[Path]:
    """Every PyO3 binding source file, including the foundation shared crate."""
    files: list[Path] = []
    for root in (repo_root / PY_BINDINGS_REL, repo_root / FOUNDATION_PY_REL):
        if not root.is_dir():
            continue
        for crate_dir in sorted(root.iterdir()):
            if not crate_dir.is_dir() or not crate_dir.name.endswith("-py"):
                continue
            src = crate_dir / "src"
            if src.is_dir():
                files.extend(
                    p for p in sorted(src.rglob("*.rs")) if not p.name.endswith("_tests.rs")
                )
    return files


def collect_python_wrappers(repo_root: Path) -> dict[str, dict[str, Any]]:
    """Map each Python export name to facts about its PyO3 wrapper."""
    wrappers: dict[str, dict[str, Any]] = {}

    for path in _binding_source_files(repo_root):
        text = path.read_text(encoding="utf-8")

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

        from_impls: dict[str, str] = {}
        for core_type, py_type in _FROM_IMPL_RE.findall(text):
            from_impls.setdefault(py_type, core_type.split("::")[-1].split("<")[0])

        # Method blocks, keyed by the Rust type they belong to. Core references
        # for a pyclass usually live here rather than in the struct body.
        impl_bodies: dict[str, str] = {}
        for match in _IMPL_RE.finditer(text):
            type_name = match.group(1)
            impl_bodies[type_name] = impl_bodies.get(type_name, "") + _balanced_block(
                text, match.end() - 1
            )

        for match in _PYITEM_RE.finditer(text):
            rust_name = match.group("name")
            args = match.group("args") or ""
            between = match.group("between") or ""
            explicit = _NAME_ATTR_RE.search(args) or _NAME_ATTR_RE.search(between)
            export = explicit.group(1) if explicit else rust_name

            decl_body = _balanced_block(text, match.end())
            body = decl_body + impl_bodies.get(rust_name, "")

            wrappers[export] = {
                "kind": match.group("kind"),
                "rust_name": rust_name,
                "source_file": str(path.relative_to(repo_root)).replace("\\", "/"),
                # The declaration alone, without method bodies: the newtype
                # field that names the wrapped core type lives here.
                "decl_body": decl_body,
                "body": body,
                "import_map": import_map,
                "from_impls": from_impls,
            }

    return wrappers


def resolve_export(
    export: str,
    info: dict[str, Any],
    surface_by_name: dict[str, list[dict[str, Any]]],
) -> Resolution:
    """Resolve one Python export to its core Rust symbol, strongest evidence first."""
    res = Resolution(python_export=export)
    body = info["body"]
    rust_name = info["rust_name"]
    import_map = info["import_map"]

    qualified_names = [(sym, crate) for crate, sym in _QUALIFIED_RE.findall(body)]
    imported_hits = [
        (name, crate)
        for name, crate in import_map.items()
        if re.search(rf"\b{re.escape(name)}\b", body)
    ]
    from_core = info["from_impls"].get(rust_name) or info["from_impls"].get(export)

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
        # Never resolve onto a Rust module -- that is the placeholder shape
        # this tool exists to eliminate.
        usable = [e for e in entries if e["kind"] != "module"]
        if not usable:
            return False
        chosen = next((e for e in usable if crate and e["crate"] == crate), usable[0])
        res.rust_symbol = symbol
        res.rust_crate = chosen["crate"]
        res.confidence = confidence
        res.evidence = evidence
        return True

    # Strongest: the wrapper calls a core symbol named exactly as it exposes.
    for symbol, crate in qualified_names:
        if symbol in {rust_name, export} and accept(
            symbol,
            _crate_ident_to_package(crate),
            "exact",
            f"{crate}::{symbol} referenced in wrapper",
            allow_infrastructure=True,
        ):
            return res

    if from_core and accept(
        from_core,
        None,
        "from_impl",
        f"impl From<{from_core}> for {rust_name}",
        allow_infrastructure=True,
    ):
        return res

    # The PyO3 newtype pattern names the wrapped core type outright:
    #
    #     #[pyclass(name = "YamlData")]
    #     pub struct PyYamlData { inner: YamlDataCore }
    #
    # A field whose declared type is a known core type is explicit structural
    # evidence, and it beats guessing from the exported name -- which would
    # miss ``YamlData`` -> ``YamlDataCore`` entirely. Only the declaration is
    # searched, not method bodies, so incidental locals are not picked up.
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

    # PyO3 wrappers are conventionally ``Py<CoreType>`` exposed under the core
    # type's own name, so an exported name matching a core type or function is
    # strong evidence. Case-insensitive fallback covers acronym differences.
    type_kinds = {"struct", "enum", "type", "trait", "reexport", "function"}
    candidates = [export, rust_name.removeprefix("Py")]
    candidates += [
        name for name in surface_by_name if name.lower() == export.lower()
    ]
    for candidate in candidates:
        entries = surface_by_name.get(candidate, [])
        if any(e["kind"] in type_kinds for e in entries) and accept(
            candidate,
            None,
            "name_match",
            f"exported name matches core symbol {candidate}",
            allow_infrastructure=True,
        ):
            return res

    # A wrapper that constructs a core type and calls one method on it: the
    # method is the real counterpart. Only methods present in the surface as
    # functions count, which filters std combinators without enumerating them.
    referenced_crates = {
        _crate_ident_to_package(crate) for _s, crate in qualified_names
    } | {_crate_ident_to_package(crate) for _n, crate in imported_hits}
    method_calls = re.findall(r"\.([a-z_][A-Za-z0-9_]*)\s*\(", body)
    core_methods = [
        name
        for name in method_calls
        if any(
            e["kind"] == "function"
            and (not referenced_crates or e["crate"] in referenced_crates)
            for e in surface_by_name.get(name, [])
        )
    ]
    export_words = set(rust_name.split("_"))
    for name in sorted(
        core_methods, key=lambda n: -len(export_words & set(n.split("_")))
    ):
        if accept(
            name, None, "core_method", f".{name}(...) called on a core type in wrapper"
        ):
            return res

    for symbol, crate in qualified_names:
        if accept(
            symbol,
            _crate_ident_to_package(crate),
            "qualified",
            f"{crate}::{symbol} referenced in wrapper",
        ):
            return res

    for name, crate in sorted(imported_hits, key=lambda kv: kv[0] != rust_name):
        if accept(
            name,
            _crate_ident_to_package(crate),
            "imported",
            f"use {crate}::{name}; referenced in wrapper",
        ):
            return res

    res.candidates = sorted(
        {s for s, _ in qualified_names} | {n for n, _ in imported_hits}
    )
    return res


def build_surface_index(repo_root: Path) -> dict[str, list[dict[str, Any]]]:
    """Index the parsed Rust surface by symbol name."""
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
    """Resolve every Python export found in the binding source."""
    surface_by_name = build_surface_index(repo_root)
    wrappers = collect_python_wrappers(repo_root)
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
