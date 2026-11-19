"""Build the static reading editions with only the Python standard library."""

import argparse
from html import escape
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import struct


SITE = Path(__file__).resolve().parents[1]
LINKS_START = "<!-- READING-LINKS-START -->"
LINKS_END = "<!-- READING-LINKS-END -->"
LAB_URL = "https://github.com/microsoft/ignite26-LAB664/blob/main/instructions/lab.md"


class DeckParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.data: dict = {}
        self.media: dict[int, list[dict]] = {}
        self.slide: int | None = None
        self.capture = False
        self.parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple]) -> None:
        attributes = dict(attrs)
        if tag == "section" and "slide" in attributes.get("class", "").split():
            self.slide = int(attributes["data-n"])
        if tag == "video" and self.slide is not None:
            self.media.setdefault(self.slide, []).append(attributes)
        if tag == "script" and attributes.get("id") == "deck-data":
            self.capture = True
            self.parts = []

    def handle_data(self, data: str) -> None:
        if self.capture:
            self.parts.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == "section":
            self.slide = None
        if tag == "script" and self.capture:
            self.data = json.loads("".join(self.parts))
            self.capture = False


def load_deck(html: str) -> DeckParser:
    parser = DeckParser()
    parser.feed(html)
    if not parser.data.get("slides"):
        raise ValueError("The original presentation has no deck-data slides.")
    return parser


def validate(content: dict, deck: DeckParser, directory: Path) -> None:
    count = len(deck.data["slides"])
    covered = []
    ids = set()
    for section in content["sections"]:
        section_id = section["id"]
        if not re.fullmatch(r"[a-z][a-z0-9-]*", section_id) or section_id in ids:
            raise ValueError(f"Invalid or duplicate section ID: {section_id}")
        ids.add(section_id)
        covered.extend(section["slides"])
        for number in section["slides"]:
            if not (directory / "assets" / "thumbs" / f"{number:02}.jpg").is_file():
                raise ValueError(f"Missing original slide thumbnail: {number}")
            image = directory / "assets" / "slides" / f"{number:02}.png"
            if not image.is_file():
                raise ValueError(f"Missing full-resolution slide image: {image}. Run tools/export_slides.mjs.")
            with image.open("rb") as stream:
                header = stream.read(24)
            if (len(header) != 24 or header[:8] != b"\x89PNG\r\n\x1a\n" or
                    struct.unpack(">II", header[16:24]) != (2880, 1620)):
                raise ValueError(f"Expected a 2880 x 1620 PNG slide image: {image}")
        if section.get("visual") is not None:
            if section["visual"] not in section["slides"]:
                raise ValueError("A section visual must belong to that section.")
        for video in section.get("videos", []):
            number = video["slide"]
            if number not in section["slides"] or len(deck.media.get(number, [])) != 1:
                raise ValueError(f"Expected one video on section slide {number}.")
            for key in ("data-src", "data-poster"):
                resource = deck.media[number][0][key]
                if not (directory / resource).is_file():
                    raise ValueError(f"Missing video resource: {resource}")
    omitted = content["omitted_slides"]
    if sorted(covered + omitted) != list(range(1, count + 1)):
        raise ValueError("Every source slide must be mapped exactly once or explicitly omitted.")
    for number in omitted:
        if deck.data["slides"][number - 1]["notes"].strip():
            raise ValueError(f"Cannot omit slide {number}: it has speaker notes.")
    used_media = [
        video["slide"]
        for section in content["sections"]
        for video in section.get("videos", [])
    ]
    if sorted(used_media) != sorted(deck.media):
        raise ValueError("Every original video must appear once in the reading edition.")


def download(content: dict, css_class: str = "button") -> str:
    return (
        f'<a class="{css_class}" href="{escape(content["download_url"])}" download>'
        f'Download PowerPoint <span>({escape(content["download_size"])})</span></a>'
    )


def lab_cta() -> str:
    return f"""<aside class="lab-cta" aria-label="Start the hands-on lab">
<h2>Build it yourself</h2>
<p>Follow the step-by-step LAB664 exercises in your provisioned lab environment.</p>
<a class="button primary" href="{LAB_URL}">Open the lab instructions <span aria-hidden="true">&rarr;</span></a>
<p class="small">The guide uses credentials and placeholders supplied by the lab platform.</p>
</aside>"""


