use super::*;

#[test]
fn compat_accepts_matching_major_and_minor_at_or_above_floor() {
    let v = SchemaVersion::new(2, 5);
    let compat = SchemaCompat::new(2, 4);
    assert_eq!(schema_compat_check(&v, &compat), Compatibility::Compatible);
}

#[test]
fn compat_equal_floor_is_compatible() {
    let v = SchemaVersion::new(1, 0);
    let compat = SchemaCompat::new(1, 0);
    assert_eq!(schema_compat_check(&v, &compat), Compatibility::Compatible);
}

#[test]
fn compat_rejects_major_mismatch() {
    let v = SchemaVersion::new(3, 0);
    let compat = SchemaCompat::new(2, 4);
    assert_eq!(
        schema_compat_check(&v, &compat),
        Compatibility::IncompatibleMajor {
            file_major: 3,
            client_accepted_major: 2
        }
    );
}

#[test]
fn compat_rejects_minor_below_floor() {
    let v = SchemaVersion::new(2, 2);
    let compat = SchemaCompat::new(2, 4);
    assert_eq!(
        schema_compat_check(&v, &compat),
        Compatibility::IncompatibleMinor {
            file_minor: 2,
            client_minimum_minor: 4
        }
    );
}
