use super::*;
use classic_version_registry_core::get_version_registry;

/// The known-version queries read this facade's own Version Registry scope, which must
/// not be the process default (#233, #244).
#[test]
fn facade_version_registry_scope_is_not_the_process_default() {
    let scope = &*VERSION_REGISTRY_SCOPE;
    assert_ne!(*scope, VersionRegistryScope::default_scope());
    assert!(!std::ptr::eq(scope.registry(), get_version_registry()));
}
