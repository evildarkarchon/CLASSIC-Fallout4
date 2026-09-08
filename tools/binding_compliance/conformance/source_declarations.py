"""Identify binding type declarations without inventing runtime behavior proof."""

from __future__ import annotations

import ast
import json
import re
from pathlib import Path

try:
    from ..node_package_metadata import _tokens
except ImportError:
    from node_package_metadata import _tokens


def _group_end(tokens: list[str], start: int, opening: str, closing: str) -> int:
    """Find a balanced group without interpreting opaque string contents."""
    depth = 0
    for index in range(start, len(tokens)):
        depth += tokens[index] == opening
        depth -= tokens[index] == closing
        if depth == 0:
            return index
    raise ValueError("unbalanced Rust source group in type declaration analyzer")


def _rust_facts(
    sources: list[str],
) -> tuple[dict[str, set[str]], set[str], set[str], set[tuple[str, str]]]:
    """Collect real pyclasses, constructors and registrations across all crate files."""
    declarations: dict[str, set[str]] = {}
    constructors: set[str] = set()
    registered: set[str] = set()
    exceptions: set[tuple[str, str]] = set()
    exception_registrations: set[str] = set()
    tokenized = [
        _tokens(re.sub(r"'([A-Za-z_][A-Za-z_0-9]*)\b(?!')", r"lifetime_\1", source))
        for source in sources
    ]
    shadowed = any(
        tokens[index : index + 3] == ["macro_rules", "!", "create_exception"]
        for tokens in tokenized
        for index in range(len(tokens))
    )
    for tokens in tokenized:
        # Rust lifetimes are identifiers rather than quoted character literals.
        # Keeping strings opaque prevents comment/raw-string declaration spoofs.
        imported = any(
            tokens[i : i + 6] == ["use", "pyo3", ":", ":", "create_exception", ";"]
            for i in range(len(tokens))
        )
        for index, token in enumerate(tokens):
            if tokens[index : index + 3] == ["#", "[", "pyclass"]:
                end = _group_end(tokens, index + 1, "[", "]")
                attributes = tokens[index + 3 : end]
                export = None
                for offset in range(len(attributes) - 2):
                    if attributes[offset : offset + 2] == ["name", "="]:
                        export = json.loads(attributes[offset + 2])
                cursor = end + 1
                while tokens[cursor : cursor + 2] == ["#", "["]:
                    cursor = _group_end(tokens, cursor + 1, "[", "]") + 1
                if tokens[cursor : cursor + 1] == ["pub"]:
                    cursor += 1
                    if tokens[cursor : cursor + 1] == ["("]:
                        cursor = _group_end(tokens, cursor, "(", ")") + 1
                if cursor + 1 < len(tokens) and tokens[cursor] in {"struct", "enum"}:
                    name = tokens[cursor + 1]
                    declarations.setdefault(export or name, set()).add(name)
            elif token == "impl" and "{" in tokens[index + 1 :]:
                start = tokens.index("{", index + 1)
                end = _group_end(tokens, start, "{", "}")
                if any(
                    tokens[pos : pos + 4] == ["#", "[", "new", "]"]
                    for pos in range(start + 1, end)
                ):
                    constructors.update(tokens[index + 1 : start])
            elif token == "add_class" and tokens[index + 1 : index + 4] == [
                ":",
                ":",
                "<",
            ]:
                end = _group_end(tokens, index + 3, "<", ">")
                if (
                    index > 0
                    and tokens[index - 1] == "."
                    and tokens[end + 1 : end + 2] == ["("]
                ):
                    registered.add(tokens[end - 1])
            elif token == "create_exception" and tokens[index + 1 : index + 3] == [
                "!",
                "(",
            ]:
                qualified = index >= 3 and tokens[index - 3 : index] == [
                    "pyo3",
                    ":",
                    ":",
                ]
                if (
                    (qualified or (imported and not shadowed))
                    and index + 5 < len(tokens)
                    and tokens[index + 4] == ","
                ):
                    exceptions.add((tokens[index + 3], tokens[index + 5]))
            elif (
                token == "add"
                and index > 0
                and tokens[index - 1] == "."
                and tokens[index + 1 : index + 2] == ["("]
            ):
                end = _group_end(tokens, index + 1, "(", ")")
                args = tokens[index + 2 : end]
                if len(args) > 2 and args[0].startswith('"') and args[1] == ",":
                    name = json.loads(args[0])
                    if any(
                        args[i : i + 8]
                        == ["get_type", ":", ":", "<", name, ">", "(", ")"]
                        for i in range(len(args))
                    ):
                        exception_registrations.add(name)
    return (
        declarations,
        constructors,
        registered,
        {
            (module, name)
            for module, name in exceptions
            if name in exception_registrations
        },
    )


