# CLASSIC - Crash Log Auto Scanner & Setup Integrity Checker

## Project Overview

CLASSIC is a Python-based desktop application with a graphical user interface (GUI) built using PySide6. Its primary purpose is to scan and analyze crash logs for the games Fallout 4 and Skyrim. The application helps users identify the cause of game crashes by providing detailed information about errors, settings, and mods. It also includes features for managing game files, such as backing up and restoring mod files, checking for script extender updates, and monitoring Papyrus logs.

The project is managed using Poetry for dependency management and can be built into a standalone executable using PyInstaller. The codebase follows a modular architecture with specialized components in the `ClassicLib/` directory handling different aspects of functionality (setup coordination, file generation, integrity checking, backups, etc.), while `CLASSIC_Interface.py` provides the GUI. It also includes a comprehensive suite of tests and uses tools like `ruff`, `mypy`, and `pyright` to ensure code quality.

## Building and Running

### Prerequisites

*   Python 3.12
*   Poetry

### Installation

1.  **Install Poetry:**
    ```powershell
    (Invoke-WebRequest -Uri https://install.python-poetry.org -UseBasicParsing).Content | py -
    ```
2.  **Configure Poetry to create a virtual environment in the project folder:**
    Create a `poetry.toml` file in the project root with the following content:
    ```toml
    [virtualenvs]
    create = true
    in-project = true
    ```
3.  **Install dependencies:**
    ```powershell
    poetry install
    ```

### Running the Application

You can run the application from the command line or through an IDE like Visual Studio Code.

*   **From the command line:**
    ```powershell
    poetry run python CLASSIC_Interface.py
    ```
*   **Using Visual Studio Code:**
    The repository includes a `.vscode/launch.json` file that allows you to run and debug the application directly from the IDE.

### Building the Executable

The project uses PyInstaller to build a standalone executable.

*   **From the command line:**
    ```powershell
    pyinstaller --clean .\CLASSIC.spec
    ```
*   **With UPX compression:**
    To reduce the size of the executable, you can use UPX.
    ```powershell
    pyinstaller --clean --upx-dir 'E:\Tools' .\CLASSIC.spec
    ```

## Development Conventions

*   **Code Style:** The project uses `ruff` for linting and formatting. The configuration can be found in the `pyproject.toml` file.
*   **Type Checking:** The project uses `mypy `pyright` for static type checking.
*   **Testing:** The project uses `pytest` for testing. The test files are located in the `tests/` directory.
*   **Dependency Management:** Dependencies are managed with Poetry and are listed in the `pyproject.toml` file.
*   **Commits:** The project does not have a formal commit message convention, but the commit history shows a preference for descriptive and concise messages.
