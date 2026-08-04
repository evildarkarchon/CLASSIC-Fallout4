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
