"""建立潮旅自營行程「小城故事・內海巡禮」到正式站（單一行程 → 本島海域）。

金鑰從環境變數 PHBAY_ADMIN_KEY 讀取，不寫進檔案。具去重（同標題已存在則跳過）。

用法（bash）：
    PHBAY_ADMIN_KEY=金鑰 python scripts/create_neihai_cruise_tour.py
"""

import json
import os
import sys
import urllib.request

API = "https://www.phbay.info/api/admin/tours"

PRICES = [
    {"label": "定價", "value": "NT$ 1,400"},
    {"label": "2026 試航價", "value": "NT$ 1,000"},
    {"label": "團購價（8 張起）", "value": "NT$ 800"},
]
PRICE_LABELS = {
    "定價": {"en": "Standard", "ja": "定価", "ko": "정가", "zh-cn": "定价"},
    "2026 試航價": {"en": "2026 launch price", "ja": "2026 就航記念価格", "ko": "2026 취항가", "zh-cn": "2026 试航价"},
    "團購價（8 張起）": {"en": "Group (8+ tickets)", "ja": "団体（8枚〜）", "ko": "단체(8매 이상)", "zh-cn": "团购价（8 张起）"},
}
LANGS = ("en", "ja", "ko", "zh-cn")


def loc_prices(lang):
    return [{"label": PRICE_LABELS[p["label"]][lang], "value": p["value"]} for p in PRICES]


CONTENT = {
    "zh-tw": {
        "title": "小城故事・內海巡禮（本島內海巡航）",
        "description": "從亞果碼頭出發航行馬公內海，一次串聯觀音亭、重光媽祖、跨海大橋、果凍海（浪蕩洲）與大菓葉玄武岩，90 分鐘輕鬆飽覽澎湖本島最經典的海岸風光。",
        "suitable_for": "親子 / 長輩 / 輕鬆巡航", "duration": "約 90 分鐘", "price_display": "2026 試航價 NT$ 1,000 / 人",
        "highlights": ["亞果碼頭出發", "觀音亭", "重光媽祖", "跨海大橋", "果凍海（浪蕩洲）巡航", "大菓葉玄武岩", "返回亞果碼頭"],
        "includes": "船資、船上飲料",
        "notes": "6 人成行，最多搭乘 13 人。每日出航 09:00、11:00 兩班。11 點趟次如需加購午餐，請事先索取午餐菜單並完成點餐。團購價須一次購買 8 張票。實際航程受天候海況影響，出發前以最終通知為準。報名與洽詢請洽潮旅國際旅行社。",
    },
    "en": {
        "title": "Small-Town Stories · Inner-Sea Cruise (Penghu Main Island)",
        "description": "Depart from Argo Marina to cruise Magong's inner sea, linking Guanyinting, Chongguang Mazu, the Penghu Great Bridge, the Jelly Sea (Langdangzhou sandbar), and Daguoye columnar basalt — the main island's most classic coastline in an easy 90 minutes.",
        "suitable_for": "Families / Seniors / Easy cruise", "duration": "About 90 min", "price_display": "2026 launch price NT$1,000 / person",
        "highlights": ["Depart Argo Marina", "Guanyinting", "Chongguang Mazu Temple", "Penghu Great Bridge", "Jelly Sea (Langdangzhou sandbar) cruise", "Daguoye columnar basalt", "Return to Argo Marina"],
        "includes": "Boat fare, onboard drinks",
        "notes": "Minimum 6 guests, up to 13 per boat. Two daily sailings at 09:00 and 11:00. For the 11:00 sailing, optional lunch can be added — please request the menu and order in advance. The group price requires buying 8 tickets at once. Sailings may change with weather and sea conditions; final notice prevails. For booking and enquiries, please contact Phbay Travel.",
    },
    "ja": {
        "title": "小さな町の物語・内海クルーズ（澎湖本島）",
        "description": "亞果マリーナから馬公の内海をクルーズ。観音亭、重光媽祖、澎湖跨海大橋、ゼリー海（浪蕩洲）、大菓葉玄武岩を一度に巡り、約90分で本島の最も象徴的な海岸風景を満喫します。",
        "suitable_for": "ファミリー / シニア / のんびりクルーズ", "duration": "約90分", "price_display": "2026 就航記念価格 NT$1,000 / 人",
        "highlights": ["亞果マリーナ出発", "観音亭", "重光媽祖", "澎湖跨海大橋", "ゼリー海（浪蕩洲）クルーズ", "大菓葉玄武岩", "亞果マリーナへ帰航"],
        "includes": "乗船料、船上ドリンク",
        "notes": "6名から催行、最大13名。毎日09:00・11:00の2便。11:00便は昼食の追加可（事前にメニューを取り寄せご注文ください）。団体価格は8枚一括購入が必要です。天候・海況により変更の場合があります。ご予約・お問い合わせは潮旅國際旅行社まで。",
    },
    "ko": {
        "title": "작은 마을 이야기 · 내해 크루즈 (펑후 본섬)",
        "description": "야궈 마리나에서 출발해 마궁 내해를 크루즈하며 관음정, 충광 마조, 펑후 대교, 젤리 바다(랑당저우 모래톱), 다궈예 주상절리를 한 번에 둘러봅니다. 약 90분에 본섬의 가장 대표적인 해안 풍경을.",
        "suitable_for": "가족 / 어르신 / 편안한 크루즈", "duration": "약 90분", "price_display": "2026 취항가 1인 NT$1,000",
        "highlights": ["야궈 마리나 출발", "관음정", "충광 마조", "펑후 대교", "젤리 바다(랑당저우 모래톱) 순항", "다궈예 주상절리", "야궈 마리나로 귀항"],
        "includes": "승선료, 선상 음료",
        "notes": "6인 이상 출발, 최대 13인. 매일 09:00·11:00 2회 운항. 11:00편은 점심 추가 가능(사전에 메뉴를 요청해 주문). 단체가는 8매 일괄 구매 필요. 날씨·해상 상황에 따라 변경될 수 있습니다. 예약 및 문의는 차오뤼 국제여행사로.",
    },
    "zh-cn": {
        "title": "小城故事・内海巡礼（本岛内海巡航）",
        "description": "从亚果码头出发航行马公内海，一次串联观音亭、重光妈祖、跨海大桥、果冻海（浪荡洲）与大菓叶玄武岩，90 分钟轻松饱览澎湖本岛最经典的海岸风光。",
        "suitable_for": "亲子 / 长辈 / 轻松巡航", "duration": "约 90 分钟", "price_display": "2026 试航价 NT$ 1,000 / 人",
        "highlights": ["亚果码头出发", "观音亭", "重光妈祖", "跨海大桥", "果冻海（浪荡洲）巡航", "大菓叶玄武岩", "返回亚果码头"],
        "includes": "船资、船上饮料",
        "notes": "6 人成行，最多搭乘 13 人。每日出航 09:00、11:00 两班。11 点趟次如需加购午餐，请事先索取午餐菜单并完成点餐。团购价须一次购买 8 张票。实际航程受天候海况影响，出发前以最终通知为准。报名与咨询请洽潮旅国际旅行社。",
    },
}


