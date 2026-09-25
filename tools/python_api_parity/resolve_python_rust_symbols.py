#!/usr/bin/env python3
"""Resolve each Python export to the core Rust symbol its PyO3 wrapper uses.

The Python counterpart to ``tools/node_api_parity/resolve_node_rust_symbols.py``,
and it exists for the same reason: the Tier-1 contract pairs a ``pythonExport``
with a ``rustSymbol``, but the gate only ever checked that the named symbol
*exists*, not that it relates to the export. Placeholder rows accumulated behind
that -- ``FileIOCore`` was mapped to the Rust modules ``core``, ``game_files``
and ``similarity`` in three separate rows, none of which verified anything.

For each ``#[pyclass]`` / ``#[pyfunction]`` in the PyO3 crate sources, this reads
the wrapper (struct definition plus every ``#[pymethods] impl`` block for it)
and collects the core symbols it references. In a merged adapter, checked-in
Python facade imports route each native export to every direct-import name.
The resolver uses:

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

import ast
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import tomllib

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
#: ``use classic_foo_core as core;`` keeps qualified uses source-backed.
_CRATE_ALIAS_USE_RE = re.compile(
    r"(?m)^\s*use\s+(classic_[a-z0-9_]+?_(?:core|py))\s+as\s+([A-Za-z_][A-Za-z0-9_]*)\s*;"
)
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
_IMPL_RE = re.compile(
    r"(?m)^\s*(?:#\[pymethods\](?:\s*#\[[^\]]*\])*\s*)?"
    r"impl\s+([A-Za-z0-9_]+)\s*\{"
)
#: Method declarations within a brace-balanced ``#[pymethods]`` impl.
_PYMETHOD_RE = re.compile(
    r"(?m)^[ \t]*(?:(?:pub(?:\([^)]*\))?|async)\s+)*fn\s+"
    r"(?P<name>[A-Za-z_][A-Za-z0-9_]*)\s*(?:<[^{}]*>)?\s*\("
)
_PYMETHOD_NAME_RE = re.compile(r'#\[pyo3\(\s*name\s*=\s*"([A-Za-z0-9_]+)"')

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
                return text[start: idx + 1]
    return text[start:]


def _collect_pymethods(block: str) -> dict[str, dict[str, str]]:
    """Return exposed method bodies keyed by their Python method/property name.

    A paired setter shares its public property key with the getter; the getter
    supplies the retained read path for source ownership checks.
    """
    methods: dict[str, dict[str, str]] = {}
    cursor = 1
    while match := _PYMETHOD_RE.search(block, cursor):
        prefix = re.sub(r"(?m)^[ \t]*//[^\n]*(?:\n|$)", "", block[cursor:match.start()])
        name = match.group("name")
        getter = re.search(r"#\[getter(?:\(([^)]*)\))?\]", prefix)
        setter = re.search(r"#\[setter(?:\(([^)]*)\))?\]", prefix)
        if re.search(r"#\[new\]", prefix):
            public_name = "__init__"
            attribute = "new"
        elif getter or setter:
            property_attr = getter or setter
            attribute = "getter" if getter else "setter"
            explicit_name = property_attr.group(1) if property_attr else None
            public_name = (
                explicit_name.strip().strip('"')
                if explicit_name else name.removeprefix(f"{'get' if getter else 'set'}_")
            )
        else:
            override = _PYMETHOD_NAME_RE.search(prefix)
            public_name = override.group(1) if override else name
            attribute = "method"
        body = _balanced_block(block, match.end())
        open_idx = block.find("{", match.end())
        if not body or open_idx == -1:
            cursor = match.end()
            continue
        cursor = open_idx + len(body)
        # A paired setter has the same public property. Prefer the getter's
        # read path when both exist; neither may silently overwrite it.
        if public_name in methods and attribute != "getter":
            continue
        methods[public_name] = {
            "rust_name": name,
            "body": body,
            "method_attribute": attribute,
        }
    return methods


@dataclass
class Resolution:
    """One Python export and the core Rust symbol it was resolved to."""

    python_export: str
    python_module: str | None = None
    rust_symbol: str | None = None
    rust_crate: str | None = None
    confidence: str = "unresolved"
    evidence: str = ""
    candidates: list[str] = field(default_factory=list)
    crate_from_source: bool = False
    route_error: str | None = None


def source_backed_crate(resolution: Resolution | None) -> str | None:
    """Return a core crate only when direct PyO3 source evidence names it."""
    if (
            resolution is not None
            and resolution.crate_from_source
            and resolution.confidence in {
                "exact", "from_impl", "imported_exact", "associated_fn",
                "conversion_fn", "inner_field", "qualified", "imported",
                "method_call", "typed_receiver"
            }
    ):
        return resolution.rust_crate
    return None


def source_backed_symbol(resolution: Resolution | None) -> str | None:
    """Return a counterpart symbol only with direct crate-backed evidence."""
    if source_backed_crate(resolution) is not None and resolution is not None:
        return resolution.rust_symbol
    return None


def _crate_ident_to_package(crate_ident: str) -> str:
    """``classic_scanlog_core`` -> ``classic-scanlog-core``."""
    return crate_ident.replace("_", "-")


def _source_type_ref(
        type_ref: str, import_map: dict[str, str]
) -> tuple[str, str | None]:
    """Return a core type's name and crate from its path or direct import."""
    parts = type_ref.split("::")
    symbol = parts[-1].split("<", 1)[0]
    crate_ident = parts[0] if len(parts) > 1 else import_map.get(symbol)
    if crate_ident in import_map:
        crate_ident = import_map[crate_ident]
    if isinstance(crate_ident, str) and crate_ident.startswith("classic_"):
        return symbol, _crate_ident_to_package(crate_ident)
    return symbol, None


