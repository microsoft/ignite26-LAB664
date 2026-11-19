# Microsoft Ignite – Document Intelligence & Content Understanding decks (web versions)

Phone-friendly reading editions and animated HTML versions of two Ignite session
decks, ready to publish with **GitHub Pages** (or any static web host):

| Folder | Session | Slides |
|---|---|---|
| [`lab664/`](lab664/) | **LAB664** – Build a claims workflow you can inspect, test, and improve | 15 |
| [`brk245/`](brk245/) | **BRK245** – Trusted agents need Document Intelligence & Content Understanding | 38 |

Each session opens as a scrollable, native HTML article with headings, edited
speaker-note prose, original diagrams, and videos with standard browser controls.
Article slide images are lossless 2880 × 1620 PNGs rendered from the original HTML,
not enlarged overview thumbnails. Tap an image or **Enlarge slide** to open a
lightbox without leaving the article. **Zoom in** shows the full-resolution image
with scrolling for small text; **Fit to screen** restores the overview.
**Back to article**, `Esc`, or a click outside the lightbox returns to the same
reading position and restores keyboard focus. Without JavaScript, the links open
the image directly, so the browser's Back button returns to the article.
PowerPoint downloads are at the top of both reading and presentation views.
LAB664 has a prominent link to the actual [lab instructions](../../instructions/lab.md).
**View animated slides** opens `presentation.html`, which retains the original
slide transitions, click-by-click builds, and unedited speaker notes.

The generated pages are checked in. Serving and deploying need no build step,
npm packages, or external runtime dependencies.

## Publish on GitHub Pages

Checking HTML into the repository makes it available to download, but GitHub's
file viewer does not run it as a website. Enable GitHub Pages to share browser
links. No new repository, npm packages, build step, or Azure resources are needed.

1. A repository administrator must open **Settings > Pages > Build and deployment**
   and select **GitHub Actions** as the source. Organization policy must allow
   Pages and the official GitHub Actions used by the workflow.
2. Merge these files and [the publishing workflow](../../.github/workflows/publish-decks.yml)
   into `main`. The **Publish HTML decks** workflow runs when this folder or the
   workflow changes on `main`. If the merge happened before Pages was enabled,
   open **Actions > Publish HTML decks > Run workflow** and select `main`.
3. If the `github-pages` environment requires approval, approve the deployment.
   The workflow publishes only `slides/web`, not the workbench, lab data, or
   the rest of the repository.
4. After the deployment succeeds, share these links:

   | Page | URL |
   |---|---|
   | Gallery | https://microsoft.github.io/ignite26-LAB664/ |
   | LAB664 | https://microsoft.github.io/ignite26-LAB664/lab664/ |
   | BRK245 | https://microsoft.github.io/ignite26-LAB664/brk245/ |

   Add `#slide-12` to a reading URL to jump to the section containing original
   slide 12, or use `presentation.html#/12` for the animated slide. Existing
   `#/12` reading-page links are also supported for included slides.
   Pages serves this folder at the site root, so published URLs do not include
   `slides/web`.

The URLs above assume the default GitHub Pages domain and no custom domain.
They will not work until Pages is enabled and a deployment succeeds.
The articles and the presentations' embedded speaker notes will be public.

## PowerPoint downloads

