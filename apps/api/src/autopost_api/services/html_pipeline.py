"""Turn model HTML into a Blogger-ready fragment.

Placeholders are replaced here. A failed lookup removes only that placeholder.
"""

from __future__ import annotations

import html
import logging
import re
from collections.abc import Callable
from html.parser import HTMLParser
from urllib.parse import quote

import httpx

from autopost_api.config import settings

logger = logging.getLogger("autopost.html")

USER_AGENT = "LumenPost/0.1 (Korean blog; open images and real reference links only)"
IMAGE_RE = re.compile(r"\[IMAGE:\s*([^\]]+?)\s*\]", re.IGNORECASE)
LINK_RE = re.compile(r"\[LINK:\s*([^|\]]+?)\s*\|\s*([^\]]+?)\s*\]", re.IGNORECASE)
MAP_RE = re.compile(r"\[MAP:\s*([^\]]+?)\s*\]", re.IGNORECASE)
PLACEHOLDER_RE = re.compile(r"\[(?:IMAGE|LINK|MAP):[^\]]*\]", re.IGNORECASE)
MAX_IMAGES = 5

TAG_STYLES = {
    "h2": (
        "margin:2.15em 0 0.7em; padding-bottom:0.28em; font-size:26px; line-height:1.4; "
        "letter-spacing:-0.03em; font-weight:700; color:#1c2b28; border-bottom:1px solid #e6efec;"
    ),
    "h3": (
        "margin:1.6em 0 0.45em; font-size:21px; line-height:1.45; letter-spacing:-0.02em; "
        "font-weight:700; color:#243833;"
    ),
    "p": (
        "margin:0 0 1.3em; font-size:18px; line-height:1.95; letter-spacing:0.012em; "
        "color:#2c3835; word-break:keep-all;"
    ),
    "ul": "margin:0.4em 0 1.4em; padding-left:1.25em;",
    "ol": "margin:0.4em 0 1.4em; padding-left:1.35em;",
    "li": "margin:0.45em 0; font-size:18px; line-height:1.85; letter-spacing:0.01em; color:#2c3835;",
    "blockquote": (
        "margin:1.4em 0 1.6em; padding:0.9em 1.1em; background:#f4faf7; "
        "border-left:4px solid #1f8a72; border-radius:10px; font-size:17px; line-height:1.8; color:#243833;"
    ),
    "strong": "font-weight:700; color:#145e52;",
    "b": "font-weight:700; color:#145e52;",
    "mark": "background:#fff3bf; padding:0 0.15em;",
    "hr": "border:0; border-top:1px solid #e6efec; margin:1.8em 0;",
}
WRAPPER_STYLE = (
    "max-width:720px; margin:0 auto; font-family:Apple SD Gothic Neo,Malgun Gothic,Noto Sans KR,sans-serif; "
    "font-size:18px; line-height:1.95; letter-spacing:0.012em; color:#2c3835; word-break:keep-all;"
)
VOID_TAGS = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source", "track", "wbr"}

ImageFinder = Callable[[str], dict[str, str] | None]
LinkFinder = Callable[[str], str | None]


def _allowed_char(ch: str) -> bool:
    code = ord(ch)
    if ch in "\n\t":
        return True
    if code < 32 or 0xE000 <= code <= 0xF8FF:
        return False
    if code <= 0x024F:
        return True
    if 0x2000 <= code <= 0x2BFF or 0x3000 <= code <= 0x303F:
        return True
    if 0x3130 <= code <= 0x318F or 0xAC00 <= code <= 0xD7AF:
        return True
    if 0xFE00 <= code <= 0xFE0F or 0x1F000 <= code <= 0x1FAFF:
        return True
    return False


def blogger_safe(text: str) -> str:
    return "".join(ch for ch in text if _allowed_char(ch))


def _plain(value: str) -> str:
    text = re.sub(r"<[^>]+>", "", value or "")
    return html.unescape(re.sub(r"\s+", " ", text)).strip()


def reference_catalog() -> list[tuple[str, str]]:
    items: list[tuple[str, str]] = []
    for part in re.split(r"[\n;]", settings.reference_links):
        if "|" not in part:
            continue
        label, url = part.split("|", 1)
        url = url.strip()
        label = label.strip()
        if label and (url.startswith("https://") or url.startswith("http://")):
            items.append((label, url))
    return items


def _catalog_url(description: str) -> str | None:
    needle = description.casefold().strip()
    if not needle:
        return None
    for label, url in reference_catalog():
        hay = label.casefold()
        if needle in hay or hay in needle:
            return url
    return None


