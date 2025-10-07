import os
from dotenv import load_dotenv
load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
OUTPUT_LANG = os.getenv("OUTPUT_LANG", "vi")
DAILY_TOP_K = int(os.getenv("DAILY_TOP_K", "10"))
TIMEZONE = os.getenv("TIMEZONE", "Asia/Ho_Chi_Minh")
OUTPUT_LANG = "tiếng Việt"

DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "ai_news.db"))
