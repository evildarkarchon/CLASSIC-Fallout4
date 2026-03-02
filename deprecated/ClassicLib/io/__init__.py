"""I/O operations for files, database, and YAML.

This package consolidates all I/O operations:
- files: File I/O operations (was FileIO/)
- database: Database connection and pooling (was Database/)
- yaml: YAML settings and configuration (was YamlSettings/)
"""

from ClassicLib.io import database, files, yaml

__all__ = ["database", "files", "yaml"]
