# ⚠️ DO NOT INSTALL FILES HERE ⚠️

This `src/` directory is reserved ONLY for entry-point scripts if needed in the future.

## Important Notes:
- **No packages should be installed here**
- **No Python modules should be created here**
- **Maturin should NOT use this directory** (configured to use project root instead)
- All Python code should be in `ClassicLib/` at the project root
- Entry points are defined in the root directory (CLASSIC_*.py files)

## Current Configuration:
- `pyproject.toml`: maturin.python-source = "." (project root, not src/)
- `setup.py`: No references to src/classic
- Entry points: Defined as root-level modules (CLASSIC_Interface, etc.)

If you see any files being created here by build tools, please check the configuration immediately.