LAB664 downloads the existing [`slides/LAB664-SlideDeck.pptx`](../LAB664-SlideDeck.pptx)
from `main` (about 30 MB).
BRK245 downloads the original `slides/BRK245-Final.pptx` from commit
[`b4c26a85f45dad099902d762f1919cc3cb0dc2df`](https://github.com/microsoft/ignite26-LAB664/commit/b4c26a85f45dad099902d762f1919cc3cb0dc2df)
through GitHub's LFS media endpoint (about 243 MB). It is intentionally pinned to
that historical version; its bytes are not added to the Pages site or restored
into the current branch. These are source PowerPoints, not regenerated versions
of the web articles. Downloads need internet access even when previewing locally.

## Preview locally

From the repository root in PowerShell, run:

```powershell
python -m http.server 8000 --bind 127.0.0.1 --directory .\slides\web
```

Open `http://localhost:8000/` and choose a deck. Stop the server with `Ctrl+C`.
Opening `slides\web\index.html` directly in a browser also works.

## Video hosting

The eight MP4 files are included alongside the decks and use relative URLs.
GitHub Pages serves them directly; no video service, player package, account,
or streaming backend is required. The supplied videos use browser-friendly H.264
MP4 encoding. Reading editions never autoplay; use the native player controls.
The animated presentation retains its original playback behavior, subject to
browser autoplay rules.

The site is approximately 119 MB (114 MiB), including full-resolution slide images
and videos; the largest video is
approximately 20 MB. This is below GitHub's 100 MiB per-file Git limit and
[Pages' 1 GB published-site limit](https://docs.github.com/en/pages/getting-started-with-github-pages/github-pages-limits).
Pages has a soft bandwidth limit of 100 GB per month, so video-heavy traffic can
consume the allowance quickly. For a large audience, move the MP4s to an approved
video host or object storage/CDN and update their URLs in the deck HTML. That is
optional for this static setup. Keep these assets as regular Git files, not Git
LFS pointers, so the Pages artifact contains playable videos and images.

## Presenting

Choose **View animated slides** on either reading page. The reading edition uses
normal browser scrolling and does not intercept slide-navigation keys.

| Action | Keys |
|---|---|
| Next build / slide | `→` `↓` `Space` `Page Down` `Enter`, or click |
| Previous | `←` `↑` `Page Up` `Backspace` |
| First / last slide | `Home` / `End` |
| Jump to a slide | type the number, then `Enter` |
| All slides | `O` (or `G`) |
| Speaker notes | `N` |
| Full screen | `F` |
| Black / white screen | `B` / `W` |
| Close a panel | `Esc` |

* Touch screens: swipe left or right.
* Videos: click a video to play or pause it. Slides that started a video automatically in PowerPoint do the same here;
  a browser may start it muted until you click once on the page.
* Print / PDF: use the browser's **Print → Save as PDF** to get one slide per page with every build shown.
* People who prefer reduced motion (operating-system setting) get the builds without animation.

## Good to know

* **Fonts.** The decks use Segoe UI. Windows shows it natively; macOS and Linux use a metric-matched fallback so
  line breaks stay close to the original.
* **Hidden slides** in the source decks are not included.
* **Original speaker notes are embedded** in `presentation.html` (press `N`).
  They have not been rewritten. The reading editions use separately edited prose
  from `reading.json`; see the editorial review below. Both are public.
* **Videos** were re-encoded where needed (H.264 MP4, web-optimized); the 4K demo video was downscaled to 1080p and
  animated GIFs were converted to looping videos.

## Editing the reading editions

Edit `lab664/reading.json` or `brk245/reading.json`, then run from the repository root:

```powershell
python .\slides\web\tools\build_reading.py
python .\slides\web\tools\build_reading.py --check
python -m unittest discover -s .\slides\web\tools -p "test_build_reading.py"
```

The generator uses only Python's standard library. It rebuilds each `index.html`
and adds the reading/download navigation to `presentation.html`, without editing
the embedded original notes. It checks that every source slide is either mapped
to a reading section or explicitly omitted, that no slide with notes is omitted,
and that all eight videos are included. It also checks that every article slide
has a lossless image at 2880 × 1620. Shared styling is in `reading.css`;
`reading.js` handles the contents menu, old slide hash links, and the accessible
native-dialog lightbox with zoom and reading-position restoration.

### Regenerate full-resolution slide images

The images are checked in, so attendees and the Pages workflow need no browser
automation tools or additional packages. For authoring, start the local preview
server, then run this command in a second PowerShell window using an already
installed Edge browser:

```powershell
node .\slides\web\tools\export_slides.mjs "C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe" http://127.0.0.1:8000/
python .\slides\web\tools\build_reading.py
```

This authoring tool uses Node.js 22's built-in WebSocket API and the browser's
local debugging protocol; it adds no npm dependencies and installs nothing.
It renders the included article slides from `presentation.html` at 1.5× their
1920 × 1080 layout, with all builds shown, loaded fonts/images, and video posters.
Output goes into each deck's `assets/slides/` folder. The original small
`assets/thumbs/` images remain for the presentation overview and gallery.

## Editorial changes to review

Throughout both articles, fragments and bullets became paragraphs; timing cues,
click directions, speaker handoffs, greetings, and spoken transitions were
removed. Adjacent material was grouped into sections. Original notes are
preserved verbatim in `presentation.html`.

The following changes deserve a content-owner check. The linked reading sections
are the changed prose; the **Original slides** disclosures link back to the
unchanged presentation.

| Reading section | Original slides | Change to check |
|---|---|---|
| [LAB664: Start with the lab](lab664/index.html#start-with-the-lab) and [Open the lab](lab664/index.html#open-the-instructions) | 1–2, 10–11 | Added direct instructions CTAs. Corrected the notes' "step 1: open CU Studio" to the checked-in guide's step 1 setup, step 2 Studio. Merged the duplicate slides 10 and 11. |
| [LAB664: The workflow](lab664/index.html#the-workflow-you-will-build) | 9 | Kept the optional step 9/10 structure and clarified that this lab uses Azure AI Search directly, not a Foundry IQ knowledge base, consistent with the repository guide. |
| [BRK245: Loan application example](brk245/index.html#loan-application-example) | 18 | The notes call a custom form a mortgage application in one paragraph and an immigration form in the result. The article follows the described result and uses "document-specific fields" instead of resolving that inconsistency by inventing a form type. |
| [BRK245: Advanced Contextualization](brk245/index.html#advanced-contextualization) | 23 | Used the slide's precise 97.41% → 99.32% F1 figures in a native table, while explicitly retaining the notes' rounded 99.3%. Kept the 19-category scope, +1.91 points, 51% cost reduction, and about 2x speed claim. |
| [BRK245: Unified experience](brk245/index.html#a-unified-developer-experience) and [Roadmap](brk245/index.html#roadmap-as-presented) | 32, 34 | Framed "try it today" and release timing as statements from the Ignite presentation, not independently verified current availability. Grouped the roadmap into a readable table; the original detailed preview/GA labels remain in the slide. |
| [BRK245: Confidence and grounding](brk245/index.html#confidence-and-grounding) | 28 | Expressed "auto-approve" as accepting extraction results after document-specific calibration, not approval of a claim or payment. |
| [BRK245: Put it into practice](brk245/index.html#put-it-into-practice) | 35–36 | Replaced the notes' unresolved `[session code]` with LAB664, as named on slide 36, and linked the real instructions. |

LAB664's closing blank/copyright slides 13–15 and BRK245's blank/title-divider
slides 1–2, 16, 19, 31, and 38 are not separate article sections. They have no
speaker notes and remain in the original presentations. No customer metrics,
benchmark results, or roadmap claims were independently revalidated.

## Regenerating the original presentation

The supplied converter is preserved in [`tools/`](tools/). Serving or publishing
the existing pages does not run it or install its dependencies. Regeneration is
optional and requires a separately prepared authoring environment with `lxml`,
Pillow, and any media conversion tools needed by the source deck. Do not install
these dependencies on attendee lab machines.

Export to a scratch directory first, not to the published session directory:

```powershell
python .\slides\web\tools\pptx2web.py ".\slides\BRK245-Final.pptx" ".\.tools\deck-export\brk245" --title "BRK245" --slug brk245
```

This optional example assumes you have separately downloaded the BRK245 source
PowerPoint to `slides\BRK245-Final.pptx`. The converter produces `index.html` and
`assets/` (EMF logos are converted with LibreOffice when installed). After reviewing
an export, use its HTML as the session's `presentation.html`, retain or regenerate
the matching thumbnails and web-encoded media, reconcile `reading.json` with the
new source, then run `build_reading.py`. Do not overwrite the reading `index.html`
with converter output. The original converter can omit notes with `--no-notes`,
but doing so does not remove prose from the separate reading edition.
