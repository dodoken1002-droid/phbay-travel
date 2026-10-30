"""2026 追風音樂燈光節（9/12–10/11）結束後，音樂節預購對外隱藏的回歸測試。"""
import unittest
from datetime import date
from unittest.mock import patch

import app as app_module
import pillar_pages
import tour_pages
from app import app


class ClosedRuleTests(unittest.TestCase):
    def test_closes_the_day_after_the_festival(self):
        self.assertIsNone(tour_pages.preorder_closed('festival', date(2026, 10, 11)))
        self.assertEqual(tour_pages.preorder_closed('festival', date(2026, 10, 12)),
                         '/penghu-2026-festival-guide')

    def test_other_products_are_untouched(self):
        self.assertIsNone(tour_pages.preorder_closed('neihai', date(2027, 1, 1)))
        self.assertEqual(tour_pages.booking_link({'preorder_slug': 'other'}, today=date(2026, 12, 1)),
                         '/preorder/other')

    def test_tour_card_drops_festival_link_after_close(self):
        self.assertIsNone(tour_pages.booking_link({'preorder_slug': 'festival'}, today=date(2026, 10, 30)))


class ClosedRouteTests(unittest.TestCase):
    def setUp(self):
        p = patch.object(tour_pages, 'today_taipei', return_value=date(2026, 10, 30))
        p.start(); self.addCleanup(p.stop)
        self.client = app.test_client()

    def test_page_redirects_to_guide_without_db(self):
        with patch.object(app_module, 'get_db', side_effect=AssertionError('不應連資料庫')):
            resp = self.client.get('/preorder/festival')
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(resp.headers['Location'].endswith('/penghu-2026-festival-guide'))

    def test_orders_api_rejects(self):
        class Cur:
            def execute(self, *a): raise AssertionError('不應查詢產品')
            def close(self): pass

        class Conn:
            def cursor(self): return Cur()
            def close(self): pass

        with patch.object(app_module, 'get_db', return_value=Conn()):
            resp = self.client.post('/api/preorder/festival/orders', json={'departure_date': '2026-11-01'})
        self.assertEqual(resp.status_code, 404)


class GuidePageTests(unittest.TestCase):
    def test_guide_no_longer_links_to_preorder(self):
        page = pillar_pages.PILLAR_PAGES['penghu-2026-festival-guide']
        self.assertNotIn('/preorder/festival', str(page))


if __name__ == '__main__':
    unittest.main()
