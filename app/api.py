from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse
from sqlalchemy import select
import json
from .db import SessionLocal
from .models import News, Summary, Picks
from .pipeline import today_str

app = FastAPI(title="AI News MVP")

HTML_PAGE = """
<!doctype html>
<html lang="vi">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>AI News – Gợi ý bài đăng hôm nay</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <script>
    tailwind.config = { theme: { extend: { colors: { brand: { DEFAULT: '#2563EB' }}}}};
  </script>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
  <style>
    body { font-family: Inter, system-ui, sans-serif; }
    .card { box-shadow: 0 1px 3px rgba(0,0,0,.08); transition: all .2s; }
    .card:hover { transform: translateY(-3px); box-shadow: 0 8px 20px rgba(0,0,0,.1); }
  </style>
</head>
<body class="bg-slate-50 text-slate-900">

  <div class="max-w-6xl mx-auto p-6">
    <h1 class="text-4xl font-extrabold mb-2">🔥 Gợi ý bài đăng hôm nay</h1>
    <p class="text-slate-600 mb-8">10 bài AI hot nhất hôm nay – có sẵn caption & hashtag để copy đăng Facebook.</p>

    <div id="list" class="grid sm:grid-cols-2 lg:grid-cols-3 gap-6"></div>
  </div>

  <!-- Template card không có ảnh và không có "So what" -->
  <template id="cardTpl">
    <div class="bg-white rounded-2xl overflow-hidden border border-slate-200 card flex flex-col">
      <div class="p-5 flex flex-col flex-grow">
        <div class="text-xs text-slate-500 mb-1 meta"></div>
        <h2 class="font-semibold text-lg mb-2 title"></h2>
        <ul class="list-disc list-inside text-sm text-slate-700 mb-3 bullets"></ul>
        <div class="text-xs text-slate-500 mb-3 hashtags"></div>
        <div class="mt-auto flex flex-wrap gap-2">
          <button class="copyCap px-3 py-2 rounded-xl bg-slate-900 text-white hover:bg-slate-800">Copy caption</button>
          <button class="copyHash px-3 py-2 rounded-xl border border-slate-200 bg-white hover:bg-slate-100">Copy hashtag</button>
          <a class="openLink px-3 py-2 rounded-xl border border-slate-200 bg-white hover:bg-slate-100" target="_blank">Nguồn</a>
        </div>
      </div>
    </div>
  </template>

  <script>
    const list = document.getElementById('list');
    const cardTpl = document.getElementById('cardTpl');

    // Hàm copy text với alert
    async function copy(text) {
      try {
        await navigator.clipboard.writeText(text);
        alert('✅ Đã copy!');
      } catch (e) {
        console.error('Copy lỗi:', e);
      }
    }

    // Hàm build caption
    function buildCaption(it) {
      const bullets = (it.bullets || []).map(b => `- ${b}`).join('\\n');
      return `${it.title_vi}\\n${bullets}\\nNguồn: ${it.source} — ${it.url}`;
    }

    async function load() {
      list.innerHTML = '<div class="text-center text-slate-500 py-10 col-span-full">Đang tải dữ liệu...</div>';
      try {
        const res = await fetch('/api/picks/today', { cache: 'no-store' });
        const data = await res.json();
        const posts = data.top_posts || [];
        list.innerHTML = '';

        if (posts.length === 0) {
          list.innerHTML = '<div class="text-center text-slate-500 py-10 col-span-full">Chưa có dữ liệu hôm nay. Hãy chạy pipeline hoặc thử làm mới.</div>';
          return;
        }

        posts.forEach(it => {
          try {
            const node = cardTpl.content.cloneNode(true);
            const meta = node.querySelector('.meta');
            const title = node.querySelector('.title');
            const ul = node.querySelector('.bullets');
            const hash = node.querySelector('.hashtags');
            const capBtn = node.querySelector('.copyCap');
            const hBtn = node.querySelector('.copyHash');
            const openBtn = node.querySelector('.openLink');

            meta.textContent = `${it.source} • #${it.rank}`;
            title.textContent = it.title_vi || '(Không có tiêu đề)';
            ul.innerHTML = (it.bullets || []).map(b => `<li>${b}</li>`).join('');
            hash.textContent = (it.hashtags || []).join(' ');
            if (openBtn) openBtn.href = it.url;

            capBtn.onclick = () => copy(buildCaption(it));
            hBtn.onclick = () => copy((it.hashtags || []).join(' '));

            list.appendChild(node);
          } catch (itemErr) {
            console.error('Lỗi khi render item:', itemErr, it);
          }
        });
      } catch (err) {
        console.error('Lỗi tải dữ liệu:', err);
        list.innerHTML = `<div class="text-center text-red-600 py-10 col-span-full">Không thể tải dữ liệu: ${err}</div>`;
      }
    }

    console.log('🟢 Script loaded');
    load();
  </script>
</body>
</html>
"""

@app.get("/", response_class=HTMLResponse)
def home():
    return HTML_PAGE


@app.get("/api/picks/today", response_class=JSONResponse)
def api_picks_today():
    d = today_str()
    with SessionLocal() as s:
        rows = s.execute(
            select(Picks, Summary, News)
            .join(Summary, Summary.id == Picks.summary_id)
            .join(News, News.id == Picks.news_id)
            .where(Picks.date_str == d)
            .order_by(Picks.rank.asc())
        ).all()

        out = []
        for p, summ, news in rows:
            out.append({
                "rank": p.rank,
                "title_vi": summ.title_vi,
                "bullets": json.loads(summ.bullets_json),
                "hashtags": summ.hashtags.split(",") if summ.hashtags else [],
                "source": news.source,
                "url": news.url,
            })
        return {"date": d, "top_posts": out}