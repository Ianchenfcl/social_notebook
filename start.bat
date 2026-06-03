@echo off
title Love AI Tutor - Startup
cls
echo ===================================================================
echo.
echo          Love AI Tutor Workspace Startup
echo.
echo ===================================================================
echo.

echo [*] Checking Python installation...
where python >nul 2>nul
if %errorlevel% neq 0 (
    echo [ERROR] Python was not found in your system PATH!
    echo Please install Python 3.9+ and make sure to check "Add Python to PATH".
    echo Download link: https://www.python.org/downloads/
    pause
    exit /b
)

echo [*] Checking Python virtual environment (.venv)...
if not exist .venv (
    echo [*] Creating virtual environment (.venv)...
    python -m venv .venv
    if %errorlevel% neq 0 (
        echo [WARNING] Failed to create virtual environment. Using global Python...
        set PY_EXEC=python
    ) else (
        echo [SUCCESS] Virtual environment created.
        set PY_EXEC=.venv\Scripts\python
    )
) else (
    set PY_EXEC=.venv\Scripts\python
)

echo [*] Installing requirements (this might take a few moments)...
%PY_EXEC% -m pip install -r requirements.txt --quiet
if %errorlevel% neq 0 (
    echo [WARNING] Dependency installation completed with warnings.
) else (
    echo [SUCCESS] Dependencies verified.
)

echo.
echo [TUTOR] If you have a Gemini API Key, paste it below.
echo         (Or press Enter to start in local demo/search mode)
echo.
set /p USER_KEY="GEMINI_API_KEY: "

if not "%USER_KEY%"=="" (
    set GEMINI_API_KEY=%USER_KEY%
    echo [SUCCESS] GEMINI_API_KEY loaded for this session!
) else (
    echo [INFO] Running in demo mode (Local search and notes enabled).
)

echo.
echo [*] Opening browser to http://localhost:8000...
start http://localhost:8000

echo [*] Launching FastAPI backend server...
%PY_EXEC% -m uvicorn app:app --reload --port 8000
if %errorlevel% neq 0 (
    echo [ERROR] Server exited abnormally.
)
pause
