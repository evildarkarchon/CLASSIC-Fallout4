//! Source audits over the TUI's own text, for two contracts a compiler cannot see.
//!
//! The first is the shared Tokio runtime rule (`AGENTS.md` rule 5). Every TUI background workflow
//! — including resuming a Local Ignore recovery continuation — must run on the single runtime owned
//! by `classic_shared_core`. A second runtime would give a resumed run a different scheduler from
//! the scan it continues, so this is pinned here rather than left to review.
//!
//! The second is the Vocabulary naming contract: the Rust core crate defining a domain concept owns
//! what that concept is called, and this frontend renders that Display Label rather than keeping a
//! table of its own. It is a source audit rather than a behavior test because a newly written
//! duplicate table produces correct strings on the day it is written and only diverges later — it
//! is behaviorally perfect at exactly the moment it should be rejected. That is not hypothetical:
//! the CLI, the GUI, and the TUI each held a copy of this vocabulary and the copies drifted, the
//! TUI's `local ignore reset` against the core's `Local Ignore reset` among them.
//!
//! Both audits share one design, which the C++ ports in `classic-cli/tests/test_display_label_audit.cpp`
//! and `classic-gui/tests/test_display_label_audit.cpp` copied from the runtime half of this file:
//!
//! * They count occurrences rather than naming functions, so new code inside an audited file is
//!   covered without anyone remembering to extend this file.
//! * Each carries a staleness meta-test that fails when its own source list falls behind — without
//!   one, a hand-written list silently stops checking whatever lands next, which is exactly where a
//!   naming table is most likely to appear.
//!
//! Both lists are written by hand even though the directory could be globbed. That is the trade the
//! CLI port documents: a declared list is reviewable in a diff and lets a failure name the offending
//! file, and the meta-tests are what stop it falling behind the directory.
//! `the_audit_covers_every_declared_workflow_module` fails when `app.rs` declares a workflow module
//! the dispatch list omits, and `the_audit_covers_every_tui_source_file` fails when any file under
//! `src/` is missing from the audited list.
//!
//! Sources are read at run time rather than through `include_str!`, matching what both C++ ports
//! already do with `ifstream`. A compile-time include is only refreshed when cargo decides the file
//! changed, and cargo decides that by timestamp — so any tool that writes a source with a timestamp
//! older than the last build (a backup restore, an archive extraction, a checkout that preserves
//! mtimes) leaves this asserting over bytes that are no longer on disk, and passing. An audit whose
//! subject is the working tree should read the working tree.
//!
//! Sibling `*_tests.rs` modules are deliberately outside the audited set. They legitimately quote
//! settled Display Labels as literals — that is how a wording a ticket decided gets pinned — and
//! they are unit tests of the very modules this audits, not frontend code a user sees.
//!
//! One asymmetry is worth knowing before trusting the naming half. After adoption the TUI names
//! none of the audited enums anywhere in `src/`, because `label()` resolves through a trait and
//! needs no type in scope — so every detector runs over sources that mention nothing, and a broken
//! detector would look exactly like a compliant frontend. `each_detector_catches_the_table_shape_it_exists_for`
//! and `the_detectors_leave_code_that_is_not_a_naming_table_alone` exist for that reason: they feed
//! each detector a synthetic table and a synthetic non-table, so the audit is proven able to fail.

use std::collections::BTreeSet;
use std::fs;
use std::path::{Path, PathBuf};

/// Every TUI source file allowed to dispatch background work.
///
/// A strict subset of [`AUDITED_SOURCES`]: dispatching is a property of the workflow modules and
/// the two entry points, while a naming table can appear anywhere a string reaches the screen.
const DISPATCHING_SOURCES: [&str; 6] = [
    "app.rs",
    "app/backup_workflow.rs",
    "app/results_workflow.rs",
    "app/update_workflow.rs",
    "event.rs",
    "main.rs",
];

/// Every non-test TUI source file, which is the set audited for naming tables.
///
/// Deliberately the whole of `src/` rather than only the modules carrying scan-run presentation
/// today. A contributor who writes a naming table is unlikely to consult this list first, and the
/// files that render a scan run are exactly the ones most likely to grow — restricting the set to
/// the current renderers would leave the next one unaudited from the day it lands.
const AUDITED_SOURCES: [&str; 19] = [
    "app.rs",
    "app/backup_workflow.rs",
    "app/results_workflow.rs",
    "app/update_workflow.rs",
    "event.rs",
    "lib.rs",
    "main.rs",
    "results_markdown.rs",
    "scan_run.rs",
    "state.rs",
    "tabs/articles_tab.rs",
    "tabs/backup_tab.rs",
    "tabs/main_tab.rs",
    "tabs/mod.rs",
    "tabs/results_tab.rs",
    "theme.rs",
    "ui.rs",
    "widgets/mod.rs",
    "widgets/path_input.rs",
];

