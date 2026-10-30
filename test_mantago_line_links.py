"""官網 LINE 按鈕一律走 MantaGO 對話互動引流（自動貼標），並載入 line-cta.js 送 GA4。"""
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).parent
OLD = 'line.me/R/ti/p/@phbay2018'

PAGE_LINKS = {
    'index.html': ['https://go.mantago.co/QnBsyj', 'https://go.mantago.co/bDsNKJ'],
    'faq.html': ['https://go.mantago.co/QnBsyj'],
    'penghu-autumn-winter.html': ['https://go.mantago.co/iCy82S'],
    'tides.html': ['https://go.mantago.co/nMG8Tp'],
    'preorder.html': ['https://go.mantago.co/QnBsyj'],
    'neihai-preorder.html': ['https://go.mantago.co/QnBsyj'],
    'qigui/index.html': ['https://go.mantago.co/QnBsyj'],
    'script.js': ['https://go.mantago.co/QnBsyj', 'https://go.mantago.co/4ATZyb'],
    'itinerary-quiz.js': ['https://go.mantago.co/4ATZyb'],
    'pillar_pages.py': ['https://go.mantago.co/QnBsyj', 'https://go.mantago.co/yjC7QY',
                        'https://go.mantago.co/fSNKzY', 'https://go.mantago.co/4ATZyb'],
    'tour_pages.py': ['https://go.mantago.co/QnBsyj'],
}


class MantagoLineLinkTests(unittest.TestCase):
    def test_no_plain_line_add_friend_links_left(self):
        for path in list(PAGE_LINKS) + ['qigui/qigui-i18n.js', 'app.py']:
            text = (ROOT / path).read_text(encoding='utf-8')
            self.assertNotIn(OLD, text, path)

    def test_pages_use_expected_mantago_links(self):
        for path, links in PAGE_LINKS.items():
            text = (ROOT / path).read_text(encoding='utf-8')
            for link in links:
                self.assertIn(link, text, f'{path} 缺 {link}')

    def test_static_pages_load_click_tracker(self):
        for path in ('index.html', 'faq.html', 'penghu-autumn-winter.html', 'tides.html',
                     'preorder.html', 'neihai-preorder.html', 'qigui/index.html'):
            text = (ROOT / path).read_text(encoding='utf-8')
            self.assertEqual(text.count('/line-cta.js'), 1, path)
        app = (ROOT / 'app.py').read_text(encoding='utf-8')
        self.assertIn('/line-cta.js', app)  # _render_blog 外框：攻略頁、行程頁、部落格

    def test_tracker_sends_ga4_event_with_link_id(self):
        js = (ROOT / 'line-cta.js').read_text(encoding='utf-8')
        self.assertIn("gtag('event', 'mantago_line_click'", js)
        self.assertIn('link_id', js)
        self.assertIn('data-line-source', js)

    def test_pillar_pages_render_topic_specific_links(self):
        import pillar_pages
        pages = pillar_pages.PILLAR_PAGES
        self.assertIn('go.mantago.co/yjC7QY', pages['penghu-3days-itinerary']['body'])
        self.assertIn('go.mantago.co/fSNKzY', pages['penghu-family-travel']['body'])
        self.assertIn('go.mantago.co/4ATZyb', pages['penghu-itinerary-recommendations']['body'])
        self.assertIn('go.mantago.co/QnBsyj', pages['penghu-food-guide']['body'])
        for slug, page in pages.items():
            hrefs = re.findall(r'href="(https://go\.mantago\.co/[A-Za-z0-9]+)"', page['body'])
            self.assertTrue(hrefs, slug)


if __name__ == '__main__':
    unittest.main()
