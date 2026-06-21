"""建立一筆「單一行程 / 北海海域」範本行程到正式站。

用途：示範海域行程的完整欄位格式，建立後可在 /admin 直接複製修改。
金鑰不寫進檔案——從環境變數 PHBAY_ADMIN_KEY 讀取。

用法（PowerShell）：
    $env:PHBAY_ADMIN_KEY="你的後台金鑰"; python scripts/create_sample_sea_tour.py
用法（bash）：
    PHBAY_ADMIN_KEY=你的後台金鑰 python scripts/create_sample_sea_tour.py
"""

import json
import os
import sys
import urllib.request

API = "https://www.phbay.info/api/admin/tours"

PAYLOAD = {
    "tabs": ["north-sea"],                      # 單一行程 → 北海海域
    "badge_text": "熱門",
    "badge_class": "popular",
    "image_url": "https://images.unsplash.com/photo-1505228395891-9a51e7e86bf6?w=600&q=80",
    "title": "北海跳島一日遊・吉貝水上活動",
    "description": "從赤崁碼頭出發航向北海，登上吉貝沙尾踏浪戲水，暢玩多項水上活動，半天就能收藏澎湖最美的海色。",
    "suitable_for": "親子 / 全年齡 / 揪團出遊",
    "duration": "1 日遊",
    "price_display": "NT$ 1,680 起 / 人",
    "is_hero": False,
    "prices": [
        {"label": "成人", "value": "NT$ 1,680"},
        {"label": "兒童（3–12 歲）", "value": "NT$ 1,280"},
    ],
    "modal_data": {
        "highlights": [
            "赤崁碼頭搭船航向北海，飽覽海上風光",
            "登上吉貝沙尾，金色沙灘踏浪戲水",
            "水上活動任選（香蕉船、甜甜圈、水上摩托車擇一）",
            "自由活動時間，享受純淨海島步調",
        ],
        "dates": [],
        "days": [],
        "includes": "來回船票、吉貝水上活動一項、保險、專業領隊",
        "notes": "受天候與海況影響可能調整航班，出發前以最終通知為準；水上活動須聽從教練指示並穿著救生衣。",
    },
    "sort_order": 1,
    "is_active": True,
    "i18n": {
        "en": {
            "title": "North Sea Island Hopping · Qibei Water Activities (Day Tour)",
            "description": "Depart from Chikan Pier for the North Sea, land on Qibei Sand Tail to wade and play, enjoy water activities, and capture Penghu's finest ocean colors in just half a day.",
            "suitable_for": "Families / All ages / Groups",
            "duration": "Day Tour",
            "price_display": "From NT$1,680 / person",
            "modal_data": {
                "highlights": [
                    "Boat from Chikan Pier to the North Sea with great ocean views",
                    "Land on Qibei Sand Tail and wade on the golden beach",
                    "Choice of one water activity (banana boat, donut ride, or jet ski)",
                    "Free time to enjoy the pure island pace",
                ],
                "includes": "Round-trip boat ticket, one Qibei water activity, insurance, professional guide",
                "notes": "Sailings may change with weather and sea conditions; final notice prevails. Follow instructor guidance and wear a life jacket for water activities.",
            },
        },
        "ja": {
            "title": "北海アイランドホッピング・吉貝ウォーターアクティビティ（日帰り）",
            "description": "赤崁埠頭から北海へ出航し、吉貝の砂尾に上陸して波打ち際で遊び、各種ウォーターアクティビティを満喫。半日で澎湖の美しい海を堪能できます。",
            "suitable_for": "ファミリー / 全年齢 / グループ",
            "duration": "日帰り",
            "price_display": "NT$1,680〜 / 人",
            "modal_data": {
                "highlights": [
                    "赤崁埠頭から北海へ、海上の景色を満喫",
                    "吉貝の砂尾に上陸し黄金のビーチで波遊び",
                    "ウォーターアクティビティ1種選択（バナナボート・ドーナツ・ジェットスキーから）",
                    "自由時間で澄んだ島のペースを満喫",
                ],
                "includes": "往復船チケット、吉貝ウォーターアクティビティ1種、保険、専門ガイド",
                "notes": "天候・海況により便が変更となる場合があります。最終案内に従ってください。アクティビティではインストラクターの指示に従い、ライフジャケットを着用してください。",
            },
        },
        "ko": {
            "title": "북해 아일랜드 호핑 · 지베이 수상 액티비티 (당일)",
            "description": "츠칸 부두에서 북해로 출항해 지베이 모래톱에 상륙, 물놀이를 즐기고 다양한 수상 액티비티를 만끽하며 반나절 만에 펑후의 가장 아름다운 바다를 담아보세요.",
            "suitable_for": "가족 / 전 연령 / 단체",
            "duration": "당일 투어",
            "price_display": "1인 NT$1,680부터",
            "modal_data": {
                "highlights": [
                    "츠칸 부두에서 북해로, 해상 풍경 만끽",
                    "지베이 모래톱 상륙, 금빛 해변에서 물놀이",
                    "수상 액티비티 1종 선택 (바나나보트·도넛·제트스키 중)",
                    "자유 시간으로 깨끗한 섬의 여유 즐기기",
                ],
                "includes": "왕복 보트 티켓, 지베이 수상 액티비티 1종, 보험, 전문 가이드",
                "notes": "날씨와 해상 상황에 따라 운항이 변경될 수 있으며 최종 안내가 우선합니다. 액티비티 시 강사 지시에 따르고 구명조끼를 착용하세요.",
            },
        },
        "zh-cn": {
            "title": "北海跳岛一日游・吉贝水上活动",
            "description": "从赤崁码头出发航向北海，登上吉贝沙尾踏浪戏水，畅玩多项水上活动，半天就能收藏澎湖最美的海色。",
            "suitable_for": "亲子 / 全年龄 / 揪团出游",
            "duration": "1 日游",
            "price_display": "NT$ 1,680 起 / 人",
            "modal_data": {
                "highlights": [
                    "赤崁码头搭船航向北海，饱览海上风光",
                    "登上吉贝沙尾，金色沙滩踏浪戏水",
                    "水上活动任选（香蕉船、甜甜圈、水上摩托车择一）",
                    "自由活动时间，享受纯净海岛步调",
                ],
                "includes": "来回船票、吉贝水上活动一项、保险、专业领队",
                "notes": "受天候与海况影响可能调整航班，出发前以最终通知为准；水上活动须听从教练指示并穿着救生衣。",
            },
        },
    },
}


def main() -> int:
    key = os.environ.get("PHBAY_ADMIN_KEY", "").strip()
    if not key:
        print("錯誤：請先設定環境變數 PHBAY_ADMIN_KEY（後台金鑰）。", file=sys.stderr)
        return 1

    body = dict(PAYLOAD, _key=key)
    request = urllib.request.Request(
        API,
        data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
        method="POST",
        headers={"Content-Type": "application/json", "X-Admin-Key": key},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        result = json.loads(response.read().decode("utf-8"))
    if not result.get("ok"):
        print(f"建立失敗：{result}", file=sys.stderr)
        return 1
    print(f"已建立範本行程（北海海域）。回應：{result}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
