# Agutroil website quality results

Measured on 30 October 2026 with Lighthouse 12.8.2, unmodified mobile/desktop profiles and the uncompressed local Python server. This is one complete final local run; no score overrides or selection of highest scores. Live delivery is verified separately after deployment.

| Page | Profile | Performance | Accessibility | Best Practices | SEO | LCP (ms) | CLS | TBT (ms) |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Homepage | mobile | 88 | 100 | 100 | 100 | 2720 | 0.0000 | 339 |
| Nythara | mobile | 97 | 100 | 100 | 100 | 2266 | 0.0000 | 109 |
| Database | mobile | 97 | 100 | 100 | 100 | 2484 | 0.0000 | 15 |
| Homepage | desktop | 100 | 100 | 100 | 100 | 588 | 0.0000 | 4 |
| Nythara | desktop | 100 | 100 | 100 | 100 | 711 | 0.0000 | 55 |
| Database | desktop | 99 | 100 | 100 | 100 | 814 | 0.0000 | 84 |

## Scope and design

The homepage now leads with the Agutroil identity, a concise introduction, three technology groups, a single Nythara project card, the GitHub profile and three current focus areas. Other projects are omitted following the owner’s updated direction. The dark technical/fantasy identity, wizard mark, portrait and original green Nythara art remain recognizable.

The site shares typography, radii, spacing tokens and one footer template across 80 meaningful pages. The 404 now belongs to the portfolio and has working absolute home/project links. German remains the portfolio language; the existing English Nythara and Codex interface remains English.

## Verification

- 14 Python unit tests passed; generated homepage, footer and all Codex outputs are current.
- 80 unique titles and descriptions; 79 indexable canonical URLs match the sitemap. Google verification is unchanged.
- All 2,698 internal references, JavaScript syntax, JSON-LD syntax, image dimensions, alt attributes, privacy patterns and size budgets pass.
- Every requested width passes: 320, 360, 390, 430, 768, 1024, 1280, 1440, 1920 and 2560. No document overflow.
- All 76 static entry/category/catalogue pages were rendered at 390 and 1440 pixels: 152 page visits, all images decoded.
- All 74 interactive detail aliases and 338 related-entry links passed, along with search, filters, sorting, incremental loading, reset and empty states.
- Clipboard copy, native and manual fallbacks, stable feedback and data-load recovery passed.
- 24 axe WCAG A/AA audits across mobile/desktop, open/closed menus, database details and the image dialog: zero violations.
- Skip links, visible focus, keyboard menu control, Escape, modal focus containment and restoration, reduced motion and JavaScript-free navigation passed.
- Landscape, long labels, 200% reflow and actual Chromium 200% browser zoom passed.
- Browser suites recorded zero console errors, failed resources or broken images.
- Visual review covered the homepage, Nythara hero/gameplay/social/guild/gallery/footer, database landing and creature/dungeon views, and 404.
- No current game capture or game data JSON changed. All 35 approved captures and protected backgrounds retain their hashes.
- The approved public game revision remains `b2bac4d`; no later gameplay is published.

## Assets and privacy

Three portfolio WebP deliveries were resized without upscaling: the portrait (560×700), social banner (1280×480) and background (1280×720). They save 611,080 bytes. One obsolete delivery image with zero consumer references was removed (162,576 bytes). Historical originals used by the profile README remain preserved and excluded from Pages. No exact duplicate production images remain.

The final published footprint is approximately 5.06 MiB, down from 5.77 MiB. Runtime JavaScript remains about 55 KiB across the site; no framework or third-party runtime dependency was introduced. Duplicate footer CSS, redundant shared font/radius declarations and obsolete Nythara 404 rules were removed.

Production privacy checks found no private filesystem paths, personal email addresses, private repository links, runtime identities, tokens, credentials or trackers. The only external HTML destination is the Agutroil GitHub profile. Development-only commands and detection patterns are excluded from Pages.

## Measurement limits

All mobile runs reported a slower host CPU than Lighthouse expects. Benchmark indices were 527.5 (homepage), 805 (Nythara) and 943 (Database). The homepage mobile performance result is 88, with 339 ms total blocking time; it is reported as measured. Desktop performance was 100/100/99. All six accessibility, best-practice and SEO scores were 100, and CLS was zero. These are lab results, not field Core Web Vitals. GitHub Pages supplies compression/cache headers absent from the local server.

Browser automation and axe complement visual and keyboard review; they cannot establish compatibility with every assistive technology.

See [repeatable commands](website-quality.md) and [asset sizes](website-asset-sizes.md).
