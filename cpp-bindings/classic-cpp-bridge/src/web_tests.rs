use super::*;

// ── URL helper tests ─────────────────────────────────────────────────────

#[test]
fn test_is_valid_url_true_for_https() {
    assert!(is_valid_url("https://nexusmods.com"));
}

#[test]
fn test_is_valid_url_false_for_garbage() {
    assert!(!is_valid_url("not-a-url"));
}

#[test]
fn test_validate_url_string_ok_returns_normalized_url() {
    let result = validate_url_string("https://nexusmods.com");
    assert!(result.is_ok(), "expected Ok, got {:?}", result);
    // url::Url::parse normalises to "https://nexusmods.com/" (trailing slash)
    let s = result.unwrap();
    assert!(
        s.starts_with("https://nexusmods.com"),
        "normalized URL should start with the input host, got: {s}"
    );
}

#[test]
fn test_validate_url_string_err_for_garbage() {
    let result = validate_url_string("garbage");
    assert!(result.is_err());
    assert!(
        !result.unwrap_err().is_empty(),
        "error message should be non-empty"
    );
}

#[test]
fn test_extract_domain_string_ok() {
    let result = extract_domain_string("https://nexusmods.com/games/fallout4");
    assert!(result.is_ok(), "expected Ok, got {:?}", result);
    assert_eq!(result.unwrap(), "nexusmods.com");
}

#[test]
fn test_extract_domain_string_err_for_invalid() {
    let result = extract_domain_string("not a url");
    assert!(result.is_err());
}

#[test]
fn test_web_get_user_agent_nonempty() {
    let ua = web_get_user_agent();
    assert!(!ua.is_empty());
    assert!(
        ua.starts_with("CLASSIC/"),
        "user agent should start with CLASSIC/, got: {ua}"
    );
}

#[test]
fn test_web_get_user_agent_with_suffix_contains_suffix() {
    let ua = web_get_user_agent_with_suffix("test-suffix");
    assert!(
        ua.contains("test-suffix"),
        "user agent should contain the suffix, got: {ua}"
    );
}

#[test]
fn test_web_join_url_contains_path() {
    let result = web_join_url("https://example.com", "path");
    assert!(result.is_ok(), "expected Ok, got {:?}", result);
    assert!(result.unwrap().contains("/path"));
}

#[test]
fn test_web_join_url_err_for_invalid_base() {
    let result = web_join_url("not a url", "path");
    assert!(result.is_err());
}

#[test]
fn test_web_build_url_with_query_both_params() {
    let keys = vec!["a".to_string(), "b".to_string()];
    let values = vec!["1".to_string(), "2".to_string()];
    let result = web_build_url_with_query("https://example.com", &keys, &values);
    assert!(result.is_ok(), "expected Ok, got {:?}", result);
    let url = result.unwrap();
    assert!(url.contains("a=1"), "expected a=1 in {url}");
    assert!(url.contains("b=2"), "expected b=2 in {url}");
}

#[test]
fn test_web_build_url_with_query_length_mismatch_returns_err() {
    let keys = vec!["only_one".to_string()];
    let values: Vec<String> = vec![];
    let result = web_build_url_with_query("https://example.com", &keys, &values);
    assert!(result.is_err(), "expected Err for mismatched vec lengths");
}

// ── ModSite helper tests ─────────────────────────────────────────────────

#[test]
fn test_mod_site_name_nexusmods() {
    let expected = CoreModSite::NexusMods.name();
    assert_eq!(mod_site_name(ffi::ModSite::NexusMods), expected);
}

#[test]
fn test_mod_site_base_url_starts_with_https() {
    let url = mod_site_base_url(ffi::ModSite::NexusMods);
    assert!(url.starts_with("https://"), "expected https://, got: {url}");
}

#[test]
fn test_mod_site_game_url_nexusmods_fallout4_nonempty() {
    let url = mod_site_game_url(ffi::ModSite::NexusMods, ffi::WebGameId::Fallout4);
    assert!(!url.is_empty());
}

#[test]
fn test_mod_site_game_url_all_variants_matrix() {
    let sites = [
        ffi::ModSite::NexusMods,
        ffi::ModSite::BethesdaNet,
        ffi::ModSite::ModDB,
    ];
    let games = [
        ffi::WebGameId::Fallout4,
        ffi::WebGameId::Fallout4VR,
        ffi::WebGameId::Skyrim,
        ffi::WebGameId::Starfield,
    ];
    for site in sites {
        for game in games {
            let url = mod_site_game_url(site, game);
            assert!(!url.is_empty(), "mod_site_game_url returned empty string");
        }
    }
}

#[test]
fn test_mod_site_name_all_variants_nonempty() {
    for site in [
        ffi::ModSite::NexusMods,
        ffi::ModSite::BethesdaNet,
        ffi::ModSite::ModDB,
    ] {
        assert!(!mod_site_name(site).is_empty());
    }
}

#[test]
fn test_mod_site_base_url_all_variants_nonempty_https() {
    for site in [
        ffi::ModSite::NexusMods,
        ffi::ModSite::BethesdaNet,
        ffi::ModSite::ModDB,
    ] {
        let url = mod_site_base_url(site);
        assert!(!url.is_empty());
        assert!(url.starts_with("https://"), "expected https://, got: {url}");
    }
}
