"""Scanning functionality for crash logs and game integrity.

This package contains two main subpackages:
- logs: Crash log scanning and analysis
- game: Game integrity and configuration scanning
"""

from ClassicLib.scanning import game, logs

__all__ = ["logs", "game"]
