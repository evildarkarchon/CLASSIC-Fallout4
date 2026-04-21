use super::*;

#[test]
fn test_get_user_agent() {
    let ua = get_user_agent();
    assert!(ua.starts_with("CLASSIC/"));
    assert!(ua.contains("8.0.0"));
}

#[test]
fn test_get_user_agent_with_suffix() {
    let ua = get_user_agent_with_suffix("Windows");
    assert_eq!(ua, "CLASSIC/8.0.0 (Windows)");
}

#[test]
fn test_validate_url() {
    assert!(validate_url("https://www.nexusmods.com").is_ok());
    assert!(validate_url("http://example.com").is_ok());
    assert!(validate_url("ftp://example.com").is_err());
    assert!(validate_url("not a url").is_err());
}

#[test]
fn test_is_valid_url() {
    assert!(is_valid_url("https://www.nexusmods.com"));
    assert!(is_valid_url("http://example.com"));
    assert!(!is_valid_url("ftp://example.com"));
    assert!(!is_valid_url("not a url"));
}

#[test]
fn test_extract_domain() {
    assert_eq!(
        extract_domain("https://www.nexusmods.com/fallout4").unwrap(),
        "www.nexusmods.com"
    );
    assert_eq!(
        extract_domain("http://example.com:8080/path").unwrap(),
        "example.com"
    );
}

#[test]
fn test_mod_site_base_url() {
    assert_eq!(ModSite::NexusMods.base_url(), "https://www.nexusmods.com");
    assert_eq!(ModSite::BethesdaNet.base_url(), "https://bethesda.net");
    assert_eq!(ModSite::ModDB.base_url(), "https://www.moddb.com");
}

#[test]
fn test_mod_site_name() {
    assert_eq!(ModSite::NexusMods.name(), "Nexus Mods");
    assert_eq!(ModSite::BethesdaNet.name(), "Bethesda.net");
    assert_eq!(ModSite::ModDB.name(), "ModDB");
}

#[test]
fn test_mod_site_game_url() {
    use classic_shared_core::GameId;

    let url = ModSite::NexusMods.game_url(GameId::Fallout4);
    assert_eq!(url, "https://www.nexusmods.com/fallout4");

    let url = ModSite::NexusMods.game_url(GameId::Skyrim);
    assert_eq!(url, "https://www.nexusmods.com/skyrimspecialedition");
}

#[test]
fn test_join_url() {
    let url = join_url("https://example.com", "path/to/resource").unwrap();
    assert_eq!(url, "https://example.com/path/to/resource");
}

#[test]
fn test_build_url_with_query() {
    let params = vec![("page", "1"), ("sort", "popular")];
    let url = build_url_with_query("https://example.com/search", &params).unwrap();
    assert_eq!(url, "https://example.com/search?page=1&sort=popular");
}

// ========================================================================
// Additional Tests for Improved Coverage
// ========================================================================

// Compile-time assertions for version string validity
const _: () = assert!(!CLASSIC_VERSION.is_empty());
const _: () =
    assert!(CLASSIC_VERSION.as_bytes()[1] == b'.' || CLASSIC_VERSION.as_bytes()[3] == b'.');

#[test]
fn test_user_agent_constants() {
    assert_eq!(USER_AGENT_PREFIX, "CLASSIC");
}

#[test]
fn test_get_user_agent_with_various_suffixes() {
    let cases = [
        ("Windows", "CLASSIC/8.0.0 (Windows)"),
        ("Linux", "CLASSIC/8.0.0 (Linux)"),
        ("macOS", "CLASSIC/8.0.0 (macOS)"),
        ("", "CLASSIC/8.0.0 ()"),
        ("Test Suite", "CLASSIC/8.0.0 (Test Suite)"),
    ];

    for (suffix, expected) in cases {
        assert_eq!(get_user_agent_with_suffix(suffix), expected);
    }
}

#[test]
fn test_validate_url_edge_cases() {
    // Valid URLs with various components
    assert!(validate_url("https://example.com").is_ok());
    assert!(validate_url("http://example.com:8080").is_ok());
    assert!(validate_url("https://example.com/path").is_ok());
    assert!(validate_url("https://example.com/path?query=1").is_ok());
    assert!(validate_url("https://example.com/path#anchor").is_ok());
    assert!(validate_url("https://user:pass@example.com").is_ok());

    // URLs with IP addresses
    assert!(validate_url("http://192.168.1.1").is_ok());
    assert!(validate_url("http://127.0.0.1:8080").is_ok());

    // Invalid schemes
    assert!(validate_url("ftp://example.com").is_err());
    assert!(validate_url("file:///path/to/file").is_err());
    assert!(validate_url("mailto:test@example.com").is_err());
    assert!(validate_url("data:text/plain,hello").is_err());

    // Malformed URLs
    assert!(validate_url("").is_err());
    assert!(validate_url("   ").is_err());
    assert!(validate_url("://missing-scheme.com").is_err());
}

