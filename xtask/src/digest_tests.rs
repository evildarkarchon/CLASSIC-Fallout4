use super::*;

#[test]
fn hex_is_two_lowercase_digits_per_byte() {
    assert_eq!(hex(&[0x00, 0x0f, 0xa0, 0xff]), "000fa0ff");
    assert_eq!(hex(&[]), "");
}

#[test]
fn sha256_hex_is_lowercase_hex_of_the_bytes() {
    // Moved from `publish::probe`, which owned the helper before it was shared.
    assert_eq!(
        sha256_hex(b"abc"),
        "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
    );
}
