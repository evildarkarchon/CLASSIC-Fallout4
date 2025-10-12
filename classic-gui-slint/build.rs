// Build script for Slint UI compilation
fn main() {
    slint_build::compile("ui/main.slint").expect("Failed to compile Slint UI");
}