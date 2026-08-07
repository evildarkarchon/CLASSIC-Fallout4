"""Display-label audit for `classic-py-cli`.

The TUI, the Qt GUI, and the native CLI have each had one of these since the
shared vocabulary work; this frontend had none, and that absence is the direct
reason a raw Vocabulary Token survived here as prose after the same bug had been
fixed in the TUI. A wording fix reaches every frontend now, but only an audit
makes a *re*-introduction fail loudly instead of shipping.

What each of the four audits proves is the same narrow thing: **the frontend did
not reword what Rust handed it.** They differ only in the shape a violation takes
in their language.

- `ui-applications/classic-tui/tests/shared_runtime_audit.rs` -- the original.
  Catches a local naming table: an audited enum turned into a string literal.
- `classic-cli/tests/test_display_label_audit.cpp` and
  `classic-gui/tests/test_display_label_audit.cpp` -- ports of it, since inverted
  to assert the *absence* of the bridge label accessors, because every label
  those frontends print now arrives inside a `label` segment.

This audit does both halves for Python, plus the two detectors the earlier three
could not express until every frontend had stopped writing sentences:

1. A token must not be interpolated into prose. This is the exact shape the bug
   took here -- ``f"...failed during {stage_label}: {message}"`` -- and the shape
   a literal scan cannot catch, because the token only appears at run time.
2. A domain phrase the presentation crate owns must not be written here. The
   deny-list behind that check is shared with the other three audits, so a
   phrase is added once rather than four times.
3. No label accessor is called; every label arrives inside a `label` segment.
4. No plural noun is re-derived for a count; Rust resolves the noun.
5. Every source file in the package is audited, so a new module cannot escape.
6. The renderer reads every one of the six segment kinds.

Wording itself is pinned once, in `classic-scan-presentation`. Nothing here
restates a sentence.
"""

from __future__ import annotations

import ast
import sys
import types
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]
CLI_PACKAGE = REPO_ROOT / "python-bindings" / "classic-py-cli" / "src" / "classic_py_cli"

# Every module in the package, as a path relative to it, listed so a newly added
# one fails the coverage test below rather than escaping the audit silently. The
# TUI audit carries the same list for the same reason. Paths rather than bare
# names because the coverage test walks recursively: a future subpackage is
# audited from the day it appears.
AUDITED_MODULES = (
    "__init__.py",
    "__main__.py",
    "app.py",
    "binding_loader.py",
    "commands.py",
    "context.py",
    "display.py",
    "exit_codes.py",
    "output.py",
    "parser.py",
    "scenarios.py",
)

# Attribute and variable names that carry a Vocabulary Token at run time. A token
# is machine-facing identity: it belongs in a structured payload and in a
# comparison, never spliced into a sentence.
TOKEN_BEARING_NAMES = frozenset(
    {
        "code",
        "disposition",
        "kind",
        "local_ignore_state",
        "phase",
        "provenance",
        "role",
        "severity",
        "stage",
        "state",
        "status",
    }
)

# Suffixes of derived names that still carry a token or a label resolved from one.
# `stage_label` is what the historical bug interpolated.
TOKEN_BEARING_SUFFIXES = ("_disposition", "_kind", "_label", "_stage", "_status", "_token")

# Sentences about a Crash Log Scan Run that `classic-scan-presentation` now owns.
#
# Read from a shared file rather than written out here, because all four frontend
# audits enforce the same list. Four inline copies would reintroduce, in the test
# layer, the very drift the presentation crate exists to delete: a contributor
# adding core-owned prose would have to remember four lists, and forgetting one
# would silently unenforce the phrase in that frontend.
CORE_OWNED_PHRASES_FILE = (
    REPO_ROOT / "business-logic" / "classic-scan-presentation" / "core-owned-phrases.txt"
)


