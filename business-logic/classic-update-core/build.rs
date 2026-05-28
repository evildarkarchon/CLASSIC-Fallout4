//! Build-script metadata for `classic-update-core` test harnesses.

/// Embed an explicit Windows UAC manifest into crate test executables.
///
/// Cargo names Rust test harnesses after the package, so this crate's
/// generated `classic_update_core-*.exe` contains the UAC installer keyword
/// `update`. Without a requested-execution-level manifest, Windows can treat
/// the harness as an updater and refuse to launch it without elevation. The
/// production crate is an `rlib`, so these arguments only affect linkable
/// harnesses/binaries that Cargo asks rustc to produce.
fn main() {
    println!("cargo:rerun-if-changed=build.rs");

    if std::env::var_os("CARGO_CFG_WINDOWS").is_some()
        && std::env::var("CARGO_CFG_TARGET_ENV").is_ok_and(|env| env == "msvc")
    {
        println!("cargo:rustc-link-arg=/MANIFEST:EMBED");
        println!("cargo:rustc-link-arg=/MANIFESTUAC:level='asInvoker'");
    }
}