#[test]
fn test_is_valid_url_edge_cases() {
    // Various valid HTTP/HTTPS URLs
    assert!(is_valid_url("https://www.google.com"));
    assert!(is_valid_url("http://localhost"));
    assert!(is_valid_url("http://localhost:3000"));
    assert!(is_valid_url("https://api.example.com/v1/users?page=1"));

    // Invalid URLs
    assert!(!is_valid_url(""));
    assert!(!is_valid_url("just text"));
    assert!(!is_valid_url("www.example.com")); // No scheme
    assert!(!is_valid_url("javascript:alert(1)"));
}

#[test]
fn test_extract_domain_edge_cases() {
    // Standard domains
    assert_eq!(
        extract_domain("https://example.com").unwrap(),
        "example.com"
    );
    assert_eq!(
        extract_domain("http://subdomain.example.com").unwrap(),
        "subdomain.example.com"
    );

    // With port
    assert_eq!(
        extract_domain("https://example.com:443").unwrap(),
        "example.com"
    );

    // With path and query
    assert_eq!(
        extract_domain("https://api.example.com/v1/users?id=123").unwrap(),
        "api.example.com"
    );

    // IP addresses
    assert_eq!(
        extract_domain("http://192.168.1.1/path").unwrap(),
        "192.168.1.1"
    );
    assert_eq!(
        extract_domain("http://127.0.0.1:8080").unwrap(),
        "127.0.0.1"
    );
}

#[test]
fn test_extract_domain_errors() {
    // Invalid URL
    let result = extract_domain("not a url");
    assert!(result.is_err());

    // Invalid scheme
    let result = extract_domain("ftp://example.com");
    assert!(result.is_err());
}

#[test]
fn test_mod_site_all_game_urls() {
    use classic_shared_core::GameId;

    // Nexus Mods
    assert_eq!(
        ModSite::NexusMods.game_url(GameId::Fallout4),
        "https://www.nexusmods.com/fallout4"
    );
    assert_eq!(
        ModSite::NexusMods.game_url(GameId::Fallout4VR),
        "https://www.nexusmods.com/fallout4vr"
    );
    assert_eq!(
        ModSite::NexusMods.game_url(GameId::Skyrim),
        "https://www.nexusmods.com/skyrimspecialedition"
    );
    assert_eq!(
        ModSite::NexusMods.game_url(GameId::Starfield),
        "https://www.nexusmods.com/starfield"
    );

    // Bethesda.net (same URL for all games)
    assert_eq!(
        ModSite::BethesdaNet.game_url(GameId::Fallout4),
        "https://bethesda.net/mods"
    );
    assert_eq!(
        ModSite::BethesdaNet.game_url(GameId::Skyrim),
        "https://bethesda.net/mods"
    );

    // ModDB (same URL for all games)
    assert_eq!(
        ModSite::ModDB.game_url(GameId::Fallout4),
        "https://www.moddb.com/games"
    );
    assert_eq!(
        ModSite::ModDB.game_url(GameId::Starfield),
        "https://www.moddb.com/games"
    );
}

#[test]
fn test_mod_site_clone_copy() {
    let site = ModSite::NexusMods;
    let cloned = site;
    let copied = site;

    assert_eq!(site, cloned);
    assert_eq!(site, copied);
}

#[test]
fn test_mod_site_eq_hash() {
    use std::collections::HashSet;

    let mut set = HashSet::new();
    set.insert(ModSite::NexusMods);
    set.insert(ModSite::BethesdaNet);
    set.insert(ModSite::ModDB);

    assert_eq!(set.len(), 3);
    assert!(set.contains(&ModSite::NexusMods));
    assert!(set.contains(&ModSite::BethesdaNet));
    assert!(set.contains(&ModSite::ModDB));

    // Inserting duplicate
    set.insert(ModSite::NexusMods);
    assert_eq!(set.len(), 3);
}

#[test]
fn test_mod_site_serialization() {
    let site = ModSite::NexusMods;

    let json = serde_json::to_string(&site).unwrap();
    let parsed: ModSite = serde_json::from_str(&json).unwrap();

    assert_eq!(site, parsed);
}

#[test]
fn test_mod_site_debug() {
    let site = ModSite::NexusMods;
    let debug = format!("{:?}", site);
    assert!(debug.contains("NexusMods"));
}

