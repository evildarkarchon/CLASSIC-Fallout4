#[cxx::bridge(namespace = "classic::struct_fix")]
mod ffi {
    struct PersonDto {
        name: String,
        age: u32,
        tags: Vec<String>,
    }
    extern "Rust" {
        fn make_person(name: &str, age: u32) -> PersonDto;
    }
}
