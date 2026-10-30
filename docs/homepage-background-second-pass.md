# Homepage background: second pass

The second pass replaces the nearly black page foundation with a continuous dark navy/blue/violet composition. The original fantasy image is byte-identical. The primary image keeps its framing, with a softer overlay/mask into About. A low-opacity central sky/valley crop of the same image continues behind the lower desktop sections; the crop excludes the wizard and castle. That secondary layer is disabled below 901 pixels. No images, scripts, blur, fixed background, animations or dependencies are added.

Stack/focus cards, the project card and GitHub panel use a dark translucent surface and a soft shadow. Navbar, footer structure, all copy, SEO, game content, database, screenshots, lightbox, database button and external-link indicator are preserved. The only HTML change is a content-hash query on the homepage stylesheet, generated automatically to avoid stale browser CSS.

## Visual evidence

Full browser captures and section comparisons are retained locally under `.git/background-second-pass/` (excluded from publication):

- `before-1440.png` / `after-1440.png` and `before-390.png` / `after-390.png`: full-page, identical viewport widths.
- `compare-stack-1440.png`, `compare-about-1440.png`, `compare-nythara-1440.png`, `compare-footer-1440.png`: side-by-side desktop comparisons.
- Matching `compare-*-390.png` files: phone comparisons.
- Additional full/section captures at 1920×1080.

The rendered comparisons were inspected before committing. The difference is plainly visible: near-black spaces become blue around About/technology, blue-violet around Nythara, and a violet/navy finish around focus/footer. The original landscape remains visible in About, while the lower crop reads as distant sky/valley rather than a repeated castle. All section positions and heights match the before-captures exactly.

## Validation

- 14 Python tests, generation freshness, JavaScript syntax, preview/content checks and all 2,705 internal references pass.
- The existing portfolio Chromium suite passes at 320, 360, 390, 430, 768, 1024, 1280, 1440, 1920 and 2560 pixels.
- Eight axe audits pass, including closed/open mobile navigation and the lightbox. No console errors, failed resources, broken images or horizontal overflow.
- All 76 static Codex pages render at mobile/desktop (152 visits). Existing 30 lightbox width/closing-method combinations, focus, scroll/history, database button and GitHub indicator checks pass.
- Homepage title, metadata, canonical, JSON-LD and script content exactly match the baseline. Normalizing the CSS version query makes the homepage HTML byte-identical to the baseline.
- Nythara, all WebP assets, game revision/data, database, lightbox files, shared tokens/scripts, robots, sitemap and Google verification have no diff. Forbidden public wording remains absent.

## Performance

Completed local Lighthouse 12.8.2 runs use the same standard mobile/desktop profiles and uncompressed Python server, with no score overrides.

| Profile | Stage | Performance | Accessibility | Best Practices | SEO | LCP (ms) | CLS | TBT (ms) |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| mobile | Before | 95 | 100 | 100 | 100 | 2860 | 0.0000 | 0 |
| desktop | Before | 99 | 100 | 100 | 100 | 609 | 0.0000 | 81 |
| mobile | After | 96 | 100 | 100 | 100 | 2791 | 0.0000 | 0 |
| desktop | After | 100 | 100 | 100 | 100 | 629 | 0.0000 | 0 |

The background asset is requested once per measured page in both stages, even though desktop CSS reuses it. The result shows no observed performance regression; lab scores vary with host load and do not establish field Core Web Vitals. Live browser verification follows the normal Pages deployment.
