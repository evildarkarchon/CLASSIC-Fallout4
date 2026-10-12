"""Remaining Python helper from the retired YAML data publish tooling.

The YAML data publish (``.github/workflows/publish-yaml-data.yml``) runs
``cargo xtask yaml-data`` now. Only ``smoke_test_pages.py`` is left, because
the app-notification publish workflow and ``tools/publish_app_notification``
still call it; it goes when that tooling is ported to
``cargo xtask app-notification``.
"""
