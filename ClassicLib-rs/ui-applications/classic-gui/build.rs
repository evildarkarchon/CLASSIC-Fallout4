//! Build script for classic-gui
//!
//! Compiles Slint UI files to Rust and embeds Windows resources (icon, manifest)
//! via `tauri-winres`.

fn main() {
    // Compile Slint UI
    let config = slint_build::CompilerConfiguration::new().with_style("fluent-dark".into());

    slint_build::compile_with_config("ui/main.slint", config).expect("Slint compilation failed");

    // Embed Windows resources: application icon and manifest
    #[cfg(target_os = "windows")]
    {
        let mut res = tauri_winres::WindowsResource::new();
        res.set_icon("assets/CLASSIC.ico");
        res.set_manifest_file("assets/classic-gui.manifest");
        res.compile().expect("Failed to compile Windows resources");
    }
}
