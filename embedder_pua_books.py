import os
import sys
import json
import uuid
import zipfile
import urllib.parse
from bs4 import BeautifulSoup
from pypdf import PdfReader
from langchain_text_splitters import RecursiveCharacterTextSplitter

# 載入本地模組
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import database
from embedder import EmbeddingService
import zhconv

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_DIR = os.path.join(BASE_DIR, "pua_books_repo")
NOTEBOOK_ID = "pua-books-notebook-uuid"

# 篩選最頂級的 15 本情感與把妹經典書籍，控制庫大小並提供最優質內容
TARGET_BOOKS = [
    "谜男方法 - 谜男.pdf",
    "把妹达人 - 尼尔.pdf",
    "把妹达人圣经 - 尼尔.epub",
    "谜男启示录 - 谜男.pdf",
    "冷读术 - 石井裕之.pdf",
    "迷上我 - 成真.txt",
    "魔鬼搭讪学 - 魔鬼咨询师.epub",
    "魔鬼约会学 - 魔鬼咨询师.epub",
    "坏蛋之道 - 约书亚·佩雷斯.pdf",
    "如何和女人见面与沟通 - 杂耍人.pdf",
    "搭讪圣经 - 郑匡宇.epub",
    "约会倍增术 - 大卫D.pdf",
    "正妹心理学 - 郑匡宇.pdf",
    "吸引力原理 - Adam Lyons.epub",
    "五步陷阱 - 死囚漫步.epub"
]

BILINGUAL_TITLES = {
    "謎男方法": "謎男方法 (The Mystery Method)",
    "把妹達人": "把妹達人 (The Game)",
    "把妹達人聖經": "把妹達人聖經 (Rules of the Game)",
    "謎男啟示錄": "謎男啟示錄 (Revelation)",
    "冷讀術": "冷讀術 (Cold Reading)",
    "迷上我": "迷上我 (Attract Her)",
    "魔鬼搭訕學": "魔鬼搭訕學 (Devil's Guide to Flirting)",
    "魔鬼約會學": "魔鬼約會學 (Devil's Guide to Dating)",
    "壞蛋之道": "壞蛋之道 (The Way of the Bad Boy)",
    "如何和女人見面與溝通": "如何和女人見面與溝通 (How to Meet and Connect with Women)",
    "搭訕聖經": "搭訕聖經 (Flirting Bible)",
    "約會倍增術": "約會倍增術 (Double Your Dating)",
    "正妹心理學": "正妹心理學 (Beautiful Girls Psychology)",
    "吸引力原理": "吸引力原理 (The Principles of Attraction)",
    "五步陷阱": "五步陷阱 (Five-Step Trap)"
}

def safe_print(text):
    try:
        encoding = sys.stdout.encoding or 'utf-8'
        print(text.encode(encoding, errors='replace').decode(encoding))
    except Exception:
        try:
            print(text.encode('ascii', errors='replace').decode('ascii'))
        except Exception:
            pass

def extract_txt_content(filepath):
    """讀取 TXT 檔案，支援多重編碼 fallback"""
    encodings = ['utf-8', 'gb18030', 'big5', 'utf-16', 'latin-1']
    for enc in encodings:
        try:
            with open(filepath, 'r', encoding=enc) as f:
                content = f.read()
                if content.strip():
                    return content
        except UnicodeDecodeError:
            continue
    raise ValueError(f"無法解碼 TXT 檔案: {filepath}")

def extract_pdf_content(filepath):
    """使用 pypdf 逐頁提取 PDF 內容"""
    reader = PdfReader(filepath)
    text_parts = []
    for idx, page in enumerate(reader.pages):
        val = page.extract_text()
        if val:
            text_parts.append(val)
    return "\n\n".join(text_parts)

def extract_epub_content(filepath):
    """解析 EPUB ZIP 封包，提取 HTML/XHTML 純文字內容"""
    text_parts = []
    with zipfile.ZipFile(filepath, 'r') as epub:
        for name in epub.namelist():
            if name.endswith(('.html', '.xhtml', '.xml', '.htm')):
                try:
                    html_content = epub.read(name)
                    # 嘗試解碼
                    try:
                        decoded = html_content.decode('utf-8')
                    except UnicodeDecodeError:
                        decoded = html_content.decode('gb18030', errors='replace')
                    
                    soup = BeautifulSoup(decoded, 'html.parser')
                    text = soup.get_text()
                    if text.strip():
                        text_parts.append(text)
                except Exception as e:
                    safe_print(f"  [!] 警告: 讀取 EPUB 內之 {name} 失敗: {str(e)}")
    return "\n\n".join(text_parts)