def build_payload():
    zh = CONTENT["zh-tw"]
    i18n = {}
    for lang in LANGS:
        d = CONTENT[lang]
        i18n[lang] = {
            "title": d["title"], "description": d["description"], "suitable_for": d["suitable_for"],
            "duration": d["duration"], "price_display": d["price_display"], "prices": loc_prices(lang),
            "modal_data": {"highlights": d["highlights"], "dates": [], "days": [], "includes": d["includes"], "notes": d["notes"]},
        }
    return {
        "tabs": ["main-island"],
        "badge_text": "2026 試航價", "badge_class": "popular",
        "image_url": "",
        "title": zh["title"], "description": zh["description"], "suitable_for": zh["suitable_for"],
        "duration": zh["duration"], "price_display": zh["price_display"],
        "is_hero": False, "prices": PRICES,
        "modal_data": {"highlights": zh["highlights"], "dates": [], "days": [], "includes": zh["includes"], "notes": zh["notes"]},
        "i18n": i18n, "sort_order": 5, "is_active": True,
    }


def existing_titles():
    try:
        with urllib.request.urlopen("https://www.phbay.info/api/tours", timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except Exception:  # noqa: BLE001
        return set()
    return {t.get("title", "") for arr in (data.get("tours") or {}).values() for t in arr}


def main() -> int:
    key = os.environ.get("PHBAY_ADMIN_KEY", "").strip()
    if not key:
        print("錯誤：請先設定環境變數 PHBAY_ADMIN_KEY（後台金鑰）。", file=sys.stderr)
        return 1
    if CONTENT["zh-tw"]["title"] in existing_titles():
        print(f"[跳過] 已存在：{CONTENT['zh-tw']['title']}")
        return 0
    payload = dict(build_payload(), _key=key)
    req = urllib.request.Request(
        API, data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        method="POST", headers={"Content-Type": "application/json", "X-Admin-Key": key},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        result = json.loads(resp.read().decode("utf-8"))
    if not result.get("ok"):
        print(f"建立失敗：{result}", file=sys.stderr)
        return 1
    print(f"[OK] id={result.get('id')} [main-island] {CONTENT['zh-tw']['title']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
