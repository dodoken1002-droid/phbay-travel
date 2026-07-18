import os
import unittest
from unittest.mock import patch

from app import app


class LotteryMetaAPITests(unittest.TestCase):
    def setUp(self):
        app.config.update(TESTING=True)
        self.client = app.test_client()
        self.headers = {'X-Admin-Key': 'lottery-test-key'}
        self.env = patch.dict(os.environ, {
            'ADMIN_KEY': 'lottery-test-key',
            'META_PAGE_ACCESS_TOKEN': 'server-only-token',
            'META_FB_PAGE_ID': '112233',
            'META_IG_USER_ID': '998877',
            'META_GRAPH_API_VERSION': 'v25.0',
        }, clear=False)
        self.env.start()

    def tearDown(self):
        self.env.stop()

    def test_status_requires_admin_and_never_returns_token(self):
        denied = self.client.get('/api/lottery/meta/status')
        self.assertEqual(denied.status_code, 401)

        response = self.client.get('/api/lottery/meta/status', headers=self.headers)
        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(payload['configured'], {'facebook': True, 'instagram': True})
        self.assertNotIn('server-only-token', response.get_data(as_text=True))

    @patch('app._meta_graph_get')
    def test_facebook_posts_are_normalized(self, graph_get):
        graph_get.return_value = {'data': [{
            'id': '112233_445566',
            'message': '留言「我要參加」抽澎湖好禮',
            'created_time': '2026-07-10T10:00:00+0000',
            'permalink_url': 'https://www.facebook.com/112233/posts/445566',
        }]}
        response = self.client.get(
            '/api/lottery/meta/posts?platform=facebook', headers=self.headers)
        self.assertEqual(response.status_code, 200)
        post = response.get_json()['posts'][0]
        self.assertEqual(post['id'], '112233_445566')
        self.assertIn('我要參加', post['text'])
        graph_get.assert_called_once()

    @patch('app._meta_graph_get')
    def test_instagram_comments_filter_keyword_and_dedupe_accounts(self, graph_get):
        graph_get.return_value = {'data': [
            {'id': 'c1', 'text': '我要參加', 'timestamp': '2026-07-09T10:00:00Z', 'username': 'penghu_fan',
             'from': {'id': 'ig-1', 'username': 'penghu_fan'}},
            {'id': 'c2', 'text': '我要參加，再留言一次', 'timestamp': '2026-07-09T11:00:00Z', 'username': 'penghu_fan',
             'from': {'id': 'ig-1', 'username': 'penghu_fan'}},
            {'id': 'c3', 'text': '純粹路過', 'username': 'traveler',
             'from': {'id': 'ig-2', 'username': 'traveler'}},
            {'id': 'c4', 'text': '我要參加'},
            {'id': 'c5', 'text': '我要參加', 'username': 'island_guest',
             'from': {'id': 'ig-3', 'username': 'island_guest'}},
            {'id': 'c6', 'text': '我要參加', 'timestamp': '2026-07-11T01:00:00Z', 'username': 'late_guest',
             'from': {'id': 'ig-4', 'username': 'late_guest'}},
        ], 'paging': {}}
        response = self.client.post('/api/lottery/meta/comments', headers=self.headers, json={
            'platform': 'instagram', 'post_id': '1790011223344', 'keyword': '我要參加',
            'cutoff': '2026-07-10T23:59:59+08:00'
        })
        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual([row['name'] for row in payload['participants']],
                         ['@penghu_fan', '@island_guest'])
        self.assertEqual(payload['stats']['comments'], 6)
        self.assertEqual(payload['stats']['eligible'], 2)
        self.assertEqual(payload['stats']['duplicates'], 1)
        self.assertEqual(payload['stats']['keyword_excluded'], 1)
        self.assertEqual(payload['stats']['missing_author'], 1)
        self.assertEqual(payload['stats']['after_cutoff'], 1)

    def test_missing_platform_configuration_is_reported(self):
        with patch.dict(os.environ, {'META_IG_USER_ID': ''}, clear=False):
            response = self.client.get(
                '/api/lottery/meta/posts?platform=instagram', headers=self.headers)
        self.assertEqual(response.status_code, 503)
        self.assertIn('META_IG_USER_ID', response.get_json()['error'])


if __name__ == '__main__':
    unittest.main()
