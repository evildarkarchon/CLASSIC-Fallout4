//! The controlled update service: a loopback HTTP fake for the
//! `update-services` and `yaml-update-operations` families.
//!
//! Those families' participants talk to a release service. Each scenario's
//! fixture scripts it under `service`: per route, a queue of responses
//! `{status, body, headers, ifNoneMatch?, stall?}`. The fake serves exactly
//! that script on `127.0.0.1:<ephemeral port>`:
//!
//! - `GET /<scenario>/pages` takes the next `pages` response, and
//!   `GET /<scenario>/api/repos/conformance/updates/releases` the next `api`
//!   response. Proxy-style absolute URLs are read by their path.
//! - A request on any other path, an exhausted queue, or a request carrying
//!   `Authorization` is recorded as an error and answered `500`.
//! - A request whose `If-None-Match` differs from the response's
//!   `ifNoneMatch` is recorded as an error (it is still answered).
//! - A `stall` response is never answered until the service stops, so the
//!   participant's own configured timeout fires.
//! - Any other method is recorded and answered `501`.
//!
//! [`ControlledUpdateService::finish`] stops the service and fails when any
//! error was recorded or any scripted response went unused. The service never
//! proxies, never resolves a remote host and never sees an expectation: the
//! run plan's input fixtures are all it reads.
//!
//! It runs on blocking threads (no Tokio; AGENTS.md rule 5). The participant
//! learns the address from `CLASSIC_CONFORMANCE_SERVICE`, and `NO_PROXY`
//! keeps ambient proxy settings from diverting loopback requests.

use std::collections::BTreeMap;
use std::sync::{Arc, Condvar, Mutex};
use std::thread::JoinHandle;

use anyhow::{Context, Result, bail};
use serde::Deserialize;
use serde_json::Value;

/// Families whose participants need the controlled update service.
pub(crate) const FAMILIES: [&str; 2] = ["update-services", "yaml-update-operations"];

/// The participant environment variable naming the service's base URL.
pub(crate) const SERVICE_ENV: &str = "CLASSIC_CONFORMANCE_SERVICE";

/// One scripted response.
#[derive(Debug, Clone, Deserialize)]
#[serde(rename_all = "camelCase")]
pub(crate) struct Scripted {
    /// HTTP status.
    #[serde(default = "default_status")]
    pub status: u16,
    /// Response body.
    #[serde(default)]
    pub body: String,
    /// Response headers.
    #[serde(default)]
    pub headers: BTreeMap<String, String>,
    /// The `If-None-Match` the request must carry (absent: none).
    #[serde(default)]
    pub if_none_match: Option<String>,
    /// Hold the request unanswered until the service stops.
    #[serde(default)]
    pub stall: bool,
}

fn default_status() -> u16 {
    200
}

/// One scenario's script: the `pages` and `api` queues.
#[derive(Debug, Clone, Default, Deserialize)]
pub(crate) struct Script {
    /// Responses for `/<scenario>/pages`.
    #[serde(default)]
    pub pages: Vec<Scripted>,
    /// Responses for `/<scenario>/api/repos/conformance/updates/releases`.
    #[serde(default)]
    pub api: Vec<Scripted>,
}

/// Reads each planned scenario's script from its input fixture's `service`
/// member, keyed by scenario ID.
///
/// # Errors
///
/// Fails when a scenario's input names no fixture, the fixture cannot be read
/// or parsed, or its `service` member is not a script.
pub(crate) fn scripts_from_plan(plan: &Value) -> Result<BTreeMap<String, Script>> {
    let mut scripts = BTreeMap::new();
    for scenario in plan["scenarios"].as_array().into_iter().flatten() {
        let id = scenario["id"]
            .as_str()
            .context("planned scenario without an id")?;
        let reference = scenario["input"]["fixtureRef"]
            .as_str()
            .with_context(|| format!("scenario {id} names no input fixture"))?;
        let path = plan["fixtures"][reference]
            .as_str()
            .with_context(|| format!("scenario {id} fixture {reference} is not planned"))?;
        let text = std::fs::read_to_string(path).with_context(|| format!("reading {path}"))?;
        let fixture: Value =
            serde_json::from_str(&text).with_context(|| format!("parsing {path}"))?;
        let script: Script = serde_json::from_value(fixture["service"].clone())
            .with_context(|| format!("scenario {id} has no valid service script"))?;
        scripts.insert(id.to_owned(), script);
    }
    Ok(scripts)
}

