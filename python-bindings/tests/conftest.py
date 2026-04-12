"""Shared pytest fixtures for classic_scanlog Python binding tests.

Provides an auto-use fixture that resets the FCX global state
(``GLOBAL_FCX_HANDLER``) before each test, preventing cross-test pollution
when ``FcxModeHandler`` tests run in the same session.
"""

from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def reset_fcx_global_state():
    """Reset ``GLOBAL_FCX_HANDLER`` before each test.

    The reset API is ``classic_scanlog.FcxModeHandler.reset_fcx_checks()``
    (classmethod verified from
    ``classic-scanlog-py/src/fcx_handler.rs:352``). The classmethod treats
    ``FcxResetError::Unnecessary`` as success, so calling it when there is
    no session state is a benign no-op.

    If the wheel is not yet built (fresh clone / cold CI) the import fails
    and the fixture becomes a no-op, so pytest collection still works.
    """
    try:
        import classic_scanlog  # type: ignore[import-not-found]
    except ImportError:
        yield
        return

    handler_cls = getattr(classic_scanlog, "FcxModeHandler", None)
    reset = getattr(handler_cls, "reset_fcx_checks", None) if handler_cls else None
    if callable(reset):
        try:
            reset()
        except Exception:  # noqa: BLE001 - best-effort cleanup
            # Never fail collection because of a teardown problem
            pass
    yield
