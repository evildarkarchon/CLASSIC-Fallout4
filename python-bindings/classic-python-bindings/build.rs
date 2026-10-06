//! Build-script metadata for `classic-update-py` test harnesses.

/// Embed an explicit Windows UAC manifest into crate test executables.
///
/// Cargo names this crate's Rust test harness after the library target, so
/// the generated `classic_update-*.exe` contains the UAC installer keyword
/// `update`. Without a requested-execution-level manifest, Windows can treat
/// the harness as an updater and refuse to launch it without elevation.
fn main() {
    println!("cargo:rerun-if-changed=build.rs");

    if std::env::var_os("CARGO_CFG_WINDOWS").is_some()
        && std::env::var("CARGO_CFG_TARGET_ENV").is_ok_and(|env| env == "msvc")
    {
        println!("cargo:rustc-link-arg=/MANIFEST:EMBED");
        println!("cargo:rustc-link-arg=/MANIFESTUAC:level='asInvoker'");
    }
}
