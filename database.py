import os
import sqlite3
import json
import uuid
import chromadb
from chromadb.config import Settings

DB_PATH = "d:/sideproject/catchbot/catch_notebook.db"
CHROMA_PATH = "d:/sideproject/catchbot/chroma_db"

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """初始化 SQLite 關聯式資料庫與 ChromaDB 向量資料庫"""
    # 1. 初始化 SQLite
    print("Initializing SQLite Database...")
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 建立 notebooks 表
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS notebooks (
        id TEXT PRIMARY KEY,
        title TEXT NOT NULL,
        description TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    # 建立 documents 表
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS documents (
        id TEXT PRIMARY KEY,
        notebook_id TEXT,
        title TEXT NOT NULL,
        author TEXT,
        publish_date TEXT,
        source_url TEXT,
        category_path TEXT, -- JSON array of strings
        raw_content TEXT NOT NULL,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (notebook_id) REFERENCES notebooks(id) ON DELETE CASCADE
    )
    ''')
    
    # 建立 document_chunks 表
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS document_chunks (
        id TEXT PRIMARY KEY,
        document_id TEXT NOT NULL,
        content TEXT NOT NULL,
        chunk_index INTEGER NOT NULL,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE
    )
    ''')
    
    # 建立 notes 表
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS notes (
        id TEXT PRIMARY KEY,
        notebook_id TEXT NOT NULL,
        title TEXT NOT NULL,
        content TEXT NOT NULL,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (notebook_id) REFERENCES notebooks(id) ON DELETE CASCADE
    )
    ''')
    
    # 預先插入一個預設的 PTT Catch 筆記本，如果不存在的話
    cursor.execute("SELECT id FROM notebooks WHERE id = 'default-catch-notebook-uuid'")
    if not cursor.fetchone():
        cursor.execute(
            "INSERT INTO notebooks (id, title, description) VALUES (?, ?, ?)",
            ("default-catch-notebook-uuid", "PTT Catch 精華區", "PTT Catch 板精華區經典文章智慧導讀知識庫")
        )
        print("Default notebook created.")
        
    # 預先插入把妹與情感經典書籍的筆記本，如果不存在的話
    cursor.execute("SELECT id FROM notebooks WHERE id = 'pua-books-notebook-uuid'")
    if not cursor.fetchone():
        cursor.execute(
            "INSERT INTO notebooks (id, title, description) VALUES (?, ?, ?)",
            ("pua-books-notebook-uuid", "把妹與情感經典書籍", "收錄把妹達人、謎男方法等經典兩性相處與社交動力學書籍")
        )
        print("PUA Books notebook created.")
        
    conn.commit()
    conn.close()
    
    # 2. 初始化 ChromaDB
    print("Initializing ChromaDB Persistent Client...")
    os.makedirs(CHROMA_PATH, exist_ok=True)
    chroma_client = chromadb.PersistentClient(path=CHROMA_PATH)
    # 我們不給予預設的 embedding 函數，因為我們會自己用 API 計算向量
    collection = chroma_client.get_or_create_collection(
        name="catch_chunks",
        metadata={"hnsw:space": "cosine"} # 使用餘弦相似度
    )
    print(f"ChromaDB initialized. Collection 'catch_chunks' is ready.")

def clear_db(notebook_id=None):
    """清空 SQLite 與 ChromaDB 中特定筆記本的舊文檔與向量資料，若 notebook_id 為 None 則清空全部"""
    print(f"Clearing document-related tables in SQLite for notebook: {notebook_id or 'ALL'}...")
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        if notebook_id:
            cursor.execute("""
                DELETE FROM document_chunks 
                WHERE document_id IN (SELECT id FROM documents WHERE notebook_id = ?)
            """, (notebook_id,))
            cursor.execute("DELETE FROM documents WHERE notebook_id = ?", (notebook_id,))
        else:
            cursor.execute("DELETE FROM document_chunks")
            cursor.execute("DELETE FROM documents")
        conn.commit()
        print("Successfully cleared document tables from SQLite.")
    except Exception as e:
        print(f"Error clearing SQLite tables: {str(e)}")
    finally:
        conn.close()

    print(f"Clearing ChromaDB collection for notebook: {notebook_id or 'ALL'}...")
    try:
        if notebook_id:
            try:
                collection = get_chroma_collection()
                collection.delete(where={"notebook_id": notebook_id})
                print(f"Successfully deleted vectors for notebook: {notebook_id} from ChromaDB.")
            except Exception as e:
                print(f"ChromaDB notebook delete error: {str(e)}")
        else:
            chroma_client = chromadb.PersistentClient(path=CHROMA_PATH)
            try:
                chroma_client.delete_collection("catch_chunks")
                print("Successfully deleted catch_chunks collection from ChromaDB.")
            except Exception as e:
                print(f"Collection delete log (can be ignored if collection did not exist): {str(e)}")
    except Exception as e:
        print(f"Error clearing ChromaDB: {str(e)}")


def save_document(doc_id, notebook_id, title, author, publish_date, source_url, category_path, raw_content):
    """儲存文件至 SQLite"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT OR REPLACE INTO documents 
        (id, notebook_id, title, author, publish_date, source_url, category_path, raw_content) 
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (doc_id, notebook_id, title, author, publish_date, source_url, json.dumps(category_path), raw_content)
    )
    conn.commit()
    conn.close()

def save_chunk(chunk_id, doc_id, content, chunk_index):
    """儲存文本區塊至 SQLite"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT OR REPLACE INTO document_chunks 
        (id, document_id, content, chunk_index) 
        VALUES (?, ?, ?, ?)
        """,
        (chunk_id, doc_id, content, chunk_index)
    )
    conn.commit()
    conn.close()

def get_chroma_collection():
    """獲取 ChromaDB 集合"""
    chroma_client = chromadb.PersistentClient(path=CHROMA_PATH)
    return chroma_client.get_or_create_collection(name="catch_chunks")

if __name__ == "__main__":
    init_db()
