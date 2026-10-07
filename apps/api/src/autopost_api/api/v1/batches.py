from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from autopost_api.api.schemas import BatchCreateRequest, BatchItemOut, BatchOut
from autopost_api.categories_allowlist import is_blocked_category_name
from autopost_api.channels import ALLOWED_CHANNELS
from autopost_api.config import settings
from autopost_api.db.models import Batch, BatchItem, Category, TopicSuggestion, User
from autopost_api.db.seed import OPERATOR_EMAIL
from autopost_api.db.session import get_db
from autopost_api.services.schedule_planner import ALLOWED_INTERVALS, normalize_intervals
from autopost_api.workers.enqueue import enqueue_batch

router = APIRouter(prefix="/batches", tags=["batches"])


def _batch_out(batch: Batch) -> BatchOut:
    items: list[BatchItemOut] = []
    for item in sorted(batch.items, key=lambda x: x.sequence_index):
        topic = item.topic_suggestion
        post = item.post
        items.append(
            BatchItemOut(
                id=item.id,
                topic_suggestion_id=item.topic_suggestion_id,
                post_id=item.post_id,
                sequence_index=item.sequence_index,
                status=item.status,
                topic_title=topic.title if topic else None,
                post_title=post.title if post else None,
                post_slug=post.slug if post else None,
                char_count=post.char_count if post else None,
                review_status=post.review_status if post else None,
            )
        )
    return BatchOut(
        id=batch.id,
        category_id=batch.category_id,
        publish_mode=batch.publish_mode,
        first_publish_at=batch.first_publish_at,
        interval_codes=list(batch.interval_codes or []),
        interval_mode=batch.interval_mode,
        channels=list(batch.channels or []),
        status=batch.status,
        created_at=batch.created_at,
        items=items,
    )


@router.post("", response_model=BatchOut)
def create_batch(
    req: BatchCreateRequest,
    db: Session = Depends(get_db),
) -> BatchOut:
    category = db.get(Category, req.category_id)
    if category is None or not category.is_active or is_blocked_category_name(category.name):
        raise HTTPException(status_code=400, detail="Invalid or blocked category")

    unknown = [c for c in req.channels if c not in ALLOWED_CHANNELS]
    if unknown:
        raise HTTPException(status_code=400, detail=f"지원하지 않는 채널: {', '.join(unknown)}")
    if "tistory" in req.channels:
        raise HTTPException(
            status_code=400,
            detail=(
                "티스토리 Open API 글쓰기는 2024년 2월에 종료되어 자동 발행할 수 없습니다. "
                "글은 티스토리 에디터에서 직접 작성해야 합니다."
            ),
        )
    channels = list(dict.fromkeys(req.channels)) or ["site"]
    missing = [c for c in channels if not settings.channel_configured(c)]
    if missing:
        raise HTTPException(
            status_code=400,
            detail=f"채널 토큰이 없습니다: {', '.join(missing)}. .env를 채운 뒤 API를 다시 시작하세요.",
        )

    if req.publish_mode == "scheduled":
        if req.first_publish_at is None:
            raise HTTPException(status_code=400, detail="first_publish_at required")
        try:
            intervals = normalize_intervals(req.interval_codes)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        bad = [c for c in intervals if c not in ALLOWED_INTERVALS]
        if bad:
            raise HTTPException(status_code=400, detail=f"unsupported intervals: {bad}")
    else:
        intervals = []

    topics = db.scalars(
        select(TopicSuggestion).where(TopicSuggestion.id.in_(req.topic_suggestion_ids))
    ).all()
    by_id = {t.id: t for t in topics}
    ordered = []
    for tid in req.topic_suggestion_ids:
        t = by_id.get(tid)
        if t is None or t.category_id != category.id:
            raise HTTPException(status_code=400, detail=f"Invalid topic: {tid}")
        ordered.append(t)

    user = db.scalar(select(User).where(User.email == OPERATOR_EMAIL))
    if user is None:
        raise HTTPException(status_code=500, detail="Operator user missing; restart API to seed")

    batch = Batch(
        user_id=user.id,
        category_id=category.id,
        publish_mode=req.publish_mode,
        first_publish_at=req.first_publish_at,
        interval_codes=intervals,
        interval_mode=req.interval_mode,
        channels=channels,
        status="pending",
    )
    db.add(batch)
    db.flush()
    for idx, topic in enumerate(ordered):
        topic.status = "selected"
        db.add(
            BatchItem(
                batch_id=batch.id,
                topic_suggestion_id=topic.id,
                sequence_index=idx,
                status="pending",
            )
        )
    db.commit()

    enqueue_batch(batch.id)

    batch = db.scalar(
        select(Batch)
        .options(
            joinedload(Batch.items).joinedload(BatchItem.topic_suggestion),
            joinedload(Batch.items).joinedload(BatchItem.post),
        )
        .where(Batch.id == batch.id)
    )
    assert batch is not None
    return _batch_out(batch)


@router.get("/{batch_id}", response_model=BatchOut)
def get_batch(batch_id: str, db: Session = Depends(get_db)) -> BatchOut:
    batch = db.scalar(
        select(Batch)
        .options(
            joinedload(Batch.items).joinedload(BatchItem.topic_suggestion),
            joinedload(Batch.items).joinedload(BatchItem.post),
        )
        .where(Batch.id == batch_id)
    )
    if batch is None:
        raise HTTPException(status_code=404, detail="Batch not found")
    return _batch_out(batch)


@router.get("", response_model=list[BatchOut])
def list_batches(db: Session = Depends(get_db)) -> list[BatchOut]:
    rows = db.scalars(
        select(Batch)
        .options(
            joinedload(Batch.items).joinedload(BatchItem.topic_suggestion),
            joinedload(Batch.items).joinedload(BatchItem.post),
        )
        .order_by(Batch.created_at.desc())
        .limit(50)
    ).unique().all()
    return [_batch_out(b) for b in rows]
