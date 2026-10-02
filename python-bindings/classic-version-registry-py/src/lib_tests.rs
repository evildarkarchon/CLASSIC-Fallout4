use super::*;
use classic_version_registry_core::get_version_registry;

/// Every registry read in this facade goes through its own Version Registry
/// scope, which must not be the process default (#233, #244).
#[test]
fn facade_registry_is_not_the_process_default_snapshot() {
    assert_ne!(*FACADE_SCOPE, VersionRegistryScope::default_scope());
    assert!(!std::ptr::eq(facade_registry(), get_version_registry()));
}
