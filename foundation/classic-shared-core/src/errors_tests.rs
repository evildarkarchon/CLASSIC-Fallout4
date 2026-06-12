use super::*;

#[test]
fn test_error_creation() {
    let err = ClassicError::io("Test I/O error", None::<std::io::Error>);
    assert!(err.to_string().contains("I/O error"));

    let err = ClassicError::path("Invalid path", Some("/test/path"));
    assert!(err.to_string().contains("Invalid path"));
}

#[test]
fn test_error_with_context() {
    let err = ClassicError::validation("Invalid value", Some("test_field"))
        .with_context("During configuration loading");
    assert!(err.to_string().contains("Invalid value"));
}

// ---- Comprehensive error constructor tests ----

#[test]
fn test_io_error_with_source() {
    let source = std::io::Error::new(std::io::ErrorKind::NotFound, "file missing");
    let err = ClassicError::io("Read failed", Some(source));
    assert!(err.to_string().contains("I/O error"));
    assert!(err.to_string().contains("Read failed"));
}

#[test]
fn test_path_error_no_path() {
    let err = ClassicError::path("Bad path", None::<String>);
    assert!(err.to_string().contains("Path error"));
}

#[test]
fn test_validation_error_no_field() {
    let err = ClassicError::validation("Invalid", None::<String>);
    assert!(err.to_string().contains("Validation error"));
}

#[test]
fn test_parse_error_full() {
    let err = ClassicError::parse("Syntax error", Some(42), Some("yaml"));
    let msg = err.to_string();
    assert!(msg.contains("Parse error"));
    assert!(msg.contains("42"));
}

#[test]
fn test_parse_error_minimal() {
    let err = ClassicError::parse("Bad format", None, None::<String>);
    assert!(err.to_string().contains("Parse error"));
}

#[test]
fn test_database_error() {
    let err = ClassicError::database("Query failed", Some("SELECT * FROM logs"));
    let msg = err.to_string();
    assert!(msg.contains("Database error"));
}

#[test]
fn test_database_error_no_query() {
    let err = ClassicError::database("Connection lost", None::<String>);
    assert!(err.to_string().contains("Database error"));
}

#[test]
fn test_encoding_error() {
    let err = ClassicError::encoding("Invalid bytes", Some("UTF-8"));
    assert!(err.to_string().contains("Encoding error"));
}

#[test]
fn test_encoding_error_no_encoding() {
    let err = ClassicError::encoding("Bad data", None::<String>);
    assert!(err.to_string().contains("Encoding error"));
}

#[test]
fn test_timeout_error() {
    let err = ClassicError::timeout("file read", 5000);
    let msg = err.to_string();
    assert!(msg.contains("timed out"));
    assert!(msg.contains("5000"));
}

#[test]
fn test_permission_error() {
    let err = ClassicError::permission("Access denied", Some("/secure/file"));
    assert!(err.to_string().contains("Permission denied"));
}

#[test]
fn test_permission_error_no_resource() {
    let err = ClassicError::permission("Not allowed", None::<String>);
    assert!(err.to_string().contains("Permission denied"));
}

#[test]
fn test_not_found_error() {
    let err = ClassicError::not_found("settings.yaml");
    assert!(err.to_string().contains("not found"));
}

#[test]
fn test_with_context_generic() {
    let err = ClassicError::Generic {
        message: "Something failed".to_string(),
        details: None,
    };
    let contexted = err.with_context("During init");
    match contexted {
        ClassicError::Generic { message, details } => {
            assert_eq!(message, "Something failed");
            assert_eq!(details, Some("During init".to_string()));
        }
        _ => panic!("Expected Generic variant"),
    }
}

#[test]
fn test_with_context_generic_existing_details() {
    let err = ClassicError::Generic {
        message: "Error".to_string(),
        details: Some("Original details".to_string()),
    };
    let contexted = err.with_context("Extra context");
    match contexted {
        ClassicError::Generic { details, .. } => {
            let d = details.unwrap();
            assert!(d.contains("Original details"));
            assert!(d.contains("Extra context"));
        }
        _ => panic!("Expected Generic variant"),
    }
}

#[test]
fn test_with_context_non_generic_wraps() {
    let err = ClassicError::not_found("config.yaml");
    let contexted = err.with_context("While loading settings");
    match contexted {
        ClassicError::Generic { message, details } => {
            assert!(message.contains("not found"));
            assert_eq!(details, Some("While loading settings".to_string()));
        }
        _ => panic!("Expected Generic variant after wrapping non-Generic"),
    }
}

