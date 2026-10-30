#!/usr/bin/env node
// Measure standard Lighthouse mobile and desktop profiles, with no score overrides.
const {execFileSync} = require('node:child_process');
const fs = require('node:fs');
const path = require('node:path');
const root = path.resolve(__dirname, '..');
const output = process.env.QA_OUTPUT || path.join(root, '.git/nythara-quality/lighthouse');
const base = process.env.QA_BASE || 'http://127.0.0.1:8792';
const cli = path.join(path.dirname(require.resolve('lighthouse/package.json')), 'cli/index.js');
fs.mkdirSync(output, {recursive:true});
const rows = [];
for (const profile of (process.env.QA_PROFILES || 'mobile,desktop').split(',')) {
  for (const [page, route] of [['Homepage','/'],['Nythara','/Nythara/'],['Database','/Nythara/database/']].filter(([page])=>!process.env.QA_PAGES||process.env.QA_PAGES.split(',').includes(page))) {
    const filename = path.join(output, `${page.toLowerCase()}-${profile}.json`);
    const args = [cli, base+route, '--only-categories=performance,accessibility,best-practices,seo', '--output=json', `--output-path=${filename}`, '--chrome-flags=--headless --no-sandbox', '--quiet'];
    if(profile==='desktop')args.push('--preset=desktop');
    execFileSync(process.execPath, args, {stdio:'inherit', env:{...process.env, CHROME_PATH:process.env.CHROME_PATH || '/usr/bin/google-chrome'}});
    const report = JSON.parse(fs.readFileSync(filename));
    const row = {page,profile,url:base+route,lighthouseVersion:report.lighthouseVersion,
      ...Object.fromEntries(Object.entries(report.categories).map(([key, value])=>[key,Math.round(value.score*100)])),
      benchmarkIndex:report.environment?.benchmarkIndex,
      LCP:report.audits['largest-contentful-paint'].numericValue,
      CLS:report.audits['cumulative-layout-shift'].numericValue,
      TBT:report.audits['total-blocking-time'].numericValue,
      warnings:report.runWarnings};
    rows.push(row);console.log(JSON.stringify(row));
    fs.writeFileSync(path.join(output,'summary.json'),JSON.stringify(rows,null,2)+'\n');
  }
}
