import subprocess
import urllib.parse
from bs4 import BeautifulSoup

def fetch_html_with_curl(url):
    cmd = [
        "curl.exe",
        "-s",
        "-A", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "-b", "over18=1",
        url
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="ignore")
        if result.returncode == 0:
            return result.stdout
        else:
            print(f"Error fetching URL: {url}, code {result.returncode}")
            return None
    except Exception as e:
        print(f"Exception fetching URL: {url}, error: {str(e)}")
        return None

def test():
    url = "https://www.ptt.cc/man/CATCH/index.html"
    html = fetch_html_with_curl(url)
    if html:
        print("Successfully fetched HTML with curl.exe!")
        soup = BeautifulSoup(html, 'html.parser')
        print("Page Title:", soup.title.text if soup.title else "No Title")
        
        # 找尋精華區文章或子目錄
        # PTT 精華區的 HTML 結構與看板列表類似
        # 目錄和文章會在 class="m-ent" 的 div 中
        m_ents = soup.find_all('div', class_='m-ent')
        print(f"Found {len(m_ents)} entries.")
        for ent in m_ents[:10]:
            title_div = ent.find('div', class_='title')
            if title_div and title_div.find('a'):
                a_tag = title_div.find('a')
                print(f"Title: {a_tag.text.strip()} | Link: {a_tag['href']}")
    else:
        print("Failed to fetch HTML.")

if __name__ == "__main__":
    test()
