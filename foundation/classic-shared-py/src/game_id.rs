use pyo3::prelude::*;

/// Python wrapper around [`classic_shared_core::GameId`].
#[pyclass(module = "classic_shared", name = "GameId")]
#[derive(Clone)]
pub struct PyGameId {
    inner: classic_shared_core::GameId,
}

#[pymethods]
impl PyGameId {
    #[classattr]
    #[allow(non_snake_case)]
    fn Fallout4() -> Self {
        Self {
            inner: classic_shared_core::GameId::Fallout4,
        }
    }

    #[classattr]
    #[allow(non_snake_case)]
    fn Fallout4VR() -> Self {
        Self {
            inner: classic_shared_core::GameId::Fallout4VR,
        }
    }

    #[classattr]
    #[allow(non_snake_case)]
    fn Skyrim() -> Self {
        Self {
            inner: classic_shared_core::GameId::Skyrim,
        }
    }

    #[classattr]
    #[allow(non_snake_case)]
    fn Starfield() -> Self {
        Self {
            inner: classic_shared_core::GameId::Starfield,
        }
    }

    fn as_str(&self) -> &'static str {
        self.inner.as_str()
    }

    fn exe_name(&self) -> &'static str {
        self.inner.exe_name()
    }

    fn is_vr(&self) -> bool {
        self.inner.is_vr()
    }

    fn __repr__(&self) -> String {
        format!("GameId.{}", self.inner.as_str())
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

/// Register `GameId` on the Python module.
pub fn register(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<PyGameId>()?;
    Ok(())
}
