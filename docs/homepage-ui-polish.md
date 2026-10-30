# Homepage UI polish and screenshot interaction

This pass preserves the homepage copy, Anton Deister / Agutroil identity, SEO metadata, original background image and all Nythara game content. It adds no image assets, framework, tracking or animation dependency.

## Presentation

- Homepage-only CSS gives the header a compact floating surface, a bounded 10-pixel backdrop blur with an opaque fallback, an active underline and matching focus styles.
- The existing fantasy background fades behind About; low-opacity radial colors and narrow gradient dividers carry the atmosphere through later sections.
- The footer uses the existing content, links and tokens inside a framed surface. Shared project styling is unchanged.
- The database CTA reuses the exact inline book drawing from `Nythara/index.html` through the site builder, without a second drawing or duplicate asset. The primary Nythara CTA stays cyan.
- Navbar GitHub links gain an aria-hidden external arrow; the destination and accessible name stay unchanged.

## Reused screenshot dialog

The existing Nythara dialog markup remains the source for the localized homepage dialog. Its controller and CSS are extracted to `assets/lightbox.js` and `assets/lightbox.css`, shared by both pages. The game page changes only its component assets; its content, screenshots, data revision and database are unchanged. Database full-image links keep their existing behavior and routing.

Native dialog handles focus containment and Escape. The shared controller adds scroll locking without unnecessary scrollbar-gutter reflow, restores focus and scroll position, and handles the close button and backdrop. Image clicks keep the dialog open. URL and history do not change; the original image href remains available without JavaScript. No new modal framework is introduced.

## Validation

- 14 Python tests, generator freshness, preview registry and JavaScript syntax pass.
- All 2,704 internal references, image references, sitemap, robots, metadata and privacy checks pass.
- All ten widths pass: 320, 360, 390, 430, 768, 1024, 1280, 1440, 1920 and 2560. No horizontal overflow.
- The portfolio suite tests three modal closing methods at every width (30 combinations), including inert background, image clicks, scroll lock, focus return and unchanged URL/history.
- Additional interaction checks pass at 390×844, 1440×900 and 1920×1080. The mobile test uses actual touch input; normal-motion contexts also preserve the scroll position.
- All 76 static Codex pages render at mobile and desktop widths; all 74 interactive aliases and 338 related-entry links pass.
- 26 axe WCAG A/AA audits report zero violations, including the homepage dialog, mobile menu and existing Nythara dialog.
- No console errors, broken images or failed resources in either browser suite.
- Screenshots reviewed at 390×844, 1440×900 and 1920×1080: header/hero, Hero→About, About→stack, database button, footer and dialog.
- Homepage title, complete metadata, JSON-LD and canonical match the baseline exactly. Google verification, robots, sitemap, all screenshots/background files and all database files are byte-identical.
- Forbidden public project/source labels and unpublished sprint references remain absent.

## Lighthouse comparison

Completed local Lighthouse 12.8.2 runs use the standard mobile and desktop profiles and an uncompressed Python server, without score overrides.

| Profile | Stage | Performance | Accessibility | Best Practices | SEO | LCP (ms) | CLS | TBT (ms) |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| mobile | Before | 95 | 100 | 100 | 100 | 2781 | 0.0000 | 90 |
| desktop | Before | 100 | 100 | 100 | 100 | 594 | 0.0000 | 0 |
| mobile | After | 95 | 100 | 100 | 100 | 2779 | 0.0000 | 101 |
| desktop | After | 100 | 100 | 100 | 100 | 615 | 0.0000 | 0 |

The mobile after-run reported slow host CPU (benchmark 799 versus 1115.5 before); its performance score remains 95. Desktop remains 100. These lab measurements do not establish field Core Web Vitals. Live delivery is checked after the normal Pages deployment.

Browser screenshots, raw measurements and test reports stay in `.git/visual-polish/` and are not published.
