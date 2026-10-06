use pyo3::prelude::*;

#[pyclass(module = "classic_settings", name = "YamlFile", from_py_object)]
#[derive(Clone)]
pub struct PyYamlFile {
    inner: classic_config_core::YamlSource,
}

#[pymethods]
impl PyYamlFile {
    #[classattr]
    #[allow(non_snake_case)]
    fn Main() -> Self {
        Self {
            inner: classic_config_core::YamlSource::Main,
        }
    }

    #[classattr]
    #[allow(non_snake_case)]
    fn Ignore() -> Self {
        Self {
            inner: classic_config_core::YamlSource::Ignore,
        }
    }

    #[classattr]
    #[allow(non_snake_case)]
    fn Game() -> Self {
        Self {
            inner: classic_config_core::YamlSource::Game,
        }
    }

    #[classattr]
    #[allow(non_snake_case)]
    fn GameLocal() -> Self {
        Self {
            inner: classic_config_core::YamlSource::GameLocal,
        }
    }

    #[classattr]
    #[allow(non_snake_case)]
    fn Test() -> Self {
        Self {
            inner: classic_config_core::YamlSource::Test,
        }
    }

    #[classattr]
    #[allow(non_snake_case)]
    fn Cache() -> Self {
        Self {
            inner: classic_config_core::YamlSource::Cache,
        }
    }

    fn as_str(&self) -> &'static str {
        self.inner.as_str()
    }

    fn description(&self) -> &'static str {
        self.inner.description()
    }

    fn __repr__(&self) -> String {
        format!("YamlFile.{}", self.inner.as_str())
    }

    fn __str__(&self) -> &'static str {
        self.inner.as_str()
    }

    fn __eq__(&self, other: &Self) -> bool {
        self.inner == other.inner
    }

    fn __hash__(&self) -> u64 {
        use std::collections::hash_map::DefaultHasher;
        use std::hash::{Hash, Hasher};

        let mut hasher = DefaultHasher::new();
        self.inner.hash(&mut hasher);
        hasher.finish()
    }
}

pub fn register(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<PyYamlFile>()?;
    Ok(())
}
