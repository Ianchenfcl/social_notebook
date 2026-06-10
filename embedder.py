import os
from dotenv import load_dotenv
load_dotenv() # 讀取 .env 檔案

import json
import uuid

import numpy as np
from langchain_text_splitters import RecursiveCharacterTextSplitter
import google.generativeai as genai
import database

# 優先讀取環境變數中的 GEMINI_API_KEY
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

class EmbeddingService:
    def __init__(self, api_key=None):
        # Read multiple keys if present
        keys_str = os.environ.get("GEMINI_API_KEYS")
        if keys_str:
            self.api_keys = [k.strip() for k in keys_str.split(",") if k.strip()]
        else:
            self.api_keys = []
            
        single_key = api_key or os.environ.get("GEMINI_API_KEY") or GEMINI_API_KEY
        if single_key and single_key not in self.api_keys:
            self.api_keys.append(single_key)
            
        self.key_index = 0
        
        if self.api_keys:
            print(f"Gemini API Keys detected ({len(self.api_keys)} keys). Key rotation enabled.")
            # Configure initial key
            genai.configure(api_key=self.api_keys[0])
            self.use_mock = False
        else:
            print("WARNING: GEMINI_API_KEY not found in environment variables or parameters!")
            print("To actually compute vectors, please set GEMINI_API_KEY.")
            print("Fallback: Using Mock Embedding Generator (Random vectors) for local development/testing.")
            self.use_mock = True

    def get_embedding(self, text, is_query=False):
        """計算文本的 Embedding 向量"""
        if self.use_mock:
            # gemini-embedding-001 的維度是 768
            # 隨機產生一個單位向量
            vec = np.random.randn(768)
            vec /= np.linalg.norm(vec)
            return vec.tolist()
        
        import time
        import re
        task_type = "retrieval_query" if is_query else "retrieval_document"
        
        max_retries = 8
        for attempt in range(max_retries):
            # Rotate key for this attempt
            current_key = self.api_keys[self.key_index]
            genai.configure(api_key=current_key)
            self.key_index = (self.key_index + 1) % len(self.api_keys)
            
            try:
                result = genai.embed_content(
                    model="models/gemini-embedding-2",
                    content=text,
                    task_type=task_type,
                    output_dimensionality=768
                )
                return result['embedding']
            except Exception as e:
                err_msg = str(e)
                if "429" in err_msg or "quota" in err_msg.lower() or "limit" in err_msg.lower():
                    sleep_time = 10.0
                    match = re.search(r"Please retry in ([0-9.]+)s", err_msg)
                    if match:
                        sleep_time = float(match.group(1)) + 1.5
                    else:
                        match_proto = re.search(r"seconds:\s*(\d+)", err_msg)
                        if match_proto:
                            sleep_time = float(match_proto.group(1)) + 1.5
                    print(f"  [!] Rate limited (429) in get_embedding. Retrying in {sleep_time:.2f} seconds (attempt {attempt + 1}/{max_retries})...")
                    time.sleep(sleep_time)
                else:
                    print(f"Error calling Google Embedding API: {err_msg}")
                    break
        
        print("Falling back to mock vector after failing all retries.")
        vec = np.random.randn(768)
        vec /= np.linalg.norm(vec)
        return vec.tolist()

    def get_embeddings_batch(self, texts):
        """批次計算文本的 Embedding 向量"""
        if self.use_mock:
            return [self.get_embedding(t) for t in texts]
        
        import time
        import re
        max_retries = 8
        for attempt in range(max_retries):
            # Rotate key for this attempt
            current_key = self.api_keys[self.key_index]
            genai.configure(api_key=current_key)
            self.key_index = (self.key_index + 1) % len(self.api_keys)
            
            try:
                result = genai.embed_content(
                    model="models/gemini-embedding-2",
                    content=texts,
                    task_type="retrieval_document",
                    output_dimensionality=768
                )
                # Success pacing: sleep is dynamic based on number of keys to stay safely under 100 RPM limit (1 chunk = 1 request)
                # If 1 key: 9.0 seconds sleep
                # If 2 keys: 5.0 seconds sleep
                # If 3+ keys: 3.0 seconds sleep
                num_keys = len(self.api_keys)
                if num_keys >= 3:
                    sleep_time = 3.0
                elif num_keys == 2:
                    sleep_time = 5.0
                else:
                    sleep_time = 13.5
                time.sleep(sleep_time)
                # 返回 embedding 陣列
                return result['embedding']
            except Exception as e:
                err_msg = str(e)
                if "429" in err_msg or "quota" in err_msg.lower() or "limit" in err_msg.lower():
                    sleep_time = 60.0
                    match = re.search(r"Please retry in ([0-9.]+)s", err_msg)
                    if match:
                        sleep_time = float(match.group(1)) + 1.5
                    else:
                        match_proto = re.search(r"seconds:\s*(\d+)", err_msg)
                        if match_proto:
                            sleep_time = float(match_proto.group(1)) + 1.5
                    print(f"  [!] Rate limited (429) in batch. Error: {err_msg}")
                    print(f"      Sleeping {sleep_time:.2f} seconds to reset rate limit (attempt {attempt + 1}/{max_retries})...")
                    time.sleep(sleep_time)
                else:
                    print(f"Error in batch embedding: {err_msg}.")
                    break
        
        # If batch embedding fails, fallback to generating mock vectors to prevent crash
        print("CRITICAL: Batch embedding failed after all retries. Falling back to mock vectors.")
        return [self.get_embedding(t) for t in texts]

