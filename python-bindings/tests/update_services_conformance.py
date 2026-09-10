"""Observe notification transport and cache bytes through Python bindings."""

import json
import os
import re
import tempfile
from pathlib import Path
from typing import Any


def observe_update_services(fixture: dict[str, Any], scenario_id: str) -> dict[str, Any]:
    """Run repeated checks against the controlled service with one isolated cache."""
    import classic_update

    base = os.environ["CLASSIC_CONFORMANCE_SERVICE"].rstrip("/") + "/" + scenario_id
    config = json.dumps({"github_api_base_url": base + "/api", "notification_pages_url": base + "/pages", "timeout_ms": fixture["timeoutMs"]})
    with tempfile.TemporaryDirectory(prefix="classic-update-") as directory:
        cache = Path(directory) / "cache"
        cache.mkdir()
        results = []
        for _ in range(fixture["checks"]):
            try:
                status = classic_update.check_app_notification_configured("conformance", "updates", fixture["installedVersion"], config, str(cache))
                display = status.display
                results.append({"status": {
                    "classification": re.sub(r"(?<!^)(?=[A-Z])", "_", status.classification).lower(),
                    "latestVersion": status.latest_version, "publishedAt": status.published_at,
                    "minSupportedVersion": status.min_supported_version,
                    "display": None if display is None else {"title": display.title, "body": display.body, "ctaUrl": display.cta_url},
                    "parseError": status.parse_error,
                }, "error": None})
            except classic_update.ClassicNotificationError as error:
                if isinstance(error, classic_update.ClassicNotificationFetchFailed):
                    code = "fetch_failed"
                elif isinstance(error, classic_update.ClassicNotificationDecodeError):
                    code = "decode"
                elif isinstance(error, classic_update.ClassicNotificationInstalledVersionParseError):
                    code = "installed_version"
                elif str(error).startswith("manifest_version ") and " not supported " in str(error):
                    code = "unsupported_version"
                else:
                    raise
                results.append({"status": None, "error": {"code": code}})
        files = [{"path": path.relative_to(directory).as_posix(), "hex": path.read_bytes().hex()} for path in sorted(cache.rglob("*")) if path.is_file()]
        return {"results": results, "files": files}
