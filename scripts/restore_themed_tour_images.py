# -*- coding: utf-8 -*-
"""還原「主題遊程徵選獲選行程」9 筆的封面圖路徑。

背景：2026-08-19 Railway 建置佇列卡住，圖片檔（images/tours/t501–t509.jpg）尚未部署，
線上會 404 變破圖，因此先把 image_url 暫時清空讓卡片顯示預設圖。
待 Railway 部署完成（線上能取得 t501.jpg）後執行本腳本還原。

執行：python restore_themed_tour_images.py <DATABASE_PUBLIC_URL>
腳本會先確認線上圖片可取得，取不到就中止不動資料庫。
"""
import sys, urllib.request, psycopg2

SORTS = [501, 502, 503, 504, 505, 506, 507, 508, 509]
CHECK = "https://www.phbay.info/images/tours/t501.jpg"


def images_live():
    try:
        req = urllib.request.Request(CHECK, method="HEAD")
        with urllib.request.urlopen(req, timeout=20) as r:
            return r.status == 200
    except Exception:
        return False


def main():
    if not images_live():
        print("圖片尚未部署（t501.jpg 取不到），中止還原。請等 Railway 部署完成後再執行。")
        sys.exit(1)
    conn = psycopg2.connect(sys.argv[1])
    cur = conn.cursor()
    n = 0
    for s in SORTS:
        cur.execute(
            "UPDATE tours SET image_url=%s, updated_at=NOW() "
            "WHERE sort_order=%s AND badge_text='主題遊程徵選獲選行程'",
            (f"/images/tours/t{s}.jpg", s),
        )
        n += cur.rowcount
    conn.commit()
    cur.close()
    conn.close()
    print(f"已還原 {n} 筆行程封面圖")


if __name__ == "__main__":
    main()