/// Returns `classic-tui/src/`, the root every listed path is written relative to.
fn source_root() -> PathBuf {
    Path::new(env!("CARGO_MANIFEST_DIR")).join("src")
}

/// Reads one listed source file whole, as it exists on disk right now.
///
/// Panicking on an unreadable path is the point: it is what replaces the compile-time existence
/// check `include_str!` used to give, so a listed file that was renamed or deleted still fails
/// loudly instead of dropping out of the audited set unnoticed.
fn read_source(relative_path: &str) -> String {
    let path = source_root().join(relative_path);
    fs::read_to_string(&path)
        .unwrap_or_else(|error| panic!("{} should be readable: {error}", path.display()))
}

/// The shared deny-list of phrases about a Crash Log Scan Run that no frontend may write.
///
/// One file, read by all four frontend audits, rather than four inline copies. A per-frontend list
/// would put back into the test layer the four-copies drift `classic-scan-presentation` exists to
/// delete: a contributor adding core-owned prose would have to remember four lists, and forgetting
/// one would leave the phrase unenforced in exactly the frontend nobody was looking at.
fn core_owned_phrases_file() -> PathBuf {
    // `CARGO_MANIFEST_DIR` is `ui-applications/classic-tui`, so the repo root is two levels up.
    Path::new(env!("CARGO_MANIFEST_DIR"))
        .join("../../business-logic/classic-scan-presentation/core-owned-phrases.txt")
}

/// Reads the shared deny-list, dropping blank lines and `#` comments.
///
/// Panics on an unreadable file for the same reason [`read_source`] does: an audit that quietly
/// enforces nothing is worse than no audit, because it reads as coverage.
fn core_owned_phrases() -> Vec<String> {
    let path = core_owned_phrases_file();
    let contents = fs::read_to_string(&path)
        .unwrap_or_else(|error| panic!("{} should be readable: {error}", path.display()));
    contents
        .lines()
        .map(str::trim)
        .filter(|line| !line.is_empty() && !line.starts_with('#'))
        .map(str::to_string)
        .collect()
}

/// Every domain enum the TUI presents, each owned by a core crate that supplies both its names.
///
/// The first four are the tables this frontend used to carry. `LogDisposition` and
/// `LogFailureStage` are here because the TUI rendered their prose too, from copies the parent
/// inventory did not count. `InfrastructureErrorStage` never had a table at all — it rendered the
/// Vocabulary *Token* through `Display`, which is an identifier in a sentence rather than a second
/// vocabulary — and now renders its Display Label like the other six.
///
/// The next two arrived with the scan-run vocabulary adoption. `ScanProgressPhase` did carry a
/// table — the four participles the progress line shows — which now resolves through `label()`
/// with the same words. `InstalledYamlDataRole` is named nowhere in `src/`, so it is here purely
/// so that the first frontend code to render a role cannot start by writing a table.
///
/// `CrashLogScanRunStatus` joined them when this frontend adopted `classic-scan-presentation`. It
/// was held back while `format_result` composed the six outcomes into count-bearing sentences of
/// its own and the detail block printed `Run status: <token>`; both are gone, and the status now
/// reaches the user as one Display Label inside a segment core owns.
///
/// The adopter that is *not* here is named in [`DEFERRED_ENUMS`] with its reason.
const AUDITED_ENUMS: [&str; 10] = [
    "InstalledYamlDataProvenance",
    "LocalIgnoreRunState",
    "InstalledYamlDataRunDiagnosticKind",
    "LocalIgnoreResetFailureStage",
    "LogDisposition",
    "LogFailureStage",
    "InfrastructureErrorStage",
    "ScanProgressPhase",
    "InstalledYamlDataRole",
    "CrashLogScanRunStatus",
];

/// The Vocabulary adopter this frontend cannot be audited for yet, and why.
///
/// It is covered by the same naming contract as the ten above and it carries a
/// Display Label, so leaving it out is a statement about this *audit* rather
/// than about the enum. It cannot be added without a false failure today:
///
/// - `LocalIgnoreRecoveryDecision` has no table in this frontend at all. Every
///   match on it selects control flow. It trips only [`arm_body_end`]'s
///   over-read, where a final arm with no successor runs to the end of the
///   enclosing item and swallows an unrelated literal — the deliberate
///   false-positive bias documented on that function.
///
/// Listed rather than merely absent so the omission is data the meta-test below
/// can check, instead of a comment that rots. A contributor moving the name
/// into `AUDITED_ENUMS` deletes it from here, and the meta-test is what tells
/// them both lists have to change together.
const DEFERRED_ENUMS: [&str; 1] = ["LocalIgnoreRecoveryDecision"];

