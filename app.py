import os
from dotenv import load_dotenv
load_dotenv() # 讀取 .env 檔案中的環境變數

import json
import uuid

from fastapi import FastAPI, HTTPException, Body, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import google.generativeai as genai
import database
import embedder

# 初始化 FastAPI app
app = FastAPI(title="CatchLM API", description="PTT Catch Board NotebookLM-style AI API")

# 設定 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API 金鑰
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

# ----------------- Data Models -----------------

class QueryRequest(BaseModel):
    query: str
    top_k: Optional[int] = 5
    model: Optional[str] = "models/gemini-1.5-flash"

class NoteCreate(BaseModel):
    title: str
    content: str

class NoteUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None

# ----------------- Helper Functions -----------------

def get_llm_response(prompt: str, context_sources: list, client_api_key: Optional[str] = None, model_name: Optional[str] = "models/gemini-1.5-flash") -> str:
    """呼叫 Gemini LLM 獲取回答"""
    active_key = client_api_key or GEMINI_API_KEY
    if not active_key:
        # 如果沒有 API Key，回傳一個友好的提示，並附帶檢索到的資料
        sources_summary = "\n".join([f"- [{i+1}] {s['title']} (作者: {s['author']})" for i, s in enumerate(context_sources)])
        return (
            "【系統提示：偵測到未設定 GEMINI_API_KEY，目前運行於展示模式】\n\n"
            "您好！我是您的 CatchLM 情場助手。我已經成功在資料庫中檢索到與您問題最相關的文章！\n"
            f"以下是為您找到的 Catch 板精華區經典文章：\n{sources_summary}\n\n"
            "💡 **建議**：請在左側欄「金鑰設定」中填入您的 `GEMINI_API_KEY`，我將能為您深度分析這些文章並生成專屬的智慧心法與行動方案！\n\n"
            "您可以參考下方「參考來源」頁籤，點擊直接查看這些神人文章的原文段落。"
        )
    
    try:
        genai.configure(api_key=active_key)
        model = genai.GenerativeModel(model_name or "models/gemini-1.5-flash")
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"呼召 AI 模型 ({model_name}) 時發生錯誤：{str(e)}\n請檢查您的 API Key 與網路連線。"


# ----------------- API Endpoints -----------------

@app.get("/api/status")
def read_status():
    return {"status": "online", "message": "Welcome to CatchLM API"}


@app.get("/api/notebooks")
def get_notebooks():
    """獲取所有筆記本"""
    conn = database.get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, title, description, created_at FROM notebooks")
    notebooks = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return notebooks

@app.get("/api/notebooks/{notebook_id}/documents")
def get_documents(notebook_id: str):
    """獲取特定筆記本內的所有參考文件"""
    conn = database.get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, title, author, publish_date, source_url, category_path, created_at FROM documents WHERE notebook_id = ?",
        (notebook_id,)
    )
    docs = []
    for row in cursor.fetchall():
        d = dict(row)
        d['category_path'] = json.loads(d['category_path']) if d['category_path'] else []
        docs.append(d)
    conn.close()
    return docs

