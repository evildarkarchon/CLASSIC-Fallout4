use super::*;
use pyo3::Python;

#[test]
fn test_pydict_to_indexmap_str() {
    // PyO3 0.27: use Python::attach with closure
    Python::attach(|py| {
        let dict = PyDict::new(py);
        dict.set_item("key1", "value1").unwrap();
        dict.set_item("key2", "value2").unwrap();

        let result = pydict_to_indexmap_str(&dict).unwrap();
        assert_eq!(result.len(), 2);
        assert_eq!(result.get("key1"), Some(&"value1".to_string()));
        assert_eq!(result.get("key2"), Some(&"value2".to_string()));

        // Verify insertion order preserved
        let keys: Vec<_> = result.keys().collect();
        assert_eq!(keys, vec!["key1", "key2"]);
    });
}

#[test]
fn test_pydict_to_indexmap_str_optional_some() {
    Python::attach(|py| {
        let dict = PyDict::new(py);
        dict.set_item("key", "value").unwrap();

        let result = pydict_to_indexmap_str_optional(Some(&dict));
        assert_eq!(result.len(), 1);
        assert_eq!(result.get("key"), Some(&"value".to_string()));
    });
}

#[test]
fn test_pydict_to_indexmap_str_optional_none() {
    let result = pydict_to_indexmap_str_optional(None);
    assert!(result.is_empty());
}

#[test]
fn test_pydict_to_indexmap_vecstr() {
    Python::attach(|py| {
        let dict = PyDict::new(py);
        let list = pyo3::types::PyList::new(py, ["a", "b", "c"]).unwrap();
        dict.set_item("key", list).unwrap();

        let result = pydict_to_indexmap_vecstr(&dict).unwrap();
        assert_eq!(result.len(), 1);
        assert_eq!(
            result.get("key"),
            Some(&vec!["a".to_string(), "b".to_string(), "c".to_string()])
        );
    });
}
