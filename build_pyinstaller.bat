@echo off
:: =============================================================================
:: CLASSIC PyInstaller Build Script
:: =============================================================================
:: This script builds the CLASSIC executable with bundled Rust extensions.
:: It assumes the Rust extensions have already been built with build_rust_local.bat
:: =============================================================================

setlocal

set PROJECT_ROOT=%~dp0
set PROJECT_ROOT=%PROJECT_ROOT:~0,-1%
set UPX_PATH=C:\Path\to\UPX

echo ========================================
echo   CLASSIC PyInstaller Build
echo ========================================
echo.

:: Check if Rust extensions exist
if not exist "%PROJECT_ROOT%\rust_extensions\*.pyd" (
    echo WARNING: No Rust extensions found in rust_extensions\
    echo.
    echo You should run build_rust_local.bat first to build the extensions.
    echo Continuing without Rust optimizations...
    echo.
    pause
)

:: Clean previous builds
echo [1/4] Cleaning previous builds...
if exist "%PROJECT_ROOT%\build" rmdir /s /q "%PROJECT_ROOT%\build"
if exist "%PROJECT_ROOT%\dist" rmdir /s /q "%PROJECT_ROOT%\dist"

:: Check if UPX is available
echo.
echo [2/4] Checking UPX availability...
if exist "%UPX_PATH%\upx.exe" (
    echo   UPX found at: %UPX_PATH%
    set UPX_ARG=--upx-dir "%UPX_PATH%"
) else (
    echo   UPX not found. Building without compression.
    echo   To enable compression, set UPX_PATH in this script.
    set UPX_ARG=
)

:: Run PyInstaller
echo.
echo [3/4] Running PyInstaller...
echo   This may take a few minutes...
echo.

uv run pyinstaller --clean %UPX_ARG% "%PROJECT_ROOT%\CLASSIC.spec"

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ERROR: PyInstaller build failed!
    pause
    exit /b 1
)

:: Check the result
echo.
echo [4/4] Verifying build output...

if exist "%PROJECT_ROOT%\dist\CLASSIC\CLASSIC.exe" (
    echo.
    echo ========================================
    echo   BUILD SUCCESSFUL!
    echo ========================================
    echo.
    echo Executable created at:
    echo   %PROJECT_ROOT%\dist\CLASSIC\CLASSIC.exe
    echo.
    echo The dist\CLASSIC\ folder contains the complete application.
    echo You can distribute this entire folder to users.
    echo.

    :: Check if Rust extensions were bundled
    if exist "%PROJECT_ROOT%\dist\CLASSIC\_internal\rust_extensions\*.pyd" (
        echo Rust extensions successfully bundled:
        dir /b "%PROJECT_ROOT%\dist\CLASSIC\_internal\rust_extensions\*.pyd"
    ) else (
        echo Note: No Rust extensions were bundled. The app will use Python fallbacks.
    )
) else (
    echo.
    echo ERROR: Executable not found in expected location!
    echo Check the build output above for errors.
)

echo.
pause

endlocal
