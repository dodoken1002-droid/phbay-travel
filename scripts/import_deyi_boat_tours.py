"""批次建立「得意遊艇」EDM 的 9 筆船遊行程到正式站（單一行程）。

依使用者決定：拿掉業者聯絡方式、洽詢一律導向潮旅國際旅行社；全部歸「單一行程」，
南方四島/七美/望安/桶盤 → 南海海域（south-sea），花火船/夜釣小管 → 本島海域（main-island）。

金鑰不寫進檔案——從環境變數 PHBAY_ADMIN_KEY 讀取。只需執行一次（重複執行會重複建立）。

用法（bash）：
    PHBAY_ADMIN_KEY=金鑰 python scripts/import_deyi_boat_tours.py
"""

import json
import os
import sys
import urllib.request

API = "https://www.phbay.info/api/admin/tours"

# 各語言共用的訂票須知（導向潮旅）
COMMON_NOTES = {
    "zh-tw": "訂票須知：船班採事先預約，開船時間於出發前一日通知；價格含當天來回船票與船上保險。"
             "取消請於出發前一日 12:00 前通知，當天未到或臨時取消恕收全額。請於船班出發前 30 分鐘至"
             "南海遊客中心報到，逾時視同取消。遇天候海況不佳或不可抗力，保留調整行程之權利。"
             "客艙備舒適沙發座椅與冷氣空調。報名與洽詢請洽潮旅國際旅行社。",
    "en": "Booking notes: Advance reservation required; departure time is confirmed the day before. "
          "Price includes the same-day round-trip boat ticket and onboard insurance. Cancellations must be "
          "made before 12:00 the day before departure; no-shows or last-minute cancellations are charged in full. "
          "Check in at the Nanhai Visitor Center 30 minutes before departure; late arrivals count as cancellations. "
          "The itinerary may be adjusted due to weather, sea conditions, or force majeure. Cabins have comfortable "
          "sofa seating and air conditioning. For booking and enquiries, please contact Phbay Travel.",
    "ja": "予約のご案内：事前予約制で、出航時間は出発前日にご連絡します。料金は当日往復の乗船券と船上保険を含みます。"
          "キャンセルは出発前日12:00までにご連絡ください。当日不参加・直前キャンセルは全額申し受けます。"
          "出航30分前までに南海ビジターセンターでチェックインしてください。遅刻はキャンセル扱いです。"
          "天候・海況・不可抗力により行程を調整する場合があります。客室には快適なソファ席とエアコンを完備。"
          "ご予約・お問い合わせは潮旅國際旅行社まで。",
    "ko": "예약 안내: 사전 예약제이며 출항 시간은 출발 전날 안내됩니다. 요금은 당일 왕복 승선권과 선상 보험을 포함합니다. "
          "취소는 출발 전날 12:00까지 알려주세요. 당일 불참 또는 임박 취소는 전액 부과됩니다. 출항 30분 전까지 "
          "남해 방문자센터에서 체크인하시고, 지각은 취소로 간주됩니다. 기상·해상 상황 또는 불가항력으로 일정이 "
          "조정될 수 있습니다. 객실에는 편안한 소파 좌석과 에어컨이 완비되어 있습니다. 예약 및 문의는 차오뤼 국제여행사로 연락 주세요.",
    "zh-cn": "订票须知：船班采事先预约，开船时间于出发前一日通知；价格含当天来回船票与船上保险。"
             "取消请于出发前一日 12:00 前通知，当天未到或临时取消恕收全额。请于船班出发前 30 分钟至"
             "南海游客中心报到，逾时视同取消。遇天候海况不佳或不可抗力，保留调整行程之权利。"
             "客舱备舒适沙发座椅与冷气空调。报名与咨询请洽潮旅国际旅行社。",
}

# 價格標籤翻譯（value 金額不變）
PRICE_LABELS = {
    "機車": {"en": "Scooter pickup", "ja": "バイク送迎", "ko": "스쿠터 픽업", "zh-cn": "机车"},
    "遊覽車": {"en": "Bus pickup", "ja": "バス送迎", "ko": "버스 픽업", "zh-cn": "游览车"},
    "未滿3歲": {"en": "Under 3", "ja": "3歳未満", "ko": "36개월 미만", "zh-cn": "未满3岁"},
    "全票": {"en": "Adult", "ja": "大人", "ko": "성인", "zh-cn": "全票"},
}

LANGS = ("en", "ja", "ko", "zh-cn")


def loc_prices(prices, lang):
    return [{"label": PRICE_LABELS.get(p["label"], {}).get(lang, p["label"]), "value": p["value"]} for p in prices]


