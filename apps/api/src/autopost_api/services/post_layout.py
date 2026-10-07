from __future__ import annotations

import html
import logging
import re
from typing import Callable

import httpx
import markdown as md

logger = logging.getLogger("autopost.layout")

IMAGE_MARKER = re.compile(r"\[\[image:\s*([^|\]]+?)(?:\s*\|\s*([^\]]+?))?\s*\]\]")
COMMONS_API = "https://commons.wikimedia.org/w/api.php"
USER_AGENT = "LumenPost/0.1 (Korean blog illustrations; openly licensed images only)"

TAG_STYLES = {
    "h2": (
        "margin:2.15em 0 0.7em; padding-bottom:0.28em; "
        "font-size:26px; line-height:1.4; letter-spacing:-0.03em; font-weight:700; "
        "color:#1c2b28; border-bottom:1px solid #e6efec;"
    ),
    "h3": (
        "margin:1.6em 0 0.45em; font-size:21px; line-height:1.45; "
        "letter-spacing:-0.02em; font-weight:700; color:#243833;"
    ),
    "p": (
        "margin:0 0 1.3em; font-size:18px; line-height:1.95; letter-spacing:0.012em; "
        "color:#2c3835; word-break:keep-all;"
    ),
    "ul": "margin:0.4em 0 1.4em; padding-left:1.25em;",
    "ol": "margin:0.4em 0 1.4em; padding-left:1.35em;",
    "li": "margin:0.45em 0; font-size:18px; line-height:1.85; letter-spacing:0.01em; color:#2c3835;",
    "blockquote": (
        "margin:1.4em 0 1.6em; padding:0.9em 1.1em; "
        "background:#f4faf7; border-left:4px solid #1f8a72; border-radius:10px; "
        "font-size:17px; line-height:1.8; color:#243833;"
    ),
    "strong": "font-weight:700; color:#145e52;",
}

WRAPPER_STYLE = (
    "max-width:720px; margin:0 auto; "
    "font-family:'Apple SD Gothic Neo','Malgun Gothic','Noto Sans KR',sans-serif; "
    "font-size:18px; line-height:1.95; letter-spacing:0.012em; color:#2c3835; word-break:keep-all;"
)


ImageFinder = Callable[[str], dict[str, str] | None]


def _plain(value: str) -> str:
    text = re.sub(r"<[^>]+>", "", value or "")
    return html.unescape(re.sub(r"\s+", " ", text)).strip()


def find_commons_image(query: str) -> dict[str, str] | None:
    """Return one openly licensed Wikimedia Commons photo for a search query."""
    query = query.strip()
    if not query:
        return None
    # Long scene descriptions often miss. Try the full phrase, then fewer words.
    words = query.split()
    attempts = [query]
    if len(words) > 4:
        attempts.append(" ".join(words[:4]))
    if len(words) > 2:
        attempts.append(" ".join(words[:2]))
    pages: dict = {}
    for attempt in attempts:
        response = httpx.get(
            COMMONS_API,
            params={
                "action": "query",
                "format": "json",
                "generator": "search",
                "gsrsearch": f"{attempt} filetype:bitmap",
                "gsrnamespace": 6,
                "gsrlimit": 8,
                "prop": "imageinfo",
                "iiprop": "url|mime|extmetadata|size",
                "iiurlwidth": 1200,
            },
            headers={"User-Agent": USER_AGENT},
            timeout=20,
        )
        if response.status_code >= 400:
            logger.warning("commons search failed status=%s", response.status_code)
            continue
        pages = (response.json().get("query") or {}).get("pages") or {}
        if pages:
            break
    for page in pages.values():
        info = (page.get("imageinfo") or [None])[0] or {}
        mime = str(info.get("mime") or "")
        if mime not in {"image/jpeg", "image/png", "image/webp"}:
            continue
        width = int(info.get("thumbwidth") or info.get("width") or 0)
        if width and width < 320:
            continue
        url = info.get("thumburl") or info.get("url")
        if not url:
            continue
        meta = info.get("extmetadata") or {}
        return {
            "url": url,
            "license": _plain((meta.get("LicenseShortName") or {}).get("value") or ""),
            "artist": _plain((meta.get("Artist") or {}).get("value") or ""),
        }
    return None


