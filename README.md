# 🚀 戀愛AI - PTT Catch 智慧情感開源知識庫 / Relationship RAG Platform

<p align="center">
  <img src="https://img.shields.io/badge/License-MIT-green.svg" alt="License">
  <img src="https://img.shields.io/badge/Python-3.9+-blue.svg" alt="Python Version">
  <img src="https://img.shields.io/badge/Database-SQLite%20%26%20ChromaDB-orange.svg" alt="Database">
  <img src="https://img.shields.io/badge/AI%20Brain-Gemini%201.5%2520Flash-purple.svg" alt="AI Brain">
</p>

---

## 🌐 Quick Links / 語言切換
* [繁體中文版說明](#繁體中文版說明-traditional-chinese)
* [English Version](#english-version)

---

# 繁體中文版說明 (Traditional Chinese)

## 📌 項目簡介
**戀愛AI** 是一款專為兩性溝通與吸引力科學深度訂製的 **開源智慧情感導讀與對話平台**。

本專案支援 **多主體知識庫 (Multi-Notebook) 切換**，預設提供兩個精心整理的知識庫：
1. **📚 PTT Catch 精華區**：收錄自 2005 年創板以來，經萬人推爆（推文數 $\ge 99$ 的「爆」文）的 57 篇殿堂級情感神作（共 366 個高品質語意區塊），自動過濾公告噪音，保留最純粹的互動心法。
2. **📖 經典情感與把妹書籍**：自動提取並向量化 15 本情感與社交動力學經典文獻（如《謎男方法》、《把妹達人》、《冷讀術》、《魔鬼搭訕學》等共 680 個語意區塊）。

系統利用先進的 **RAG（檢索增強生成）** 技術，讓您能與多位情感大師和經典書籍作者進行深度對話，一鍵生成智慧學習導讀（Study Guide），並針對您的兩性溝通、心態提升等問題，提供極具建設性的客製化行動方案！

---

## 🛡️ 設計理念與著作權尊重 (技術中立)

為了保障開源社群的健康發展、尊重原作者權益，並避免不必要的內容爭議，**戀愛AI** 在設計上導入了以下關鍵機制：

1. **🔗 尊重著作權的「引用溯源橋樑」（Fair Use Citation Bridge）**：
   - **合理使用（Fair Use）**：本系統扮演「通往原著與精華區的橋樑」。AI 的每一句回答都會強制帶上可點擊的 `[Source X]` 引用標籤。
   - **雙向網頁導流**：左側文檔列表與右側引文對照面板，均已串接 **PTT 網頁版原文或 GitHub 經典書籍原著之超連結**。使用者點擊即可在**新分頁直接開啟原文**，有效為論壇與原著作者引流，活化經典資產。
2. **🧠 技術中立與零幻覺防禦**：
   - 採用 **SQLite（目錄管理）+ ChromaDB（向量檢索）** 雙核心引擎，確保 AI 僅根據所選知識庫內的文獻真實內容進行回答，防禦 AI 瞎編與幻覺。
   - **免責宣告**：本工具為純技術中立之開源閱讀輔助外掛，不對資料庫內文之觀點做任何背書。
3. **🔒 用戶隱私防護**：
   - API Key 僅儲存於用戶本機瀏覽器 `localStorage`，不經過任何後端伺服器，確保金鑰隱私絕對安全。

---

## 🌟 核心特色 (Features)
* **🗂️ 多主體知識庫自由切換**：可於左側控制面板無縫切換「PTT Catch 精華區」與「經典情感與把妹書籍」兩大知識庫，載入不同文件並與 AI 對話。
* **📞 撥打電話給戀愛AI導師**：點擊右上角「撥打語音導師」按鈕，即可與多種風格的 AI 語音導師（如 Zephyr, Puck 等）進行如同打電話般的即時語音對話。
  * **全新支援「螢幕分享」與「鏡頭分享」模式**：能讓 AI 導師看著您的聊天紀錄或直接指導您的穿搭與肢體動作。
  * 支援 **Barge-in（插話打斷）** 功能，讓您的兩性對話演練更加逼真。
* **📝 情感互動測驗 (Interactive Quizzes)**：內建多達 9 種不同難度與主題的實戰測驗題庫（包含「廢物測試特訓」、「網路交友特訓」等特選題），隨時檢驗您的聊天心法與社交框架，並支援個人進度儲存與重新測驗。
* **💎 純淨無噪聲資料庫**：自動過濾板規、公告等噪聲，專注於實戰與心法。
* **🎨 三欄式質感介面 (Tailwind CSS)**：
  * **左欄**：參考來源清單（支援一鍵點擊在新分頁開啟原文，並可一鍵生成 Study Guide 智慧導讀大綱）。
  * **中欄**：AI 問答視窗（帶有 `[Source X]` 引用智慧徽章）。
  * **右欄**：多功能面板（包含個人筆記、原文對照、情感測驗），**支援一鍵放大至全螢幕**，方便無干擾閱讀或測驗。
* **⚙️ 降級展示模式**：未輸入 Key 時自動降級為展示模式，依然可正常搜尋文章與記錄筆記。

---

## 🛠️ 快速開始

本專案經過自動化封裝，支援 Windows 與 macOS/Linux 系統！

### 步驟 1：取得免費的 Gemini API Key
1. 前往 **[Google AI Studio](https://aistudio.google.com/)**。
2. 點擊 **"Get API key"** -> **"Create API key"** 並複製您的金鑰（格式為 `AIzaSy...`）。

### 步驟 2：啟動系統
*   **Windows 系統**：在專案根目錄下，直接雙擊執行 **`start.bat`**。
*   **macOS / Linux 系統**：打開終端機（Terminal），切換至專案根目錄，執行以下指令：
    ```bash
    chmod +x start.sh
    ./start.sh
    ```
啟動腳本會**全自動於背景檢查並安裝**環境所需的 Python 套件（採用 `.venv` 獨立虛擬環境隔離，不影響您原本的系統設定），並自動開啟瀏覽器：
👉 **`http://localhost:8000`**

貼上您的 API Key 並選擇模型，即可開始！
*(若暫無金鑰，直接按 Enter 即可進入「展示檢索模式」體驗本地語意搜尋)*

---

# English Version

## 📌 About 戀愛AI (Love AI Tutor)
**戀愛AI** is an open-source **Relationship RAG Platform** deeply tailored for the PTT CATCH community (a premier forum for relationship psychology and soft skills) and classic literature on relationship/social dynamics. 

By indexing **57 legendary dating masterpieces (366 high-quality semantic chunks)** with $\ge 99$ upvotes since 2005, and **15 classic relationship books** (e.g. *The Mystery Method*, *The Game*, *Cold Reading*), users can chat or **make live voice calls** with top-tier relationship mentors. It leverages **RAG (Retrieval-Augmented Generation)** to generate custom action plans, mindset training, and Study Guides to elevate your communication skills!

---

## 🛡️ Strategic Design (Copyright Respect & Neutrality)

To protect the open-source community and respect original authors, 戀愛AI implements:

1. **🔗 Fair Use Citation Bridge**:
   - Every AI-synthesized claim is strictly anchored via `[Source X]` badges.
   - Clickable cards and source viewers **link back directly to the original PTT web URLs or book sources in a new tab**, driving web traffic back to original threads and revitalizing community assets.
2. **🧠 Advanced RAG to Prevent Hallucination**:
   - Built on a **SQLite + ChromaDB** dual engine, ensuring AI only answers based on verified classics.
   - **Neutrality Disclaimer**: 戀愛AI is a technical reading utility; it remains content-neutral and does not endorse any specific advice in the dataset.
3. **🔒 Client-Side Local Privacy**:
   - API keys are secured purely within browser `localStorage`. No backend server logging is involved.

---

## 🌟 Key Features
- **🗂️ Multi-Notebook Support**: Swap between "PTT Catch Classics" and "Classic Relationship Books" on the fly.
- **📞 Phone Call with AI Mentors**: Click "撥打語音導師" to voice call multiple AI coaches (Zephyr, Puck, etc.) with real-time **barge-in / interruption** support.
  - **Screen & Camera Sharing**: Allow the AI mentor to view your screen (e.g., chat logs) or camera (e.g., outfit checks) for ultra-personalized feedback.
- **📝 Interactive Quizzes**: Test your social dynamics and mindset with 9 different relationship quizzes, complete with progress tracking and retry mechanics.
- **🎨 Premium Triple-Panel UI**: Clean responsive design with source indexing, interactive RAG chat window, and a multi-functional side panel (Notes, Source Viewer, Quizzes) that supports **fullscreen expansion** for distraction-free reading.

---

## 🛠️ Quick Start

This project is packaged with automation scripts for both Windows and macOS/Linux.

### Step 1: Obtain a Free Gemini API Key
1. Go to **[Google AI Studio](https://aistudio.google.com/)**.
2. Click **"Get API key"** -> **"Create API key"** and copy your `AIzaSy...` key.

### Step 2: Launch the System
*   **Windows**: Double-click **`start.bat`** in the project root folder.
*   **macOS / Linux**: Open your Terminal, navigate to the project root directory, and run:
    ```bash
    chmod +x start.sh
    ./start.sh
    ```
The launch script will **automatically create a Python virtual environment (`.venv`), install all requirements**, and open:
👉 **`http://localhost:8000`**

Input your API Key and choose a model to start!
*(You can also skip key configuration by pressing Enter to start in "Demo Retrieval Mode")*

