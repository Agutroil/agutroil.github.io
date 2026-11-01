# Agutroil website and Nythara refresh

Historical report for PR #7. The subsequent publication policy supersedes its
multi-project presentation: Nythara is now the only presented project. See
`website-quality.md` for the current policy.

## Presentation

The homepage keeps the dark navigation, fantasy/Linux artwork, portrait, shared
design tokens and footer. Projects now follow About, ahead of the technology
stack. Nythara has a clearer introduction, an explicit alpha status, a compact
technical summary, a prominent Database link and three additional gallery views.

MedCore, Blog Pulse, Aura and Auto-Abenteuer have compact overview cards again.
Their descriptions come from previously published website history (`86bdf06`
and `eee32be`), without new availability, download, security-audit or release
claims. No private repository links are exposed. Anton Deister / Agutroil,
developer, Linux enthusiast, open-source creator and technology enthusiast remain
the profile identity.

The shared native screenshot dialog gains localized previous/next buttons, an
image counter and left/right arrow keys. Repeated images on the Nythara page
share one gallery position. The clicked preview's caption and focus-return
target are retained. Escape, backdrop/close-button dismissal, inert background,
scroll locking and direct image links without JavaScript continue to work.

## Nythara publication boundary

GitHub's `main` was checked on 2026-11-01 and resolves to
`b2bac4d03207db30e3d8e0314056b9f96a64e0e0` (Sprint 26 presentation).
Sprint 27 implementation/presentation and the stacked Sprint 28–30 work remain
open. No Sprint 27–31 feature, screenshot, source link or release claim is added.

The website's existing data revision and approved capture manifest remain
unchanged. The homepage gallery reuses the already published Silverwood, Hollow
Ruins and party captures. All 35 existing screenshot files, backgrounds, game
data and Database pages are byte-identical to the base revision. No game
checkout, game process or self-hosted runner is accessed or changed.

Godot 4.7.2, GDScript, GL Compatibility, 2D characters in a 3D world,
server-authoritative architecture and the performance focus on older PCs and
integrated graphics agree with the merged main documentation. These are
technical facts and development targets, not new release or benchmark claims.
The static publication guard now covers Sprint 27–31 across the whole site.

## Performance, accessibility and SEO

No production dependency, font request, tracking or framework is added. Three
800×450 WebP previews are derived from the existing website captures, preserving
their full frames (Lanczos resize, quality 84, method 6). Together they use 66,758
bytes instead of the original 211,512 bytes, a 68% reduction for thumbnail delivery.
Responsive sources retain the originals for higher pixel densities, and every
lightbox link still opens the original 1600×900 image. The previews load lazily
with explicit dimensions and asynchronous decoding. The AVIF banner and reduced
motion support are retained. The new shared dialog assets have a cache version;
the homepage stylesheet retains its generated content hash.

The measured published file total changes from 5,287,524 to 5,365,193 bytes
(77,669 additional bytes including the three previews). Original image files
are unchanged; runtime JavaScript grows by 1,351 bytes. The homepage loads the gallery only
as they approach the viewport. See `website-asset-sizes.md` for the size audit.

The Database button can wrap on narrow screens. Project facts and galleries
collapse to one column, with visible focus indicators and 44px dialog controls.
Language changes are marked on the homepage's English copy and Database link.

The title, canonical, social images, favicons, JSON-LD, sitemap and robots remain
valid. The homepage description and social descriptions reflect the requested
identity; the game page declares its English Open Graph locale. The existing
Google verification file is byte-identical; there was no verification meta tag
to replace.

## Validation

- Build freshness, 14 existing Python tests, preview integrity and JS syntax pass.
- Static audit: 2,717 internal references, 79 sitemap URLs, no privacy findings.
- Portfolio browser suite: 12 widths from 320 to 2560, including 390×844,
  768×1024, 1366×768 and 1600×900; no horizontal overflow.
- 76 static Database pages checked at both mobile and desktop widths.
- 36 dialog closing combinations, gallery button/arrow/wraparound checks,
  keyboard focus, mobile menu, no-JavaScript navigation and touch input pass.
- Nythara suite: ten widths, 74 interactive detail routes, 338 related links,
  search/filter/sort, copy-link fallbacks, retry behavior and actual 200% browser
  zoom pass.
- 26 axe WCAG A/AA audits across both suites report zero violations. These
  automated checks do not replace evaluation with every assistive technology.
- No unresolved console errors, resource errors or broken images. One Nythara
  run lost its local preview server after its geometry/detail checks; the
  affected functional/accessibility checks passed after restarting that server.
  The interrupted report is retained with the local QA artifacts.
- Screenshots reviewed at all four requested sizes, plus the mobile project
  body and touch-controlled dialog. Reports and captures stay in
  `.git/website-refresh/`, outside the published files.
- HTTP checks of the public homepage, Database and GitHub profile return 200.
- The tracked/new text-file scan finds no local checkout paths or credentials.
  Google verification, all game assets/data, robots and sitemap have no diff.

The new read-only `Website checks` workflow runs the existing static checks on
GitHub-hosted Ubuntu. Browser tooling remains development-only and unchanged.

## Lighthouse lab measurements

Lighthouse 12.8.2 uses the standard mobile/desktop profiles and the local,
uncompressed Python server. Accessibility, Best Practices and SEO are 100 in
all listed runs; CLS is 0 throughout.

| Page / stage | Mobile performance | Desktop performance |
| --- | ---: | ---: |
| Homepage, unchanged base | 96 | 98 |
| Homepage, first gallery implementation | 87 | 86 |
| Homepage, responsive preview delivery | 92 | 86 |
| Nythara | 98 | 99 |

The final homepage's LCP is 3,315ms mobile and 710ms desktop; TBT is 7ms and
319ms respectively. The added gallery increases homepage payload compared with
the base despite using smaller previews. The new previews reduce its own image
delivery from 212KB to 67KB. Host CPU measurements varied substantially between
runs, and some mobile runs report Lighthouse's slow-CPU warning. These are lab
measurements, not field Core Web Vitals or a claim that all performance scores
improved.