def _canonical_source_entry(
        entry: dict[str, Any],
        surface_by_name: dict[str, list[dict[str, Any]]],
) -> dict[str, Any] | None:
    """Follow external Rust reexports to the defining crate and symbol.

    Returns ``None`` if an external target is missing or the reexport chain
    cycles, so a stale namesake cannot supply ownership evidence.
    """
    seen: set[tuple[str, str]] = set()
    current = entry
    while current["kind"] == "reexport":
        source_expr = current.get("source_expr", "")
        match = _QUALIFIED_RE.fullmatch(source_expr)
        if match is None:
            return current
        target_crate = _crate_ident_to_package(match.group(1))
        target_symbol = match.group(2)
        target = (target_crate, target_symbol)
        if target in seen:
            return None
        seen.add(target)
        candidates = [
            candidate for candidate in surface_by_name.get(target_symbol, [])
            if candidate["crate"] == target_crate and candidate["kind"] != "module"
        ]
        if not candidates:
            return None
        current = next(
            (candidate for candidate in candidates if candidate["kind"] != "reexport"),
            candidates[0],
        )
    return current


def _binding_source_files(repo_root: Path) -> list[Path]:
    """Every PyO3 binding source file, including a future merged adapter crate."""
    files: list[Path] = []
    for root in (repo_root / PY_BINDINGS_REL, repo_root / FOUNDATION_PY_REL):
        if not root.is_dir():
            continue
        for crate_dir in sorted(root.iterdir()):
            if not crate_dir.is_dir() or not (
                    crate_dir.name.endswith("-py")
                    or (crate_dir / "Cargo.toml").is_file()
            ):
                continue
            src = crate_dir / "src"
            if src.is_dir():
                files.extend(
                    p for p in sorted(src.rglob("*.rs")) if not p.name.endswith("_tests.rs")
                )
    return files


def _python_module_for_source(repo_root: Path, path: Path) -> str | None:
    """Identify the direct-import facade from a legacy crate or facade path."""
    parts = path.relative_to(repo_root).parts
    crate_name = parts[1]
    src_relative = path.relative_to(repo_root / parts[0] / crate_name / "src")
    for component in reversed((*src_relative.parts[:-1], path.stem)):
        if re.fullmatch(r"classic_[a-z0-9_]+", component):
            return component
    if crate_name.endswith("-py"):
        return crate_name.removesuffix("-py").replace("-", "_")
    return None