def _figure(image: dict[str, str], caption: str) -> str:
    credit_bits = [bit for bit in (image.get("artist") or "", image.get("license") or "") if bit]
    credit = " · ".join(credit_bits)
    caption_html = html.escape(caption.strip()) if caption.strip() else ""
    credit_html = html.escape(credit)
    tail = " · ".join(bit for bit in (caption_html, credit_html) if bit)
    return (
        '<figure style="margin:1.7em 0 1.9em;">'
        f'<img src="{html.escape(image["url"], quote=True)}" alt="{html.escape(caption.strip(), quote=True)}" '
        'style="width:100%; height:auto; border-radius:16px; display:block;">'
        f'<figcaption style="margin-top:0.55em; font-size:13px; line-height:1.55; '
        f'letter-spacing:0; color:#6d7b77;">{tail}</figcaption>'
        "</figure>"
    )


def _style_tags(document: str) -> str:
    for tag, style in TAG_STYLES.items():
        pattern = re.compile(rf"<{tag}(\s[^>]*)?>", re.IGNORECASE)

        def replace(match: re.Match[str], style: str = style, tag: str = tag) -> str:
            attrs = match.group(1) or ""
            if re.search(r"\sstyle=", attrs, re.IGNORECASE):
                return match.group(0)
            return f'<{tag} style="{style}"{attrs}>'

        document = pattern.sub(replace, document)
    return document


def ensure_image_markers(body: str, queries: list | None) -> str:
    """Add up to two photo slots when the draft forgot them."""
    existing = len(IMAGE_MARKER.findall(body))
    if existing >= 2:
        return body
    markers: list[str] = []
    for item in queries or []:
        if not isinstance(item, dict):
            continue
        query = str(item.get("query") or "").strip()
        caption = str(item.get("caption") or query).strip()
        if query:
            markers.append(f"[[image: {query} | {caption}]]")
        if existing + len(markers) >= 2:
            break
    if not markers:
        return body
    headings = list(re.finditer(r"^## .+$", body, re.MULTILINE))
    if len(headings) < 2:
        return body.rstrip() + "\n\n" + "\n\n".join(markers) + "\n"
    slots = [headings[index].start() for index in (1, 2) if index < len(headings)]
    result = body
    for position, marker in zip(reversed(slots), reversed(markers[: len(slots)])):
        result = result[:position] + marker + "\n\n" + result[position:]
    return result


def _allowed_char(ch: str) -> bool:
    code = ord(ch)
    if ch in "\n\t":
        return True
    if code < 32 or 0xE000 <= code <= 0xF8FF:
        return False
    # Hangul, common punctuation, and emoji stay. Rare Latin extensions do not.
    if code <= 0x024F:
        return True
    if 0x2000 <= code <= 0x206F or 0x2070 <= code <= 0x2BFF:
        return True
    if 0x3000 <= code <= 0x303F or 0x3130 <= code <= 0x318F or 0xAC00 <= code <= 0xD7AF:
        return True
    if 0xFE00 <= code <= 0xFE0F or 0x1F000 <= code <= 0x1FAFF:
        return True
    return False


def _blogger_safe(text: str) -> str:
    """Drop characters that make the Blogger API reject an otherwise valid post."""
    return "".join(ch for ch in text if _allowed_char(ch))


def render_readable_html(
    body_markdown: str,
    *,
    image_finder: ImageFinder = find_commons_image,
    max_images: int = 3,
) -> str:
    """Turn markdown into spaced HTML with a few openly licensed photos."""
    used = 0
    seen_urls: set[str] = set()

    def replace_marker(match: re.Match[str]) -> str:
        nonlocal used
        query = match.group(1).strip()
        caption = (match.group(2) or query).strip()
        if used >= max_images:
            return ""
        try:
            image = image_finder(query)
        except Exception:
            logger.exception("image lookup failed query=%s", query)
            image = None
        if not image or image["url"] in seen_urls:
            return ""
        seen_urls.add(image["url"])
        used += 1
        return _figure(image, caption)

    marked = IMAGE_MARKER.sub(replace_marker, _blogger_safe(body_markdown))
    body_html = md.markdown(marked, extensions=["extra", "sane_lists"])
    body_html = _style_tags(body_html)
    return f'<div style="{WRAPPER_STYLE}">{body_html}</div>'
