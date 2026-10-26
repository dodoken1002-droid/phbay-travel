"""全站船班公告：公開 API 失敗時一律回 normal、過期自動恢復、後台權限與輸入檢查，
以及頂部資訊列（weather-banner.js）的顯示規則。"""
import pathlib
import unittest
from unittest.mock import patch

import app as app_module
from app import app

ROOT = pathlib.Path(__file__).resolve().parent


class FakeCursor:
    def __init__(self, row):
        self.row = row
        self.executed = []

    def execute(self, sql, params=None):
        self.executed.append((sql, params))

    def fetchone(self):
        return self.row

    def close(self):
        pass


class FakeConn:
    def __init__(self, row):
        self.cur = FakeCursor(row)
        self.committed = False

    def cursor(self):
        return self.cur

    def commit(self):
        self.committed = True

    def close(self):
        pass


class PublicSailingNoticeTests(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

    def get(self, row=None, error=None):
        def fake_db():
            if error:
                raise error
            return FakeConn(row)
        with patch.object(app_module, 'get_db', fake_db):
            return self.client.get('/api/sailing-notice').get_json()

    def test_active_suspended_notice_is_returned(self):
        d = self.get({'level': 'suspended', 'message': '七美航線停駛', 'expired': False})
        self.assertEqual((d['level'], d['message']), ('suspended', '七美航線停駛'))

    def test_blank_message_uses_default_text(self):
        d = self.get({'level': 'caution', 'message': '', 'expired': False})
        self.assertEqual(d['message'], app_module.SAILING_DEFAULT_MESSAGES['caution'])

    def test_expired_notice_falls_back_to_normal(self):
        d = self.get({'level': 'suspended', 'message': '停駛', 'expired': True})
        self.assertEqual((d['level'], d['message']), ('normal', ''))

    def test_database_error_never_breaks_the_page(self):
        d = self.get(error=RuntimeError('db down'))
        self.assertEqual((d['ok'], d['level']), (True, 'normal'))

    def test_unknown_level_in_db_is_ignored(self):
        d = self.get({'level': 'panic', 'message': 'x', 'expired': False})
        self.assertEqual(d['level'], 'normal')


class AdminSailingNoticeTests(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

    def patch_notice(self, body, role='orders'):
        admin = {'id': 1, 'username': 'staff', 'name': '小陳', 'role': role} if role else None
        conn = FakeConn({'level': body.get('level'), 'message': body.get('message', ''),
                         'updated_by': '小陳', 'updated_at': '2026-10-27 08:00', 'expired': False})
        with patch.object(app_module, 'current_admin', return_value=admin), \
             patch.object(app_module, 'get_db', return_value=conn):
            r = self.client.patch('/api/admin/sailing-notice', json=body)
        return r, conn

    def test_requires_login(self):
        r, conn = self.patch_notice({'level': 'caution'}, role=None)
        self.assertEqual(r.status_code, 401)
        self.assertFalse(conn.committed)

    def test_editor_role_cannot_change_it(self):
        r, _ = self.patch_notice({'level': 'caution'}, role='editor')
        self.assertEqual(r.status_code, 401)

    def test_orders_role_can_publish(self):
        r, conn = self.patch_notice({'level': 'suspended', 'message': '今日望安航線停駛'})
        self.assertEqual(r.status_code, 200)
        self.assertTrue(conn.committed)
        self.assertEqual(conn.cur.executed[0][1], ('suspended', '今日望安航線停駛', '小陳'))

    def test_rejects_unknown_level_and_long_text(self):
        r, conn = self.patch_notice({'level': 'storm'})
        self.assertEqual(r.status_code, 400)
        r, conn = self.patch_notice({'level': 'caution', 'message': '字' * 41})
        self.assertEqual(r.status_code, 400)
        self.assertFalse(conn.committed)


class BannerScriptTests(unittest.TestCase):
    def setUp(self):
        self.js = (ROOT / 'weather-banner.js').read_text(encoding='utf-8')

    def test_banner_fetches_notice_and_only_shows_warnings(self):
        self.assertIn("fetch('/api/sailing-notice'", self.js)
        self.assertIn("n.level !== 'caution' && n.level !== 'suspended'", self.js)
        self.assertIn("'/faq#autumn-sailing'", self.js)

    def test_mobile_one_line_rule_keeps_the_sailing_pill(self):
        self.assertIn(':not(.banner-weather):not(.banner-sailing){display:none}', self.js)

    def test_faq_anchor_exists(self):
        self.assertIn('id="autumn-sailing"', (ROOT / 'faq.html').read_text(encoding='utf-8'))

    def test_admin_panel_is_on_the_neihai_tab(self):
        html = (ROOT / 'admin.html').read_text(encoding='utf-8')
        self.assertIn('id="sailing-level"', html)
        self.assertIn("loadSailingNotice(); }", html)


if __name__ == '__main__':
    unittest.main()
