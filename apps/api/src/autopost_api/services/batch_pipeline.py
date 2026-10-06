from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from autopost_api.channels import ALLOWED_CHANNELS
from autopost_api.db.models import Batch, BatchItem, Post, PostSeoTag, PublishJob, TopicSuggestion
from autopost_api.services.content_generator import ContentGenerationService
from autopost_api.services.quality_reviewer import review_generated_post, should_review
from autopost_api.services.schedule_planner import plan_run_times


def _unique_slug(db: Session, base: str) -> str:
    slug = base
    n = 2
    while db.scalar(select(Post.id).where(Post.slug == slug)):
        slug = f"{base}-{n}"
        n += 1
    return slug


def process_batch(db: Session, batch_id: str) -> Batch:
    batch = db.scalar(
        select(Batch)
        .options(
            joinedload(Batch.items)
            .joinedload(BatchItem.topic_suggestion)
            .joinedload(TopicSuggestion.category)
        )
        .where(Batch.id == batch_id)
    )
    if batch is None:
        raise ValueError("batch not found")

    batch.status = "generating"
    db.commit()

    generator = ContentGenerationService()
    ready_posts: list[Post] = []

    for item in sorted(batch.items, key=lambda x: x.sequence_index):
        topic = item.topic_suggestion
        category = topic.category
        item.status = "generating"
        db.commit()

        result = generator.generate_from_topic(topic, category)
        review = {"review_status": "skipped", "review_notes": ""}
        if should_review(sequence_index=item.sequence_index):
            review = review_generated_post(result)

        post = Post(
            category_id=category.id,
            title=result["title"],
            slug=_unique_slug(db, result["slug"]),
            body_markdown=result["body_markdown"],
            body_html=result["body_html"],
            excerpt=result["excerpt"],
            char_count=result["char_count"],
            status="ready",
            model_id=result["model_id"],
            tokens_in=result["tokens_in"],
            tokens_out=result["tokens_out"],
            adsense_eligible=review["review_status"] != "flagged",
            review_status=review["review_status"],
            review_notes=review["review_notes"],
        )
        db.add(post)
        db.flush()
        for tag in result["seo_tags"]:
            tag_text = str(tag).strip()[:80]
            if tag_text:
                db.add(PostSeoTag(post_id=post.id, tag=tag_text, tag_type="keyword"))

        item.post_id = post.id
        item.status = "generated"
        topic.status = "generated"
        ready_posts.append(post)
        db.commit()

    now = datetime.now(timezone.utc)
    if batch.publish_mode == "immediate":
        times = [now for _ in ready_posts]
    else:
        if batch.first_publish_at is None:
            raise ValueError("first_publish_at required for scheduled mode")
        times = plan_run_times(
            first_publish_at=batch.first_publish_at,
            count=len(ready_posts),
            interval_codes=list(batch.interval_codes or []),
            mode=batch.interval_mode or "sequential_cycle",
        )

    channels = [c for c in (batch.channels or ["site"]) if c in ALLOWED_CHANNELS]
    if not channels:
        channels = ["site"]
    channels = sorted(channels, key=lambda code: 0 if code == "site" else 1)

    for idx, post in enumerate(ready_posts):
        run_at = times[idx]
        for channel in channels:
            key = f"{post.id}:{channel}:{run_at.isoformat()}"
            db.add(
                PublishJob(
                    post_id=post.id,
                    channel_code=channel,
                    run_at=run_at,
                    status="queued",
                    idempotency_key=key,
                )
            )

    batch.status = "ready"
    db.commit()
    db.refresh(batch)
    return batch
