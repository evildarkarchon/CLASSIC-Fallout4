#[cfg(windows)]
fn main() {
    cxx_build::bridges([
        "src/simple.rs",
        "src/struct_ffi.rs",
        "src/enum_ffi.rs",
        "src/opaque_ffi.rs",
        "src/mixed_ffi.rs",
    ])
    .include("include")
    .std("c++17")
    .compile("fake-bridge");
}

#[cfg(not(windows))]
fn main() {}
