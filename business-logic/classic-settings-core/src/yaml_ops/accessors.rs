//! Dot-path accessors and typed YAML extractors.

use super::error::YamlError;
use super::operations::YamlOperations;
use indexmap::IndexMap;
use std::collections::HashMap;
use yaml_rust2::Yaml;

fn navigate<'a>(root: &'a Yaml, key_path: &str) -> Option<&'a Yaml> {
    let mut current = root;
    for key in key_path.split('.') {
        let Yaml::Hash(hash) = current else {
            return None;
        };
        current = hash.get(&Yaml::String(key.to_string()))?;
    }
    Some(current)
}

fn string_pairs(map: &yaml_rust2::yaml::Hash) -> impl Iterator<Item = (String, String)> + '_ {
    map.iter()
        .filter_map(|(k, v)| match (k.as_str(), v.as_str()) {
            (Some(key), Some(value)) => Some((key.to_string(), value.to_string())),
            _ => None,
        })
}

fn string_vec_pairs(
    map: &yaml_rust2::yaml::Hash,
) -> impl Iterator<Item = (String, Vec<String>)> + '_ {
    map.iter().filter_map(|(k, v)| {
        let key = k.as_str()?.to_string();
        let values = match v {
            Yaml::String(s) => vec![s.clone()],
            Yaml::Array(arr) => arr
                .iter()
                .filter_map(|item| item.as_str().map(String::from))
                .collect(),
            _ => return None,
        };
        Some((key, values))
    })
}

impl YamlOperations {
    /// Retrieves a specific setting from a YAML structure based on a dot-delimited key path.
    pub fn get_setting(&self, yaml: &Yaml, key_path: &str) -> Option<Yaml> {
        navigate(yaml, key_path).cloned()
    }

    /// Updates or creates a value in a nested YAML structure at the specified key path.
    #[must_use = "setting modification may fail; handle the Result"]
    pub fn set_setting(&self, yaml: &Yaml, key_path: &str, value: Yaml) -> Result<Yaml, YamlError> {
        if key_path.trim().is_empty() {
            return Err(YamlError::InvalidKeyPath("Empty key path".to_string()));
        }

        let mut root_yaml = yaml.clone();
        let keys: Vec<&str> = key_path.split('.').collect();
        if keys.iter().any(|key| key.is_empty()) {
            return Err(YamlError::InvalidKeyPath(
                "Key path contains empty segment".to_string(),
            ));
        }
        let last_key = keys
            .last()
            .ok_or_else(|| YamlError::InvalidKeyPath("Empty key path".to_string()))?;

        fn ensure_hash(yaml: &mut Yaml) -> &mut yaml_rust2::yaml::Hash {
            if !matches!(yaml, Yaml::Hash(_)) {
                *yaml = Yaml::Hash(yaml_rust2::yaml::Hash::new());
            }
            match yaml {
                Yaml::Hash(h) => h,
                _ => unreachable!(),
            }
        }

        let mut current = &mut root_yaml;
        for key in &keys[..keys.len() - 1] {
            let hash = ensure_hash(current);
            current = hash
                .entry(Yaml::String(key.to_string()))
                .or_insert(Yaml::Hash(yaml_rust2::yaml::Hash::new()));
        }

        ensure_hash(current).insert(Yaml::String(last_key.to_string()), value);
        Ok(root_yaml)
    }

    /// Get multiple settings at once.
    pub fn get_settings_batch(&self, yaml: &Yaml, key_paths: &[&str]) -> HashMap<String, Yaml> {
        let mut results = HashMap::with_capacity(key_paths.len());
        for key_path in key_paths {
            if let Some(value) = self.get_setting(yaml, key_path) {
                results.insert(key_path.to_string(), value);
            }
        }
        results
    }

    /// Set multiple settings at once.
    pub fn set_settings_batch(
        &self,
        yaml: &Yaml,
        settings: &[(&str, Yaml)],
    ) -> Result<Yaml, YamlError> {
        let mut current = yaml.clone();
        for (key_path, value) in settings {
            current = self.set_setting(&current, key_path, value.clone())?;
        }
        Ok(current)
    }

    /// Extract a string value from YAML using a dot-separated key path.
    pub fn get_string_value(&self, data: &Yaml, key_path: &str, default: &str) -> String {
        navigate(data, key_path)
            .and_then(Yaml::as_str)
            .unwrap_or(default)
            .to_string()
    }

    /// Extract a vector of strings from YAML using a dot-separated key path.
    pub fn get_vec_value(&self, data: &Yaml, key_path: &str) -> Vec<String> {
        match navigate(data, key_path) {
            Some(Yaml::Array(arr)) => arr
                .iter()
                .filter_map(|item| item.as_str().map(String::from))
                .collect(),
            _ => Vec::new(),
        }
    }

    /// Extract a hashmap from YAML using a dot-separated key path.
    pub fn get_hashmap_value(&self, data: &Yaml, key_path: &str) -> HashMap<String, String> {
        match navigate(data, key_path) {
            Some(Yaml::Hash(map)) => string_pairs(map).collect(),
            _ => HashMap::new(),
        }
    }

    /// Get an IndexMap of string key-value pairs from YAML data, preserving insertion order.
    pub fn get_indexmap_value(&self, data: &Yaml, key_path: &str) -> IndexMap<String, String> {
        match navigate(data, key_path) {
            Some(Yaml::Hash(map)) => string_pairs(map).collect(),
            _ => IndexMap::new(),
        }
    }

    /// Get a HashMap where values are arrays of strings (`Vec<String>`) from YAML data.
    pub fn get_hashmap_vec_value(
        &self,
        data: &Yaml,
        key_path: &str,
    ) -> HashMap<String, Vec<String>> {
        match navigate(data, key_path) {
            Some(Yaml::Hash(map)) => string_vec_pairs(map).collect(),
            _ => HashMap::new(),
        }
    }

    /// Get an IndexMap where values are arrays of strings (`Vec<String>`) from YAML data.
    pub fn get_indexmap_vec_value(
        &self,
        data: &Yaml,
        key_path: &str,
    ) -> IndexMap<String, Vec<String>> {
        match navigate(data, key_path) {
            Some(Yaml::Hash(map)) => string_vec_pairs(map).collect(),
            _ => IndexMap::new(),
        }
    }
}

#[cfg(test)]
#[path = "accessors_tests.rs"]
mod tests;
