# AI News MVP (RSS → Rank → VN Summary → Dashboard)

Tech Stack Overview:

Frontend: TailwindCSS, Vanilla JS
Backend: FastAPI, SQLAlchemy, SQLite
AI/NLP: OpenAI GPT / Google Gemini
Infrastructure: Local SQLite DB + Cron job
Automation: Bash script
Data Sources: RSS feeds

A minimal pipeline to:
1) Fetch AI news from curated RSS feeds
2) Extract article text
3) De-duplicate & score “hotness”
4) Summarize & Việt hoá 5–10 bài hot mỗi ngày
5) Serve a small dashboard/API via FastAPI

## 0) Requiments
- Python 3.10+
- `pip install -r requirements.txt`
- Sao chép `.env.example` → `.env` và đặt API key (OpenAI hoặc model khác).

## 1) Run
```bash
python -m app.pipeline  # chạy toàn bộ pipeline (ingest → extract → rank → summarize → picks)
uvicorn app.api:app --reload --port 8000  # mở dashboard/API
# Mở http://localhost:8000 để xem web, http://localhost:8000/api/picks/today để xem JSON
```

## 2) Cron (7:30 am daily)
Trong Linux/macOS:
```bash
crontab -e
30 7 * * * /usr/bin/bash {project}/scripts/run_daily.sh
```
`scripts/run_daily.sh`, -- đường dẫn project
