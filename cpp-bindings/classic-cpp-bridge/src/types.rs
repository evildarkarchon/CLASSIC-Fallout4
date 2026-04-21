//! Shared collection wrappers for CXX FFI.
//!
//! CXX cannot directly represent associative containers (HashMap, IndexMap).
//! This module provides opaque wrapper types with accessor functions that
//! C++ can use to iterate and query map contents.

use indexmap::IndexMap;

/// Opaque wrapper around `IndexMap<String, String>` for CXX FFI.
///
/// Provides accessor functions since CXX cannot represent associative containers.
pub struct StringMap {
    inner: IndexMap<String, String>,
}

/// Opaque wrapper around `IndexMap<String, Vec<String>>` for CXX FFI.
///
/// Used for suspect stack patterns and other multi-value maps.
pub struct StringVecMap {
    inner: IndexMap<String, Vec<String>>,
}

impl StringMap {
    pub fn new(inner: IndexMap<String, String>) -> Self {
        Self { inner }
    }

    pub fn from_hashmap(map: std::collections::HashMap<String, String>) -> Self {
        Self {
            inner: map.into_iter().collect(),
        }
    }
}

impl StringVecMap {
    pub fn new(inner: IndexMap<String, Vec<String>>) -> Self {
        Self { inner }
    }
}

// ── CXX bridge functions (called from C++) ──────────────────────────

fn string_map_get(map: &StringMap, key: &str) -> String {
    map.inner.get(key).cloned().unwrap_or_default()
}

fn string_map_contains(map: &StringMap, key: &str) -> bool {
    map.inner.contains_key(key)
}

fn string_map_keys(map: &StringMap) -> Vec<String> {
    map.inner.keys().cloned().collect()
}

fn string_map_values(map: &StringMap) -> Vec<String> {
    map.inner.values().cloned().collect()
}

fn string_map_len(map: &StringMap) -> usize {
    map.inner.len()
}

fn string_map_is_empty(map: &StringMap) -> bool {
    map.inner.is_empty()
}

fn string_vec_map_get(map: &StringVecMap, key: &str) -> Vec<String> {
    map.inner.get(key).cloned().unwrap_or_default()
}

fn string_vec_map_contains(map: &StringVecMap, key: &str) -> bool {
    map.inner.contains_key(key)
}

fn string_vec_map_keys(map: &StringVecMap) -> Vec<String> {
    map.inner.keys().cloned().collect()
}

fn string_vec_map_len(map: &StringVecMap) -> usize {
    map.inner.len()
}

fn string_vec_map_is_empty(map: &StringVecMap) -> bool {
    map.inner.is_empty()
}

#[cxx::bridge(namespace = "classic::types")]
mod ffi {
    extern "Rust" {
        // Opaque types
        type StringMap;
        type StringVecMap;

        // StringMap accessors
        fn string_map_get(map: &StringMap, key: &str) -> String;
        fn string_map_contains(map: &StringMap, key: &str) -> bool;
        fn string_map_keys(map: &StringMap) -> Vec<String>;
        fn string_map_values(map: &StringMap) -> Vec<String>;
        fn string_map_len(map: &StringMap) -> usize;
        fn string_map_is_empty(map: &StringMap) -> bool;

        // StringVecMap accessors
        fn string_vec_map_get(map: &StringVecMap, key: &str) -> Vec<String>;
        fn string_vec_map_contains(map: &StringVecMap, key: &str) -> bool;
        fn string_vec_map_keys(map: &StringVecMap) -> Vec<String>;
        fn string_vec_map_len(map: &StringVecMap) -> usize;
        fn string_vec_map_is_empty(map: &StringVecMap) -> bool;
    }
}

#[cfg(test)]
#[path = "types_tests.rs"]
mod tests;