/// Mutable service state, shared by the request handlers.
#[derive(Debug, Default)]
struct State {
    /// Remaining responses per (scenario, route).
    remaining: BTreeMap<(String, &'static str), Vec<Scripted>>,
    /// Recorded protocol errors.
    errors: Vec<String>,
}

/// A running controlled update service; stop it with [`Self::finish`].
pub(crate) struct ControlledUpdateService {
    url: String,
    server: Arc<tiny_http::Server>,
    state: Arc<Mutex<State>>,
    stopped: Arc<(Mutex<bool>, Condvar)>,
    acceptor: Option<JoinHandle<Vec<JoinHandle<()>>>>,
}

impl ControlledUpdateService {
    /// Starts serving `scripts` on an ephemeral loopback port.
    ///
    /// # Errors
    ///
    /// Fails when the loopback listener cannot be bound.
    pub fn start(scripts: BTreeMap<String, Script>) -> Result<Self> {
        let server = tiny_http::Server::http("127.0.0.1:0")
            .map_err(|error| anyhow::anyhow!("binding the controlled update service: {error}"))?;
        let Some(address) = server.server_addr().to_ip() else {
            bail!("the controlled update service did not bind an IP address");
        };
        let mut remaining = BTreeMap::new();
        for (scenario, script) in scripts {
            remaining.insert((scenario.clone(), "pages"), script.pages);
            remaining.insert((scenario, "api"), script.api);
        }
        let state = Arc::new(Mutex::new(State {
            remaining,
            errors: Vec::new(),
        }));
        let server = Arc::new(server);
        let stopped = Arc::new((Mutex::new(false), Condvar::new()));
        let acceptor = {
            let (server, state, stopped) = (
                Arc::clone(&server),
                Arc::clone(&state),
                Arc::clone(&stopped),
            );
            std::thread::spawn(move || {
                let mut handlers = Vec::new();
                for request in server.incoming_requests() {
                    let (state, stopped) = (Arc::clone(&state), Arc::clone(&stopped));
                    // One thread per request, so a stalled response never
                    // blocks the next request.
                    handlers.push(std::thread::spawn(move || {
                        handle(request, &state, &stopped)
                    }));
                }
                handlers
            })
        };
        Ok(Self {
            url: format!("http://{address}"),
            server,
            state,
            stopped,
            acceptor: Some(acceptor),
        })
    }

    /// The base URL, `http://127.0.0.1:<port>`.
    pub fn url(&self) -> &str {
        &self.url
    }

    /// Stops the service, releasing stalled requests, and reports whether the
    /// participant followed the script exactly.
    ///
    /// # Errors
    ///
    /// Returns every recorded error plus the scripted responses nobody
    /// requested, joined with `; `.
    pub fn finish(mut self) -> std::result::Result<(), String> {
        self.stop();
        let state = self.state.lock().expect("service state lock");
        let unused: Vec<String> = state
            .remaining
            .iter()
            .filter(|(_, queue)| !queue.is_empty())
            .map(|((scenario, route), _)| format!("{scenario}/{route}"))
            .collect();
        let mut problems = state.errors.clone();
        if !unused.is_empty() {
            problems.push(format!("unused responses: {}", unused.join(", ")));
        }
        if problems.is_empty() {
            Ok(())
        } else {
            Err(problems.join("; "))
        }
    }

