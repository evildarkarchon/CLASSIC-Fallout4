use super::*;
use classic_registry_core::{clear_all, get_application_dir};
use pyo3::exceptions::PyRuntimeError;
use pyo3::types::PyModule;
use serial_test::serial;
use std::{env, fs};
use tempfile::tempdir;

#[test]
#[serial]
fn module_init_registers_script_directory_as_application_dir() {
    let temp_dir = tempdir().expect("temp dir should be created");
    let script_dir = temp_dir.path().join("script-dir");
    let run_dir = temp_dir.path().join("run-dir");
    fs::create_dir_all(&script_dir).expect("script dir should exist");
    fs::create_dir_all(&run_dir).expect("run dir should exist");

    let original_dir = env::current_dir().expect("current dir should resolve");
    env::set_current_dir(&run_dir).expect("cwd should switch to run dir");
    clear_all();

    let test_result = Python::attach(|py| -> PyResult<()> {
        let main = PyModule::import(py, "__main__")?;
        let sys = PyModule::import(py, "sys")?;
        let original_main_file = main
            .getattr("__file__")
            .ok()
            .and_then(|value| value.extract::<String>().ok());
        let original_argv: Vec<String> = sys.getattr("argv")?.extract()?;

        let outcome = (|| -> PyResult<()> {
            let script_path = script_dir.join("run_scanlog.py");
            main.setattr("__file__", script_path.to_string_lossy().into_owned())?;
            sys.setattr("argv", vec![script_path.to_string_lossy().into_owned()])?;

            let module = PyModule::new(py, "classic_scanlog")?;
            classic_scanlog(&module)?;

            if get_application_dir() != Some(script_dir.clone()) {
                return Err(PyRuntimeError::new_err(format!(
                    "expected APP_DIR to be {}, got {:?}",
                    script_dir.display(),
                    get_application_dir()
                )));
            }

            Ok(())
        })();

        match original_main_file {
            Some(path) => main.setattr("__file__", path)?,
            None => {
                let _ = main.delattr("__file__");
            }
        }
        sys.setattr("argv", original_argv)?;
        clear_all();

        outcome
    });

    env::set_current_dir(original_dir).expect("cwd should be restored");
    test_result.expect("module init should register the executed script directory");
}
