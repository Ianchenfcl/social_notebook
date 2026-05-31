# 🚀 ForumRAG-Explorer (CatchLM) - 專為論壇精華區設計的開源 RAG 智慧導讀工具 / Open-Source Forum RAG Explorer

<p align="center">
  <img src="https://img.shields.io/badge/License-MIT-green.svg" alt="License">
  <img src="https://img.shields.io/badge/Python-3.9+-blue.svg" alt="Python Version">
  <img src="https://img.shields.io/badge/RAG-SQLite%20%26%20ChromaDB-orange.svg" alt="RAG Architecture">
  <img src="https://img.shields.io/badge/Google%20Gemini-3.5%20Flash%20%2F%203.1%20Lite-purple.svg" alt="Models">
</p>

---

## 🌐 Quick Links / 語言切換
* [繁體中文版說明](#繁體中文版說明-traditional-chinese)
* [English Version](#english-version)

---

# 繁體中文版說明 (Traditional Chinese)

## 📌 項目定位與宣告
**ForumRAG-Explorer (CatchLM)** 是一個**純技術性研究的開源 RAG（檢索增強生成）架構探討工具**。

### 💡 開發初衷與技術挑戰
在閱讀傳統論壇（如 BBS / PTT）長篇精華區時，使用者常面臨「文章篇幅過長、資訊碎片化、難以檢索特定主題」的痛點。然而，若直接使用通用型大語言模型（LLM）回答，極易產生 **AI 幻覺（Hallucination）**，且無法提供可信賴的參考來源。

為了探討如何讓 AI 在長篇樹狀論壇目錄中進行**精準語意檢索與 100% 溯源對照**，我們開發了這套基於 **SQLite（結構化目錄管理）+ ChromaDB（向量相似度检索）** 的雙效 RAG 系統。本專案以 **PTT CATCH 板精華區的公開爆款文章（57 篇，切分為 366 個語意區塊）作為評估用測試數據集（Showcase Dataset）**，藉此驗證本 RAG 導讀架構在特定領域語境下的精準引用能力。

> [!IMPORTANT]
> **免責與中立性聲明**：本專案為開源輔助導讀工具與 AI 架構實驗，**工具本身為純技術中立，不對資料集內文回答的觀點做任何背書或價值判斷**。AI 的回答均基於公開論壇歷史前輩們留下的文章，若有引用偏差，均屬 Embedding 向量模型或 Prompt 調校之技術改進空間。

---

## 🌟 核心特色 (技術亮點)

1. **🔗 尊重版權與原作者的「引用溯源橋樑」（Fair Use Citation Bridge）**：
   - 系統嚴格遵守著作權法合理使用範疇。AI 生成的每一句分析，皆會強制帶上 `[Source X]` 引用徽章。
   - **活化論壇資產**：左側文檔與右側引文對照面板均支援**點擊直連 PTT 網頁版原文超連結**，作為「通往原文的橋樑」，為主站原貼文進行二次導流與活化。
2. **三欄式 RAG 語意導讀介面**：
   - **左欄**：測試數據集列表（支援點擊直跳 PTT 分頁）。
   - **中欄**：RAG 智慧對答視窗，動態渲染 `[Source]` 溯源 Pill Badges。
   - **右欄**：雙分頁對照（原文片段高亮對照檢視 + 用戶筆記編輯器）。
3. **🔒 100% 客戶端隱私保護**：
   - API Key 僅儲存於用戶瀏覽器本地 `localStorage`，不經過任何後端伺服器，免除金鑰洩漏風險。
4. **🔌 高度可擴充性（Board-Agnostic）**：
   - 核心 SQLite + ChromaDB 檢索管線完全獨立。此系統架構可輕鬆套用到 Stock 板、PC_Shopping 板等其他論壇精華區。

---

## 🛠️ 快速開始 (Windows 雙擊即用)

本專案經過傻瓜化封裝，**使用者完全無需開啟終端機手動下指令安裝套件**！

### 步驟 1：取得免費的 Gemini API Key
1. 前往 **[Google AI Studio](https://aistudio.google.com/)**。
2. 點擊 **"Get API key"** -> **"Create API key"** 並複製您的金鑰（格式為 `AIzaSy...`）。

### 步驟 2：一鍵啟動
1. 在專案根目錄下，直接雙擊執行 **`start.bat`**。
2. 腳本會**全自動背景檢查並安裝**環境所需的 Python 套件（如已安裝將以毫秒級速度自動跳過），並自動於瀏覽器開啟：
   👉 **`http://localhost:8000`**
3. 貼上您的 API Key 並選擇模型，即可開始評估 RAG 效能！
   *(若暫無金鑰，直接 Enter 即可進入「展示檢索模式」體驗本地語意搜尋)*

---

# English Version

## 📌 Project Positioning
**ForumRAG-Explorer (CatchLM)** is an **open-source technical research framework and utility tool designed for RAG (Retrieval-Augmented Generation) exploration over hierarchical legacy forum archives.**

Rather than generating custom content, this project demonstrates how to structure a robust **SQLite (structural metadata index) + ChromaDB (vector retrieval) dual-engine pipeline** to solve AI hallucinations and citation absence when digesting extremely long discussion threads. The public archive of PTT CATCH is leveraged strictly as a **showcase dataset** to evaluate semantic search and precise citation accuracy.

---

## 🌟 Key Technical Features

1. **🔗 Fair Use Citation Bridge**:
   - Strictly respects copyrights. Every generative claim is strictly anchored via `[Source X]` citations.
   - Clickable source cards and citation tags **link back directly to the original PTT web URLs in a new tab**, driving web traffic back to original threads and revitalizing community assets.
2. **Three-Column RAG Explorer Interface**:
   - *Left*: Test dataset catalog with clickable web-view links.
   - *Middle*: Semantic Q&A with dynamic source anchor badges.
   - *Right*: Dual-tab panel (Cited source paragraph viewer + Local Scratch Note editor).
3. **🔒 100% Local Privacy**:
   - API keys are secured purely within browser `localStorage`. No backend server logging is involved.
4. **🔌 Generic and Board-Agnostic Architecture**:
   - Easily adaptable! This RAG pipeline can be seamlessly deployed over other public discussion archives (e.g., Stock forums, Tech purchase guides).

---

## 🛠️ Quick Start (One-Click Setup)

No manual CLI commands are required!

### Step 1: Obtain a Free Gemini API Key
1. Go to **[Google AI Studio](https://aistudio.google.com/)**.
2. Click **"Get API key"** -> **"Create API key"** and copy your `AIzaSy...` key.

### Step 2: One-Click Launch
1. Double-click **`start.bat`** in the project root folder.
2. The batch script will **automatically verify and install all Python requirements in the background**, then open:
   👉 **`http://localhost:8000`**
3. Input your API Key and choose a model to evaluate the RAG retriever!
   *(You can also skip key configuration by pressing Enter to start in "Demo Retrieval Mode")*