def figure(number: int, deck: DeckParser) -> str:
    title = " ".join(deck.data["slides"][number - 1]["title"].split())
    image = f"assets/slides/{number:02}.png"
    return f"""<figure class="original-figure">
<a class="slide-enlarge" href="{image}" data-slide="{number}" aria-label="Enlarge slide {number}: {escape(title)}">
<img src="{image}" alt="{escape(title)}" loading="lazy" decoding="async" width="2880" height="1620">
</a>
<figcaption><a class="slide-enlarge" href="{image}" data-slide="{number}">Enlarge slide {number}</a> <span aria-hidden="true">&middot;</span> <a href="presentation.html#/{number}">View animated slide</a></figcaption>
</figure>"""


def render_section(section: dict, deck: DeckParser) -> str:
    parts = [f'<section class="reading-section" id="{section["id"]}">']
    for number in section["slides"]:
        parts.append(f'<span class="slide-anchor" id="slide-{number}"></span>')
    parts.append(f'<h2>{escape(section["title"])}</h2>')
    parts.extend(f"<p>{escape(text)}</p>" for text in section["paragraphs"])
    for key, tag in (("bullets", "ul"), ("steps", "ol")):
        if key in section:
            parts.append(f"<{tag}>")
            parts.extend(f"<li>{escape(text)}</li>" for text in section[key])
            parts.append(f"</{tag}>")
    if "table" in section:
        table = section["table"]
        parts.append('<div class="table-wrap"><table><thead><tr>')
        parts.extend(f'<th scope="col">{escape(text)}</th>' for text in table["headers"])
        parts.append("</tr></thead><tbody>")
        for row in table["rows"]:
            parts.append("<tr>")
            parts.append(f'<th scope="row">{escape(row[0])}</th>')
            parts.extend(f"<td>{escape(text)}</td>" for text in row[1:])
            parts.append("</tr>")
        parts.append("</tbody></table></div>")
    if "closing" in section:
        parts.append(f'<p>{escape(section["closing"])}</p>')
    for video in section.get("videos", []):
        media = deck.media[video["slide"]][0]
        caption = escape(video["caption"])
        parts.append(f"""<figure class="demo">
<video controls playsinline preload="none" poster="{escape(media["data-poster"])}" aria-label="{caption}">
<source src="{escape(media["data-src"])}" type="video/mp4">
<a href="{escape(media["data-src"])}">Download this demo video</a>.
</video>
<figcaption>{caption} <a href="{escape(media["data-src"])}">Open video file</a></figcaption>
</figure>""")
    if "visual" in section:
        parts.append(figure(section["visual"], deck))
    for link in section.get("links", []):
        parts.append(f'<p class="resource-link"><a href="{escape(link["href"])}">{escape(link["label"])} <span aria-hidden="true">&rarr;</span></a></p>')
    if section.get("lab_cta"):
        parts.append(lab_cta())
    remaining = [n for n in section["slides"] if n != section.get("visual")]
    if remaining:
        label = "Original slide" if len(remaining) == 1 else "Original slides"
        numbers = ", ".join(str(n) for n in remaining)
        parts.append(f'<details class="source-slides"><summary>{label} {numbers}</summary>')
        parts.extend(figure(number, deck) for number in remaining)
        parts.append("</details>")
    parts.append("</section>")
    return "\n".join(parts)


