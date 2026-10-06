from __future__ import annotations

import logging
import random
import uuid

from sqlalchemy import select

from autopost_api.categories_allowlist import is_blocked_category_name
from autopost_api.config import settings
from autopost_api.db.models import Batch, BatchItem, Category, Post, TopicSuggestion, User
from autopost_api.db.seed import OPERATOR_EMAIL
from autopost_api.db.session import SessionLocal
from autopost_api.integrations.claude_client import recommend_topics
from autopost_api.workers.enqueue import enqueue_batch

logger = logging.getLogger("autopost.autopilot")


def autopilot_channels() -> list[str]:
    codes = [part.strip() for part in settings.autopilot_channels.split(",") if part.strip()]
    return [code for code in codes if settings.channel_configured(code)]


def run_autopilot() -> str:
    """Pick a random category and topic, then queue one post."""
    if not settings.autopilot_enabled:
        return "disabled"
    if settings.use_mock_claude:
        logger.warning("autopilot skipped: ANTHROPIC_API_KEY is empty")
        return "no-key"
    channels = autopilot_channels()
    if not channels:
        logger.warning("autopilot skipped: no configured publish channel")
        return "no-channel"

    db = SessionLocal()
    try:
        categories = [
            category
            for category in db.scalars(select(Category).where(Category.is_active.is_(True))).all()
            if not is_blocked_category_name(category.name)
        ]
        if not categories:
            logger.warning("autopilot skipped: no active category")
            return "no-category"
        category = random.choice(categories)
        recent = db.scalars(
            select(Post.title).where(Post.category_id == category.id).order_by(Post.created_at.desc()).limit(50)
        ).all()
        payload = recommend_topics(category.name, category.description or "", list(recent))
        topics_data = payload.get("topics") or []
        if len(topics_data) < 1:
            logger.warning("autopilot skipped: no topics returned")
            return "no-topics"

        batch_recommend_id = str(uuid.uuid4())
        created: list[TopicSuggestion] = []
        for item in topics_data[:10]:
            row = TopicSuggestion(
                category_id=category.id,
                batch_recommend_id=batch_recommend_id,
                title=str(item.get("title") or "Untitled")[:300],
                angle=str(item.get("angle") or ""),
                seed_keywords=list(item.get("seed_keywords") or []),
                score=float(item.get("score") or 0),
                status="suggested",
                raw_model_response=item,
            )
            db.add(row)
            created.append(row)
        db.commit()
        for row in created:
            db.refresh(row)

        topic = random.choice(created)
        user = db.scalar(select(User).where(User.email == OPERATOR_EMAIL))
        if user is None:
            logger.warning("autopilot skipped: operator user missing")
            return "no-user"

        topic.status = "selected"
        batch = Batch(
            user_id=user.id,
            category_id=category.id,
            publish_mode="immediate",
            interval_codes=[],
            interval_mode="sequential_cycle",
            channels=channels,
            status="pending",
        )
        db.add(batch)
        db.flush()
        db.add(
            BatchItem(
                batch_id=batch.id,
                topic_suggestion_id=topic.id,
                sequence_index=0,
                status="pending",
            )
        )
        db.commit()
        enqueue_batch(batch.id)
        logger.info(
            "autopilot queued batch=%s category=%s topic=%s channels=%s",
            batch.id,
            category.slug,
            topic.title,
            ",".join(channels),
        )
        return batch.id
    except Exception:
        db.rollback()
        logger.exception("autopilot failed")
        return "failed"
    finally:
        db.close()
