"""Small shared fragments for the buildless portfolio and generated Codex."""
from html import escape
from string import Template
from site_assets import ROOT


def footer(language: str = 'en', revision: str = '') -> str:
    german = language == 'de'
    rendered = Template((ROOT / 'tools/templates/site-footer.html').read_text()).substitute(
        navigation_label='Fußnavigation' if german else 'Footer navigation',
        home_label='Startseite' if german else 'Home',
        projects_label='Projekte' if german else 'Projects',
        database_label='Datenbank' if german else 'Database',
        detail=f'<span id="footer-source">Game Data Revision: {escape(revision)}</span>' if revision else '')
    return '\n'.join(line.rstrip() for line in rendered.splitlines()) + '\n'
