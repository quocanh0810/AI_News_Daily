from sqlalchemy import String, Integer, DateTime, Text, JSON, Float, UniqueConstraint
from sqlalchemy.orm import mapped_column, Mapped
from datetime import datetime
from .db import Base

class News(Base):
    __tablename__ = "news"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    url: Mapped[str] = mapped_column(String(2048), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(512))
    source: Mapped[str] = mapped_column(String(128), index=True)
    published_at: Mapped[datetime] = mapped_column(DateTime, index=True)
    og_image: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    content_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    lang: Mapped[str | None] = mapped_column(String(16), nullable=True)
    fetched_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    social_score: Mapped[float] = mapped_column(Float, default=0.0)
    topic_tags: Mapped[str | None] = mapped_column(String(256), nullable=True)  # comma-separated

class Summary(Base):
    __tablename__ = "summaries"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    news_id: Mapped[int] = mapped_column(Integer, index=True)
    title_vi: Mapped[str] = mapped_column(String(256))
    bullets_json: Mapped[str] = mapped_column(Text)  # JSON list
    so_what_vn: Mapped[str] = mapped_column(Text)
    hashtags: Mapped[str] = mapped_column(String(128))
    attribution: Mapped[str] = mapped_column(String(256))
    url: Mapped[str] = mapped_column(String(2048))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class Picks(Base):
    __tablename__ = "picks"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    date_str: Mapped[str] = mapped_column(String(16), index=True)  # YYYY-MM-DD
    rank: Mapped[int] = mapped_column(Integer)
    news_id: Mapped[int] = mapped_column(Integer, index=True)
    summary_id: Mapped[int] = mapped_column(Integer, index=True)
