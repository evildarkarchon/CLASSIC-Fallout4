"""Support utilities and helper modules.

This package consolidates various support modules:
- backup: Backup management
- documents: Documents path detection and checking
- docs_path: Documents path utilities
- game_path: Game path detection and validation
- integrity: Game integrity verification
- update: Application update functionality
- xse: Script extender checking
- papyrus: Papyrus log analysis
- resources: Resource loading utilities
- setup: Setup coordination
- file_gen: File generation utilities
- gui_components: GUI component utilities
- path_validator: Path validation utilities
- versions: Version registry and management
"""

from ClassicLib.support import (
    backup,
    docs_path,
    documents,
    file_gen,
    game_path,
    gui_components,
    integrity,
    papyrus,
    path_validator,
    resources,
    setup,
    update,
    versions,
    xse,
)

__all__ = [
    "backup",
    "docs_path",
    "documents",
    "file_gen",
    "game_path",
    "gui_components",
    "integrity",
    "papyrus",
    "path_validator",
    "resources",
    "setup",
    "update",
    "versions",
    "xse",
]
