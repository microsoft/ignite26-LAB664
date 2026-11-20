# Microsoft Ignite – Document Intelligence & Content Understanding decks (web versions)

A phone-friendly reading edition and animated HTML version of the LAB664 Ignite
session deck, ready to publish with **GitHub Pages** (or any static web host):

| Folder | Session | Slides |
|---|---|---|
| [`lab664/`](lab664/) | **LAB664** – Build a claims workflow you can inspect, test, and improve | 15 |

The session opens as a scrollable, native HTML article with headings, edited
speaker-note prose, original diagrams, and videos with standard browser controls.
Article slide images are lossless 2880 × 1620 PNGs rendered from the original HTML,
not enlarged overview thumbnails. Tap an image or **Enlarge slide** to open a
lightbox without leaving the article. **Zoom in** shows the full-resolution image
with scrolling for small text; **Fit to screen** restores the overview.
**Back to article**, `Esc`, or a click outside the lightbox returns to the same
reading position and restores keyboard focus. Without JavaScript, the links open
the image directly, so the browser's Back button returns to the article.
A PowerPoint download is at the top of the reading and presentation views.
The article has a prominent link to the actual [lab instructions](../../instructions/lab.md).
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
from `main` (about 30 MB). It is the source PowerPoint, not a regenerated version
of the web article. The download needs internet access even when previewing locally.

## Preview locally

From the repository root in PowerShell, run:

```powershell
python -m http.server 8000 --bind 127.0.0.1 --directory .\slides\web
```

Open `http://localhost:8000/` and choose the deck. Stop the server with `Ctrl+C`.
Opening `slides\web\index.html` directly in a browser also works.

## Video hosting

The demo MP4 is included alongside the deck and use relative URLs.
GitHub Pages serves them directly; no video service, player package, account,
or streaming backend is required. The supplied videos use browser-friendly H.264
MP4 encoding. Reading editions never autoplay; use the native player controls.
The animated presentation retains its original playback behavior, subject to
browser autoplay rules.

The site is approximately 28 MB, including full-resolution slide images and
the demo video. This is below GitHub's 100 MiB per-file Git limit and
[Pages' 1 GB published-site limit](https://docs.github.com/en/pages/getting-started-with-github-pages/github-pages-limits).
Pages has a soft bandwidth limit of 100 GB per month, so video-heavy traffic can
consume the allowance quickly. For a large audience, move the MP4s to an approved
video host or object storage/CDN and update their URLs in the deck HTML. That is
optional for this static setup. Keep these assets as regular Git files, not Git
LFS pointers, so the Pages artifact contains playable videos and images.

## Presenting

Choose **View animated slides** on the reading page. The reading edition uses
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

Edit `lab664/reading.json`, then run from the repository root:

```powershell
python .\slides\web\tools\build_reading.py
python .\slides\web\tools\build_reading.py --check
python -m unittest discover -s .\slides\web\tools -p "test_build_reading.py"
```

The generator uses only Python's standard library. It rebuilds each `index.html`
and adds the reading/download navigation to `presentation.html`, without editing
the embedded original notes. It checks that every source slide is either mapped
to a reading section or explicitly omitted, that no slide with notes is omitted,
and that every video is included. It also checks that every article slide
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
Output goes into the deck's `assets/slides/` folder. The original small
`assets/thumbs/` images remain for the presentation overview and gallery.

## Editorial changes to review

Throughout the article, fragments and bullets became paragraphs; timing cues,
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

LAB664's closing blank/copyright slides 13–15 are not separate article sections.
They have no speaker notes and remain in the original presentation. No customer metrics,
benchmark results, or roadmap claims were independently revalidated.

## Regenerating the original presentation

The supplied converter is preserved in [`tools/`](tools/). Serving or publishing
the existing pages does not run it or install its dependencies. Regeneration is
optional and requires a separately prepared authoring environment with `lxml`,
Pillow, and any media conversion tools needed by the source deck. Do not install
these dependencies on attendee lab machines.

Export to a scratch directory first, not to the published session directory:

```powershell
python .\slides\web\tools\pptx2web.py ".\slides\LAB664-SlideDeck.pptx" ".\.tools\deck-export\lab664" --title "LAB664" --slug lab664
```

The converter produces `index.html` and
`assets/` (EMF logos are converted with LibreOffice when installed). After reviewing
an export, use its HTML as the session's `presentation.html`, retain or regenerate
the matching thumbnails and web-encoded media, reconcile `reading.json` with the
new source, then run `build_reading.py`. Do not overwrite the reading `index.html`
with converter output. The original converter can omit notes with `--no-notes`,
but doing so does not remove prose from the separate reading edition.
