use super::*;
use std::sync::{Arc, Mutex};
use std::thread;

/// Each request's path and its `(name, value)` headers, in arrival order.
type Seen = Arc<Mutex<Vec<(String, Vec<(String, String)>)>>>;

/// Serves `routes` (path, status, body, optional `Location`) from a localhost
/// `tiny_http` server until dropped; records each request's path and headers.
struct Server {
    base: String,
    seen: Seen,
    server: Arc<tiny_http::Server>,
    worker: Option<thread::JoinHandle<()>>,
}

impl Server {
    fn start(routes: Vec<(&'static str, u16, &'static [u8], Option<&'static str>)>) -> Self {
        let server = Arc::new(tiny_http::Server::http("127.0.0.1:0").expect("bind test server"));
        let base = format!(
            "http://{}",
            server.server_addr().to_ip().expect("ip address")
        );
        let seen: Seen = Arc::default();
        let worker = {
            let server = Arc::clone(&server);
            let seen = Arc::clone(&seen);
            thread::spawn(move || {
                for request in server.incoming_requests() {
                    let headers = request
                        .headers()
                        .iter()
                        .map(|header| (header.field.to_string(), header.value.to_string()))
                        .collect();
                    seen.lock()
                        .expect("lock")
                        .push((request.url().to_owned(), headers));
                    let route = routes.iter().find(|route| route.0 == request.url());
                    let (status, body, location) =
                        route.map_or((404, &b""[..], None), |route| (route.1, route.2, route.3));
                    let mut response =
                        tiny_http::Response::from_data(body).with_status_code(status);
                    if let Some(location) = location {
                        response.add_header(
                            tiny_http::Header::from_bytes("Location", location).expect("header"),
                        );
                    }
                    // A client that hung up is not this test's concern.
                    let _ = request.respond(response);
                }
            })
        };
        Self {
            base,
            seen,
            server,
            worker: Some(worker),
        }
    }

    fn url(&self, path: &str) -> String {
        format!("{}{path}", self.base)
    }
}

impl Drop for Server {
    fn drop(&mut self) {
        self.server.unblock();
        if let Some(worker) = self.worker.take() {
            // A panicking worker already failed its request; nothing to add.
            let _ = worker.join();
        }
    }
}

fn get<'a>(
    url: &'a str,
    headers: &'a [(&'a str, &'a str)],
    user_agent: Option<&'a str>,
) -> Request<'a> {
    Request {
        url,
        headers,
        user_agent,
        socket_timeout: Duration::from_secs(5),
    }
}

#[test]
fn fetch_returns_status_and_body_and_sends_headers_and_user_agent() {
    let server = Server::start(vec![("/a.yaml", 200, b"hello", None)]);
    let url = server.url("/a.yaml");

    let response = fetch(&get(&url, &[("Accept", "*/*")], Some("probe-test/1"))).expect("fetch");

    assert_eq!(
        response,
        Response {
            status: 200,
            body: b"hello".to_vec()
        }
    );
    let seen = server.seen.lock().expect("lock");
    let headers = &seen[0].1;
    let header = |name: &str| {
        headers
            .iter()
            .find(|(field, _)| field.eq_ignore_ascii_case(name))
            .map(|(_, value)| value.clone())
    };
    assert_eq!(header("Accept").as_deref(), Some("*/*"));
    assert_eq!(header("User-Agent").as_deref(), Some("probe-test/1"));
    assert_eq!(header("Authorization"), None);
    // No compression is negotiated, so the hashed body is the served bytes.
    assert_eq!(header("Accept-Encoding"), None);
}

#[test]
fn fetch_follows_redirects_and_reports_error_statuses_as_responses() {
    let server = Server::start(vec![
        ("/moved", 302, b"", Some("/final")),
        ("/final", 200, b"payload", None),
    ]);

    let moved = server.url("/moved");
    assert_eq!(
        fetch(&get(&moved, &[], None)).expect("fetch").body,
        b"payload"
    );

    let missing = server.url("/missing");
    assert_eq!(fetch(&get(&missing, &[], None)).expect("fetch").status, 404);
}

#[test]
fn fetch_reports_a_transport_failure_as_an_error() {
    // Bind then drop a listener so the port is (almost certainly) closed.
    let port = std::net::TcpListener::bind("127.0.0.1:0")
        .expect("bind")
        .local_addr()
        .expect("addr")
        .port();
    let url = format!("http://127.0.0.1:{port}/x");

    assert!(fetch(&get(&url, &[], None)).is_err());
}

#[test]
fn poll_returns_the_first_success_and_reports_each_retry() {
    let mut results = vec![Err("a"), Err("b"), Ok(7)].into_iter();
    let mut retries = Vec::new();

    let polled = poll(
        Schedule {
            timeout: Duration::from_secs(60),
            interval: Duration::ZERO,
        },
        || results.next().expect("attempt result"),
        |attempt, failure: &&str, _remaining| retries.push((attempt, *failure)),
    );

    assert_eq!(
        polled,
        Polled::Ready {
            value: 7,
            attempt: 3
        }
    );
    assert_eq!(retries, [(1, "a"), (2, "b")]);
}

#[test]
fn poll_with_a_zero_timeout_makes_exactly_one_attempt() {
    let mut calls = 0;

    let polled: Polled<(), &str> = poll(
        Schedule {
            timeout: Duration::ZERO,
            interval: Duration::from_secs(10),
        },
        || {
            calls += 1;
            Err("down")
        },
        |_, _, _| panic!("no retry line without time left"),
    );

    assert_eq!(
        polled,
        Polled::TimedOut {
            last: "down",
            attempts: 1
        }
    );
    assert_eq!(calls, 1);
}