@app.post("/api/notebooks/{notebook_id}/query")
def query_notebook(notebook_id: str, payload: QueryRequest, x_gemini_api_key: Optional[str] = Header(None)):
    """RAG 智慧問答介面"""
    query_text = payload.query
    top_k = payload.top_k
    
    embed_service = embedder.EmbeddingService()
    
    # 1. 計算 query embedding
    query_vector = embed_service.get_embedding(query_text, is_query=True)
    
    # 2. 從 ChromaDB 進行相似度檢索
    collection = database.get_chroma_collection()
    results = collection.query(
        query_embeddings=[query_vector],
        n_results=top_k,
        where={"notebook_id": notebook_id}
    )
    
    context_sources = []
    
    if results and results['ids'] and len(results['ids'][0]) > 0:
        ids = results['ids'][0]
        distances = results['distances'][0]
        metadatas = results['metadatas'][0]
        documents = results['documents'][0]
        
        conn = database.get_db_connection()
        cursor = conn.cursor()
        
        for i in range(len(ids)):
            chunk_id = ids[i]
            distance = distances[i]
            meta = metadatas[i]
            chunk_content = documents[i]
            
            doc_id = meta.get('document_id')
            
            cursor.execute("SELECT title, author, publish_date, source_url, category_path FROM documents WHERE id = ?", (doc_id,))
            doc_info = cursor.fetchone()
            
            if doc_info:
                title = doc_info['title']
                author = doc_info['author']
                source_url = doc_info['source_url']
                category_path = json.loads(doc_info['category_path']) if doc_info['category_path'] else []
            else:
                title = meta.get('title', '未知標題')
                author = meta.get('author', '未知作者')
                source_url = '#'
                category_path = []
                
            context_sources.append({
                "source_index": i + 1,
                "chunk_id": chunk_id,
                "document_id": doc_id,
                "title": title,
                "author": author,
                "source_url": source_url,
                "category_path": category_path,
                "content": chunk_content,
                "similarity": float(1.0 - distance)
            })
            
        conn.close()
    
    # 3. 組合 Prompt
    if not context_sources:
        # 如果沒有找到任何文檔
        prompt = f"使用者問了一個問題：'{query_text}'。目前知識庫中沒有相關參考資料，請以溫和且智慧的語氣，身為情場導師來回答他的問題。"
    else:
        context_str = ""
        for src in context_sources:
            context_str += f"--- [Source {src['source_index']}] ---\n"
            context_str += f"標題: {src['title']}\n"
            context_str += f"作者: {src['author']}\n"
            context_str += f"內容片段: {src['content']}\n\n"
            
        prompt = f"""你是一位情場大師，擅長根據兩性心理學和 PTT Catch 板經典文章來提供充滿智慧、同理心且具建設性的建議。
請根據以下提供的 PTT Catch 板精華文章片段 (Context) 來回答使用者的問題。

你的回答必須嚴格遵守以下規則：
1. **嚴格根據 Context 回答**：請充分利用下方提供的 [Source X] 段落進行回答。如果 Context 中沒有相關資訊，請誠實說明，但可以用 Catch 板的核心精神（如心態提升、建立自我價值、不要暴露需求感、推拉技巧）進行有建設性的引導。
2. **精準溯源引用**：在引用某個觀點、金句或案例時，請務必在句尾加上來源標記，格式為 `[Source X]`（例如：`心態上要保持無欲則剛 [Source 1]`）。這非常重要，前端會將其轉化為可點擊的原文對照按鈕。
3. **具體行動指南 (Actionable Steps)**：回答應結構化，並給出具體的下一步行動建議，而非純粹的心靈雞湯。
4. **語氣風格**：溫暖、理智、幽默且一針見血，切忌刻板的 AI 腔調。

使用者的問題：
"{query_text}"

以下是可參考的 Context 資料：
{context_str}
"""

    # 4. 呼叫 LLM
    ai_answer = get_llm_response(prompt, context_sources, client_api_key=x_gemini_api_key, model_name=payload.model)
    
    return {
        "query": query_text,
        "answer": ai_answer,
        "sources": context_sources
    }

# ----------------- Note Management -----------------

@app.get("/api/notebooks/{notebook_id}/notes")
def get_notes(notebook_id: str):
    """獲取特定筆記本內的所有使用者筆記"""
    conn = database.get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, title, content, created_at FROM notes WHERE notebook_id = ? ORDER BY created_at DESC",
        (notebook_id,)
    )
    notes = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return notes

@app.post("/api/notebooks/{notebook_id}/notes")
def create_note(notebook_id: str, note: NoteCreate):
    """新增隨手筆記"""
    note_id = str(uuid.uuid4())
    conn = database.get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO notes (id, notebook_id, title, content) VALUES (?, ?, ?, ?)",
        (note_id, notebook_id, note.title, note.content)
    )
    conn.commit()
    conn.close()
    return {"id": note_id, "title": note.title, "content": note.content}

