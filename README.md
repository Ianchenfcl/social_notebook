# 🚀 CatchLM - PTT Catch 智慧情感知識庫 / Relationship RAG Platform

CatchLM 是一款仿 **NotebookLM** 設計的智慧情感導讀與對話平台。基於雙效資料庫（SQLite + ChromaDB），結合 Google Gemini 模型，讓您與兩性精華區的多位大師進行深度對話，並具備原文高亮對照、引用溯源與隨手筆記編輯功能。

---

## 🌐 Quick Start / 快速開始

### 1. 🔑 取得免費的 Gemini API Key / Get API Key
1. 前往 **[Google AI Studio](https://aistudio.google.com/)**。
2. 點擊 **"Get API key"** -> **"Create API key"** 並複製金鑰（`AIzaSy...`）。

### 2. 🚀 一鍵啟動 / One-Click Run
1. 本專案**免手動下指令安裝套件**！
2. 在專案根目錄下，直接雙擊執行 **`start.bat`**。
3. 啟動腳本會**全自動檢查/安裝環境所需的 Python 套件**，並自動於瀏覽器開啟：**`http://localhost:8000`**。
4. 在網頁左下角貼上您的 API Key 並選擇模型，即可開始！
   *(若暫時無金鑰，直接按 Enter 啟動即可進入「展示檢索模式」)*

---

## 🌟 核心特色 / Features
* **💎 純淨爆款神作集**：自動收錄 57 篇殿堂級經典情感文章（366 個語意區塊），自動過濾公告噪聲。
* **三欄式質感介面 (Tailwind CSS)**：
  * **左欄**：參考來源清單（支援**一鍵點擊直接在新分頁開啟 PTT 網頁版原文**）。
  * **中欄**：AI 問答視窗（句尾帶有可點擊的 `[Source X]` 引用標籤）。
  * **右欄**：雙分頁原文片段高亮對照 + 隨手筆記本。
* **🔒 安全保護**：API Key 保存在瀏覽器 `localStorage`，不經過後端伺服器儲存。
* **⚙️ 降級展示模式**：未輸入 Key 時自動降級為展示模式，依然可正常搜尋文章與記錄筆記。

---

## 📂 專案架構 / Architecture
* `start.bat`：一鍵自動確認依賴並啟動服務的 Windows 批次檔。
* `app.py`：使用 FastAPI 實作的後端與 RAG 搜尋接口。
* `database.py` & `embedder.py`：雙資料庫系統與自動清空舊資料的向量管線。
* `static/index.html`：毛玻璃質感 SPA 前端介面。
