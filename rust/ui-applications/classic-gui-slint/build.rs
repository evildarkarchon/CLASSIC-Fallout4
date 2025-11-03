//! Build script for Slint UI compilation.
//!
//! This build script compiles the Slint UI files at build time, generating
//! Rust code for the UI components defined in `ui/main.slint`.

fn main() {
    slint_build::compile("ui/main.slint").expect("Failed to compile Slint UI");
}
