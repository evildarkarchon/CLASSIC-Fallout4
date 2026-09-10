"""The local service executes authored responses without forwarding requests."""

import urllib.error
import urllib.request

import pytest
from controlled_update_service import ControlledUpdateService


def test_service_serves_sequences_and_rejects_unplanned_requests():
    """A cache revalidation gets its own response; extra requests fail closed."""
    service = {
        "case": {
            "pages": [
                {"status": 200, "body": "fixture", "headers": {"ETag": '"fixture"'}},
                {"status": 304, "body": "", "headers": {}, "ifNoneMatch": '"fixture"'},
            ],
            "api": [],
        }
    }
    with ControlledUpdateService(service) as local:
        assert urllib.request.urlopen(local.url + "/case/pages").read() == b"fixture"
        request = urllib.request.Request(
            local.url + "/case/pages", headers={"If-None-Match": '"fixture"'}
        )
        with pytest.raises(urllib.error.HTTPError) as response:
            urllib.request.urlopen(request)
        assert response.value.code == 304
        local.assert_complete()
        with pytest.raises(urllib.error.HTTPError):
            urllib.request.urlopen(local.url + "/unplanned/pages")
        with pytest.raises(ValueError, match="unplanned"):
            local.assert_complete()


def test_service_stalls_until_client_timeout_and_releases_on_shutdown():
    """Timeouts use an unanswered request, independent of scheduling sleeps."""
    with ControlledUpdateService(
        {"case": {"pages": [{"stall": True}], "api": []}}
    ) as local:
        with pytest.raises(TimeoutError):
            urllib.request.urlopen(local.url + "/case/pages", timeout=0.05)
        local.assert_complete()


def test_service_rejects_unplanned_http_methods():
    """An unsupported method cannot disappear behind the HTTP server's 501."""
    with ControlledUpdateService({}) as local:
        request = urllib.request.Request(local.url + "/unplanned", method="POST")
        with pytest.raises(urllib.error.HTTPError):
            urllib.request.urlopen(request)
        with pytest.raises(ValueError, match="unplanned HTTP error"):
            local.assert_complete()
