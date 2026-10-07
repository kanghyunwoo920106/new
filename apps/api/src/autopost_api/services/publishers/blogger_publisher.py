from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import httpx

from autopost_api.config import settings

TOKEN_URL = "https://oauth2.googleapis.com/token"


class BloggerPublisher:
    """Publishes to a Google Blogger blog via the official Blogger API v3."""

    channel_code = "blogger"

    def publish(self, post: Any) -> dict:
        if not settings.channel_configured("blogger"):
            raise RuntimeError(
                "구글 블로거 설정이 없습니다. .env에 BLOGGER_BLOG_ID와 "
                "GOOGLE_REFRESH_TOKEN(또는 BLOGGER_ACCESS_TOKEN)을 넣으세요."
            )

        token = self._access_token()
        labels = [tag.tag for tag in (post.seo_tags or []) if getattr(tag, "tag", "")][:20]
        content = post.body_html or post.body_markdown or post.excerpt or ""
        url = f"https://www.googleapis.com/blogger/v3/blogs/{settings.blogger_blog_id.strip()}/posts"
        response = httpx.post(
            url,
            headers={"Authorization": f"Bearer {token}"},
            json={
                "kind": "blogger#post",
                "title": post.title,
                "content": content,
                "labels": labels,
            },
            timeout=45,
        )
        if response.status_code >= 400:
            raise RuntimeError(f"구글 블로거 발행 실패: {response.text[:500]}")
        data = response.json()

        if post.status == "ready":
            post.status = "published_blogger"
        if post.published_at is None:
            post.published_at = datetime.now(timezone.utc)
        return {"url": data.get("url"), "channel": "blogger", "post_id": data.get("id")}

    def _access_token(self) -> str:
        if (
            settings.google_client_id.strip()
            and settings.google_client_secret.strip()
            and settings.google_refresh_token.strip()
        ):
            response = httpx.post(
                TOKEN_URL,
                data={
                    "client_id": settings.google_client_id.strip(),
                    "client_secret": settings.google_client_secret.strip(),
                    "refresh_token": settings.google_refresh_token.strip(),
                    "grant_type": "refresh_token",
                },
                timeout=30,
            )
            if response.status_code >= 400:
                raise RuntimeError(f"구글 토큰 갱신 실패: {response.text[:500]}")
            token = response.json().get("access_token")
            if not token:
                raise RuntimeError("구글 토큰 응답에 access_token이 없습니다.")
            return token
        return settings.blogger_access_token.strip()

    def latest_published_at(self) -> datetime | None:
        """Published time of the newest live post, if the blog has one."""
        if not settings.channel_configured("blogger"):
            return None
        token = self._access_token()
        url = f"https://www.googleapis.com/blogger/v3/blogs/{settings.blogger_blog_id.strip()}/posts"
        response = httpx.get(
            url,
            headers={"Authorization": f"Bearer {token}"},
            params={"maxResults": 1, "fetchBodies": "false", "status": "live"},
            timeout=30,
        )
        if response.status_code >= 400:
            raise RuntimeError(f"구글 블로거 글 목록 조회 실패: {response.text[:500]}")
        items = response.json().get("items") or []
        if not items:
            return None
        raw = str(items[0].get("published") or "")
        if not raw:
            return None
        published = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        if published.tzinfo is None:
            published = published.replace(tzinfo=timezone.utc)
        return published.astimezone(timezone.utc)
