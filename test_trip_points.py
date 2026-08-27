"""旅次點數與認列政策的行為測試。

重點在冪等性：旅次狀態反覆變動時，點數只能補差額，不可重複發放，
也不可竄改歷史紀錄（取消要走負向沖銷）。
"""
import os
import re
import unittest
from pathlib import Path
from unittest.mock import patch

from member_program import points_per_trip, sync_trip_points


ROOT = Path(__file__).parent


class FakeCursor:
    """只認得 sync_trip_points 用到的四種語句的假 cursor。"""

    def __init__(self, trip, awarded):
        self.trip = dict(trip)
        self.awarded = awarded
        self.inserts = []
        self.updates = []
        self._next = None

    def execute(self, sql, params=()):
        text = ' '.join(sql.split())
        if text.startswith('SELECT id,member_id,tour_name,status,counts_trip'):
            self._next = self.trip
        elif 'COALESCE(SUM(delta),0)' in text:
            self._next = {'awarded': self.awarded}
        elif text.startswith('INSERT INTO member_points'):
            self.inserts.append(params)
            self._next = None
        elif text.startswith('UPDATE member_trips SET points_awarded'):
            self.updates.append(params)
            self._next = None
        else:
            raise AssertionError(f'未預期的語句：{text[:60]}')

    def fetchone(self):
        return self._next


TRIP = {'id': 7, 'member_id': 3, 'tour_name': '小城故事・內海巡禮'}


class SyncTripPointsTests(unittest.TestCase):
    def test_completed_countable_trip_awards_points(self):
        cur = FakeCursor({**TRIP, 'status': 'completed', 'counts_trip': True}, awarded=0)
        self.assertEqual(sync_trip_points(cur, 7), points_per_trip())
        self.assertEqual(len(cur.inserts), 1)
        self.assertEqual(cur.inserts[0][2], points_per_trip())
        self.assertEqual(cur.updates[0][0], points_per_trip())

    def test_running_twice_does_not_double_award(self):
        """已經給過同額點數時不得再寫入帳本，否則重跑同步就會灌點。"""
        cur = FakeCursor({**TRIP, 'status': 'completed', 'counts_trip': True},
                         awarded=points_per_trip())
        self.assertEqual(sync_trip_points(cur, 7), points_per_trip())
        self.assertEqual(cur.inserts, [])

    def test_cancelled_trip_reverses_previous_award(self):
        """取消要產生負向沖銷，而不是刪掉或改寫原本的紀錄。"""
        cur = FakeCursor({**TRIP, 'status': 'cancelled', 'counts_trip': True},
                         awarded=points_per_trip())
        self.assertEqual(sync_trip_points(cur, 7), 0)
        self.assertEqual(len(cur.inserts), 1)
        self.assertEqual(cur.inserts[0][2], -points_per_trip())
        self.assertEqual(cur.updates[0][0], 0)

    def test_non_countable_trip_earns_nothing(self):
        """代售行程（counts_trip=False）即使完成也不給點。"""
        cur = FakeCursor({**TRIP, 'status': 'completed', 'counts_trip': False}, awarded=0)
        self.assertEqual(sync_trip_points(cur, 7), 0)
        self.assertEqual(cur.inserts, [])

    def test_planned_trip_earns_nothing(self):
        cur = FakeCursor({**TRIP, 'status': 'planned', 'counts_trip': True}, awarded=0)
        self.assertEqual(sync_trip_points(cur, 7), 0)
        self.assertEqual(cur.inserts, [])

    def test_missing_trip_is_safe(self):
        cur = FakeCursor({'id': None}, awarded=0)
        cur.trip = None
        self.assertEqual(sync_trip_points(cur, 999), 0)

    def test_points_per_trip_is_configurable(self):
        with patch.dict(os.environ, {'MEMBER_POINTS_PER_TRIP': '250'}, clear=False):
            self.assertEqual(points_per_trip(), 250)
        with patch.dict(os.environ, {'MEMBER_POINTS_PER_TRIP': '亂填'}, clear=False):
            self.assertEqual(points_per_trip(), 100)
        with patch.dict(os.environ, {'MEMBER_POINTS_PER_TRIP': '-5'}, clear=False):
            self.assertEqual(points_per_trip(), 0)


class TripPolicyAdminTests(unittest.TestCase):
    """後台認列政策開關的介面與權限契約。"""

    def setUp(self):
        self.app_src = (ROOT / 'app.py').read_text(encoding='utf-8')
        self.admin = (ROOT / 'admin.html').read_text(encoding='utf-8')

    def test_policy_endpoints_exist(self):
        self.assertIn("@app.route('/api/admin/preorder/products', methods=['GET'])", self.app_src)
        self.assertIn("/api/admin/preorder/products/<int:product_id>/counts-as-trip", self.app_src)

    def test_policy_change_is_owner_only(self):
        """認列政策屬商業決策，訂位人員不得變更。"""
        body = self.app_src.split('def admin_preorder_product_trip_policy')[1].split('@app.route')[0]
        self.assertIn('if not is_admin():', body)
        self.assertNotIn("has_role('orders')", body)

    def test_policy_listing_is_readable_by_orders_role(self):
        body = self.app_src.split('def admin_preorder_products')[1].split('@app.route')[0]
        self.assertIn("has_role('orders')", body)

    def test_policy_change_corrects_existing_trips_and_points(self):
        body = self.app_src.split('def admin_preorder_product_trip_policy')[1].split('@app.route')[0]
        self.assertIn('sync_trip_points(cur, row[', body)
        self.assertIn('recalculate_member(cur, member_id)', body)
        self.assertIn('write_audit(', body)

    def test_admin_ui_has_toggle_and_escapes_product_name(self):
        self.assertIn('id="trip-policy-list"', self.admin)
        self.assertIn('function saveTripPolicy(', self.admin)
        self.assertIn('${memberEsc(p.name)}', self.admin)
        self.assertIn('${memberEsc(p.slug)}', self.admin)

    def test_members_tab_loads_policy(self):
        self.assertIn('loadMembers(); loadTripPolicy();', self.admin)


class MemberPassportTests(unittest.TestCase):
    """會員中心旅行護照必須顯示點數，且五國語言齊備。"""

    def setUp(self):
        self.html = (ROOT / 'member.html').read_text(encoding='utf-8')

    def test_passport_shows_points_column(self):
        self.assertIn('<th data-t="points">點數</th>', self.html)
        self.assertIn('points_awarded', self.html)

    def test_points_label_is_translated_into_four_languages(self):
        self.assertEqual(4, len(re.findall(r"points:'", self.html)),
                         '英日韓簡中四語都必須有 points 字串（繁中走 HTML 預設值）')


if __name__ == '__main__':
    unittest.main()
