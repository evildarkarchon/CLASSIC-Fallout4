#[cxx::bridge(namespace = "classic::simple")]
mod ffi {
    extern "Rust" {
        fn simple_hello(name: &str) -> String;
        fn simple_add(a: u32, b: u32) -> u32;
    }
}
