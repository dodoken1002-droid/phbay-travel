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

    # ── 2. 共用池：預購訂單＋線下已售是否超過上限 ────────────
    print("\n【2】共用座位池（預購訂單 ＋ 線下已售）")
    cur.execute("""
        SELECT p.id, p.slug, p.name, p.capacity,
               STRING_AGG(DISTINCT t.title, '、') AS tours
        FROM preorder_products p
        LEFT JOIN tours t ON t.preorder_slug = p.slug
        GROUP BY p.id, p.slug, p.name, p.capacity
        HAVING COUNT(t.id) > 0
    """)
    pools = cur.fetchall()
    if not pools:
        print("  （尚無行程對應到預購產品）")
    for pool in pools:
        print(f"  ▸ {pool['name']}（{pool['slug']}，上限 {pool['capacity']}）")
        print(f"    共用行程：{pool['tours']}")
        cur.execute("""
            SELECT d::text AS d,
                   COALESCE(SUM(online), 0) AS online, COALESCE(SUM(manual), 0) AS manual
            FROM (
                SELECT departure_date AS d,
                       SUM(CASE WHEN status <> 'cancelled' THEN passenger_count ELSE 0 END) AS online,
                       0 AS manual
                FROM preorder_orders WHERE product_id = %s GROUP BY departure_date
                UNION ALL
                SELECT hold_date AS d, 0 AS online, pax AS manual
                FROM preorder_manual_holds WHERE product_id = %s
            ) x GROUP BY d ORDER BY d
        """, (pool['id'], pool['id']))
        for r in cur.fetchall():
            sold = int(r['online']) + int(r['manual'])
            cap = pool['capacity']
            over = (sold - cap) if cap is not None and sold > cap else 0
            if over:
                problems += 1
            mark = f"  ⚠ 超賣 {over} 人" if over else ""
            rem = (cap - sold) if cap is not None else '—'
            print(f"      {r['d']}  預購 {r['online']:>2} ＋ 線下 {r['manual']:>2} = {sold:>2}/{cap}"
                  f"  剩 {rem}{mark}")

    # ── 3. 未接上預購產品、仍用人工計數的梯次 ────────────────
    cur.execute("""
        SELECT t.title, COUNT(*) AS n
        FROM tour_slots s JOIN tours t ON t.id = s.tour_id
        WHERE s.is_active = TRUE AND (t.preorder_slug IS NULL OR t.preorder_slug = '')
        GROUP BY t.title ORDER BY t.title
    """)
    legacy = cur.fetchall()
    print("\n【3】仍使用人工計數的梯次（無對應預購產品，名額需人工維護）")
    if legacy:
        for r in legacy:
            print(f"    {str(r['title'])[:34]:36} {r['n']} 個梯次")
    else:
        print("    （無）")

    print(f"\n→ 共 {problems} 項需要注意" if problems else "\n→ 一切正常")
    cur.close()
    conn.close()


if __name__ == "__main__":
    main()
