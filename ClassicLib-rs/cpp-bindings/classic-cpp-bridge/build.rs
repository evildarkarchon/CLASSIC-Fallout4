#[cfg(windows)]
fn main() {
    cxx_build::bridges([
        "src/types.rs",
        "src/runtime.rs",
        "src/registry.rs",
        "src/yaml.rs",
        "src/config.rs",
        "src/scanner.rs",
        "src/database.rs",
        "src/files.rs",
        "src/scangame.rs",
        "src/game.rs",
        "src/update.rs",
        "src/message.rs",
        "src/perf.rs",
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
