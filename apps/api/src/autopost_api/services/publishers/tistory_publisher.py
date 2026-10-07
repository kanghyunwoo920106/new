"""Tistory official write API ended in February 2024.

Notice: https://notice.tistory.com/2664
New access tokens cannot be issued. This publisher does not call the old
write endpoint and does not use a browser or cookie session.
"""

from __future__ import annotations

from typing import Any

SHUTDOWN_MESSAGE = (
    "티스토리 Open API 글쓰기는 2024년 2월에 종료되어 자동 발행할 수 없습니다. "
    "글은 티스토리 에디터에서 직접 작성해야 합니다."
)


class TistoryPublisher:
    channel_code = "tistory"

    def publish(self, post: Any) -> dict:
        del post
        raise RuntimeError(SHUTDOWN_MESSAGE)