# 9 筆行程資料。每筆：tab、badge、sort、prices(zh 標籤)、各語言欄位。
# notes 會自動接上 COMMON_NOTES[lang]。
TOURS = [
    {
        "tab": "south-sea", "badge_text": "熱銷 No.1", "badge_class": "popular", "sort": 1,
        "prices": [{"label": "機車", "value": "NT$ 1,500"}, {"label": "遊覽車", "value": "NT$ 1,600"}, {"label": "未滿3歲", "value": "NT$ 100"}],
        "zh-tw": {
            "title": "南方四島（含藍洞）＋七美深度遊・專人全程導覽",
            "description": "一日航向南方四島，巡航龍蝦洞與西吉藍洞，登島東吉與七美深度漫遊，再串聯無人島與賞鳥，澎湖南海精華一次收齊。",
            "suitable_for": "親子 / 深度旅遊 / 攝影愛好者", "duration": "1 日遊", "price_display": "NT$ 1,500 起 / 人",
            "highlights": ["08:00 馬公出發 → 鋤頭嶼（龍蝦洞巡航）", "東吉嶼登島約 1.5 小時", "西吉嶼藍洞巡航",
                           "七美登島約 3 小時", "無人島巡航（東西嶼坪、南鐵砧、頭巾嶼）", "賞鳥（需配合燕鷗季）", "16:30 抵達馬公"],
            "includes": "當天來回船票、船上保險、專人全程導覽、冰水、遮陽傘",
            "notes": "機車人數逢單加收 100 元。可加購七美浮潛 800 元/人（提供毛巾、防寒衣、目鏡最高 800 度、呼吸管）。賞鳥需配合燕鷗季。",
        },
        "en": {"title": "Four Southern Islands (Blue Cave) + Cimei In-depth Tour · Guided",
               "description": "A full-day voyage to the Four Southern Islands: cruise the Lobster Cave and Xiji Blue Cave, land on Dongji and Cimei for in-depth exploration, plus uninhabited-islet cruising and birdwatching — the essence of Penghu's South Sea in one day.",
               "suitable_for": "Families / In-depth travel / Photography lovers", "duration": "Day Tour", "price_display": "From NT$1,500 / person",
               "highlights": ["08:00 depart Magong → Chutou Islet (Lobster Cave cruise)", "Dongji Island landing approx. 1.5 hrs", "Xiji Blue Cave cruise",
                              "Cimei Island landing approx. 3 hrs", "Uninhabited-islet cruise (Dongxiyuping, Nantiezhen, Toujin)", "Birdwatching (in tern season)", "16:30 arrive Magong"],
               "includes": "Same-day round-trip boat ticket, onboard insurance, full guided service, iced water, parasol",
               "notes": "An odd number of scooter-pickup guests adds NT$100. Optional Cimei snorkeling add-on NT$800/person (towel, wetsuit, mask up to 800°, snorkel provided). Birdwatching depends on tern season."},
        "ja": {"title": "南方四島（ブルーケーブ）＋七美ディープツアー・専属ガイド",
               "description": "南方四島へ向かう日帰りクルーズ。ロブスター洞窟と西吉ブルーケーブを巡航し、東吉・七美に上陸してじっくり散策。無人島クルーズや野鳥観察も。澎湖南海のハイライトを一日で。",
               "suitable_for": "ファミリー / ディープ旅行 / 写真好き", "duration": "日帰り", "price_display": "NT$1,500〜 / 人",
               "highlights": ["08:00 馬公出発 → 鋤頭嶼（ロブスター洞窟クルーズ）", "東吉島 上陸 約1.5時間", "西吉ブルーケーブ クルーズ",
                              "七美島 上陸 約3時間", "無人島クルーズ（東西嶼坪・南鉄砧・頭巾嶼）", "野鳥観察（アジサシの季節に応じて）", "16:30 馬公着"],
               "includes": "当日往復乗船券、船上保険、専属ガイド、冷たい水、日傘",
               "notes": "バイク送迎が奇数人数の場合は100元追加。七美シュノーケリングの追加可（800元/人、タオル・ウェットスーツ・度付きゴーグル最大800度・シュノーケル付き）。野鳥観察はアジサシの季節次第。"},
        "ko": {"title": "남방사도(블루케이브)＋치메이 심층투어 · 전담 가이드",
               "description": "남방사도로 향하는 당일 크루즈. 랍스터 동굴과 시지 블루케이브를 순항하고 둥지·치메이에 상륙해 깊이 둘러봅니다. 무인도 크루즈와 탐조까지, 펑후 남해의 하이라이트를 하루에.",
               "suitable_for": "가족 / 심층 여행 / 사진 애호가", "duration": "당일 투어", "price_display": "1인 NT$1,500부터",
               "highlights": ["08:00 마궁 출발 → 추터우섬(랍스터 동굴 순항)", "둥지섬 상륙 약 1.5시간", "시지 블루케이브 순항",
                              "치메이섬 상륙 약 3시간", "무인도 순항(둥시위핑·난톄전·터우진)", "탐조(제비갈매기 시즌에 따라)", "16:30 마궁 도착"],
               "includes": "당일 왕복 승선권, 선상 보험, 전담 가이드, 시원한 물, 양산",
               "notes": "스쿠터 픽업 인원이 홀수면 100元 추가. 치메이 스노클링 추가 가능(800元/인, 수건·잠수복·도수 고글 최대 800도·스노클 제공). 탐조는 제비갈매기 시즌에 따름."},
        "zh-cn": {"title": "南方四岛（含蓝洞）＋七美深度游・专人全程导览",
                  "description": "一日航向南方四岛，巡航龙虾洞与西吉蓝洞，登岛东吉与七美深度漫游，再串联无人岛与赏鸟，澎湖南海精华一次收齐。",
                  "suitable_for": "亲子 / 深度旅游 / 摄影爱好者", "duration": "1 日游", "price_display": "NT$ 1,500 起 / 人",
                  "highlights": ["08:00 马公出发 → 锄头屿（龙虾洞巡航）", "东吉屿登岛约 1.5 小时", "西吉屿蓝洞巡航",
                                 "七美登岛约 3 小时", "无人岛巡航（东西屿坪、南铁砧、头巾屿）", "赏鸟（需配合燕鸥季）", "16:30 抵达马公"],
                  "includes": "当天来回船票、船上保险、专人全程导览、冰水、遮阳伞",
                  "notes": "机车人数逢单加收 100 元。可加购七美浮潜 800 元/人（提供毛巾、防寒衣、目镜最高 800 度、呼吸管）。赏鸟需配合燕鸥季。"},
    },
    {
        "tab": "south-sea", "badge_text": "", "badge_class": "", "sort": 2,
        "prices": [{"label": "機車", "value": "NT$ 1,300"}, {"label": "遊覽車", "value": "NT$ 1,400"}, {"label": "未滿3歲", "value": "NT$ 100"}],
        "zh-tw": {
            "title": "七美深度遊＋藍洞巡航",
            "description": "登島七美深度漫遊雙心石滬與小台灣，再巡航西吉夢幻藍洞，半日飽覽澎湖南海最經典的島景。",
            "suitable_for": "親子 / 深度旅遊", "duration": "1 日遊", "price_display": "NT$ 1,300 起 / 人",
            "highlights": ["08:00 馬公出發 → 七美登島約 3 小時", "西吉嶼藍洞巡航", "賞鳥（需配合燕鷗季）", "14:00 抵達馬公"],
            "includes": "當天來回船票、船上保險、冰水、遮陽傘", "notes": "機車人數逢單加收 100 元。賞鳥需配合燕鷗季。",
        },
        "en": {"title": "Cimei In-depth Tour + Blue Cave Cruise",
               "description": "Land on Cimei to explore the Twin-Heart Stone Weir and Little Taiwan, then cruise the dreamy Xiji Blue Cave — Penghu South Sea's most classic island scenery in half a day.",
               "suitable_for": "Families / In-depth travel", "duration": "Day Tour", "price_display": "From NT$1,300 / person",
               "highlights": ["08:00 depart Magong → Cimei landing approx. 3 hrs", "Xiji Blue Cave cruise", "Birdwatching (in tern season)", "14:00 arrive Magong"],
               "includes": "Same-day round-trip boat ticket, onboard insurance, iced water, parasol", "notes": "An odd number of scooter-pickup guests adds NT$100. Birdwatching depends on tern season."},
        "ja": {"title": "七美ディープツアー＋ブルーケーブクルーズ",
               "description": "七美に上陸してダブルハート石滬やリトル台湾を散策し、西吉の幻想的なブルーケーブを巡航。澎湖南海の最も象徴的な島景色を半日で。",
               "suitable_for": "ファミリー / ディープ旅行", "duration": "日帰り", "price_display": "NT$1,300〜 / 人",
               "highlights": ["08:00 馬公出発 → 七美 上陸 約3時間", "西吉ブルーケーブ クルーズ", "野鳥観察（アジサシの季節に応じて）", "14:00 馬公着"],
               "includes": "当日往復乗船券、船上保険、冷たい水、日傘", "notes": "バイク送迎が奇数人数の場合は100元追加。野鳥観察はアジサシの季節次第。"},
        "ko": {"title": "치메이 심층투어 + 블루케이브 순항",
               "description": "치메이에 상륙해 쌍심석호와 리틀 타이완을 둘러보고 시지의 환상적인 블루케이브를 순항합니다. 펑후 남해의 가장 대표적인 섬 풍경을 반나절에.",
               "suitable_for": "가족 / 심층 여행", "duration": "당일 투어", "price_display": "1인 NT$1,300부터",
               "highlights": ["08:00 마궁 출발 → 치메이 상륙 약 3시간", "시지 블루케이브 순항", "탐조(제비갈매기 시즌에 따라)", "14:00 마궁 도착"],
               "includes": "당일 왕복 승선권, 선상 보험, 시원한 물, 양산", "notes": "스쿠터 픽업 인원이 홀수면 100元 추가. 탐조는 제비갈매기 시즌에 따름."},
        "zh-cn": {"title": "七美深度游＋蓝洞巡航",
                  "description": "登岛七美深度漫游双心石沪与小台湾，再巡航西吉梦幻蓝洞，半日饱览澎湖南海最经典的岛景。",
                  "suitable_for": "亲子 / 深度旅游", "duration": "1 日游", "price_display": "NT$ 1,300 起 / 人",
                  "highlights": ["08:00 马公出发 → 七美登岛约 3 小时", "西吉屿蓝洞巡航", "赏鸟（需配合燕鸥季）", "14:00 抵达马公"],
                  "includes": "当天来回船票、船上保险、冰水、遮阳伞", "notes": "机车人数逢单加收 100 元。赏鸟需配合燕鸥季。"},
    },
    {
        "tab": "south-sea", "badge_text": "", "badge_class": "", "sort": 3,
        "prices": [{"label": "機車", "value": "NT$ 1,200"}, {"label": "遊覽車", "value": "NT$ 1,400"}, {"label": "未滿3歲", "value": "NT$ 100"}],
        "zh-tw": {
            "title": "七美＋望安＋桶盤巡航",
            "description": "一趟串聯南海三島：望安綠蠵龜故鄉、七美雙心石滬，再巡航柱狀玄武岩的桶盤嶼，地質與人文一次飽覽。",
            "suitable_for": "親子 / 三島巡禮", "duration": "1 日遊", "price_display": "NT$ 1,200 起 / 人",
            "highlights": ["08:00 馬公出發 → 望安登島約 1.5～2 小時", "七美登島約 2～2.5 小時", "桶盤嶼巡航", "14:30 抵達馬公"],
            "includes": "當天來回船票、船上保險", "notes": "機車人數逢單加收 190 元。",
        },
        "en": {"title": "Cimei + Wang'an + Tongpan Cruise",
               "description": "Link three South-Sea islands in one trip: Wang'an, home of green sea turtles; Cimei's Twin-Heart Stone Weir; then a cruise around the columnar-basalt Tongpan Islet — geology and culture in one day.",
               "suitable_for": "Families / Three-island tour", "duration": "Day Tour", "price_display": "From NT$1,200 / person",
               "highlights": ["08:00 depart Magong → Wang'an landing approx. 1.5–2 hrs", "Cimei landing approx. 2–2.5 hrs", "Tongpan Islet cruise", "14:30 arrive Magong"],
               "includes": "Same-day round-trip boat ticket, onboard insurance", "notes": "An odd number of scooter-pickup guests adds NT$190."},
        "ja": {"title": "七美＋望安＋桶盤クルーズ",
               "description": "南海の三島を一度に。アオウミガメの故郷・望安、七美のダブルハート石滬、そして柱状玄武岩の桶盤嶼を巡航。地質と人文を一日で満喫。",
               "suitable_for": "ファミリー / 三島巡り", "duration": "日帰り", "price_display": "NT$1,200〜 / 人",
               "highlights": ["08:00 馬公出発 → 望安 上陸 約1.5〜2時間", "七美 上陸 約2〜2.5時間", "桶盤嶼 クルーズ", "14:30 馬公着"],
               "includes": "当日往復乗船券、船上保険", "notes": "バイク送迎が奇数人数の場合は190元追加。"},
        "ko": {"title": "치메이 + 왕안 + 퉁판 순항",
               "description": "남해 세 섬을 한 번에. 푸른바다거북의 고향 왕안, 치메이의 쌍심석호, 그리고 주상절리 현무암의 퉁판섬을 순항합니다. 지질과 인문을 하루에.",
               "suitable_for": "가족 / 세 섬 투어", "duration": "당일 투어", "price_display": "1인 NT$1,200부터",
               "highlights": ["08:00 마궁 출발 → 왕안 상륙 약 1.5~2시간", "치메이 상륙 약 2~2.5시간", "퉁판섬 순항", "14:30 마궁 도착"],
               "includes": "당일 왕복 승선권, 선상 보험", "notes": "스쿠터 픽업 인원이 홀수면 190元 추가."},
        "zh-cn": {"title": "七美＋望安＋桶盘巡航",
                  "description": "一趟串联南海三岛：望安绿蠵龟故乡、七美双心石沪，再巡航柱状玄武岩的桶盘屿，地质与人文一次饱览。",
                  "suitable_for": "亲子 / 三岛巡礼", "duration": "1 日游", "price_display": "NT$ 1,200 起 / 人",
                  "highlights": ["08:00 马公出发 → 望安登岛约 1.5～2 小时", "七美登岛约 2～2.5 小时", "桶盘屿巡航", "14:30 抵达马公"],
                  "includes": "当天来回船票、船上保险", "notes": "机车人数逢单加收 190 元。"},
    },
    {
        "tab": "south-sea", "badge_text": "離島花火", "badge_class": "firework", "sort": 4,
        "prices": [{"label": "全票", "value": "NT$ 1,600"}, {"label": "未滿3歲", "value": "NT$ 100"}],
        "zh-tw": {
            "title": "七美場花火・離島花火之夜",
            "description": "傍晚直航七美登島，在離島的夜空下欣賞專屬花火，施放完畢登船返航，把澎湖花火看得更近更浪漫。",
            "suitable_for": "情侶 / 家庭 / 賞花火", "duration": "半日（傍晚出發）", "price_display": "NT$ 1,600 / 人",
            "highlights": ["17:00 出發直達七美登島", "島上欣賞七美場花火", "花火施放完畢登船返航"],
            "includes": "當天來回船票、船上保險", "notes": "限七美場花火施放日；確切日期依主辦單位公告。",
        },
        "en": {"title": "Cimei Fireworks · Offshore Fireworks Night",
               "description": "Sail directly to Cimei at dusk and enjoy a dedicated fireworks show under the offshore night sky, then board to return — Penghu fireworks, closer and more romantic.",
               "suitable_for": "Couples / Families / Fireworks", "duration": "Half day (evening)", "price_display": "NT$1,600 / person",
               "highlights": ["17:00 depart directly to Cimei", "Watch the Cimei fireworks on the island", "Board to return after the show"],
               "includes": "Same-day round-trip boat ticket, onboard insurance", "notes": "Only on Cimei fireworks dates; exact dates per the organizer's announcement."},
        "ja": {"title": "七美会場花火・離島花火の夜",
               "description": "夕方に七美へ直航上陸し、離島の夜空の下で専用の花火を鑑賞。打ち上げ終了後に乗船して帰航。澎湖の花火をより近くロマンチックに。",
               "suitable_for": "カップル / ファミリー / 花火", "duration": "半日（夕方出発）", "price_display": "NT$1,600 / 人",
               "highlights": ["17:00 七美へ直航上陸", "島で七美会場の花火を鑑賞", "打ち上げ終了後に乗船・帰航"],
               "includes": "当日往復乗船券、船上保険", "notes": "七美会場の花火開催日限定。正確な日程は主催者の発表に準じます。"},
        "ko": {"title": "치메이 불꽃놀이 · 낙도 불꽃의 밤",
               "description": "저녁에 치메이로 직항 상륙해 낙도의 밤하늘 아래 전용 불꽃놀이를 감상하고, 종료 후 승선해 귀항합니다. 펑후 불꽃을 더 가깝고 낭만적으로.",
               "suitable_for": "커플 / 가족 / 불꽃놀이", "duration": "반일(저녁 출발)", "price_display": "1인 NT$1,600",
               "highlights": ["17:00 치메이로 직항 상륙", "섬에서 치메이 불꽃놀이 감상", "행사 종료 후 승선·귀항"],
               "includes": "당일 왕복 승선권, 선상 보험", "notes": "치메이 불꽃놀이 개최일 한정. 정확한 일정은 주최 측 공지에 따름."},
        "zh-cn": {"title": "七美场花火・离岛花火之夜",
                  "description": "傍晚直航七美登岛，在离岛的夜空下欣赏专属花火，施放完毕登船返航，把澎湖花火看得更近更浪漫。",
                  "suitable_for": "情侣 / 家庭 / 赏花火", "duration": "半日（傍晚出发）", "price_display": "NT$ 1,600 / 人",
                  "highlights": ["17:00 出发直达七美登岛", "岛上欣赏七美场花火", "花火施放完毕登船返航"],
                  "includes": "当天来回船票、船上保险", "notes": "限七美场花火施放日；确切日期依主办单位公告。"},
    },
    {
        "tab": "south-sea", "badge_text": "離島花火", "badge_class": "firework", "sort": 5,
        "prices": [{"label": "全票", "value": "NT$ 1,300"}, {"label": "未滿3歲", "value": "NT$ 100"}],
        "zh-tw": {
            "title": "望安場花火・離島花火之夜",
            "description": "傍晚直航望安登島，在綠蠵龜故鄉的夜空欣賞專屬花火，施放完畢登船返航，享受離島限定的花火浪漫。",
            "suitable_for": "情侶 / 家庭 / 賞花火", "duration": "半日（傍晚出發）", "price_display": "NT$ 1,300 / 人",
            "highlights": ["17:00 出發直達望安登島", "島上欣賞望安場花火", "花火施放完畢登船返航"],
            "includes": "當天來回船票、船上保險", "notes": "限望安場花火施放日；確切日期依主辦單位公告。",
        },
        "en": {"title": "Wang'an Fireworks · Offshore Fireworks Night",
               "description": "Sail directly to Wang'an at dusk and enjoy a dedicated fireworks show in the home of green sea turtles, then board to return — an offshore-exclusive fireworks romance.",
               "suitable_for": "Couples / Families / Fireworks", "duration": "Half day (evening)", "price_display": "NT$1,300 / person",
               "highlights": ["17:00 depart directly to Wang'an", "Watch the Wang'an fireworks on the island", "Board to return after the show"],
               "includes": "Same-day round-trip boat ticket, onboard insurance", "notes": "Only on Wang'an fireworks dates; exact dates per the organizer's announcement."},
        "ja": {"title": "望安会場花火・離島花火の夜",
               "description": "夕方に望安へ直航上陸し、アオウミガメの故郷の夜空で専用の花火を鑑賞。打ち上げ終了後に乗船して帰航。離島限定の花火ロマンを。",
               "suitable_for": "カップル / ファミリー / 花火", "duration": "半日（夕方出発）", "price_display": "NT$1,300 / 人",
               "highlights": ["17:00 望安へ直航上陸", "島で望安会場の花火を鑑賞", "打ち上げ終了後に乗船・帰航"],
               "includes": "当日往復乗船券、船上保険", "notes": "望安会場の花火開催日限定。正確な日程は主催者の発表に準じます。"},
        "ko": {"title": "왕안 불꽃놀이 · 낙도 불꽃의 밤",
               "description": "저녁에 왕안으로 직항 상륙해 푸른바다거북의 고향 밤하늘에서 전용 불꽃놀이를 감상하고, 종료 후 승선해 귀항합니다. 낙도 한정 불꽃 로맨스.",
               "suitable_for": "커플 / 가족 / 불꽃놀이", "duration": "반일(저녁 출발)", "price_display": "1인 NT$1,300",
               "highlights": ["17:00 왕안으로 직항 상륙", "섬에서 왕안 불꽃놀이 감상", "행사 종료 후 승선·귀항"],
               "includes": "당일 왕복 승선권, 선상 보험", "notes": "왕안 불꽃놀이 개최일 한정. 정확한 일정은 주최 측 공지에 따름."},
        "zh-cn": {"title": "望安场花火・离岛花火之夜",
                  "description": "傍晚直航望安登岛，在绿蠵龟故乡的夜空欣赏专属花火，施放完毕登船返航，享受离岛限定的花火浪漫。",
                  "suitable_for": "情侣 / 家庭 / 赏花火", "duration": "半日（傍晚出发）", "price_display": "NT$ 1,300 / 人",
                  "highlights": ["17:00 出发直达望安登岛", "岛上欣赏望安场花火", "花火施放完毕登船返航"],
                  "includes": "当天来回船票、船上保险", "notes": "限望安场花火施放日；确切日期依主办单位公告。"},
    },
    {
        "tab": "main-island", "badge_text": "", "badge_class": "", "sort": 6,
        "prices": [{"label": "全票", "value": "NT$ 380"}, {"label": "未滿3歲", "value": "NT$ 100"}],
        "zh-tw": {
            "title": "花火船・海上賞澎湖花火",
            "description": "花火施放當晚搭船出海，從最佳視角在海上欣賞澎湖花火與燈光秀，避開岸邊人潮，浪漫滿分。",
            "suitable_for": "親子 / 情侶 / 賞花火", "duration": "約 1 小時（夜間）", "price_display": "NT$ 380 / 人",
            "highlights": ["花火施放日當晚 20:30 出發", "海上欣賞澎湖花火與燈光秀", "21:30 抵達馬公"],
            "includes": "當天來回船票、船上保險", "notes": "限花火施放日；確切日期依主辦單位公告。",
        },
        "en": {"title": "Fireworks Boat · Penghu Fireworks at Sea",
               "description": "On fireworks nights, set sail to watch the Penghu fireworks and light show from the best vantage point at sea — away from the shoreline crowds, pure romance.",
               "suitable_for": "Families / Couples / Fireworks", "duration": "Approx. 1 hr (night)", "price_display": "NT$380 / person",
               "highlights": ["20:30 departure on fireworks nights", "Watch the Penghu fireworks and light show at sea", "21:30 arrive Magong"],
               "includes": "Same-day round-trip boat ticket, onboard insurance", "notes": "Only on fireworks dates; exact dates per the organizer's announcement."},
        "ja": {"title": "花火船・海上で澎湖花火鑑賞",
               "description": "花火開催の夜に出航し、海上のベストポジションから澎湖の花火と光のショーを鑑賞。岸辺の人混みを避けてロマンチックに。",
               "suitable_for": "ファミリー / カップル / 花火", "duration": "約1時間（夜間）", "price_display": "NT$380 / 人",
               "highlights": ["花火開催日の夜 20:30 出発", "海上で澎湖の花火と光のショーを鑑賞", "21:30 馬公着"],
               "includes": "当日往復乗船券、船上保険", "notes": "花火開催日限定。正確な日程は主催者の発表に準じます。"},
        "ko": {"title": "불꽃 보트 · 해상에서 펑후 불꽃놀이 감상",
               "description": "불꽃놀이가 있는 밤에 출항해 해상의 최적 위치에서 펑후 불꽃과 조명 쇼를 감상합니다. 해변 인파를 피해 더욱 낭만적으로.",
               "suitable_for": "가족 / 커플 / 불꽃놀이", "duration": "약 1시간(야간)", "price_display": "1인 NT$380",
               "highlights": ["불꽃놀이 당일 밤 20:30 출발", "해상에서 펑후 불꽃과 조명 쇼 감상", "21:30 마궁 도착"],
               "includes": "당일 왕복 승선권, 선상 보험", "notes": "불꽃놀이 개최일 한정. 정확한 일정은 주최 측 공지에 따름."},
        "zh-cn": {"title": "花火船・海上赏澎湖花火",
                  "description": "花火施放当晚搭船出海，从最佳视角在海上欣赏澎湖花火与灯光秀，避开岸边人潮，浪漫满分。",
                  "suitable_for": "亲子 / 情侣 / 赏花火", "duration": "约 1 小时（夜间）", "price_display": "NT$ 380 / 人",
                  "highlights": ["花火施放日当晚 20:30 出发", "海上欣赏澎湖花火与灯光秀", "21:30 抵达马公"],
                  "includes": "当天来回船票、船上保险", "notes": "限花火施放日；确切日期依主办单位公告。"},
    },
    {
        "tab": "main-island", "badge_text": "", "badge_class": "", "sort": 7,
        "prices": [{"label": "全票", "value": "NT$ 500"}, {"label": "未滿3歲", "value": "NT$ 100"}],
        "zh-tw": {
            "title": "夜釣小管・海上體驗",
            "description": "夜晚出海集魚燈下釣小管，現釣現嚐鮮甜小管麵線，船上備伴唱設備，是澎湖夏夜最有人氣的海上體驗。",
            "suitable_for": "親子 / 揪團 / 夜釣體驗", "duration": "約 2 小時（夜間）", "price_display": "NT$ 500 / 人",
            "highlights": ["19:00 出發出海", "集魚燈下體驗夜釣小管", "享用鮮甜小管麵線", "21:00 抵達"],
            "includes": "當天來回船票、船上保險、釣具組、伴唱設備、小管麵線",
            "notes": "未滿 12 歲孩童須與家長共用釣竿，並由家長協助操作。",
        },
        "en": {"title": "Night Squid Fishing · Sea Experience",
               "description": "Head out at night to fish for squid under fish-luring lamps and taste fresh squid noodles on the spot; karaoke equipment onboard — Penghu's most popular summer-night experience.",
               "suitable_for": "Families / Groups / Night fishing", "duration": "Approx. 2 hrs (night)", "price_display": "NT$500 / person",
               "highlights": ["19:00 departure", "Night squid fishing under fish-luring lamps", "Enjoy fresh squid noodles", "21:00 arrive"],
               "includes": "Same-day round-trip boat ticket, onboard insurance, fishing gear set, karaoke equipment, squid noodles",
               "notes": "Children under 12 must share a rod with a parent and be assisted by the parent."},
        "ja": {"title": "夜釣りイカ・海上体験",
               "description": "夜に出航し集魚灯の下でイカ釣り、釣りたての甘いイカそうめんをその場で堪能。船上にはカラオケ設備も。澎湖の夏の夜で一番人気の海上体験。",
               "suitable_for": "ファミリー / グループ / 夜釣り", "duration": "約2時間（夜間）", "price_display": "NT$500 / 人",
               "highlights": ["19:00 出航", "集魚灯の下で夜のイカ釣り体験", "新鮮で甘いイカそうめんを堪能", "21:00 到着"],
               "includes": "当日往復乗船券、船上保険、釣り具セット、カラオケ設備、イカそうめん",
               "notes": "12歳未満のお子様は保護者と竿を共用し、保護者の補助が必要です。"},
        "ko": {"title": "야간 한치 낚시 · 해상 체험",
               "description": "밤에 출항해 집어등 아래에서 한치를 낚고, 갓 잡은 달콤한 한치 국수를 바로 맛봅니다. 선상에 노래방 설비도. 펑후 여름밤 최고 인기 해상 체험.",
               "suitable_for": "가족 / 단체 / 야간 낚시", "duration": "약 2시간(야간)", "price_display": "1인 NT$500",
               "highlights": ["19:00 출항", "집어등 아래 야간 한치 낚시 체험", "신선하고 달콤한 한치 국수 즐기기", "21:00 도착"],
               "includes": "당일 왕복 승선권, 선상 보험, 낚시 도구 세트, 노래방 설비, 한치 국수",
               "notes": "12세 미만 어린이는 보호자와 낚싯대를 함께 쓰고 보호자의 도움을 받아야 합니다."},
        "zh-cn": {"title": "夜钓小管・海上体验",
                  "description": "夜晚出海集鱼灯下钓小管，现钓现尝鲜甜小管面线，船上备伴唱设备，是澎湖夏夜最有人气的海上体验。",
                  "suitable_for": "亲子 / 揪团 / 夜钓体验", "duration": "约 2 小时（夜间）", "price_display": "NT$ 500 / 人",
                  "highlights": ["19:00 出发出海", "集鱼灯下体验夜钓小管", "享用鲜甜小管面线", "21:00 抵达"],
                  "includes": "当天来回船票、船上保险、钓具组、伴唱设备、小管面线",
                  "notes": "未满 12 岁孩童须与家长共用钓竿，并由家长协助操作。"},
    },
    {
        "tab": "main-island", "badge_text": "", "badge_class": "", "sort": 8,
        "prices": [{"label": "全票", "value": "NT$ 700"}, {"label": "未滿3歲", "value": "NT$ 100"}],
        "zh-tw": {
            "title": "夜釣小管＋賞花火",
            "description": "一趟玩兩種澎湖夏夜經典：先在集魚燈下夜釣小管、品嚐小管麵線，再到海上欣賞澎湖花火，玩好玩滿。",
            "suitable_for": "親子 / 揪團 / 賞花火", "duration": "約 2.5 小時（夜間）", "price_display": "NT$ 700 / 人",
            "highlights": ["19:00 出發出海", "夜釣小管＋鮮甜小管麵線", "海上欣賞澎湖花火", "21:30 抵達"],
            "includes": "當天來回船票、船上保險、釣具組、伴唱設備、小管麵線、海上賞花火",
            "notes": "限花火施放日；未滿 12 歲孩童須與家長共用釣竿，並由家長協助操作。",
        },
        "en": {"title": "Night Squid Fishing + Fireworks",
               "description": "Two Penghu summer-night classics in one trip: squid fishing with squid noodles under fish-luring lamps, then the Penghu fireworks at sea.",
               "suitable_for": "Families / Groups / Fireworks", "duration": "Approx. 2.5 hrs (night)", "price_display": "NT$700 / person",
               "highlights": ["19:00 departure", "Night squid fishing + fresh squid noodles", "Watch the Penghu fireworks at sea", "21:30 arrive"],
               "includes": "Same-day round-trip boat ticket, onboard insurance, fishing gear set, karaoke equipment, squid noodles, fireworks viewing at sea",
               "notes": "Only on fireworks dates; children under 12 must share a rod with a parent and be assisted by the parent."},
        "ja": {"title": "夜釣りイカ＋花火鑑賞",
               "description": "澎湖の夏の夜の定番を一度に。集魚灯の下でイカ釣りとイカそうめんを楽しんだ後、海上で澎湖の花火を鑑賞。",
               "suitable_for": "ファミリー / グループ / 花火", "duration": "約2.5時間（夜間）", "price_display": "NT$700 / 人",
               "highlights": ["19:00 出航", "夜のイカ釣り＋甘いイカそうめん", "海上で澎湖の花火を鑑賞", "21:30 到着"],
               "includes": "当日往復乗船券、船上保険、釣り具セット、カラオケ設備、イカそうめん、海上花火鑑賞",
               "notes": "花火開催日限定。12歳未満のお子様は保護者と竿を共用し、保護者の補助が必要です。"},
        "ko": {"title": "야간 한치 낚시 + 불꽃놀이 감상",
               "description": "펑후 여름밤 클래식 두 가지를 한 번에. 집어등 아래에서 한치 낚시와 한치 국수를 즐긴 뒤 해상에서 펑후 불꽃놀이를 감상.",
               "suitable_for": "가족 / 단체 / 불꽃놀이", "duration": "약 2.5시간(야간)", "price_display": "1인 NT$700",
               "highlights": ["19:00 출항", "야간 한치 낚시 + 달콤한 한치 국수", "해상에서 펑후 불꽃놀이 감상", "21:30 도착"],
               "includes": "당일 왕복 승선권, 선상 보험, 낚시 도구 세트, 노래방 설비, 한치 국수, 해상 불꽃놀이 감상",
               "notes": "불꽃놀이 개최일 한정. 12세 미만 어린이는 보호자와 낚싯대를 함께 쓰고 보호자의 도움을 받아야 합니다."},
        "zh-cn": {"title": "夜钓小管＋赏花火",
                  "description": "一趟玩两种澎湖夏夜经典：先在集鱼灯下夜钓小管、品尝小管面线，再到海上欣赏澎湖花火，玩好玩满。",
                  "suitable_for": "亲子 / 揪团 / 赏花火", "duration": "约 2.5 小时（夜间）", "price_display": "NT$ 700 / 人",
                  "highlights": ["19:00 出发出海", "夜钓小管＋鲜甜小管面线", "海上欣赏澎湖花火", "21:30 抵达"],
                  "includes": "当天来回船票、船上保险、钓具组、伴唱设备、小管面线、海上赏花火",
                  "notes": "限花火施放日；未满 12 岁孩童须与家长共用钓竿，并由家长协助操作。"},
    },
    {
        "tab": "main-island", "badge_text": "客製包船", "badge_class": "custom", "sort": 9,
        "prices": [],
        "zh-tw": {
            "title": "客製化包船・專屬航程",
            "description": "依你的需求規劃南海、東海、北海跳島，或夜釣小管、花火船等主題，專屬包船、彈性出發，適合家庭、公司行號與親友團。",
            "suitable_for": "團體 / 公司行號 / 親友包船", "duration": "依需求客製", "price_display": "客製報價・歡迎洽詢",
            "highlights": ["可規劃南海／東海／北海跳島", "可結合夜釣小管、花火船等主題", "專屬包船、出發時間彈性"],
            "includes": "依包船方案規劃（船班、保險等）", "notes": "詳細行程與報價請洽潮旅國際旅行社，由專人為你規劃。",
        },
        "en": {"title": "Custom Charter · Private Voyage",
               "description": "Plan South-, East-, or North-Sea island hopping, or themes like night squid fishing and fireworks boats — a private charter with flexible departure, ideal for families, companies, and groups.",
               "suitable_for": "Groups / Companies / Private charter", "duration": "Customized", "price_display": "Custom quote · enquire",
               "highlights": ["Plan South / East / North Sea island hopping", "Combine themes like night squid fishing and fireworks", "Private charter with flexible departure"],
               "includes": "Arranged per the charter plan (boat, insurance, etc.)", "notes": "For detailed itineraries and quotes, please contact Phbay Travel for tailored planning."},
        "ja": {"title": "貸切チャーター・専用航程",
               "description": "南海・東海・北海のアイランドホッピングや、夜釣りイカ・花火船などのテーマをご要望に合わせて企画。専用チャーターで出発も柔軟、ご家族・企業・グループに最適。",
               "suitable_for": "グループ / 企業 / 貸切", "duration": "ご要望に応じて", "price_display": "個別見積・お問い合わせ歓迎",
               "highlights": ["南海／東海／北海のアイランドホッピングを企画可", "夜釣りイカ・花火船などのテーマと組合せ可", "専用チャーターで出発時間も柔軟"],
               "includes": "チャータープランに応じて手配（乗船・保険など）", "notes": "詳しい行程とお見積りは潮旅國際旅行社へ。専任スタッフが企画いたします。"},
        "ko": {"title": "맞춤 전세선 · 전용 항정",
               "description": "남해·동해·북해 아일랜드 호핑이나 야간 한치 낚시·불꽃 보트 등 테마를 요청에 맞춰 기획합니다. 전용 전세선으로 출발도 유연해 가족·기업·단체에 적합.",
               "suitable_for": "단체 / 기업 / 전세", "duration": "요청에 따라 맞춤", "price_display": "맞춤 견적 · 문의 환영",
               "highlights": ["남해/동해/북해 아일랜드 호핑 기획 가능", "야간 한치 낚시·불꽃 보트 등 테마 결합 가능", "전용 전세선, 출발 시간 유연"],
               "includes": "전세 플랜에 따라 준비(승선·보험 등)", "notes": "자세한 일정과 견적은 차오뤼 국제여행사로 문의해 주세요. 전담 직원이 기획해 드립니다."},
        "zh-cn": {"title": "客制化包船・专属航程",
                  "description": "依你的需求规划南海、东海、北海跳岛，或夜钓小管、花火船等主题，专属包船、弹性出发，适合家庭、公司行号与亲友团。",
                  "suitable_for": "团体 / 公司行号 / 亲友包船", "duration": "依需求客制", "price_display": "客制报价・欢迎咨询",
                  "highlights": ["可规划南海／东海／北海跳岛", "可结合夜钓小管、花火船等主题", "专属包船、出发时间弹性"],
                  "includes": "依包船方案规划（船班、保险等）", "notes": "详细行程与报价请洽潮旅国际旅行社，由专人为你规划。"},
    },
]


