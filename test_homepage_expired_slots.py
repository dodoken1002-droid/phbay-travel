"""首頁不再顯示過期場次「剩餘名額」、已結束活動移出精選的回歸測試。"""
import unittest
from datetime import date
from unittest.mock import patch

import app as app_module
import tour_pages
from app import app


class FakeCursor:
    def __init__(self, results):
        self._results = list(results)
        self._last = []

    def execute(self, *a):
        self._last = self._results.pop(0) if self._results else []

    def fetchall(self):
        return self._last

    def close(self):
        pass


class FakeConn:
    def __init__(self, results):
        self._cur = FakeCursor(results)

    def cursor(self):
        return self._cur

    def close(self):
        pass


def _slot(i, d, label):
    return {'id': i, 'tour_id': 99, 'date_label': label, 'slot_date': d, 'capacity': 5,
            'booked': 0, 'waitlist_cap': 0, 'waitlisted': 0, 'is_active': True, 'created_at': None}


class SlotsApiTests(unittest.TestCase):
    def setUp(self):
        p = patch.object(tour_pages, 'today_taipei', return_value=date(2026, 11, 12))
        p.start(); self.addCleanup(p.stop)
        self.client = app.test_client()

    def test_past_slots_are_hidden(self):
        rows = [_slot(1, date(2026, 10, 3), '10/3'), _slot(2, date(2026, 11, 12), '11/12'),
                _slot(3, date(2027, 3, 1), '3/1'), _slot(4, None, '日期洽詢')]
        with patch.object(app_module, 'get_db', return_value=FakeConn([rows, []])):
            data = self.client.get('/api/slots').get_json()
        self.assertTrue(data['ok'])
        self.assertEqual([s['date_label'] for s in data['slots']], ['11/12', '3/1', '日期洽詢'])


class ToursApiTests(unittest.TestCase):
    def setUp(self):
        p = patch.object(tour_pages, 'today_taipei', return_value=date(2026, 11, 12))
        p.start(); self.addCleanup(p.stop)
        self.client = app.test_client()

    def test_ended_festival_tour_leaves_featured(self):
        rows = [
            {'id': 9, 'title': '花路追風之旅', 'tabs': ['featured', '3d2n'], 'preorder_slug': 'festival'},
            {'id': 2, 'title': '澎湖經典三日遊', 'tabs': ['featured', '3d2n'], 'preorder_slug': None},
        ]
        with patch.object(app_module, 'get_db', return_value=FakeConn([rows])):
            tours = self.client.get('/api/tours').get_json()['tours']
        self.assertEqual([t['id'] for t in tours['featured']], [2])
        ended = next(t for t in tours['3d2n'] if t['id'] == 9)
        self.assertEqual(ended['sale_status'], 'ended')
        self.assertIsNone(ended['preorder_slug'])
        self.assertIsNone(next(t for t in tours['3d2n'] if t['id'] == 2)['sale_status'])


class TourPageBadgeTests(unittest.TestCase):
    def test_ended_badge_on_detail_page(self):
        tour = {'id': 9, 'title': '花路追風之旅', 'tabs': ['3d2n'], 'preorder_slug': 'festival',
                'badge_text': '官方合作', 'modal_data': {}}
        body = tour_pages.render_tour_page(tour, today=date(2026, 11, 12))[3]
        self.assertIn('活動已結束', body)
        self.assertNotIn('官方合作', body)

    def test_open_tour_keeps_badge(self):
        tour = {'id': 2, 'title': '經典', 'tabs': ['3d2n'], 'preorder_slug': None,
                'badge_text': '最受歡迎', 'modal_data': {}}
        body = tour_pages.render_tour_page(tour, today=date(2026, 11, 12))[3]
        self.assertIn('最受歡迎', body)


if __name__ == '__main__':
    unittest.main()