/// The four enums that adopted the Vocabulary naming contract alongside this audit.
///
/// Fixed at the four this frontend was asked to account for, so that "audited or
/// deferred" stays a claim about a known set rather than a tautology over
/// whatever the two lists happen to contain.
const NEWLY_ADOPTED_ENUMS: [&str; 4] = [
    "CrashLogScanRunStatus",
    "ScanProgressPhase",
    "LocalIgnoreRecoveryDecision",
    "InstalledYamlDataRole",
];

#[test]
fn every_newly_adopted_enum_is_either_audited_or_explicitly_deferred() {
    // The stale-list guard for the enum lists, playing the role the recursive
    // directory listing plays for the source lists. Without it, an adopter could
    // be dropped from `AUDITED_ENUMS` and read as never having been in scope.
    for name in NEWLY_ADOPTED_ENUMS {
        assert!(
            AUDITED_ENUMS.contains(&name) || DEFERRED_ENUMS.contains(&name),
            "{name} adopted the Vocabulary naming contract but is neither audited \
             nor listed in DEFERRED_ENUMS with a reason"
        );
    }

    // Both at once would be a contributor who moved a name across and forgot to
    // delete it, leaving a deferral note for something already enforced.
    for name in DEFERRED_ENUMS {
        assert!(
            !AUDITED_ENUMS.contains(&name),
            "{name} is audited now; delete it from DEFERRED_ENUMS and its reason"
        );
        assert!(
            NEWLY_ADOPTED_ENUMS.contains(&name),
            "{name} is deferred but is not one of the adopters this audit tracks"
        );
    }
}

#[test]
fn the_tui_never_constructs_its_own_async_runtime() {
    for name in DISPATCHING_SOURCES {
        let source = read_source(name);
        for forbidden in [
            "Runtime::new",
            "runtime::Builder",
            "#[tokio::main]",
            "block_on(",
        ] {
            assert!(
                !source.contains(forbidden),
                "{name} must not use `{forbidden}`; background work belongs on \
                 classic_shared_core::get_runtime()"
            );
        }
    }
}

#[test]
fn every_tui_spawn_targets_the_shared_runtime() {
    for name in DISPATCHING_SOURCES {
        let source = read_source(name);
        let spawns = source.matches(".spawn(").count();
        let shared_spawns = source.matches("get_runtime().spawn(").count();
        assert_eq!(
            spawns, shared_spawns,
            "{name} spawns {spawns} task(s) but only {shared_spawns} target the shared runtime"
        );
    }
}

#[test]
fn the_audit_covers_every_declared_workflow_module() {
    let app_rs = read_source("app.rs");
    for line in app_rs.lines() {
        let Some(module) = line
            .trim()
            .strip_prefix("mod ")
            .and_then(|rest| rest.strip_suffix(';'))
        else {
            continue;
        };
        // The sibling unit-test module required by AGENTS.md rule 11 is declared the same way but
        // resolves to `app_tests.rs`, not `app/tests.rs`, and dispatches no background work.
        if module == "tests" {
            continue;
        }
        let expected = format!("app/{module}.rs");
        assert!(
            DISPATCHING_SOURCES.contains(&expected.as_str()),
            "app.rs declares `mod {module};` but `{expected}` is not audited here; add it to \
             DISPATCHING_SOURCES so its background work stays on the shared runtime"
        );
    }
}

#[test]
fn local_ignore_recovery_resume_is_dispatched_like_every_other_workflow() {
    let app_rs = read_source("app.rs");
    assert!(
        app_rs.contains("fn resume_local_ignore_recovery"),
        "the recovery resume seam should stay a named function in app.rs"
    );
    assert!(
        app_rs.contains("get_runtime().spawn("),
        "app.rs should dispatch its background work through the shared runtime"
    );
}

#[test]
fn no_tui_source_turns_an_audited_enum_into_a_string_literal() {
    let mut offenders = Vec::new();
    for name in AUDITED_SOURCES {
        let source = read_source(name);
        for enum_name in AUDITED_ENUMS {
            let tables = count_naming_tables(&source, enum_name);
            if tables > 0 {
                offenders.push(format!(
                    "{name} turns {enum_name} into {tables} string literal(s)"
                ));
            }
            // A variant glob is reported on its own because it is not a table — it is the one
            // import that would hide every later table from all three detectors, since the variants
            // it brings in are then spelled bare. Naming the enum costs a contributor nothing and
            // keeps the audit able to see the file at all.
            if source.contains(&format!("{enum_name}::*")) {
                offenders.push(format!(
                    "{name} glob-imports {enum_name}'s variants, which this audit cannot see through"
                ));
            }
        }
    }

    // Accumulated into one assertion rather than one per file: a contributor who reached for tables
    // usually wrote more than one, and failing on the first would report them across as many runs
    // as they wrote.
    assert!(
        offenders.is_empty(),
        "the core crate that owns a domain enum owns its Display Label too; call \
         classic_vocabulary::Vocabulary::label() instead, so the CLI, the GUI, and the TUI cannot \
         disagree about the same outcome:\n  {}",
        offenders.join("\n  ")
    );
}

