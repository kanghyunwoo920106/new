from __future__ import annotations

import random
from typing import Any

from autopost_api.config import settings
from autopost_api.integrations.claude_client import review_post_sample


def should_review(*, sequence_index: int, sample_rate: float | None = None) -> bool:
    """Review first item of each batch, plus ~sample_rate of the rest."""
    rate = settings.review_sample_rate if sample_rate is None else sample_rate
    if sequence_index == 0:
        return True
    return random.random() < rate


def review_generated_post(post_payload: dict[str, Any]) -> dict[str, Any]:
    result = review_post_sample(
        title=post_payload["title"],
        excerpt=post_payload.get("excerpt") or "",
        body_markdown=post_payload["body_markdown"],
        seo_tags=list(post_payload.get("seo_tags") or []),
    )
    passed = bool(result.get("pass", True))
    return {
        "review_status": "passed" if passed else "flagged",
        "review_notes": result.get("notes") or "",
        "raw": result,
    }
