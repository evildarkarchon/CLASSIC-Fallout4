use pyo3::prelude::*;

#[pyclass(
    module = "classic_version_registry",
    name = "Fallout4Version",
    from_py_object
)]
#[derive(Clone)]
pub struct PyFallout4Version {
    inner: classic_version_registry_core::Fallout4Version,
}

#[pymethods]
impl PyFallout4Version {
    #[classattr]
    #[allow(non_snake_case)]
    fn Original() -> Self {
        Self {
            inner: classic_version_registry_core::Fallout4Version::Original,
        }
    }

    #[classattr]
    #[allow(non_snake_case)]
    fn NextGen() -> Self {
        Self {
            inner: classic_version_registry_core::Fallout4Version::NextGen,
        }
    }

    #[classattr]
    #[allow(non_snake_case)]
    fn AnniversaryEdition() -> Self {
        Self {
            inner: classic_version_registry_core::Fallout4Version::AnniversaryEdition,
        }
    }

    #[classattr]
    #[allow(non_snake_case)]
    fn Vr() -> Self {
        Self {
            inner: classic_version_registry_core::Fallout4Version::Vr,
        }
    }

    #[staticmethod]
    fn from_str(s: &str) -> PyResult<Self> {
        use std::str::FromStr;

        classic_version_registry_core::Fallout4Version::from_str(s)
            .map(|inner| Self { inner })
            .map_err(pyo3::exceptions::PyValueError::new_err)
    }

    #[staticmethod]
    fn all() -> Vec<Self> {
        classic_version_registry_core::Fallout4Version::all()
            .iter()
            .map(|&inner| Self { inner })
            .collect()
    }

    fn is_vr(&self) -> bool {
        self.inner.is_vr()
    }

    fn is_standard(&self) -> bool {
        self.inner.is_standard()
    }

    fn exe_name(&self) -> &'static str {
        self.inner.exe_name()
    }

    fn docs_folder_name(&self) -> &'static str {
        self.inner.docs_folder_name()
    }

    fn steam_app_id(&self) -> u32 {
        self.inner.steam_app_id()
    }

    fn version(&self) -> String {
        self.inner.game_version().to_string()
    }

    fn registry_id(&self) -> &'static str {
        self.inner.registry_id()
    }

    fn short_name(&self) -> &'static str {
        self.inner.short_name()
    }

    fn xse_acronym(&self) -> &'static str {
        self.inner.xse_acronym()
    }

    fn display_name(&self) -> &'static str {
        self.inner.display_name()
    }

    fn as_str(&self) -> &'static str {
        self.inner.as_str()
    }

    fn __repr__(&self) -> String {
        format!("Fallout4Version.{}", self.inner.as_str())
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
    m.add_class::<PyFallout4Version>()?;
    m.add("NULL_VERSION", "0.0.0")?;
    Ok(())
}
