use super::*;

#[test]
fn test_parse_4_component() {
    let v = GameVersion::parse("1.10.163.0").unwrap();
    assert_eq!(v.major, 1);
    assert_eq!(v.minor, 10);
    assert_eq!(v.patch, 163);
    assert_eq!(v.build, 0);
}

#[test]
fn test_parse_3_component() {
    let v = GameVersion::parse("1.10.163").unwrap();
    assert_eq!(v.major, 1);
    assert_eq!(v.minor, 10);
    assert_eq!(v.patch, 163);
    assert_eq!(v.build, 0);
}

#[test]
fn test_parse_invalid() {
    assert!(GameVersion::parse("1.10").is_err());
    assert!(GameVersion::parse("1.10.163.0.1").is_err());
    assert!(GameVersion::parse("abc.def.ghi").is_err());
    assert!(GameVersion::parse("").is_err());
}

#[test]
fn test_display() {
    let v = GameVersion::new(1, 10, 163, 0);
    assert_eq!(v.to_string(), "1.10.163.0");
}

#[test]
fn test_comparison() {
    let v1 = GameVersion::parse("1.10.163.0").unwrap();
    let v2 = GameVersion::parse("1.10.984.0").unwrap();
    let v3 = GameVersion::parse("1.2.72.0").unwrap();

    assert!(v1 < v2);
    assert!(v3 < v1);
    assert!(v1 == v1);
}

#[test]
fn test_semantic_distance() {
    let v1 = GameVersion::parse("1.10.163.0").unwrap();
    let v2 = GameVersion::parse("1.10.500.0").unwrap();
    let v3 = GameVersion::parse("1.10.984.0").unwrap();

    // Patch difference only
    assert_eq!(v1.semantic_distance(&v2), 337);
    assert_eq!(v1.semantic_distance(&v3), 821);

    // Same version = 0 distance
    assert_eq!(v1.semantic_distance(&v1), 0);
}

#[test]
fn test_same_major() {
    let v1 = GameVersion::parse("1.10.163.0").unwrap();
    let v2 = GameVersion::parse("1.10.984.0").unwrap();
    let v3 = GameVersion::parse("2.0.0.0").unwrap();

    assert!(v1.same_major(&v2));
    assert!(!v1.same_major(&v3));
}