def _has_facade_source_path(crate_dir: Path, path: Path) -> bool:
    """Whether a Rust source path itself identifies a direct-import facade."""
    src_relative = path.relative_to(crate_dir / "src")
    return any(
        re.fullmatch(r"classic_[a-z0-9_]+", component)
        for component in (*src_relative.parts[:-1], path.stem)
    )


def _native_module_for_crate(crate_dir: Path) -> str:
    """Read the PyO3 extension name used by facade import statements."""
    manifest_path = crate_dir / "Cargo.toml"
    if not manifest_path.is_file():
        return crate_dir.name.replace("-", "_")
    manifest = tomllib.loads(manifest_path.read_text(encoding="utf-8"))
    package_name = manifest["package"]["name"].replace("-", "_")
    return manifest.get("lib", {}).get("name", package_name)


def _facade_module_for_path(path: Path) -> str | None:
    """Recognize a direct-import facade module or package initializer."""
    module = path.parent.name if path.name == "__init__.py" else path.stem
    return module if re.fullmatch(r"classic_[a-z0-9_]+", module) else None


def _facade_routes(
        crate_dir: Path, native_module: str
) -> tuple[dict[str, str | None], bool]:
    """Trace explicit facade imports to native names.

    Returns the public-name-to-native-name routes (``None`` for a declared
    ``__all__`` name without an import) and whether any facade source exists.
    Raises ``ValueError`` for unreadable or invalid facade source, wildcard or
    conflicting native routes, or a facade with no traceable public names.
    """
    routes: dict[str, str | None] = {}
    facade_files = [
        path for path in sorted(crate_dir.rglob("*.py"))
        if _facade_module_for_path(path) is not None
        and not {"tests", ".venv", "build", "dist", "target"}.intersection(path.parts)
    ]
    for path in facade_files:
        module = _facade_module_for_path(path)
        assert module is not None
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except (OSError, UnicodeError, SyntaxError) as error:
            raise ValueError(f"cannot read Python facade {path}: {error}") from error
        native_aliases: set[str] = set()
        module_routes: dict[str, str] = {}
        declared: set[str] = set()
        # Only module-level bindings become attributes of the direct-import
        # facade; aliases inside helpers must not certify a public export.
        for node in tree.body:
            if isinstance(node, ast.ImportFrom):
                imported_module = node.module or ""
                if imported_module.split(".")[-1] == native_module:
                    for alias in node.names:
                        if alias.name == "*":
                            raise ValueError(
                                f"cannot source-resolve wildcard native import in {path}"
                            )
                        module_routes[alias.asname or alias.name] = alias.name
                elif not imported_module:
                    native_aliases.update(
                        alias.asname or alias.name
                        for alias in node.names if alias.name == native_module
                    )
            elif isinstance(node, ast.Import):
                native_aliases.update(
                    alias.asname or alias.name
                    for alias in node.names
                    if alias.name.split(".")[-1] == native_module
                )
            elif isinstance(node, ast.Assign):
                if (
                        isinstance(node.value, ast.Attribute)
                        and isinstance(node.value.value, ast.Name)
                        and node.value.value.id in native_aliases
                ):
                    for target in node.targets:
                        if isinstance(target, ast.Name):
                            module_routes[target.id] = node.value.attr
                if any(
                        isinstance(target, ast.Name) and target.id == "__all__"
                        for target in node.targets
                ) and isinstance(node.value, (ast.List, ast.Tuple)):
                    declared.update(
                        item.value for item in node.value.elts
                        if isinstance(item, ast.Constant) and isinstance(item.value, str)
                    )
        for public_name, native_export in module_routes.items():
            if public_name.startswith("_"):
                continue
            key = f"{module}.{public_name}"
            if key in routes and routes[key] != native_export:
                raise ValueError(f"conflicting native routes for {key}: {path}")
            routes[key] = native_export
        for public_name in declared:
            routes.setdefault(f"{module}.{public_name}", None)
        if not module_routes and not declared:
            raise ValueError(f"facade has no traceable native exports: {path}")
    return routes, bool(facade_files)


