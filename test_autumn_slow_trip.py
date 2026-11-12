"""秋冬專頁「秋冬慢旅行」詢價區塊與攻略頁入口的回歸測試（PR #42）。"""
import collections
import os
import re
import unittest
from html.parser import HTMLParser

from app import app

ROOT = os.path.dirname(os.path.abspath(__file__))
VOID = {'meta', 'link', 'img', 'br', 'input', 'hr', 'source', 'area', 'base', 'col', 'embed', 'wbr', 'track', 'param'}
MANTAGO_AUTUMN = 'https://go.mantago.co/iCy82S'


class _Structure(HTMLParser):
    def __init__(self):
        super().__init__()
        self.stack, self.errors = [], []
        self.ids = collections.Counter()
        self.hash_links = set()
        self.sections = []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if a.get('id'):
            self.ids[a['id']] += 1
        if tag == 'a' and (a.get('href') or '').startswith('#') and len(a['href']) > 1:
            self.hash_links.add(a['href'][1:])
        if tag == 'section':
            self.sections.append(a)
        if tag not in VOID:
            self.stack.append(tag)

    def handle_endtag(self, tag):
        if tag in VOID:
            return
        if not self.stack or self.stack[-1] != tag:
            self.errors.append((tag, self.getpos()[0]))
        else:
            self.stack.pop()


def _read(name):
    with open(os.path.join(ROOT, name), encoding='utf-8') as f:
        return f.read()


class AutumnPageTests(unittest.TestCase):
    def setUp(self):
        self.html = _read('penghu-autumn-winter.html')
        self.p = _Structure()
        self.p.feed(self.html)

    def test_tags_balanced(self):
        self.assertEqual(self.p.errors, [])
        self.assertEqual(self.p.stack, [])

    def test_ids_unique_and_anchors_resolve(self):
        self.assertEqual([k for k, v in self.p.ids.items() if v > 1], [])
        for anchor in ('service', 'contact', 'autumn-slow-trip'):
            self.assertEqual(self.p.ids[anchor], 1, anchor)
        self.assertEqual(sorted(h for h in self.p.hash_links if h not in self.p.ids), [])

    def test_service_section_restored(self):
        service = [s for s in self.p.sections if s.get('id') == 'service']
        self.assertEqual(len(service), 1)
        self.assertIn('service', service[0].get('class', '').split())

    def test_slow_trip_cta_uses_autumn_mantago_entry(self):
        block = self.html[self.html.index('id="autumn-slow-trip"'):self.html.index('id="service"')]
        self.assertIn(f'href="{MANTAGO_AUTUMN}"', block)
        self.assertIn('data-line-source="autumn_slow_trip_cta"', block)

    def test_no_unconfirmed_commitments(self):
        block = self.html[self.html.index('id="autumn-slow-trip"'):self.html.index('id="service"')]
        self.assertNotRegex(block, r'NT\$|\d[\d,]*\s*元|保證|立即下訂|兩人即可成行')
        self.assertIn('參考行程', block)
        self.assertNotIn('兩人即可成行', self.html)


class GuideEntranceTests(unittest.TestCase):
    def test_guides_link_to_slow_trip_block_once(self):
        client = app.test_client()
        for path in ('/penghu-3days-itinerary', '/penghu-family-travel'):
            body = client.get(path).get_data(as_text=True)
            self.assertEqual(len(re.findall(r'href="/penghu-autumn-winter#autumn-slow-trip"', body)), 1, path)
            self.assertIn('不適用本頁的套裝參考價', body)
            self.assertIn('內海巡禮冬季暫停預約', body)


if __name__ == '__main__':
    unittest.main()
