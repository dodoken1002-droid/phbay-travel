# -*- coding: utf-8 -*-
"""把行程梯次接上預購產品，改為單一名額來源（2026-08-27）。

做三件事：
  1. tours.preorder_slug：音樂節兩條行程（花路追風、追風海龜）→ festival 產品（共用同一批座位）
  2. tour_slots.slot_date：由 date_label（如「9/19(微醺節拍夜)」）解析出真正的日期，供比對
  3. preorder_manual_holds：把老闆原本人工維護的已售數，轉成「線下已售人數」

轉換規則（重要）：
  老闆的人工數字代表該日期「總共已售」。共用池的兩條行程會各自被標記，
  故取同日期兩條行程的最大值當作總已售；再扣掉系統已知的預購訂單人數，
  剩下的才是線下（電話／LINE／同業）已售，避免把預購訂單重複計算兩次。
      線下已售 = max(0, 老闆標記的總已售 − 預購訂單人數)
  轉換後前台顯示的「已售／剩餘」會與老闆原本認知一致。

執行：python link_tours_to_preorder.py <DATABASE_PUBLIC_URL> [--apply]
不加 --apply 只試算不寫入。
"""
import re
import sys
import psycopg2
import psycopg2.extras

YEAR = 2026
SLUG = 'festival'
TOUR_TITLE_KEYWORDS = ('花路追風', '追風海龜')


def parse_label_date(label):
    """「9/19(微醺節拍夜)」→ (2026, 9, 19)；解析不出來回 None。"""
    m = re.search(r'(\d{1,2})\s*/\s*(\d{1,2})', label or '')
    if not m:
        return None
    return f"{YEAR}-{int(m.group(1)):02d}-{int(m.group(2)):02d}"


def main():
    url = sys.argv[1]
    apply = '--apply' in sys.argv
    conn = psycopg2.connect(url, cursor_factory=psycopg2.extras.RealDictCursor)
    cur = conn.cursor()

    cur.execute("SELECT id, capacity FROM preorder_products WHERE slug=%s", (SLUG,))
    prod = cur.fetchone()
    if not prod:
        print(f"找不到預購產品 slug={SLUG}")
        sys.exit(1)
    cap = prod['capacity']
    print(f"預購產品 {SLUG}：id={prod['id']} 每日上限={cap}\n")

    # 1) 行程對應
    cur.execute("SELECT id, title FROM tours")
    targets = [r for r in cur.fetchall()
               if any(k in (r['title'] or '') for k in TOUR_TITLE_KEYWORDS)]
    print("【1】行程 → 預購產品對應")
    for t in targets:
        print(f"    tour {t['id']:>3}  {t['title'][:30]}  →  {SLUG}")
        if apply:
            cur.execute("UPDATE tours SET preorder_slug=%s WHERE id=%s", (SLUG, t['id']))
    tour_ids = [t['id'] for t in targets]

    # 2) 梯次日期
    print("\n【2】梯次 date_label → slot_date")
    cur.execute("SELECT id, tour_id, date_label, booked FROM tour_slots "
                "WHERE tour_id = ANY(%s) ORDER BY tour_id, id", (tour_ids,))
    slots = cur.fetchall()
    owner_total = {}   # date -> 老闆標記的總已售（取兩條行程最大值）
    for s in slots:
        d = parse_label_date(s['date_label'])
        print(f"    slot {s['id']:>3} tour {s['tour_id']:>3}  {s['date_label'][:22]:24} → {d or '⚠ 解析失敗'}"
              f"   人工已售={s['booked']}")
        if d:
            owner_total[d] = max(owner_total.get(d, 0), int(s['booked'] or 0))
            if apply:
                cur.execute("UPDATE tour_slots SET slot_date=%s WHERE id=%s", (d, s['id']))

    # 3) 線下已售人數
    cur.execute("""SELECT departure_date::text AS d,
                          COALESCE(SUM(CASE WHEN status<>'cancelled' THEN passenger_count ELSE 0 END),0) AS pax
                   FROM preorder_orders WHERE product_id=%s GROUP BY departure_date""", (prod['id'],))
    online = {r['d']: int(r['pax']) for r in cur.fetchall()}

    print("\n【3】換算線下已售人數（並確認前台顯示與原本一致）")
    print(f"    {'日期':<12} {'老闆標記總已售':>14} {'預購訂單':>8} {'線下已售':>8} {'合計':>6} {'上限':>5} {'剩餘':>5}")
    for d in sorted(set(list(owner_total.keys()) + list(online.keys()))):
        total = owner_total.get(d, 0)
        on = online.get(d, 0)
        manual = max(0, total - on)
        combined = on + manual
        remaining = (cap - combined) if cap is not None else '—'
        flag = '  ⚠ 老闆標記低於預購訂單' if total and on > total else ''
        print(f"    {d:<12} {total:>14} {on:>8} {manual:>8} {combined:>6} {str(cap):>5} {str(remaining):>5}{flag}")
        if apply:
            cur.execute("""
                INSERT INTO preorder_manual_holds (product_id, hold_date, pax, note, updated_at)
                VALUES (%s,%s,%s,%s,NOW())
                ON CONFLICT (product_id, hold_date)
                DO UPDATE SET pax=EXCLUDED.pax, updated_at=NOW()
            """, (prod['id'], d, manual, '由原人工梯次數字轉入（2026-08-27）'))

    if apply:
        conn.commit()
        print("\n✅ 已寫入")
    else:
        conn.rollback()
        print("\n（試算模式，未寫入。確認無誤後加 --apply）")
    cur.close()
    conn.close()


if __name__ == '__main__':
    main()