    fn stop(&mut self) {
        let (flag, signal) = &*self.stopped;
        *flag.lock().expect("stop flag lock") = true;
        signal.notify_all();
        self.server.unblock();
        if let Some(acceptor) = self.acceptor.take()
            && let Ok(handlers) = acceptor.join()
        {
            for handler in handlers {
                // A handler that panicked already recorded nothing useful;
                // the service result does not depend on it.
                let _ = handler.join();
            }
        }
    }
}

impl Drop for ControlledUpdateService {
    fn drop(&mut self) {
        self.stop();
    }
}

/// The route `url` names: `(scenario, route)`, with proxy-style absolute
/// URLs read by their path and any query ignored.
fn route(url: &str) -> Option<(String, &'static str)> {
    let path = match url.split_once("://") {
        Some((_, rest)) => rest.find('/').map_or("/", |index| &rest[index..]),
        None => url,
    };
    let path = path.split(['?', '#']).next().unwrap_or("");
    let parts: Vec<&str> = path.trim_matches('/').split('/').collect();
    match parts.as_slice() {
        [scenario, "pages"] => Some(((*scenario).to_owned(), "pages")),
        [
            scenario,
            "api",
            "repos",
            "conformance",
            "updates",
            "releases",
        ] => Some(((*scenario).to_owned(), "api")),
        _ => None,
    }
}

/// Answers one request from the script, recording any deviation.
fn handle(request: tiny_http::Request, state: &Mutex<State>, stopped: &(Mutex<bool>, Condvar)) {
    let header = |name: &str| {
        request
            .headers()
            .iter()
            .find(|header| header.field.to_string().eq_ignore_ascii_case(name))
            .map(|header| header.value.as_str().to_owned())
    };
    if *request.method() != tiny_http::Method::Get {
        state
            .lock()
            .expect("service state lock")
            .errors
            .push(format!(
                "unplanned HTTP error: 501 ({} {})",
                request.method(),
                request.url()
            ));
        // A client that hung up is not the service's concern.
        let _ = request.respond(
            tiny_http::Response::from_data(b"unsupported method".to_vec()).with_status_code(501),
        );
        return;
    }
    let response = {
        let mut state = state.lock().expect("service state lock");
        let queued = route(request.url())
            .filter(|_| header("Authorization").is_none())
            .and_then(|key| state.remaining.get_mut(&key))
            .filter(|queue| !queue.is_empty())
            .map(|queue| queue.remove(0));
        match queued {
            None => {
                state.errors.push(format!(
                    "unplanned or authenticated request: {}",
                    request.url()
                ));
                None
            }
            Some(response) => {
                if header("If-None-Match") != response.if_none_match {
                    state
                        .errors
                        .push(format!("unexpected conditional request: {}", request.url()));
                }
                Some(response)
            }
        }
    };
    let Some(response) = response else {
        let _ = request.respond(
            tiny_http::Response::from_data(b"unplanned request".to_vec()).with_status_code(500),
        );
        return;
    };
    if response.stall {
        // Hold the request until the service stops: the participant's real
        // configured timeout must fire, not a guessed delay here.
        let (flag, signal) = stopped;
        let mut done = flag.lock().expect("stop flag lock");
        while !*done {
            done = signal.wait(done).expect("stop flag wait");
        }
        return;
    }
    // `from_data` adds no Content-Type: the script's headers are the only
    // ones the participant sees, as with the retired Python service.
    let mut reply = tiny_http::Response::from_data(response.body.into_bytes())
        .with_status_code(response.status);
    for (name, value) in &response.headers {
        if let Ok(header) = tiny_http::Header::from_bytes(name.as_bytes(), value.as_bytes()) {
            reply.add_header(header);
        }
    }
    let _ = request.respond(reply);
}

#[cfg(test)]
#[path = "update_service_tests.rs"]
mod tests;
