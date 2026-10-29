"""Semantic checks for generated, JavaScript-independent Codex pages."""
from hashlib import sha256
import json
import unittest

from build_nythara_pages import DATA, ROOT, build_outputs, entity_key, slug
from check_website import Document


class StaticPageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.before = {p: sha256(p.read_bytes()).hexdigest() for p in DATA.glob('*.json')}
        cls.outputs = build_outputs()
        cls.aliases = json.loads(cls.outputs[DATA / 'permalinks.json'])

    def test_each_record_has_one_resolving_canonical_without_duplicate_alias_pages(self):
        meta = json.loads((DATA / 'metadata.json').read_text())
        keys = {}
        for category in meta['categories']:
            for entry in json.loads((DATA / (category['key'] + '.json')).read_text())['entries']:
                path = self.aliases[f'{entry["type"]}/{entry["id"]}']
                self.assertNotIn('#', path)
                self.assertIn(ROOT / path.lstrip('/') / 'index.html', self.outputs)
                keys.setdefault(entity_key(entry['type'], entry['id']), set()).add(path)
        self.assertTrue(all(len(paths) == 1 for paths in keys.values()))
        self.assertEqual(len({path for paths in keys.values() for path in paths}), len(keys))

    def test_static_content_and_relationships_do_not_require_javascript(self):
        for path in set(self.aliases.values()):
            doc = Document(self.outputs[ROOT / path.lstrip('/') / 'index.html'])
            self.assertEqual(doc.headings[0], 1, path)
            self.assertEqual(doc.headings.count(1), 1, path)
            self.assertTrue(all(script['type'] == 'application/ld+json' for script in doc.scripts), path)
            schemas = json.loads(doc.scripts[0]['text'])['@graph']
            crumbs = next(s for s in schemas if s['@type'] == 'BreadcrumbList')['itemListElement']
            self.assertEqual([c['position'] for c in crumbs], [1, 2, 3, 4])
            self.assertEqual(crumbs[-1]['item'], doc.canonicals[0])

    def test_landing_has_usable_catalogue_content_before_javascript(self):
        html = self.outputs[ROOT / 'Nythara/database/index.html']
        doc = Document(html)
        self.assertIn('Prepare for the next adventure.', html)
        self.assertIn('./entries/', doc.refs)
        metadata = json.loads((DATA / 'metadata.json').read_text())
        self.assertIn(f'<strong id="snapshot-count">{metadata["total_primary_entries"]}</strong>', html)
        for category in metadata['categories']:
            self.assertIn('#' + category['key'], doc.refs)

    def test_build_preserves_public_source_json_and_slugs_use_stable_ids(self):
        self.assertEqual(self.before, {p: sha256(p.read_bytes()).hexdigest() for p in DATA.glob('*.json')})
        self.assertEqual(slug('enemy_briarling'), 'briarling')
        self.assertEqual(slug('world_moonroot_sanctum'), 'moonroot-sanctum')
        self.assertEqual(slug('weapon_warden_blade'), 'warden-blade')


if __name__ == '__main__': unittest.main()
