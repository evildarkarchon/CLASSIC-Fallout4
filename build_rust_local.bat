@echo off
:: =============================================================================
:: CLASSIC Rust Extension Local Build Script
:: =============================================================================
:: This script builds the Rust extensions locally and places them in the correct
:: locations for both development (uvx) and production (PyInstaller) use.
::
:: NO pip installation, NO GitHub Actions, NO CI/CD required!
:: Everything is built and bundled locally on the developer's machine.
:: =============================================================================

setlocal enabledelayedexpansion

:: Check for required tools
echo [1/8] Checking prerequisites...
where maturin >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: maturin not found. Please install it first:
    echo   uv tool install maturin
    exit /b 1
)

where cargo >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Rust/Cargo not found. Please install Rust from https://rustup.rs/
    exit /b 1
)

:: Set up directories
set PROJECT_ROOT=%~dp0
set PROJECT_ROOT=%PROJECT_ROOT:~0,-1%
set RUST_EXTENSIONS_DIR=%PROJECT_ROOT%\classic_core
set TEMP_BUILD_DIR=%PROJECT_ROOT%\temp_rust_build

echo.
echo [2/8] Setting up directories...
echo   Project Root: %PROJECT_ROOT%
echo   Extensions Dir: %RUST_EXTENSIONS_DIR%
echo   Temp Build: %TEMP_BUILD_DIR%

:: Create directories
if not exist "%RUST_EXTENSIONS_DIR%" mkdir "%RUST_EXTENSIONS_DIR%"
if not exist "%TEMP_BUILD_DIR%" mkdir "%TEMP_BUILD_DIR%"

:: Clean previous builds
echo.
echo [3/8] Cleaning previous builds...
if exist "%RUST_EXTENSIONS_DIR%\*.pyd" del /q "%RUST_EXTENSIONS_DIR%\*.pyd"
if exist "%RUST_EXTENSIONS_DIR%\*.so" del /q "%RUST_EXTENSIONS_DIR%\*.so"
if exist "%RUST_EXTENSIONS_DIR%\*.dll" del /q "%RUST_EXTENSIONS_DIR%\*.dll"
if exist "%TEMP_BUILD_DIR%\*" del /q "%TEMP_BUILD_DIR%\*"

:: Build the Rust extension with maturin
echo.
echo [4/8] Building Rust extension with maturin...
cd "%PROJECT_ROOT%"

:: Build for the current Python version in release mode
:: Using --out to specify where to place the wheel
maturin build --release --out "%TEMP_BUILD_DIR%" --compatibility manylinux2014

if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Maturin build failed!
    exit /b 1
)

:: Extract the wheel to get the .pyd file
echo.
echo [5/8] Extracting compiled extension from wheel...

:: Find the wheel file
for %%f in ("%TEMP_BUILD_DIR%\*.whl") do (
    set WHEEL_FILE=%%f
)

if not defined WHEEL_FILE (
    echo ERROR: No wheel file found in %TEMP_BUILD_DIR%
    exit /b 1
)

echo   Found wheel: %WHEEL_FILE%

:: Create a temporary extraction directory
set EXTRACT_DIR=%TEMP_BUILD_DIR%\extracted
if exist "%EXTRACT_DIR%" rmdir /s /q "%EXTRACT_DIR%"
mkdir "%EXTRACT_DIR%"

:: Extract the wheel (it's just a ZIP file)
powershell -NoProfile -Command "Expand-Archive -Path '%WHEEL_FILE%' -DestinationPath '%EXTRACT_DIR%' -Force"

:: Find and copy the .pyd files (Windows) or .so files (Linux)
echo.
echo [6/8] Copying compiled extensions...

:: Look for .pyd files (Windows Python extensions)
for /r "%EXTRACT_DIR%" %%f in (*.pyd) do (
    echo   Found extension: %%~nxf
    copy "%%f" "%RUST_EXTENSIONS_DIR%\" >nul

    :: Also copy to the Python package location for direct import
    set TARGET_DIR=%PROJECT_ROOT%\classic-rust\python\classic_core
    if not exist "!TARGET_DIR!" mkdir "!TARGET_DIR!"
    copy "%%f" "!TARGET_DIR!\" >nul

    :: Copy to ClassicLib for backward compatibility
    set CLASSICLIB_DIR=%PROJECT_ROOT%\ClassicLib\rust_ext
    if not exist "!CLASSICLIB_DIR!" mkdir "!CLASSICLIB_DIR!"
    copy "%%f" "!CLASSICLIB_DIR!\" >nul
)

:: Also look for any required DLL dependencies
for /r "%EXTRACT_DIR%" %%f in (*.dll) do (
    :: Skip Python DLLs (they're provided by Python itself)
    echo %%~nxf | findstr /i "python" >nul
    if !ERRORLEVEL! NEQ 0 (
        echo   Found dependency: %%~nxf
        copy "%%f" "%RUST_EXTENSIONS_DIR%\" >nul
    )
)

:: Create a manifest file for tracking
echo.
echo [7/8] Creating manifest file...
set MANIFEST_FILE=%RUST_EXTENSIONS_DIR%\MANIFEST.txt
echo Rust Extensions Build Manifest > "%MANIFEST_FILE%"
echo ============================== >> "%MANIFEST_FILE%"
echo Build Date: %DATE% %TIME% >> "%MANIFEST_FILE%"
echo. >> "%MANIFEST_FILE%"
echo Files: >> "%MANIFEST_FILE%"
dir /b "%RUST_EXTENSIONS_DIR%\*.pyd" >> "%MANIFEST_FILE%" 2>nul
dir /b "%RUST_EXTENSIONS_DIR%\*.dll" >> "%MANIFEST_FILE%" 2>nul
echo. >> "%MANIFEST_FILE%"
echo Locations: >> "%MANIFEST_FILE%"
echo - classic_core\  (for PyInstaller bundling) >> "%MANIFEST_FILE%"
echo - classic-rust\python\classic_core\  (for development) >> "%MANIFEST_FILE%"
echo - ClassicLib\rust_ext\  (for backward compatibility) >> "%MANIFEST_FILE%"

:: Clean up temporary files
echo.
echo [8/8] Cleaning up temporary files...
rmdir /s /q "%TEMP_BUILD_DIR%"

:: Summary
echo.
echo ========================================
echo    BUILD COMPLETED SUCCESSFULLY!
echo ========================================
echo.
echo Rust extensions have been built and placed in:
echo   1. %RUST_EXTENSIONS_DIR%
echo   2. %PROJECT_ROOT%\classic-rust\python\classic_core
echo   3. %PROJECT_ROOT%\ClassicLib\rust_ext
echo.
echo These locations ensure the extensions work with:
echo   - PyInstaller (bundled in _internal)
echo   - uvx (from GitHub repo)
echo   - Local development (direct import)
echo.
echo Next steps:
echo   1. Commit the classic_core directory to git
echo   2. Run build_pyinstaller.bat to create the executable
echo   3. Test with test_rust_loading.py
echo.

endlocal
