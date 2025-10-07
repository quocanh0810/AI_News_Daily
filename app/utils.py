import httpx, re
from bs4 import BeautifulSoup

def get_og_image(url: str):
    try:
        r = httpx.get(url, timeout=15)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html5lib")
        tag = soup.find("meta", property="og:image")
        if tag and tag.get("content"):
            return tag["content"]
        return None
    except Exception:
        return None