def _brave_url(description: str) -> str | None:
    key = settings.brave_search_api_key.strip()
    if not key:
        return None
    response = httpx.get(
        "https://api.search.brave.com/res/v1/web/search",
        params={"q": description, "count": 3},
        headers={"X-Subscription-Token": key, "Accept": "application/json", "User-Agent": USER_AGENT},
        timeout=20,
    )
    if response.status_code >= 400:
        logger.warning("brave search failed status=%s", response.status_code)
        return None
    results = ((response.json().get("web") or {}).get("results")) or []
    for item in results:
        url = str(item.get("url") or "")
        if url.startswith("https://") or url.startswith("http://"):
            return url
    return None


def _wikipedia_url(description: str) -> str | None:
    response = httpx.get(
        "https://ko.wikipedia.org/w/api.php",
        params={"action": "opensearch", "search": description, "limit": 1, "namespace": 0, "format": "json"},
        headers={"User-Agent": USER_AGENT},
        timeout=15,
    )
    if response.status_code >= 400:
        return None
    payload = response.json()
    if not isinstance(payload, list) or len(payload) < 4 or not payload[3]:
        return None
    title = str(payload[1][0]) if len(payload) > 1 and payload[1] else ""
    tokens = [token for token in re.split(r"\s+", description) if len(token) >= 2]
    if tokens and not any(token.casefold() in title.casefold() for token in tokens):
        return None
    url = str(payload[3][0])
    if url.startswith("https://") or url.startswith("http://"):
        return url
    return None


def find_reference_url(description: str) -> str | None:
    """Return a real URL from the user list or a search API. Never invent one."""
    for finder in (_catalog_url, _brave_url, _wikipedia_url):
        try:
            url = finder(description)
        except Exception:
            logger.exception("link lookup failed")
            url = None
        if url:
            return url
    return None


def _unsplash_image(query: str) -> dict[str, str] | None:
    key = settings.unsplash_access_key.strip()
    if not key:
        return None
    response = httpx.get(
        "https://api.unsplash.com/search/photos",
        params={"query": query, "per_page": 1, "orientation": "landscape"},
        headers={"Authorization": f"Client-ID {key}", "Accept-Version": "v1", "User-Agent": USER_AGENT},
        timeout=20,
    )
    if response.status_code >= 400:
        logger.warning("unsplash search failed status=%s", response.status_code)
        return None
    results = response.json().get("results") or []
    if not results:
        return None
    photo = results[0]
    url = ((photo.get("urls") or {}).get("regular")) or ""
    if not url:
        return None
    user = photo.get("user") or {}
    return {
        "url": url,
        "alt": _plain(photo.get("alt_description") or query),
        "artist": _plain(user.get("name") or ""),
        "source_name": "Unsplash",
        "source_url": str((photo.get("links") or {}).get("html") or user.get("links", {}).get("html") or ""),
    }


def _pexels_image(query: str) -> dict[str, str] | None:
    key = settings.pexels_api_key.strip()
    if not key:
        return None
    response = httpx.get(
        "https://api.pexels.com/v1/search",
        params={"query": query, "per_page": 1, "orientation": "landscape"},
        headers={"Authorization": key, "User-Agent": USER_AGENT},
        timeout=20,
    )
    if response.status_code >= 400:
        logger.warning("pexels search failed status=%s", response.status_code)
        return None
    photos = response.json().get("photos") or []
    if not photos:
        return None
    photo = photos[0]
    url = ((photo.get("src") or {}).get("large")) or ""
    if not url:
        return None
    return {
        "url": url,
        "alt": _plain(photo.get("alt") or query),
        "artist": _plain(photo.get("photographer") or ""),
        "source_name": "Pexels",
        "source_url": str(photo.get("url") or photo.get("photographer_url") or ""),
    }


def find_stock_image(query: str) -> dict[str, str] | None:
    for finder in (_unsplash_image, _pexels_image):
        try:
            image = finder(query)
        except Exception:
            logger.exception("image lookup failed query=%s", query)
            image = None
        if image:
            return image
    return None


def _figure(image: dict[str, str], *, hero: bool) -> str:
    alt = html.escape(image.get("alt") or "", quote=True)
    src = html.escape(image["url"], quote=True)
    credit_bits = [bit for bit in (image.get("artist") or "", image.get("source_name") or "") if bit]
    credit = " · ".join(credit_bits)
    source = image.get("source_url") or ""
    if source.startswith("http"):
        credit_html = (
            f'<a href="{html.escape(source, quote=True)}" target="_blank" rel="noopener" '
            f'style="color:#6d7b77;">{html.escape(credit or "출처")}</a>'
        )
    else:
        credit_html = html.escape(credit)
    margin = "0 0 1.8em" if hero else "1.7em 0 1.9em"
    return (
        f'<figure style="margin:{margin};">'
        f'<img src="{src}" alt="{alt}" style="width:100%; height:auto; border-radius:16px; display:block;">'
        f'<figcaption style="margin-top:0.55em; font-size:13px; line-height:1.55; letter-spacing:0; color:#6d7b77;">'
        f"{credit_html}</figcaption></figure>"
    )


