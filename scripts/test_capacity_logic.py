"""P0-0 驗證：直接從 app.py 抽出改過的函式，用假 cursor 跑，不連任何資料庫。"""
import ast, os, sys, zlib
from datetime import date, datetime, timedelta

SRC = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'app.py'), encoding='utf-8').read()
tree = ast.parse(SRC)
WANT = {'_manual_hold_pax', '_slot_booked_pax', '_slot_lock_key',
        '_preorder_slot_status', '_preorder_availability'}
picked = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in WANT]
assert {n.name for n in picked} == WANT, {n.name for n in picked}

ns = {'zlib': zlib, 'date': date, 'datetime': datetime, 'timedelta': timedelta}

# ── 假資料：產品 9，capacity 5；2026-09-19 有線上訂單 1 人、線下已售 2 人 ──
ORDERS = {('2026-09-19', ''): 1, ('2026-09-20', ''): 0}
MANUAL = {'2026-09-19': 2}

class FakeCur:
    def __init__(self): self.last = None
    def execute(self, sql, params=()):
        self.last = (' '.join(sql.split()), params)
    def fetchone(self):
        sql, p = self.last
        if 'FROM preorder_manual_holds WHERE product_id' in sql:
            d = str(p[1])
            return {'pax': MANUAL[d]} if d in MANUAL else None
        if 'SUM(passenger_count)' in sql and 'preorder_orders' in sql:
            return {'booked': ORDERS.get((str(p[1]), p[2]), 0)}
        raise AssertionError('未預期的 SQL: ' + sql)
    def fetchall(self):
        sql, p = self.last
        if 'GROUP BY departure_date, departure_time' in sql:
            return [{'departure_date': k[0], 'departure_time': k[1], 'booked': v}
                    for k, v in ORDERS.items()]
        if 'hold_date::text' in sql:
            return [{'d': d, 'pax': v} for d, v in MANUAL.items()]
        raise AssertionError('未預期的 SQL: ' + sql)
    def close(self): pass

cur = FakeCur()
ns['get_db'] = lambda: type('C', (), {'cursor': lambda s: cur, 'close': lambda s: None})()
ns['_taiwan_now'] = lambda: datetime(2026, 9, 1, 10, 0)
ns['_sailing_departed'] = lambda d, t, now=None: False

for n in picked:
    exec(compile(ast.Module([n], []), '<app.py>', 'exec'), ns)

fail = []
def check(label, got, want):
    ok = got == want
    print(('  PASS  ' if ok else '  FAIL  ') + f'{label}: got={got!r} want={want!r}')
    if not ok: fail.append(label)

print('1) _slot_lock_key 必須是決定性的（跨行程同值）')
k1 = ns['_slot_lock_key'](9, date(2026, 9, 19), '')
k2 = ns['_slot_lock_key'](9, '2026-09-19', '')
check('同參數同鍵值', k1, k2)
check('鍵值在 int4 範圍內', 0 <= k1 < 2**31, True)
check('不同場次不同鍵值', k1 != ns['_slot_lock_key'](9, date(2026, 9, 20), ''), True)

print('2) _slot_booked_pax ＝ 線上訂單 ＋ 線下已售')
check('9/19：線上1＋線下2', ns['_slot_booked_pax'](cur, 9, date(2026, 9, 19), ''), 3)
check('9/20：線上0＋線下0', ns['_slot_booked_pax'](cur, 9, date(2026, 9, 20), ''), 0)

print('3) _preorder_availability 的剩餘名額要扣掉線下已售')
product = {'id': 9, 'capacity': 5, 'min_people': 2, 'slot_type': 'daily',
           'times': '', 'duration_days': 1,
           'date_start': date(2026, 9, 19), 'date_end': date(2026, 9, 20)}
items = {i['date']: i for i in
         ns['_preorder_availability'](product, date(2026, 9, 19), date(2026, 9, 21))}
check('9/19 booked', items['2026-09-19']['booked'], 3)
check('9/19 remaining（修好前是 4，修好後是 2）', items['2026-09-19']['remaining'], 2)
check('9/19 已達 min_people 應為 guaranteed', items['2026-09-19']['status'], 'guaranteed')
check('9/20 remaining 不受影響', items['2026-09-20']['remaining'], 5)

print('4) 額滿判斷：線下已售把最後的位子吃掉時要擋下')
MANUAL['2026-09-20'] = 5
items = {i['date']: i for i in
         ns['_preorder_availability'](product, date(2026, 9, 19), date(2026, 9, 21))}
check('9/20 線下賣滿 → full', items['2026-09-20']['status'], 'full')
check('9/20 remaining', items['2026-09-20']['remaining'], 0)

print('\n' + ('全部通過' if not fail else f'{len(fail)} 項失敗：{fail}'))
sys.exit(1 if fail else 0)
