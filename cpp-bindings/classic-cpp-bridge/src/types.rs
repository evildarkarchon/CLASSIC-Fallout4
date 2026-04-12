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
mod tests {
    use super::*;

    #[test]
    fn test_string_map_construction() {
        let mut map = IndexMap::new();
        map.insert("key1".to_string(), "value1".to_string());
        map.insert("key2".to_string(), "value2".to_string());
        let sm = StringMap::new(map);
        assert_eq!(string_map_len(&sm), 2);
        assert!(!string_map_is_empty(&sm));
    }

    #[test]
    fn test_string_map_get_existing() {
        let mut map = IndexMap::new();
        map.insert("hello".to_string(), "world".to_string());
        let sm = StringMap::new(map);
        assert_eq!(string_map_get(&sm, "hello"), "world");
    }

    #[test]
    fn test_string_map_get_missing() {
        let sm = StringMap::new(IndexMap::new());
        assert_eq!(string_map_get(&sm, "missing"), "");
    }

    #[test]
    fn test_string_map_contains() {
        let mut map = IndexMap::new();
        map.insert("exists".to_string(), "yes".to_string());
        let sm = StringMap::new(map);
        assert!(string_map_contains(&sm, "exists"));
        assert!(!string_map_contains(&sm, "nope"));
    }

    #[test]
    fn test_string_map_keys_values() {
        let mut map = IndexMap::new();
        map.insert("a".to_string(), "1".to_string());
        map.insert("b".to_string(), "2".to_string());
        let sm = StringMap::new(map);
        assert_eq!(string_map_keys(&sm), vec!["a", "b"]);
        assert_eq!(string_map_values(&sm), vec!["1", "2"]);
    }

    #[test]
    fn test_string_map_empty() {
        let sm = StringMap::new(IndexMap::new());
        assert!(string_map_is_empty(&sm));
        assert_eq!(string_map_len(&sm), 0);
        assert!(string_map_keys(&sm).is_empty());
        assert!(string_map_values(&sm).is_empty());
    }

    #[test]
    fn test_string_map_from_hashmap() {
        let mut hm = std::collections::HashMap::new();
        hm.insert("key".to_string(), "val".to_string());
        let sm = StringMap::from_hashmap(hm);
        assert_eq!(string_map_get(&sm, "key"), "val");
    }

    #[test]
    fn test_string_vec_map_construction() {
        let mut map = IndexMap::new();
        map.insert(
            "patterns".to_string(),
            vec!["a".to_string(), "b".to_string()],
        );
        let svm = StringVecMap::new(map);
        assert_eq!(string_vec_map_len(&svm), 1);
        assert!(!string_vec_map_is_empty(&svm));
    }

    #[test]
    fn test_string_vec_map_get_existing() {
        let mut map = IndexMap::new();
        map.insert(
            "stack".to_string(),
            vec!["frame1".to_string(), "frame2".to_string()],
        );
        let svm = StringVecMap::new(map);
        assert_eq!(string_vec_map_get(&svm, "stack"), vec!["frame1", "frame2"]);
    }

    #[test]
    fn test_string_vec_map_get_missing() {
        let svm = StringVecMap::new(IndexMap::new());
        let result = string_vec_map_get(&svm, "missing");
        assert!(result.is_empty());
    }

    #[test]
    fn test_string_vec_map_contains() {
        let mut map = IndexMap::new();
        map.insert("key".to_string(), vec!["val".to_string()]);
        let svm = StringVecMap::new(map);
        assert!(string_vec_map_contains(&svm, "key"));
        assert!(!string_vec_map_contains(&svm, "other"));
    }

    #[test]
    fn test_string_vec_map_keys() {
        let mut map = IndexMap::new();
        map.insert("x".to_string(), vec![]);
        map.insert("y".to_string(), vec![]);
        let svm = StringVecMap::new(map);
        assert_eq!(string_vec_map_keys(&svm), vec!["x", "y"]);
    }

    #[test]
    fn test_string_vec_map_empty() {
        let svm = StringVecMap::new(IndexMap::new());
        assert!(string_vec_map_is_empty(&svm));
        assert_eq!(string_vec_map_len(&svm), 0);
    }
}