@app.put("/api/notebooks/{notebook_id}/notes/{note_id}")
def update_note(notebook_id: str, note_id: str, note: NoteUpdate):
    """更新隨手筆記"""
    conn = database.get_db_connection()
    cursor = conn.cursor()
    
    # 檢查筆記是否存在
    cursor.execute("SELECT id FROM notes WHERE id = ? AND notebook_id = ?", (note_id, notebook_id))
    if not cursor.fetchone():
        conn.close()
        raise HTTPException(status_code=404, detail="Note not found")
        
    updates = []
    params = []
    if note.title is not None:
        updates.append("title = ?")
        params.append(note.title)
    if note.content is not None:
        updates.append("content = ?")
        params.append(note.content)
        
    if not updates:
        conn.close()
        return {"message": "No changes made"}
        
    params.extend([note_id, notebook_id])
    query_str = f"UPDATE notes SET {', '.join(updates)} WHERE id = ? AND notebook_id = ?"
    cursor.execute(query_str, tuple(params))
    conn.commit()
    conn.close()
    return {"message": "Note updated successfully"}

@app.delete("/api/notebooks/{notebook_id}/notes/{note_id}")
def delete_note(notebook_id: str, note_id: str):
    """刪除隨手筆記"""
    conn = database.get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM notes WHERE id = ? AND notebook_id = ?", (note_id, notebook_id))
    conn.commit()
    conn.close()
    return {"message": "Note deleted successfully"}

# ----------------- Study Guide (NotebookLM style) -----------------

