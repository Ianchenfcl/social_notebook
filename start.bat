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
echo [*] 正在確認環境所需的 Python 套件已安裝 (若已安裝將極速跳過)...
pip install -r requirements.txt --quiet
if %errorlevel% neq 0 (
    echo [!] 自動確認套件時遇到些微狀況，將嘗試直接載入服務...
) else (
    echo [✔] 環境套件確認完畢！
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
uvicorn app:app --reload --port 8000
pause
