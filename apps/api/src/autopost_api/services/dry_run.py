"""Generate one post and save HTML without calling the Blogger API."""

from __future__ import annotations

import random
from pathlib import Path
from types import SimpleNamespace

from sqlalchemy import select

from autopost_api.categories_allowlist import is_blocked_category_name
from autopost_api.config import ROOT, settings
from autopost_api.db.models import Category, Post
from autopost_api.db.session import SessionLocal
from autopost_api.integrations.claude_client import recommend_topics
from autopost_api.services.content_generator import ContentGenerationService


def dry_run_output_path() -> Path:
    path = Path(settings.autopilot_dry_run_path)
    if not path.is_absolute():
        path = ROOT / path
    return path


def run_dry_run() -> str:
    """Pick one topic, render HTML, and write it to disk. Does not publish."""
    db = SessionLocal()
    try:
        categories = [
            category
            for category in db.scalars(select(Category).where(Category.is_active.is_(True))).all()
            if not is_blocked_category_name(category.name)
        ]
        if not categories:
            raise RuntimeError("no-category")
        category = random.choice(categories)
        recent = db.scalars(
            select(Post.title).where(Post.category_id == category.id).order_by(Post.created_at.desc()).limit(50)
        ).all()
        payload = recommend_topics(category.name, category.description or "", list(recent))
    finally:
        db.close()

    topics = payload.get("topics") or []
    if not topics:
        raise RuntimeError("no-topics")
    item = random.choice(topics[:10])
    topic = SimpleNamespace(
        title=str(item.get("title") or "Untitled"),
        angle=str(item.get("angle") or ""),
        seed_keywords=list(item.get("seed_keywords") or []),
    )
    result = ContentGenerationService().generate_from_topic(topic, category)
    path = dry_run_output_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(result["body_html"], encoding="utf-8")
    return str(path)
