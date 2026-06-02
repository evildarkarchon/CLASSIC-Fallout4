"""Local dry-run harness for the app-notification publish workflow.

This script mirrors the source-only, side-effect-free portions of
``.github/workflows/publish-app-notification.yml`` so maintainers can verify
``app-notification-v<SEMVER>`` tags, generated manifest bytes, Pages staging,
and gate ordering without pushing a throwaway tag or touching GitHub Releases.
"""

from __future__ import annotations

import argparse
import functools
import http.server
import shutil
import socketserver
import subprocess
import sys
import tempfile
import threading
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Iterator, Sequence
from urllib.parse import quote

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools.publish_app_notification import validate  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SOURCE = REPO_ROOT / "CLASSIC Data" / "app-notification.yaml"
STAGED_MANIFEST_REL = Path("staging") / "manifest.json"
PAGES_LATEST_REL = Path("gh-pages") / "app-notification" / "manifest-latest.json"
RELEASE_ASSET_REL = Path("releases") / "download"

_STALE_MANIFEST_BYTES = b"""\
{
  "manifest_version": "1.0",
  "release_tag": "v0.0.0",
  "latest_version": "0.0.0",
  "published_at": "1970-01-01T00:00:00Z"
}
"""


def _configure_line_buffering() -> None:
    """Line-buffer dry-run output so subprocess logs keep workflow order."""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(line_buffering=True)
        except AttributeError:
            # Some test doubles only implement the basic file-like surface.
            continue


_configure_line_buffering()


class _QuietHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    """HTTP file handler that keeps dry-run output focused on workflow steps."""

    def log_message(self, _format: str, *_args: object) -> None:
        # Suppress per-request access logs; the probe scripts print the result.
        return


class _ReusableThreadingHTTPServer(socketserver.ThreadingMixIn, http.server.HTTPServer):
    """Threaded localhost server with address reuse for fast pytest runs."""

    allow_reuse_address = True
    daemon_threads = True


def _step(number: int, message: str) -> None:
    """Print a stable workflow-step marker for dry-run transcripts."""
    print(f"[{number}/9] {message}")


def _print_failures(errors: Sequence[str]) -> None:
    """Print validator errors using the existing workflow log convention."""
    for err in errors:
        print(f"FAIL: {err}", file=sys.stderr)


def _run(cmd: Sequence[str]) -> int:
    """Run a helper script and stream its output to the caller."""
    print("+ " + " ".join(cmd))
    completed = subprocess.run(cmd, cwd=REPO_ROOT, check=False)
    return completed.returncode


