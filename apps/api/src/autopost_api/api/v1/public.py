from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from autopost_api.api.schemas import PostOut, SeoTagOut
from autopost_api.db.models import Post
from autopost_api.db.session import get_db

router = APIRouter(prefix="/public", tags=["public"])


def _public_post(post: Post) -> PostOut:
    return PostOut(
        id=post.id,
        category_id=post.category_id,
        category_name=post.category.name if post.category else None,
        title=post.title,
        slug=post.slug,
        excerpt=post.excerpt,
        body_markdown=post.body_markdown,
        body_html=post.body_html,
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


@router.get("/posts", response_model=list[PostOut])
def list_published(db: Session = Depends(get_db)) -> list[PostOut]:
    rows = db.scalars(
        select(Post)
        .options(joinedload(Post.category), joinedload(Post.seo_tags))
        .where(Post.status == "published_site")
        .order_by(Post.published_at.desc())
        .limit(100)
    ).unique().all()
    return [_public_post(p) for p in rows]


@router.get("/posts/{slug}", response_model=PostOut)
def get_published(slug: str, db: Session = Depends(get_db)) -> PostOut:
    post = db.scalar(
        select(Post)
        .options(joinedload(Post.category), joinedload(Post.seo_tags))
        .where(Post.slug == slug, Post.status == "published_site")
    )
    if post is None:
        raise HTTPException(status_code=404, detail="Post not found")
    return _public_post(post)
