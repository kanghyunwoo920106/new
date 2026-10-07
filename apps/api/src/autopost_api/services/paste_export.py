"""Save the same HTML sent to Blogger so it can be pasted by hand."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from autopost_api.config import ROOT

PASTE_DIR = ROOT / "paste"
_INVALID = re.compile(r'[\\/:*?"<>|\x00-\x1f]+')


def paste_filename(title: str, when: datetime | None = None) -> str:
    moment = when or datetime.now(timezone.utc)
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    stamp = moment.astimezone(ZoneInfo("Asia/Seoul")).strftime("%Y%m%d-%H%M")
    cleaned = _INVALID.sub("-", title).strip(" .-")
    cleaned = re.sub(r"-{2,}", "-", cleaned)[:80].strip("-") or "post"
    return f"{stamp}-{cleaned}.html"


def render_paste_document(title: str, body_html: str, *, category: str = "", url: str = "") -> str:
    del url
    lines = [f"제목: {title.strip() or '글'}"]
    if category.strip():
        lines.append(f"카테고리: {category.strip()}")
    comment = "<!--\n" + "\n".join(lines) + "\n-->\n"
    return comment + body_html.strip() + "\n"


def write_paste_html(
    title: str,
    body_html: str,
    *,
    category: str = "",
    url: str = "",
    when: datetime | None = None,
    directory: Path | None = None,
) -> Path:
    folder = directory or PASTE_DIR
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / paste_filename(title, when)
    path.write_text(
        render_paste_document(title, body_html, category=category, url=url),
        encoding="utf-8",
    )
    return path


def export_batch_html(db: Any, batch: Any, *, directory: Path | None = None) -> list[Path]:
    """Write one paste file per post that already has HTML."""
    from autopost_api.db.models import Post

    paths: list[Path] = []
    for item in getattr(batch, "items", []) or []:
        post_id = getattr(item, "post_id", None)
        if not post_id:
            continue
        post = db.get(Post, post_id)
        if post is None:
            continue
        html = getattr(post, "body_html", None)
        if not isinstance(html, str) or not html.strip():
            continue
        category = ""
        category_row = getattr(post, "category", None)
        if category_row is not None:
            category = str(getattr(category_row, "name", "") or "")
        published_at = getattr(post, "published_at", None)
        if not isinstance(published_at, datetime):
            published_at = None
        paths.append(
            write_paste_html(
                str(getattr(post, "title", "") or "글"),
                html,
                category=category,
                when=published_at,
                directory=directory,
            )
        )
    return paths
