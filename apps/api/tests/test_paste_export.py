import unittest
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock

from autopost_api.services.paste_export import export_batch_html, paste_filename, render_paste_document, write_paste_html


class PasteExportTests(unittest.TestCase):
    def test_filename_uses_seoul_time_and_strips_unsafe_characters(self):
        when = datetime(2026, 10, 6, 21, 7, tzinfo=timezone.utc)
        name = paste_filename('편의점 레시피: 한 끼/두 끼', when)
        self.assertTrue(name.startswith("20261007-0607-"))
        self.assertNotIn("/", name)
        self.assertNotIn(":", name)
        self.assertTrue(name.endswith(".html"))

    def test_document_keeps_body_and_title_comment(self):
        text = render_paste_document("도시락", "<p>본문</p>", category="음식·요리", url="https://example.blogspot.com/1")
        self.assertIn("제목: 도시락", text)
        self.assertIn("카테고리: 음식·요리", text)
        self.assertNotIn("블로거:", text)
        self.assertNotIn("example.blogspot.com", text)
        self.assertIn("<p>본문</p>", text)
        self.assertTrue(text.strip().endswith("</p>"))

    def test_write_and_skip_missing_html(self, tmp_path=None):
        folder = self._folder()
        path = write_paste_html("정리", "<p>본문</p>", category="생활·정리", directory=folder)
        self.assertEqual(path.parent, folder)
        self.assertIn("<p>본문</p>", path.read_text(encoding="utf-8"))

        post = SimpleNamespace(title="정리", body_html="<p>본문</p>", category=SimpleNamespace(name="생활·정리"), published_at=None)
        empty = SimpleNamespace(title="빈 글", body_html=MagicMock(), category=None, published_at=None)
        batch = SimpleNamespace(items=[SimpleNamespace(post_id="a"), SimpleNamespace(post_id="b")])
        db = MagicMock()
        db.get.side_effect = lambda model, key: post if key == "a" else empty
        written = export_batch_html(db, batch, directory=folder)
        self.assertEqual(len(written), 1)

    def _folder(self):
        import tempfile
        from pathlib import Path

        return Path(tempfile.mkdtemp())


if __name__ == "__main__":
    unittest.main()
