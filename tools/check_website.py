#!/usr/bin/env python3
"""Fast static checks for the published GitHub Pages files; no network required."""
from __future__ import annotations

import argparse
from collections import Counter
from hashlib import sha256
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import subprocess
from urllib.parse import unquote, urlsplit
import xml.etree.ElementTree as ET

from site_assets import ROOT, IMAGE_EXTENSIONS, image_size

PUBLIC_EXTENSIONS = IMAGE_EXTENSIONS | {'.html', '.css', '.js', '.json', '.txt', '.xml'}


def published_files() -> list[Path]:
    excluded = []
    config = ROOT / '_config.yml'
    if config.exists():
        excluded = re.findall(r'^  - (.+)$', config.read_text(), re.M)
    candidates = subprocess.check_output(['git', 'ls-files', '--cached', '--others', '--exclude-standard'], cwd=ROOT, text=True).splitlines()
    return sorted({ROOT / name for name in candidates if Path(name).suffix.lower() in PUBLIC_EXTENSIONS
                   and not any(part.startswith('.') for part in Path(name).parts)
                   and not any(name == item or name.startswith(item + '/') for item in excluded)
                   and (ROOT / name).is_file()})


class Document(HTMLParser):
    def __init__(self, text: str):
        super().__init__(convert_charrefs=True)
        self.ids = []; self.refs = []; self.images = []; self.meta = {}; self.canonicals = []; self.scripts = []
        self.titles = []; self.title = None; self.script = None; self.headings = []
        self.errors = []
        self.feed(text)

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if 'id' in a: self.ids.append(a['id'])
        for key in ['href', 'src', 'poster']:
            if a.get(key): self.refs.append(a[key])
        if a.get('srcset'):
            self.refs.extend(item.strip().split()[0] for item in a['srcset'].split(','))
        if tag == 'meta': self.meta.setdefault(a.get('name', a.get('property')), []).append(a.get('content', ''))
        if tag == 'link' and a.get('rel') == 'canonical': self.canonicals.append(a.get('href'))
        if tag == 'img': self.images.append(a)
        if tag == 'a' and a.get('target') == '_blank' and not {'noopener', 'noreferrer'}.issubset(set(a.get('rel', '').split())):
            self.errors.append('New-tab link needs noopener noreferrer')
        if a.get('tabindex', '').isdigit() and int(a['tabindex']) > 0: self.errors.append('Positive tabindex')
        if tag == 'title': self.title = ''
        if tag == 'script' and a.get('src') and urlsplit(a['src']).netloc: self.errors.append('External runtime JavaScript')
        if tag == 'script' and not a.get('src'): self.script = {'type': a.get('type'), 'text': ''}
        if re.fullmatch('h[1-6]', tag): self.headings.append(int(tag[1]))

    def handle_data(self, text):
        if self.title is not None: self.title += text
        if self.script is not None: self.script['text'] += text

    def handle_endtag(self, tag):
        if tag == 'title' and self.title is not None: self.titles.append(self.title); self.title = None
        if tag == 'script' and self.script is not None: self.scripts.append(self.script); self.script = None


