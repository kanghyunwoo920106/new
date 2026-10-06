from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from autopost_api.config import settings


class SitePublisher:
    channel_code = "site"

    def publish(self, post: Any) -> dict:
        post.status = "published_site"
        post.published_at = datetime.now(timezone.utc)
        url = f"{settings.site_public_base_url}/posts/{post.slug}"
        return {"url": url, "channel": "site"}
