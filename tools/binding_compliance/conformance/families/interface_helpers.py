"""Exact interface-owned golden markup and read-only report discovery evidence."""

import json
from functools import partial

from ..coverage import CoveragePredicate, FamilyCoveragePolicy

# CommonMark list-item rules preserve the nested empty markers in "* *".
# https://spec.commonmark.org/0.31.2/#list-items
_GOLDEN = {
    "markdown-rendering": {
        "quirks": {
            "normalized": "**Alert**\n\n-----\n\n## Details\n\n- alpha\n- beta",
            "htmlBody": "<p><strong>Alert</strong></p>\n"
            "<hr />\n"
            "<h2>Details</h2>\n"
            "<ul>\n"
            "<li>alpha</li>\n"
            "<li>beta</li>\n"
            "</ul>\n",
            "documentComplete": True,
        },
        "escaping": {
            "normalized": "## Encoded\n\nA < B & C.\n\n`x < y`",
            "htmlBody": "<h2>Encoded</h2>\n"
            "<p>A &lt; B &amp; C.</p>\n"
            "<p><code>x &lt; y</code></p>\n",
            "documentComplete": True,
        },
        "empty": {"normalized": "", "htmlBody": "", "documentComplete": True},
        "empty-frame": {
            "normalized": "* *",
            "htmlBody": "<ul>\n<li>\n<ul>\n<li></li>\n</ul>\n</li>\n</ul>\n",
            "documentComplete": True,
        },
    },
    "report-discovery": {
        "populated": {
            "reports": ["new-AUTOSCAN.md", "old-AUTOSCAN.md"],
            "files": [
                {"path": "nested/deep-AUTOSCAN.md", "hex": "64656570"},
                {"path": "new-AUTOSCAN.md", "hex": "6e6577"},
                {"path": "notes.md", "hex": "6e6f7465"},
                {"path": "old-AUTOSCAN.md", "hex": "6f6c64"},
            ],
            "directories": ["directory-AUTOSCAN.md", "nested"],
        },
        "missing": {"reports": [], "files": [], "directories": []},
    },
}
_SELECTORS = {
    "markdown-rendering": (
        ("markdown_to_html", "normalize_markdown"),
        ("parity:cxx:2c624a0ad743bab6", "parity:cxx:5feb28dc0ac98182"),
    ),
    "report-discovery": (("discover_report_files",), ("parity:cxx:a0c197477ec619ba",)),
}


def _matches(family, case, value):
    """Compare exact UI content, envelope status, and complete file snapshots."""
    return json.dumps(value, sort_keys=True) == json.dumps(
        _GOLDEN[family][case], sort_keys=True
    )


def interface_coverage_policy(family):
    """Bind only the actual bridge-only exports; no core counterpart is manufactured."""
    names, selectors = _SELECTORS[family]
    return FamilyCoveragePolicy(
        family,
        tuple(
            CoveragePredicate(
                id=f"{family}.{case}",
                capability_id=f"{family}.observe",
                action=f"{family}.observe",
                observation_family="interface-output",
                rust_symbols=names,
                binding_obligation_ids=selectors,
                runtime_operations=names,
                matches=partial(_matches, family, case),
            )
            for case in _GOLDEN[family]
        ),
    )


def _relative(value):
    """Limit authored filesystem entries to simple owned relative paths."""
    return (
        isinstance(value, str)
        and bool(value)
        and not any(c in value for c in "\\\\:")
        and all(part not in {"", ".", ".."} for part in value.split("/"))
    )


def validate_interface_pack(document, root):
    """Validate input-only Markdown or filesystem fixtures before either adapter runs."""
    family = document["familyId"]
    paths = []
    fixture_root = (root / document["fixtureRoot"]).resolve()
    for case in document["scenarios"]:
        reference = case["input"].get("fixtureRef")
        if (
            case["action"] != f"{family}.observe"
            or case["input"] != {"fixtureRef": reference}
            or case["fixtureRefs"] != [reference]
        ):
            raise ValueError("invalid interface scenario input")
        path = (fixture_root / document["fixtures"][reference]).resolve()
        if not path.is_relative_to(fixture_root):
            raise ValueError("interface fixture escapes root")
        fixture = json.loads(path.read_text(encoding="utf-8"))
        if family == "markdown-rendering":
            valid = set(fixture) == {"markdown"} and isinstance(
                fixture["markdown"], str
            )
        else:
            valid = (
                set(fixture) == {"files", "directories", "missing"}
                and type(fixture["missing"]) is bool
                and isinstance(fixture["files"], list)
                and isinstance(fixture["directories"], list)
            )
            valid = (
                valid
                and all(_relative(p) for p in fixture["directories"])
                and all(
                    set(f) == {"path", "content", "modifiedSeconds"}
                    and _relative(f["path"])
                    and isinstance(f["content"], str)
                    and type(f["modifiedSeconds"]) is int
                    and 1 <= f["modifiedSeconds"] <= 2000000000
                    for f in fixture["files"]
                )
            )
        if not valid or not _matches(family, case["id"], case["expected"]):
            raise ValueError("invalid interface fixture or golden output")
        paths.append(path)
    return tuple(paths)
