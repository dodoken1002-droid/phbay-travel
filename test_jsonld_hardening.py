"""JSON-LD 輸出強化：</script> 跳脫、圖片絕對網址、空 dateModified、@id 連結。"""
import json
import re
import unittest
from unittest import mock

import app as app_module
from app import app, _ld_script, _ld_abs_url, SITE


LD_RE = re.compile(r'<script type="application/ld\+json">(.*?)</script>', re.S)


class FakeCursor:
    def __init__(self, row):
        self.row = row

    def execute(self, *a, **k):
        pass

    def fetchone(self):
        return self.row

    def close(self):
        pass


class FakeConn:
    def __init__(self, row):
        self.row = row

    def cursor(self):
        return FakeCursor(self.row)

    def commit(self):
        pass

    def rollback(self):
        pass

    def close(self):
        pass


def make_post(**over):
    post = {
        'id': 1, 'slug': 'kueibi', 'title': '奎壁山摩西分海', 'summary': '退潮時步道才會露出。',
        'content': '<p>內文</p><img src="/images/a.jpg"><img src="data:image/png;base64,xx">',
        'cover_image': '/images/cover.jpg', 'tags': '景點', 'author': '潮旅國際旅行社',
        'published_at': '2026-06-22', 'created_at': '2026-06-22', 'updated_at': None,
        'faq': None, 'info_box': None, 'i18n': None, 'view_count': 0, 'is_published': True,
    }
    post.update(over)
    return post


class LdScriptTests(unittest.TestCase):
    def test_closing_script_tag_is_escaped(self):
        out = _ld_script({'name': '</script><script>alert(1)</script>'})
        inner = LD_RE.search(out).group(1)
        self.assertNotIn('</', inner)
        self.assertEqual(json.loads(inner)['name'], '</script><script>alert(1)</script>')

    def test_abs_url(self):
        self.assertEqual(_ld_abs_url('/images/a.jpg'), f'{SITE}/images/a.jpg')
        self.assertEqual(_ld_abs_url('images/a.jpg'), f'{SITE}/images/a.jpg')
        self.assertEqual(_ld_abs_url('https://cdn.example/a.jpg'), 'https://cdn.example/a.jpg')
        self.assertEqual(_ld_abs_url('//cdn.example/a.jpg'), 'https://cdn.example/a.jpg')
        self.assertIsNone(_ld_abs_url('data:image/png;base64,xx'))
        self.assertIsNone(_ld_abs_url('javascript:alert(1)'))
        self.assertIsNone(_ld_abs_url(''))
        self.assertIsNone(_ld_abs_url(None))

    def test_no_raw_ld_json_dumps_left_in_app(self):
        with open(app_module.__file__, encoding='utf-8') as f:
            src = f.read()
        self.assertEqual(src.count('<script type="application/ld+json">'), 1,
                         'app.py 的 JSON-LD 一律走 _ld_script()')


class BlogPostJsonLdTests(unittest.TestCase):
    def setUp(self):
        app.config.update(TESTING=True)
        self.client = app.test_client()

    def render(self, post):
        with mock.patch.object(app_module, 'get_db', return_value=FakeConn(post)), \
             mock.patch.object(app_module, '_countable_pageview', return_value=False):
            resp = self.client.get(f'/blog/{post["slug"]}')
        self.assertEqual(resp.status_code, 200)
        html = resp.get_data(as_text=True)
        blocks = [json.loads(b) for b in LD_RE.findall(html)]
        return html, {b.get('@type'): b for b in blocks}

    def test_article_images_are_absolute_and_skip_data_uri(self):
        _, ld = self.render(make_post())
        self.assertEqual(ld['Article']['image'],
                         [f'{SITE}/images/cover.jpg', f'{SITE}/images/a.jpg'])
        self.assertEqual(ld['Article']['@id'], f'{SITE}/blog/kueibi#article')

    def test_empty_date_modified_is_omitted(self):
        _, ld = self.render(make_post())
        self.assertNotIn('dateModified', ld['Article'])
        _, ld = self.render(make_post(updated_at='2026-10-01'))
        self.assertEqual(ld['Article']['dateModified'], '2026-10-01')

    def test_faq_with_script_tag_cannot_break_out(self):
        evil = '</script><script>alert(1)</script>'
        html, ld = self.render(make_post(faq=[{'q': '能過去嗎？', 'a': evil}]))
        # 跳脫前 '</script>' 會提早關閉 JSON-LD 標籤，後面的 <script> 就會被執行
        self.assertNotIn('</script><script>alert(1)', html)
        self.assertEqual(ld['FAQPage']['@id'], f'{SITE}/blog/kueibi#faq')
        self.assertEqual(ld['FAQPage']['mainEntity'][0]['acceptedAnswer']['text'], evil)


if __name__ == '__main__':
    unittest.main()