#[test]
fn no_tui_source_writes_a_sentence_the_presentation_crate_owns() {
    let phrases = core_owned_phrases();
    let mut offenders = Vec::new();
    for name in AUDITED_SOURCES {
        let code = string_literals(&read_source(name));
        for phrase in &phrases {
            if contains(&code, phrase.as_bytes()) {
                offenders.push(format!("{name} writes {phrase:?}"));
            }
        }
    }

    assert!(
        offenders.is_empty(),
        "classic-scan-presentation already states these things about a Crash Log Scan Run; render \
         the display lines it produces instead of restating them here, so a wording fix lands once \
         and reaches every frontend:\n  {}",
        offenders.join("\n  ")
    );
}

#[test]
fn the_shared_deny_list_is_readable_and_not_empty() {
    // The detector loops over the deny-list, so an empty or mislocated list asserts nothing while
    // still reporting green — the "reads as coverage while providing none" failure the detector
    // self-tests below exist to prevent for the naming half. The other three audits carry the same
    // guard against the same file.
    let phrases = core_owned_phrases();
    assert!(
        phrases.len() >= 10,
        "the shared deny-list at {} looks truncated: {} phrase(s)",
        core_owned_phrases_file().display(),
        phrases.len()
    );
    assert!(
        phrases.contains(&"Crash Log Scan Run failed during".to_string()),
        "the shared deny-list no longer carries the phrase the original drift took"
    );
    // No constraint on an entry's shape is asserted any more, and that is deliberate. An earlier
    // version required each entry to contain a space, because the detector searched comment-stripped
    // *code* and a bare word could match an identifier. That constraint was load-bearing only
    // because the detector was reading more than it needed: `string_literals` now yields literals
    // alone, where no identifier can appear, so `succeeded,` — core-owned prose that occurs in
    // ordinary code as `terminal.succeeded, terminal.failed` — is safe to list.
}

/// Returns the contents of every string literal in `source`, one per line, with nothing else.
///
/// Literals rather than comment-stripped code, which is what this scanned first. Prose is only ever
/// a literal, so scanning anything more than literals only adds ways to be wrong — and it was wrong:
/// `succeeded,` is core-owned prose that occurs verbatim in ordinary code as `terminal.succeeded,
/// terminal.failed`. Extracting literals removes that whole class of false positive rather than
/// asking the deny-list to dodge it, and puts this in line with the Python audit, which reads
/// literals off the AST for the same reason.
///
/// Comments never appear, for the reason the CXX parity gate's name scan was fixed: a comment
/// *describing* the drift is not the drift, and this file's own module docs quote the phrases it
/// forbids. Tracking string state is what tells the two apart, and it also stops a `//` inside a
/// path or URL literal from reading as the start of a comment.
///
/// Literals are newline-separated rather than concatenated so two adjacent ones cannot form a
/// phrase neither contains — `"succeeded" ", "` must not read as `succeeded, `.
fn string_literals(source: &str) -> Vec<u8> {
    let bytes = source.as_bytes();
    let mut out = Vec::with_capacity(bytes.len());
    let mut index = 0;
    while index < bytes.len() {
        // A character literal holding a quote — `'"'` or `'\"'`, and the same inside `b'…'` — would
        // otherwise open a string that never closes where the scanner thinks it does, dropping the
        // rest of the file from the audit. That is exactly the "reads as coverage while providing
        // none" failure this file's guards exist to prevent, so it is handled rather than left
        // latent. A lifetime (`&'static str`) has no closing quote two or three bytes along, so it
        // falls through to the ordinary branch untouched.
        if bytes[index] == b'\'' {
            let escaped = bytes.get(index + 1) == Some(&b'\\');
            let close = index + if escaped { 3 } else { 2 };
            if bytes.get(close) == Some(&b'\'') {
                index = close + 1;
                continue;
            }
        }
        // A raw string takes no escapes, so `r"C:\dir\"` ends at its own quote and a `\"` inside it
        // is two characters rather than one. Handled before the ordinary-string branch, which would
        // otherwise read that backslash as an escape and run past the end of the literal.
        if bytes[index] == b'r' {
            let mut hashes = index + 1;
            while bytes.get(hashes) == Some(&b'#') {
                hashes += 1;
            }
            if bytes.get(hashes) == Some(&b'"') {
                let fence = hashes - (index + 1);
                index = hashes + 1;
                while index < bytes.len() {
                    if bytes[index] == b'"'
                        && bytes[index + 1..]
                            .iter()
                            .take(fence)
                            .filter(|byte| **byte == b'#')
                            .count()
                            == fence
                    {
                        index += 1 + fence;
                        break;
                    }
                    out.push(bytes[index]);
                    index += 1;
                }
                out.push(b'\n');
                continue;
            }
        }
        if bytes[index] == b'/' && bytes.get(index + 1) == Some(&b'/') {
            while index < bytes.len() && bytes[index] != b'\n' {
                index += 1;
            }
            continue;
        }
        if bytes[index] == b'/' && bytes.get(index + 1) == Some(&b'*') {
            index += 2;
            // Rust block comments nest, unlike C++'s.
            let mut depth = 1usize;
            while index < bytes.len() && depth > 0 {
                if bytes[index] == b'/' && bytes.get(index + 1) == Some(&b'*') {
                    depth += 1;
                    index += 2;
                } else if bytes[index] == b'*' && bytes.get(index + 1) == Some(&b'/') {
                    depth -= 1;
                    index += 2;
                } else {
                    index += 1;
                }
            }
            continue;
        }
        if bytes[index] == b'"' {
            index += 1;
            while index < bytes.len() {
                if bytes[index] == b'\\' {
                    index += 2;
                    continue;
                }
                if bytes[index] == b'"' {
                    index += 1;
                    break;
                }
                out.push(bytes[index]);
                index += 1;
            }
            out.push(b'\n');
            continue;
        }
        // Ordinary code, which is deliberately dropped rather than collected.
        index += 1;
    }
    out
}

