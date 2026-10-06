"""Web utilities for CLASSIC
"""

# Direct-import facade over the one CLASSIC native extension. Every name is
# the canonical native object, so values and exceptions created through any
# facade are the same Python types everywhere. Keep the import list and the
# literal ``__all__`` in step with ``__init__.pyi``: validate_stubs.py and the
# Python parity resolver read both.

from _classic_native._native.classic_web import (
    CLASSIC_VERSION,
    ModSite,
    USER_AGENT_PREFIX,
    __version__,
    build_url_with_query,
    extract_domain,
    get_user_agent,
    get_user_agent_with_suffix,
    is_valid_url,
    join_url,
    validate_url,
)

__all__ = [
    "CLASSIC_VERSION",
    "ModSite",
    "USER_AGENT_PREFIX",
    "__version__",
    "build_url_with_query",
    "extract_domain",
    "get_user_agent",
    "get_user_agent_with_suffix",
    "is_valid_url",
    "join_url",
    "validate_url",
]
