use super::ContentIdentity;

/// The empty-input SHA-256, used as a fixed vector rather than a recomputation.
const EMPTY_SHA256: &str = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855";

#[test]
fn empty_bytes_have_the_known_digest_and_zero_length() {
    let identity = ContentIdentity::from_bytes(b"");

    assert_eq!(identity.sha256_hex(), EMPTY_SHA256);
    assert_eq!(identity.byte_len(), 0);
}

#[test]
fn digest_is_lowercase_hex_of_exactly_sixty_four_characters() {
    let identity = ContentIdentity::from_bytes(b"durable publication");
    let hex = identity.sha256_hex();

    assert_eq!(hex.len(), 64);
    assert!(
        hex.chars()
            .all(|c| c.is_ascii_hexdigit() && !c.is_uppercase()),
        "digest was not lowercase hex: {hex}"
    );
}

#[test]
fn byte_length_tracks_the_exact_input() {
    assert_eq!(ContentIdentity::from_bytes(&[0u8; 4096]).byte_len(), 4096);
}

#[test]
fn identical_bytes_produce_equal_identities() {
    assert_eq!(
        ContentIdentity::from_bytes(b"same"),
        ContentIdentity::from_bytes(b"same")
    );
}

#[test]
fn differing_bytes_produce_different_identities() {
    assert_ne!(
        ContentIdentity::from_bytes(b"one"),
        ContentIdentity::from_bytes(b"two")
    );
}

#[test]
fn a_streamed_reader_yields_the_same_identity_as_the_whole_buffer() {
    // Larger than one digest round, so the chunk boundary is actually crossed.
    let bytes = vec![7u8; 200 * 1024];

    let streamed = ContentIdentity::from_reader(bytes.as_slice()).expect("streaming a buffer");

    assert_eq!(streamed, ContentIdentity::from_bytes(&bytes));
    assert_eq!(streamed.byte_len(), 200 * 1024);
}

#[test]
fn an_empty_reader_has_the_known_empty_digest() {
    let identity = ContentIdentity::from_reader(&[] as &[u8]).expect("streaming nothing");

    assert_eq!(identity.sha256_hex(), EMPTY_SHA256);
    assert_eq!(identity.byte_len(), 0);
}

#[test]
fn a_read_failure_is_reported_rather_than_producing_a_partial_digest() {
    struct FailsAfterFirstRound;

    impl std::io::Read for FailsAfterFirstRound {
        fn read(&mut self, _buffer: &mut [u8]) -> std::io::Result<usize> {
            Err(std::io::Error::new(
                std::io::ErrorKind::PermissionDenied,
                "device refused the read",
            ))
        }
    }

    let error =
        ContentIdentity::from_reader(FailsAfterFirstRound).expect_err("a read failure propagates");

    assert_eq!(error.kind(), std::io::ErrorKind::PermissionDenied);
}

#[test]
fn an_expected_digest_matches_regardless_of_letter_case() {
    let identity = ContentIdentity::from_bytes(b"durable publication");
    let lowercase = identity.sha256_hex();

    assert!(identity.matches_sha256_hex(&lowercase));
    assert!(identity.matches_sha256_hex(&lowercase.to_uppercase()));
}

#[test]
fn an_expected_digest_of_the_wrong_bytes_or_the_wrong_length_does_not_match() {
    let identity = ContentIdentity::from_bytes(b"one");

    assert!(!identity.matches_sha256_hex(&ContentIdentity::from_bytes(b"two").sha256_hex()));
    assert!(
        !identity.matches_sha256_hex(&identity.sha256_hex()[..63]),
        "a truncated digest is not a prefix match"
    );
    assert!(!identity.matches_sha256_hex(""));
}
