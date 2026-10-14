"""小城故事・內海巡禮冬季暫停預約（2026/10/14–2027/2/28）的回歸測試。"""
import unittest
from datetime import date
from unittest.mock import patch

import app as app_module
from app import app


class NeihaiClosedPeriodTests(unittest.TestCase):
    def test_closed_reason_covers_both_ends(self):
        for d in (date(2026, 10, 14), date(2026, 12, 25), date(2027, 2, 28)):
            self.assertIsNotNone(app_module._neihai_closed_reason(d), d)
        for d in (date(2026, 10, 13), date(2027, 3, 1)):
            self.assertIsNone(app_module._neihai_closed_reason(d), d)

    def test_public_order_in_closed_period_is_rejected_before_db(self):
        client = app.test_client()
        with patch.object(app_module, 'get_db', side_effect=AssertionError('不應連資料庫')), \
             patch.object(app_module, '_sailing_departed', return_value=False):
            resp = client.post('/api/neihai/preorders', json={
                'sailing_date': '2026-12-01', 'sailing_time': '09:00', 'passengers': []})
        self.assertEqual(resp.status_code, 400)
        self.assertIn('暫停預約', resp.get_json()['error'])

    def test_availability_marks_closed_dates(self):
        class Cur:
            def execute(self, *a): pass
            def fetchall(self): return []
            def close(self): pass

        class Conn:
            def cursor(self): return Cur()
            def close(self): pass

        with patch.object(app_module, 'get_db', return_value=Conn()), \
             patch.object(app_module, '_sailing_departed', return_value=False):
            items = app_module._neihai_month_availability(date(2027, 2, 27), date(2027, 3, 2))
        by_date = {}
        for it in items:
            by_date.setdefault(it['date'], set()).add(it['status'])
        self.assertEqual(by_date['2027-02-27'], {'closed'})
        self.assertEqual(by_date['2027-02-28'], {'closed'})
        self.assertNotIn('closed', by_date['2027-03-01'])


if __name__ == '__main__':
    unittest.main()
