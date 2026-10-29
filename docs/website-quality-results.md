# Website quality results

Measured on 29 October 2026 against the pre-deployment local source with Lighthouse 12.8.2, default mobile/desktop profiles and the uncompressed Python static server. No score overrides were used.

| Page | Profile | Performance | Accessibility | Best Practices | SEO | LCP (ms) | CLS | TBT (ms) |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Nythara | mobile | 93 | 100 | 100 | 100 | 2113 | 0.0000 | 260 |
| Database | mobile | 98 | 100 | 100 | 100 | 2410 | 0.0000 | 50 |
| Nythara | desktop | 98 | 100 | 100 | 100 | 930 | 0.0000 | 104 |
| Database | desktop | 100 | 100 | 100 | 100 | 511 | 0.0000 | 58 |

## Measurement limits

The local mobile Nythara score is 93, below the 95 target. Both mobile runs reported that the shared host CPU was slower than Lighthouse expects; benchmark indices were 669 and 824.5. Earlier exploratory runs varied widely as host load changed. Scores here are one complete pre-deployment run, not a selection of the highest results. Subsequent changes add the catalogue cache fingerprint and retry recovery guard; live checks measure the deployed revision. The production CDN supplies compression and cache headers absent from the local server. Live measurements are collected separately after publication. No simulated CPU multiplier was reduced to raise scores.

Lab CLS was 0 for both pages on both profiles. These are lab measurements, not field Core Web Vitals. GitHub Pages cache/security headers are hosting-controlled; no backend or custom server was introduced.

## Functional and accessibility verification

- 11 Python unit tests passed, including the original 7 preview tests.
- Preview validation: 74/74; character screenshots: 0; missing assets: 0.
- All 74 interactive detail aliases, 338 related-entry links, filters, sorting, incremental loading, search and no-results state passed.
- Clipboard copy, native fallback, manual fallback, reset feedback and stable detail geometry passed.
- Versioned-catalogue loading and recovery from a simulated data-fetch failure passed.
- 320, 360, 390, 430, 768, 1024, 1280, 1440, 1920 and 2560 CSS pixels passed without horizontal overflow.
- Landscape at 844×390 and long German/English labels passed.
- Actual Chromium browser zoom was set to 200% through browser settings: a 1280-pixel window produced a 640-CSS-pixel viewport with device pixel ratio 2. Nythara, Database home, filters, dungeon detail, a static monster page and 404 passed.
- Sixteen axe WCAG A/AA audits across mobile/desktop views reported zero violations.
- Native modal focus, background focus prevention, Escape, opener restoration, skip links and reduced motion passed.
- JavaScript-free landing/catalogue/equipment pages passed; visual review covered the hero, world, gameplay, multiplayer, social, LFG, Codex, gallery, footer, generated details and 404.
- Public metadata, sitemap, asset budgets, protected background/sprite hashes, syntax, privacy and internal-link checks passed.

See [asset sizes](website-asset-sizes.md) and [repeatable commands](website-quality.md).