/// Returns whether `haystack` contains `needle`, over bytes so no encoding assumption is needed.
fn contains(haystack: &[u8], needle: &[u8]) -> bool {
    !needle.is_empty()
        && haystack.len() >= needle.len()
        && haystack
            .windows(needle.len())
            .any(|window| window == needle)
}

/// Counts every naming-table shape `source` gives `enum_name`, under any name it is imported by.
///
/// Three detectors, because a naming table has more than one shape. The first two read `match` arms
/// and single lines, which both key on `Name::` and so miss a table whose vocabulary never names a
/// variant at all. The third keys on the signature instead, which is what makes it the one that
/// holds when the strings hide in a lookup container or behind a catch-all arm.
fn count_naming_tables(source: &str, enum_name: &str) -> usize {
    names_for(source, enum_name)
        .iter()
        .map(|name| {
            count_literal_returning_arms(source, name)
                + count_variant_lines_with_literals(source, name)
                + count_literals_in_label_shaped_functions(source, name)
        })
        .sum()
}

/// Returns every spelling `enum_name` can be written as in `source`.
///
/// `use path::Enum as Alias;` renames the type for the rest of the file, and the two detectors that
/// key on `Name::` would then match nothing — the same hole `classic-gui`'s audit closes for C++
/// `using` aliases. Rust needs it more, not less: an alias there is a plain rename with no trace of
/// the original spelling left at the use site.
fn names_for(source: &str, enum_name: &str) -> Vec<String> {
    let renamed = format!("{enum_name} as ");
    let mut names = vec![enum_name.to_string()];
    for line in source.lines() {
        let Some((_, tail)) = line.split_once(&renamed) else {
            continue;
        };
        let alias: String = tail
            .chars()
            .take_while(|character| character.is_alphanumeric() || *character == '_')
            .collect();
        if !alias.is_empty() {
            names.push(alias);
        }
    }
    names
}

#[test]
fn the_audit_covers_every_tui_source_file() {
    // The stale-list guard for the naming-table audit. `AUDITED_SOURCES` is written by hand, so
    // without this a new file under `src/` would be unaudited from the day it lands — and new code
    // is where a naming table is likeliest to appear.
    let audited: BTreeSet<&str> = AUDITED_SOURCES.into_iter().collect();

    let root = source_root();
    let mut present = Vec::new();
    collect_rust_sources(&root, &root, &mut present);

    let mut unaudited: Vec<String> = present
        .into_iter()
        .filter(|path| !audited.contains(path.as_str()))
        .collect();
    unaudited.sort();

    assert!(
        unaudited.is_empty(),
        "add these to audited_sources() so their Display Label handling stays audited: {}",
        unaudited.join(", ")
    );
}

/// Collects every non-test `.rs` file under `directory`, as a `/`-separated path relative to `root`.
///
/// Recursive, because a file added under a future `src/<subdir>/` would otherwise be neither
/// audited nor reported — silently unaudited, which is the one hole the meta-test exists to close.
fn collect_rust_sources(root: &Path, directory: &Path, found: &mut Vec<String>) {
    let entries = fs::read_dir(directory)
        .unwrap_or_else(|error| panic!("{} should be readable: {error}", directory.display()));
    for entry in entries {
        let path = entry.expect("a directory entry should be readable").path();
        if path.is_dir() {
            collect_rust_sources(root, &path, found);
            continue;
        }
        if path.extension().is_none_or(|extension| extension != "rs") {
            continue;
        }
        let Some(file_name) = path.file_name().and_then(|name| name.to_str()) else {
            continue;
        };
        // Sibling unit-test modules quote settled Display Labels on purpose; see the module doc.
        if file_name.ends_with("_tests.rs") {
            continue;
        }
        found.push(relative_slash_path(root, &path));
    }
}