#[test]
fn test_join_url_edge_cases() {
    // Trailing slash on base
    let url = join_url("https://example.com/", "path").unwrap();
    assert!(url.contains("path"));

    // Leading slash on path
    let url = join_url("https://example.com", "/path").unwrap();
    assert!(url.contains("path"));

    // Complex path
    let url = join_url("https://example.com/api/v1", "users/123").unwrap();
    assert!(url.contains("users/123"));

    // Empty path - should return base
    let url = join_url("https://example.com/base", "").unwrap();
    assert!(url.contains("example.com"));
}

#[test]
fn test_join_url_errors() {
    // Invalid base URL
    let result = join_url("not a url", "path");
    assert!(result.is_err());

    // Invalid scheme
    let result = join_url("ftp://example.com", "path");
    assert!(result.is_err());
}

#[test]
fn test_build_url_with_query_edge_cases() {
    // Empty params - URL library may add trailing ? which is still valid
    let url = build_url_with_query("https://example.com/search", &[]).unwrap();
    // Just verify it's still a valid URL and has the base
    assert!(url.starts_with("https://example.com/search"));

    // Single param
    let url = build_url_with_query("https://example.com/search", &[("q", "test")]).unwrap();
    assert_eq!(url, "https://example.com/search?q=test");

    // Multiple params
    let params = vec![("a", "1"), ("b", "2"), ("c", "3")];
    let url = build_url_with_query("https://example.com", &params).unwrap();
    assert!(url.contains("a=1"));
    assert!(url.contains("b=2"));
    assert!(url.contains("c=3"));

    // Params with special characters
    let params = vec![("q", "hello world"), ("tag", "c++")];
    let url = build_url_with_query("https://example.com/search", &params).unwrap();
    assert!(url.contains("q=hello"));
    assert!(url.contains("tag=c"));
}

#[test]
fn test_build_url_with_query_errors() {
    // Invalid base URL
    let result = build_url_with_query("not a url", &[("q", "test")]);
    assert!(result.is_err());

    // Invalid scheme
    let result = build_url_with_query("ftp://example.com", &[("q", "test")]);
    assert!(result.is_err());
}

#[test]
fn test_web_error_display() {
    let err = WebError::InvalidUrl("test url".to_string());
    let display = format!("{}", err);
    assert!(display.contains("Invalid URL"));
    assert!(display.contains("test url"));

    let err = WebError::InvalidScheme("ftp".to_string());
    let display = format!("{}", err);
    assert!(display.contains("Invalid URL scheme"));
    assert!(display.contains("ftp"));
}

#[test]
fn test_web_error_debug() {
    let err = WebError::InvalidUrl("test".to_string());
    let debug = format!("{:?}", err);
    assert!(debug.contains("InvalidUrl"));
}

#[test]
fn test_web_error_from_url_parse_error() {
    let url_err = url::Url::parse(":::").unwrap_err();
    let err: WebError = url_err.into();

    let display = format!("{}", err);
    assert!(display.contains("URL parse error"));
}

#[test]
fn test_web_result_type() {
    fn returns_ok() -> WebResult<String> {
        Ok("success".to_string())
    }

    fn returns_err() -> WebResult<String> {
        Err(WebError::InvalidUrl("test".to_string()))
    }

    assert!(returns_ok().is_ok());
    assert!(returns_err().is_err());
}

#[test]
fn test_validate_url_returns_parsed_url() {
    let url = validate_url("https://www.nexusmods.com/fallout4").unwrap();

    assert_eq!(url.scheme(), "https");
    assert_eq!(url.host_str(), Some("www.nexusmods.com"));
    assert_eq!(url.path(), "/fallout4");
}

#[test]
fn test_unicode_in_urls() {
    // Unicode in path should work
    let url = validate_url("https://example.com/path/файл");
    assert!(url.is_ok());

    // Unicode domain (punycode)
    // Note: This might or might not work depending on URL parsing
    let url = validate_url("https://example.com/中文路径");
    assert!(url.is_ok());
}

#[test]
fn test_url_with_fragments() {
    let url = validate_url("https://example.com/page#section").unwrap();
    assert_eq!(url.fragment(), Some("section"));
}

#[test]
fn test_url_with_username_password() {
    let url = validate_url("https://user:password@example.com").unwrap();
    assert_eq!(url.username(), "user");
    assert_eq!(url.password(), Some("password"));
}

#[test]
fn test_long_url() {
    let long_path = "a".repeat(1000);
    let url_str = format!("https://example.com/{}", long_path);
    let result = validate_url(&url_str);
    assert!(result.is_ok());
}

#[test]
fn test_mod_site_all_variants_covered() {
    // Ensure all variants are tested
    let sites = [ModSite::NexusMods, ModSite::BethesdaNet, ModSite::ModDB];

    for site in sites {
        // Each should have a base_url
        assert!(!site.base_url().is_empty());
        assert!(site.base_url().starts_with("https://"));

        // Each should have a name
        assert!(!site.name().is_empty());
    }
}
