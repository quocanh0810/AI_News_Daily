import math
from datetime import datetime, timezone
from sqlalchemy import select
from .db import SessionLocal
from .models import News

SOURCE_WEIGHT = {
    "OpenAI Blog": 1.0,
    "Google AI Blog": 1.0,
    "DeepMind": 1.0,
    "Anthropic": 0.95,
    "Meta AI": 0.9,
    "Microsoft Research": 0.9,
    "MIT News - AI": 0.85,
    "Stanford HAI": 0.85,
    "IEEE Spectrum AI": 0.8,
    "TechCrunch AI": 0.75,
    "VentureBeat AI": 0.7,
    "Wired AI": 0.7
}

def freshness_score(published_at, tau_hours=24):
    # Nếu thời điểm bài viết không có tz -> gắn UTC
    if published_at is None:
        published_at = datetime.now(timezone.utc)
    elif published_at.tzinfo is None:
        published_at = published_at.replace(tzinfo=timezone.utc)

    now = datetime.now(timezone.utc)
    dt = (now - published_at).total_seconds() / 3600.0
    return math.exp(-dt / max(1.0, tau_hours))

def rank_recent(limit=50):
    with SessionLocal() as s:
        rows = s.execute(select(News).order_by(News.published_at.desc()).limit(limit)).scalars().all()
        ranked = []
        for r in rows:
            f = freshness_score(r.published_at or datetime.now(timezone.utc))
            sw = SOURCE_WEIGHT.get(r.source, 0.6)
            # simple base score; could add social signals
            score = 0.6*f + 0.4*sw
            ranked.append((score, r))
        ranked.sort(key=lambda x: x[0], reverse=True)
        return ranked