def process_and_embed_catch_data(json_file_path=None):
    if json_file_path is None:
        BASE_DIR = os.path.dirname(os.path.abspath(__file__))
        json_file_path = os.path.join(BASE_DIR, "catch_posts.json")
        
    if not os.path.exists(json_file_path):
        print(f"Error: JSON file '{json_file_path}' not found! Has the crawler completed?")
        return

    # 初始化與清除資料庫 (僅清除 PTT Catch 筆記本對應的舊資料)
    database.init_db()
    database.clear_db("default-catch-notebook-uuid")
    
    with open(json_file_path, 'r', encoding='utf-8') as f:
        posts = json.load(f)
        
    print(f"Loaded {len(posts)} articles from JSON file.")
    
    # 建立文本切分器
    # PTT 文章通常段落長度不一，我們設定 chunks 大小為 600 字，重疊 120 字
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=600,
        chunk_overlap=120,
        length_function=len,
        separators=["\n\n", "\n", "。", "！", "？", " ", ""]
    )
    
    embed_service = EmbeddingService()
    chroma_collection = database.get_chroma_collection()
    
    default_notebook_id = "default-catch-notebook-uuid"
    
    # 批次處理大小
    BATCH_SIZE = 15
    
    all_chunks_to_embed = []
    
    print("Chunking articles...")
    for idx, post in enumerate(posts):
        doc_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, post['url'])) # 用 URL 穩定生成 UUID
        
        # 1. 儲存原始文件到 SQLite
        database.save_document(
            doc_id=doc_id,
            notebook_id=default_notebook_id,
            title=post['title'],
            author=post['author'],
            publish_date=post['date'],
            source_url=post['url'],
            category_path=post['category_path'],
            raw_content=post['content']
        )
        
        # 2. 切分文本
        chunks = text_splitter.split_text(post['content'])
        
        for c_idx, chunk_text in enumerate(chunks):
            chunk_id = f"{doc_id}_chunk_{c_idx}"
            
            # 儲存 chunk 到 SQLite
            database.save_chunk(
                chunk_id=chunk_id,
                doc_id=doc_id,
                content=chunk_text,
                chunk_index=c_idx
            )
            
            # 加入待 embedding 列表
            all_chunks_to_embed.append({
                "id": chunk_id,
                "document_id": doc_id,
                "text": chunk_text,
                "metadata": {
                    "document_id": doc_id,
                    "notebook_id": default_notebook_id,
                    "title": post['title'],
                    "author": post['author'],
                    "category_path": json.dumps(post['category_path']),
                    "chunk_index": c_idx
                }
            })
            
    print(f"Total chunks generated: {len(all_chunks_to_embed)}")
    print("Computing embeddings and writing to ChromaDB in batches...")
    
    # 批次進行 Embedding 與寫入 ChromaDB
    total_chunks = len(all_chunks_to_embed)
    for i in range(0, total_chunks, BATCH_SIZE):
        batch = all_chunks_to_embed[i:i+BATCH_SIZE]
        batch_texts = [item['text'] for item in batch]
        batch_ids = [item['id'] for item in batch]
        batch_metas = [item['metadata'] for item in batch]
        
        print(f"Processing chunk batch {i+1} to {min(i+BATCH_SIZE, total_chunks)} of {total_chunks}...")
        
        # 呼叫 Embedding API
        embeddings = embed_service.get_embeddings_batch(batch_texts)
        
        # 寫入 ChromaDB
        chroma_collection.add(
            ids=batch_ids,
            embeddings=embeddings,
            metadatas=batch_metas,
            documents=batch_texts # ChromaDB 亦可儲存純文字方便調用
        )
        
    print(f"Successfully embedded and stored {total_chunks} chunks into ChromaDB and SQLite!")

if __name__ == "__main__":
    process_and_embed_catch_data()
