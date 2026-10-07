import unittest
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

from autopost_api.config import settings
from autopost_api.services.publishers.blogger_publisher import BloggerPublisher
from autopost_api.services.publishers.tistory_publisher import TistoryPublisher


class _Tag:
    def __init__(self, tag: str):
        self.tag = tag


class _Post:
    def __init__(self):
        self.title = "정리 시작"
        self.body_html = "<p>본문</p>"
        self.body_markdown = "본문"
        self.excerpt = "요약"
        self.status = "ready"
        self.published_at = None
        self.seo_tags = [_Tag("정리")]


class ExternalPublisherTests(unittest.TestCase):
    def setUp(self):
        self._saved = {
            "tistory_access_token": settings.tistory_access_token,
            "tistory_blog_name": settings.tistory_blog_name,
            "blogger_blog_id": settings.blogger_blog_id,
            "blogger_access_token": settings.blogger_access_token,
            "google_client_id": settings.google_client_id,
            "google_client_secret": settings.google_client_secret,
            "google_refresh_token": settings.google_refresh_token,
        }

    def tearDown(self):
        for key, value in self._saved.items():
            setattr(settings, key, value)

    def test_tistory_write_is_refused_after_api_shutdown(self):
        settings.tistory_access_token = "token"
        settings.tistory_blog_name = "lumen"
        with patch("httpx.post") as post:
            with self.assertRaises(RuntimeError) as raised:
                TistoryPublisher().publish(_Post())
        post.assert_not_called()
        self.assertIn("2024년 2월", str(raised.exception))
        self.assertFalse(settings.channel_configured("tistory"))

    def test_blogger_refreshes_token_then_writes(self):
        settings.blogger_blog_id = "123"
        settings.google_client_id = "cid"
        settings.google_client_secret = "sec"
        settings.google_refresh_token = "refresh"
        settings.blogger_access_token = ""
        token_response = MagicMock()
        token_response.status_code = 200
        token_response.json.return_value = {"access_token": "ya29"}
        write_response = MagicMock()
        write_response.status_code = 200
        write_response.json.return_value = {"id": "p1", "url": "https://www.blogger.com/p1"}

        def fake_post(url, **kwargs):
            if "oauth2.googleapis.com" in url:
                return token_response
            return write_response

        with patch("autopost_api.services.publishers.blogger_publisher.httpx.post", side_effect=fake_post) as post:
            result = BloggerPublisher().publish(_Post())
        self.assertEqual(result["channel"], "blogger")
        self.assertEqual(result["url"], "https://www.blogger.com/p1")
        write_call = post.call_args_list[1]
        self.assertIn("/blogs/123/posts", write_call.args[0])
        self.assertEqual(write_call.kwargs["headers"]["Authorization"], "Bearer ya29")
        self.assertEqual(write_call.kwargs["json"]["labels"], ["정리"])

    def test_blogger_uses_the_topic_name_as_the_only_label(self):
        settings.blogger_blog_id = "123"
        settings.blogger_access_token = "token"
        settings.google_client_id = ""
        post = _Post()
        post.category = type("Category", (), {"name": "음식·요리"})()
        post.seo_tags = [_Tag("집밥"), type("CategoryTag", (), {"tag": "음식·요리", "tag_type": "category"})()]
        response = MagicMock()
        response.status_code = 200
        response.json.return_value = {"id": "p1", "url": "https://www.blogger.com/p1"}
        with patch("autopost_api.services.publishers.blogger_publisher.httpx.post", return_value=response) as post_call:
            BloggerPublisher().publish(post)
        self.assertEqual(post_call.call_args.kwargs["json"]["labels"], ["음식·요리"])

    def test_blogger_reads_latest_published_time(self):
        settings.blogger_blog_id = "123"
        settings.google_client_id = "cid"
        settings.google_client_secret = "sec"
        settings.google_refresh_token = "refresh"
        token_response = MagicMock()
        token_response.status_code = 200
        token_response.json.return_value = {"access_token": "ya29"}
        list_response = MagicMock()
        list_response.status_code = 200
        list_response.json.return_value = {"items": [{"published": "2026-10-07T12:08:00+09:00"}]}

        with (
            patch("autopost_api.services.publishers.blogger_publisher.httpx.post", return_value=token_response),
            patch("autopost_api.services.publishers.blogger_publisher.httpx.get", return_value=list_response) as get,
        ):
            published = BloggerPublisher().latest_published_at()
        self.assertEqual(published, datetime(2026, 10, 7, 3, 8, tzinfo=timezone.utc))
        self.assertIn("/blogs/123/posts", get.call_args.args[0])


if __name__ == "__main__":
    unittest.main()
