from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from autopost_api.api.schemas import RecommendRequest, RecommendResponse, TopicOut
from autopost_api.categories_allowlist import is_blocked_category_name
from autopost_api.config import settings
from autopost_api.db.models import Category, Post, TopicSuggestion
from autopost_api.db.session import get_db
from autopost_api.integrations.claude_client import recommend_topics

router = APIRouter(prefix="/topics", tags=["topics"])


@router.post("/recommend", response_model=RecommendResponse)
def recommend(req: RecommendRequest, db: Session = Depends(get_db)) -> RecommendResponse:
    category = db.get(Category, req.category_id)
    if category is None or not category.is_active:
        raise HTTPException(status_code=404, detail="Category not found")
    if is_blocked_category_name(category.name):
        raise HTTPException(status_code=400, detail="Category is blocked by allowlist policy")

    recent = db.scalars(
        select(Post.title).where(Post.category_id == category.id).order_by(Post.created_at.desc()).limit(50)
    ).all()

    payload = recommend_topics(category.name, category.description or "", list(recent))
    topics_data = payload.get("topics") or []
    if len(topics_data) < 10:
        raise HTTPException(status_code=502, detail="AI returned fewer than 10 topics")

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

    return RecommendResponse(
        batch_recommend_id=batch_recommend_id,
        mock_claude=settings.use_mock_claude,
        topics=[TopicOut.model_validate(t) for t in created],
    )
