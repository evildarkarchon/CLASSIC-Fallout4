"""Pure Python implementations serving as fallbacks.

This module contains pure Python implementations that serve as fallbacks
when Rust acceleration is not available for the plugin analyzer component.
Other components now require Rust -- see factory.py.
"""

from ClassicLib.integration.python.plugin_py import PythonPluginAnalyzer

__all__ = [
    # Core classes
    "PythonPluginAnalyzer",
]
