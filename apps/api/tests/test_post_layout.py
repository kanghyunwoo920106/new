import unittest

from autopost_api.services.post_layout import ensure_image_markers, render_readable_html


class PostLayoutTests(unittest.TestCase):
    def test_styles_body_and_inserts_an_open_image(self):
        def finder(query: str) -> dict[str, str]:
            self.assertIn("kitchen", query)
            return {"url": "https://example.com/fridge.jpg", "artist": "Ada", "license": "CC BY"}

        html = render_readable_html(
            "\n\n".join(
                [
                    "냉장고를 열면 눈이 편해져요. 🍅",
                    "[[image: open kitchen refrigerator vegetables | 칸이 보이는 냉장고]]",
                    "## 칸을 나누면",
                    "보이는 곳에 두면 먼저 먹게 됩니다.",
                ]
            ),
            image_finder=finder,
        )
        self.assertIn("font-size:18px", html)
        self.assertIn("letter-spacing:0.012em", html)
        self.assertIn("line-height:1.95", html)
        self.assertIn("https://example.com/fridge.jpg", html)
        self.assertIn("칸이 보이는 냉장고", html)
        self.assertIn("Ada", html)
        self.assertIn("🍅", html)
        self.assertNotIn("[[image:", html)

    def test_missing_markers_are_inserted_before_later_sections(self):
        body = ensure_image_markers(
            "## 처음\n\n도입입니다.\n\n## 다음\n\n본문입니다.\n\n## 끝\n\n마무리입니다.",
            [{"query": "sunny kitchen table", "caption": "식탁"}, {"query": "hands washing vegetables", "caption": "손질"}],
        )
        self.assertEqual(body.count("[[image:"), 2)
        self.assertLess(body.index("sunny kitchen"), body.index("## 다음"))

    def test_missing_image_does_not_leave_a_marker(self):
        html = render_readable_html(
            "짧은 문단입니다.\n\n[[image: missing photo | 없는 사진]]\n\n다음 문단입니다.",
            image_finder=lambda _query: None,
        )
        self.assertNotIn("[[image:", html)
        self.assertIn("다음 문단입니다.", html)


if __name__ == "__main__":
    unittest.main()
