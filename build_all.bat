@echo off
REM Build script for all CLASSIC-Fallout4 PyInstaller executables
REM This script builds all versions of the application with proper data bundling

echo ============================================================
echo CLASSIC-Fallout4 Build Script
echo ============================================================
echo.

REM Clean up shadowing directories that could interfere with imports
REM These can be created by accidental wheel extractions or build artifacts
set FOUND_SHADOWING=0
for %%D in (classic_shared classic_config classic_database classic_file_io classic_message classic_path classic_perf classic_pybridge classic_registry classic_scangame classic_scanlog classic_settings classic_yaml classic_constants classic_version classic_resource classic_xse classic_web classic_update) do (
    if exist "%%D" (
        set FOUND_SHADOWING=1
    )
)

if %FOUND_SHADOWING%==1 (
    echo ============================================================
    echo WARNING: Found directories that could shadow Rust modules!
    echo ============================================================
    for %%D in (classic_shared classic_config classic_database classic_file_io classic_message classic_path classic_perf classic_pybridge classic_registry classic_scangame classic_scanlog classic_settings classic_yaml classic_constants classic_version classic_resource classic_xse classic_web classic_update) do (
        if exist "%%D" (
            echo   - %%D
        )
    )
    echo.
    echo These directories can prevent Python from finding the installed Rust modules.
    echo They are likely build artifacts or accidental wheel extractions.
    echo.

    set /p CLEANUP_CHOICE="Delete these directories? [Y/N] (default: Y): "
    if "%CLEANUP_CHOICE%"=="" set CLEANUP_CHOICE=Y

    if /i "%CLEANUP_CHOICE%"=="Y" (
        echo Cleaning up shadowing directories...
        for %%D in (classic_shared classic_config classic_database classic_file_io classic_message classic_path classic_perf classic_pybridge classic_registry classic_scangame classic_scanlog classic_settings classic_yaml classic_constants classic_version classic_resource classic_xse classic_web classic_update) do (
            if exist "%%D" (
                echo   Deleting %%D...
                rmdir /s /q "%%D"
            )
        )
        echo Cleanup complete!
    ) else (
        echo Skipping cleanup - WARNING: These directories may cause import issues!
    )
    echo.
)

REM Check if uv is available
where uv >nul 2>nul
if %errorlevel% equ 0 (
    set PYTHON_CMD=uv run python
    set PYINSTALLER_CMD=uv run pyinstaller
    set MATURIN_CMD=uv run maturin
    echo Using uv environment
) else (
    REM Fallback to system Python if uv not found
    set PYTHON_CMD=python
    set PYINSTALLER_CMD=pyinstaller
    set MATURIN_CMD=maturin
    echo Using system Python - Note: uv is recommended for this project
    echo Install uv from: https://github.com/astral-sh/uv
)

REM Build Rust workspace (if source available)
REM
REM Architecture Overview (as of 2025-11-01):
REM -----------------------------------------
REM The Rust workspace uses separated architecture:
REM   - *-core crates: Pure Rust business logic (rlib only, NO PyO3)
REM   - *-py crates: Thin PyO3 bindings (cdylib, produces .pyd files)
REM
REM This separation enables:
REM   1. CLI/TUI applications to use pure Rust business logic directly
REM   2. Python applications to use the same logic via PyO3 bindings
REM   3. 10-150x performance improvements for all operations
REM Python imports individual modules directly (e.g., import classic_yaml)
REM
if exist "rust\python-bindings\classic-yaml-py" (
    echo ============================================================
    echo Building Rust workspace (separated architecture)...
    echo ============================================================
    echo Building: *-core crates (business logic) + *-py crates (bindings)

    REM Create dist-rust directory in project root if it doesn't exist
    if not exist "dist-rust" mkdir "dist-rust"

    REM Build all Rust modules to a single dist-rust directory
    echo Building Rust modules with maturin...
    set BUILD_SUCCESS=1

    REM Foundation Layer
    echo   Building classic_shared...
    cd "rust\foundation\classic-shared-py"
    %MATURIN_CMD% build --release --out "%~dp0dist-rust" >nul 2>&1
    if %errorlevel% neq 0 (
        echo   WARNING: classic_shared build failed!
        set BUILD_SUCCESS=0
    )
    cd "%~dp0"

    REM Python Bindings Layer
    for %%M in (classic-config-py classic-database-py classic-file-io-py classic-message-py classic-path-py classic-perf-py classic-pybridge-py classic-registry-py classic-scangame-py classic-scanlog-py classic-settings-py classic-yaml-py classic-constants-py classic-version-py classic-resource-py classic-xse-py classic-web-py classic-update-py) do (
        echo   Building %%M...
        cd "rust\python-bindings\%%M"
        %MATURIN_CMD% build --release --out "%~dp0dist-rust" >nul 2>&1
        if %errorlevel% neq 0 (
            echo   WARNING: %%M build failed!
            set BUILD_SUCCESS=0
        )
        cd "%~dp0"
    )

    if %BUILD_SUCCESS%==1 (
        REM Extract all built extensions from wheels
        echo Extracting Rust extensions from wheels...

        REM Remove old rust_extensions directory
        if exist "rust_extensions" rmdir /s /q "rust_extensions"
        mkdir "rust_extensions"

        REM Extract each module's .pyd from its wheel (flattened structure)
        for %%W in (dist-rust\*.whl) do (
            echo   Extracting %%~nxW...
            REM Use Python to extract .pyd files directly to rust_extensions/
            %PYTHON_CMD% -c "import zipfile, sys; z = zipfile.ZipFile('%%W'); [z.extract(f, 'temp_extract') for f in z.namelist() if f.endswith('.pyd') or f.endswith('__init__.py') or f.endswith('.pyi')]" >nul 2>&1
        )

        REM Move extracted files to rust_extensions (flattened)
        if exist "temp_extract" (
            for /r "temp_extract" %%F in (*.pyd) do (
                copy "%%F" "rust_extensions\" >nul
                echo   - %%~nxF
            )
            for /r "temp_extract" %%F in (__init__.py) do (
                REM Rename __init__.py to module_name__init__.py to avoid conflicts
                for %%D in ("%%~dpF.") do (
                    copy "%%F" "rust_extensions\%%~nxD__init__.py" >nul
                )
            )
            for /r "temp_extract" %%F in (*.pyi) do (
                copy "%%F" "rust_extensions\" >nul
            )
            rmdir /s /q "temp_extract"
        )

        REM Create manifest file
        echo Rust extensions built on %date% %time% > "rust_extensions\MANIFEST.txt"
        echo. >> "rust_extensions\MANIFEST.txt"
        echo Architecture: Separated *-core (business logic) + *-py (PyO3 bindings) >> "rust_extensions\MANIFEST.txt"
        echo Structure: Flattened (no subdirectories to avoid module shadowing) >> "rust_extensions\MANIFEST.txt"
        echo. >> "rust_extensions\MANIFEST.txt"
        echo Modules: >> "rust_extensions\MANIFEST.txt"
        dir /b "rust_extensions\*.pyd" >> "rust_extensions\MANIFEST.txt"

        echo.
        echo Rust extensions ready in rust_extensions/ (flattened structure)
    ) else (
        echo WARNING: Some Rust modules failed to build!
        echo Continuing without full Rust optimizations...
    )
    echo.
) else (
    echo ============================================================
    echo Rust source not found - checking for pre-built extensions...
    echo ============================================================
    if exist "rust_extensions" (
        echo Found pre-built Rust extensions in rust_extensions/ (flattened)
        dir /b "rust_extensions\*.pyd"
    ) else (
        echo No Rust extensions available - using pure Python
    )
    echo.
)