/// Renders `path` relative to `root` with `/` separators, so failures read the same on every OS.
fn relative_slash_path(root: &Path, path: &Path) -> String {
    let relative: PathBuf = path
        .strip_prefix(root)
        .expect("collected paths live under the source root")
        .to_path_buf();
    relative
        .components()
        .map(|component| component.as_os_str().to_string_lossy().into_owned())
        .collect::<Vec<_>>()
        .join("/")
}

/// Counts `match` arms naming `enum_name` whose body contains a string literal.
///
/// Counting rather than naming is deliberate: this never asks whether a particular function exists,
/// so a table written into an audited file under any name is found.
fn count_literal_returning_arms(source: &str, enum_name: &str) -> usize {
    let qualified = format!("{enum_name}::");
    let mut count = 0;
    let mut at = 0;
    while let Some(offset) = source[at..].find(&qualified) {
        let variant_start = at + offset;
        let scan_from = variant_start + qualified.len();
        let arm = &source[variant_start..arm_body_end(source, &qualified, scan_from)];
        if let Some(arrow) = arm.find("=>")
            && arm[arrow..].contains('"')
        {
            count += 1;
        }
        at = scan_from;
    }
    count
}

/// Returns where one `match` arm's body ends.
///
/// An arm runs to the next arm naming the same enum, or to the end of the enclosing item, whichever
/// comes first. The item end is anchored on a newline followed by `}` because rustfmt puts every
/// top-level item's closing brace at column zero, and a table's final arm has no successor to bound
/// it. Over-reading errs toward a false positive, which a contributor sees and can argue with,
/// rather than a false negative, which no one ever sees.
fn arm_body_end(source: &str, qualified: &str, from: usize) -> usize {
    let next_variant = source[from..].find(qualified).map(|at| from + at);
    let item_end = source[from..].find("\n}").map(|at| from + at);
    next_variant
        .into_iter()
        .chain(item_end)
        .min()
        .unwrap_or(source.len())
}

/// Counts non-comment lines naming a variant of `enum_name` beside a later string literal.
///
/// The arm scan cannot see the same table written as an expression or as a lookup container —
/// `if kind == Kind::Parse { "parse" } else { "" }`, or a `[(Kind::Parse, "parse"), ..]` const.
/// Pairing the two on one line catches those shapes without trying to parse Rust.
fn count_variant_lines_with_literals(source: &str, enum_name: &str) -> usize {
    let qualified = format!("{enum_name}::");
    source
        .lines()
        .filter(|line| !line.trim_start().starts_with("//"))
        .filter(|line| {
            line.find(&qualified)
                .is_some_and(|at| line[at..].contains('"'))
        })
        .count()
}

/// Counts string literals inside string-returning functions that take `enum_name`.
///
/// This is the detector that holds when the other two do not. A naming table need not name a
/// variant at all — a `HashMap`, an index into a `const [&str; N]`, or a catch-all `_ => "unknown"`
/// all produce the same drift. What every one of them shares is the shape: a function that takes
/// one of these enums and hands back a string. Nothing in this frontend has a legitimate reason to
/// be that function anymore, because the core already is one.
///
/// Restricting the check to a *string-returning* signature is what keeps it usable: a predicate, a
/// width helper, or a control-flow branch that takes one of these enums is not a naming table and
/// is not counted. It does not distinguish a table from a formatter that takes the enum and returns
/// a wider message — that reads as a false positive, which a contributor sees and can argue with,
/// rather than a false negative, which no one ever sees.
fn count_literals_in_label_shaped_functions(source: &str, enum_name: &str) -> usize {
    let mut count = 0;
    let mut at = 0;
    while let Some(offset) = source[at..].find("fn ") {
        let signature_start = at + offset;
        at = signature_start + "fn ".len();

        let Some(body_start) = find_body_start(source, signature_start) else {
            continue;
        };
        let signature = &source[signature_start..body_start];
        if !signature.contains(enum_name) || !returns_a_string(signature) {
            continue;
        }

        let body = &source[body_start..find_body_end(source, body_start)];
        // Quotes come in pairs, so halving them reports literals rather than delimiters. An escaped
        // quote would inflate this, but the assertion is against zero, so an inflated non-zero
        // count is still a correct verdict.
        count += body.matches('"').count() / 2;
    }
    count
}

