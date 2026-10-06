from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from autopost_api.api.schemas import PublishJobOut
from autopost_api.db.models import PublishJob
from autopost_api.db.session import get_db

router = APIRouter(prefix="/jobs", tags=["jobs"])


def _job_out(job: PublishJob) -> PublishJobOut:
    return PublishJobOut(
        id=job.id,
        post_id=job.post_id,
        post_title=job.post.title if job.post else None,
        post_slug=job.post.slug if job.post else None,
        channel_code=job.channel_code,
        run_at=job.run_at,
        status=job.status,
        attempt=job.attempt,
        result_payload=job.result_payload,
        last_error=job.last_error,
    )


@router.get("", response_model=list[PublishJobOut])
def list_jobs(
    status: str | None = Query(default=None),
    db: Session = Depends(get_db),
) -> list[PublishJobOut]:
    q = select(PublishJob).options(joinedload(PublishJob.post)).order_by(PublishJob.run_at.desc())
    if status:
        q = q.where(PublishJob.status == status)
    rows = db.scalars(q.limit(100)).unique().all()
    return [_job_out(j) for j in rows]


@router.post("/{job_id}/cancel", response_model=PublishJobOut)
def cancel_job(job_id: str, db: Session = Depends(get_db)) -> PublishJobOut:
    job = db.scalar(select(PublishJob).options(joinedload(PublishJob.post)).where(PublishJob.id == job_id))
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.status not in {"queued", "locked"}:
        raise HTTPException(status_code=400, detail=f"Cannot cancel job in status={job.status}")
    job.status = "cancelled"
    db.commit()
    db.refresh(job)
    return _job_out(job)
