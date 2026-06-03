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
if errorlevel 1 goto nopython

echo [*] Checking Python virtual environment (.venv)...
if exist .venv\Scripts\python.exe goto use_venv

echo [*] Creating virtual environment (.venv)...
python -m venv .venv
if errorlevel 1 goto venv_failed

:use_venv
set PY_EXEC=.venv\Scripts\python.exe
echo [SUCCESS] Virtual environment ready.
goto install_req

:venv_failed
echo [WARNING] Failed to create virtual environment. Using global Python...
set PY_EXEC=python
goto install_req

:install_req
echo [*] Installing requirements (this might take a few moments)...
%PY_EXEC% -m pip install -r requirements.txt --quiet
if errorlevel 1 echo [WARNING] Dependency installation completed with warnings.
if not errorlevel 1 echo [SUCCESS] Dependencies verified.

echo.
echo [TUTOR] If you have a Gemini API Key, paste it below.
echo         (Or press Enter to start in local demo/search mode)
echo.
set /p USER_KEY="GEMINI_API_KEY: "

if "%USER_KEY%"=="" goto running_demo
set GEMINI_API_KEY=%USER_KEY%
echo [SUCCESS] GEMINI_API_KEY loaded for this session!
goto launch_server

:running_demo
echo [INFO] Running in demo mode (Local search and notes enabled).

:launch_server
echo.
echo [*] Opening browser to http://localhost:8000...
start http://localhost:8000

echo [*] Launching FastAPI backend server...
%PY_EXEC% -m uvicorn app:app --reload --port 8000
if errorlevel 1 echo [ERROR] Server exited abnormally.
goto end

:nopython
echo [ERROR] Python was not found in your system PATH!
echo Please install Python 3.9+ and make sure to check "Add Python to PATH".
echo Download link: https://www.python.org/downloads/
pause
exit /b

:end
pause
