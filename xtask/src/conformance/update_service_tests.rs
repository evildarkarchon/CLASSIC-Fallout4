//! The controlled update service, driven in-process with the request shapes
//! of both families that use it: update-services' Pages and releases-API
//! checks with ETag revalidation and a stalled service, and
//! yaml-update-operations' repeated Pages reads through a proxy URL.

use std::time::Duration;

use serde_json::json;

use super::*;

/// A blocking client that returns every status as a response.
fn agent(timeout: Duration) -> ureq::Agent {
    let config = ureq::Agent::config_builder()
        .http_status_as_error(false)
        .timeout_global(Some(timeout))
        .build();
    ureq::Agent::new_with_config(config)
}

/// `(status, body)` of a GET, with optional `If-None-Match`.
fn get(url: &str, if_none_match: Option<&str>) -> Result<(u16, String), ureq::Error> {
    let mut request = agent(Duration::from_secs(10)).get(url);
    if let Some(tag) = if_none_match {
        request = request.header("If-None-Match", tag);
    }
    let mut response = request.call()?;
    let status = response.status().as_u16();
    let body = response.body_mut().read_to_string().unwrap_or_default();
    Ok((status, body))
}

fn script(value: serde_json::Value) -> Script {
    serde_json::from_value(value).expect("script deserializes")
}

fn service(scripts: &[(&str, serde_json::Value)]) -> ControlledUpdateService {
    ControlledUpdateService::start(
        scripts
            .iter()
            .map(|(id, value)| ((*id).to_owned(), script(value.clone())))
            .collect(),
    )
    .expect("service starts")
}

#[test]
fn update_services_requests_follow_the_script_with_revalidation() {
    let service = service(&[(
        "cache-revalidation",
        json!({
            "pages": [
                {"status": 200, "body": "{\"latest_version\":\"9.2.0\"}", "headers": {"ETag": "\"v1\""}},
                {"status": 304, "body": "", "headers": {}, "ifNoneMatch": "\"v1\""}
            ],
            "api": [{"status": 200, "body": "[]", "headers": {}}]
        }),
    )]);
    let base = format!("{}/cache-revalidation", service.url());
    assert!(service.url().starts_with("http://127.0.0.1:"));
    assert_eq!(
        get(&format!("{base}/pages"), None).unwrap(),
        (200, "{\"latest_version\":\"9.2.0\"}".to_owned())
    );
    assert_eq!(
        get(&format!("{base}/pages"), Some("\"v1\"")).unwrap().0,
        304
    );
    assert_eq!(
        get(
            &format!("{base}/api/repos/conformance/updates/releases"),
            None
        )
        .unwrap(),
        (200, "[]".to_owned())
    );
    assert_eq!(service.finish(), Ok(()));
}

#[test]
fn unplanned_requests_and_unused_responses_fail_the_service() {
    let service = service(&[(
        "available",
        json!({"pages": [{"status": 404, "body": ""}], "api": [{"status": 200, "body": "[]"}]}),
    )]);
    let base = format!("{}/available", service.url());
    assert_eq!(get(&format!("{base}/elsewhere"), None).unwrap().0, 500);
    let mut authenticated = agent(Duration::from_secs(10))
        .get(&format!("{base}/pages"))
        .header("Authorization", "token secret")
        .call()
        .unwrap();
    assert_eq!(authenticated.status().as_u16(), 500);
    let _ = authenticated.body_mut().read_to_string();
    // A conditional request the script did not plan is recorded.
    assert_eq!(
        get(&format!("{base}/pages"), Some("\"stale\"")).unwrap().0,
        404
    );
    let problems = service.finish().unwrap_err();
    assert!(
        problems.contains("unplanned or authenticated request: /available/elsewhere"),
        "{problems}"
    );
    assert!(
        problems.contains("unplanned or authenticated request: /available/pages"),
        "{problems}"
    );
    assert!(
        problems.contains("unexpected conditional request"),
        "{problems}"
    );
    assert!(
        problems.contains("unused responses: available/api"),
        "{problems}"
    );
}

#[test]
fn a_stalled_response_waits_for_the_client_timeout_and_releases_on_finish() {
    let service = service(&[("timeout", json!({"pages": [{"stall": true}], "api": []}))]);
    let started = std::time::Instant::now();
    let result = agent(Duration::from_millis(300))
        .get(&format!("{}/timeout/pages", service.url()))
        .call();
    assert!(
        result.is_err(),
        "the stalled request must time out: {result:?}"
    );
    assert!(started.elapsed() < Duration::from_secs(5));
    assert_eq!(service.finish(), Ok(()));
}

#[test]
fn other_methods_are_unplanned() {
    let service = service(&[("current", json!({"pages": [], "api": []}))]);
    let response = agent(Duration::from_secs(10))
        .post(&format!("{}/current/pages", service.url()))
        .send("x")
        .unwrap();
    assert_eq!(response.status().as_u16(), 501);
    let problems = service.finish().unwrap_err();
    assert!(problems.contains("unplanned HTTP error: 501"), "{problems}");
}

#[test]
fn yaml_update_operations_read_pages_repeatedly_through_a_proxy_url() {
    let manifest = "{\"files\":[],\"manifest_version\":1}";
    let service = service(&[(
        "controlled-consent",
        json!({
            "pages": [
                {"status": 200, "body": manifest, "headers": {}},
                {"status": 200, "body": manifest, "headers": {}}
            ],
            "api": []
        }),
    )]);
    let pages = format!("{}/controlled-consent/pages", service.url());
    assert_eq!(get(&pages, None).unwrap(), (200, manifest.to_owned()));
    assert_eq!(get(&pages, None).unwrap(), (200, manifest.to_owned()));
    assert_eq!(service.finish(), Ok(()));

    // A proxy-style absolute request target is routed by its path.
    assert_eq!(
        route("http://127.0.0.1:9/controlled-consent/pages?x=1"),
        Some(("controlled-consent".to_owned(), "pages"))
    );
    assert_eq!(
        route("/a/api/repos/conformance/updates/releases"),
        Some(("a".to_owned(), "api"))
    );
    assert_eq!(route("/a/api/repos/other/releases"), None);
}

#[test]
fn scripts_come_from_the_planned_input_fixtures() {
    let dir = tempfile::tempdir().unwrap();
    let fixture = dir.path().join("current.json");
    std::fs::write(
        &fixture,
        serde_json::to_vec(&json!({"installedVersion": "9.1.0", "service": {"pages": [{"status": 404, "body": ""}], "api": []}})).unwrap(),
    )
    .unwrap();
    let plan = json!({
        "fixtures": {"current": fixture.to_string_lossy()},
        "scenarios": [{"id": "current", "input": {"fixtureRef": "current"}}]
    });
    let scripts = scripts_from_plan(&plan).unwrap();
    assert_eq!(scripts["current"].pages.len(), 1);
    assert_eq!(scripts["current"].pages[0].status, 404);
    assert!(scripts["current"].api.is_empty());

    let broken = json!({"fixtures": {}, "scenarios": [{"id": "x", "input": {"fixtureRef": "x"}}]});
    assert!(scripts_from_plan(&broken).is_err());
}
