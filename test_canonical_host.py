import os
import unittest
from unittest.mock import patch

from app import app

PROD_RAILWAY = 'web-production-83d7b.up.railway.app'


class CanonicalHostRedirectTests(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

    def _get(self, path, host, env='production', method='get'):
        with patch.dict(os.environ, {'RAILWAY_ENVIRONMENT_NAME': env}):
            return getattr(self.client, method)(path, base_url=f'https://{host}')

    def test_prod_railway_domain_redirects_to_www(self):
        resp = self._get('/blog?page=2', PROD_RAILWAY)
        self.assertEqual(resp.status_code, 308)
        self.assertEqual(resp.headers['Location'], 'https://www.phbay.info/blog?page=2')

    def test_prod_railway_sitemap_and_robots_redirect(self):
        for path in ('/sitemap.xml', '/robots.txt'):
            resp = self._get(path, PROD_RAILWAY, method='head')
            self.assertEqual(resp.status_code, 308, path)
            self.assertEqual(resp.headers['Location'], f'https://www.phbay.info{path}')

    def test_bare_domain_still_redirects(self):
        resp = self._get('/faq.html', 'phbay.info', env='')
        self.assertEqual(resp.headers['Location'], 'https://www.phbay.info/faq.html')

    def test_staging_railway_domain_not_redirected(self):
        resp = self._get('/robots.txt', 'phbay-member-v1-staging-staging.up.railway.app', env='staging')
        self.assertNotEqual(resp.status_code, 308)

    def test_post_and_api_on_railway_domain_not_redirected(self):
        # LINE webhook 等呼叫方可能還設著 railway 網域，不能被轉址打斷
        self.assertNotEqual(self._get('/api/line/webhook', PROD_RAILWAY, method='post').status_code, 308)
        self.assertNotEqual(self._get('/api/tours', PROD_RAILWAY).status_code, 308)


if __name__ == '__main__':
    unittest.main()
