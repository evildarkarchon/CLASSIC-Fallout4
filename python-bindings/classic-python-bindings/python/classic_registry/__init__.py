"""Python module for registry access.

This module provides a thread-safe, process-wide registry (owned by this
facade) for storing and retrieving singleton instances and configuration
values.

# Examples

```python
from classic_core import registry

# Register values
registry.register(registry.Keys.GAME, "Fallout4")
registry.register(registry.Keys.IS_GUI_MODE, True)

# Retrieve values
game = registry.get(registry.Keys.GAME)
is_gui = registry.is_gui_mode()

# Check registration
if registry.is_registered(registry.Keys.GAME):
    print("Game is configured")
```
"""

# Direct-import facade over the one CLASSIC native extension. Every name is
# the canonical native object, so values and exceptions created through any
# facade are the same Python types everywhere. Keep the import list and the
# literal ``__all__`` in step with ``__init__.pyi``: validate_stubs.py and the
# Python parity resolver read both.

from _classic_native._native.classic_registry import (
    Keys,
    __version__,
    clear_all,
    get,
    get_application_dir,
    get_game,
    get_game_path_gui,
    get_game_version_string,
    get_local_dir,
    get_manual_docs_gui,
    get_yaml_cache,
    is_enb_present,
    is_gui_mode,
    is_registered,
    is_version_auto_detected,
    is_xse_valid,
    register,
    set_application_dir,
    set_game,
    unregister,
)

__all__ = [
    "Keys",
    "__version__",
    "clear_all",
    "get",
    "get_application_dir",
    "get_game",
    "get_game_path_gui",
    "get_game_version_string",
    "get_local_dir",
    "get_manual_docs_gui",
    "get_yaml_cache",
    "is_enb_present",
    "is_gui_mode",
    "is_registered",
    "is_version_auto_detected",
    "is_xse_valid",
    "register",
    "set_application_dir",
    "set_game",
    "unregister",
]
