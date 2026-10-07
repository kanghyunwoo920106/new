from __future__ import annotations

import re
from typing import Any

from slugify import slugify

from autopost_api.config import settings
from autopost_api.integrations.claude_client import generate_deep_post
from autopost_api.services.post_layout import ensure_image_markers, render_readable_html


def count_content_chars(text: str) -> int:
    plain = re.sub(r"[#>*`\[\]()\-_]", "", text)
    plain = re.sub(r"\s+", "", plain)
    return len(plain)


class ContentGenerationService:
    def generate_from_topic(self, topic: Any, category: Any) -> dict[str, Any]:
        data, meta = generate_deep_post(
            title=topic.title,
            angle=topic.angle or "",
            keywords=topic.seed_keywords or [],
            category_name=category.name,
            min_chars=settings.min_post_chars,
        )
        body_md = data["body_markdown"]
        char_count = count_content_chars(body_md)
        if char_count < settings.min_post_chars:
            data, meta = generate_deep_post(
                title=topic.title,
                angle=(topic.angle or "")
                + f"\n이전이 {char_count}자라서 부족합니다. 더 깊게 확장하세요.",
                keywords=topic.seed_keywords or [],
                category_name=category.name,
                min_chars=settings.min_post_chars,
            )
            body_md = data["body_markdown"]
            char_count = count_content_chars(body_md)

        body_md = ensure_image_markers(body_md, data.get("image_queries"))
        body_html = render_readable_html(body_md)
        title = data.get("title") or topic.title
        # ASCII slugs avoid Next.js / proxy double-encoding issues with Hangul paths.
        base_slug = slugify(title, allow_unicode=False) or "post"
        return {
            "title": title,
            "slug": base_slug,
            "excerpt": (data.get("excerpt") or data.get("meta_description") or "")[:500],
            "body_markdown": body_md,
            "body_html": body_html,
            "seo_tags": data.get("seo_tags") or topic.seed_keywords or [],
            "char_count": char_count,
            "model_id": meta.get("model") or settings.claude_model_generate,
            "tokens_in": int(meta.get("input_tokens") or 0),
            "tokens_out": int(meta.get("output_tokens") or 0),
            "meta": meta,
        }
