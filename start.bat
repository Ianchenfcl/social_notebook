@echo off
chcp 65001 > nul
title 戀愛AI - 一鍵啟動大師
cls
echo ===================================================================
echo.
echo          ██████╗ █████╗ ████████╗ ██████╗██╗  ██╗██╗     ███╗   ███╗
echo         ██╔════╝██╔══██╗╚══██╔══╝██╔════╝██║  ██║██║     ████╗ ████║
echo         ██║     ███████║   ██║   ██║     ███████║██║     ██╔████╔██║
echo         ██║     ██╔══██║   ██║   ██║     ██╔══██║██║     ██║╚██╔╝██║
echo         ╚██████╗██║  ██║   ██║   ╚██████╗██║  ██║███████╗██║ ╚═╝ ██║
echo          ╚═════╝╚═╝  ╚═╝   ╚═╝    ╚═════╝╚═╝  ╚═╝╚══════╝╚═╝     ╚═╝
echo.
echo                       PTT Catch 智慧情感知識庫
echo ===================================================================
echo.
echo [*] 歡迎使用 戀愛AI 智慧工作區！
echo [*] 本腳本將協助您一鍵啟動後端 API 服務與網頁介面。
echo.
echo [*] 正在確認 Python 環境...
where python >nul 2>nul
if %errorlevel% neq 0 (
    echo [!] 錯誤：找不到 Python！
    echo ─────────────────────────────────────────────────────────────
    echo 請前往 Python 官方網站下載安裝 Python 3.9 或以上版本：
    echo 👉 https://www.python.org/downloads/
    echo.
    echo 💡 重要提示：安裝時請務必勾選「Add Python to PATH」選項！
    echo ─────────────────────────────────────────────────────────────
    pause
    exit /b
)

echo [*] 正在檢查虛擬環境 (.venv)...
if not exist .venv (
    echo [*] 正在建立 Python 虛擬環境 (.venv)...
    python -m venv .venv
    if %errorlevel% neq 0 (
        echo [!] 建立虛擬環境失敗，將嘗試使用系統預設的 Python 環境...
        set PY_EXEC=python
    ) else (
        echo [✔] 虛擬環境建立成功！
        set PY_EXEC=.venv\Scripts\python
    )
) else (
    set PY_EXEC=.venv\Scripts\python
)

echo [*] 正在確認環境所需的 Python 套件已安裝 (若已安裝將極速跳過)...
%PY_EXEC% -m pip install -r requirements.txt --quiet
if %errorlevel% neq 0 (
    echo [!] 自動安裝套件時遇到一些狀況，將嘗試直接載入服務...
) else (
    echo [✔] 虛擬環境套件確認完畢！
)
echo.
echo 💡 [提示] 若您擁有 Gemini API Key，請在下方貼上。
echo    (直接按 Enter 鍵將以「展示與檢索測試模式」啟動，免金鑰即可使用搜尋功能)
echo.
set /p USER_KEY="👉 請貼上您的 GEMINI_API_KEY: "

if not "%USER_KEY%"=="" (
    set GEMINI_API_KEY=%USER_KEY%
    echo.
    echo [✔] 已成功為本工作階段載入您的 GEMINI_API_KEY！
) else (
    echo.
    echo [!] 未輸入金鑰，系統將以「展示模式」啟動（僅支援文章檢索與筆記功能）。
)

echo.
echo [*] 正在您的瀏覽器中開啟前端介面...
start http://localhost:8000
echo.
echo [*] 正在啟動 FastAPI 後端服務...
echo.
%PY_EXEC% -m uvicorn app:app --reload --port 8000
if %errorlevel% neq 0 (
    echo [!] 後端服務異常終止。
)
pause
