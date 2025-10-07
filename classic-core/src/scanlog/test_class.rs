//! Test class to verify PyO3 registration

use pyo3::prelude::*;

#[pyclass]
pub struct TestClass {
    value: String,
}

#[pymethods]
impl TestClass {
    #[new]
    pub fn new() -> Self {
        Self {
            value: "test".to_string(),
        }
    }

    pub fn get_value(&self) -> String {
        self.value.clone()
    }
}
