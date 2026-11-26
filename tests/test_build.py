import importlib.util
import json
import tempfile
import unittest
import xml.etree.ElementTree as ET
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlparse

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('build', ROOT / 'scripts/build.py')
build = importlib.util.module_from_spec(spec)
spec.loader.exec_module(build)

class Links(HTMLParser):
    def __init__(self):
        super().__init__(); self.targets = []
    def handle_starttag(self, tag, attrs):
        for key, value in attrs:
            if key in ('href', 'src') and value and value.startswith('/') and not value.startswith('//'):
                self.targets.append(value)

class PublicationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        build.build()

    def test_every_local_link_resolves(self):
        for page in (ROOT / '_site').rglob('*.html'):
            parser = Links(); parser.feed(page.read_text())
            for link in parser.targets:
                path = unquote(urlparse(link).path).lstrip('/')
                target = ROOT / '_site' / path
                if target.is_dir(): target /= 'index.html'
                self.assertTrue(target.is_file(), f'{page}: {link}')

    def test_content_validation_rejects_duplicate_ids_and_unsafe_urls(self):
        original = build.load_articles()
        for field, value in [('id', original[1]['id']), ('url', 'javascript:alert(1)')]:
            items = json.loads(json.dumps(original)); items[0][field] = value
            with tempfile.TemporaryDirectory() as td:
                f = Path(td) / 'bad.json'; f.write_text(json.dumps(items))
                with self.assertRaises(ValueError): build.load_articles(f)

    def test_both_languages_have_stable_pages(self):
        for article in build.load_articles():
            for lang in ('zh', 'en'):
                page = ROOT / '_site' / build.route(lang, article['id']).lstrip('/') / 'index.html'
                text = page.read_text()
                self.assertIn(build.esc(article['original']), text)
                self.assertIn(build.esc(article['title'][lang]), text)
                self.assertIn(article['published'], text)
                self.assertNotIn('api_key', text.lower())

    def test_feed_and_sitemap_are_valid_xml(self):
        for file in ('feed.xml', 'sitemap.xml'):
            ET.parse(ROOT / '_site' / file)

    def test_user_text_is_escaped(self):
        self.assertEqual(build.esc('<script>'), '&lt;script&gt;')

    def test_editor_is_isolated_and_article_links_select_the_note(self):
        for lang, prefix in [('zh', ''), ('en', '/en')]:
            editor = (ROOT / '_site' / (prefix.lstrip('/') + '/' if prefix else '') / 'editor/index.html').read_text()
            self.assertIn('Content-Security-Policy', editor)
            self.assertIn('noindex,nofollow', editor)
            self.assertIn('/assets/note-editor.mjs', editor)
            self.assertNotIn('/assets/app.js', editor)
            self.assertNotIn('giscus.app', editor)
            self.assertIn('type="password"', editor)
            for article in build.load_articles():
                page = (ROOT / '_site' / build.route(lang, article['id']).lstrip('/') / 'index.html').read_text()
                self.assertIn(f'{prefix}/editor/?article={article["id"]}', page)
        index = json.loads((ROOT / '_site/editor/articles.json').read_text())
        self.assertEqual({a['id'] for a in index}, {a['id'] for a in build.load_articles()})

if __name__ == '__main__': unittest.main()
