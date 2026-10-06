use super::*;
use classic_registry_core::{clear_all, get_application_dir};
use pyo3::exceptions::PyRuntimeError;
use pyo3::types::PyModule;
use serial_test::serial;
use std::{env, fs};
use tempfile::tempdir;

#[test]
#[serial]
fn module_init_registers_script_directory_in_its_own_registry_scope() {
    let temp_dir = tempdir().expect("temp dir should be created");
    let script_dir = temp_dir.path().join("script-dir");
    let run_dir = temp_dir.path().join("run-dir");
    fs::create_dir_all(&script_dir).expect("script dir should exist");
    fs::create_dir_all(&run_dir).expect("run dir should exist");

    let original_dir = env::current_dir().expect("current dir should resolve");
    env::set_current_dir(&run_dir).expect("cwd should switch to run dir");
    SCANLOG_REGISTRY_SCOPE.clear_all();
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
            register_facade(&module)?;

            if SCANLOG_REGISTRY_SCOPE.get_application_dir() != Some(script_dir.clone()) {
                return Err(PyRuntimeError::new_err(format!(
                    "expected APP_DIR to be {}, got {:?}",
                    script_dir.display(),
                    SCANLOG_REGISTRY_SCOPE.get_application_dir()
                )));
            }
            // The facade writes only its own scope, never the default one.
            if get_application_dir().is_some() {
                return Err(PyRuntimeError::new_err(format!(
                    "default APP_DIR should stay unset, got {:?}",
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
        SCANLOG_REGISTRY_SCOPE.clear_all();
        clear_all();

        outcome
    });

    env::set_current_dir(original_dir).expect("cwd should be restored");
    test_result.expect("module init should register the executed script directory");
}

/// `PluginAnalyzer` and scan runs started through this facade read its own
/// Version Registry scope, which must not be the process default (#233, #244).
#[test]
fn facade_version_registry_scope_is_not_the_process_default() {
    use classic_version_registry_core::{VersionRegistryScope, get_version_registry};

    let scope = &*SCANLOG_VERSION_REGISTRY_SCOPE;
    assert_ne!(*scope, VersionRegistryScope::default_scope());
    assert!(!std::ptr::eq(scope.registry(), get_version_registry()));
}

/// FCX setup inside scan runs started through this facade hashes in its own
/// file-hash scope, never the process default that unscoped Rust, CXX, and
/// Node runs use (#259).
#[test]
fn facade_file_hash_scope_is_not_the_process_default() {
    assert_ne!(*SCANLOG_HASH_SCOPE, FileHashScope::default_scope());
}

/// Standard discovery inside scan runs started through this facade reads the
/// Game Local document through its own YAML-file cache scope, never the
/// process default that unscoped Rust, CXX, and Node runs use (#234).
#[test]
fn facade_yaml_file_cache_scope_is_not_the_process_default() {
    use classic_shared_core::yaml::YamlFileCacheScope;

    assert_ne!(
        *SCANLOG_YAML_FILE_SCOPE,
        YamlFileCacheScope::default_scope()
    );
}

/// `classic_config.clear_yaml_cache()` clears only the default YAML-file
/// scope, so this facade's cached Game Local entries and counters survive it,
/// while this facade's own scope can still be cleared (#234).
#[test]
#[serial]
fn config_clear_leaves_facade_yaml_entries_and_counters() {
    use classic_shared_core::yaml::YamlOperations;

    let temp_dir = tempdir().expect("temp dir should be created");
    let local = temp_dir.path().join("CLASSIC Fallout4 Local.yaml");
    fs::write(&local, "Game_Info:\n  Docs_Folder_XSE: probe-xse\n").expect("Local.yaml");
    let scope = &*SCANLOG_YAML_FILE_SCOPE;
    scope.clear();
    scope.reset_stats();
    let ops = YamlOperations::with_cache_scope(scope.clone());
    ops.load_yaml_file(&local).expect("first load");
    ops.load_yaml_file(&local).expect("cached load");
    let filled = scope.stats();
    assert_eq!((filled.hits, filled.misses, filled.size), (1, 1, 1));

    crate::classic_config::clear_yaml_cache();

    let after_config_clear = scope.stats();
    assert_eq!(
        (
            after_config_clear.hits,
            after_config_clear.misses,
            after_config_clear.size
        ),
        (1, 1, 1),
        "the config facade's clear must not evict or reset scanlog's scope"
    );

    scope.clear();
    assert_eq!(scope.stats().size, 0, "the facade's own scope still clears");
}