def _link(anchor: str, url: str) -> str:
    return (
        f'<a href="{html.escape(url, quote=True)}" target="_blank" rel="noopener" '
        f'style="color:#145e52;">{html.escape(anchor.strip())}</a>'
    )


def _map_iframe(place: str) -> str:
    src = "https://www.google.com/maps?q=" + quote(place.strip()) + "&output=embed"
    title = html.escape(place.strip(), quote=True)
    return (
        '<div style="margin:1.6em 0 1.8em;">'
        f'<iframe title="{title}" src="{html.escape(src, quote=True)}" loading="lazy" '
        'referrerpolicy="no-referrer-when-downgrade" '
        'style="width:100%; height:320px; border:0; border-radius:16px;"></iframe>'
        "</div>"
    )


def _replace_token(document: str, pattern: re.Pattern[str], block: bool, render: Callable[[re.Match[str]], str]) -> str:
    if block:
        wrapped = re.compile(
            r"<p\b[^>]*>\s*" + pattern.pattern + r"\s*</p>",
            pattern.flags,
        )
        document = wrapped.sub(render, document)
    return pattern.sub(render, document)


def _style_tags(document: str) -> str:
    for tag, style in TAG_STYLES.items():
        matcher = re.compile(rf"<{tag}(\s[^>]*)?>", re.IGNORECASE)

        def replace(match: re.Match[str], style: str = style, tag: str = tag) -> str:
            attrs = match.group(1) or ""
            if re.search(r"\sstyle=", attrs, re.IGNORECASE):
                return match.group(0)
            return f'<{tag} style="{style}"{attrs}>'

        document = matcher.sub(replace, document)
    return document


class _TagStack(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=False)
        self.stack: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() not in VOID_TAGS:
            self.stack.append(tag.lower())

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag in VOID_TAGS or tag not in self.stack:
            return
        while self.stack and self.stack[-1] != tag:
            self.stack.pop()
        if self.stack:
            self.stack.pop()


def _close_open_tags(document: str) -> str:
    parser = _TagStack()
    try:
        parser.feed(document)
        parser.close()
    except Exception:
        logger.exception("html parse failed; leaving tags as generated")
        return document
    if not parser.stack:
        return document
    return document + "".join(f"</{tag}>" for tag in reversed(parser.stack))


def _promote_hero(document: str) -> str:
    match = re.search(r"<figure\b.*?</figure>", document, re.DOTALL | re.IGNORECASE)
    if not match or not document[: match.start()].strip():
        return document
    return match.group(0) + "\n" + (document[: match.start()] + document[match.end() :]).strip()


def _strip_document_shell(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:html)?\s*", "", text, flags=re.IGNORECASE)
        text = re.sub(r"\s*```$", "", text)
    text = re.sub(r"(?is)^<html[^>]*>.*?<body[^>]*>", "", text)
    text = re.sub(r"(?is)</body>\s*</html>\s*$", "", text)
    text = re.sub(r"(?is)^<body[^>]*>|</body>$", "", text)
    return text.strip()


def process_blog_html(
    raw_html: str,
    *,
    image_finder: ImageFinder | None = None,
    link_finder: LinkFinder | None = None,
) -> str:
    """Replace placeholders, drop failures, and return styled body HTML."""
    images = image_finder or find_stock_image
    links = link_finder or find_reference_url
    document = blogger_safe(_strip_document_shell(raw_html))
    used = 0
    seen: set[str] = set()

    def render_image(match: re.Match[str]) -> str:
        nonlocal used
        if used >= MAX_IMAGES:
            return ""
        query = match.group(1).strip()
        try:
            image = images(query)
        except Exception:
            logger.exception("image placeholder failed")
            image = None
        if not image or image.get("url") in seen:
            return ""
        seen.add(image["url"])
        used += 1
        if not image.get("alt"):
            image["alt"] = query
        return _figure(image, hero=used == 1)

    def render_link(match: re.Match[str]) -> str:
        anchor = match.group(1).strip()
        description = match.group(2).strip()
        try:
            url = links(description)
        except Exception:
            logger.exception("link placeholder failed")
            url = None
        if not url:
            return html.escape(anchor)
        return _link(anchor, url)

    def render_map(match: re.Match[str]) -> str:
        place = match.group(1).strip()
        if not place:
            return ""
        return _map_iframe(place)

    document = _replace_token(document, IMAGE_RE, True, render_image)
    document = _replace_token(document, MAP_RE, True, render_map)
    document = _replace_token(document, LINK_RE, False, render_link)
    document = PLACEHOLDER_RE.sub("", document)
    document = _promote_hero(document)
    document = _style_tags(document)
    document = _close_open_tags(document)
    return f'<div style="{WRAPPER_STYLE}">{document}</div>'
