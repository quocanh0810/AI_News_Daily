import os, json, re
from collections import Counter
from typing import Dict, List
from .config import OPENAI_API_KEY, OPENAI_MODEL, OUTPUT_LANG

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

# ----------------- OFFLINE FALLBACK -----------------
STOPWORDS = {
    "the","a","an","and","or","but","if","then","else","for","to","of","in","on","at","by",
    "with","about","as","is","are","was","were","be","been","being","this","that","it","its",
    "from","into","over","under","after","before","between","within","without","we","you",
    "they","their","our","i","he","she","them","his","her","my","me","us"
}

def _sentences(text: str):
    text = re.sub(r"\s+", " ", (text or "").strip())
    return re.split(r"(?<=[.!?])\s+", text) if text else []

def _keywords(text: str, topk=5):
    words = [w for w in re.findall(r"[A-Za-z]{3,}", (text or "").lower()) if w not in STOPWORDS]
    freq = Counter(words)
    return [w for w,_ in freq.most_common(topk)]

def _offline_summary(url: str, title: str, source: str, content: str) -> Dict:
    bullets = _sentences(content or "")[:4]
    kws = _keywords((title or "") + " " + (content or ""), 5)
    return {
        "title_vi": f"[TÓM TẮT] {(title or '')[:80]}",
        "bullets": bullets or ["(Không trích được nội dung)"],
        "so_what_vn": "Gợi ý: xem khả năng ứng dụng tại VN (doanh nghiệp/giáo dục/chính sách).",
        "hashtags": ["#AInews"] + [f"#{k.capitalize()}" for k in kws[:3]],
        "attribution": source or "",
        "url": url or ""
    }

# ----------------- OPENAI (nếu còn dùng) -----------------
def _openai_summary(url: str, title: str, source: str, content: str) -> Dict:
    from openai import OpenAI
    client = OpenAI(api_key=OPENAI_API_KEY)
    system = f"""Bạn là biên tập viên công nghệ. Hãy tóm tắt bài viết về AI sang {OUTPUT_LANG}.
⚠️ Toàn bộ đầu ra phải bằng tiếng Việt tự nhiên.
Trả JSON với các trường: title_vi, bullets, so_what_vn, hashtags, attribution, url."""
    user = f"[TITLE]: {title}\n[SOURCE]: {source}\n[URL]: {url}\n[CONTENT]:\n{(content or '')[:4000]}"
    resp = client.chat.completions.create(
        model=OPENAI_MODEL,
        messages=[{"role":"system","content":system},{"role":"user","content":user}],
        temperature=0.3,
        response_format={"type":"json_object"},
    )
    return json.loads(resp.choices[0].message.content)

# ----------------- GOOGLE GEMINI (REST v1 – KHÔNG DÙNG SDK) -----------------
def _google_summary_rest(url: str, title: str, source: str, content: str) -> Dict:
    if not GOOGLE_API_KEY:
        raise RuntimeError("GOOGLE_API_KEY is missing")
    import requests

    endpoint = "https://generativelanguage.googleapis.com/v1/models/gemini-1.5-flash:generateContent"
    system_prompt = f"""Bạn là biên tập viên công nghệ. Hãy tóm tắt bài viết về AI sang {OUTPUT_LANG}.
⚠️ Toàn bộ kết quả phải bằng tiếng Việt tự nhiên.
Yêu cầu:
- Tiêu đề {OUTPUT_LANG} (60–90 ký tự), chính xác & hấp dẫn.
- 3–5 bullet: cái mới / tại sao quan trọng / số liệu (nếu có) / ứng dụng.
- 1–2 câu 'So what' cho Việt Nam.
- 3 hashtag ngắn (ví dụ: #AInews, #LLM, #RAG).
Trả JSON: title_vi, bullets, so_what_vn, hashtags, attribution, url."""
    user_prompt = f"[TITLE]: {title}\n[SOURCE]: {source}\n[URL]: {url}\n[CONTENT]:\n{(content or '')[:4000]}"

    payload = {
        "system_instruction": {"parts": [{"text": system_prompt}]},
        "contents": [{"role": "user", "parts": [{"text": user_prompt}]}],
        "generationConfig": {
            "temperature": 0.3,
            # ép JSON thuần để parse dễ
            "response_mime_type": "application/json"
        }
    }
    r = requests.post(endpoint, params={"key": GOOGLE_API_KEY}, json=payload, timeout=60)
    if r.status_code != 200:
        raise RuntimeError(f"Gemini HTTP {r.status_code}: {r.text[:300]}")
    data = r.json()
    try:
        text = data["candidates"][0]["content"]["parts"][0]["text"]
    except Exception:
        raise RuntimeError(f"Gemini response parse error: {json.dumps(data)[:300]}")

    # Model đã được ép trả JSON string
    try:
        out = json.loads(text)
    except Exception:
        # fallback cực chẳng đã nếu model vẫn trả text thường
        bullets = re.findall(r"[-•]\s*(.+)", text)
        out = {
            "title_vi": f"[Tóm tắt] {title}",
            "bullets": bullets[:5] or [text[:250]],
            "so_what_vn": "Tác động tại Việt Nam: " + (bullets[-1] if bullets else ""),
            "hashtags": ["#AInews", "#Gemini", "#Tech"],
            "attribution": source or "",
            "url": url or "",
        }
    # đảm bảo field
    out.setdefault("attribution", source or "")
    out.setdefault("url", url or "")
    return out

# ----------------- PUBLIC API -----------------
def summarize_article(url: str, title: str, source: str, content: str) -> Dict:
    # 1/ OpenAI (nếu có), 429/quota thì tự rơi xuống bước 2
    if OPENAI_API_KEY:
        try:
            return _openai_summary(url, title, source, content)
        except Exception as e:
            print(f"[summarizer] OpenAI failed → {e.__class__.__name__}. Trying Google REST...")

    # 2/ Google REST v1 (không dùng SDK)
    if GOOGLE_API_KEY:
        try:
            return _google_summary_rest(url, title, source, content)
        except Exception as e:
            print(f"[summarizer] Google REST failed → {e.__class__.__name__}. Using offline fallback...")

    # 3/ Offline
    return _offline_summary(url, title, source, content)