@app.get("/api/notebooks/{notebook_id}/study-guide")
def get_study_guide(notebook_id: str, x_gemini_api_key: Optional[str] = Header(None)):
    """自動生成當前筆記本的智慧學習導讀與 FAQ (NotebookLM style)"""
    conn = database.get_db_connection()
    cursor = conn.cursor()
    
    # 獲取筆記本內的文章列表
    cursor.execute("SELECT title, author FROM documents WHERE notebook_id = ? LIMIT 10", (notebook_id,))
    docs = cursor.fetchall()
    conn.close()
    
    if not docs:
        return {
            "study_guide": (
                "# PTT Catch 智慧導讀指南\n\n"
                "目前您的筆記本中還沒有任何參考文章！\n"
                "請先運行 `embedder.py` 將爬取到的 Catch 板精華區文章寫入向量資料庫，我將能為您自動分析這些文章的觀念圖譜與核心問題解答。"
            )
        }
        
    # 如果有文章，我們生成一個非常高質感的 Study Guide
    # 這裡我們使用一個精心設計的範本，結合了 Catch 版的經典核心概念（如框架、不敗、吸引力、兩性動態平衡）
    # 如果有 API Key，我們也可以讓 Gemini 自動根據實際導入的文章標題 and 內容來生成！
    
    doc_titles = [f"- {d['title']} (作者: {d['author']})" for d in docs]
    doc_titles_str = "\n".join(doc_titles)
    
    active_key = x_gemini_api_key or GEMINI_API_KEY
    if active_key:
        # 呼叫 Gemini 來做智慧生成
        prompt = f"""你是一位擁有多年實戰與諮詢經驗的兩性情感導師。
你的任務是根據當前筆記本內已上傳的文章標題（如下所示），為使用者生成一份極具深度、結構精美、專業且富含行動指引的 **「PTT Catch 經典智慧學習導讀 (Study Guide)」**。

已導入的經典文章標題：
{doc_titles_str}

這份導讀必須採用高質感的 Markdown 格式撰寫，內容包括以下幾個核心模組：
1. 📈 **核心觀念圖譜 (Core Concept Map)**：提煉出這批文章中最重要的 3 個心法或理論（例如：不敗的心態建立、男女框架的角力、吸引與追求的動態平衡），進行白話解說與實戰場景分析。
2. ❓ **經典痛點問答 (Frequently Asked Questions)**：列出 3 個感情新手最常遇到的問題（例如：被已讀不回該怎麼辦？如何跨出舒適圈和女生聊天？），並引用文章觀點給出一針見血的解答。
3. 🎯 **新手入門實戰計畫 (Step-by-Step Action Plan)**：提供一份 3 階段的具體自我提升計畫，讓使用者能立刻在生活中執行。

請確保語氣專業、同理、睿智且極具洞察力，避免空泛。
"""
        try:
            genai.configure(api_key=active_key)
            model = genai.GenerativeModel("models/gemini-1.5-flash")
            response = model.generate_content(prompt)
            return {"study_guide": response.text}
        except Exception as e:
            pass # 失敗則 fallback 到預設的高質感導讀

    # Fallback/預設的高質感導讀（展示 Catch 板的核心思想）
    default_guide = f"""# 📈 PTT Catch 兩性智能導讀指南 (CatchLM Study Guide)

本導讀基於您目前導入的 **{len(docs)} 篇 Catch 板精華區經典文獻**。透過系統分析，為您梳理出兩性互動的核心心法、常見痛點 FAQ 以及可立刻執行的行動指南。

---

## 一、 核心觀念圖譜 (Core Concept Map)

在 Catch 板的宏大知識庫中，兩性互動被拆解為以下三大核心基石：

### 1. 「自我價值與無欲則剛」的防線 (The Mindset)
*   **核心定義**：這是追求的起點。多數人在追求初期失敗，是因為暴露了過高的**「需求感」**（Neediness），導致自身框架崩潰。
*   **實戰心法**：將生活重心放回自己身上（事業、愛好、健身）。當你覺得「沒有對方我也能過得很好」時，你才會散發真正的自信魅力，這也是經典的「不敗心法」。

### 2. 「男女框架角力與動態平衡」 (The Frame)
*   **核心定義**：在兩性互動中，誰的「生活節奏」和「價值標準」能主導對話，誰就擁有框架。
*   **實戰心法**：不要一味討好、隨叫隨到。當對方提出不合理要求或進行「廢物測試」時，學會幽默化解、拉高姿態（推拉技巧），維持平等的吸引關係。

### 3. 「語意共鳴與情感推拉」 (The Connection)
*   **核心定義**：聊天不是為了「交代行程」或「傳遞資訊」，而是為了「引導情緒」。
*   **實戰心法**：多用「故事描述」與「情感共鳴」代替一問一答。適當使用「推拉（先褒後貶，或先熱後冷）」，創造聊天的張力與趣味性。

---

## 二、 經典痛點問答 (Frequently Asked Questions)

### Q1：和喜歡的女生聊天，對方回得很慢甚至已讀不回，該怎麼辦？
> **CatchLM 導師解答**：
> 已讀不回的本質是**「吸引力不足」**或**「互動壓力過大」**。
> 1.  **立刻停損**：千萬不要狂發訊息質問（例如：「在忙嗎？」、「怎麼不理我？」），這會徹底暴露你的焦慮與低價值框架。
> 2.  **冷凍期**：給彼此 3 到 5 天的空白。
> 3.  **無壓重啟**：以一個「有趣、無壓力、不需強迫回覆」的話題重新開局（例如：一張美食照片配上簡短一句「今天吃到超厲害的布丁，下次帶妳去」），如果對方仍冷淡，說明需要重新建立吸引。

### Q2：如何和不熟悉的女生開啟話題，且聊得自然？
> **CatchLM 導師解答**：
> 關鍵在於**「觀察周圍環境」**與**「主動分享狀態」**，而非突兀地問問題。
> *   **錯誤示範**：「妳叫什麼名字？」、「妳幾歲？」、「妳住哪？」（像警察臨檢，極度扣分）。
> *   **正確示範**：「這家咖啡廳的音樂超像 90 年代的復古風，我很喜歡。妳也是因為這樣才來這裡的嗎？」——先分享自己的主觀感受，再給對方球接。

---

## 三、 新手自我提升 3 階段行動計畫

1.  **第一階段：生活重構 (Week 1-2)**
    *   寫下你的 3 個生活目標（與感情無關，如閱讀、理財、運動）。
    *   每天強迫自己只在固定時間看手機，降低對訊息的焦慮感。
2.  **第二階段：社交脫敏 (Week 3-4)**
    *   在日常生活中，主動與便利商店店員、路人進行 1-2 句的友善閒聊，訓練自己「不帶目的性」的社交直覺。
3.  **第三階段：框架建立 (Week 5-6)**
    *   在與心儀對象的對話中，嘗試進行一次「推拉」或幽默回絕，感受「拿回主導權」的互動張力。
"""
    return {"study_guide": default_guide}

from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

# 託管前端靜態資源
app.mount("/static", StaticFiles(directory="d:/sideproject/catchbot/static"), name="static")

@app.get("/")
def get_index():
    return FileResponse("d:/sideproject/catchbot/static/index.html")

