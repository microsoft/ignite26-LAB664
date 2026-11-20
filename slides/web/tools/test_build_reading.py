import copy
import json
import unittest

from build_reading import SITE, load_deck, render_presentation, render_reading, validate


class ReadingEditionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.editions = {}
        for directory in sorted(path.parent for path in SITE.glob("*/reading.json")):
            slug = directory.name
            original = (directory / "presentation.html").read_text(encoding="utf-8")
            content = json.loads((directory / "reading.json").read_text(encoding="utf-8"))
            cls.editions[slug] = (directory, original, content, load_deck(original))

    def test_every_source_slide_and_video_is_accounted_for(self):
        for slug, (directory, _, content, deck) in self.editions.items():
            with self.subTest(slug=slug):
                validate(content, deck, directory)
                html = render_reading(content, deck)
                for section in content["sections"]:
                    for number in section["slides"]:
                        self.assertIn(f'id="slide-{number}"', html)
                self.assertEqual(html.count("<video controls"), len(deck.media))
                self.assertNotIn("autoplay", html)

    def test_missing_slide_or_video_is_rejected(self):
        directory, _, content, deck = self.editions["lab664"]
        missing_slide = copy.deepcopy(content)
        missing_slide["sections"][1]["slides"] = []
        with self.assertRaisesRegex(ValueError, "Every source slide"):
            validate(missing_slide, deck, directory)
        missing_video = copy.deepcopy(content)
        missing_video["sections"][0]["videos"] = []
        with self.assertRaisesRegex(ValueError, "Every original video"):
            validate(missing_video, deck, directory)

    def test_cannot_drop_a_slide_with_notes(self):
        directory, _, content, deck = self.editions["lab664"]
        modified = copy.deepcopy(content)
        removed = modified["sections"].pop(1)
        modified["omitted_slides"].extend(removed["slides"])
        with self.assertRaisesRegex(ValueError, "Cannot omit slide 3"):
            validate(modified, deck, directory)

    def test_authored_text_is_escaped(self):
        _, _, content, deck = self.editions["lab664"]
        modified = copy.deepcopy(content)
        modified["sections"][0]["paragraphs"] = ['Text with <script>alert("x")</script> & more.']
        html = render_reading(modified, deck)
        self.assertIn("&lt;script&gt;alert(&quot;x&quot;)&lt;/script&gt; &amp; more.", html)
        self.assertNotIn('<script>alert("x")</script>', html)

    def test_slide_images_open_in_a_lightbox_with_a_direct_image_fallback(self):
        for slug, (_, _, content, deck) in self.editions.items():
            with self.subTest(slug=slug):
                html = render_reading(content, deck)
                self.assertIn('<dialog class="slide-lightbox" aria-labelledby="lightbox-title">', html)
                self.assertIn('<form method="dialog">', html)
                self.assertIn("Back to article", html)
                self.assertIn('aria-pressed="false">Zoom in', html)
                self.assertNotIn('src="assets/thumbs/', html)
                for section in content["sections"]:
                    for number in section["slides"]:
                        self.assertIn(f'href="assets/slides/{number:02}.png" data-slide="{number}"', html)
                        self.assertIn(f'src="assets/slides/{number:02}.png"', html)
                        self.assertIn(f'href="presentation.html#/{number}"', html)

    def test_presentation_links_are_idempotent_and_preserve_notes(self):
        for slug, (_, original, content, deck) in self.editions.items():
            with self.subTest(slug=slug):
                updated = render_presentation(original, content)
                self.assertEqual(render_presentation(updated, content), updated)
                self.assertEqual(load_deck(updated).data, deck.data)
                self.assertEqual(updated.count('aria-label="Reading and downloads"'), 1)
                self.assertIn(content["download_url"], updated)


if __name__ == "__main__":
    unittest.main()
