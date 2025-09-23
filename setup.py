"""Setup.py for compatibility with setuptools and uv."""


from setuptools import find_packages, setup

# Find all packages in src and root
packages = find_packages(where="src") + find_packages(where=".", include=["ClassicLib", "ClassicLib.*"])

# Define package directories
package_dir = {
    "classic": "src/classic",
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

# Entry points matching the pyproject.toml scripts
entry_points = {
    "console_scripts": [
        "classic=classic.gui:main",
        "classic-gui=classic.gui:main",
        "classic-cli=classic.cli:main",
        "classic-tui=classic.tui:main",
        "classic-scan=classic.scan:main",
    ],
}

setup(
    packages=packages,
    package_dir=package_dir,
    package_data=package_data,
    include_package_data=True,
    entry_points=entry_points,
    py_modules=["CLASSIC_Interface", "CLASSIC_TUI", "CLASSIC_ScanLogs", "CLASSIC_ScanGame"],
)
