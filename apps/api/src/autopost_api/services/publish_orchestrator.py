from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from autopost_api.services.publishers.site_publisher import SitePublisher


class PublishOrchestrator:
    def __init__(self, db: Session):
        self.db = db
        self.publishers = {"site": SitePublisher()}

    def publish(self, job: Any) -> dict:
        if job.channel_code != "site":
            raise ValueError(
                f"Phase 1 supports own-site publishing only; got channel={job.channel_code}"
            )
        post = job.post
        result = self.publishers["site"].publish(post)
        self.db.add(post)
        self.db.flush()
        return result
