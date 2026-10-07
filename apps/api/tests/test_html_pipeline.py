import unittest
from unittest.mock import patch

from autopost_api.config import settings
from autopost_api.integrations.claude_client import pick_voice_styles
from autopost_api.services import autopilot
from autopost_api.services.html_pipeline import process_blog_html


class HtmlPipelineTests(unittest.TestCase):
    def test_replaces_image_link_and_map_and_drops_failures(self):
        def images(query: str):
            if "missing" in query:
                return None
            return {
                "url": "https://images.example/photo.jpg",
                "alt": query,
                "artist": "Ada",
                "source_name": "Unsplash",
                "source_url": "https://unsplash.com/photos/abc",
            }

        def links(description: str):
            if "위키" in description:
                return "https://ko.wikipedia.org/wiki/Hoi_An"
            return None

        html = process_blog_html(
            """
            [IMAGE: hoi an lantern street]
            <p>골목을 걷다가 그냥 앉았다. 근데 이게 포인트.</p>
            <h2>밤에 더 낫더라 🏮</h2>
            <p>[IMAGE: missing photo]</p>
            <p>공식 안내는 [LINK: 호이안 | 호이안 위키] 여기.</p>
            <p>없는 링크는 [LINK: 비밀 지도 | 존재하지 않는 사이트] 이렇게.</p>
            [MAP: 호이안 올드타운 베트남]
            <p>가 볼 만함
            """,
            image_finder=images,
            link_finder=links,
        )
        self.assertIn("https://images.example/photo.jpg", html)
        self.assertIn("width:100%", html)
        self.assertIn('target="_blank"', html)
        self.assertIn("https://ko.wikipedia.org/wiki/Hoi_An", html)
        self.assertIn("비밀 지도", html)
        self.assertNotIn("존재하지 않는 사이트", html)
        self.assertIn("maps?q=", html)
        self.assertIn("output=embed", html)
        self.assertNotIn("[IMAGE:", html)
        self.assertNotIn("[LINK:", html)
        self.assertNotIn("[MAP:", html)
        self.assertIn("font-size:18px", html)
        self.assertTrue(html.rstrip().endswith("</p></div>") or "</p>" in html)

    def test_voice_stays_on_the_guide_style(self):
        voices = pick_voice_styles()
        self.assertEqual(voices, ["차분한 설명체. 어미는 ~예요, ~해요, ~합니다, ~세요만 쓴다."])

    def test_dry_run_does_not_publish(self):
        saved = settings.autopilot_dry_run
        saved_path = settings.autopilot_dry_run_path
        settings.autopilot_dry_run = False
        try:
            with (
                patch("autopost_api.db.models.Base"),
                patch("autopost_api.db.seed.seed_if_empty"),
                patch("autopost_api.db.session.SessionLocal", return_value=unittest.mock.MagicMock()),
                patch("autopost_api.db.session.engine"),
                patch("autopost_api.services.dry_run.run_dry_run", return_value="/tmp/post.html") as dry_run,
                patch.object(autopilot, "run_autopilot") as run_autopilot,
            ):
                autopilot.main(["--dry-run", "--output", "data/dry-run/sample.html"])
            self.assertEqual(settings.autopilot_dry_run_path, "data/dry-run/sample.html")
            dry_run.assert_called_once()
            run_autopilot.assert_not_called()
        finally:
            settings.autopilot_dry_run = saved
            settings.autopilot_dry_run_path = saved_path


if __name__ == "__main__":
    unittest.main()