def _load_core_owned_phrases() -> tuple[str, ...]:
    """Return every phrase in the shared deny-list, in file order.

    Blank lines and `#` comments are skipped and each phrase is stripped, so the
    file stays readable and its line endings do not matter.
    """

    lines = CORE_OWNED_PHRASES_FILE.read_text(encoding="utf-8").splitlines()
    return tuple(
        stripped
        for stripped in (line.strip() for line in lines)
        if stripped and not stripped.startswith("#")
    )


# Phrases this frontend enforces that the shared list cannot carry yet.
#
# `succeeded,` is owned by `classic-scan-presentation` (`render_outcome_summary`),
# and this audit forbade it before the shared file existed. It cannot move into
# that file while the Qt GUI still composes its own transient status-bar summary
# from the scan worker's `finished` signal, because the shared list is enforced by
# every frontend at once and the GUI would fail on a migration that has not
# happened. Dropping it instead would silently weaken this frontend to make the
# consolidation look tidier, so it stays here, named, until the shared list can
# take it.
LOCALLY_ENFORCED_PHRASES = ("succeeded,",)

PRESENTATION_OWNED_PHRASES = _load_core_owned_phrases() + LOCALLY_ENFORCED_PHRASES

# The label entry points `classic_scanlog` publishes. They stay correct for a
# surface that labels a domain enum *outside* a display line -- this CLI has no
# such surface any more, because every label it prints arrives inside a `label`
# segment. Their absence is the assertion, exactly as in the C++ audits.
LABEL_ACCESSORS = (
    "scan_run_infrastructure_error_stage_label",
    "scan_run_installed_yaml_data_diagnostic_kind_label",
    "scan_run_local_ignore_reset_failure_stage_label",
    "scan_run_local_ignore_yaml_data_state_label",
    "scan_run_log_disposition_label",
    "scan_run_log_failure_stage_label",
)


def _audited_sources() -> list[tuple[str, str]]:
    """Return the name and text of every audited module."""

    return [
        (name, (CLI_PACKAGE / name).read_text(encoding="utf-8"))
        for name in AUDITED_MODULES
    ]


def _mentions_a_token(expression: ast.expr) -> str | None:
    """Return the first token-bearing name an expression reads, if any.

    Attributes and plain names only. A subscript is deliberately not inspected:
    the scan-run binding publishes every token as an attribute, and dictionary
    keys named ``status`` elsewhere in this CLI describe compliance scenarios
    rather than a Crash Log Scan Run.
    """

    for node in ast.walk(expression):
        name = None
        if isinstance(node, ast.Attribute):
            name = node.attr
        elif isinstance(node, ast.Name):
            name = node.id
        if name is None:
            continue
        if name in TOKEN_BEARING_NAMES or name.endswith(TOKEN_BEARING_SUFFIXES):
            return name
    return None


def _docstring_ids(tree: ast.Module) -> set[int]:
    """Return the identities of every docstring node in a parsed module.

    Docstrings and comments are documentation, not prose a user reads about a
    run, so the literal scans below exclude them. Not excluding them makes a
    comment that merely *describes* the drift read as the drift -- the same
    false positive the CXX parity gate's name scan hit, and fixed the same way.
    """

    documented: set[int] = set()
    for node in ast.walk(tree):
        if not isinstance(
            node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)
        ):
            continue
        body = getattr(node, "body", [])
        if not body:
            continue
        first = body[0]
        if (
            isinstance(first, ast.Expr)
            and isinstance(first.value, ast.Constant)
            and isinstance(first.value.value, str)
        ):
            documented.add(id(first.value))
    return documented


def _string_literals(name: str, source: str) -> list[str]:
    """Return every non-docstring string literal in a module, f-string parts included.

    Comments never appear here at all, because `ast` discards them.
    """

    tree = ast.parse(source, filename=name)
    skip = _docstring_ids(tree)
    return [
        node.value
        for node in ast.walk(tree)
        if isinstance(node, ast.Constant)
        and isinstance(node.value, str)
        and id(node) not in skip
    ]


