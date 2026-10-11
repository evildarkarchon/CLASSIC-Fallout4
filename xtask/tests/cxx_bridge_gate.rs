//! Fixture-tree tests for `cargo xtask cxx-bridge-gate`, driven through
//! `cxx_bridge_gate::run` (the subcommand seam).

mod common;

use common::FixtureRepo;
use xtask::{Outcome, cxx_bridge_gate};

/// Runs the gate over `repo` and returns its findings rendered as
/// `path:line: rule: message` lines (empty on a pass).
fn findings(repo: &FixtureRepo) -> Vec<String> {
    match cxx_bridge_gate::run(&repo.root(), cxx_bridge_gate::Args::default()).expect("gate runs") {
        Outcome::Pass { .. } => Vec::new(),
        Outcome::Fail { findings, .. } => findings.iter().map(ToString::to_string).collect(),
    }
}

/// A bridge with two functions in `classic::m`, declared on lines 4 and 5.
const TWO_FNS: &str = r#"#[cxx::bridge(namespace = "classic::m")]
mod ffi {
    extern "Rust" {
        fn used() -> i32;
        fn unused() -> i32;
    }
}
"#;

#[test]
fn qualified_reference_keeps_a_function_and_the_rest_are_orphans() {
    let repo = FixtureRepo::cxx()
        .bridge("m.rs", TWO_FNS)
        .cli("main.cpp", "int main() { return classic::m::used(); }\n");

    assert_eq!(
        findings(&repo),
        [
            "cpp-bindings/classic-cpp-bridge/src/m.rs:5: orphan-export: \
          function classic::m::unused has no caller in classic-cli/src or classic-gui/src"
        ]
    );
}

/// The finding for an uncalled function declared at `file:line`.
fn orphan_fn(file_line: &str, qualified: &str) -> String {
    format!(
        "cpp-bindings/classic-cpp-bridge/src/{file_line}: orphan-export: \
         function {qualified} has no caller in classic-cli/src or classic-gui/src"
    )
}

/// The finding for an unreachable type declared at `file:line`.
fn orphan_type(file_line: &str, kind: &str, qualified: &str) -> String {
    format!(
        "cpp-bindings/classic-cpp-bridge/src/{file_line}: orphan-export: \
         {kind} {qualified} is not reachable from any surviving function"
    )
}

/// The finding for a refused reference form at a frontend `path:line`.
fn unsupported(path_line: &str, form: &str) -> String {
    format!(
        "{path_line}: unsupported-reference-form: unsupported reference form `{form}`; \
         reference bridge exports only as classic::<module>::name or <alias>::name with \
         `namespace <alias> = classic::<module>;`"
    )
}

#[test]
fn namespace_alias_reference_keeps_functions_in_any_header_extension() {
    let repo = FixtureRepo::cxx().bridge("m.rs", TWO_FNS).gui(
        "workers/worker.hpp",
        "namespace mm = classic::m;\ninline int both() { return mm::used() + mm::unused(); }\n",
    );

    assert_eq!(findings(&repo), Vec::<String>::new());
}

#[test]
fn global_qualification_is_the_same_qualified_form() {
    let repo = FixtureRepo::cxx().bridge("m.rs", TWO_FNS).gui(
        "a.h",
        "namespace mm = ::classic::m;\nint f() { return ::classic::m::used() + mm::unused(); }\n",
    );

    assert_eq!(findings(&repo), Vec::<String>::new());
}

#[test]
fn using_directives_and_declarations_on_a_bridge_namespace_are_rejected() {
    let repo = FixtureRepo::cxx().bridge("m.rs", TWO_FNS).cli(
        "a.cpp",
        "#include <classic_cxx_bridge/m.h>\n\
         using namespace classic::m;\n\
         using classic::m::used;\n\
         namespace mm = classic::m;\n\
         using namespace mm;\n\
         int f() { return used() + unused(); }\n",
    );

    assert_eq!(
        findings(&repo),
        [
            unsupported("classic-cli/src/a.cpp:2", "using namespace classic::m"),
            unsupported("classic-cli/src/a.cpp:3", "using classic::m::used"),
            unsupported("classic-cli/src/a.cpp:5", "using namespace mm"),
            orphan_fn("m.rs:4", "classic::m::used"),
            orphan_fn("m.rs:5", "classic::m::unused"),
        ]
    );
}