/// Returns the offset of the `{` opening a body, or `None` when there is none.
///
/// Stops at `;` so a trait method declaration is never mistaken for a definition.
fn find_body_start(source: &str, from: usize) -> Option<usize> {
    source[from..]
        .find(['{', ';'])
        .map(|offset| from + offset)
        .filter(|at| source.as_bytes()[*at] == b'{')
}

/// Returns the offset one past the `}` closing the body opened at `body_start`.
///
/// Braces are counted naively rather than lexed. Format strings such as `"{}"` carry balanced
/// braces and so cancel out; an unbalanced one would end the body early, which makes the scan read
/// *less* text than it should — so this errs the other way from [`arm_body_end`] and is why the
/// other two detectors exist rather than this one alone.
fn find_body_end(source: &str, body_start: usize) -> usize {
    let mut depth = 0usize;
    for (offset, character) in source[body_start..].char_indices() {
        match character {
            '{' => depth += 1,
            '}' => {
                depth -= 1;
                if depth == 0 {
                    return body_start + offset + 1;
                }
            }
            _ => {}
        }
    }
    source.len()
}

/// A multi-line `match` table inside a function that returns no string, so only the arm scan sees it.
const ARM_SHAPED_TABLE: &str = r#"
fn width(stage: LogFailureStage) -> usize {
    match stage {
        LogFailureStage::Analysis =>
            "analysis".len(),
        LogFailureStage::ReportWrite =>
            "report write".len(),
    }
}
"#;

/// A lookup container, which carries no `=>` and no function at all — only the line scan sees it.
const CONTAINER_SHAPED_TABLE: &str = r#"
const LABELS: [(LogDisposition, &str); 1] = [(LogDisposition::Failed, "failed")];
"#;

/// A table indexed rather than matched, so only the signature scan sees it.
const INDEX_SHAPED_TABLE: &str = r#"
fn label(stage: LogFailureStage) -> &'static str {
    let table = ["analysis", "report write"];
    table[stage as usize]
}
"#;

/// The same table written under a rename, which every detector misses without alias resolution.
const ALIASED_TABLE: &str = r#"
use classic_scanlog_core::scan_run::contract::LogDisposition as Disposition;

fn label(disposition: Disposition) -> Span<'static> {
    Span::raw(match disposition {
        Disposition::Succeeded => "succeeded",
        Disposition::Failed => "failed",
    })
}
"#;

/// A function that takes an audited enum without naming it, which must stay uncounted.
const NOT_A_TABLE: &str = r#"
fn is_terminal(disposition: LogDisposition) -> bool {
    !matches!(disposition, LogDisposition::CancelledBeforeStart)
}
"#;

#[test]
fn each_detector_catches_the_table_shape_it_exists_for() {
    // Without this, every detector could be silently broken and the audit above would stay green
    // forever — a source audit that cannot fail is indistinguishable from no audit at all. Each
    // sample is written to trip exactly one detector, so a regression names the one that broke
    // rather than reporting that "something" stopped working.
    assert_eq!(
        count_literal_returning_arms(ARM_SHAPED_TABLE, "LogFailureStage"),
        2,
        "the arm scan should read both arms of a table whose bodies sit on their own lines"
    );
    assert_eq!(
        count_variant_lines_with_literals(CONTAINER_SHAPED_TABLE, "LogDisposition"),
        1,
        "the line scan should read a lookup container, which has no match arm to find"
    );
    assert_eq!(
        count_literals_in_label_shaped_functions(INDEX_SHAPED_TABLE, "LogFailureStage"),
        2,
        "the signature scan should read a table that names no variant at all"
    );
    assert!(
        count_naming_tables(ALIASED_TABLE, "LogDisposition") > 0,
        "a table written under `use ... as Alias` should still be found"
    );
}

#[test]
fn the_detectors_leave_code_that_is_not_a_naming_table_alone() {
    // The other half of the proof. A detector that answered "table" to everything would also make
    // the audit above green-forever-useless the moment anyone had to weaken it to land a change.
    for enum_name in AUDITED_ENUMS {
        assert_eq!(
            count_naming_tables(NOT_A_TABLE, enum_name),
            0,
            "a predicate over {enum_name} is not a naming table"
        );
    }
}

/// The sentence a frontend would reach for, written as the template it would actually be written as.
///
/// `format!` rather than a verbatim paste, because a template is the shape drift takes in practice:
/// the phrase survives and only the stage is substituted. Matching a phrase rather than a whole
/// sentence is what lets the plain substring test see it.
const REWORDED_SENTENCE: &str = r#"
fn summary(stage: InfrastructureErrorStage, message: &str) -> String {
    format!("Crash Log Scan Run failed during {} - {message}", stage.label())
}
"#;

