# Public website quality

The game snapshot remains `a218110`. This pass changes the public presentation and
its tooling. It adds no gameplay, account system, tracking or data collection.

## Build and check

The deployed website remains plain HTML, CSS, JavaScript, images and JSON. Node
packages are development tools only and are excluded from GitHub Pages.

From the repository root:

```bash
python3 tools/build_nythara_pages.py
python3 -m unittest discover -s tools -p 'test_*.py'
python3 tools/nythara_previews.py
python3 tools/check_website.py --report
```

`check_website.py` checks generated output freshness, internal URLs and fragments,
assets, duplicate IDs, heading levels, image dimensions and alt attributes,
canonical and social metadata, JSON-LD syntax, sitemap coverage, JavaScript
syntax, privacy patterns and size budgets. It uses Python's standard library and
Node's syntax checker; it makes no network requests.

For browser checks:

```bash
npm ci --prefix tools
npx --prefix tools playwright install chromium
python3 -m http.server 8792 --bind 127.0.0.1
# In another terminal:
node tools/check_nythara_browser.cjs
node tools/measure_nythara_lighthouse.cjs
```

Set `CHROME_PATH` to an installed Chromium/Chrome executable when needed. Set
`QA_BASE` to test another local origin or the deployed site. Reports and screenshots
stay under `.git/nythara-quality/`, outside the published files. The browser checker
covers 320, 360, 390, 430, 768, 1024, 1280, 1440, 1920 and 2560 CSS pixels, landscape,
actual 200% Chromium browser zoom and reflow, long labels, all detail routes, relationships, Copy Link,
keyboard controls, modal focus, reduced motion, JavaScript-free Codex content and
WCAG A/AA checks with axe. Browser automation complements manual screenshot review;
it cannot establish accessibility for every assistive technology.

Lighthouse uses its unmodified mobile and desktop profiles. Scores vary with CPU,
network and browser version. The basic Python server has neither compression nor
production cache headers; final live measurements include GitHub Pages delivery.
There is no browser-specific content, audit detection or score manipulation.

## Static Codex URLs

`tools/build_nythara_pages.py` reads only the already-public JSON snapshot. It
never opens the game checkout. Run it after updating the snapshot or preview map;
`--check` verifies freshness without writing anything.

The current 74 category records represent 63 unique entities. Equipment aliases
share their equipment page with the corresponding item; boss aliases share their
boss page with the corresponding monster. Each entity has one canonical page.
Slugs come from stable record IDs, so a display-name change does not change URLs.
The generator also creates 12 category pages, one catalogue index, the sitemap,
a permalink lookup, the prerendered interactive landing page and a combined runtime JSON catalogue.

Every generated page contains its title, description, canonical and social
metadata, visible facts, preview, breadcrumb navigation, `BreadcrumbList` data,
related entries and a link into the interactive Database. All useful content is
available without JavaScript. Hash routes, search, filters, sorting and Copy Link
continue to work in the interactive Database. Its dedicated permalink link opens
the canonical entry page; Copy Link keeps sharing the current interactive route.

Do not edit generated HTML by hand. Entry templates live in `tools/templates/codex.html`; the Database landing templates are
`tools/templates/database-home.html` and `tools/templates/database-home-content.html`. The manifest limits stale-page cleanup to previously
generated files carrying the generator marker.

## Assets and budgets

See [the size report](website-asset-sizes.md) for measured production totals and
the largest 20 files. Published totals exclude development files and preserved
historical PNG/SVG originals explicitly listed in `_config.yml`; these remain in
Git, and profile README image links still resolve through their intended host.

The initial production candidate set was 22,713,882 bytes (21.662 MiB): Nythara
8,146,595 bytes and Database 405,758 bytes. That included large original PNGs.

- The two green backgrounds and four synchronized creature sprites are protected
  by SHA-256 checks in `tools/website-budgets.json` and remain byte-identical.
- Six used 1600×900 runtime captures gain WebP sources at quality 90, effort 6.
  The original JPEGs remain full-size lightbox targets and compatibility fallbacks.
  These WebPs save about 49% together; measured PSNR against the decoded originals
  is 42.96–46.33 dB. Text and HUD details were also checked visually.
- Only the hero gains AVIF, at 800 and 1600 pixels, quality 70, effort 6. The small
  variant is 45,908 bytes; the large is 115,488 bytes. JPEG remains the social-card
  image and fallback. No unnecessary third format is generated for each capture.
- The older representative world-art WebP shrinks from 2,430,781 to 308,546 bytes;
  the Agutroil background shrinks from 2,562,378 to 374,504 bytes. Both keep their
  original dimensions. The new green backgrounds are untouched.
- Root-page PNG delivery switches to WebP. Original PNGs stay in Git for the
  profile README/history and are excluded from the Pages build. The small header
  portrait is 120×120, sufficient for its 40-pixel display at 3× pixel density.
- Photos and artwork remain raster images; text stays browser-rendered, icons
  remain SVG, and creature sprites retain pixel rendering.

Enforced production limits are 2 MiB per image and 500 KiB per background. Prefer
under 300 KiB for routine previews. The shared world artwork is about 301 KiB,
retained at quality 90 rather than recompressed to save a marginal few bytes.
Use no external runtime JS, tracking libraries or backend dependency. Keep new
assets far below hosting and Git object limits. Do not rewrite history.

The [GitHub Pages limits](https://docs.github.com/en/pages/getting-started-with-github-pages/github-pages-limits)
allow up to 1 GB published output and a ten-minute deployment; this site stays far
below both. The pre-pass Git object report was 11.50 MiB loose plus 10.94 MiB packed,
with no garbage. Use `git count-objects -vH` to measure the current object database;
local ignored browser reports and Node dependencies are not repository objects.

## Rendering and accessibility decisions

The hero and sections now appear immediately. Removing scroll reveal observers
avoids initial compositing and delayed content visibility. CSS and JavaScript are
separate readable files; known unused styles and unused state were removed.
The Database loads one generated catalogue instead of a metadata/category request
waterfall. Its landing layout and snapshot counts are generated as HTML and reused
by JavaScript, avoiding an initial DOM rebuild. The catalogue request uses a generated content-hash query
so a new deployment cannot reuse an older cached data snapshot. Search remains synchronous, local
and immediate.

The hero has responsive sources and a matching preload; it is the only image with
high fetch priority. Backgrounds use ordinary preloads. Below-fold images remain
lazy, decoded asynchronously and dimensioned. Dynamic preview containers reserve
space; dialog dimensions come from the opener. Copy feedback reserves its line
height before the status appears, so confirmation does not move the detail body.

Native modal dialogs supply inert background behavior and focus containment. The
close button receives focus; Escape closes and focus returns to the opener.
All pages have a working skip link and reduced-motion support. No fake install
experience or unnecessary web manifest is added; the existing mark supplies the
SVG favicon and Apple touch icon.

The custom 404 uses absolute, local paths so it also works for missing nested
URLs. It is `noindex` and omitted from the sitemap. Its normal `/404.html` URL is
checked separately from an actually missing path, which must return HTTP 404.

## Deployment

No suitable tracked Actions workflow existed, so no additional workflow or
second deployment system was introduced. The fast checks above run locally.
Push the reviewed final changes once to `main`, wait for the existing GitHub
Pages workflow, then verify the live HTML, assets, generated URLs, sitemap and
actual missing-path response. Keep the public site a game presentation.
