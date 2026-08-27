"""會員系統上線前審查修正的回歸測試（XSS 跳脫、旅次認列政策、交易隔離）。"""
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).parent


class AdminEscapingTests(unittest.TestCase):
    """後台諮詢卡片走 innerHTML，任何使用者可控欄位都必須經過 memberEsc()。

    utm_source 由訪客的網址帶入、備註與姓名由訪客自行填寫，未跳脫即為儲存型 XSS；
    而後台頁面 JS 持有 ADMIN_KEY，一旦被觸發等同整個後台被接管。
    """

    UNESCAPED = [
        '${c.name}', '${c.phone}', '${c.notes||', '${c.budget||',
        '${c.people||', '${c.visit_count||', '${c.created_at}',
        "${((c.utm||{}).utm_source)||'(direct)'}",
    ]

    def setUp(self):
        self.html = (ROOT / 'admin.html').read_text(encoding='utf-8')

    def test_no_unescaped_contact_fields(self):
        for pattern in self.UNESCAPED:
            self.assertNotIn(pattern, self.html,
                             f'{pattern} 未經 memberEsc()，後台有儲存型 XSS 風險')

    def test_utm_source_is_escaped(self):
        self.assertIn("memberEsc(((c.utm||{}).utm_source)||'(direct)')", self.html)

    def test_escape_helper_covers_all_html_metacharacters(self):
        helper = re.search(r'function memberEsc\(v\)\{[^\n]*', self.html).group(0)
        for entity in ('&amp;', '&lt;', '&gt;', '&quot;', '&#39;'):
            self.assertIn(entity, helper, f'memberEsc 未輸出 {entity}')


class TripRecognitionPolicyTests(unittest.TestCase):
    """旅次認列必須由商品層級的政策旗標決定，不可一律 TRUE。

    規劃書已載明：代售產品不得認列為潮旅旅次，否則會員等級會灌水。
    """

    def setUp(self):
        self.app_src = (ROOT / 'app.py').read_text(encoding='utf-8')

    def test_preorder_products_have_policy_column(self):
        self.assertIn(
            'ALTER TABLE preorder_products ADD COLUMN IF NOT EXISTS counts_as_trip',
            self.app_src)

    def test_sync_does_not_hardcode_counts_trip(self):
        self.assertNotIn("VALUES (%s,%s,%s,%s,%s,%s,TRUE,'由訂單狀態自動同步')", self.app_src)

    def test_preorder_sync_reads_product_flag(self):
        self.assertIn("counts_trip=bool(synced.get('counts_as_trip', True))", self.app_src)

    def test_manual_override_is_not_overwritten_by_autosync(self):
        """ON CONFLICT 不可覆寫 counts_trip，客服的人工判定優先於自動同步。"""
        conflict = re.search(r'ON CONFLICT \(source_type,source_ref\) DO UPDATE SET(.*?)RETURNING',
                             self.app_src, re.S).group(1)
        self.assertNotIn('counts_trip', conflict)


class TransactionIsolationTests(unittest.TestCase):
    """會員功能是附加價值，任何失敗都不得讓核心訂位／建表作業一起失敗。"""

    def setUp(self):
        self.app_src = (ROOT / 'app.py').read_text(encoding='utf-8')

    def test_trip_sync_is_wrapped_in_savepoint(self):
        self.assertIn('SAVEPOINT member_trip_sync', self.app_src)
        self.assertIn('ROLLBACK TO SAVEPOINT member_trip_sync', self.app_src)

    def test_order_sync_guards_against_missing_join_row(self):
        self.assertEqual(2, self.app_src.count('synced = cur.fetchone()'))
        self.assertEqual(2, len(re.findall(r'synced = cur\.fetchone\(\)\s*\n\s*if synced:',
                                           self.app_src)))

    def test_member_table_creation_is_isolated(self):
        self.assertIn('SAVEPOINT member_tables', self.app_src)
        self.assertIn('ROLLBACK TO SAVEPOINT member_tables', self.app_src)


class SecretKeyGuardTests(unittest.TestCase):
    """會員登入態與 OTP 的 HMAC 都繫於 secret_key，正式環境不得使用預設值。"""

    def test_production_refuses_default_secret(self):
        app_src = (ROOT / 'app.py').read_text(encoding='utf-8')
        self.assertIn('_SECRET_KEY_FALLBACK', app_src)
        self.assertIn("RAILWAY_ENVIRONMENT_NAME", app_src.split('def get_db')[0])
        self.assertIn('raise RuntimeError', app_src.split('def get_db')[0])


class MemberMigrationHookTests(unittest.TestCase):
    """CREATE TABLE IF NOT EXISTS 不會改動既有資料表，新欄位必須有遷移清單。

    2026-07 的 contacts 事故正是漏了這份清單，線上諮詢一個月內每筆都寫入失敗。
    """

    def test_migration_list_exists_and_is_applied(self):
        src = (ROOT / 'member_program.py').read_text(encoding='utf-8')
        self.assertIn('MEMBER_COLUMN_MIGRATIONS', src)
        self.assertIn('_migrate_member_columns(cur)', src)
        self.assertIn('ADD COLUMN IF NOT EXISTS', src)


if __name__ == '__main__':
    unittest.main()
