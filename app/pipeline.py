from sqlalchemy import select
from datetime import datetime
from dateutil import tz
import json, time

from .db import engine, SessionLocal, Base
from .models import News, Summary, Picks
from .config import DAILY_TOP_K, TIMEZONE
from .ingest import ingest_once
from .extract import extract_missing_text
from .dedupe import dedupe_titles
from .ranker import rank_recent
from .summarizer import summarize_article

def today_str():
    tzinfo = tz.gettz(TIMEZONE)
    return datetime.now(tz=tzinfo).strftime("%Y-%m-%d")

def run_pipeline():
    Base.metadata.create_all(bind=engine)

    # 📰 1. Crawl dữ liệu gốc
    n_new = ingest_once()

    # 🧠 2. Extract nội dung (nếu có async)
    n_ext = 0
    try:
        n_ext = __import__("asyncio").run(
            __import__("app.extract", fromlist=["extract_missing_text"]).extract_missing_text()
        )
    except Exception:
        pass

    # 🧩 3. Loại trùng tiêu đề
    n_dup = dedupe_titles()

    # 🧮 4. Xếp hạng các bài gần đây
    ranked = rank_recent(limit=120)

    # ⚙️ 5. Lọc bài có nội dung (text dài > 200 ký tự)
    ranked_with_text = [r for _, r in ranked if r.content_text and len(r.content_text) > 200]

    # ✅ 6. Giới hạn chỉ lấy 50 bài đầu tiên để tóm tắt
    limited = ranked_with_text[:50]

    # 🔝 7. Sau đó chỉ chọn top DAILY_TOP_K (mặc định = 10)
    top = limited[:DAILY_TOP_K]

    with SessionLocal() as s:
        picks_date = today_str()
        # Xoá pick cũ trong DB
        s.execute(__import__("sqlalchemy").text("DELETE FROM picks WHERE date_str = :d"), {"d": picks_date})
        s.commit()

        created = 0
        for idx, news in enumerate(top, start=1):
            print(f"[{idx}/{len(top)}] 🧾 Summarizing: {news.title[:80]} ...")

            # 🪶 8. Tóm tắt bằng GPT hoặc offline fallback
            summ = summarize_article(news.url, news.title, news.source, news.content_text)

            # 🕒 Thêm delay để tránh rate limit (nếu có key GPT)
            time.sleep(2)

            # 💾 Lưu vào DB
            summary = Summary(
                news_id=news.id,
                title_vi=summ.get("title_vi", news.title)[:250],
                bullets_json=json.dumps(summ.get("bullets", []), ensure_ascii=False),
                so_what_vn=summ.get("so_what_vn", ""),
                hashtags=",".join(summ.get("hashtags", []))[:120],
                attribution=summ.get("attribution", news.source),
                url=summ.get("url", news.url),
            )
            s.add(summary)
            s.flush()

            s.add(Picks(date_str=picks_date, rank=idx, news_id=news.id, summary_id=summary.id))
            created += 1

        s.commit()

    print(f"✅ Pipeline done: {created} picks saved.")
    return {"new_items": n_new, "extracted": n_ext, "deduped": n_dup, "picks": created}

if __name__ == "__main__":
    res = run_pipeline()
    print(res)