use super::*;

// ── User-agent helper tests ──────────────────────────────────────────────

#[test]
fn test_web_get_user_agent_nonempty() {
    let ua = web_get_user_agent();
    assert!(!ua.is_empty());
    assert!(
        ua.starts_with("CLASSIC/"),
        "user agent should start with CLASSIC/, got: {ua}"
    );
}
