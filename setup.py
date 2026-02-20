"""Setup.py for compatibility with setuptools and uv."""

from setuptools import find_packages, setup

# Find all packages in root (no src directory)
packages = find_packages(where=".", include=["ClassicLib", "ClassicLib.*"])

# Define package directories (no src/classic)
package_dir = {
    "ClassicLib": "ClassicLib",
}

# Collect all CLASSIC Data files
package_data = {
    "": [
        "CLASSIC Data/**/*.yaml",
        "CLASSIC Data/**/*.yml",
        "CLASSIC Data/**/*.db",
        "CLASSIC Data/**/*.txt",
        "CLASSIC Data/**/*.md",
    ],
}

# Entry points matching the pyproject.toml scripts (using root modules)
entry_points = {
    "console_scripts": [
        "classic=classic_interface:main",
        "classic-gui=classic_interface:main",
        "classic-qml=classic_interface_qml:main",
        "classic-cli=classic_scanlogs:main",
        "classic-scan=classic_scangame:main",
    ],
}

setup(
    packages=packages,
    package_dir=package_dir,
    package_data=package_data,
    include_package_data=True,
    entry_points=entry_points,
    py_modules=["classic_interface", "classic_interface_qml", "classic_scanlogs", "classic_scangame"],
)