def render_reading(content: dict, deck: DeckParser) -> str:
    title = escape(content["title"])
    session = escape(content["session"])
    introduction = "\n".join(f"<p>{escape(text)}</p>" for text in content["intro"])
    contents = "\n".join(
        f'<a href="#{section["id"]}">{escape(section["title"])}</a>'
        for section in content["sections"]
    )
    sections = "\n".join(render_section(section, deck) for section in content["sections"])
    lab_link = (
        f'<a class="button primary" href="{escape(content["lab_url"])}">Open the lab instructions <span aria-hidden="true">&rarr;</span></a>'
        if "lab_url" in content else ""
    )
    note = (
        f'<p class="edition-note">{escape(content["availability_note"])}</p>'
        if "availability_note" in content else ""
    )
    return f"""<!doctype html>
<!-- Generated by tools/build_reading.py. Edit reading.json, then rebuild. -->
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>{session}: {title}</title>
<meta name="description" content="{escape(content["description"])}">
<meta property="og:title" content="{session}: {title}">
<meta property="og:image" content="assets/thumbs/cover.jpg">
<meta name="theme-color" content="#0b0b12">
<link rel="stylesheet" href="../reading.css">
<script src="../reading.js" defer></script>
</head>
<body class="reading-view">
<a class="skip-link" href="#content">Skip to content</a>
<header class="reader-header">
<div class="header-inner">
<nav class="breadcrumbs" aria-label="Breadcrumb"><a href="../">Microsoft Ignite 2026</a><span aria-hidden="true">/</span><span>{session}</span></nav>
<h1>{title}</h1>
<div class="header-actions">
{download(content)}
{lab_link}
<a class="text-action" href="presentation.html">View animated slides <span aria-hidden="true">&nearr;</span></a>
</div>
<div class="introduction">{introduction}</div>
<p class="edition-label">Reading edition &middot; Adapted from the session's speaker notes</p>
</div>
</header>
<div class="reader-layout">
<aside class="reader-sidebar">
<details class="contents">
<summary>On this page</summary>
<nav aria-label="On this page">{contents}</nav>
</details>
</aside>
<main id="content" class="reader-content">
{note}
{sections}
<footer class="reader-footer">
<h2>Keep the original close</h2>
<p>The original slide layouts, animations, and unedited speaker notes are available in the presentation view.</p>
<div class="footer-actions">{download(content)}<a href="presentation.html">View animated slides</a></div>
<p class="small"><a href="https://github.com/microsoft/ignite26-LAB664/blob/main/slides/web/README.md#editorial-changes-to-review">Editorial changes to review</a> &middot; <a href="../">All sessions</a></p>
</footer>
</main>
</div>
<dialog class="slide-lightbox" aria-labelledby="lightbox-title">
<header class="lightbox-toolbar">
<h2 id="lightbox-title">Slide image</h2>
<form method="dialog"><button class="lightbox-close" autofocus>Back to article <span aria-hidden="true">&times;</span></button></form>
</header>
<div class="lightbox-viewport" tabindex="0" role="region" aria-label="Slide image. Use Zoom in to read small text, then scroll to explore.">
<img class="lightbox-image" alt="" width="2880" height="1620">
</div>
<footer class="lightbox-toolbar">
<button class="lightbox-zoom" type="button" aria-pressed="false">Zoom in</button>
<p class="lightbox-status" role="status" hidden></p>
<a class="lightbox-original" href="presentation.html">View animated slide</a>
</footer>
</dialog>
</body>
</html>
"""


def render_presentation(html: str, content: dict) -> str:
    html = re.sub(
        re.escape(LINKS_START) + r".*?" + re.escape(LINKS_END) + r"\n?",
        "", html, flags=re.DOTALL,
    )
    stylesheet = '<link rel="stylesheet" href="../reading.css" data-reading-links>'
    if stylesheet not in html:
        html = html.replace("</head>", stylesheet + "\n</head>", 1)
    links = f"""{LINKS_START}
<nav class="deck-reading-links" aria-label="Reading and downloads">
<a href="./">Read as an article</a>
{download(content, "deck-download")}
</nav>
{LINKS_END}
"""
    if "<body>" not in html:
        raise ValueError("Cannot add download links: presentation body was not found.")
    return html.replace("<body>\n", "<body>\n" + links, 1)


def build(check: bool = False) -> None:
    for slug in ("lab664", "brk245"):
        directory = SITE / slug
        content = json.loads((directory / "reading.json").read_text(encoding="utf-8"))
        presentation = directory / "presentation.html"
        original = presentation.read_text(encoding="utf-8")
        deck = load_deck(original)
        validate(content, deck, directory)
        outputs = {
            directory / "index.html": render_reading(content, deck),
            presentation: render_presentation(original, content),
        }
        for path, text in outputs.items():
            if check:
                if path.read_text(encoding="utf-8") != text:
                    raise ValueError(f"Generated file is out of date: {path}")
            else:
                path.write_text(text, encoding="utf-8", newline="\n")
        print(f"{slug}: {'checked' if check else 'built'} reading and presentation views")


if __name__ == "__main__":
    arguments = argparse.ArgumentParser(description=__doc__)
    arguments.add_argument("--check", action="store_true", help="Fail if generated HTML is stale.")
    build(check=arguments.parse_args().check)