#[test]
fn reopening_aliasing_an_alias_and_relative_lookup_are_rejected() {
    let repo = FixtureRepo::cxx().bridge("m.rs", TWO_FNS).gui(
        "a.cpp",
        "namespace classic::m { int extra(); }\n\
         namespace mm = classic::m;\n\
         namespace again = mm;\n\
         namespace classic::gui {\n\
         int f() { return m::used(); }\n\
         }\n\
         int g() { return classic::m::used() + classic::m::unused(); }\n",
    );

    assert_eq!(
        findings(&repo),
        [
            unsupported("classic-gui/src/a.cpp:1", "namespace classic::m"),
            unsupported("classic-gui/src/a.cpp:3", "namespace again = mm"),
            unsupported(
                "classic-gui/src/a.cpp:5",
                "m::used (relative lookup without a namespace alias)"
            ),
        ]
    );
}

#[test]
fn frontend_owned_classic_namespaces_and_type_aliases_are_not_rejected() {
    let repo = FixtureRepo::cxx().bridge("m.rs", TWO_FNS).gui(
        "a.cpp",
        "namespace classic::gui { int label(); }\n\
         using classic::gui::label;\n\
         using namespace classic::gui;\n\
         using Value = classic::m::Value;\n\
         int f() { return classic::toQString(label()) + classic::m::used() + classic::m::unused(); }\n",
    );

    assert_eq!(findings(&repo), Vec::<String>::new());
}

#[test]
fn references_inside_comments_and_string_literals_do_not_count() {
    let repo = FixtureRepo::cxx().bridge("m.rs", TWO_FNS).cli(
        "a.cpp",
        "// classic::m::used(); using namespace classic::m;\n\
         /* classic::m::unused();\n\
            using classic::m::used; */\n\
         const char* a = \"classic::m::used()\";\n\
         const char* b = R\"(using namespace classic::m;)\";\n\
         char c = ':';\n",
    );

    assert_eq!(
        findings(&repo),
        [
            orphan_fn("m.rs:4", "classic::m::used"),
            orphan_fn("m.rs:5", "classic::m::unused"),
        ]
    );
}

#[test]
fn callers_outside_the_production_src_trees_do_not_count() {
    let call = "int f() { return classic::m::used() + classic::m::unused(); }\n";
    let repo = FixtureRepo::cxx()
        .bridge("m.rs", TWO_FNS)
        .file("classic-cli/tests/test_m.cpp", call)
        .file(
            "classic-cli/tests/conformance/classic_cxx_m_conformance.h",
            call,
        )
        .file("classic-gui/tests/test_m.cpp", call)
        .file("benches/m_bench.cpp", call);

    assert_eq!(
        findings(&repo),
        [
            orphan_fn("m.rs:4", "classic::m::used"),
            orphan_fn("m.rs:5", "classic::m::unused"),
        ]
    );
}

#[test]
fn types_survive_only_by_reachability_from_surviving_functions() {
    let bridge = r#"#[cxx::bridge(namespace = "classic::m")]
mod ffi {
    struct Outer {
        inner: Vec<Inner>,
    }
    struct Inner {
        kind: Kind,
    }
    enum Kind {
        A,
    }
    struct Named {
        x: i32,
    }
    struct OnlyFromOrphan {
        x: i32,
    }
    extern "Rust" {
        type Handle;
        type Unused;
        fn make(handle: &Handle) -> Result<Outer>;
        fn unused() -> OnlyFromOrphan;
    }
}
"#;
    // `Named` and `OnlyFromOrphan` are spelled out by frontend code, which
    // does not keep a type alive.
    let repo = FixtureRepo::cxx().bridge("m.rs", bridge).gui(
        "a.cpp",
        "void f(const classic::m::Handle& h) {\n\
         auto outer = classic::m::make(h);\n\
         classic::m::Named named{};\n\
         using Alias = classic::m::OnlyFromOrphan;\n\
         }\n",
    );

    assert_eq!(
        findings(&repo),
        [
            orphan_type("m.rs:12", "struct", "classic::m::Named"),
            orphan_type("m.rs:15", "struct", "classic::m::OnlyFromOrphan"),
            orphan_type("m.rs:20", "opaque type", "classic::m::Unused"),
            orphan_fn("m.rs:22", "classic::m::unused"),
        ]
    );
}

