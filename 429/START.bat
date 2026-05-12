@echo off
chcp 65001 >nul 2>&1
REM ============================================
REM  Midtrans 429 Bypass - Quick Launcher
REM  Double-click this file to start
REM ============================================

cd /d "%~dp0"

REM -- Find Python --
where python >nul 2>&1
if %errorlevel%==0 (
    set "PY=python"
    goto :found
)
where python3 >nul 2>&1
if %errorlevel%==0 (
    set "PY=python3"
    goto :found
)
where py >nul 2>&1
if %errorlevel%==0 (
    set "PY=py"
    goto :found
)

echo.
echo [ERROR] Python not found!
echo Please install Python from https://www.python.org/downloads/
echo Make sure to check "Add Python to PATH" during installation.
echo.
pause
exit /b 1

:found
echo Using: %PY%

REM -- Check dependencies --
%PY% -c "import curl_cffi, playwright" >nul 2>&1
if %errorlevel% neq 0 (
    echo.
    echo [SETUP] Installing dependencies...
    %PY% -m pip install curl_cffi playwright
    %PY% -m playwright install chromium
    echo.
)

REM -- Run --
if "%~1"=="" (
    %PY% "%~dp0bypass_429.py"
) else (
    %PY% "%~dp0bypass_429.py" "%~1"
)
pause
