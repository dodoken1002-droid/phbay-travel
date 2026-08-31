"""後台預購訂單「看起來消失了」的回歸測試，以及父表刪除連鎖的防護。

背景：2026-08-31 站方回報內海預購紀錄全部消失。實際上 11 筆訂單都在，
但出航日都在 2026-07，而後台月份預設當月（2026-08），列表因此一片空白。
"""
import io
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).parent


def src(name):
    return io.open(ROOT / name, encoding='utf-8').read()


def endpoint(app_src, fn):
    return app_src.split('def ' + fn + '(')[1].split('@app.route')[0]


class MonthDefaultTests(unittest.TestCase):
    """月份沒有訂單時不該只是空白——要嘛自動開在有資料的月份，要嘛講清楚資料在哪。"""

    def setUp(self):
        self.app_src = src('app.py')

    def test_both_listings_report_orders_per_month(self):
        for fn in ('admin_neihai_preorders', 'admin_preorder_orders'):
            body = endpoint(self.app_src, fn)
            self.assertIn("to_char", body, fn + ' 未統計各月訂單數')
            self.assertIn('months=months', body, fn + ' 未把各月統計回傳給前端')

    def test_first_load_opens_the_latest_month_that_has_orders(self):
        """不帶 month 參數時，後端要挑最近有訂單的月份，而不是死板的當月。"""
        for fn in ('admin_neihai_preorders', 'admin_preorder_orders'):
            body = endpoint(self.app_src, fn)
            self.assertIn("with_orders[-1] if with_orders else None", body,
                          fn + ' 首次載入仍固定為當月')

    def test_all_months_mode_drops_the_date_filter(self):
        neihai = endpoint(self.app_src, 'admin_neihai_preorders')
        self.assertIn('show_all = requested == "all"', neihai)
        self.assertIn('base_sql.format(where="")', neihai)

        preorder = endpoint(self.app_src, 'admin_preorder_orders')
        self.assertIn("show_all = requested == 'all'", preorder)
        self.assertIn("where = '1=1' if show_all else", preorder)

    def test_start_is_never_formatted_when_it_is_none(self):
        """全部月份模式下 start 是 None，月份欄位必須改回傳 'all'。"""
        for fn, quote in (('admin_neihai_preorders', '"'), ('admin_preorder_orders', "'")):
            body = endpoint(self.app_src, fn)
            self.assertIn('month=' + quote + 'all' + quote + ' if show_all else', body,
                          fn + ' 在 start 為 None 時仍會呼叫 strftime')

    def test_month_filter_still_uses_the_departure_date(self):
        """篩選依據維持出航日；這裡只是確認沒有在修 UX 時改動語意。"""
        neihai = endpoint(self.app_src, 'admin_neihai_preorders')
        self.assertIn('s.sailing_date >= %s AND s.sailing_date < %s', neihai)


class AdminUiTests(unittest.TestCase):
    def setUp(self):
        self.html = src('admin.html')

    def test_both_tabs_offer_an_all_months_toggle(self):
        for box in ('neihai-all-months', 'preorder-all-months'):
            self.assertIn('id="' + box + '"', self.html)

    def test_empty_month_tells_the_user_where_the_data_is(self):
        self.assertIn('function monthJumpHint', self.html)
        self.assertIn('這個月沒有訂單，但資料都還在。', self.html)
        for jump in ("'jumpNeihaiMonth'", "'jumpPreorderMonth'"):
            self.assertIn('monthJumpHint(d.months, d.month, ' + jump + ')', self.html)

    def test_month_input_is_no_longer_forced_to_the_current_month(self):
        """舊行為是載入前先塞當月，導致後端永遠拿不到「請你決定」的空值。"""
        self.assertNotIn("if (el && !el.value) el.value = neihaiMonthDefault();", self.html)
        self.assertNotIn("if (monthEl && !monthEl.value) monthEl.value = neihaiMonthDefault();",
                         self.html)

    def test_the_backend_choice_is_written_back_into_the_picker(self):
        self.assertEqual(2, self.html.count(
            "if (monthEl && d.month && d.month !== 'all') monthEl.value = d.month;"))

    def test_stat_label_reflects_all_months_mode(self):
        self.assertEqual(2, self.html.count("d.month === 'all' ? '全部訂單' : '本月訂單'"))


class CascadeHazardTests(unittest.TestCase):
    """刪掉一筆航次或一個預購商品，不該把底下的訂單與乘客個資一起帶走。"""

    def setUp(self):
        self.app_src = src('app.py')

    def _table(self, name):
        """取出某張表的 CREATE TABLE 區塊，避免斷言誤傷其他表的同名外鍵。"""
        m = re.search(r'CREATE TABLE IF NOT EXISTS ' + name + r' \((.*?)\n *\)',
                      self.app_src, re.S)
        self.assertIsNotNone(m, name + ' 的建表語句找不到')
        return m.group(1)

    def test_order_parents_restrict_instead_of_cascade(self):
        """訂單所屬的父表被刪除時必須擋下，不能連帶清空訂單。"""
        orders = self._table('neihai_preorders')
        self.assertIn('REFERENCES neihai_sailings(id) ON DELETE RESTRICT', orders)
        self.assertNotIn('ON DELETE CASCADE', orders)

        preorders = self._table('preorder_orders')
        self.assertIn('REFERENCES preorder_products(id) ON DELETE RESTRICT', preorders)
        self.assertNotIn('ON DELETE CASCADE', preorders)

    def test_capacity_holds_may_still_cascade(self):
        """preorder_manual_holds 是人工容量保留，不是客戶資料。

        商品刪除時讓它跟著消失是正確的，不應比照訂單改成 RESTRICT——
        否則刪一個已結束的商品會被一堆無意義的保留紀錄擋住。
        """
        holds = self._table('preorder_manual_holds')
        self.assertIn('REFERENCES preorder_products(id) ON DELETE CASCADE', holds)

    def test_child_rows_still_cascade_with_their_order(self):
        """乘客與異動紀錄跟著訂單走是正確的，不要一併改掉。"""
        for child in ('REFERENCES neihai_preorders(id) ON DELETE CASCADE',
                      'REFERENCES preorder_orders(id) ON DELETE CASCADE'):
            self.assertIn(child, self.app_src)

    def test_existing_databases_get_migrated(self):
        """既有資料庫的表已存在，CREATE TABLE IF NOT EXISTS 不會改到外鍵。"""
        self.assertIn("confdeltype = 'c'", self.app_src)
        self.assertIn('ON DELETE RESTRICT', self.app_src)
        migration = self.app_src.split("既有資料庫的外鍵修正")[1][:1600]
        for table in ('neihai_preorders', 'preorder_orders'):
            self.assertIn(table, migration)
        self.assertIn('DROP CONSTRAINT', migration)

    def test_migration_is_idempotent(self):
        """只挑 confdeltype='c'（CASCADE）的外鍵處理，改過就不再動。"""
        migration = self.app_src.split("既有資料庫的外鍵修正")[1][:1600]
        self.assertIn("confdeltype = 'c'", migration)
        self.assertIn('if row:', migration)

    def test_no_endpoint_deletes_those_parent_tables(self):
        """目前沒有端點會刪航次或商品，RESTRICT 是防手動清理資料庫的防護網。"""
        self.assertIsNone(re.search(r'DELETE FROM (preorder_products|neihai_sailings)',
                                    self.app_src))


if __name__ == '__main__':
    unittest.main()
