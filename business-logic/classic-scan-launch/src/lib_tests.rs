use super::*;
use classic_vocabulary::assert_vocabulary_conformance;

#[test]
fn zero_concurrency_count_means_adaptive_and_any_other_count_is_a_limit() {
    assert_eq!(MaxConcurrency::from_count(0), MaxConcurrency::Adaptive);
    assert_eq!(MaxConcurrency::from_count(0).limit(), None);
    assert_eq!(MaxConcurrency::from_count(4).limit(), Some(4));
}

#[test]
fn launch_kind_vocabularies_are_conformant() {
    assert_vocabulary_conformance::<CrashLogScanLaunchDiagnosticKind>();
    assert_vocabulary_conformance::<CrashLogScanLaunchErrorKind>();
}
