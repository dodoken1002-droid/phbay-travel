# -*- coding: utf-8 -*-
"""名額對帳：找出可能超賣的梯次／船班。

背景（2026-08-27 發現）：同一批實際座位目前存在兩套互不相通的名額系統──
  1. tour_slots        ：首頁行程卡的梯次晶片，只被「諮詢表單」扣減（儲存式計數 booked）
  2. preorder_orders   ：預購頁訂單，名額由 capacity - SUM(passenger_count) 動態計算
  3. neihai_preorders  ：內海預購，同樣動態計算；但後台建立訂單不檢查上限
兩套系統互不扣減，任一通路都可能各自賣滿 → 超賣。

本腳本唯讀，不修改任何資料。
執行：python check_capacity_conflicts.py <DATABASE_PUBLIC_URL>
"""
import sys
import psycopg2
import psycopg2.extras


def main():
    conn = psycopg2.connect(sys.argv[1], cursor_factory=psycopg2.extras.RealDictCursor)
    cur = conn.cursor()
    problems = 0

    # ── 1. 內海／通用預購：已超過上限的場次 ──────────────────
    print("【1】預購訂單超過上限的場次")
    cur.execute("""
        SELECT s.sailing_date::text AS d, s.sailing_time AS t, s.capacity,
               SUM(CASE WHEN p.status <> 'cancelled' THEN p.passenger_count ELSE 0 END) AS pax
        FROM neihai_sailings s JOIN neihai_preorders p ON p.sailing_id = s.id
        GROUP BY s.id, s.sailing_date, s.sailing_time, s.capacity
        HAVING SUM(CASE WHEN p.status <> 'cancelled' THEN p.passenger_count ELSE 0 END) > s.capacity
        ORDER BY s.sailing_date
    """)
    for r in cur.fetchall():
        problems += 1
        print(f"  ⚠ 內海 {r['d']} {r['t']}  {r['pax']}/{r['capacity']}  超賣 {r['pax'] - r['capacity']} 人")

    cur.execute("""
        SELECT pr.slug, pr.capacity, o.departure_date::text AS d, o.departure_time AS t,
               SUM(o.passenger_count) AS pax
        FROM preorder_orders o JOIN preorder_products pr ON pr.id = o.product_id
        WHERE o.status <> 'cancelled' AND pr.capacity IS NOT NULL
        GROUP BY pr.slug, pr.capacity, o.departure_date, o.departure_time
        HAVING SUM(o.passenger_count) > pr.capacity
        ORDER BY o.departure_date
    """)
    for r in cur.fetchall():
        problems += 1
        print(f"  ⚠ 預購 {r['slug']} {r['d']} {r['t'] or ''}  {r['pax']}/{r['capacity']}  超賣 {r['pax'] - r['capacity']} 人")
    if problems == 0:
        print("  （無）")

    # ── 2. 兩套系統並存的行程：合計是否已超過單邊上限 ─────────
    print("\n【2】同時有『行程卡梯次』與『預購訂單』的行程（兩套名額互不扣減）")
    cur.execute("""
        SELECT s.id, s.tour_id, t.title, s.date_label, s.capacity, s.booked
        FROM tour_slots s LEFT JOIN tours t ON t.id = s.tour_id
        WHERE s.is_active = TRUE
        ORDER BY s.tour_id, s.id
    """)
    slots = cur.fetchall()
    cur.execute("""
        SELECT pr.slug, pr.capacity, o.departure_date::text AS d,
               SUM(o.passenger_count) AS pax
        FROM preorder_orders o JOIN preorder_products pr ON pr.id = o.product_id
        WHERE o.status <> 'cancelled'
        GROUP BY pr.slug, pr.capacity, o.departure_date
    """)
    pre = cur.fetchall()
    if slots and pre:
        print("  行程卡梯次：")
        for s in slots:
            print(f"    tour{s['tour_id']:>3} {str(s['title'])[:20]:22} {s['date_label'][:18]:20} "
                  f"諮詢已訂 {s['booked']}/{s['capacity']}")
        print("  預購訂單：")
        for p in pre:
            print(f"    {p['slug'][:16]:18} {p['d']}  預購已訂 {p['pax']}/{p['capacity']}")
        print("  ⚠ 以上兩份數字互不扣減；若代表同一批座位，實際已售 = 兩者相加。")
        problems += 1
    else:
        print("  （無並存情形）")

    print(f"\n→ 共 {problems} 項需要注意" if problems else "\n→ 一切正常")
    cur.close()
    conn.close()


if __name__ == "__main__":
    main()
