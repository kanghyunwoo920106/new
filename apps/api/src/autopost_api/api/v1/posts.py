from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from autopost_api.api.schemas import PostOut, SeoTagOut
from autopost_api.db.models import Post, PublishJob
from autopost_api.db.session import get_db
from autopost_api.services.publish_orchestrator import PublishOrchestrator

router = APIRouter(prefix="/posts", tags=["posts"])


def _post_out(post: Post, *, include_body: bool = True) -> PostOut:
    return PostOut(
        id=post.id,
        category_id=post.category_id,
        category_name=post.category.name if post.category else None,
        title=post.title,
        slug=post.slug,
        excerpt=post.excerpt,
        body_markdown=post.body_markdown if include_body else None,
        body_html=post.body_html if include_body else None,
        char_count=post.char_count,
        status=post.status,
        model_id=post.model_id,
        adsense_eligible=post.adsense_eligible,
        review_status=post.review_status,
        review_notes=post.review_notes,
        published_at=post.published_at,
        created_at=post.created_at,
        seo_tags=[SeoTagOut.model_validate(t) for t in post.seo_tags],
    )


@router.get("", response_model=list[PostOut])
def list_posts(
    status: str | None = Query(default=None),
    db: Session = Depends(get_db),
) -> list[PostOut]:
    q = select(Post).options(joinedload(Post.category), joinedload(Post.seo_tags)).order_by(Post.created_at.desc())
    if status:
        q = q.where(Post.status == status)
    rows = db.scalars(q.limit(100)).unique().all()
    return [_post_out(p, include_body=False) for p in rows]


@router.get("/{post_id}", response_model=PostOut)
def get_post(post_id: str, db: Session = Depends(get_db)) -> PostOut:
    post = db.scalar(
        select(Post)
        .options(joinedload(Post.category), joinedload(Post.seo_tags))
        .where(Post.id == post_id)
    )
    if post is None:
        raise HTTPException(status_code=404, detail="Post not found")
    return _post_out(post)


@router.post("/{post_id}/publish", response_model=PostOut)
def publish_now(post_id: str, db: Session = Depends(get_db)) -> PostOut:
    post = db.scalar(
        select(Post)
        .options(joinedload(Post.category), joinedload(Post.seo_tags))
        .where(Post.id == post_id)
    )
    if post is None:
        raise HTTPException(status_code=404, detail="Post not found")
    if post.status == "published_site":
        return _post_out(post)

    now = datetime.now(timezone.utc)
    key = f"{post.id}:site:{now.isoformat()}:manual"
    job = PublishJob(
        post_id=post.id,
        channel_code="site",
        run_at=now,
        status="running",
        attempt=1,
        idempotency_key=key,
    )
    db.add(job)
    db.flush()
    result = PublishOrchestrator(db).publish(job)
    job.status = "succeeded"
    job.result_payload = result
    db.commit()
    db.refresh(post)
    return _post_out(post)