#[test]
fn the_phrase_detector_catches_the_drift_it_exists_for() {
    // Same proof the naming detectors carry above, for the same reason: the TUI writes none of these
    // phrases now, so a broken phrase detector and a compliant frontend look identical from here.
    let code = string_literals(REWORDED_SENTENCE);
    assert!(
        contains(&code, b"Crash Log Scan Run failed during"),
        "a sentence template reusing a core-owned phrase should be caught"
    );
}

#[test]
fn the_phrase_detector_reads_code_rather_than_comments() {
    // A comment describing the drift is documentation, not the drift — the same false positive the
    // CXX parity gate's name scan hit. This file's own module docs would trip a detector that could
    // not tell the two apart.
    let commented = string_literals(
        "// Crash Log Scan Run failed during is core's to say.\n\
         /* Crash Log Scan Run failed during, again. */\nlet x = 1;\n",
    );
    assert!(!contains(&commented, b"Crash Log Scan Run failed during"));

    // The converse: a literal writing it is the drift, and a raw string is still a literal.
    let raw = string_literals("let s = r\"Crash Log Scan Run failed during\";\n");
    assert!(contains(&raw, b"Crash Log Scan Run failed during"));
}

#[test]
fn the_phrase_detector_reads_literals_rather_than_the_code_around_them() {
    // `succeeded,` is core-owned prose and also, character for character, an ordinary argument list.
    // A detector that searched code rather than literals reported the Qt GUI's
    // `emit finished(terminal.total, terminal.succeeded, terminal.failed, ...)` as drift, which is
    // how this scanner came to extract literals instead of merely stripping comments.
    let code = string_literals("emit finished(terminal.succeeded, terminal.failed);\n");
    assert!(!contains(&code, b"succeeded,"));

    let written = string_literals("let s = \"3 succeeded, 4 failed\";\n");
    assert!(contains(&written, b"succeeded,"));

    // Two adjacent literals must not fuse into a phrase neither contains, or the separator this
    // relies on is doing nothing.
    let adjacent = string_literals("let s = concat!(\"succeeded\", \", failed\");\n");
    assert!(!contains(&adjacent, b"succeeded,"));
}

#[test]
fn the_phrase_detector_survives_a_character_literal_holding_a_quote() {
    // A `'"'` read as a string opener would swallow everything up to the next quote, taking the
    // phrase after it out of the audit — a silent hole rather than a failure. No TUI source
    // contains one today, which is precisely why it needs a test rather than a reader's vigilance.
    let code = string_literals(
        "let quote = '\"';\nlet escaped = '\\'';\nlet s = \"Crash Log Scan Run failed during\";\n",
    );
    assert!(contains(&code, b"Crash Log Scan Run failed during"));

    // A lifetime is not a character literal and must not be consumed as one.
    let lifetime = string_literals(
        "fn label(s: &'static str) -> &'static str { \"Crash Log Scan recovery failed\" }\n",
    );
    assert!(contains(&lifetime, b"Crash Log Scan recovery failed"));
}

#[test]
fn the_phrase_detector_does_not_mistake_a_literal_slash_for_a_comment() {
    // A path or URL literal containing `//` must not read as the start of a comment, or everything
    // after it on that line silently leaves the audited text — including a phrase written there.
    let code = string_literals(
        "let url = \"https://example.invalid\"; let s = \"Crash Log Scan Run failed during\";\n",
    );
    assert!(contains(&code, b"Crash Log Scan Run failed during"));
}

#[test]
fn the_phrase_detector_leaves_compliant_rendering_alone() {
    // The other half of the proof. Rendering a segment core produced is the correct shape and must
    // stay quiet, or the audit becomes noise a contributor learns to work around.
    let compliant = string_literals(
        "fn render(line: &DisplayLine) -> String {\n\
             line.segments.iter().map(segment_text).collect::<Vec<_>>().join(\" \")\n\
         }\n",
    );
    for phrase in core_owned_phrases() {
        assert!(
            !contains(&compliant, phrase.as_bytes()),
            "concatenating core's own segments should not read as writing {phrase:?}"
        );
    }
}

/// Returns whether `signature`'s return type is text the terminal can render.
///
/// Only the text after `->` is examined, so a `&str` *parameter* never reads as a string return.
///
/// `Span`, `Line`, and `Text` are ratatui's own text types and are here for the reason the GUI
/// audit had to add `QString`: the natural label shape in a frontend is whatever that frontend
/// draws with, and an allowlist of only `str`/`String` matches nothing in a toolkit that wraps its
/// strings. `Cow<'_, str>` is already covered by `str`.
fn returns_a_string(signature: &str) -> bool {
    const TEXT_RETURNS: [&str; 5] = ["str", "String", "Span", "Line", "Text"];
    signature.split_once("->").is_some_and(|(_, returns)| {
        TEXT_RETURNS
            .iter()
            .any(|text_type| returns.contains(text_type))
    })
}
