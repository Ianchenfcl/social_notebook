import requests
from bs4 import BeautifulSoup
import time

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Cookie': 'over18=1'
}

def test_crawl():
    url = "https://www.ptt.cc/man/CATCH/index.html"
    try:
        response = requests.get(url, headers=headers, timeout=10)
        print(f"Status Code: {response.status_code}")
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            print("Successfully retrieved page!")
            print("Title:", soup.title.text if soup.title else "No Title")
            
            # Find links
            links = soup.find_all('a')
            print(f"Found {len(links)} links on the root page.")
            
            # Print a few examples of links
            m_divs = soup.find_all('div', class_='m-ent')
            print(f"Found {len(m_divs)} entry divs.")
            for i, ent in enumerate(m_divs[:10]):
                title_link = ent.find('div', class_='title').find('a') if ent.find('div', class_='title') else None
                if title_link:
                    print(f"{i+1}: [{title_link.text}] -> {title_link['href']}")
                else:
                    print(f"{i+1}: No title link in entry div")
        else:
            print("Failed to retrieve page, HTML response preview:")
            print(response.text[:500])
    except Exception as e:
        print("An error occurred:", str(e))

if __name__ == "__main__":
    test_crawl()
