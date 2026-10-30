#!/usr/bin/env python3
"""Build the portfolio and shared footer; never reads another repository."""
import argparse
import json
import re
from string import Template

from site_assets import ROOT
from site_layout import database_book, footer, screenshot_dialog


def build_outputs():
    templates = ROOT / 'tools/templates'
    header = (templates / 'portfolio-header.html').read_text().rstrip()
    person = {'@type': 'Person', '@id': 'https://agutroil.github.io/#person',
              'name': 'Anton Deister', 'alternateName': 'Agutroil', 'url': 'https://agutroil.github.io/',
              'image': 'https://agutroil.github.io/assets/anton-deister-profile.webp',
              'sameAs': ['https://github.com/Agutroil'],
              'knowsAbout': ['Linux', 'Debian', 'Software Development', 'Game Development',
                             'Web Development', 'Godot', 'Programming']}
    schema = {'@context': 'https://schema.org', '@graph': [person,
              {'@type': 'WebSite', '@id': 'https://agutroil.github.io/#website',
               'name': 'Agutroil', 'url': 'https://agutroil.github.io/',
               'inLanguage': 'de', 'author': {'@id': person['@id']}},
              {'@type': 'ProfilePage', 'url': 'https://agutroil.github.io/',
               'name': 'Anton Deister | Agutroil – Entwickler, Linux, Games & Web',
               'mainEntity': {'@id': person['@id']},
               'isPartOf': {'@id': 'https://agutroil.github.io/#website'}}]}
    outputs = {ROOT / 'index.html': Template((templates / 'portfolio-home.html').read_text()).substitute(
        header=header.replace('<a href="/">Startseite</a>', '<a href="/" aria-current="page">Startseite</a>', 1),
        footer=footer('de'), database_book=database_book(), lightbox=screenshot_dialog('de'),
        structured_data=json.dumps(schema, ensure_ascii=False, indent=2)),
        ROOT / '404.html': Template((templates / '404.html').read_text()).substitute(header=header, footer=footer('de'))}
    # Only synchronize this marked fragment; the hand-authored game page stays editable.
    game = ROOT / 'Nythara/index.html'
    text = game.read_text()
    pattern = r'  <!-- Shared footer:.*?  <!-- End shared footer -->\n?'
    if not re.search(pattern, text, re.S):
        raise ValueError('Shared footer markers missing from Nythara/index.html')
    outputs[game] = re.sub(pattern, lambda _: footer(), text, count=1, flags=re.S)
    return outputs


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    outputs = build_outputs()
    changed = [p for p, content in outputs.items() if not p.exists() or p.read_text() != content]
    if args.check and changed:
        raise SystemExit('Regenerate shared layout: ' + ', '.join(str(p.relative_to(ROOT)) for p in changed))
    if not args.check:
        for path in changed:
            path.write_text(outputs[path])
    # Generate from the approved public JSON only, including the complete sitemap.
    from build_nythara_pages import main as build_codex
    build_codex()
    print('Portfolio and shared layout: current.')


if __name__ == '__main__':
    main()
