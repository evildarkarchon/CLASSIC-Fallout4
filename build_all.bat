@echo off
REM Build script for all CLASSIC-Fallout4 PyInstaller executables
REM This script builds all versions of the application with proper data bundling

echo ============================================================
echo CLASSIC-Fallout4 Build Script
echo ============================================================
echo.

REM Check if uv is available
where uv >nul 2>1
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

REM Build Rust extensions first (if source available)
if exist classic-rust (
    echo ============================================================
    echo Building Rust extensions...
    echo ============================================================

    REM Build the Rust extension from classic-rust directory
    echo Building release build with maturin...
    cd classic-rust
    %MATURIN_CMD% build --release --out ..\dist-rust
    cd ..
    if %errorlevel% neq 0 (
        echo WARNING: Rust extension build failed!
        echo Continuing without Rust optimizations...
    ) else (
        REM Extract the entire classic_core package from wheel
        echo Extracting Rust extension from wheel...

        REM Remove old classic_core if it exists
        if exist classic_core rmdir /s /q classic_core

        REM Use Python to extract the entire classic_core directory from the wheel
        %PYTHON_CMD% -c "import zipfile, glob, shutil, os; wheel = glob.glob('dist-rust/*.whl')[0]; z = zipfile.ZipFile(wheel); members = [f for f in z.namelist() if f.startswith('classic_core/')]; z.extractall('temp_extract', members); shutil.copytree('temp_extract/classic_core', 'classic_core', dirs_exist_ok=True)"

        REM Clean up
        if exist temp_extract rmdir /s /q temp_extract

        REM Show what was extracted
        echo Extracted classic_core package with:
        dir /b classic_core\*.*

        REM Create manifest file
        echo Rust extensions built on %date% %time% > classic_core\MANIFEST.txt
        echo. >> classic_core\MANIFEST.txt
        dir /b classic_core\*.pyd >> classic_core\MANIFEST.txt

        echo Rust extensions ready in classic_core/
    )
    echo.
) else (
    echo ============================================================
    echo Rust source not found - checking for pre-built extensions...
    echo ============================================================
    if exist classic_core (
        echo Found pre-built Rust extensions in classic_core/
        dir /b classic_core\*.pyd 2>nul
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

REM Test resource loading in development mode
echo Testing resource loading...
%PYTHON_CMD% test_resource_loading.py
if %errorlevel% neq 0 (
    echo ERROR: Resource loading test failed!
    echo Please fix the issues before building.
    pause
    exit /b 1
)
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

REM Build TUI version
echo ============================================================
echo Building TUI version (CLASSIC-TUI.exe)...
echo ============================================================
%PYINSTALLER_CMD% --clean CLASSIC-TUI.spec
if %errorlevel% neq 0 (
    echo ERROR: TUI build failed!
    pause
    exit /b 1
)
echo TUI build complete: dist\CLASSIC-TUI.exe
echo.

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
)

REM Test the built executable
echo ============================================================
echo Testing frozen executable...
echo ============================================================
if exist "dist\CLASSIC-Test.exe" (
    dist\CLASSIC-Test.exe
) else (
    echo Creating temporary test of GUI executable...
    echo import sys > test_frozen.py
    echo sys.path.insert(0, 'dist/CLASSIC') >> test_frozen.py
    echo exec(open('test_resource_loading.py').read()) >> test_frozen.py
    cd dist\CLASSIC
    CLASSIC.exe /c "python ..\..\test_frozen.py"
    cd ..\..
    del test_frozen.py
)

echo.
echo ============================================================
echo Build Summary
echo ============================================================
echo.
dir dist\*.exe dist\CLASSIC\*.exe 2>nul | findstr "exe$"
echo.
echo All builds completed successfully!
echo.
echo Executables are located in the 'dist' directory:
echo - GUI Folder: dist\CLASSIC\CLASSIC.exe (folder distribution - smaller)
echo - GUI Single: dist\CLASSIC-GUI-OneFile.exe (single file - portable)
echo - CLI: dist\CLASSIC-CLI.exe (single file)
echo - TUI: dist\CLASSIC-TUI.exe (single file)
if exist "dist\CLASSIC-Test.exe" (
    echo - Test: dist\CLASSIC-Test.exe (debug build)
)
echo.
pause