def _shared_exception_declarations(
    root: Path, sources: list[str]
) -> set[tuple[str, str]]:
    """Recognize the imported shared macro only with its standard expansion and registration.

    Token comparison pins declaration semantics while permitting whitespace and
    comment edits. A changed macro or local shadow must regain an evidence owner.
    """
    path = root / "foundation/classic-shared-py/src/exceptions.rs"
    if not path.is_file():
        return set()
    expected = {
        "define_exceptions": """{
            (module: $module:ident, base: $base:ident, io: $io:ident, parse: $parse:ident) => {
                pyo3::create_exception!($module, $base, pyo3::exceptions::PyException,
                    concat!("Base exception for ", stringify!($module), " Rust errors"));
                pyo3::create_exception!($module, $io, $base,
                    concat!(stringify!($module), " I/O errors"));
                pyo3::create_exception!($module, $parse, $base,
                    concat!(stringify!($module), " parse/validation errors"));
            };
        }""",
        "register_exceptions": """{
            ($m:expr, $base:ident, $io:ident, $parse:ident) => {{
                $m.add(stringify!($base), $m.py().get_type::<$base>())?;
                $m.add(stringify!($io), $m.py().get_type::<$io>())?;
                $m.add(stringify!($parse), $m.py().get_type::<$parse>())?;
            }};
        }""",
    }
    tokens = _tokens(path.read_text(encoding="utf-8"))
    for name, body in expected.items():
        starts = [
            i + 3
            for i in range(len(tokens) - 3)
            if tokens[i : i + 3] == ["macro_rules", "!", name]
        ]
        if len(starts) != 1 or tokens[starts[0]] != "{":
            return set()
        end = _group_end(tokens, starts[0], "{", "}")
        if tokens[starts[0] : end + 1] != _tokens(body):
            return set()
    declared: set[tuple[str, str]] = set()
    for source in sources:
        tokens = _tokens(
            re.sub(r"'([A-Za-z_][A-Za-z_0-9]*)\b(?!')", r"lifetime_\1", source)
        )
        if any(
            tokens[i : i + 3]
            in (
                ["macro_rules", "!", "define_exceptions"],
                ["macro_rules", "!", "register_exceptions"],
            )
            for i in range(len(tokens))
        ):
            continue
        imported: set[str] = set()
        for i in range(len(tokens) - 5):
            if tokens[i : i + 5] == ["use", "classic_shared", ":", ":", "{"]:
                end = _group_end(tokens, i + 4, "{", "}")
                names = tokens[i + 5 : end]
                if "as" not in names:
                    imported.update(names)
        if not set(expected) <= imported:
            continue
        registrations = set()
        definitions = []
        for i in range(len(tokens) - 2):
            if tokens[i + 1 : i + 3] != ["!", "("] or tokens[i] not in expected:
                continue
            end = _group_end(tokens, i + 2, "(", ")")
            args = tokens[i + 3 : end]
            if (
                tokens[i] == "register_exceptions"
                and len(args) == 7
                and args[1::2] == [",", ",", ","]
            ):
                registrations.add(tuple(args[2::2]))
            elif (
                tokens[i] == "define_exceptions"
                and len(args) == 15
                and args[0::4] == ["module", "base", "io", "parse"]
                and args[1::4] == [":"] * 4
                and args[3::4] == [","] * 3
            ):
                definitions.append((args[2], tuple(args[6::4])))
        for module, names in definitions:
            if names in registrations:
                declared.update((module, name) for name in names)
    return declared


def python_declaration_exports(repo_root: Path) -> set[tuple[str, str]]:
    """Find type-only exports corroborated by both live stubs and PyO3 source.

    Explicit constructors in either representation prevent structural ownership.
    Methods, properties and static factories are independent runtime rows; this
    function classifies only the containing type declaration. Unknown or
    mismatched source owners receive no declaration disposition.
    """
    root = repo_root.resolve()
    declarations: set[tuple[str, str]] = set()
    for layer in ("foundation", "python-bindings"):
        for stub in sorted((root / layer).glob("*-py/*.pyi")):
            module = ast.parse(stub.read_text(encoding="utf-8"), filename=str(stub))
            typed_dict_names = {
                alias.asname or alias.name
                for statement in module.body
                if isinstance(statement, ast.ImportFrom)
                and statement.module in {"typing", "typing_extensions"}
                for alias in statement.names
                if alias.name == "TypedDict"
            }
            typed_dict_names -= {
                statement.name
                for statement in module.body
                if isinstance(
                    statement, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)
                )
            }
            # A rebound imported name no longer denotes typing's erased dictionary contract.
            typed_dict_names -= {
                node.id
                for statement in module.body
                if isinstance(statement, (ast.Assign, ast.AnnAssign, ast.AugAssign))
                for node in ast.walk(statement)
                if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store)
            }
            source_root = stub.parent / "src"
            # A filename is not a cfg boundary: production modules can end in _tests.rs.
            sources = [
                path.read_text(encoding="utf-8")
                for path in sorted(source_root.rglob("*.rs"))
            ]
            types, constructors, registered, exceptions = _rust_facts(sources)
            exceptions |= _shared_exception_declarations(root, sources)
            for definition in module.body:
                if not isinstance(definition, ast.ClassDef):
                    continue
                if any(
                    isinstance(member, (ast.FunctionDef, ast.AsyncFunctionDef))
                    and member.name in {"__init__", "__new__"}
                    for member in definition.body
                ):
                    continue
                if any(
                    isinstance(base, ast.Name) and base.id in typed_dict_names
                    for base in definition.bases
                ):
                    declarations.add((stub.stem, definition.name))
                    continue
                names = types.get(definition.name, set())
                # Standard exception declarations have no custom Rust constructor;
                # the retained stub gate separately verifies their Python bases.
                if (names and names <= registered and not names & constructors) or (
                    stub.stem,
                    definition.name,
                ) in exceptions:
                    declarations.add((stub.stem, definition.name))
    return declarations
