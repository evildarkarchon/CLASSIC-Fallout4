use super::*;

// ========================================================================
// CoercedValue Accessor Tests
// ========================================================================

#[test]
fn test_coerced_value_accessors() {
    assert_eq!(CoercedValue::Int(42).as_i64(), Some(42));
    assert_eq!(CoercedValue::Int(42).as_bool(), None);
    assert_eq!(CoercedValue::Bool(true).as_bool(), Some(true));
    assert_eq!(CoercedValue::Bool(true).as_i64(), None);
    assert_eq!(CoercedValue::Float(3.125).as_f64(), Some(3.125));
    assert_eq!(CoercedValue::Float(3.125).as_str(), None);
    assert_eq!(CoercedValue::String("hi".into()).as_str(), Some("hi"));
    assert_eq!(CoercedValue::Path("/tmp".into()).as_str(), Some("/tmp"));
}
