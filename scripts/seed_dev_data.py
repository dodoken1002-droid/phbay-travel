# -*- coding: utf-8 -*-
"""在本機 dev 資料庫種一組測試資料，複製正式站的名額情境。

⚠️ 只能對本機 dev cluster 執行。腳本會檢查連線字串必須指向 localhost 的
非標準埠（55432），避免手滑打到正式庫。

種出來的情境（festival 產品，capacity 5）：
  2026-09-12  線上 2 人 ＋ 線下已售 3 人 = 5/5  → 應該額滿
  2026-09-19  線上 2 人 ＋ 線下已售 0 人 = 2/5  → 剩 3

用法：.venv/Scripts/python.exe scripts/seed_dev_data.py
"""
import os
import sys
from pathlib import Path

import psycopg2
import psycopg2.extras
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / 'dev.env', override=True)

URL = os.environ.get('DATABASE_URL', '')
if 'localhost:55432' not in URL and '127.0.0.1:55432' not in URL:
    sys.exit('拒絕執行：DATABASE_URL 不是本機 dev cluster（localhost:55432）。')

conn = psycopg2.connect(URL, cursor_factory=psycopg2.extras.RealDictCursor)
cur = conn.cursor()

cur.execute("SELECT id, slug, capacity, min_people, max_party FROM preorder_products WHERE slug='festival'")
prod = cur.fetchone()
if not prod:
    sys.exit('找不到 festival 產品，請先讓 app 跑一次 init_db。')
pid = prod['id']
print(f"產品 festival：capacity={prod['capacity']} min_people={prod['min_people']} max_party={prod['max_party']}")

# 重跑時先清乾淨，讓腳本（與 test_p0_0_live.py）可以重複執行。
# ⚠️ 必須連 test_p0_0_live.py 自己建立的訂單（公開下單的 FESTIV*、匯入的 IMPOVER*）
# 一起刪掉，否則第二次跑會因為 9/19 已被前一輪塞滿、IMPOVER* 已存在被略過，
# 而出現一堆看起來像 regression 的假失敗。這是 dev 庫，直接清掉該產品全部訂單最乾淨。
cur.execute("DELETE FROM preorder_orders WHERE product_id=%s", (pid,))
cur.execute("DELETE FROM preorder_manual_holds WHERE product_id=%s", (pid,))

for dep_date, pax in (('2026-09-12', 2), ('2026-09-19', 2)):
    cur.execute("""
        INSERT INTO preorder_orders (product_id, departure_date, departure_time,
            contact_name, contact_phone, passenger_count, status, booking_ref)
        VALUES (%s, %s, '', '測試客', '0900000000', %s, 'confirmed_departure', %s)
        RETURNING id
    """, (pid, dep_date, pax, 'TEST' + dep_date.replace('-', '')))
    oid = cur.fetchone()['id']
    for i in range(pax):
        cur.execute("""
            INSERT INTO preorder_passengers (order_id, name, national_id, birth_date, phone)
            VALUES (%s, %s, %s, %s, %s)
        """, (oid, f'旅客{i + 1}', f'A12345678{i}', '1990-01-01', '0900000000'))

cur.execute("""
    INSERT INTO preorder_manual_holds (product_id, hold_date, pax, note)
    VALUES (%s, %s, %s, %s)
    ON CONFLICT (product_id, hold_date) DO UPDATE SET pax = EXCLUDED.pax
""", (pid, '2026-09-12', 3, '電話賣掉的（測試資料）'))

conn.commit()
print('已種：2026-09-12 線上 2 ＋ 線下 3 = 5/5（應額滿）、2026-09-19 線上 2 = 2/5（應剩 3）')