def collect_python_wrappers(repo_root: Path) -> dict[str, dict[str, Any]]:
    """Route PyO3 native names to facade-qualified public exports.

    Raises ``ValueError`` for unrouteable native source or duplicate native
    declarations; explicit missing facade imports are recorded for gate diagnostics.
    """
    native_wrappers: dict[Path, dict[str, dict[str, Any]]] = {}

    for path in _binding_source_files(repo_root):
        parts = path.relative_to(repo_root).parts
        crate_dir = repo_root / parts[0] / parts[1]
        native_exports = native_wrappers.setdefault(crate_dir, {})
        text = path.read_text(encoding="utf-8")
        module = _python_module_for_source(repo_root, path)

        import_map: dict[str, str] = {}
        import_symbols: dict[str, str] = {}
        crate_aliases = {
            alias: crate for crate, alias in _CRATE_ALIAS_USE_RE.findall(text)
        }
        for crate, body in _USE_RE.findall(text):
            inner = body
            if "{" in inner:
                inner = inner[inner.find("{") + 1: inner.rfind("}")]
            for part in inner.split(","):
                part = part.strip()
                if not part:
                    continue
                name = part.split(" as ")[-1].strip() if " as " in part else part
                name = name.split("::")[-1].strip()
                if name and name != "*":
                    import_map[name] = crate
                    import_symbols[name] = part.split(" as ")[0].split("::")[-1].strip()

        from_impls: dict[str, str] = {}
        for core_type, py_type in _FROM_IMPL_RE.findall(text):
            from_impls.setdefault(py_type, core_type)

        # Method blocks, keyed by the Rust type they belong to. Core references
        # for a pyclass usually live here rather than in the struct body.
        impl_bodies: dict[str, str] = {}
        methods_by_type: dict[str, dict[str, dict[str, Any]]] = {}
        for match in _IMPL_RE.finditer(text):
            type_name = match.group(1)
            block = _balanced_block(text, match.end() - 1)
            impl_bodies[type_name] = impl_bodies.get(type_name, "") + block
            if "#[pymethods]" in match.group(0):
                methods_by_type.setdefault(type_name, {}).update(
                    {
                        name: {
                            **method,
                            "source_file": str(path.relative_to(repo_root)).replace("\\", "/"),
                            "import_map": import_map,
                            "crate_aliases": crate_aliases,
                        }
                        for name, method in _collect_pymethods(block).items()
                    }
                )

        for match in _PYITEM_RE.finditer(text):
            rust_name = match.group("name")
            args = match.group("args") or ""
            between = match.group("between") or ""
            explicit = _NAME_ATTR_RE.search(args) or _NAME_ATTR_RE.search(between)
            export = explicit.group(1) if explicit else rust_name

            decl_body = _balanced_block(text, match.end())
            body = decl_body + impl_bodies.get(rust_name, "")

            if export in native_exports:
                existing = native_exports[export]
                if not ("#[cfg(" in between and existing["cfg_conditional"]):
                    raise ValueError(f"duplicate PyO3 native export {export}: {path}")
                # Mutually exclusive platform definitions share one public name.
                # Prefer the variant with direct core references for source parity.
                if len(_QUALIFIED_RE.findall(body)) <= len(
                        _QUALIFIED_RE.findall(existing["body"])
                ):
                    continue
            native_exports[export] = {
                "source_module": module,
                "source_facade_path": _has_facade_source_path(crate_dir, path),
                "native_export": export,
                "cfg_conditional": "#[cfg(" in between,
                "kind": match.group("kind"),
                "rust_name": rust_name,
                "source_file": str(path.relative_to(repo_root)).replace("\\", "/"),
                # The declaration alone, without method bodies: the newtype
                # field that names the wrapped core type lives here.
                "decl_body": decl_body,
                "body": body,
                "import_map": import_map,
                "import_symbols": import_symbols,
                "crate_aliases": crate_aliases,
                "from_impls": from_impls,
                "methods": methods_by_type.get(rust_name, {}),
            }

    wrappers: dict[str, dict[str, Any]] = {}
    for crate_dir, native_exports in native_wrappers.items():
        native_module = _native_module_for_crate(crate_dir)
        facade_routes, has_facade_files = _facade_routes(crate_dir, native_module)
        if has_facade_files:
            for key, native_export in facade_routes.items():
                module, public_name = key.split(".", 1)
                native_info = native_exports.get(native_export) if native_export else None
                if native_info is None:
                    reason = (
                        f"native export {native_export} not found in {native_module}"
                        if native_export else "no traceable native import"
                    )
                    wrappers[key] = {
                        "python_module": module,
                        "python_export": public_name,
                        "unresolved_route": reason,
                    }
                else:
                    wrappers[key] = {
                        **native_info,
                        "python_module": module,
                        "python_export": public_name,
                    }
            continue
        for native_export, info in native_exports.items():
            module = info["source_module"]
            legacy_facade = (
                module is not None
                and (
                    (crate_dir / f"{module}.pyi").is_file()
                    or not (crate_dir / "Cargo.toml").is_file()
                )
            )
            if module is None or not (info["source_facade_path"] or legacy_facade):
                raise ValueError(
                    f"PyO3 native export {native_export} has no facade route: "
                    f"{info['source_file']}"
                )
            key = f"{module}.{native_export}"
            if key in wrappers:
                raise ValueError(f"duplicate PyO3 wrapper for {key}")
            wrappers[key] = {
                **info,
                "python_module": module,
                "python_export": native_export,
            }
    method_wrappers: dict[str, dict[str, Any]] = {}
    for class_key, class_info in wrappers.items():
        for method_name, method_info in class_info.get("methods", {}).items():
            key = f"{class_key}.{method_name}"
            if key in wrappers or key in method_wrappers:
                raise ValueError(f"duplicate PyO3 method export for {key}")
            method_wrappers[key] = {
                **method_info,
                "kind": "method",
                "python_module": class_info["python_module"],
                "python_export": f"{class_info['python_export']}.{method_name}",
                "class_decl_body": class_info["decl_body"],
                "class_import_map": class_info["import_map"],
                "class_import_symbols": class_info["import_symbols"],
                "class_crate_aliases": class_info["crate_aliases"],
            }
    wrappers.update(method_wrappers)
    return wrappers


