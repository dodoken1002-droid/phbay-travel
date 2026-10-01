import os
import pathlib
import re
import unittest
from unittest.mock import patch


ROOT = pathlib.Path(__file__).resolve().parent
PLANNER_NAV_HREF = '/penghu-itinerary-recommendations/planner?src=nav'


class PlannerHomeEntryTests(unittest.TestCase):
    def test_every_navigation_copy_links_to_planner(self):
        files = [
            'index.html', 'faq.html', 'neihai-preorder.html', 'preorder.html',
            'privacy.html', 'terms.html', 'tides.html', 'app.py',
        ]
        for name in files:
            with self.subTest(name=name):
                source = (ROOT / name).read_text(encoding='utf-8')
                self.assertIn(PLANNER_NAV_HREF, source)

    def test_home_entries_and_translation_contract(self):
        index = (ROOT / 'index.html').read_text(encoding='utf-8')
        script = (ROOT / 'script.js').read_text(encoding='utf-8')
        i18n = (ROOT / 'i18n.js').read_text(encoding='utf-8')
        self.assertIn('planner?src=home_block', index)
        self.assertIn('planner?src=home_quiz', script)
        self.assertIn("trackQuizCta('${best}','planner')", script)
        for key in ('nav.planner', 'planner.entry.title', 'planner.entry.desc',
                    'planner.entry.cta', 'planner.entry.quizCta'):
            self.assertEqual(i18n.count(f"'{key}'"), 4, key)
        blocks = dict(re.findall(r"^  '?(en|ja|ko|zh-cn)'?: \{(.*?)^  \},?$", i18n, re.S | re.M))
        self.assertEqual(set(blocks), {'en', 'ja', 'ko', 'zh-cn'})
        for lang in ('en', 'ja', 'ko'):
            for key in ('nav.planner', 'planner.entry.cta', 'planner.entry.quizCta'):
                value = re.search(r"'%s':'([^']*)'" % re.escape(key), blocks[lang]).group(1)
                self.assertTrue(value.endswith('(Chinese)'), f'{lang} {key} 必須標示 (Chinese)')
        self.assertNotIn('(Chinese)', blocks['zh-cn'], '簡體中文讀得懂試排器，不需要標示')
        for name in ('faq.html', 'privacy.html', 'terms.html', 'tides.html', 'index.html'):
            source = (ROOT / name).read_text(encoding='utf-8')
            self.assertNotRegex(source, r'i18n\.js\?v=(?!20261001b)',
                                f'{name} 的 i18n.js 版本要更新，否則會吃到舊快取')

    def test_planner_stays_noindex_and_out_of_sitemap_contract(self):
        app = (ROOT / 'app.py').read_text(encoding='utf-8')
        route = app[app.index("@app.route('/penghu-itinerary-recommendations/planner')"):]
        route = route[:route.index('\n@app.route', 1)]
        self.assertIn('<meta name="robots" content="noindex,follow">', route)
        self.assertNotIn('/penghu-itinerary-recommendations/planner', (ROOT / 'robots.txt').read_text(encoding='utf-8'))

    def test_rendered_planner_is_noindex_and_absent_from_sitemap(self):
        os.environ.setdefault('SKIP_SCHEMA_INIT', '1')
        import app as app_module
        client = app_module.app.test_client()
        with patch.object(app_module, 'get_db', side_effect=RuntimeError('no db in test')):
            sitemap = client.get('/sitemap.xml')
            page = client.get('/penghu-itinerary-recommendations/planner')
        xml = sitemap.get_data(as_text=True)
        self.assertEqual(sitemap.status_code, 200)
        self.assertIn('https://www.phbay.info/penghu-itinerary-recommendations</loc>', xml)
        self.assertNotIn('/planner', xml)
        html = page.get_data(as_text=True)
        self.assertIn('<meta name="robots" content="noindex,follow">', html)
        self.assertNotIn('id="itinerary-planner-v1" aria-live', html)


if __name__ == '__main__':
    unittest.main()
