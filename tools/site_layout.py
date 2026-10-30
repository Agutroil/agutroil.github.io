"""Small shared fragments for the buildless portfolio and generated Codex."""
from html import escape
import re
from string import Template
from site_assets import ROOT


def database_book() -> str:
    """Reuse the existing Nythara navigation drawing as the single icon source."""
    source = (ROOT / 'Nythara/index.html').read_text()
    match = re.search(r'<svg class="nav-database-mark".*?</svg>', source, re.S)
    if not match:
        raise ValueError('Existing Nythara database book icon was not found')
    return re.sub(r'\s+', ' ', match[0]).replace('nav-database-mark', 'database-button-icon').replace('width="16"', 'width="26"').replace('height="16"', 'height="26"')


def screenshot_dialog(language: str = 'en') -> str:
    """Reuse the existing game screenshot dialog, localizing its two UI labels."""
    source = (ROOT / 'Nythara/index.html').read_text()
    match = re.search(r'  <dialog class="lightbox".*?</dialog>', source, re.S)
    if not match:
        raise ValueError('Existing Nythara screenshot dialog was not found')
    markup = match[0]
    if language == 'de':
        markup = markup.replace('Nythara · in-game image', 'Nythara · Spielaufnahme').replace('aria-label="Close image"', 'aria-label="Bild schließen"')
    return markup


def footer(language: str = 'en', revision: str = '') -> str:
    german = language == 'de'
    rendered = Template((ROOT / 'tools/templates/site-footer.html').read_text()).substitute(
        navigation_label='Fußnavigation' if german else 'Footer navigation',
        home_label='Startseite' if german else 'Home',
        projects_label='Projekte' if german else 'Projects',
        database_label='Datenbank' if german else 'Database',
        detail=f'<span id="footer-source">Game Data Revision: {escape(revision)}</span>' if revision else '')
    return '\n'.join(line.rstrip() for line in rendered.splitlines()) + '\n'
