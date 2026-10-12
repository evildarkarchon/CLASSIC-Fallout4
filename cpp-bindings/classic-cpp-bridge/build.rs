#[cfg(windows)]
fn main() {
    cxx_build::bridges([
        "src/runtime.rs",
        "src/registry.rs",
        "src/settings.rs",
        "src/shared.rs",
        "src/config.rs",
        "src/scanner.rs",
        "src/files.rs",
        "src/scangame.rs",
        "src/xse.rs",
        "src/path.rs",
        "src/web.rs",
        "src/update.rs",
        "src/message.rs",
        "src/markdown.rs",
    ])
    .include("include")
    .std("c++17")
    .compile("classic-cpp-bridge");

    println!("cargo:rerun-if-changed=src/");
}

#[cfg(not(windows))]
fn main() {
    println!("cargo:rerun-if-changed=src/");
}
