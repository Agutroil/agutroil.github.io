#!/usr/bin/env node
// Real Chromium checks; run a static server first. No browser test framework needed.
const {chromium} = require('playwright');
const AxeBuilder = require('@axe-core/playwright').default;
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const root = path.resolve(__dirname, '..');
const base = process.env.QA_BASE || 'http://127.0.0.1:8792';
const output = process.env.QA_OUTPUT || path.join(root, '.git/nythara-quality/browser');
const read = file => JSON.parse(fs.readFileSync(path.join(root,'Nythara/database/data',file+'.json')));
const metadata = read('metadata');
const all = metadata.categories.flatMap(c=>read(c.key).entries);
const aliases = read('permalinks');
const links = e=>(e.sections||[]).flatMap(s=>s.links||[]);
const key = (type,id)=>`${({boss:'monster',equipment:'item'})[type]||type}/${id}`;
const report=(process.env.QA_FUNCTIONAL_ONLY || process.env.QA_A11Y_ONLY) ? JSON.parse(fs.readFileSync(path.join(output,'report.json'))) : {widths:[],details:0,relatedLinks:0,accessibility:[],functional:[],consoleErrors:[],resourceErrors:[],zoom:[],landscape:false};
fs.mkdirSync(output,{recursive:true});
(async()=>{
 const browser=await chromium.launch({executablePath:process.env.CHROME_PATH||undefined});
 try{
  const context=await browser.newContext({viewport:{width:1440,height:1000},reducedMotion:'reduce',permissions:['clipboard-read','clipboard-write']});
  const page=await context.newPage();
  page.on('pageerror',e=>report.consoleErrors.push(e.message));
  page.on('console',m=>{if(m.type()==='error')report.consoleErrors.push(m.text());});
  page.on('response',r=>{if(r.status()>=400)report.resourceErrors.push({url:r.url(),status:r.status()});});
  page.on('requestfailed',r=>{if(r.failure()?.errorText!=='net::ERR_ABORTED')report.resourceErrors.push({url:r.url(),error:r.failure()?.errorText});});
  const goto=async route=>{
   await page.goto(base+route);
   if(route.startsWith('/Nythara/database/')&&route.split('#')[0]==='/Nythara/database/')await page.waitForSelector('#view-root[aria-busy="false"]');
  };
  const geometry=async label=>{
   const geometry=await page.evaluate(()=>({scroll:document.documentElement.scrollWidth,viewport:innerWidth}));
   assert(geometry.scroll<=geometry.viewport+1,`${label}: document overflow ${JSON.stringify(geometry)}`);
   const outside=await page.locator('main *,.topbar *').evaluateAll(els=>els.filter(el=>{
    if(el.namespaceURI==='http://www.w3.org/2000/svg'||!el.checkVisibility())return false;
    const r=el.getBoundingClientRect();
    if(!r.width||(r.left>=-1&&r.right<=innerWidth+1))return false;
    for(let p=el.parentElement;p;p=p.parentElement)if(['hidden','clip','scroll','auto'].includes(getComputedStyle(p).overflowX))return false;
    return true;
   }).map(el=>({tag:el.tagName,class:el.className,text:el.textContent.trim().slice(0,45)})));
   assert.deepEqual(outside,[],label);
  };
  const decode=async selector=>page.locator(selector+' img').evaluateAll(imgs=>Promise.all(imgs.map(img=>{if(!img.getAttribute('src'))return;img.loading='eager';return img.decode();})));
  const screenshot=async(label,selector)=>{
   await page.locator(selector).scrollIntoViewIfNeeded();
   await page.screenshot({path:path.join(output,label+'.png')});
  };
  if (!process.env.QA_A11Y_ONLY) {
  if (!process.env.QA_FUNCTIONAL_ONLY) {
  for(const width of [320,360,390,430,768,1024,1280,1440,1920,2560]){
   await page.setViewportSize({width,height:1000});
   await goto('/Nythara/');
   await page.waitForSelector('#content-counts a');
   for(const id of ['top','gameplay','world','friends','group','online','codex','gallery']){
    const section=page.locator('#'+id);await section.scrollIntoViewIfNeeded();
    if(id==='codex')await page.waitForSelector('.codex-card');
    await decode('#'+id);await geometry(`Nythara ${id} ${width}`);
    if([390,1440].includes(width))await screenshot(`game-${id}-${width}`,'#'+id);
   }
   await geometry(`Nythara footer ${width}`);
   for(const [label,hash] of [['home',''],['monsters','#monsters'],['monster','#monster/enemy_briarling'],['boss','#monster/enemy_rootbound_seer'],['dungeon','#dungeon/world_moonroot_sanctum'],['equipment','#equipment/weapon_warden_blade']]){
    await goto('/Nythara/database/'+hash);await decode('main');await geometry(`Database ${label} ${width}`);
    if([390,1440].includes(width))await screenshot(`db-${label}-${width}`,label==='home'?'#hero':'#view-root');
   }
   await goto('/Nythara/database/#monsters');
   if(await page.locator('.filter-panel').getAttribute('open')===null){await page.locator('.filter-panel summary').focus();await page.keyboard.press('Enter');}
   await page.locator('#filter-archetype').selectOption('Heavy');
   assert.equal(await page.locator('.entry-card').count(),all.filter(e=>e.type==='monster'&&e.filters?.archetype==='Heavy').length);
   await geometry(`Database filters ${width}`);
   await page.locator('#db-search').fill('Briarling');
   await page.waitForFunction(()=>document.querySelector('.entry-card')?.getAttribute('href')==='#monster/enemy_briarling');
   await geometry(`Database search ${width}`);
   for(const route of ['/Nythara/database/monster/briarling/','/Nythara/database/dungeon/moonroot-sanctum/','/404.html']){
    await goto(route);await decode('main');await geometry(`Static ${route} ${width}`);
   }
   report.widths.push(width);console.log(`Responsive ${width}: PASS`);
  }
  await page.setViewportSize({width:1440,height:1000});
  for(const entry of all){
   await goto('/Nythara/database/#'+entry.type+'/'+entry.id);
   assert.equal(await page.locator('.detail-copy h2').textContent(),entry.name);
   assert.equal(await page.locator('.permalink-link').getAttribute('href'),aliases[`${entry.type}/${entry.id}`]);
   const own=key(entry.type,entry.id);
   const expected=new Set(links(entry).map(l=>key(l.type,l.id)).filter(k=>k!==own));
   for(const other of all)if(key(other.type,other.id)!==own&&links(other).some(l=>key(l.type,l.id)===own))expected.add(key(other.type,other.id));
   const actual=await page.locator('.related-section .entity-link').evaluateAll(es=>es.map(e=>{const [type,...id]=e.hash.slice(1).split('/');return [type,decodeURIComponent(id.join('/'))];}));
   assert.deepEqual(new Set(actual.map(([t,id])=>key(t,id))),expected,entry.id);
   report.details++;report.relatedLinks+=actual.length;
  }
  await goto('/Nythara/database/#items');
  await page.locator('[data-load-more]').click();
  assert.equal(await page.locator('.entry-card').count(),metadata.counts.items);
  await page.locator('#sort-select').selectOption('name-desc');
  const names=await page.locator('.entry-name').allTextContents();
  assert.deepEqual(names,[...names].sort((a,b)=>b.localeCompare(a)));
  await page.locator('#filter-rarity').selectOption('Rare');
  assert.equal(await page.locator('.entry-card').count(),all.filter(e=>e.type==='item'&&e.filters?.rarity==='Rare').length);
  await page.locator('[data-reset-filters]').click();
  assert.equal(await page.locator('.entry-card').count(),12);
  await page.locator('#db-search').fill('zzzz-no-such-adventure');
  await page.waitForSelector('.empty-state');
  assert.equal(await page.locator('.entry-card').count(),0);
  await page.locator('#search-clear').click();
  assert.equal(await page.locator('#db-search').inputValue(),'');
  report.functional.push('Immediate search, no-results state, filters, reset, sorting, incremental loading, all hash routes and relationships');
  }
  await goto('/Nythara/database/#monster/enemy_briarling');
  const before=await page.locator('.detail-record').boundingBox();
  const copyWidth=(await page.locator('[data-copy-link]').boundingBox()).width;
  await page.locator('[data-copy-link]').click();
  await page.waitForFunction(()=>document.querySelector('[data-copy-link]').dataset.copied==='true');
  assert.equal(await page.locator('[data-copy-link]').textContent(),'Copied');
  assert.equal(await page.evaluate(()=>navigator.clipboard.readText()),page.url());
  assert.equal((await page.locator('[data-copy-link]').boundingBox()).width,copyWidth);
  assert.equal((await page.locator('.detail-record').boundingBox()).y,before.y);
  await page.waitForFunction(()=>document.querySelector('[data-copy-link]').textContent==='Copy Link');
  await page.evaluate(()=>{window.readOriginal=navigator.clipboard.readText.bind(navigator.clipboard);Object.defineProperty(navigator,'clipboard',{configurable:true,value:undefined});location.hash='#dungeon/world_moonroot_sanctum';});
  await page.waitForFunction(()=>document.querySelector('.detail-copy h2').textContent==='Moonroot Sanctum');
  await page.locator('[data-copy-link]').click();await page.waitForFunction(()=>document.querySelector('[data-copy-link]').dataset.copied==='true');
  assert.equal(await page.evaluate(()=>window.readOriginal()),page.url());
  await page.evaluate(()=>{document.execCommand=()=>false;location.hash='#monster/enemy_briarling';});
  await page.waitForFunction(()=>document.querySelector('.detail-copy h2').textContent==='Briarling');
  await page.locator('[data-copy-link]').click();
  assert.equal(await page.locator('#share-link').inputValue(),page.url());
  assert(await page.locator('#share-link').evaluate(el=>el===document.activeElement));
  report.functional.push('Copy Link: stable feedback, clipboard, native fallback, manual fallback, live status');
  await goto('/Nythara/');
  await page.keyboard.press('Tab');assert.equal(await page.evaluate(()=>document.activeElement.className),'skip-link');
  await page.keyboard.press('Enter');assert.equal(await page.evaluate(()=>document.activeElement.id),'main');
  const opener=page.locator('#friends .capture-link');await opener.focus();await page.keyboard.press('Enter');
  assert.equal(await page.evaluate(()=>document.activeElement.id),'lightbox-close');
  await page.locator('.brand').evaluate(el=>el.focus());
  assert(await page.evaluate(()=>document.getElementById('lightbox').contains(document.activeElement)));
  for(let i=0;i<4;i++)await page.keyboard.press('Tab');
  assert(!await page.evaluate(()=>document.activeElement.closest('header.topbar')));
  await page.keyboard.press('Escape');assert(await opener.evaluate(el=>el===document.activeElement));
  assert.equal(await page.locator('html').evaluate(el=>getComputedStyle(el).scrollBehavior),'auto');
  report.functional.push('Skip link, modal focus, native focus containment, Escape, opener focus restoration, reduced motion');
  await page.setViewportSize({width:844,height:390});
  for(const route of ['/Nythara/','/Nythara/database/#monsters','/Nythara/database/#dungeon/world_moonroot_sanctum']){await goto(route);await geometry('Landscape '+route);}
  report.landscape=true;
  await page.setViewportSize({width:640,height:450});
  for(const route of ['/Nythara/','/Nythara/database/#monsters','/Nythara/database/#equipment/weapon_warden_blade','/Nythara/database/dungeon/moonroot-sanctum/']){
   await goto(route);await geometry('200% reflow '+route);report.zoom.push(route);
  }
  await goto('/Nythara/database/#monsters');
  if(await page.locator('.filter-panel').getAttribute('open')===null)await page.locator('.filter-panel summary').click();
  await page.locator('#filter-archetype').evaluate(el=>el.options[el.selectedIndex].textContent='Sehr lange deutsche und englische Bezeichnung / exceptionally long label');
  await geometry('Long filter label');
  await goto('/Nythara/database/#monster/enemy_briarling');
  await page.locator('.detail-copy h2').evaluate(el=>el.textContent='AußergewöhnlichLangerKreaturennameWithoutWordBreaks');await geometry('Long creature name');
  }
  await context.close();
  report.accessibility = [];
  for(const width of [390,1440]){
   const auditContext = await browser.newContext({viewport:{width,height:1000},reducedMotion:'reduce'});
   for(const [label,route] of [['game','/Nythara/'],['database','/Nythara/database/'],['monster','/Nythara/database/#monster/enemy_briarling'],['boss','/Nythara/database/#boss/enemy_rootbound_seer'],['dungeon','/Nythara/database/#dungeon/world_moonroot_sanctum'],['equipment','/Nythara/database/#equipment/weapon_warden_blade'],['static','/Nythara/database/monster/briarling/'],['404','/404.html']]){
    const auditPage=await auditContext.newPage();
    await auditPage.goto(base+route);
    if(route.split('#')[0]==='/Nythara/database/')await auditPage.waitForSelector('#view-root[aria-busy="false"]');
    const axe=await new AxeBuilder({page:auditPage}).withTags(['wcag2a','wcag2aa','wcag21a','wcag21aa']).analyze();
    report.accessibility.push({label,width,violations:axe.violations.map(v=>({id:v.id,impact:v.impact,targets:v.nodes.map(n=>n.target)}))});
    await auditPage.close();
    console.log(`Accessibility ${label} ${width}: ${axe.violations.length} violations`);
   }
   await auditContext.close();
  }
  const noJs=await browser.newContext({javaScriptEnabled:false,viewport:{width:390,height:844},deviceScaleFactor:3});
  const fallback=await noJs.newPage();
  for(const route of ['/Nythara/database/','/Nythara/database/entries/','/Nythara/database/equipment/warden-blade/']){
   await fallback.goto(base+route);assert(await fallback.locator('h1').isVisible());
   if(route==='/Nythara/database/')assert(await fallback.locator('noscript a[href="./entries/"]').isVisible());
  }
  await noJs.close();
  const retryContext=await browser.newContext();
  try{
   const retryPage=await retryContext.newPage();
   await retryPage.route('**/data/catalogue.json*',route=>route.fulfill({status:503,body:'Temporarily unavailable'}));
   await retryPage.goto(base+'/Nythara/database/');
   await retryPage.waitForSelector('[data-retry]');
   await retryPage.unroute('**/data/catalogue.json*');
   await retryPage.locator('[data-retry]').click();
   await retryPage.waitForSelector('#view-root[aria-busy="false"] .category-overview');
   assert.equal(await retryPage.locator('[data-retry]').count(),0);
   report.functional.push('Data-load failure and retry restore the prerendered home');
  }finally{await retryContext.close();}
  const zoomContext=await chromium.launchPersistentContext(path.join(output,'zoom-profile'),{
   executablePath:process.env.CHROME_PATH||undefined,channel:process.env.CHROME_PATH?undefined:'chromium',
   viewport:null,reducedMotion:'reduce',args:['--window-size=1280,900']});
  try{
   const zoomPage=await zoomContext.newPage();
   await zoomPage.goto('chrome://settings/appearance');
   await zoomPage.evaluate(()=>chrome.settingsPrivate.setDefaultZoom(2));
   report.browserZoom={factor:2,routes:[]};
   for(const route of ['/Nythara/','/Nythara/database/','/Nythara/database/#monsters','/Nythara/database/#dungeon/world_moonroot_sanctum','/Nythara/database/monster/briarling/','/404.html']){
    await zoomPage.goto(base+route);
    if(route.split('#')[0]==='/Nythara/database/')await zoomPage.waitForSelector('#view-root[aria-busy="false"]');
    const dimensions=await zoomPage.evaluate(()=>({cssWidth:innerWidth,windowWidth:outerWidth,dpr:devicePixelRatio,scrollWidth:document.documentElement.scrollWidth}));
    assert.equal(dimensions.dpr,2);
    assert(dimensions.cssWidth<=dimensions.windowWidth/1.9);
    assert(dimensions.scrollWidth<=dimensions.cssWidth+1,`200% browser zoom ${route}`);
    report.browserZoom.routes.push({route,...dimensions});
   }
   await zoomPage.screenshot({path:path.join(output,'browser-zoom-200.png')});
  }finally{await zoomContext.close();}
  assert.deepEqual(report.accessibility.flatMap(r=>r.violations),[]);
  assert.deepEqual(report.consoleErrors,[]);assert.deepEqual(report.resourceErrors,[]);
  console.log('Keyboard, database, static fallback, accessibility and responsive QA: PASS');
 }finally{fs.writeFileSync(path.join(output,'report.json'),JSON.stringify(report,null,2)+'\n');await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
