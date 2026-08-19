# -*- coding: utf-8 -*-
"""替 2026 主題遊程徵選獲選行程補上「完整行程海報」與「業者聯絡方式」。

寫入 tours.modal_data 的兩個欄位：
  posters : 圖片路徑陣列（含各語言版本的 DM，前端渲染成可點擊放大的縮圖）
  contact : {agency, partner, phone, line, email, website, license}

聯絡資訊一律取自業者 DM 上自行公布的內容；DM 未公布電話者只列單位名稱，
由前端統一附上「也可直接洽潮旅國際旅行社協助報名」。

執行：python update_themed_tour_posters.py <DATABASE_PUBLIC_URL>
可重複執行（每次覆寫這兩個欄位，其餘 modal_data 內容保留）。
"""
import sys, json, psycopg2

V = "?v=20260819"
P = "/images/tours/posters/"

DATA = {
 501: dict(posters=["p501.jpg"],
           contact=dict(agency="浩運動旅行社有限公司（Hao Sports Travel Co., Ltd.）",
                        partner="浩育樂開發有限公司、愛玩水民宿")),
 502: dict(posters=["p502.jpg"],
           contact=dict(agency="浩運動旅行社有限公司（Hao Sports Travel Co., Ltd.）",
                        partner="浩育樂開發有限公司、愛玩水民宿")),
 503: dict(posters=["p503.jpg"],
           contact=dict(agency="佳期旅行社")),
 504: dict(posters=["p504.jpg", "p504b.jpg", "p504c.jpg"],
           contact=dict(agency="星晴旅行社 Starsunny",
                        phone="06-9269015", line="@441zmcdz",
                        license="註冊編號 855200／旅行社執照 (甲)06857／品保 澎147")),
 505: dict(posters=["p505.jpg", "p505b.jpg"],
           contact=dict(agency="漁翁島旅行社")),
 506: dict(posters=["p506.jpg"],
           contact=dict(agency="珊瑚礁旅遊 Travel in PESCADORES")),
 507: dict(posters=["p507.jpg", "p507b.jpg"],
           contact=dict(agency="行路旅行社",
                        phone="0918-255-108（專案洽詢：李慕昀）",
                        line="@ph614", license="交觀甲 05121")),
 508: dict(posters=["p508.jpg"],
           contact=dict(agency="長立旅行社 Ever Lead Travel Service Co.",
                        partner="長春大飯店 Hotel Ever Spring（06-927-3336）",
                        phone="06-926-0296（澎湖分公司）／02-2567-2001（總公司）",
                        line="0910687820", email="everlead99@gmail.com",
                        website="www.el-travel.com.tw")),
 509: dict(posters=["p509a.jpg", "p509b.jpg", "p509c.jpg", "p509d.jpg"],
           contact=dict(agency="程逸商旅 Orange Leisure Sdn Bhd（馬來西亞）",
                        phone="+603-8734 2168", email="info@orangeleisure.com",
                        website="www.orangeleisure.com")),
}


def main():
    conn = psycopg2.connect(sys.argv[1])
    cur = conn.cursor()
    n = 0
    for sort, d in DATA.items():
        cur.execute("SELECT modal_data FROM tours "
                    "WHERE sort_order=%s AND badge_text='主題遊程徵選獲選行程'", (sort,))
        row = cur.fetchone()
        if not row:
            print(f"  跳過 {sort}：找不到行程")
            continue
        md = row[0] or {}
        if isinstance(md, str):
            md = json.loads(md)
        md["posters"] = [P + f + V for f in d["posters"]]
        md["contact"] = d["contact"]
        cur.execute("UPDATE tours SET modal_data=%s, updated_at=NOW() "
                    "WHERE sort_order=%s AND badge_text='主題遊程徵選獲選行程'",
                    (json.dumps(md, ensure_ascii=False), sort))
        n += cur.rowcount
    conn.commit()
    cur.close()
    conn.close()
    print(f"已更新 {n} 筆行程的海報與聯絡資訊")


if __name__ == "__main__":
    main()
