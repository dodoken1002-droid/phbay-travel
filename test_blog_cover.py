"""部落格封面：data URI 改由 /blog/cover/<slug>.jpg 對外提供，並進 og:image 與 JSON-LD。"""
import base64
import json
import re
import unittest
from unittest import mock

import app as app_module
from app import app, SITE, _cover_data, _cover_input_error, _post_cover_url
from test_jsonld_hardening import FakeConn, LD_RE, make_post

JPEG = b'\xff\xd8\xff\xe0fake-jpeg-bytes'
JPEG_URI = 'data:image/jpeg;base64,' + base64.b64encode(JPEG).decode()


class CoverHelperTests(unittest.TestCase):
    def test_cover_data_decodes_allowed_raster_types(self):
        self.assertEqual(_cover_data(JPEG_URI), ('image/jpeg', JPEG))
        png = 'data:image/png;base64,' + base64.b64encode(b'png').decode()
        self.assertEqual(_cover_data(png), ('image/png', b'png'))

    def test_cover_data_rejects_svg_html_and_urls(self):
        svg = 'data:image/svg+xml;base64,' + base64.b64encode(b'<svg onload=alert(1)>').decode()
        self.assertIsNone(_cover_data(svg))
        self.assertIsNone(_cover_data('data:text/html;base64,PHNjcmlwdD4='))
        self.assertIsNone(_cover_data('/images/cover.jpg'))
        self.assertIsNone(_cover_data(''))
        self.assertIsNone(_cover_data(None))

    def test_post_cover_url(self):
        url = _post_cover_url({'slug': 'kueibi', 'cover_image': JPEG_URI})
        self.assertRegex(url, r'^/blog/cover/kueibi\.jpg\?v=[0-9a-f]{10}$')
        other_uri = 'data:image/jpeg;base64,' + base64.b64encode(JPEG + b'-v2').decode()
        other = _post_cover_url({'slug': 'kueibi', 'cover_image': other_uri})
        self.assertNotEqual(url, other, '換圖就要換網址，否則長快取會卡舊圖')
        self.assertEqual(_post_cover_url({'slug': 'k', 'cover_image': '/images/a.jpg'}), '/images/a.jpg')
        self.assertEqual(_post_cover_url({'slug': 'k', 'cover_image': ''}), '')
        self.assertEqual(_post_cover_url({'slug': 'k', 'cover_image': 'data:image/svg+xml;base64,PHN2Zz4='}), '')

    def test_cover_input_validation(self):
        for ok in ('', None, JPEG_URI, '/images/a.jpg', 'images/a.jpg', 'https://cdn.example/a.jpg'):
            self.assertIsNone(_cover_input_error(ok), ok)
        self.assertIsNotNone(_cover_input_error('data:image/svg+xml;base64,PHN2Zz4='))
        self.assertIsNotNone(_cover_input_error('javascript:alert(1)'))
        self.assertIsNotNone(_cover_input_error('data:image/jpeg;base64,' + 'A' * app_module.COVER_MAX_CHARS))


class CoverRouteTests(unittest.TestCase):
    def setUp(self):
        app.config.update(TESTING=True)
        self.client = app.test_client()

    def get(self, path, row):
        with mock.patch.object(app_module, 'get_db', return_value=FakeConn(row)), \
             mock.patch.object(app_module, '_countable_pageview', return_value=False):
            return self.client.get(path)

    def test_serves_decoded_image_with_long_cache(self):
        resp = self.get('/blog/cover/kueibi.jpg?v=abc', {'cover_image': JPEG_URI})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data, JPEG)
        self.assertEqual(resp.mimetype, 'image/jpeg')
        self.assertIn('immutable', resp.headers['Cache-Control'])
        self.assertEqual(resp.headers['X-Content-Type-Options'], 'nosniff')

    def test_unversioned_url_gets_short_cache(self):
        # 全域 .jpg 長快取不能蓋掉：沒帶 ?v 的網址換圖後要能更新
        resp = self.get('/blog/cover/kueibi.jpg', {'cover_image': JPEG_URI})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.headers['Cache-Control'], 'public, max-age=3600')

    def test_missing_cover_is_not_cached(self):
        resp = self.get('/blog/cover/none.jpg', None)
        self.assertEqual(resp.headers['Cache-Control'], 'no-store')

    def test_missing_or_unsafe_cover_is_404(self):
        self.assertEqual(self.get('/blog/cover/none.jpg', None).status_code, 404)
        self.assertEqual(self.get('/blog/cover/x.jpg', {'cover_image': '/images/a.jpg'}).status_code, 404)
        svg = 'data:image/svg+xml;base64,' + base64.b64encode(b'<svg/>').decode()
        self.assertEqual(self.get('/blog/cover/x.jpg', {'cover_image': svg}).status_code, 404)

    def test_post_page_uses_cover_url_for_og_image_and_jsonld(self):
        resp = self.get('/blog/kueibi', make_post(cover_image=JPEG_URI))
        html = resp.get_data(as_text=True)
        self.assertNotIn('data:image/jpeg', html, '文章頁不能再內嵌封面 data URI')
        cover = re.search(r'<img class="blog-cover" src="([^"]+)"', html).group(1)
        self.assertTrue(cover.startswith('/blog/cover/kueibi.jpg?v='))
        og = re.search(r'<meta property="og:image" content="([^"]+)"', html).group(1)
        self.assertEqual(og, SITE + cover)
        article = next(b for b in map(json.loads, LD_RE.findall(html)) if b.get('@type') == 'Article')
        self.assertEqual(article['image'][0], SITE + cover)


class AdminCoverSaveTests(unittest.TestCase):
    def setUp(self):
        app.config.update(TESTING=True)
        self.client = app.test_client()

    def test_rejects_svg_cover_before_touching_db(self):
        with mock.patch.object(app_module, 'has_role', return_value=True), \
             mock.patch.object(app_module, 'get_db', side_effect=AssertionError('不應寫入 DB')):
            resp = self.client.put('/api/admin/posts/1', json={
                'title': 't', 'slug': 's', 'cover_image': 'data:image/svg+xml;base64,PHN2Zz4='})
        self.assertEqual(resp.status_code, 400)
        self.assertFalse(resp.get_json()['ok'])


if __name__ == '__main__':
    unittest.main()