def _referenced_identifiers(name: str, source: str) -> set[str]:
    """Return every identifier a module names in code, however it reaches it.

    Attribute access, a bare name, and a `getattr` string are all collected,
    because the accessor this CLI used to call was reached by the third.
    """

    tree = ast.parse(source, filename=name)
    referenced: set[str] = set(_string_literals(name, source))
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute):
            referenced.add(node.attr)
        elif isinstance(node, ast.Name):
            referenced.add(node.id)
    return referenced


def _is_prose(value: str) -> bool:
    """Return whether a literal f-string fragment reads as a sentence.

    Whitespace is the test. ``f"{stage}: {message}"`` is a structured join;
    ``f"failed during {stage}"`` is prose with a machine identifier in it.
    """

    return any(character.isspace() for character in value.strip())


def _prose_constant(node: ast.expr) -> bool:
    """Return whether an expression is a string literal that reads as a sentence."""

    return (
        isinstance(node, ast.Constant)
        and isinstance(node.value, str)
        and _is_prose(node.value)
    )


def _token_in_prose_violations(name: str, source: str) -> list[str]:
    """Return every place a module splices a token-bearing value into a sentence.

    All four ways Python builds a string are covered. Checking only f-strings
    would leave the audit describing the shape the bug happened to take rather
    than the thing it must prevent, and a contributor reaching for ``+`` or
    ``.format()`` would pass a green audit while reintroducing the exact drift.
    """

    violations: list[str] = []
    tree = ast.parse(source, filename=name)
    for node in ast.walk(tree):
        mentioned: str | None = None

        if isinstance(node, ast.JoinedStr):
            # f"failed during {stage_label}"
            if any(_prose_constant(part) for part in node.values):
                for part in node.values:
                    if isinstance(part, ast.FormattedValue):
                        mentioned = mentioned or _mentions_a_token(part.value)
        elif isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
            # "failed during " + stage_label
            if _prose_constant(node.left) or _prose_constant(node.right):
                for side in (node.left, node.right):
                    if not _prose_constant(side):
                        mentioned = mentioned or _mentions_a_token(side)
        elif isinstance(node, ast.BinOp) and isinstance(node.op, ast.Mod):
            # "failed during %s" % stage_label
            if _prose_constant(node.left):
                mentioned = _mentions_a_token(node.right)
        elif (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "format"
            and _prose_constant(node.func.value)
        ):
            # "failed during {}".format(stage_label)
            for argument in [*node.args, *(keyword.value for keyword in node.keywords)]:
                mentioned = mentioned or _mentions_a_token(argument)

        if mentioned is not None:
            violations.append(f"{name}:{node.lineno} joins {mentioned!r} to prose")
    return violations


def _plural_violations(name: str, source: str) -> list[str]:
    """Return every place a module re-derives a plural noun for a count.

    Catches both shapes the duplicated helper took across the frontends: a
    conditional between a singular and a plural literal, and a bare ``+ "s"``.
    """

    violations: list[str] = []
    tree = ast.parse(source, filename=name)
    for node in ast.walk(tree):
        if isinstance(node, ast.IfExp):
            body, orelse = node.body, node.orelse
            if (
                isinstance(body, ast.Constant)
                and isinstance(orelse, ast.Constant)
                and isinstance(body.value, str)
                and isinstance(orelse.value, str)
                and {body.value + "s", orelse.value + "s"} & {body.value, orelse.value}
            ):
                violations.append(f"{name}:{node.lineno} chooses a noun's number")
        if (
            isinstance(node, ast.BinOp)
            and isinstance(node.op, ast.Add)
            and isinstance(node.right, ast.Constant)
            and node.right.value == "s"
        ):
            violations.append(f"{name}:{node.lineno} appends a plural suffix")
    return violations


