import sys
import json
import database
import embedder

def search_catch_knowledge(query_text, top_k=3):
    """根據使用者的查詢，進行語意檢索"""
    embed_service = embedder.EmbeddingService()
    
    print(f"\nComputing query embedding for: '{query_text}'...")
    query_vector = embed_service.get_embedding(query_text, is_query=True)
    
    print("Searching in ChromaDB...")
    collection = database.get_chroma_collection()
    
    # 執行向量檢索
    results = collection.query(
        query_embeddings=[query_vector],
        n_results=top_k
    )
    
    if not results or not results['ids'] or len(results['ids'][0]) == 0:
        print("No matching results found.")
        return
    
    ids = results['ids'][0]
    distances = results['distances'][0]
    metadatas = results['metadatas'][0]
    documents = results['documents'][0]
    
    print(f"\nFound {len(ids)} highly relevant chunks:\n")
    
    # 連接 SQLite 取得結構化資訊
    conn = database.get_db_connection()
    cursor = conn.cursor()
    
    for i in range(len(ids)):
        chunk_id = ids[i]
        distance = distances[i]
        meta = metadatas[i]
        text = documents[i]
        
        # 相似度 (餘弦距離越小越相似，如果是 cosine 距離，similarity = 1 - distance)
        similarity = 1.0 - distance
        
        doc_id = meta.get('document_id')
        
        # 從 SQLite 中取得該文件的完整資訊與目錄路徑
        cursor.execute("SELECT title, author, publish_date, source_url, category_path FROM documents WHERE id = ?", (doc_id,))
        doc_info = cursor.fetchone()
        
        title = doc_info['title'] if doc_info else meta.get('title', 'Unknown Title')
        author = doc_info['author'] if doc_info else meta.get('author', 'Unknown Author')
        category_json = doc_info['category_path'] if doc_info else meta.get('category_path', '[]')
        category_path = json.loads(category_json) if isinstance(category_json, str) else category_json
        source_url = doc_info['source_url'] if doc_info else "#"
        
        print(f"==================================================")
        print(f"Rank {i+1} | 相似度: {similarity:.4f}")
        print(f"標題: {title}")
        print(f"作者: {author}")
        print(f"路徑: {' > '.join(category_path) if category_path else 'Root'}")
        print(f"網址: {source_url}")
        print(f"Chunk ID: {chunk_id}")
        print(f"--------------------------------------------------")
        print(f"內容片段:\n{text.strip()}")
        print(f"==================================================\n")
        
    conn.close()

if __name__ == "__main__":
    if len(sys.argv) > 1:
        query = " ".join(sys.argv[1:])
        search_catch_knowledge(query)
    else:
        print("戀愛AI Semantic Search CLI Test Tool")
        print("Usage: python search.py <your query>")
        print("Example: python search.py 怎麼跟不熟的女生聊天")
        
        # 互動模式
        while True:
            try:
                query = input("\n請輸入搜尋問題 (輸入 'q' 離開): ").strip()
                if not query:
                    continue
                if query.lower() == 'q':
                    break
                search_catch_knowledge(query)
            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"An error occurred: {str(e)}")
