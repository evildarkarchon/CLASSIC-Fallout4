//! CLASSIC Python adapter: one PyO3 extension behind 18 direct-import facades.
//!
//! This crate replaces the former 17 `python-bindings/classic-*-py` crates and
//! `foundation/classic-shared-py`. It builds one native extension,
//! `_classic_native._native`, and one wheel. The wheel's 18 Python facade
//! packages (`classic_config`, `classic_shared`, ...) re-export the canonical
//! native classes, functions, and exceptions registered here, so a value created
//! through one facade is the same Python type another facade accepts.
//!
//! # Layout
//!
//! - [`support`] holds the PyO3 conversion, exception, GIL, and runtime helpers
//!   every facade shares (the former `classic-shared-py` library).
//! - One module per facade (`classic_config`, `classic_scanlog`, ...) holds that
//!   facade's adapter code and its `register` function.
//!
//! Business rules and authoritative state stay in the Rust core crates. Where a
//! former extension image's statics were observable from Python (typed registry
//! and application directory, YAML caches, file-hash cache, Version Registry
//! snapshots), the facade module owns an opaque core scope handle and passes it
//! at facade entry or object construction, so merging the images does not merge
//! that state. The `classic_perf` and `classic_shared` timing views deliberately
//! share this image's one default metrics store.
//!
//! # Runtime
//!
//! Every async entry point runs on CLASSIC's one shared Tokio runtime:
//! [`support::initialize_async_runtime`] attaches PyO3's coroutine scheduling to
//! `classic_shared_core::get_runtime()` before any facade is registered.

use pyo3::prelude::*;
use pyo3::types::PyModule;

pub mod support;

pub mod classic_config;
pub mod classic_database;
pub mod classic_file_io;
pub mod classic_message;
pub mod classic_path;
pub mod classic_perf;
pub mod classic_registry;
pub mod classic_resource;
pub mod classic_scangame;
pub mod classic_scanlog;
pub mod classic_settings;
pub mod classic_shared;
pub mod classic_update;
pub mod classic_user_settings;
pub mod classic_version;
pub mod classic_version_registry;
pub mod classic_web;
pub mod classic_xse;

/// Python package that owns the native extension module.
const NATIVE_PACKAGE: &str = "_classic_native._native";

/// One facade: its import name and the function that registers its exports.
type FacadeRegistration = (&'static str, fn(&Bound<'_, PyModule>) -> PyResult<()>);

/// Every direct-import facade, in registration order.
///
/// Registration order is not observable: each facade's import-time effects
/// (for example `classic_config` and `classic_scanlog` recording the script
/// directory as their application directory) land in that facade's own core
/// scope.
const FACADES: [FacadeRegistration; 18] = [
    ("classic_shared", classic_shared::register_facade),
    ("classic_config", classic_config::register_facade),
    ("classic_database", classic_database::register_facade),
    ("classic_file_io", classic_file_io::register_facade),
    ("classic_message", classic_message::register_facade),
    ("classic_path", classic_path::register_facade),
    ("classic_perf", classic_perf::register_facade),
    ("classic_registry", classic_registry::register_facade),
    ("classic_resource", classic_resource::register_facade),
    ("classic_scangame", classic_scangame::register_facade),
    ("classic_scanlog", classic_scanlog::register_facade),
    ("classic_settings", classic_settings::register_facade),
    ("classic_update", classic_update::register_facade),
    (
        "classic_user_settings",
        classic_user_settings::register_facade,
    ),
    ("classic_version", classic_version::register_facade),
    (
        "classic_version_registry",
        classic_version_registry::register_facade,
    ),
    ("classic_web", classic_web::register_facade),
    ("classic_xse", classic_xse::register_facade),
];

/// The import names of the 18 direct-import facades this extension serves.
pub fn facade_names() -> impl Iterator<Item = &'static str> {
    FACADES.iter().map(|(name, _)| *name)
}

/// Native module initialization for `_classic_native._native`.
///
/// Builds one submodule per facade, named exactly like the facade so native
/// functions keep their historical `__module__`, and records each in
/// `sys.modules` as `_classic_native._native.<facade>` so the checked-in facade
/// packages can import their names from it. A facade submodule is created once
/// per process; every facade package re-exports those same objects.
#[pymodule]
fn _native(m: &Bound<'_, PyModule>) -> PyResult<()> {
    let py = m.py();
    support::initialize_async_runtime()?;
    support::configure_python_stdio(py);

    let sys_modules = PyModule::import(py, "sys")?.getattr("modules")?;
    for (name, register) in FACADES {
        let facade = PyModule::new(py, name)?;
        register(&facade)?;
        m.add_submodule(&facade)?;
        sys_modules.set_item(format!("{NATIVE_PACKAGE}.{name}"), &facade)?;
    }

    m.add("__version__", env!("CARGO_PKG_VERSION"))?;
    m.add_function(wrap_pyfunction!(support::shares_classic_runtime, m)?)?;
    Ok(())
}

#[cfg(test)]
#[path = "lib_tests.rs"]
mod tests;
