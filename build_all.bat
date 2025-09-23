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

    REM Build the Rust extension
    echo Building release build with maturin...
    %MATURIN_CMD% build --release --out dist-rust
    if %errorlevel% neq 0 (
        echo WARNING: Rust extension build failed!
        echo Continuing without Rust optimizations...
    ) else (
        REM Extract the built extension from wheel
        echo Extracting Rust extension from wheel...
        if not exist rust_extensions mkdir rust_extensions

        REM Use Python to extract the .pyd file from the wheel
        %PYTHON_CMD% -c "import zipfile, glob, shutil; wheel = glob.glob('dist-rust/*.whl')[0]; z = zipfile.ZipFile(wheel); [z.extract(f, 'temp_extract') for f in z.namelist() if f.endswith('.pyd')]; [shutil.copy2(f'temp_extract/{f}', 'rust_extensions/') for f in z.namelist() if f.endswith('.pyd')]"

        REM Clean up
        if exist temp_extract rmdir /s /q temp_extract

        REM Create manifest file
        echo Rust extensions built on %date% %time% > rust_extensions\MANIFEST.txt
        echo. >> rust_extensions\MANIFEST.txt
        dir /b rust_extensions\*.pyd >> rust_extensions\MANIFEST.txt

        echo Rust extensions ready in rust_extensions/
    )
    echo.
) else (
    echo ============================================================
    echo Rust source not found - checking for pre-built extensions...
    echo ============================================================
    if exist rust_extensions (
        echo Found pre-built Rust extensions in rust_extensions/
        dir /b rust_extensions\*.pyd 2>nul
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
