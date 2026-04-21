use super::*;

#[test]
fn test_resource_type_as_str() {
    assert_eq!(ResourceType::Texture.as_str(), "texture");
    assert_eq!(ResourceType::Plugin.as_str(), "plugin");
    assert_eq!(ResourceType::Other.as_str(), "other");
}

#[test]
fn test_resource_type_from_str() {
    assert_eq!(
        "texture".parse::<ResourceType>().unwrap(),
        ResourceType::Texture
    );
    assert_eq!(
        "TEXTURE".parse::<ResourceType>().unwrap(),
        ResourceType::Texture
    );
    assert_eq!(
        "plugin".parse::<ResourceType>().unwrap(),
        ResourceType::Plugin
    );
    assert_eq!(
        "unknown".parse::<ResourceType>().unwrap(),
        ResourceType::Other
    );
}

#[test]
fn test_resource_type_extensions() {
    assert!(ResourceType::Texture.extensions().contains(&"dds"));
    assert!(ResourceType::Plugin.extensions().contains(&"esp"));
    assert!(ResourceType::Script.extensions().contains(&"pex"));
}

#[test]
fn test_detect_resource_type() {
    assert_eq!(
        detect_resource_type(Path::new("texture.dds")),
        ResourceType::Texture
    );
    assert_eq!(
        detect_resource_type(Path::new("plugin.esp")),
        ResourceType::Plugin
    );
    assert_eq!(
        detect_resource_type(Path::new("script.pex")),
        ResourceType::Script
    );
    assert_eq!(
        detect_resource_type(Path::new("readme.txt")),
        ResourceType::Other
    );
}

#[test]
fn test_detect_resource_type_case_insensitive() {
    assert_eq!(
        detect_resource_type(Path::new("texture.DDS")),
        ResourceType::Texture
    );
    assert_eq!(
        detect_resource_type(Path::new("plugin.ESP")),
        ResourceType::Plugin
    );
}

#[test]
fn test_is_supported_resource() {
    assert!(is_supported_resource(Path::new("texture.dds")));
    assert!(is_supported_resource(Path::new("plugin.esp")));
    assert!(!is_supported_resource(Path::new("readme.txt")));
}

#[test]
fn test_resource_info_new() {
    let info = ResourceInfo::new(PathBuf::from("texture.dds"));
    assert_eq!(info.path, PathBuf::from("texture.dds"));
    assert_eq!(info.resource_type, ResourceType::Texture);
    assert_eq!(info.size, 0);
}

#[test]
fn test_resource_info_with_size() {
    let info = ResourceInfo::with_size(PathBuf::from("texture.dds"), 1024);
    assert_eq!(info.path, PathBuf::from("texture.dds"));
    assert_eq!(info.resource_type, ResourceType::Texture);
    assert_eq!(info.size, 1024);
}