// ---- From implementations ----

#[test]
fn test_from_io_error_not_found() {
    let io_err = std::io::Error::new(std::io::ErrorKind::NotFound, "file missing");
    let err: ClassicError = io_err.into();
    match err {
        ClassicError::NotFound { .. } => {}
        _ => panic!("Expected NotFound variant, got {:?}", err),
    }
}

#[test]
fn test_from_io_error_permission() {
    let io_err = std::io::Error::new(std::io::ErrorKind::PermissionDenied, "denied");
    let err: ClassicError = io_err.into();
    match err {
        ClassicError::Permission { .. } => {}
        _ => panic!("Expected Permission variant, got {:?}", err),
    }
}

#[test]
fn test_from_io_error_timeout() {
    let io_err = std::io::Error::new(std::io::ErrorKind::TimedOut, "timed out");
    let err: ClassicError = io_err.into();
    match err {
        ClassicError::Timeout { .. } => {}
        _ => panic!("Expected Timeout variant, got {:?}", err),
    }
}

#[test]
fn test_from_io_error_other() {
    let io_err = std::io::Error::other("unexpected");
    let err: ClassicError = io_err.into();
    match err {
        ClassicError::Io { .. } => {}
        _ => panic!("Expected Io variant, got {:?}", err),
    }
}

#[test]
#[allow(invalid_from_utf8)]
fn test_from_utf8_error() {
    // Create an invalid UTF-8 sequence
    let bytes = &[0xff, 0xfe];
    let utf8_err = std::str::from_utf8(bytes).unwrap_err();
    let err: ClassicError = utf8_err.into();
    match err {
        ClassicError::Encoding { encoding, .. } => {
            assert_eq!(encoding, Some("UTF-8".to_string()));
        }
        _ => panic!("Expected Encoding variant, got {:?}", err),
    }
}

// ---- IntoClassicError trait ----

#[test]
fn test_into_classic_error_ok() {
    let result: Result<i32, std::io::Error> = Ok(42);
    let classic_result = result.into_classic("test context");
    assert_eq!(classic_result.unwrap(), 42);
}

#[test]
fn test_into_classic_error_err() {
    let result: Result<i32, std::io::Error> = Err(std::io::Error::other("bad things"));
    let classic_result = result.into_classic("test context");
    let err = classic_result.unwrap_err();
    match err {
        ClassicError::Generic { message, details } => {
            assert_eq!(message, "test context");
            assert!(details.unwrap().contains("bad things"));
        }
        _ => panic!("Expected Generic variant"),
    }
}

// ---- Error variant Display ----

#[test]
fn test_all_error_variants_display() {
    let errors: Vec<ClassicError> = vec![
        ClassicError::Io {
            message: "io".to_string(),
            source: None,
        },
        ClassicError::Path {
            message: "path".to_string(),
            path: Some("/p".to_string()),
        },
        ClassicError::Validation {
            message: "val".to_string(),
            field: Some("f".to_string()),
        },
        ClassicError::Parse {
            message: "parse".to_string(),
            position: Some(1),
            context: Some("ctx".to_string()),
        },
        ClassicError::Database {
            message: "db".to_string(),
            query: Some("q".to_string()),
        },
        ClassicError::Cache {
            message: "cache".to_string(),
        },
        ClassicError::Encoding {
            message: "enc".to_string(),
            encoding: Some("UTF-8".to_string()),
        },
        ClassicError::Timeout {
            operation: "op".to_string(),
            duration_ms: 100,
        },
        ClassicError::Permission {
            message: "perm".to_string(),
            resource: Some("res".to_string()),
        },
        ClassicError::Configuration {
            message: "config".to_string(),
            key: Some("k".to_string()),
        },
        ClassicError::Processing {
            message: "proc".to_string(),
            stage: Some("s".to_string()),
        },
        ClassicError::NotFound {
            resource: "res".to_string(),
        },
        ClassicError::InvalidState {
            message: "state".to_string(),
            expected: Some("A".to_string()),
            actual: Some("B".to_string()),
        },
        ClassicError::Generic {
            message: "gen".to_string(),
            details: Some("det".to_string()),
        },
    ];

    for err in errors {
        let display = err.to_string();
        assert!(!display.is_empty(), "Error Display should not be empty");
    }
}