@pytest.mark.parametrize(("name", "source"), _audited_sources(), ids=AUDITED_MODULES)
def test_no_source_interpolates_a_vocabulary_token_into_prose(name: str, source: str) -> None:
    """A token never reaches a user as part of a sentence.

    This is the bug #170 records against this CLI, which told a user a run
    ``failed during formid_database_access``. It is caught structurally rather
    than by searching for the token, because the token appears only at run time.
    """

    assert _token_in_prose_violations(name, source) == [], (
        "A Vocabulary Token is machine-facing identity; the sentence around it "
        "belongs to classic-scan-presentation."
    )


@pytest.mark.parametrize(("name", "source"), _audited_sources(), ids=AUDITED_MODULES)
def test_no_source_writes_a_sentence_the_presentation_crate_owns(name: str, source: str) -> None:
    """No frontend-local copy of a statement Rust already makes about a run."""

    for literal in _string_literals(name, source):
        for phrase in PRESENTATION_OWNED_PHRASES:
            assert phrase not in literal, (
                f"{name} writes {phrase!r}, which classic-scan-presentation owns. "
                "Render the run's display lines instead of restating them here."
            )


@pytest.mark.parametrize(("name", "source"), _audited_sources(), ids=AUDITED_MODULES)
def test_no_source_resolves_a_display_label_for_itself(name: str, source: str) -> None:
    """Every label this CLI prints arrives inside a `label` segment.

    The accessors themselves stay published and correct; this frontend simply has
    no surface left that labels a domain enum outside a display line.
    """

    referenced = _referenced_identifiers(name, source)
    for accessor in LABEL_ACCESSORS:
        assert accessor not in referenced, (
            f"{name} reaches {accessor}. A label already carried in a display "
            "segment must not be re-derived."
        )


@pytest.mark.parametrize(("name", "source"), _audited_sources(), ids=AUDITED_MODULES)
def test_no_source_re_derives_a_plural_noun(name: str, source: str) -> None:
    """A `count` segment arrives with the noun Rust already agreed with its value."""

    assert _plural_violations(name, source) == [], (
        "Rust resolves the noun for a count; this frontend prints value then noun."
    )


# --- The audit auditing itself ---------------------------------------------
#
# An audit that passes because its detector never fires is worse than no audit:
# it reads as coverage. Each detector is therefore run against the drift it
# exists to catch, written out here as source text. These are the only places in
# this file where a violating shape appears, and they are strings rather than
# code, so the audit above cannot see them.


def test_the_token_detector_catches_the_bug_it_exists_for() -> None:
    """The historical shape fails the detector, and the correct shape does not."""

    drift = 'summary = f"Crash Log Scan Run failed during {stage_label}: {message}"\n'
    assert _token_in_prose_violations("drift.py", drift)

    # A token compared, and a token placed in a structured payload, are both what
    # tokens are for. Neither may trip the detector, or the audit becomes noise a
    # contributor learns to work around.
    correct = (
        'if str(result.status) == "setup_failed":\n'
        '    payload = {"status": result.status, "stage": error.stage}\n'
        'joined = f"{error.stage}:{error.message}"\n'
    )
    assert _token_in_prose_violations("correct.py", correct) == []


@pytest.mark.parametrize(
    "drift",
    [
        'summary = f"Crash Log Scan Run failed during {error.stage}"\n',
        'summary = "Crash Log Scan Run failed during " + stage_label\n',
        'summary = "Crash Log Scan Run failed during %s" % error.stage\n',
        'summary = "Crash Log Scan Run failed during {}".format(error.stage)\n',
    ],
    ids=["f-string", "concatenation", "percent", "format"],
)
def test_the_token_detector_sees_every_way_python_builds_a_string(drift: str) -> None:
    """No spelling of the same drift escapes.

    Checking only the f-string shape would pin the form the bug happened to take
    rather than the thing that must not happen, and would pass a contributor who
    reached for ``+`` instead.
    """

    assert _token_in_prose_violations("drift.py", drift)


def test_the_plural_detector_catches_both_shapes_the_helper_took() -> None:
    """Each duplicated pluralization shape fails; printing Rust's noun does not."""

    assert _plural_violations("drift.py", 'noun = "log" if count == 1 else "logs"\n')
    assert _plural_violations("drift.py", 'noun = "log" + "s"\n')
    assert _plural_violations(
        "correct.py", 'rendered = f"{segment.count} {segment.text}"\n'
    ) == []