def resolve_export(
        export: str,
        info: dict[str, Any],
        surface_by_name: dict[str, list[dict[str, Any]]],
) -> Resolution:
    """Resolve one Python export to its core Rust symbol, strongest evidence first."""
    res = Resolution(python_export=export, python_module=info.get("python_module"))
    # Documentation may name imported core types that the wrapper never uses.
    # Strip whole-line Rust comments before collecting source references.
    body = re.sub(r"(?m)^[ \t]*//[^\n]*(?:\n|$)", "", info["body"])
    rust_name = info["rust_name"]
    import_map = info["import_map"]
    crate_aliases = info.get("crate_aliases", {})
    reference_map = {**import_map, **crate_aliases}
    decl_body = re.sub(
        r"(?m)^[ \t]*//[^\n]*(?:\n|$)", "", info.get("decl_body", "")
    )
    # A struct's declaration may mention input types unrelated to its core
    # counterpart. Incidental fallback scans only behavior in its impl blocks.
    operative_body = (
        body[len(decl_body):]
        if info.get("kind") in {"struct", "enum"} and body.startswith(decl_body)
        else body
    )

    qualified_names = [(sym, crate) for crate, sym in _QUALIFIED_RE.findall(body)]
    for alias, crate in crate_aliases.items():
        qualified_names.extend(
            (symbol, crate)
            for symbol in re.findall(
                rf"\b{re.escape(alias)}::(?:[a-z0-9_]+::)*([A-Za-z0-9_]+)",
                body,
            )
        )
    imported_hits = [
        (name, crate)
        for name, crate in import_map.items()
        if re.search(rf"\b{re.escape(name)}\b", body)
    ]
    from_ref = info["from_impls"].get(rust_name) or info["from_impls"].get(export)
    from_core, from_crate = (
        _source_type_ref(from_ref, reference_map) if from_ref else (None, None)
    )
    source_crates_by_symbol: dict[str, set[str]] = {}
    for symbol, crate_ident in [*qualified_names, *imported_hits]:
        source_crates_by_symbol.setdefault(symbol, set()).add(
            _crate_ident_to_package(crate_ident)
        )
    if from_core and from_crate:
        source_crates_by_symbol.setdefault(from_core, set()).add(from_crate)

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
        """Accept a non-module symbol only from its source-identified crate."""
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
        # An unqualified fallback must respect crate evidence already present
        # in this wrapper; otherwise a name match can undo a failed path lookup.
        source_crates = {crate} if crate else source_crates_by_symbol.get(symbol)
        if source_crates:
            usable = [e for e in usable if e["crate"] in source_crates]
            if not usable:
                return False
        chosen = usable[0]
        canonical = _canonical_source_entry(chosen, surface_by_name)
        if canonical is None:
            return False
        res.rust_symbol = canonical["symbol"]
        res.rust_crate = canonical["crate"]
        res.confidence = confidence
        res.evidence = (
            f"{evidence}; reexported from {canonical['crate']}"
            if canonical is not chosen else evidence
        )
        res.crate_from_source = crate is not None
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
            from_crate,
            "from_impl",
            f"impl From<{from_ref}> for {rust_name}",
            allow_infrastructure=True,
    ):
        return res

    # A top-level wrapper can expose one associated operation of an imported
    # core type. The receiver type itself is not the operation's counterpart.
    if info.get("kind") == "fn":
        export_words = set(rust_name.split("_"))
        associated_calls = re.findall(
            r"\b([A-Z][A-Za-z0-9_]*)::([a-z_][A-Za-z0-9_]*)\s*\(", body
        )
        for owner, method in sorted(
                associated_calls,
                key=lambda call: -len(export_words & set(call[1].split("_"))),
        ):
            crate_ident = import_map.get(owner)
            if (
                    method == "new"
                    or not crate_ident
                    or not (export_words & set(method.split("_")))
            ):
                continue
            crate = _crate_ident_to_package(crate_ident)
            if any(
                    entry["kind"] == "function" and entry["crate"] == crate
                    for entry in surface_by_name.get(method, [])
            ) and accept(
                method,
                crate,
                "associated_fn",
                f"{owner}::{method}(...) called in wrapper",
            ):
                return res

    # A same-named imported core type beats an unrelated input field, such as
    # GameScanOrchestrator's GameScanConfig. The source import fixes its crate.
    for name, crate_ident in imported_hits:
        if name in {rust_name, export, rust_name.removeprefix("Py")} and accept(
                name,
                _crate_ident_to_package(crate_ident),
                "imported_exact",
                f"use {crate_ident}::{name}; wrapper names the same core type",
                allow_infrastructure=True,
        ):
            return res

    # The declared result of an into_core conversion identifies a DTO's core
    # counterpart more directly than other types used inside the conversion.
    converted = re.search(
        r"\bfn\s+into_core\s*\([^)]*\)\s*->\s*([A-Za-z_][A-Za-z0-9_:]*)",
        body,
    )
    if converted:
        converted_symbol, converted_crate = _source_type_ref(
            converted.group(1), reference_map
        )
        if converted_crate and accept(
                converted_symbol,
                converted_crate,
                "conversion_fn",
                f"into_core returns {converted.group(1)}",
                allow_infrastructure=True,
        ):
            return res

    # The PyO3 newtype pattern names the wrapped core type outright:
    #
    #     #[pyclass(name = "YamlData")]
    #     pub struct PyYamlData { inner: YamlDataCore }
    #
    # An inner field whose declared type is a known core type is structural
    # evidence, and it beats guessing from the exported name -- which would
    # miss ``YamlData`` -> ``YamlDataCore`` entirely. Only the declaration is
    # searched, and other typed fields may just be inputs to a Python DTO.
    field_refs = re.findall(
        r"(?m)^\s*(?:pub(?:\([^)]*\))?\s+)?([a-z_][A-Za-z0-9_]*)\s*:\s*"
        r"(?:Option\s*<\s*|Arc\s*<\s*|Vec\s*<\s*)*([A-Za-z][A-Za-z0-9_:]*)",
        info.get("decl_body", ""),
    )
    for field_name, field_type in field_refs:
        if field_name != "inner":
            continue
        field_symbol, field_crate = _source_type_ref(field_type, reference_map)
        entries = surface_by_name.get(field_symbol, [])
        if any(
                e["kind"] in {"struct", "enum", "type", "reexport"} for e in entries
        ) and accept(
            field_symbol,
            field_crate,
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

    operative_qualified = [
        (symbol, crate) for crate, symbol in _QUALIFIED_RE.findall(operative_body)
    ]
    for alias, crate in crate_aliases.items():
        operative_qualified.extend(
            (symbol, crate)
            for symbol in re.findall(
                rf"\b{re.escape(alias)}::(?:[a-z0-9_]+::)*([A-Za-z0-9_]+)",
                operative_body,
            )
        )
    for symbol, crate in operative_qualified:
        if accept(
                symbol,
                _crate_ident_to_package(crate),
                "qualified",
                f"{crate}::{symbol} referenced in wrapper",
        ):
            return res

    operative_imports = [
        (name, crate) for name, crate in imported_hits
        if re.search(rf"\b{re.escape(name)}\b", operative_body)
    ]
    for name, crate in sorted(operative_imports, key=lambda kv: kv[0] != rust_name):
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


def build_surface_index(
        repo_root: Path, rust_manifest: dict[str, Any] | None = None
) -> dict[str, list[dict[str, Any]]]:
    """Index a supplied Rust manifest or parse the repository source once."""
    if rust_manifest is None:
        sys.path.append(str(Path(__file__).resolve().parent))
        import generate_baseline as gb

        rust_manifest = parse_rust_surface(
            repo_root,
            target_crates=gb.RUST_TARGET_CRATES,
            owner_by_crate=gb.RUST_OWNER_BY_CRATE,
        )
    index: dict[str, list[dict[str, Any]]] = {}
    for entry in rust_manifest["symbols"]:
        index.setdefault(entry["symbol"], []).append(entry)
    return index


def resolve_method_export(
        info: dict[str, Any],
        surface_by_name: dict[str, list[dict[str, Any]]],
) -> Resolution:
    """Resolve a PyO3 method from its body or typed inner receiver.

    Distinct core candidates remain unresolved. A receiver with no verified
    public method still supplies crate-only evidence, with no Rust symbol.
    """
    res = Resolution(
        python_export=info["python_export"],
        python_module=info["python_module"],
    )
    body = re.sub(r"(?m)^[ \t]*//[^\n]*(?:\n|$)", "", info["body"])
    import_map = info["import_map"]
    crate_aliases = info.get("crate_aliases", {})
    candidates: set[tuple[str, str]] = set()
    method_words = set(info["rust_name"].split("_")) - {"get", "set", "new"}

    def add_function(symbol: str, crate_ident: str) -> None:
        """Add a name-aligned, public function at its canonical manifest owner."""
        if not (method_words & set(symbol.split("_"))):
            return
        crate = _crate_ident_to_package(crate_ident)
        for entry in surface_by_name.get(symbol, []):
            if entry["crate"] != crate or entry["kind"] not in {"function", "reexport"}:
                continue
            canonical = _canonical_source_entry(entry, surface_by_name)
            if canonical is not None and canonical["kind"] == "function":
                candidates.add((canonical["crate"], canonical["symbol"]))

    for crate_ident, symbol in _QUALIFIED_RE.findall(body):
        add_function(symbol, crate_ident)
    for alias, crate_ident in crate_aliases.items():
        for symbol in re.findall(
                rf"\b{re.escape(alias)}::(?:[a-z0-9_]+::)*([A-Za-z0-9_]+)", body
        ):
            add_function(symbol, crate_ident)
    for owner, symbol in re.findall(
            r"\b([A-Z][A-Za-z0-9_]*)::([a-z_][A-Za-z0-9_]*)\s*\(", body
    ):
        if owner in import_map:
            add_function(symbol, import_map[owner])
    for symbol, crate_ident in import_map.items():
        if re.search(rf"(?<![.\w:]){re.escape(symbol)}\s*\(", body):
            add_function(symbol, crate_ident)

    receiver_crate: str | None = None
    inner = re.search(
        r"(?m)^\s*inner\s*:\s*"
        r"(?:Option\s*<\s*|Arc\s*<\s*|Vec\s*<\s*)*([A-Za-z][A-Za-z0-9_:]*)",
        info.get("class_decl_body", ""),
    )
    uses_inner = bool(re.search(r"\bself\s*\.\s*inner\b", body))
    constructs_inner = bool(re.search(r"\bSelf\s*\{[^{}]*\binner\s*:", body))
    if inner and (uses_inner or constructs_inner):
        class_imports = {
            **info.get("class_import_map", {}),
            **info.get("class_crate_aliases", {}),
        }
        inner_symbol, inner_crate = _source_type_ref(inner.group(1), class_imports)
        inner_symbol = info.get("class_import_symbols", {}).get(inner_symbol, inner_symbol)
        if inner_crate:
            type_entries = [
                entry for entry in surface_by_name.get(inner_symbol, [])
                if entry["crate"] == inner_crate
                and entry["kind"] in {"struct", "enum", "type", "reexport"}
            ]
            if type_entries:
                canonical = _canonical_source_entry(type_entries[0], surface_by_name)
                if canonical is not None:
                    receiver_crate = canonical["crate"]
                    # Chained builders may reach the typed inner value through
                    # std::mem::take or clone before the domain method call.
                    if uses_inner and isinstance(receiver_crate, str):
                        for method in re.findall(r"\.\s*([a-z_][A-Za-z0-9_]*)\s*\(", body):
                            add_function(method, receiver_crate.replace("-", "_"))

    # A constructor may build a lookup from another crate as an input, then
    # store the analyzer it returns. The typed `Self.inner` owns the result.
    if constructs_inner and receiver_crate:
        candidates = {
            candidate for candidate in candidates if candidate[0] == receiver_crate
        }

    if len(candidates) == 1:
        res.rust_crate, res.rust_symbol = next(iter(candidates))
        res.confidence = "method_call"
        res.evidence = "method body calls a crate-backed core function"
        res.crate_from_source = True
    elif not candidates and receiver_crate:
        res.rust_crate = receiver_crate
        res.confidence = "typed_receiver"
        action = "constructs" if constructs_inner else "uses"
        res.evidence = f"method {action} inner core value from {receiver_crate}"
        res.crate_from_source = True
    else:
        res.candidates = sorted(f"{crate}::{symbol}" for crate, symbol in candidates)
    return res


def resolve_all(
        repo_root: Path, rust_manifest: dict[str, Any] | None = None
) -> dict[str, Resolution]:
    """Resolve facade exports and retain explicit missing native routes."""
    surface_by_name = build_surface_index(repo_root, rust_manifest)
    wrappers = collect_python_wrappers(repo_root)
    return {
        key: (
            Resolution(
                python_export=info["python_export"],
                python_module=info["python_module"],
                evidence=info["unresolved_route"],
                route_error=info["unresolved_route"],
            )
            if "unresolved_route" in info
            else resolve_method_export(info, surface_by_name)
            if info["kind"] == "method"
            else resolve_export(info["python_export"], info, surface_by_name)
        )
        for key, info in wrappers.items()
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
