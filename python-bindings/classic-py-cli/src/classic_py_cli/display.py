"""Rendering of Rust-owned Crash Log Scan Run Display Content.

Rust decides *what* a Crash Log Scan Run says; this module decides only *how it
looks* in a plain, pipeable terminal. It composes no sentence about a run: it
concatenates the segments of a line Rust already wrote, in Rust's order.

It renders exactly as the native C++ CLI and the Node demo CLI do -- segments
joined by single spaces, no styling, no capitalization rule, paths whole -- so a
diagnostic a user learned to read in one frontend is still readable here.

Severity reaches no surface in this frontend. `classic-py-cli` writes one stream
of plain lines through :func:`classic_py_cli.output.render_result`, shared by
every command and read structurally by the compliance harness; splitting a run's
lines across two streams would be a change to that shared contract rather than a
change to this run's presentation. Mapping every severity onto plain text is an
explicitly correct adapter choice, and severity stays available on the line for
the day this CLI grows a use for it.

See ``docs/api/classic-scan-presentation.md`` for the adapter rules this module
follows, and ``docs/implementation/scan_run_presentation_consolidation.md`` for
why it exists.
"""

from __future__ import annotations

from typing import Any


def render_display_line(line: Any) -> str:
    """Render one Rust-owned display line as a single plain string.

    Args:
        line: A ``ScanRunDisplayLine`` from the ``classic_scanlog`` binding, or
            anything exposing the same ``segments`` sequence.

    Returns:
        The line's segments concatenated in reading order, separated by single
        spaces. Segments are never reordered within a line, and no wording is
        added between them.

    The line's ``severity`` is deliberately unread; see the module docstring.

    A segment that renders to nothing is dropped rather than joined, so it cannot
    leave a doubled space behind. Only an unrecognized kind can reach that state,
    and it is the one case where this frontend has nothing to print.
    """

    return render_display_segments(line.segments)


def render_display_segments(segments: Any) -> str:
    """Render a bare segment sequence as a single plain string.

    Args:
        segments: An ordered sequence of ``ScanRunDisplaySegment``, such as a
            ``ScanRunRecoveryDecisionDescription.description``.

    Returns:
        The segments concatenated in reading order, separated by single spaces.

    Split out of :func:`render_display_line` because a recovery decision's
    description is a segment list with no line around it -- there is no severity
    to read and no line to belong to. The concatenation rule is deliberately the
    same one rather than a second copy of it.
    """

    rendered = (_render_segment(segment) for segment in segments)
    return " ".join(text for text in rendered if text)


def render_display_lines(lines: Any) -> list[str]:
    """Render an ordered sequence of display lines, one string per line.

    Args:
        lines: The ``display_lines`` sequence from a ``ScanRunExecution``, a
            ``ScanRunEvent``, or a resume-failure exception.

    Returns:
        One rendered string per line, in the order Rust emitted them. This
        frontend reorders, groups, and omits nothing.
    """

    return [render_display_line(line) for line in lines]


def _render_segment(segment: Any) -> str:
    """Render one flattened segment by reading only the field its kind selects.

    A ``count`` prints its value beside the noun Rust already resolved to agree
    with it, so this CLI never re-decides a plural and no user reads "1 logs". A
    ``path`` prints whole; truncating to a filename would be this frontend's
    invention, and a user who wants to open the Autoscan Report needs the path
    that reached it.

    An unrecognized kind falls back to whichever payload field carries a value.
    The taxonomy is frozen at six kinds and the binding ships beside this CLI, so
    this is unreachable in practice -- but the fallback picks a payload rather
    than composing prose. The worst it can do is print a value bare instead of in
    its intended place, or print nothing at all if a future kind carries its
    payload in ``count`` alone. It can never invent a word.
    """

    kind = str(segment.kind)
    if kind == "count":
        return f"{segment.count} {segment.text}"
    if kind == "path":
        return str(segment.path)
    if kind in {"text", "label", "name", "emphasis"}:
        return str(segment.text)
    return str(segment.text or segment.path)
