import trafilatura, httpx, asyncio
from sqlalchemy import select
from .db import SessionLocal
from .models import News

async def fetch_and_extract(session, url):
    try:
        resp = await session.get(url, timeout=20)
        resp.raise_for_status()
        return trafilatura.extract(resp.text, include_comments=False, include_tables=False)
    except Exception:
        return None

async def extract_missing_text():
    cnt = 0
    async with httpx.AsyncClient() as client:
        with SessionLocal() as s:
            q = s.execute(select(News).where(News.content_text.is_(None))).scalars().all()
            for n in q:
                content = await fetch_and_extract(client, n.url)
                if content and len(content) > 200:
                    n.content_text = content
                    s.add(n); cnt += 1
            s.commit()
    return cnt

if __name__ == "__main__":
    asyncio.run(extract_missing_text())
