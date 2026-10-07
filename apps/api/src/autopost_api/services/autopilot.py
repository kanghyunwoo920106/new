from __future__ import annotations

import logging
import random
import sys
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from autopost_api.categories_allowlist import is_blocked_category_name
from autopost_api.config import settings
from autopost_api.db.models import Batch, BatchItem, Category, Post, TopicSuggestion, User
from autopost_api.db.seed import OPERATOR_EMAIL
from autopost_api.db.session import SessionLocal
from autopost_api.integrations.claude_client import recommend_topics
from autopost_api.workers.enqueue import enqueue_batch

logger = logging.getLogger("autopost.autopilot")


# Slots are 3 hours apart. A second attempt inside one slot must not publish again.
RECENT_POST_WINDOW = timedelta(hours=2)


def published_recently(published_at: datetime | None, *, now: datetime, within: timedelta) -> bool:
    if published_at is None:
        return False
    if published_at.tzinfo is None:
        published_at = published_at.replace(tzinfo=timezone.utc)
    return now - published_at.astimezone(timezone.utc) < within


def blogger_posted_recently(within: timedelta = RECENT_POST_WINDOW) -> bool:
    """True when this Blogger slot already has a live post."""
    if "blogger" not in autopilot_channels():
        return False
    from autopost_api.services.publishers.blogger_publisher import BloggerPublisher

    published_at = BloggerPublisher().latest_published_at()
    return published_recently(published_at, now=datetime.now(timezone.utc), within=within)


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


_FAILURES = frozenset(
    {"failed", "no-key", "no-channel", "no-category", "no-topics", "no-user", "disabled"}
)


def _apply_cli(argv: list[str]) -> None:
    if "--dry-run" in argv:
        settings.autopilot_dry_run = True
    if "--output" in argv:
        index = argv.index("--output")
        if index + 1 >= len(argv):
            raise SystemExit("dry-run --output 뒤에 파일 경로가 필요합니다.")
        settings.autopilot_dry_run_path = argv[index + 1]


def main(argv: list[str] | None = None) -> None:
    """One-shot entrypoint for an always-on scheduler such as GitHub Actions.

    Generates one post, waits until that work finishes, publishes due jobs,
    then exits. A non-zero exit means nothing was published.
    `--dry-run` writes HTML and does not publish.
    """
    logging.basicConfig(level=logging.INFO)
    _apply_cli(sys.argv[1:] if argv is None else argv)
    if settings.autopilot_dry_run:
        from autopost_api.db.models import Base
        from autopost_api.db.seed import seed_if_empty
        from autopost_api.db.session import SessionLocal, engine
        from autopost_api.services.dry_run import run_dry_run

        Base.metadata.create_all(bind=engine)
        db = SessionLocal()
        try:
            seed_if_empty(db)
        finally:
            db.close()
        try:
            print(run_dry_run())
        except Exception:
            logger.exception("dry-run failed")
            raise SystemExit(1) from None
        return
    from autopost_api.db.models import Base, PublishJob
    from autopost_api.db.seed import seed_if_empty
    from autopost_api.db.session import SessionLocal, engine
    from autopost_api.workers.enqueue import wait_inline
    from autopost_api.workers.scheduler import dispatch_due_jobs

    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        seed_if_empty(db)
    finally:
        db.close()

    try:
        if not settings.autopilot_ignore_recent and blogger_posted_recently():
            print("already-posted")
            return
    except Exception:
        logger.exception("recent Blogger post check failed; continuing")

    result = run_autopilot()
    print(result)
    if result in _FAILURES:
        raise SystemExit(1)
    if settings.use_celery:
        logger.error("autopilot one-shot requires the inline scheduler, not Celery")
        raise SystemExit(1)

    wait_inline()
    published = dispatch_due_jobs()
    print(f"published={published}")

    db = SessionLocal()
    try:
        batch = db.get(Batch, result)
        if batch is None or batch.status != "ready":
            status = batch.status if batch is not None else "missing"
            print(f"batch_status={status}")
            raise SystemExit(1)
        post_ids = [item.post_id for item in batch.items if item.post_id]
        jobs = []
        if post_ids:
            jobs = list(db.scalars(select(PublishJob).where(PublishJob.post_id.in_(post_ids))).all())
        failed = [job for job in jobs if job.status != "succeeded"]
        if not jobs or failed or published < 1:
            summary = ",".join(f"{job.channel_code}:{job.status}" for job in jobs) or "none"
            print(f"publish_jobs={summary}")
            raise SystemExit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()