def test_the_shared_deny_list_is_readable_and_not_empty() -> None:
    """A truncated deny-list would make the phrase detector pass vacuously.

    The phrase test loops over the deny-list, so a short list asserts almost
    nothing while still reporting green -- the "reads as coverage while providing
    none" failure the rest of this file is built to avoid. The three native audits
    carry the same guard against the same shared file.

    A *missing* file is not checked here, because it cannot reach this point:
    `PRESENTATION_OWNED_PHRASES` is built at import, so an unreadable file fails
    the whole module at collection, which is louder than any assertion.
    """

    shared = _load_core_owned_phrases()
    assert len(shared) >= 10
    assert "Crash Log Scan Run failed during" in shared

    # Every phrase in the *shared* file must be multi-word. This audit does not
    # need that -- it extracts literals from the AST -- but the three native
    # audits search comment-stripped source instead, where a single-word entry
    # could match an identifier. The shared file has to satisfy its strictest
    # consumer, and asserting it here means the file is checked wherever it is
    # read rather than only where the constraint bites.
    for phrase in shared:
        assert " " in phrase, (
            f"{phrase!r} is a single word; a shared deny-list entry must be a phrase, or the "
            "native audits cannot tell prose from an identifier."
        )

    # The local supplement is deliberately exempt from that rule: `succeeded,` is
    # a bare fragment, which is part of why it cannot move to the shared file yet.
    assert LOCALLY_ENFORCED_PHRASES, "the supplement must not be emptied without moving its phrases"
    assert all(phrase == phrase.strip() for phrase in PRESENTATION_OWNED_PHRASES)


def test_the_phrase_detector_reads_literals_rather_than_comments() -> None:
    """A comment describing the drift is documentation; a literal writing it is not."""

    assert PRESENTATION_OWNED_PHRASES[0] not in " ".join(
        _string_literals("commented.py", f"# {PRESENTATION_OWNED_PHRASES[0]} once\nx = 1\n")
    )
    assert PRESENTATION_OWNED_PHRASES[0] in " ".join(
        _string_literals("drift.py", f'x = "{PRESENTATION_OWNED_PHRASES[0]} discovery"\n')
    )


def test_the_audit_covers_every_module_in_the_package() -> None:
    """A newly added module is audited, or this test fails until it is listed.

    Recursive rather than top-level: the package is flat today, and a glob that
    only saw the top level would let a whole subpackage escape the audit — the
    exact failure this test exists to prevent, in the one shape it would not see.
    """

    present = {
        path.relative_to(CLI_PACKAGE).as_posix()
        for path in CLI_PACKAGE.rglob("*.py")
        if "__pycache__" not in path.parts
    }
    assert present == set(AUDITED_MODULES)


def test_the_renderer_reads_every_segment_kind() -> None:
    """The positive half: no kind's payload is silently dropped.

    Moved down a level from "this CLI resolves every label", which it no longer
    does -- the same relocation the native CLI and the Qt GUI made when their
    audits inverted.
    """

    sys.path.insert(0, str(CLI_PACKAGE.parent))
    from classic_py_cli.display import render_display_line

    payloads = {
        "text": "fixed prose",
        "label": "a Display Label",
        "count": "logs",
        "path": "C:/logs/crash.log",
        "name": "Buffout 4",
        "emphasis": "set apart",
    }
    for kind, payload in payloads.items():
        segment = types.SimpleNamespace(
            kind=kind,
            text="" if kind == "path" else payload,
            path=payload if kind == "path" else "",
            count=7 if kind == "count" else 0,
        )
        rendered = render_display_line(
            types.SimpleNamespace(severity="info", segments=[segment])
        )
        assert payload in rendered, f"the {kind} segment's payload never reached the output"
        if kind == "count":
            assert rendered == "7 logs"