REM Clean previous builds
echo Cleaning previous builds...
if exist dist rmdir /s /q dist
if exist build rmdir /s /q build
echo.

REM Build GUI version (folder distribution)
echo ============================================================
echo Building GUI version - Folder Distribution (CLASSIC.exe)...
echo ============================================================
%PYINSTALLER_CMD% --clean CLASSIC.spec
if %errorlevel% neq 0 (
    echo ERROR: GUI build failed!
    pause
    exit /b 1
)
echo GUI build complete: dist\CLASSIC\
echo.

REM Build GUI single-file version
echo ============================================================
echo Building GUI version - Single File (CLASSIC-GUI-OneFile.exe)...
echo ============================================================
%PYINSTALLER_CMD% --clean CLASSIC-GUI-OneFile.spec
if %errorlevel% neq 0 (
    echo ERROR: GUI single-file build failed!
    pause
    exit /b 1
)
echo GUI single-file build complete: dist\CLASSIC-GUI-OneFile.exe
echo.

REM Build CLI version
echo ============================================================
echo Building CLI version (CLASSIC-CLI.exe)...
echo ============================================================
%PYINSTALLER_CMD% --clean CLASSIC-CLI.spec
if %errorlevel% neq 0 (
    echo ERROR: CLI build failed!
    pause
    exit /b 1
)
echo CLI build complete: dist\CLASSIC-CLI.exe
echo.

REM Note: TUI is now a pure Rust application, built separately
REM Build with: cd rust\ui-applications\classic-tui && cargo build --release

REM Optional: Build test version
set /p BUILD_TEST="Build test/debug version? (y/n): "
if /i "%BUILD_TEST%"=="y" (
    echo ============================================================
    echo Building Test version (CLASSIC-Test.exe)...
    echo ============================================================
    %PYINSTALLER_CMD% --clean CLASSIC-Test.spec
    if %errorlevel% neq 0 (
        echo ERROR: Test build failed!
        pause
        exit /b 1
    )
    echo Test build complete: dist\CLASSIC-Test.exe
    echo.

    REM Test the built executable
    echo ============================================================
    echo Testing frozen executable...
    echo ============================================================
    dist\CLASSIC-Test.exe
    echo.
)

echo ============================================================
echo Build Summary
echo ============================================================
echo.
dir dist\*.exe dist\CLASSIC\*.exe 2>nul | findstr /i "exe$"
echo.
echo All builds completed successfully!
echo.
echo Executables are located in the 'dist' directory:
echo - GUI Folder: dist\CLASSIC\CLASSIC.exe (folder distribution - smaller)
echo - GUI Single: dist\CLASSIC-GUI-OneFile.exe (single file - portable)
echo - CLI: dist\CLASSIC-CLI.exe (single file)
if exist "dist\CLASSIC-Test.exe" (
    echo - Test: dist\CLASSIC-Test.exe (debug build)
)
echo.
echo Note: TUI is now a pure Rust application. Build separately with:
echo   cd rust\ui-applications\classic-tui ^&^& cargo build --release
echo.
echo Build script completed!
pause
