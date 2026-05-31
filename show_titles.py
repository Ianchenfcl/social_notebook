import json
import os
import sys

def safe_print(text):
    try:
        encoding = sys.stdout.encoding or 'utf-8'
        print(text.encode(encoding, errors='replace').decode(encoding))
    except Exception:
        try:
            print(text.encode('ascii', errors='replace').decode('ascii'))
        except Exception:
            pass

def show():
    path = "d:/sideproject/catchbot/catch_posts.json"
    if not os.path.exists(path):
        print("catch_posts.json does not exist yet.")
        return
        
    try:
        with open(path, 'r', encoding='utf-8') as f:
            posts = json.load(f)
        safe_print(f"==================================================")
        safe_print(f"當前已抓取之爆款經典總數: {len(posts)}")
        safe_print(f"==================================================")
        for i, p in enumerate(posts):
            cats = " > ".join(p['category_path']) if p['category_path'] else "Root"
            safe_print(f"{i+1:2d} | [{cats}] {p['title']} (作者: {p['author']}) - 字數: {len(p['content'])}")
        safe_print(f"==================================================")
    except Exception as e:
        safe_print(f"Error reading json: {str(e)}")

if __name__ == "__main__":
    show()
