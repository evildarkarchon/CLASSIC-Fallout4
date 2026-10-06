//! Build-script metadata for the `classic-python-bindings` test harnesses.

/// Embed an explicit Windows UAC manifest into crate test executables.
///
/// Carried over from the retired `classic-update-py` crate, whose test
/// harness was named after its library target (`classic_update-*.exe`) and so
/// contained the UAC installer keyword `update`. Without a
/// requested-execution-level manifest, Windows can treat such an executable
/// as an updater and refuse to launch it without elevation. The one adapter's
/// harness (`_native-*.exe`) no longer carries that keyword, but the manifest
/// keeps any test or bench executable whose name does from tripping it.
fn main() {
    println!("cargo:rerun-if-changed=build.rs");

    if std::env::var_os("CARGO_CFG_WINDOWS").is_some()
        && std::env::var("CARGO_CFG_TARGET_ENV").is_ok_and(|env| env == "msvc")
    {
        println!("cargo:rustc-link-arg=/MANIFEST:EMBED");
        println!("cargo:rustc-link-arg=/MANIFESTUAC:level='asInvoker'");
    }
}
