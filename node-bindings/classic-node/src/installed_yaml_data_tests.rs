//! Installed YAML Data vocabulary projection tests.
//!
//! Expectations are derived from `classic-config-core`, never restated. A
//! hand-written array here would be another copy of the vocabulary: it would
//! pass against a surface that had already drifted, because it would only be
//! comparing this file's copy against itself. Iterating `VARIANTS` also means a
//! new variant is covered without anyone remembering to extend these tests.
//!
//! Only the projection rules are exercised here. Everything reachable from a
//! real inspection is covered from JavaScript in `__test__/config.spec.ts`,
//! where the published strings are what a consumer actually receives.

use super::*;
// Imported here rather than in `installed_yaml_data.rs`: the module itself only
// projects labels through `crate::vocabulary::display_label`, so the trait is in
// scope only where the tests read `label()` off a core variant to derive their
// expectation from.
use classic_vocabulary::Vocabulary;

#[test]
/// Every projected JavaScript variant resolves back to the core Display Label.
fn every_config_enum_projects_its_core_display_label() {
    for variant in CoreInstalledYamlDataProvenance::VARIANTS.iter().copied() {
        assert_eq!(
            installed_yaml_data_provenance_label(provenance_to_js(variant)),
            variant.label(),
        );
    }
    for variant in CoreInstalledYamlDataDiagnosticKind::VARIANTS
        .iter()
        .copied()
    {
        assert_eq!(
            installed_yaml_data_diagnostic_kind_label(diagnostic_kind_to_js(variant)),
            variant.label(),
        );
    }
    for variant in CoreLocalIgnoreYamlDataState::VARIANTS.iter().copied() {
        assert_eq!(
            local_ignore_yaml_data_state_label(local_ignore_state_to_js(variant)),
            variant.label(),
        );
    }
}

#[test]
/// No Display Label reaches JavaScript empty.
fn no_config_display_label_reaches_javascript_empty() {
    // The label functions fall back to an empty string for a value the forward
    // projection cannot produce. That fallback must stay unreachable for every
    // real variant, because an empty label is exactly the "variant that renders
    // as nothing" the naming contract exists to prevent.
    for variant in CoreInstalledYamlDataProvenance::VARIANTS.iter().copied() {
        assert!(!installed_yaml_data_provenance_label(provenance_to_js(variant)).is_empty());
    }
    for variant in CoreInstalledYamlDataDiagnosticKind::VARIANTS
        .iter()
        .copied()
    {
        assert!(
            !installed_yaml_data_diagnostic_kind_label(diagnostic_kind_to_js(variant)).is_empty()
        );
    }
    for variant in CoreLocalIgnoreYamlDataState::VARIANTS.iter().copied() {
        assert!(!local_ignore_yaml_data_state_label(local_ignore_state_to_js(variant)).is_empty());
    }
}