def process_and_embed_pua_books():
    if not os.path.exists(REPO_DIR):
        safe_print(f"錯誤: 找不到書籍目錄 '{REPO_DIR}'！請確認是否克隆成功。")
        return

    # 1. 初始化資料庫並清空該筆記本的舊資料
    database.init_db()
    database.clear_db(NOTEBOOK_ID)
    
    # 2. 準備文本切分器
    # 書籍篇幅較大，我們將 block 設定為 800 字，重疊 150 字，以保持上下文完整度
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=800,
        chunk_overlap=150,
        length_function=len,
        separators=["\n\n", "\n", "。", "！", "？", "；", " ", ""]
    )

    embed_service = EmbeddingService()
    chroma_collection = database.get_chroma_collection()
    
    all_chunks_to_embed = []
    
    # 3. 掃描並解析目標書籍
    safe_print("--------------------------------------------------")
    safe_print("開始提取情感與把妹經典書籍內容...")
    safe_print("--------------------------------------------------")
    
    for book_name in TARGET_BOOKS:
        filepath = os.path.join(REPO_DIR, book_name)
        if not os.path.exists(filepath):
            safe_print(f"[!] 找不到書籍: {book_name}，跳過。")
            continue
            
        safe_print(f"[*] 正在解析: {book_name} ...")
        
        # 解析標題與作者
        name_without_ext, ext = os.path.splitext(book_name)
        if " - " in name_without_ext:
            parts = name_without_ext.split(" - ")
            title = parts[0].strip()
            author = parts[1].strip()
        else:
            title = name_without_ext
            author = "精華經典"
            
        # 依據副檔名提取文字
        try:
            if ext.lower() == '.txt':
                content = extract_txt_content(filepath)
            elif ext.lower() == '.pdf':
                content = extract_pdf_content(filepath)
            elif ext.lower() == '.epub':
                content = extract_epub_content(filepath)
            else:
                continue
                
            # 將提取之標題、作者與內容統一轉換為繁體中文，消除簡體干擾，符合用戶閱讀體驗
            title = zhconv.convert(title, 'zh-hant')
            # 轉換為中英雙語書名
            title = BILINGUAL_TITLES.get(title, title)
            author = zhconv.convert(author, 'zh-hant')
            content = zhconv.convert(content, 'zh-hant')
                
            char_count = len(content)
            if char_count < 100:
                safe_print(f"  [!] 提取文字過少 ({char_count} 字)，跳過此書。")
                continue
                
            safe_print(f"  [✔] 成功提取並轉換為繁體中文，共 {char_count} 字")
        except Exception as e:
            safe_print(f"  [❌] 提取失敗 ({book_name}): {str(e)}")
            continue

        # 生成穩定的文件 UUID
        doc_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, book_name))
        
        # PUA 書籍不提供超連結導流，設定為 '#' 避免跳轉
        github_url = "#"
        
        # 儲存文件到 SQLite
        database.save_document(
            doc_id=doc_id,
            notebook_id=NOTEBOOK_ID,
            title=title,
            author=author,
            publish_date="經典文獻",
            source_url=github_url,
            category_path=["經典情感書籍", author],
            raw_content=content
        )
        
        # 切分文本
        chunks = text_splitter.split_text(content)
        safe_print(f"  [+] 已切分為 {len(chunks)} 個語意區塊 (Chunks)")
        
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
                "text": chunk_text,
                "metadata": {
                    "document_id": doc_id,
                    "notebook_id": NOTEBOOK_ID,
                    "title": title,
                    "author": author,
                    "category_path": json.dumps(["經典情感書籍", author]),
                    "chunk_index": c_idx
                }
            })
            
    total_chunks = len(all_chunks_to_embed)
    safe_print("--------------------------------------------------")
    safe_print(f"解析完成！待計算向量 Chunks 總計: {total_chunks}")
    safe_print("開始批次計算 Embedding 並寫入 ChromaDB...")
    safe_print("--------------------------------------------------")
    
    # 4. 批次計算向量與寫入向量資料庫
    BATCH_SIZE = 15
    for i in range(0, total_chunks, BATCH_SIZE):
        batch = all_chunks_to_embed[i:i+BATCH_SIZE]
        batch_texts = [item['text'] for item in batch]
        batch_ids = [item['id'] for item in batch]
        batch_metas = [item['metadata'] for item in batch]
        
        safe_print(f"[*] 正在處理區塊批次 {i+1} 至 {min(i+BATCH_SIZE, total_chunks)} / {total_chunks} ...")
        
        # 呼叫 Embedding API
        embeddings = embed_service.get_embeddings_batch(batch_texts)
        
        # 寫入 ChromaDB
        chroma_collection.add(
            ids=batch_ids,
            embeddings=embeddings,
            metadatas=batch_metas,
            documents=batch_texts
        )
        
    safe_print("--------------------------------------------------")
    safe_print("🎉 恭喜！把妹與情感經典書籍資料庫成功載入並完成向量化！")
    safe_print("--------------------------------------------------")

if __name__ == "__main__":
    process_and_embed_pua_books()
