//! Build script for classic-gui - compiles Slint UI files to Rust

fn main() {
    let config = slint_build::CompilerConfiguration::new()
        .with_style("fluent-dark".into());

    slint_build::compile_with_config("ui/main.slint", config)
        .expect("Slint compilation failed");
}