def build_payload(t):
    zh = t["zh-tw"]
    i18n = {}
    for lang in LANGS:
        d = t[lang]
        i18n[lang] = {
            "title": d["title"], "description": d["description"], "suitable_for": d["suitable_for"],
            "duration": d["duration"], "price_display": d["price_display"],
            "prices": loc_prices(t["prices"], lang),
            "modal_data": {
                "highlights": d["highlights"], "dates": [], "days": [],
                "includes": d["includes"], "notes": d["notes"] + " " + COMMON_NOTES[lang],
            },
        }
    return {
        "tabs": [t["tab"]],
        "badge_text": t["badge_text"], "badge_class": t["badge_class"],
        "image_url": "",  # 留空 → 前台用預設圖，建議之後在 /admin 上傳封面
        "title": zh["title"], "description": zh["description"], "suitable_for": zh["suitable_for"],
        "duration": zh["duration"], "price_display": zh["price_display"],
        "is_hero": False, "prices": t["prices"],
        "modal_data": {
            "highlights": zh["highlights"], "dates": [], "days": [],
            "includes": zh["includes"], "notes": zh["notes"] + " " + COMMON_NOTES["zh-tw"],
        },
        "i18n": i18n, "sort_order": t["sort"], "is_active": True,
    }


def existing_titles():
    """抓目前線上所有行程標題，用來去重（避免重複建立）。"""
    try:
        with urllib.request.urlopen("https://www.phbay.info/api/tours", timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except Exception:  # noqa: BLE001
        return set()
    titles = set()
    for arr in (data.get("tours") or {}).values():
        for t in arr:
            titles.add(t.get("title", ""))
    return titles


def main() -> int:
    key = os.environ.get("PHBAY_ADMIN_KEY", "").strip()
    if not key:
        print("錯誤：請先設定環境變數 PHBAY_ADMIN_KEY（後台金鑰）。", file=sys.stderr)
        return 1

    have = existing_titles()
    created = []
    skipped = 0
    for t in TOURS:
        if t["zh-tw"]["title"] in have:
            print(f"[跳過] 已存在：{t['zh-tw']['title']}")
            skipped += 1
            continue
        payload = dict(build_payload(t), _key=key)
        req = urllib.request.Request(
            API, data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            method="POST", headers={"Content-Type": "application/json", "X-Admin-Key": key},
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                result = json.loads(resp.read().decode("utf-8"))
        except Exception as exc:  # noqa: BLE001
            print(f"[失敗] {t['zh-tw']['title']}: {exc}", file=sys.stderr)
            continue
        if result.get("ok"):
            created.append((result.get("id"), t["tab"], t["zh-tw"]["title"]))
            print(f"[OK] id={result.get('id')} [{t['tab']}] {t['zh-tw']['title']}")
        else:
            print(f"[失敗] {t['zh-tw']['title']}: {result}", file=sys.stderr)

    print(f"\n本次新建 {len(created)} 筆，跳過 {skipped} 筆（已存在），共 {len(TOURS)} 筆。")
    return 0 if (len(created) + skipped) == len(TOURS) else 1


if __name__ == "__main__":
    raise SystemExit(main())