def audit() -> tuple[dict, list[str]]:
    files = published_files(); errors = []; links = 0; images = 0
    from build_nythara_pages import build_outputs
    for generated, expected in build_outputs().items():
        if not generated.is_file() or generated.read_text() != expected:
            errors.append(f'Stale generated output: {generated.relative_to(ROOT)}')
    file_set = set(files)
    documents = {p: Document(p.read_text()) for p in files if p.suffix == '.html'}
    budgets = json.loads((ROOT / 'tools/website-budgets.json').read_text())
    aliases = json.loads((ROOT / 'Nythara/database/data/permalinks.json').read_text())
    meta = json.loads((ROOT / 'Nythara/database/data/metadata.json').read_text())
    categories = {c['key'] for c in meta['categories']}
    canonicals = []

    def fail(path, message): errors.append(f'{path.relative_to(ROOT)}: {message}')

    def check_ref(ref, source):
        nonlocal links
        parsed = urlsplit(ref)
        if parsed.scheme in {'data', 'mailto', 'tel'}: return
        if parsed.netloc and parsed.netloc != 'agutroil.github.io': return
        if parsed.scheme and parsed.scheme not in {'http', 'https'}:
            fail(source, 'Unsupported link protocol'); return
        target = (ROOT / unquote(parsed.path).lstrip('/') if parsed.path.startswith('/') else source.parent / unquote(parsed.path)) if parsed.path else source
        target = target.resolve()
        if target.is_dir(): target = target / 'index.html'
        links += 1
        if target not in file_set:
            fail(source, f'Missing or excluded resource: {ref}'); return
        fragment = unquote(parsed.fragment)
        if not fragment or target not in documents: return
        if target == ROOT / 'Nythara/database/index.html' and (fragment in categories | {'search', 'top', 'main'} or fragment in aliases): return
        if fragment not in documents[target].ids: fail(source, f'Unknown fragment: {ref}')

    for path, doc in documents.items():
        if re.fullmatch(r'google[a-z0-9]+\.html', path.name): continue
        if len(doc.titles) != 1 or not doc.titles[0].strip(): fail(path, 'Expected one nonempty title')
        if len(doc.canonicals) != 1: fail(path, 'Expected one canonical')
        else:
            canonicals.append(doc.canonicals[0])
            relative = str(path.relative_to(ROOT))
            expected = '/' + (relative[:-10] if relative.endswith('index.html') else relative)
            if doc.canonicals[0] != 'https://agutroil.github.io' + expected: fail(path, 'Canonical does not match the public URL')
        for key in ['description', 'viewport', 'robots', 'theme-color']:
            if len(doc.meta.get(key, [])) != 1 or not doc.meta[key][0].strip(): fail(path, f'Missing/duplicate metadata: {key}')
        if 'noindex' not in doc.meta.get('robots', [''])[0]:
            for key in ['og:title', 'og:description', 'og:type', 'og:url', 'og:image', 'og:image:width', 'og:image:height', 'twitter:card', 'twitter:title', 'twitter:description', 'twitter:image']:
                if len(doc.meta.get(key, [])) != 1: fail(path, f'Missing/duplicate social metadata: {key}')
            if doc.meta.get('twitter:card') != ['summary_large_image']: fail(path, 'Expected large Twitter card')
        if doc.headings.count(1) != 1: fail(path, 'Expected one h1')
        for before, after in zip(doc.headings, doc.headings[1:]):
            if after > before + 1: fail(path, f'Heading level skips h{before} → h{after}')
        if len(doc.ids) != len(set(doc.ids)): fail(path, 'Duplicate IDs')
        for error in doc.errors: fail(path, error)
        for ref in doc.refs: check_ref(ref, path)
        for key in ['og:image', 'twitter:image']:
            for ref in doc.meta.get(key, []): check_ref(ref, path)
        for image in doc.images:
            images += 1
            if 'alt' not in image: fail(path, 'Image without alt')
            if image.get('id') == 'lightbox-image': continue  # Assigned from the opener before showModal().
            if not all(image.get(k, '').isdigit() and int(image[k]) > 0 for k in ['width', 'height']): fail(path, f'Image without dimensions: {image.get("src")}')
        for script in doc.scripts:
            if script['type'] == 'application/ld+json':
                try: json.loads(script['text'])
                except ValueError: fail(path, 'Invalid JSON-LD')
            else:
                result = subprocess.run(['node', '--check'], input=script['text'], text=True, capture_output=True)
                if result.returncode: fail(path, 'Invalid inline JavaScript')

    if len(canonicals) != len(set(canonicals)): errors.append('Duplicate canonical pages')
    for path in files:
        relative = str(path.relative_to(ROOT))
        if path.suffix in IMAGE_EXTENSIONS:
            width, height = image_size(path)
            if min(width, height) <= 0: fail(path, 'Invalid image dimensions')
            if path.stat().st_size > budgets['image_max_bytes']: fail(path, 'Image size budget exceeded')
            if 'background' in path.name and path.stat().st_size > budgets['background_max_bytes']: fail(path, 'Background budget exceeded')
        if path.suffix == '.js':
            result = subprocess.run(['node', '--check', str(path)], text=True, capture_output=True)
            if result.returncode: fail(path, 'Invalid JavaScript')
        if path.suffix in {'.css', '.js'}:
            for ref in re.findall(r'url\(\s*[\"\']?([^\"\')\s]+)', path.read_text()): check_ref(ref, path)
        if path.suffix in {'.html', '.css', '.js', '.json', '.txt', '.xml', '.svg'}:
            text = path.read_text()
            patterns = {
                'private repository': r'(?:github\.com|raw\.githubusercontent\.com)/Agutroil/Nythara\b',
                'private API': r'api\.github\.com[^\s\"\']*Nythara',
                'local filesystem path': r'/home/deister|file://',
                'secret': r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----|\bgh[pousr]_[A-Za-z0-9]{20,}|\bgithub_pat_[A-Za-z0-9_]{20,}|\bsk-[A-Za-z0-9_-]{24,}|(?:password|access_token|credential)\s*[=:]\s*[\"\'][^\"\']{8,}',
                'tracking': r'googletagmanager|google-analytics|connect\.facebook\.net|hotjar|plausible\.io/js',
            }
            if relative.startswith('Nythara/'):
                patterns.update({'unsupported guild claim': r'sprint[ -]?26|persistent guild|guild roles|guild persistence|guild management',
                    'source marketing': r'open[ -]source|source code|github repository|view source|(?-i:\bMIT\b)|\bclone\b|\bfork\b'})
            for label, pattern in patterns.items():
                if re.search(pattern, text, re.I): fail(path, label)
        if path.suffix == '.json':
            try: json.loads(path.read_text())
            except ValueError: fail(path, 'Invalid JSON')
    for relative, expected in budgets['protected_assets'].items():
        if sha256((ROOT / relative).read_bytes()).hexdigest() != expected: errors.append(f'Protected game/green asset changed: {relative}')
    sitemap = ET.parse(ROOT / 'sitemap.xml')
    urls = [node.text for node in sitemap.findall('.//{*}loc')]
    if len(urls) != len(set(urls)): errors.append('Duplicate sitemap URLs')
    expected_urls = {doc.canonicals[0] for doc in documents.values() if len(doc.canonicals) == 1 and 'noindex' not in doc.meta.get('robots', [''])[0]}
    if set(urls) != expected_urls: errors.append('Sitemap and indexable canonicals differ')
    for url in urls:
        if urlsplit(url).fragment: errors.append('Hash route in sitemap')
        check_ref(url, ROOT / 'sitemap.xml')
    if meta['source_short_commit'] != 'a218110': errors.append('Unexpected game data revision')
    for key in aliases:
        check_ref(aliases[key], ROOT / 'Nythara/database/index.html')
    summary = {'production_files': len(files), 'published_bytes': sum(p.stat().st_size for p in files),
        'nythara_bytes': sum(p.stat().st_size for p in files if p.is_relative_to(ROOT / 'Nythara')),
        'database_bytes': sum(p.stat().st_size for p in files if p.is_relative_to(ROOT / 'Nythara/database')),
        'html_bytes': sum(p.stat().st_size for p in files if p.suffix == '.html'),
        'css_bytes': sum(p.stat().st_size for p in files if p.suffix == '.css'),
        'js_bytes': sum(p.stat().st_size for p in files if p.suffix == '.js'),
        'image_bytes': sum(p.stat().st_size for p in files if p.suffix in IMAGE_EXTENSIONS),
        'html_pages': len(documents), 'images_in_html': images, 'internal_references_checked': links,
        'sitemap_urls': len(urls), 'privacy_findings': 0 if not errors else None,
        'largest_20': [{'path': str(p.relative_to(ROOT)), 'bytes': p.stat().st_size} for p in sorted(files, key=lambda p: p.stat().st_size, reverse=True)[:20]]}
    if summary['published_bytes'] > budgets['site_max_bytes']: errors.append('Published site budget exceeded')
    if summary['js_bytes'] > budgets['runtime_js_max_bytes']: errors.append('Runtime JavaScript budget exceeded')
    return summary, errors


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--report', action='store_true', help='Write the deterministic asset report in docs.')
    parser.add_argument('--json-output', type=Path)
    args = parser.parse_args()
    summary, errors = audit()
    if args.json_output: args.json_output.write_text(json.dumps({**summary, 'errors': errors}, indent=2) + '\n')
    if args.report:
        lines = ['# Published asset sizes', '', 'Generated by `python3 tools/check_website.py --report`. Sizes exclude the development tooling and historical originals listed in `_config.yml`; those originals stay in Git.', '', '| Scope | Bytes | MiB |', '| --- | ---: | ---: |']
        for key in ['published_bytes', 'nythara_bytes', 'database_bytes', 'html_bytes', 'css_bytes', 'js_bytes', 'image_bytes']:
            value = summary[key]; lines.append(f'| {key.replace("_bytes", "").replace("_", " ")} | {value:,} | {value / 1048576:.3f} |')
        lines += ['', '## Largest 20 published assets', '', '| Asset | Bytes |', '| --- | ---: |']
        lines += [f'| `{row["path"]}` | {row["bytes"]:,} |' for row in summary['largest_20']]
        lines += ['', '## Largest tracked files (including preserved originals)', '', '| File | Bytes |', '| --- | ---: |']
        tracked = [ROOT / name for name in subprocess.check_output(['git', 'ls-files'], cwd=ROOT, text=True).splitlines() if (ROOT / name).is_file()]
        lines += [f'| `{path.relative_to(ROOT)}` | {path.stat().st_size:,} |' for path in sorted(tracked, key=lambda p:p.stat().st_size, reverse=True)[:20]]
        lines += ['', f'Checked {summary["production_files"]} files, {summary["sitemap_urls"]} sitemap URLs and {summary["internal_references_checked"]} internal references.', '']
        (ROOT / 'docs/website-asset-sizes.md').write_text('\n'.join(lines))
    print(json.dumps({key: value for key, value in summary.items() if key != 'largest_20'}, indent=2))
    for error in errors: print('FAIL:', error)
    if errors: raise SystemExit(1)


if __name__ == '__main__': main()
