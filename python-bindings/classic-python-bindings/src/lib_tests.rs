use super::*;
use std::collections::BTreeSet;

#[test]
fn the_adapter_serves_exactly_the_eighteen_direct_imports() {
    let names: BTreeSet<&str> = facade_names().collect();

    assert_eq!(names.len(), 18, "facade names must be unique");
    assert!(names.iter().all(|name| name.starts_with("classic_")));
    assert!(names.contains("classic_shared"));
    assert!(names.contains("classic_perf"));
}

#[test]
fn native_init_registers_each_facade_once_on_the_shared_runtime() {
    Python::attach(|py| {
        let module = PyModule::new(py, "_native").expect("module");
        _native(&module).expect("native init");

        // Every PyO3 coroutine schedules on CLASSIC's one shared runtime.
        assert!(support::shares_classic_runtime());

        let sys_modules = PyModule::import(py, "sys")
            .and_then(|sys| sys.getattr("modules"))
            .expect("sys.modules");
        for name in facade_names() {
            let registered = sys_modules
                .get_item(format!("{NATIVE_PACKAGE}.{name}"))
                .expect("facade submodule recorded in sys.modules");
            let attribute = module.getattr(name).expect("facade submodule attribute");
            // One submodule object per facade, named like the facade so native
            // functions keep their historical `__module__`.
            assert!(registered.is(&attribute), "{name}");
            let module_name: String = attribute
                .getattr("__name__")
                .and_then(|value| value.extract())
                .expect("submodule name");
            assert_eq!(module_name, name);
            let version: String = attribute
                .getattr("__version__")
                .and_then(|value| value.extract())
                .expect("facade version");
            assert_eq!(version, env!("CARGO_PKG_VERSION"), "{name}");
        }
    });
}
