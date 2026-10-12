//! Anonymous HTTP probing for publish verification: one blocking GET and a
//! fixed-interval poll loop with an overall deadline. Body digests come from
//! [`crate::digest::sha256_hex`].
//!
//! Built on `ureq` (blocking, no Tokio), so xtask never starts an async
//! runtime of its own (AGENTS.md rule 5). Requests carry no credentials: a
//! publish must prove what an anonymous client will see.

use std::time::{Duration, Instant};

/// The largest response body a probe reads. Published assets are a few
/// hundred KiB; the cap only stops a misbehaving server from exhausting
/// memory.
const MAX_BODY_BYTES: u64 = 256 * 1024 * 1024;

/// One anonymous GET.
#[derive(Debug, Clone, Copy)]
pub(crate) struct Request<'a> {
    /// Absolute URL to fetch.
    pub url: &'a str,
    /// Extra request headers, e.g. `("Accept", "*/*")`.
    pub headers: &'a [(&'a str, &'a str)],
    /// `User-Agent` to send; `None` keeps `ureq`'s default.
    pub user_agent: Option<&'a str>,
    /// Applies separately to connecting, awaiting the response head, and
    /// receiving the body (the closest match to a socket timeout).
    pub socket_timeout: Duration,
}

/// A completed HTTP exchange, whatever its status.
#[derive(Debug, Clone, PartialEq, Eq)]
pub(crate) struct Response {
    /// Final status code after redirects.
    pub status: u16,
    /// Full response body.
    pub body: Vec<u8>,
}

/// Performs `request`, following redirects, and returns the final status and
/// body. Error statuses (4xx/5xx) are returned as responses, not errors, so
/// callers can report them.
///
/// # Errors
///
/// Returns a one-line description of a transport failure (DNS, connect,
/// TLS, timeout, or an unreadable body).
pub(crate) fn fetch(request: &Request<'_>) -> Result<Response, String> {
    let mut config = ureq::Agent::config_builder()
        .http_status_as_error(false)
        .timeout_connect(Some(request.socket_timeout))
        .timeout_recv_response(Some(request.socket_timeout))
        .timeout_recv_body(Some(request.socket_timeout));
    if let Some(user_agent) = request.user_agent {
        config = config.user_agent(user_agent);
    }
    let agent = ureq::Agent::new_with_config(config.build());

    let mut builder = agent.get(request.url);
    for (name, value) in request.headers {
        builder = builder.header(*name, *value);
    }
    let mut response = builder.call().map_err(|error| error.to_string())?;
    let status = response.status().as_u16();
    let body = response
        .body_mut()
        .with_config()
        .limit(MAX_BODY_BYTES)
        .read_to_vec()
        .map_err(|error| error.to_string())?;
    Ok(Response { status, body })
}

/// How long a poll may run and how long it waits between attempts.
#[derive(Debug, Clone, Copy)]
pub(crate) struct Schedule {
    /// Overall budget, measured from the start of the poll.
    pub timeout: Duration,
    /// Wait between attempts (shortened near the deadline, never below 1 s
    /// unless the interval itself is shorter).
    pub interval: Duration,
}

/// The end state of [`poll`].
#[derive(Debug, Clone, PartialEq, Eq)]
pub(crate) enum Polled<T, E> {
    /// An attempt succeeded.
    Ready {
        /// The successful attempt's value.
        value: T,
        /// 1-based number of the successful attempt.
        attempt: u32,
    },
    /// The deadline passed; `last` is the final attempt's failure.
    TimedOut {
        /// The last failure seen.
        last: E,
        /// Number of attempts made.
        attempts: u32,
    },
}

/// Runs `attempt` until it succeeds or `schedule.timeout` has elapsed.
///
/// After each failed attempt with time left, `on_retry(attempt, &failure,
/// whole_seconds_remaining)` is called (callers print their retry line), then
/// the loop sleeps `min(interval, max(1 s, whole seconds remaining))`. This
/// is the retired Python tools' loop: at least one attempt always runs, even
/// with a zero timeout.
pub(crate) fn poll<T, E>(
    schedule: Schedule,
    mut attempt: impl FnMut() -> Result<T, E>,
    mut on_retry: impl FnMut(u32, &E, u64),
) -> Polled<T, E> {
    let deadline = Instant::now() + schedule.timeout;
    let mut number = 0;
    loop {
        number += 1;
        let failure = match attempt() {
            Ok(value) => {
                return Polled::Ready {
                    value,
                    attempt: number,
                };
            }
            Err(failure) => failure,
        };
        let remaining = deadline.saturating_duration_since(Instant::now());
        if remaining.is_zero() {
            return Polled::TimedOut {
                last: failure,
                attempts: number,
            };
        }
        let whole_seconds = remaining.as_secs();
        on_retry(number, &failure, whole_seconds);
        std::thread::sleep(
            schedule
                .interval
                .min(Duration::from_secs(whole_seconds.max(1))),
        );
    }
}

#[cfg(test)]
#[path = "probe_tests.rs"]
mod tests;