#[test]
fn extern_cpp_items_are_excluded_but_their_signatures_root_types() {
    let bridge = r#"#[cxx::bridge(namespace = "classic::m")]
mod ffi {
    struct Event {
        phase: Phase,
    }
    enum Phase {
        Start,
    }
    struct Delivery {
        accepted: bool,
    }
    unsafe extern "C++" {
        include!("classic_cxx_bridge/observer.h");
        type Observer;
        fn on_event(self: &Observer, event: &Event) -> Delivery;
    }
    extern "Rust" {
        unsafe fn run(observer: *const Observer) -> i32;
    }
}
"#;
    let repo = FixtureRepo::cxx().bridge("m.rs", bridge).cli(
        "a.cpp",
        "int f(const Observer* o) { return classic::m::run(o); }\n",
    );

    assert_eq!(findings(&repo), Vec::<String>::new());
}

#[test]
fn every_bridge_in_a_file_is_found_and_doc_comment_text_is_not_a_bridge() {
    let bridges = r#"//! This crate mirrors enums across `#[cxx::bridge]` modules.

/// Not a bridge: #[cxx::bridge(namespace = "classic::ghost")]
#[cxx::bridge(namespace = "classic::a")]
mod first {
    extern "Rust" {
        fn same_name() -> i32;
    }
}

mod outer {
    #[cxx::bridge(namespace = "classic::b")]
    mod second {
        extern "Rust" {
            fn same_name() -> i32;
        }
    }
}
"#;
    let repo = FixtureRepo::cxx().bridge("both.rs", bridges).gui(
        "a.cpp",
        "int f() { return classic::a::same_name() + classic::ghost::same_name(); }\n",
    );

    assert_eq!(
        findings(&repo),
        [orphan_fn("both.rs:15", "classic::b::same_name")]
    );
}

#[test]
fn the_namespace_comes_from_the_attribute_not_the_file_name() {
    let bridge = r#"#[cxx::bridge(namespace = "classic::other")]
mod ffi {
    extern "Rust" {
        fn f() -> i32;
    }
}
"#;
    let by_file_name = FixtureRepo::cxx()
        .bridge("stem.rs", bridge)
        .cli("a.cpp", "int g() { return classic::stem::f(); }\n");
    assert_eq!(
        findings(&by_file_name),
        [orphan_fn("stem.rs:4", "classic::other::f")]
    );

    let by_attribute = FixtureRepo::cxx()
        .bridge("stem.rs", bridge)
        .cli("a.cpp", "int g() { return classic::other::f(); }\n");
    assert_eq!(findings(&by_attribute), Vec::<String>::new());
}

#[test]
fn a_passing_run_summarises_what_was_checked() {
    let repo = FixtureRepo::cxx().bridge("m.rs", TWO_FNS).cli(
        "a.cpp",
        "int f() { return classic::m::used() + classic::m::unused(); }\n",
    );

    let outcome = cxx_bridge_gate::run(&repo.root(), cxx_bridge_gate::Args::default()).unwrap();
    assert_eq!(
        outcome,
        Outcome::Pass {
            summary: "cxx-bridge-gate: every export has a production caller \
                      (2 exports in 1 bridge modules, 1 frontend files scanned)"
                .into()
        }
    );
}

#[test]
fn a_bridge_without_a_namespace_or_a_missing_tree_is_an_operational_error() {
    let no_namespace = FixtureRepo::cxx().bridge("m.rs", "#[cxx::bridge]\nmod ffi {}\n");
    let error =
        cxx_bridge_gate::run(&no_namespace.root(), cxx_bridge_gate::Args::default()).unwrap_err();
    assert!(error.to_string().contains("m.rs:2"), "{error:#}");

    let no_bridges = FixtureRepo::cxx();
    assert!(cxx_bridge_gate::run(&no_bridges.root(), cxx_bridge_gate::Args::default()).is_err());

    let no_frontends = FixtureRepo::empty().bridge("m.rs", TWO_FNS);
    assert!(cxx_bridge_gate::run(&no_frontends.root(), cxx_bridge_gate::Args::default()).is_err());
}
