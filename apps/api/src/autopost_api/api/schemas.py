from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class CategoryOut(BaseModel):
    id: str
    name: str
    slug: str
    description: str
    adsense_slot_hint: str
    is_active: bool

    model_config = {"from_attributes": True}


class TopicOut(BaseModel):
    id: str
    category_id: str
    batch_recommend_id: str
    title: str
    angle: str
    seed_keywords: list[str]
    score: float
    status: str

    model_config = {"from_attributes": True}


class RecommendRequest(BaseModel):
    category_id: str


class RecommendResponse(BaseModel):
    batch_recommend_id: str
    mock_claude: bool
    topics: list[TopicOut]


class BatchCreateRequest(BaseModel):
    category_id: str
    topic_suggestion_ids: list[str] = Field(min_length=1)
    publish_mode: Literal["immediate", "scheduled"]
    first_publish_at: datetime | None = None
    interval_codes: list[str] = Field(default_factory=list)
    interval_mode: Literal["sequential_cycle"] = "sequential_cycle"
    channels: list[str] = Field(default_factory=lambda: ["site"])


class BatchItemOut(BaseModel):
    id: str
    topic_suggestion_id: str
    post_id: str | None
    sequence_index: int
    status: str
    topic_title: str | None = None
    post_title: str | None = None
    post_slug: str | None = None
    char_count: int | None = None
    review_status: str | None = None


class BatchOut(BaseModel):
    id: str
    category_id: str
    publish_mode: str
    first_publish_at: datetime | None
    interval_codes: list[str]
    interval_mode: str
    channels: list[str]
    status: str
    created_at: datetime
    items: list[BatchItemOut] = []


class SeoTagOut(BaseModel):
    tag: str
    tag_type: str

    model_config = {"from_attributes": True}


class PostOut(BaseModel):
    id: str
    category_id: str
    category_name: str | None = None
    title: str
    slug: str
    excerpt: str
    body_markdown: str | None = None
    body_html: str | None = None
    char_count: int
    status: str
    model_id: str
    adsense_eligible: bool
    review_status: str
    review_notes: str
    published_at: datetime | None
    created_at: datetime
    seo_tags: list[SeoTagOut] = []


class PublishJobOut(BaseModel):
    id: str
    post_id: str
    post_title: str | None = None
    post_slug: str | None = None
    channel_code: str
    run_at: datetime
    status: str
    attempt: int
    result_payload: dict | None = None
    last_error: str | None = None


class HealthOut(BaseModel):
    status: str
    mock_claude: bool
    database: str
    scheduler: str
    configured_channels: list[str] = Field(default_factory=lambda: ["site"])
