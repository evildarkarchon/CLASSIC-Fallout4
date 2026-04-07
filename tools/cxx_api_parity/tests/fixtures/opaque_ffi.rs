#[cxx::bridge(namespace = "classic::opaque_fix")]
mod ffi {
    extern "Rust" {
        type DataStore;
        fn data_store_new() -> Box<DataStore>;
        fn data_store_get(store: &DataStore, key: &str) -> String;
    }
}
