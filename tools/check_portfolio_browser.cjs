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
const report = {widths:[], staticPages:0, accessibility:[], keyboard:[], lightbox:[], consoleErrors:[], resourceErrors:[], brokenImages:[]};
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
      // The closed modal has no source until an opener supplies its full image.
      return imgs.filter(img => !(img.id === 'lightbox-image' && !img.getAttribute('src')) && !img.naturalWidth).map(img => img.src);
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
      await visit('/');
      const database = page.getByRole('link', {name:'Datenbank öffnen', exact:true});
      assert.equal(await database.getAttribute('href'), '/Nythara/database/');
      assert(await database.locator('svg[aria-hidden="true"]').isVisible());
      const buttonBox = await database.boundingBox();
      assert(buttonBox.height >= 44);
      assert.equal(await database.locator('span').first().evaluate(el=>{
        const range = document.createRange(); range.selectNodeContents(el); return range.getClientRects().length;
      }), 1, `Database label wraps ${width}`);
      const github = page.locator('#nav-links a[href="https://github.com/Agutroil"]');
      assert.equal(await github.locator('[aria-hidden="true"]').textContent(), '↗');

      const opener = page.locator('.project-preview a[data-lightbox]');
      const dialog = page.locator('#lightbox');
      for (const method of ['button', 'escape', 'overlay']) {
        await opener.scrollIntoViewIfNeeded();
        await opener.focus();
        const before = await page.evaluate(()=>({x:scrollX,y:scrollY,url:location.href,history:history.length}));
        if (method === 'escape') await page.keyboard.press('Enter');
        else await opener.click();
        await page.locator('#lightbox-image').evaluate(img=>img.decode());
        assert(await dialog.isVisible());
        assert.equal(await page.evaluate(()=>document.activeElement.id), 'lightbox-close');
        assert.equal(await page.getByRole('dialog', {name:'Aktuelle Nythara-Spielaufnahme'}).count(), 1);
        assert.equal(await page.locator('#lightbox-close').getAttribute('aria-label'), 'Bild schließen');
        const box = await dialog.boundingBox();
        assert(box.x >= 0 && box.x + box.width <= width && box.y >= 0 && box.y + box.height <= 1000);
        assert(await dialog.evaluate(el=>el.scrollHeight<=el.clientHeight&&el.scrollWidth<=el.clientWidth));
        const closeBox = await page.locator('#lightbox-close').boundingBox();
        assert(closeBox.width >= 44 && closeBox.height >= 44);
        assert.equal(await page.locator('#lightbox-image').evaluate(img=>getComputedStyle(img).objectFit), 'contain');
        await page.locator('#lightbox-image').click();
        assert(await dialog.evaluate(el=>el.open), 'Image click must keep dialog open');
        await page.mouse.move(1,1); await page.mouse.wheel(0,400);
        await page.waitForTimeout(50);
        assert.equal(await page.evaluate(()=>scrollY), before.y, `Background scroll ${width}`);
        await page.locator('.brand').evaluate(el=>el.focus());
        assert(await page.evaluate(()=>document.getElementById('lightbox').contains(document.activeElement)));
        if (method === 'button') await page.getByRole('button', {name:'Bild schließen'}).click();
        else if (method === 'escape') await page.keyboard.press('Escape');
        else await page.mouse.click(1,1);
        await page.waitForFunction(el=>!document.getElementById('lightbox').open&&document.activeElement===el,await opener.elementHandle());
        assert.deepEqual(await page.evaluate(()=>({x:scrollX,y:scrollY,url:location.href,history:history.length})), before, `Position/URL/history ${width} ${method}`);
        report.lightbox.push({width,method,status:'PASS'});
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
        const states = route === '/' ? (width === 390 ? ['closed','open','lightbox'] : ['desktop','lightbox']) : (width === 390 ? ['closed','open'] : ['desktop']);
        for (const state of states) {
          if (state === 'open') await page.locator('#menu-toggle').click();
          if (state === 'lightbox') {
            if (await page.locator('#menu-toggle').getAttribute('aria-expanded') === 'true') await page.locator('#menu-toggle').click();
            await page.locator('.project-preview a[data-lightbox]').click();
            await page.locator('#lightbox-image').evaluate(img=>img.decode());
          }
          const audit = await new AxeBuilder({page}).withTags(['wcag2a','wcag2aa','wcag21a','wcag21aa']).analyze();
          report.accessibility.push({route,width,state,violations:audit.violations.map(v=>({id:v.id,impact:v.impact,targets:v.nodes.map(n=>n.target)}))});
          console.log(`Portfolio accessibility ${route} ${width} ${state}: ${audit.violations.length}`);
          if (state === 'lightbox') await page.keyboard.press('Escape');
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
      if (route === '/') assert((await fallback.locator('.project-preview a').getAttribute('href')).endsWith('/current-player-equipped-adventurer.webp'));
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
