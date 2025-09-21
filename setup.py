"""Setup.py for compatibility with pkg_resources and setuptools."""

from setuptools import setup, find_packages

setup(
    name="classic",
    packages=find_packages(where="src") + ["ClassicLib"],
    package_dir={"": "src", "ClassicLib": "ClassicLib"},
    package_data={
        "classic": [
            "../CLASSIC Data/**/*.yaml",
            "../CLASSIC Data/**/*.yml",
            "../CLASSIC Data/**/*.db",
            "../CLASSIC Data/**/*.txt",
        ],
    },
    include_package_data=True,
)
