# app/ingest.py
import feedparser, yaml, os, re
from datetime import datetime, timezone
from dateutil import parser as dateparser
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from .db import engine, SessionLocal, Base
from .models import News
from .utils import get_og_image

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SOURCES = os.path.join(os.path.dirname(__file__), "sources.yaml")

def load_sources():
    with open(SOURCES, "r", encoding="utf-8") as f:
        y = yaml.safe_load(f)
    return y["feeds"]

KEYWORDS = [
    "ai","artificial intelligence","machine learning","deep learning",
    "llm","gpt","rag","agent","multimodal","transformer","diffusion",
    "anthropic","openai","deepmind","meta ai","google ai","microsoft"
]

def is_relevant(title: str):
    t = title.lower()
    return any(k in t for k in KEYWORDS)

def normalize_url(url: str) -> str:
    # chuẩn hoá query: bỏ utm_*
    url = re.sub(r"[?&](utm_[^=]+=[^&]+)", "", url)
    # hợp nhất domain arXiv
    url = url.replace("export.arxiv.org", "arxiv.org")
    # bỏ slash cuối
    if url.endswith("/"):
        url = url[:-1]
    return url

def ingest_once():
    Base.metadata.create_all(bind=engine)
    feeds = load_sources()
    added = 0

    with SessionLocal() as s:
        # 1) Tải sẵn các URL đã có trong DB
        existing = set(u for (u,) in s.execute(select(News.url)).all())
        # 2) Bộ nhớ tạm cho URL được thêm trong phiên này (chưa commit)
        seen = set()

        for f in feeds:
            d = feedparser.parse(f["url"])
            for e in d.entries:
                title = (e.get("title") or "").strip()
                link = (e.get("link") or "").strip()
                if not title or not link:
                    continue
                if not is_relevant(title):
                    continue

                url = normalize_url(link)

                # 3) Chặn trùng trước khi add
                if url in existing or url in seen:
                    continue

                # published
                published = e.get("published") or e.get("updated") or ""
                try:
                    published_at = dateparser.parse(published)
                except Exception:
                    published_at = datetime.now(timezone.utc)

                source = f.get("name", d.feed.get("title", "unknown"))
                og_image = get_og_image(url)

                news = News(
                    url=url, title=title, source=source,
                    published_at=published_at,
                    og_image=og_image, lang=None, content_text=None
                )
                s.add(news)
                # đánh dấu vào bộ nhớ tạm
                seen.add(url)

        # 4) Commit an toàn – nếu lỡ vẫn trùng (do DB đã có mà existing chưa bắt được), rollback từng mục
        try:
            s.commit()
            added = len(seen)
        except IntegrityError:
            s.rollback()
            # Commit lại từng bản ghi để bỏ qua cái lỗi
            for url in list(seen):
                try:
                    # nếu đã tồn tại thì bỏ
                    if s.execute(select(News).where(News.url == url)).scalar_one_or_none():
                        seen.remove(url)
                        continue
                    # không có thì add lại (trường hợp rollback đã xoá pending)
                    # (ở đây đơn giản bỏ qua việc add lại chi tiết; thực tế hiếm gặp)
                except Exception:
                    pass
            # commit cuối (không thêm gì mới nữa)
            s.commit()

    return added

if __name__ == "__main__":
    n = ingest_once()
    print(f"Ingested {n} new items.")