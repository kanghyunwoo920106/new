from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from autopost_api.services.publishers.blogger_publisher import BloggerPublisher
from autopost_api.services.publishers.site_publisher import SitePublisher
from autopost_api.services.publishers.tistory_publisher import TistoryPublisher


class PublishOrchestrator:
    def __init__(self, db: Session):
        self.db = db
        self.publishers = {
            "site": SitePublisher(),
            "tistory": TistoryPublisher(),
            "blogger": BloggerPublisher(),
        }

    def publish(self, job: Any) -> dict:
        publisher = self.publishers.get(job.channel_code)
        if publisher is None:
            raise ValueError(f"지원하지 않는 발행 채널입니다: {job.channel_code}")
        post = job.post
        result = publisher.publish(post)
        self.db.add(post)
        self.db.flush()
        return result
