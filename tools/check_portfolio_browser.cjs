#!/usr/bin/env node
// Portfolio, shared navigation and every generated static page in real Chromium.
const {chromium} = require('playwright');
const AxeBuilder = require('@axe-core/playwright').default;
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const root = path.resolve(__dirname, '..');
const base = process.env.QA_BASE || 'http://127.0.0.1:8792';
const output = process.env.QA_OUTPUT || path.join(root, '.git/complete-quality/portfolio');
const report = {widths:[], staticPages:0, accessibility:[], keyboard:[], consoleErrors:[], resourceErrors:[], brokenImages:[]};
fs.mkdirSync(output, {recursive:true});

(async () => {
  const browser = await chromium.launch({executablePath:process.env.CHROME_PATH || undefined});
  const context = await browser.newContext({reducedMotion:'reduce'});
  const page = await context.newPage();
  page.on('pageerror', error => report.consoleErrors.push(error.message));
  page.on('console', message => { if (message.type() === 'error') report.consoleErrors.push(message.text()); });
  page.on('response', response => { if (response.status() >= 400) report.resourceErrors.push({url:response.url(), status:response.status()}); });
  page.on('requestfailed', request => { if (request.failure()?.errorText !== 'net::ERR_ABORTED') report.resourceErrors.push({url:request.url(), error:request.failure()?.errorText}); });
  const visit = async route => { assert.equal((await page.goto(base + route)).status(), 200, route); };
  const images = async () => {
    const broken = await page.locator('img').evaluateAll(async imgs => {
      await Promise.all(imgs.map(img => { img.loading = 'eager'; return img.decode().catch(() => {}); }));
      return imgs.filter(img => !img.naturalWidth).map(img => img.src);
    });
    report.brokenImages.push(...broken);
    assert.deepEqual(broken, []);
  };
  const geometry = async label => {
    const result = await page.evaluate(() => ({width:innerWidth, scroll:document.documentElement.scrollWidth}));
    assert(result.scroll <= result.width, `${label}: ${JSON.stringify(result)}`);
    const outside = await page.locator('main *, header *, footer *').evaluateAll(elements => elements.filter(el => {
      if (el.namespaceURI === 'http://www.w3.org/2000/svg' || !el.checkVisibility()) return false;
      const rect = el.getBoundingClientRect();
      if (!rect.width || (rect.left >= -1 && rect.right <= innerWidth + 1)) return false;
      for (let parent=el.parentElement; parent; parent=parent.parentElement) {
        if (['hidden','clip','scroll','auto'].includes(getComputedStyle(parent).overflowX)) return false;
      }
      return true;
    }).map(el => el.outerHTML.slice(0,180)));
    assert.deepEqual(outside, [], label);
  };
  try {
    for (const width of [320,360,390,430,768,1024,1280,1440,1920,2560]) {
      await page.setViewportSize({width,height:1000});
      for (const route of ['/', '/404.html']) {
        await visit(route); await images(); await geometry(`${route} ${width}`);
        for (const section of await page.locator('main section,footer').all()) {
          await section.scrollIntoViewIfNeeded(); await geometry(`section ${route} ${width}`);
        }
        if ([390,1440].includes(width)) {
          await page.screenshot({path:path.join(output,`${route==='/'?'home':'404'}-${width}.png`),fullPage:true});
        }
      }
      await visit('/');
      if (width <= 640) {
        const toggle = page.locator('#menu-toggle');
        assert.equal(await page.locator('#nav-links').isVisible(), false);
        await toggle.focus(); await page.keyboard.press('Enter');
        assert.equal(await toggle.getAttribute('aria-expanded'), 'true');
        await geometry(`open menu ${width}`);
        await page.keyboard.press('Tab'); assert.equal(await page.evaluate(()=>document.activeElement.textContent), 'Startseite');
        await page.keyboard.press('Escape'); assert(await toggle.evaluate(el=>el===document.activeElement));
        assert.equal(await page.locator('#nav-links').isVisible(), false);
        await toggle.click(); await page.locator('#nav-links a[href="/#projects"]').click();
        assert.equal(await page.locator('#nav-links').isVisible(), false);
        assert.equal(await page.evaluate(()=>document.activeElement.id), 'projects');
      }
      report.widths.push(width); console.log(`Portfolio ${width}: PASS`);
    }
    await page.setViewportSize({width:390,height:844});
    await visit('/');
    await page.keyboard.press('Tab'); assert.equal(await page.evaluate(()=>document.activeElement.className), 'skip-link');
    await page.keyboard.press('Enter'); assert.equal(await page.evaluate(()=>document.activeElement.id), 'main');
    const cta = page.locator('.hero .button').first();
    await cta.focus();
    assert.equal(await cta.evaluate(el=>getComputedStyle(el).outlineStyle), 'solid');
    await page.keyboard.press('Enter');
    const projectTop = await page.locator('#projects').evaluate(el=>el.getBoundingClientRect().top);
    assert(projectTop >= await page.locator('header').evaluate(el=>el.getBoundingClientRect().bottom), 'Sticky header covers project anchor');
    assert.equal(await page.locator('html').evaluate(el=>getComputedStyle(el).scrollBehavior), 'auto');
    report.keyboard.push('Skip link, CTA anchors, visible focus, menu Enter/Escape/Tab, closed-menu focus, reduced motion');

    const staticPages = JSON.parse(fs.readFileSync(path.join(root,'Nythara/database/data/static-pages.json')));
    for (const width of [390,1440]) {
      await page.setViewportSize({width,height:1000});
      for (const file of staticPages) {
        if (file === 'Nythara/database/index.html') continue;
        const route = '/' + file.replace(/index\.html$/, '');
        await visit(route); await images(); await geometry(`${route} ${width}`);
        assert.equal(await page.locator('.site-footer').count(), 1);
        assert.equal(await page.locator('.site-footer a[href="https://github.com/Agutroil"]').count(), 1);
        report.staticPages++;
      }
    }
    for (const width of [390,1440]) {
      await page.setViewportSize({width,height:1000});
      for (const route of ['/', '/404.html']) {
        await visit(route);
        const states = width === 390 ? ['closed','open'] : ['desktop'];
        for (const state of states) {
          if (state === 'open') await page.locator('#menu-toggle').click();
          const audit = await new AxeBuilder({page}).withTags(['wcag2a','wcag2aa','wcag21a','wcag21aa']).analyze();
          report.accessibility.push({route,width,state,violations:audit.violations.map(v=>({id:v.id,impact:v.impact,targets:v.nodes.map(n=>n.target)}))});
          console.log(`Portfolio accessibility ${route} ${width} ${state}: ${audit.violations.length}`);
        }
      }
    }
    const noJs = await browser.newContext({javaScriptEnabled:false,viewport:{width:320,height:844}});
    const fallback = await noJs.newPage();
    for (const route of ['/', '/404.html', '/Nythara/']) {
      await fallback.goto(base+route);
      assert(await fallback.locator('header nav').isVisible(), `No-JS navigation ${route}`);
      assert.equal(await fallback.locator('header .menu-toggle:visible').count(),0);
      assert(await fallback.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
    }
    await noJs.close();
    await page.setViewportSize({width:640,height:450});
    for (const route of ['/', '/404.html']) { await visit(route); await geometry(`200% reflow ${route}`); }
    report.keyboard.push('Navigation with JavaScript disabled; 200% reflow');
    assert.deepEqual(report.accessibility.flatMap(a=>a.violations), []);
    assert.deepEqual(report.consoleErrors, []);
    assert.deepEqual(report.resourceErrors, []);
    assert.deepEqual(report.brokenImages, []);
    console.log('Portfolio, shared layout and all static Codex pages: PASS');
  } finally {
    fs.writeFileSync(path.join(output,'report.json'), JSON.stringify(report,null,2)+'\n');
    await browser.close();
  }
})().catch(error=>{console.error(error);process.exitCode=1;});
