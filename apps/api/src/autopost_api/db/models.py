from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def _uuid() -> str:
    return str(uuid.uuid4())


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    timezone: Mapped[str] = mapped_column(String(64), default="Asia/Seoul")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    categories: Mapped[list[Category]] = relationship(back_populates="user")


class Category(Base):
    __tablename__ = "categories"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    slug: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    adsense_slot_hint: Mapped[str] = mapped_column(String(64), default="")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    user: Mapped[User] = relationship(back_populates="categories")
    topics: Mapped[list[TopicSuggestion]] = relationship(back_populates="category")
    posts: Mapped[list[Post]] = relationship(back_populates="category")


class TopicSuggestion(Base):
    __tablename__ = "topic_suggestions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    category_id: Mapped[str] = mapped_column(ForeignKey("categories.id"), nullable=False)
    batch_recommend_id: Mapped[str] = mapped_column(String(36), nullable=False)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    angle: Mapped[str] = mapped_column(Text, default="")
    seed_keywords: Mapped[list] = mapped_column(JSON, default=list)
    score: Mapped[float] = mapped_column(Float, default=0.0)
    status: Mapped[str] = mapped_column(String(32), default="suggested")
    raw_model_response: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    category: Mapped[Category] = relationship(back_populates="topics")


class Batch(Base):
    __tablename__ = "batches"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    category_id: Mapped[str] = mapped_column(ForeignKey("categories.id"), nullable=False)
    publish_mode: Mapped[str] = mapped_column(String(16), nullable=False)
    first_publish_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    interval_codes: Mapped[list] = mapped_column(JSON, default=list)
    interval_mode: Mapped[str] = mapped_column(String(32), default="sequential_cycle")
    channels: Mapped[list] = mapped_column(JSON, default=lambda: ["site"])
    status: Mapped[str] = mapped_column(String(32), default="pending")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    items: Mapped[list[BatchItem]] = relationship(back_populates="batch", order_by="BatchItem.sequence_index")


class BatchItem(Base):
    __tablename__ = "batch_items"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    batch_id: Mapped[str] = mapped_column(ForeignKey("batches.id"), nullable=False)
    topic_suggestion_id: Mapped[str] = mapped_column(ForeignKey("topic_suggestions.id"), nullable=False)
    post_id: Mapped[str | None] = mapped_column(ForeignKey("posts.id"), nullable=True)
    sequence_index: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="pending")

    batch: Mapped[Batch] = relationship(back_populates="items")
    topic_suggestion: Mapped[TopicSuggestion] = relationship()
    post: Mapped[Post | None] = relationship()


class Post(Base):
    __tablename__ = "posts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    category_id: Mapped[str] = mapped_column(ForeignKey("categories.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    slug: Mapped[str] = mapped_column(String(320), unique=True, nullable=False)
    body_markdown: Mapped[str] = mapped_column(Text, nullable=False)
    body_html: Mapped[str] = mapped_column(Text, nullable=False)
    excerpt: Mapped[str] = mapped_column(String(500), default="")
    char_count: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(32), default="draft")
    model_id: Mapped[str] = mapped_column(String(64), default="")
    prompt_version: Mapped[str] = mapped_column(String(32), default="v1")
    tokens_in: Mapped[int] = mapped_column(Integer, default=0)
    tokens_out: Mapped[int] = mapped_column(Integer, default=0)
    cost_usd_estimate: Mapped[float] = mapped_column(Float, default=0.0)
    adsense_eligible: Mapped[bool] = mapped_column(Boolean, default=True)
    review_status: Mapped[str] = mapped_column(String(32), default="skipped")
    review_notes: Mapped[str] = mapped_column(Text, default="")
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)

    category: Mapped[Category] = relationship(back_populates="posts")
    seo_tags: Mapped[list[PostSeoTag]] = relationship(back_populates="post", cascade="all, delete-orphan")
    publish_jobs: Mapped[list[PublishJob]] = relationship(back_populates="post")


class PostSeoTag(Base):
    __tablename__ = "post_seo_tags"
    __table_args__ = (UniqueConstraint("post_id", "tag", name="uq_post_tag"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    post_id: Mapped[str] = mapped_column(ForeignKey("posts.id", ondelete="CASCADE"), nullable=False)
    tag: Mapped[str] = mapped_column(String(80), nullable=False)
    tag_type: Mapped[str] = mapped_column(String(32), default="keyword")

    post: Mapped[Post] = relationship(back_populates="seo_tags")


class PublishJob(Base):
    __tablename__ = "publish_jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    post_id: Mapped[str] = mapped_column(ForeignKey("posts.id"), nullable=False)
    channel_code: Mapped[str] = mapped_column(String(32), nullable=False, default="site")
    run_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="queued")
    attempt: Mapped[int] = mapped_column(Integer, default=0)
    max_attempts: Mapped[int] = mapped_column(Integer, default=5)
    locked_by: Mapped[str | None] = mapped_column(String(64), nullable=True)
    locked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    idempotency_key: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    result_payload: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)

    post: Mapped[Post] = relationship(back_populates="publish_jobs")


class GenerationLog(Base):
    __tablename__ = "generation_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    post_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    request_meta: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    response_meta: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    latency_ms: Mapped[int] = mapped_column(Integer, default=0)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