def _git_stdout(args: Sequence[str]) -> str | None:
    """Return trimmed ``git`` stdout, or ``None`` if the command fails."""
    completed = subprocess.run(
        ["git", *args],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        return None
    text = completed.stdout.strip()
    return text or None


def _utc_now_rfc3339() -> str:
    """Return current UTC time in the RFC 3339 shape accepted by the manifest."""
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def resolve_published_at(
    workflow_tag: str,
    explicit: str | None,
    require_existing_tag: bool,
) -> tuple[str, str]:
    """Resolve the timestamp used when the source leaves ``published_at`` null.

    The GitHub workflow runs on an existing tag, so it prefers annotated tagger
    time and falls back to the tagged commit's committer time. The local harness
    uses the same lookup when the tag exists locally, but can fall back to the
    current UTC time so maintainers do not need to create a temporary tag.
    """
    if explicit:
        return explicit, "--published-at argument"

    tag_ref = f"refs/tags/{workflow_tag}"
    tagger_ts = _git_stdout(
        ["for-each-ref", "--format=%(taggerdate:iso-strict)", tag_ref]
    )
    if tagger_ts:
        return tagger_ts, f"local annotated tag {workflow_tag}"

    commit_ts = _git_stdout(["log", "-1", "--format=%cI", workflow_tag])
    if commit_ts:
        return commit_ts, f"local lightweight tag/commit {workflow_tag}"

    if require_existing_tag:
        raise SystemExit(
            "FAIL: workflow tag does not exist locally, so no workflow timestamp "
            "could be resolved. Pass --published-at or omit --require-existing-tag."
        )

    return _utc_now_rfc3339(), "current UTC time (tag does not exist locally)"


def _prepare_work_dir(path: Path | None) -> Path:
    """Create and return the root used for dry-run outputs."""
    if path is not None:
        path.mkdir(parents=True, exist_ok=True)
        return path.resolve()
    return Path(tempfile.mkdtemp(prefix="classic-app-notification-dry-run-")).resolve()


def _stage_release_asset(
    work_dir: Path,
    workflow_tag: str,
    manifest: Path,
    stale: bool,
) -> Path:
    """Stage the local file that stands in for the GitHub release asset."""
    asset_path = work_dir / RELEASE_ASSET_REL / workflow_tag / "manifest.json"
    asset_path.parent.mkdir(parents=True, exist_ok=True)
    if stale:
        asset_path.write_bytes(_STALE_MANIFEST_BYTES)
    else:
        shutil.copyfile(manifest, asset_path)
    return asset_path


def _stage_pages(
    work_dir: Path,
    workflow_tag: str,
    manifest: Path,
    stale: bool,
) -> tuple[Path, Path]:
    """Stage the two ``gh-pages`` files written by the publish workflow."""
    latest_path = work_dir / PAGES_LATEST_REL
    tagged_path = (
        work_dir
        / "gh-pages"
        / "app-notification"
        / f"manifest-{workflow_tag}.json"
    )
    latest_path.parent.mkdir(parents=True, exist_ok=True)
    if stale:
        latest_path.write_bytes(_STALE_MANIFEST_BYTES)
        tagged_path.write_bytes(_STALE_MANIFEST_BYTES)
    else:
        shutil.copyfile(manifest, latest_path)
        shutil.copyfile(manifest, tagged_path)
    return latest_path, tagged_path


@contextmanager
def _serve_directory(root: Path) -> Iterator[str]:
    """Serve ``root`` on a temporary localhost URL for reused probe scripts."""
    handler = functools.partial(_QuietHTTPRequestHandler, directory=str(root))
    server = _ReusableThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        host, port = server.server_address
        yield f"http://{host}:{port}"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def _run_generate_manifest(source: Path, output: Path, published_at: str) -> int:
    """Run the existing manifest generator with the dry-run timestamp."""
    return _run(
        [
            sys.executable,
            "tools/publish_app_notification/generate_manifest.py",
            "--source",
            str(source),
            "--output",
            str(output),
            "--published-at",
            published_at,
        ]
    )


def _run_release_probe(
    base_url: str,
    workflow_tag: str,
    manifest: Path,
    timeout: int,
) -> int:
    """Run the existing release-asset probe against the local staged asset."""
    quoted_tag = quote(workflow_tag, safe="")
    return _run(
        [
            sys.executable,
            "tools/publish_app_notification/verify_release_asset.py",
            "--url",
            f"{base_url}/releases/download/{quoted_tag}/manifest.json",
            "--expected-body-path",
            str(manifest),
            "--timeout-seconds",
            str(timeout),
            "--poll-interval-seconds",
            "1",
        ]
    )


def _run_pages_smoke(base_url: str, manifest: Path, timeout: int) -> int:
    """Run the reused Pages smoke-test helper against the local staged Pages tree."""
    return _run(
        [
            sys.executable,
            "tools/publish_yaml_data/smoke_test_pages.py",
            "--base-url",
            f"{base_url}/gh-pages",
            "--expected-body-path",
            str(manifest),
            "--pages-path",
            "app-notification/manifest-latest.json",
            "--timeout-seconds",
            str(timeout),
            "--poll-interval-seconds",
            "1",
        ]
    )


def run(args: argparse.Namespace) -> int:
    """Execute the local dry-run workflow and return its process exit code."""
    source = args.source.resolve()

    _step(1, "Validate app-notification workflow tag")
    tag_errors = validate.validate_workflow_tag(args.workflow_tag)
    if tag_errors:
        _print_failures(tag_errors)
        return 1
    print(f"OK: {args.workflow_tag} passes app-notification tag validation")

    _step(2, "Validate app-notification source")
    source_errors = validate.validate_path(source)
    if source_errors:
        _print_failures(source_errors)
        return 1
    print(f"OK: {source} passes app-notification validation")

    _step(3, "Resolve tag publication timestamp")
    try:
        published_at, timestamp_source = resolve_published_at(
            args.workflow_tag,
            args.published_at,
            args.require_existing_tag,
        )
    except SystemExit as err:
        print(str(err), file=sys.stderr)
        return 1
    print(f"published_at={published_at} ({timestamp_source})")

    work_dir = _prepare_work_dir(args.work_dir)
    manifest_path = work_dir / STAGED_MANIFEST_REL

    _step(4, "Generate manifest.json")
    if _run_generate_manifest(source, manifest_path, published_at) != 0:
        return 1
    print(f"staged manifest: {manifest_path}")

    with _serve_directory(work_dir) as base_url:
        _step(5, "Stage local release asset")
        asset_path = _stage_release_asset(
            work_dir,
            args.workflow_tag,
            manifest_path,
            args.simulate_release_asset_mismatch,
        )
        print(f"staged release asset: {asset_path}")

        _step(6, "Verify local release asset with existing probe")
        if (
            _run_release_probe(
                base_url,
                args.workflow_tag,
                manifest_path,
                args.timeout_seconds,
            )
            != 0
        ):
            return 1

        _step(7, "Stage local gh-pages manifests")
        latest_path, tagged_path = _stage_pages(
            work_dir,
            args.workflow_tag,
            manifest_path,
            args.simulate_pages_mismatch,
        )
        print(f"staged Pages latest: {latest_path}")
        print(f"staged Pages tagged: {tagged_path}")

        _step(8, "Smoke-test local Pages manifest with reused helper")
        if _run_pages_smoke(base_url, manifest_path, args.timeout_seconds) != 0:
            return 1

    _step(9, "Dry run complete; live workflow would clear prerelease flag now")
    print(f"dry-run outputs preserved under: {work_dir}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    """Build the command-line parser for the local dry-run harness."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--workflow-tag",
        required=True,
        help="Tag that would trigger the workflow, e.g. app-notification-v9.2.0",
    )
    parser.add_argument(
        "--source",
        type=Path,
        default=DEFAULT_SOURCE,
        help='Path to app-notification.yaml (default: "CLASSIC Data/app-notification.yaml")',
    )
    parser.add_argument(
        "--published-at",
        help=(
            "RFC 3339 timestamp to use when the source has published_at: null. "
            "Defaults to the local tag timestamp when present, otherwise current UTC."
        ),
    )
    parser.add_argument(
        "--require-existing-tag",
        action="store_true",
        help=(
            "Require the workflow tag to exist locally so timestamp resolution "
            "mirrors CI exactly."
        ),
    )
    parser.add_argument(
        "--work-dir",
        type=Path,
        help="Directory for dry-run outputs. Defaults to a preserved temp directory.",
    )
    parser.add_argument(
        "--timeout-seconds",
        type=int,
        default=5,
        help="Retry budget for the local release and Pages probes (default: 5).",
    )
    parser.add_argument(
        "--simulate-release-asset-mismatch",
        action="store_true",
        help="Stage stale release-asset bytes so the release probe fails before Pages staging.",
    )
    parser.add_argument(
        "--simulate-pages-mismatch",
        action="store_true",
        help="Stage stale Pages bytes so the Pages smoke test fails before final visibility.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Parse command-line arguments and run the dry-run workflow."""
    parser = build_parser()
    args = parser.parse_args(argv)
    return run(args)


if __name__ == "__main__":
    sys.exit(main())
