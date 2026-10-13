//! A localhost `tiny_http` server for the publish-probe tests.
//!
//! Routes map a request path to a queue of `(status, body)` responses: each
//! request takes the next one, and the last is repeated once the queue is down
//! to one. Unknown paths get 404.

use std::collections::HashMap;
use std::sync::{Arc, Mutex};
use std::thread;

type Routes = Arc<Mutex<HashMap<String, Vec<(u16, Vec<u8>)>>>>;

/// A running server; stopped when dropped.
pub struct TestServer {
    base: String,
    routes: Routes,
    hits: Arc<Mutex<Vec<String>>>,
    server: Arc<tiny_http::Server>,
    worker: Option<thread::JoinHandle<()>>,
}

impl TestServer {
    /// Starts an empty server on `127.0.0.1:<free port>`.
    pub fn start() -> Self {
        let server = Arc::new(tiny_http::Server::http("127.0.0.1:0").expect("bind test server"));
        let base = format!(
            "http://{}",
            server.server_addr().to_ip().expect("ip listener")
        );
        let routes: Routes = Arc::default();
        let hits = Arc::new(Mutex::new(Vec::new()));
        let worker = {
            let (server, routes, hits) =
                (Arc::clone(&server), Arc::clone(&routes), Arc::clone(&hits));
            thread::spawn(move || {
                for request in server.incoming_requests() {
                    let path = request.url().to_owned();
                    hits.lock().expect("lock").push(path.clone());
                    let (status, body) = {
                        let mut routes = routes.lock().expect("lock");
                        match routes.get_mut(&path) {
                            Some(queue) if queue.len() > 1 => queue.remove(0),
                            Some(queue) if !queue.is_empty() => queue[0].clone(),
                            _ => (404, Vec::new()),
                        }
                    };
                    // A client that hung up is not the test's concern.
                    let _ = request
                        .respond(tiny_http::Response::from_data(body).with_status_code(status));
                }
            })
        };
        Self {
            base,
            routes,
            hits,
            server,
            worker: Some(worker),
        }
    }

    /// Serves `responses` in order for `path` (which starts with `/`).
    pub fn route(&self, path: &str, responses: Vec<(u16, Vec<u8>)>) {
        self.routes
            .lock()
            .expect("lock")
            .insert(path.to_owned(), responses);
    }

    /// The absolute URL of `path`.
    pub fn url(&self, path: &str) -> String {
        format!("{}{path}", self.base)
    }

    /// The server root URL, with no trailing slash.
    pub fn base(&self) -> &str {
        &self.base
    }

    /// How many requests `path` has received.
    pub fn hits(&self, path: &str) -> usize {
        self.hits
            .lock()
            .expect("lock")
            .iter()
            .filter(|hit| *hit == path)
            .count()
    }
}

impl Drop for TestServer {
    fn drop(&mut self) {
        self.server.unblock();
        if let Some(worker) = self.worker.take() {
            // A panicked worker has already failed its request; nothing to add.
            let _ = worker.join();
        }
    }
}
