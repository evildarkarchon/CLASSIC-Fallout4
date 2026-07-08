use super::*;
use crate::SettingsError;
use crate::loader::parse_yaml_content;

#[test]
fn test_merge_yaml_documents_recursively_merges_nested_maps() {
    let docs = parse_yaml_content(
        "memory://settings.yaml",
        "paths:\n  game_root: C:/Games/Fallout4\n  nested:\n    a: 1\n---\npaths:\n  nested:\n    b: 2\n",
    )
    .unwrap();

    let merged = merge_yaml_documents("memory://settings.yaml", &docs).unwrap();

    assert_eq!(
        merged["paths"]["game_root"].as_str(),
        Some("C:/Games/Fallout4")
    );
    assert_eq!(merged["paths"]["nested"]["a"].as_i64(), Some(1));
    assert_eq!(merged["paths"]["nested"]["b"].as_i64(), Some(2));
}

#[test]
fn test_merge_yaml_documents_replaces_sequences_and_type_conflicts() {
    let docs = parse_yaml_content(
        "memory://settings.yaml",
        "items:\n  - a\nvalue:\n  nested: true\n---\nitems:\n  - b\nvalue: replaced\n",
    )
    .unwrap();

    let merged = merge_yaml_documents("memory://settings.yaml", &docs).unwrap();

    assert_eq!(merged["items"][0].as_str(), Some("b"));
    assert_eq!(merged["items"][1].as_str(), None);
    assert_eq!(merged["value"].as_str(), Some("replaced"));
}

#[test]
fn test_merge_yaml_documents_empty_stream_is_error() {
    let err = merge_yaml_documents("memory://settings.yaml", &[]).unwrap_err();

    match err {
        SettingsError::EmptyDocument { source } => {
            assert_eq!(source.label(), Some("memory://settings.yaml"))
        }
        e => panic!("Expected EmptyDocument, got {:?}", e),
    }
}

#[test]
fn test_merge_yaml_documents_rejects_non_mapping_documents() {
    let docs = parse_yaml_content("memory://settings.yaml", "key: value\n---\n- item\n").unwrap();

    let err = merge_yaml_documents("memory://settings.yaml", &docs).unwrap_err();

    match err {
        SettingsError::InvalidYamlStructure {
            source,
            index,
            found,
        } => {
            assert_eq!(source.label(), Some("memory://settings.yaml"));
            assert_eq!(index, 1);
            assert_eq!(found, "sequence");
        }
        e => panic!("Expected InvalidYamlStructure, got {:?}", e),
    }
}
