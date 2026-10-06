from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import httpx

from autopost_api.config import settings

TISTORY_WRITE_URL = "https://www.tistory.com/apis/post/write"


class TistoryPublisher:
    channel_code = "tistory"

    def publish(self, post: Any) -> dict:
        if not settings.channel_configured("tistory"):
            raise RuntimeError("티스토리 설정이 없습니다. .env에 TISTORY_ACCESS_TOKEN과 TISTORY_BLOG_NAME을 넣으세요.")

        tags = ",".join(tag.tag for tag in (post.seo_tags or []) if getattr(tag, "tag", ""))
        content = post.body_html or post.body_markdown or post.excerpt or ""
        form = {
            "access_token": settings.tistory_access_token.strip(),
            "output": "json",
            "blogName": settings.tistory_blog_name.strip(),
            "title": post.title,
            "content": content,
            "visibility": "3",
            "tag": tags,
            "acceptComment": "1",
        }
        response = httpx.post(TISTORY_WRITE_URL, data=form, timeout=45)
        response.raise_for_status()
        payload = response.json()
        body = payload.get("tistory") or {}
        status = str(body.get("status") or "")
        if status != "200":
            message = body.get("error_message") or body.get("error") or payload
            raise RuntimeError(f"티스토리 발행 실패: {message}")

        if post.status == "ready":
            post.status = "published_tistory"
        if post.published_at is None:
            post.published_at = datetime.now(timezone.utc)
        return {"url": body.get("url"), "channel": "tistory", "post_id": body.get("postId")}
