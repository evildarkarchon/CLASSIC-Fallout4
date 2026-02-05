//! Build script for classic-gui - compiles Slint UI files to Rust

fn main() {
    slint_build::compile("ui/main.slint").expect("Slint compilation failed");
}
