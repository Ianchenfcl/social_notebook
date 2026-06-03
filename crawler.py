import os
import json
import time
import subprocess
import re
import sys
from bs4 import BeautifulSoup

BASE_URL = "https://www.ptt.cc"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_FILE = os.path.join(BASE_DIR, "catch_posts.json")

def safe_print(text):
    """強健的控制台輸出函數，100% 根除 Windows CP950/Big5 編碼崩潰問題"""
    try:
        encoding = sys.stdout.encoding or 'utf-8'
        print(text.encode(encoding, errors='replace').decode(encoding))
    except Exception:
        try:
            print(text.encode('ascii', errors='replace').decode('ascii'))
        except Exception:
            pass

def fetch_html_with_curl(url):
    cmd = [
        "curl.exe",
        "-s",
        "-A", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "-b", "over18=1",
        "--ssl-no-revoke",  # 解決 Windows 下 SSL 握手 code 35 錯誤
        url
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="ignore")
        if result.returncode == 0:
            return result.stdout
        else:
            safe_print(f"Error fetching URL: {url}, code {result.returncode}")
            return None
    except Exception as e:
        safe_print(f"Exception fetching URL: {url}, error: {str(e)}")
        return None

def clean_title(title_text):
    if not title_text:
        return ""
    # 清理 ANSI 框線與 PTT 常見特殊符號，完全防範編碼錯誤
    chars_to_remove = ["◆", "◇", "■", "□", "▲", "▼", "★", "☆", "│", "├", "┤", "┌", "┐", "└", "┘", "─", "┬", "┴", "┼", "═", "║", "╔", "╗", "╚", "╝", "◄", "►", "┐"]
    cleaned = title_text
    for char in chars_to_remove:
        cleaned = cleaned.replace(char, "")
    cleaned = " ".join(cleaned.split())
    return cleaned.strip()

def parse_post(html, url, category_path):
    soup = BeautifulSoup(html, 'html.parser')
    main_content = soup.find('div', id='main-content')
    if not main_content:
        return None
    
    author = "未知"
    title = ""
    date_str = "未知時間"
    
    meta_lines = main_content.find_all('div', class_='article-metaline')
    for line in meta_lines:
        tag = line.find('span', class_='article-meta-tag')
        val = line.find('span', class_='article-meta-value')
        if tag and val:
            tag_text = tag.text.strip()
            val_text = val.text.strip()
            if tag_text == "作者":
                author = val_text
            elif tag_text == "標題":
                title = val_text
            elif tag_text == "時間":
                date_str = val_text
    
    if not title:
        title_tag = soup.find('title')
        title = title_tag.text.replace(" - 看板 CATCH - 批踢踢實業坊", "").strip() if title_tag else "無標題"
    
    content_copy = BeautifulSoup(str(main_content), 'html.parser')
    
    # 移除 meta header
    for el in content_copy.find_all('div', class_='article-metaline'):
        el.decompose()
    for el in content_copy.find_all('div', class_='article-metaline-right'):
        el.decompose()
    
    # 刪除推文區
    for el in content_copy.find_all('div', class_='push'):
        el.decompose()
    
    text_content = content_copy.get_text()
    
    # 移除簽名檔
    signature_index = text_content.rfind('\n--\n')
    if signature_index != -1:
        text_content = text_content[:signature_index]
        
    return {
        "title": clean_title(title),
        "author": author,
        "date": date_str,
        "content": text_content.strip(),
        "url": url,
        "category_path": category_path
    }

class PTTCatchPopularCrawler:
    def __init__(self, delay=0.8):
        self.delay = delay
        self.posts_crawled = []
        self.visited_urls = set()

    def get_all_popular_links(self):
        """遍歷 PTT CATCH 搜尋 recommend:99 的所有分頁，收集爆款文章連結"""
        safe_print("[*] Starting to fetch PTT CATCH recommend:99 post list...")
        page = 1
        all_post_links = []
        
        while True:
            url = f"https://www.ptt.cc/bbs/CATCH/search?page={page}&q=recommend%3A99"
            safe_print(f" -> Scanning search results page {page}...")
            time.sleep(self.delay)
            
            html = fetch_html_with_curl(url)
            if not html:
                break
                
            soup = BeautifulSoup(html, 'html.parser')
            m_ents = soup.find_all('div', class_='r-ent')
            
            if not m_ents:
                safe_print(" -> Scanning completed. No more popular posts pages.")
                break
                
            found_count = 0
            for ent in m_ents:
                title_div = ent.find('div', class_='title')
                if title_div and title_div.find('a'):
                    a_tag = title_div.find('a')
                    title_text = clean_title(a_tag.text)
                    href = a_tag['href']
                    full_url = BASE_URL + href
                    
                    # 篩選掉純公告、水桶、板主判決等垃圾文章
                    trash_keywords = ["公告", "水桶", "檢舉", "板規", "版規", "SYSOP", "申訴", "判決", "版主", "板主"]
                    if any(kw in title_text for kw in trash_keywords):
                        continue
                        
                    all_post_links.append({
                        "title": title_text,
                        "url": full_url
                    })
                    found_count += 1
            
            safe_print(f"    Page {page}: Selected {found_count} classic dry-goods.")
            page += 1
            
        safe_print(f"[OK] Link collection completed! Selected {len(all_post_links)} legendary posts!")
        return all_post_links

    def start(self):
        safe_print("=========================================================")
        safe_print("  PTT Catch Popular dry-goods Crawler")
        print("=========================================================")
        
        # 1. 收集連結
        post_links = self.get_all_popular_links()
        
        # 2. 爬取每篇文章的內文
        total_to_crawl = len(post_links)
        safe_print(f"\n[*] Starting to download and parse these {total_to_crawl} classic posts...")
        
        for idx, item in enumerate(post_links):
            p_url = item['url']
            if p_url in self.visited_urls:
                continue
            self.visited_urls.add(p_url)
            
            safe_print(f" [{idx+1}/{total_to_crawl}] Fetching: {item['title']}...")
            time.sleep(self.delay)
            
            p_html = fetch_html_with_curl(p_url)
            if p_html:
                post_data = parse_post(p_html, p_url, ["板友爆推神作"])
                
                # 再次字數過濾與板規過濾，確保萬無一失
                if post_data and len(post_data['content']) >= 300:
                    if "本板板規" in post_data['content']:
                        safe_print(" -> Content is rules, skipping.")
                        continue
                    self.posts_crawled.append(post_data)
                    # 每次成功爬取，存檔一次
                    self.save_progress()
                else:
                    reason = "too short" if post_data else "parse error"
                    safe_print(f" -> Skipping ({reason})")
                    
        safe_print(f"\n[OK] Classic posts fetch completed! Total collected {len(self.posts_crawled)} posts!")
        self.save_progress()

    def save_progress(self):
        os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
        with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
            json.dump(self.posts_crawled, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    crawler = PTTCatchPopularCrawler(delay=0.8)
    crawler.start()
