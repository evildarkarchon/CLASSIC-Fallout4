"""Run an adapter against input-only, loopback HTTP response sequences.

This server never proxies, resolves remote hosts, reads credentials, or receives
expectations. Unexpected paths, headers and unused responses fail the launcher.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit


class ControlledUpdateService:
    """Own a loopback listener and bounded request handlers for one invocation."""

    def __init__(self, scenarios: dict):
        """Copy input response sequences; request handlers never inspect oracles."""
        self.remaining = {
            key: {route: list(items) for route, items in value.items()}
            for key, value in scenarios.items()
        }
        self.errors: list[str] = []
        self.lock = threading.Lock()
        self.stopped = threading.Event()
        owner = self

        class Handler(BaseHTTPRequestHandler):
            """Serve only an exact Pages or releases-list route on localhost."""

            def log_message(self, *_args):
                """Keep protocol logs out of adapter receipt output."""

            def send_error(self, code, message=None, explain=None):
                """Record unsupported methods and malformed requests as failures."""
                with owner.lock:
                    owner.errors.append(f"unplanned HTTP error: {code}")
                super().send_error(code, message, explain)

            def do_GET(self):
                """Consume one scripted response or record an unexpected request."""
                parsed = urlsplit(self.path)
                parts = parsed.path.strip("/").split("/")
                case = parts[0]
                route = (
                    "pages"
                    if parts[1:] == ["pages"]
                    else "api"
                    if parts[1:]
                       == ["api", "repos", "conformance", "updates", "releases"]
                    else None
                )
                with owner.lock:
                    queue = owner.remaining.get(case, {}).get(route, [])
                    if route is None or not queue or self.headers.get("Authorization"):
                        owner.errors.append(
                            "unplanned or authenticated request: " + self.path
                        )
                        response = {"status": 500, "body": "unplanned request"}
                    else:
                        response = queue.pop(0)
                        if self.headers.get("If-None-Match") != response.get(
                                "ifNoneMatch"
                        ):
                            owner.errors.append(
                                "unexpected conditional request: " + self.path
                            )
                if response.get("stall"):
                    # Wait for ownership teardown, not a guessed wall-clock delay:
                    # the client must trigger its real configured timeout.
                    owner.stopped.wait()
                    return
                body = response.get("body", "").encode("utf-8")
                try:
                    self.send_response(response["status"])
                    for key, value in response.get("headers", {}).items():
                        self.send_header(key, value)
                    self.send_header("Content-Length", str(len(body)))
                    self.end_headers()
                    self.wfile.write(body)
                except (BrokenPipeError, ConnectionResetError):
                    # A configured client timeout may close the socket first.
                    pass

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.url = f"http://127.0.0.1:{self.server.server_port}"

    def __enter__(self):
        """Start serving before returning the assigned loopback endpoint."""
        self.thread.start()
        return self

    def assert_complete(self):
        """Reject omitted requests as well as extra requests and credential leaks."""
        pending = [
            f"{case}/{route}"
            for case, routes in self.remaining.items()
            for route, responses in routes.items()
            if responses
        ]
        if self.errors or pending:
            raise ValueError(
                "; ".join(self.errors + ["unused responses: " + str(pending)])
            )

    def __exit__(self, *_args):
        """Release stalled handlers and close all service-owned resources."""
        self.stopped.set()
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()


def main(arguments: list[str] | None = None) -> int:
    """Launch the supplied adapter command with a scoped local service endpoint."""
    arguments = sys.argv[1:] if arguments is None else arguments
    if arguments and arguments[0] == "--":
        arguments = arguments[1:]
    plan = json.loads(
        Path(os.environ["CLASSIC_CONFORMANCE_RUN_PLAN"]).read_text(encoding="utf-8")
    )
    scenarios = {
        case["id"]: json.loads(
            Path(plan["fixtures"][case["input"]["fixtureRef"]]).read_text(
                encoding="utf-8"
            )
        )["service"]
        for case in plan["scenarios"]
    }
    with ControlledUpdateService(scenarios) as service:
        environment = os.environ.copy()
        environment["CLASSIC_CONFORMANCE_SERVICE"] = service.url
        # Explicit endpoint clients never infer credentials. NO_PROXY prevents
        # ambient proxy settings from diverting the loopback service requests.
        environment["NO_PROXY"] = "127.0.0.1,localhost"
        result = subprocess.run(arguments, env=environment, check=False)
        service.assert_complete()
        return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
