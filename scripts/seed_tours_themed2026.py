# -*- coding: utf-8 -*-
"""2026 澎湖主題遊程徵選獲選行程 → tours 資料表（套裝行程・四天三夜）
來源：使用者提供的獲選業者 DM（C:\\Users\\USER\\Downloads\\主題遊程）。
badge_text 一律「主題遊程徵選獲選行程」（金色獎項徽章，卡片左上角）。
執行：python seed_tours_themed2026.py <DATABASE_PUBLIC_URL>
同名 title 跳過，可重複執行。"""
import sys, json, psycopg2

NOTE = ("本行程為 2026 澎湖主題遊程徵選獲選行程，由獲選旅行社規劃執行，潮旅國際旅行社協助諮詢與報名；"
        "出發日期、售價與內容以該旅行社最終公告為準。遇天候海象不佳，主辦單位保留調整或取消之權利。")

def T(title, desc, suit, dur, price, prices, hi, inc, notes, i18n, sort, tabs=None):
    return dict(tabs=tabs or ["4d3n"], title=title, description=desc, suitable_for=suit,
                duration=dur, price_display=price, prices=prices,
                modal_data={"dates": [], "days": [], "highlights": hi,
                            "includes": inc, "notes": notes + NOTE},
                i18n=i18n, sort_order=sort)

def L(en, ja, ko, cn):
    return {"en": en, "ja": ja, "ko": ko, "zh-cn": cn}

TOURS = [
T("澎湖追風派對 Wind Chase Party｜風浪板四天三夜",
  "「風不是離開澎湖的理由，而是來的理由。」專為風浪板、風箏板、翼艇玩家設計的四天三夜追風行程：世界級東北季風浪區、青灣暖身、北海駁島平花水域、龍門進階浪區挑戰，搭配在地主廚海鮮饗宴與專業海上攝影。由浩運動旅行社規劃，浩育樂開發與愛玩水民宿協力。",
  "風浪板 / 風箏板 / 翼艇玩家", "四天三夜", "線上詢價",
  [{"label":"四天三夜行程","value":"線上詢價"}],
  ["Day1 青灣暖身＋裝備檢查、迎賓海鮮晚宴",
   "Day2 北海駁島追風・澎澎灘平花水域",
   "Day3 龍門浪區進階挑戰、國際玩家技術交流",
   "Day4 白坑海域收尾＋伴手禮採購",
   "專業海上攝影團隊全程記錄"],
  "住宿、在地主廚海鮮餐、專業教練帶領、海上攝影、接送",
  "適合已有風浪板／風箏板／翼艇基礎的玩家；風況依季節調整。",
  L({"title":"Penghu Wind Chase Party｜4D3N Windsurfing","description":"'Wind is not the reason to leave Penghu. Wind is the reason to come.' A 4-day windsurfing, kitesurfing and wing foil trip: world-class NE monsoon conditions at Qingloo, North Sea flat water, and the Longmen wave challenge, with chef-selected Penghu seafood and pro marine photography.","duration":"4 days 3 nights","suitable_for":"Windsurf / Kitesurf / Wing foil"},
    {"title":"澎湖ウインドチェイスパーティー｜4日間ウインドサーフィン","description":"ウインドサーフィン・カイトサーフィン・ウイングフォイル愛好家のための4日間。世界級の北東季節風、青湾でのウォームアップ、北海のフラットウォーター、龍門の上級波エリアに挑戦。シェフ厳選の海鮮とプロの海上撮影付き。","duration":"3泊4日","suitable_for":"ウインド／カイト／ウイングフォイル"},
    {"title":"펑후 윈드체이스 파티｜3박4일 윈드서핑","description":"윈드서핑·카이트서핑·윙포일 마니아를 위한 4일 일정. 세계급 북동 계절풍, 칭완 워밍업, 북해 플랫워터, 룽먼 상급 웨이브 도전. 셰프 특선 해산물과 프로 해상 촬영 포함.","duration":"3박 4일","suitable_for":"윈드서핑 / 카이트 / 윙포일"},
    {"title":"澎湖追风派对 Wind Chase Party｜风浪板四天三夜","description":"专为风浪板、风筝板、翼艇玩家设计的四天三夜追风行程：世界级东北季风浪区、青湾暖身、北海驳岛平花水域、龙门进阶浪区挑战，搭配在地主厨海鲜飨宴与专业海上摄影。","duration":"四天三夜","suitable_for":"风浪板 / 风筝板 / 翼艇玩家"}), 501),

T("澎湖秋冬主題遊程｜慵藍號遊艇 × 小城故事內海巡禮",
  "115 年度秋冬限定企劃：搭乘專利研發的慵藍號新型遊艇（6 人即成行），享受專屬私密空間深入澎湖內海秘境。四天三夜結合國手級教練指導的風浪板課程、南方四島紫色珊瑚海與藍洞浮潛、SUP 體驗，以及頂級海鮮晚宴與沙洲秘境午餐。由浩運動旅行社規劃。",
  "質感小團 / 海上活動愛好者", "四天三夜", "線上詢價",
  [{"label":"四天三夜行程","value":"線上詢價"}],
  ["慵藍號專屬遊艇，6 人即可成行",
   "國手級教練分級風浪板教學（內海到外海）",
   "南方四島紫色珊瑚海、海底薰衣草森林、藍洞巡航",
   "頂級海鮮晚宴、沙洲秘境午餐",
   "彈性行程：可換浪漫三傻遊艇、虎克船長海釣、夜釣小管等"],
  "住宿、餐食、遊艇、水上活動、教練、300 萬旅平險＋20 萬醫療險",
  "不含台灣本島至澎湖來回機票／船票與個人額外消費；秋冬限定出發、名額有限。",
  L({"title":"Penghu Autumn-Winter Theme Tour｜Yacht & Inner Sea Cruise","description":"Autumn-winter exclusive: board the patented 'Yonglan' yacht (min 6 guests) for a private cruise into Penghu's inner sea. Four days combining national-team-level windsurfing coaching, purple coral and Blue Cave snorkeling in South Penghu, SUP, plus premium seafood dinners and a sandbar lunch.","duration":"4 days 3 nights","suitable_for":"Premium small group"},
    {"title":"澎湖秋冬テーマツアー｜専用ヨット×内海クルーズ","description":"秋冬限定企画。特許新型ヨット「慵藍號」（6名から催行）で澎湖内海の秘境へ。ナショナルコーチによるウインドサーフィン指導、南方四島の紫サンゴとブルーケーブのシュノーケリング、SUP、高級海鮮ディナーと砂洲の秘境ランチ。","duration":"3泊4日","suitable_for":"上質な少人数旅"},
    {"title":"펑후 가을·겨울 테마 투어｜전용 요트 & 내해 크루즈","description":"가을·겨울 한정 기획. 특허 신형 요트 '융란호'(6인 출발)로 펑후 내해 비경으로. 국가대표급 코치의 윈드서핑 강습, 남방사도 보라 산호와 블루케이브 스노클링, SUP, 프리미엄 해산물 만찬까지.","duration":"3박 4일","suitable_for":"프리미엄 소그룹"},
    {"title":"澎湖秋冬主题游程｜慵蓝号游艇 × 小城故事内海巡礼","description":"秋冬限定企划：搭乘专利研发的慵蓝号新型游艇（6 人即成行），深入澎湖内海秘境。四天三夜结合国手级教练风浪板课程、南方四岛紫色珊瑚海与蓝洞浮潜、SUP 体验，以及顶级海鲜晚宴。","duration":"四天三夜","suitable_for":"质感小团 / 海上活动"}), 502),

T("澎湖慢旅 4 日｜多留一天給澎湖",
  "「四天，不只是多一天，而是完整認識一座島。」世界級玄武岩 × 百年聚落 × 海岸秘境，跟著島民過一天。北環、西嶼、東海、馬公一次深度探索，搭配跨島巡航與海牧體驗、漁市場走讀、小管一日乾與花宅 DIY，並搭乘台灣好行支持地方創生。台北、台中、高雄同步出發。",
  "深度慢旅 / 首次深度玩澎湖", "四天三夜", "線上詢價",
  [{"label":"四天三夜（含往返機票）","value":"線上詢價"}],
  ["山海全遊：北環、西嶼、東海、馬公一次玩透",
   "海洋體驗：跨島巡航、海洋牧場",
   "世界地景：玄武岩、燈塔、百年聚落、小希臘漁港",
   "島民生活：漁市場、小管一日乾、花宅 DIY、社區故事",
   "永續旅行：搭乘台灣好行、支持地方創生"],
  "往返機票、飯店 3 晚住宿、員貝東海一日遊、台灣好行港南線、內海風車高牧體食、南寮社區導覽、3 早餐 2 午餐 3 晚餐、專屬車、250 萬旅責險＋20 萬醫療險",
  "2026 出發日期：8/19・20・26・27，9/3・6・9・16・20・23，10/1・4・7・11。",
  L({"title":"Penghu Slow Travel 4 Days｜Stay One More Day","description":"'Four days is not just one more day — it's truly getting to know an island.' World-class basalt, century-old villages and hidden coastlines, living a day like an islander: North Ring, Xiyu, East Sea and Magong in depth, with island cruising, ocean ranch, fish market walks and local DIY.","duration":"4 days 3 nights","suitable_for":"Slow travel / First deep trip"},
    {"title":"澎湖スロートラベル4日間｜もう一日を澎湖に","description":"「4日間は、ただ一日多いのではなく、島を丸ごと知る時間」。世界級の玄武岩×百年集落×海岸の秘境を、島民のように過ごす。北環・西嶼・東海・馬公を深く巡り、島巡りクルーズや海洋牧場、魚市場散策、DIY体験も。","duration":"3泊4日","suitable_for":"スローな深掘り旅"},
    {"title":"펑후 슬로우 트래블 4일｜하루 더 펑후에서","description":"'4일은 하루 더가 아니라, 섬을 온전히 아는 시간'. 세계급 현무암, 백년 마을, 숨은 해안을 섬사람처럼 보내기. 북환·시위·동해·마공 심층 탐방과 섬 크루즈, 해양목장, 어시장 산책, DIY 체험까지.","duration":"3박 4일","suitable_for":"슬로우 트래블 / 첫 심층 여행"},
    {"title":"澎湖慢旅 4 日｜多留一天给澎湖","description":"世界级玄武岩 × 百年聚落 × 海岸秘境，跟着岛民过一天。北环、西屿、东海、马公一次深度探索，搭配跨岛巡航与海牧体验、渔市场走读、小管一日干与花宅 DIY。","duration":"四天三夜","suitable_for":"深度慢旅"}), 503),

T("2026 秋遊澎湖｜環島 × 手作 × 摩西分海 療癒四日遊",
  "星晴旅行社的秋日療癒路線：親手餵食海魚、與烏賊拔河，享受炭烤海鮮與海鮮粥吃到飽；走訪跨海大橋與保存完整的二崁聚落，體驗仙人掌巴斯克手作；探訪鬼斧神工的風櫃洞與摩西分海奇景；最後漫步外婆的澎湖灣、參拜天后宮。在地專業導遊帶領，行程輕鬆愉快。",
  "親子 / 長輩 / 輕鬆環島", "四天三夜", "線上詢價",
  [{"label":"四天三夜行程","value":"線上詢價"}],
  ["Day1 抵達澎湖・海洋牧場（餵魚、炭烤海鮮吃到飽）",
   "Day2 跨海大橋、二崁聚落、大菓葉玄武岩、仙人掌巴斯克手作",
   "Day3 摩西分海、風櫃聽濤、南寮村、澎湖南環",
   "Day4 天后宮、篤行十村、文化走讀與伴手禮採購",
   "在地專業導遊帶領、貼心旅遊保險"],
  "住宿、餐食、在地導遊、手作體驗、旅遊保險",
  "行程輕鬆愉快，適合親子與長輩同行。",
  L({"title":"2026 Autumn Escape to Penghu｜Island, Crafts & Moses' Parting Sea","description":"A relaxing autumn journey through Penghu's sea, culture and local flavors: ocean ranch feeding and all-you-can-eat grilled oysters, the Great Bridge and Erkan village, a cactus Basque cheesecake workshop, the Moses' Parting Sea tidal path, Tianhou Temple and Duxing 10th Village.","duration":"4 days 3 nights","suitable_for":"Families / Seniors / Easy pace"},
    {"title":"2026 秋の澎湖｜島巡り×手作り×モーゼの海割れ 癒しの4日間","description":"海洋牧場で餌やりと牡蠣の炭火焼き食べ放題、跨海大橋と二崁集落、サボテンのバスクチーズケーキ作り、奎壁山「モーゼの海割れ」、天后宮と篤行十村へ。地元ガイド同行のゆったり旅。","duration":"3泊4日","suitable_for":"ファミリー／シニア"},
    {"title":"2026 가을 펑후｜섬 일주 × 수공예 × 모세의 기적 힐링 4일","description":"해양목장 먹이주기와 굴 숯불구이 무한리필, 대교와 얼칸 마을, 선인장 바스크 치즈케이크 만들기, 모세의 기적 갯길, 천후궁과 두싱10촌까지. 현지 가이드와 함께하는 여유로운 일정.","duration":"3박 4일","suitable_for":"가족 / 시니어 / 여유로운 일정"},
    {"title":"2026 秋游澎湖｜环岛 × 手作 × 摩西分海 疗愈四日游","description":"亲手喂食海鱼、炭烤海鲜吃到饱；走访跨海大桥与二崁聚落，体验仙人掌巴斯克手作；探访风柜洞与摩西分海奇景；漫步外婆的澎湖湾、参拜天后宫。","duration":"四天三夜","suitable_for":"亲子 / 长辈 / 轻松环岛"}), 504),

T("海好有你｜澎湖慢旅小旅行（海洋共好）",
  "慢慢走進島嶼，遇見海洋與生活——讓旅行成為一段與海洋共好的開始。每位旅客團費提撥 NT$200 作為海洋保育基金。四天三夜走訪鎖港漁市場的海洋餐桌小旅行、魚拓製作與即時料理共學、望安島生態與珊瑚復育浮潛、赤崁博藤基地再生文創 DIY，以及夜間星空導覽。",
  "永續旅行 / 海洋教育 / 親子", "四天三夜", "線上詢價",
  [{"label":"四天三夜（2 人成行・6 人成團）","value":"線上詢價"}],
  ["每人團費提撥 NT$200 作為海洋保育基金",
   "Day1 南環自由行、鎖港漁市場海洋餐桌、魚拓製作與料理共學",
   "Day2 望安島生態與聚落導覽、珊瑚復育及生態礁浮潛",
   "Day3 赤崁博藤基地再生文創 DIY、北環自由行、夜間星空導覽",
   "Day4 市區巡禮（天后宮、四眼井、日據郵便局、篤行十村）",
   "前 100 名旅客限定加贈海島 BBQ 晚宴"],
  "松山–澎湖來回機票、3 晚住宿、鎖港漁市場海洋餐桌小旅行、望安山海行一日遊、DIY 體驗、1 天午餐、1 天晚餐、250 萬旅責險＋20 萬醫療險",
  "2 人成行、6 人成團，歡迎散客報名，滿團即可出發。",
  L({"title":"Better for the Sea, Better with You｜Penghu Slow Travel Escape","description":"Slow down, step into the island, and discover the sea and local life. NT$200 from every traveler is donated to a marine conservation fund. Four days of ocean-to-table dining, Wang'an eco tour with coral restoration snorkeling, circular-craft DIY and a nighttime stargazing tour.","duration":"4 days 3 nights","suitable_for":"Sustainable travel / Marine education"},
    {"title":"海好有你｜澎湖スロートラベル（海と共に）","description":"島にゆっくり入り、海と暮らしに出会う旅。参加費からお一人NT$200を海洋保全基金へ。漁市場のオーシャン・トゥ・テーブル、望安島の生態ツアーとサンゴ再生シュノーケリング、循環クラフトDIY、星空ナイトツアー。","duration":"3泊4日","suitable_for":"サステナブル／海洋教育"},
    {"title":"바다에 좋고 당신과 더 좋게｜펑후 슬로우 트래블","description":"천천히 섬으로 들어가 바다와 삶을 만나는 여행. 1인당 NT$200을 해양보전기금에 기부. 어시장 오션투테이블, 왕안섬 생태 투어와 산호 복원 스노클링, 순환 공예 DIY, 밤 별빛 투어.","duration":"3박 4일","suitable_for":"지속가능 여행 / 해양 교육"},
    {"title":"海好有你｜澎湖慢旅小旅行（海洋共好）","description":"慢慢走进岛屿，遇见海洋与生活。每位旅客团费提拨 NT$200 作为海洋保育基金。四天三夜走访锁港渔市场海洋餐桌、望安岛生态与珊瑚复育浮潜、再生文创 DIY 与夜间星空导览。","duration":"四天三夜","suitable_for":"永续旅行 / 海洋教育 / 亲子"}), 505),

T("澎湖秘境忘憂島｜4 天 3 夜深度生態之旅",
  "私人島嶼・獨家海域的深度生態行程：親手復育珊瑚、潮間帶抓野生石斑魚、星空海上夜泊、珊瑚秘境浮潛、隱藏版無人島登陸與永續聚落自由行——六大深度體驗一次收藏。合法承租無人島、專業安全團隊全程守護。由珊瑚礁旅遊規劃。",
  "生態深度 / 企業領袖 / 特殊體驗", "四天三夜", "線上詢價",
  [{"label":"四天三夜（名額有限）","value":"線上詢價"}],
  ["親手復育珊瑚（Coral Restoration）",
   "潮間帶抓野生石斑魚",
   "星空海上夜泊・無人島營火",
   "珊瑚秘境浮潛、隱藏版無人島登陸",
   "永續聚落自由行",
   "合法承租無人島，專業安全團隊全程守護"],
  "住宿、餐食、船資、浮潛與生態活動、專業教練與安全團隊、保險",
  "名額有限；連怕水的人都會愛上的海洋之旅，高端企業領袖團體亦適合。",
  L({"title":"Wangyou Island Secret Escape｜4D3N Deep Eco Journey","description":"A private island and exclusive waters: hands-on coral restoration, intertidal grouper fishing, stargazing and overnight at sea, snorkeling in a coral sanctuary, landing on a hidden uninhabited island and a sustainable village visit — six unique experiences in one trip.","duration":"4 days 3 nights","suitable_for":"Deep eco / Corporate retreat"},
    {"title":"澎湖秘境・忘憂島｜3泊4日 深度エコツアー","description":"プライベート島と専用海域で過ごす特別な旅。サンゴの植え付け、潮間帯でのハタ捕り、星空の海上泊、サンゴ礁シュノーケリング、無人島上陸、サステナブル集落散策の6大体験。","duration":"3泊4日","suitable_for":"エコ深掘り／企業研修"},
    {"title":"펑후 비경 왕유섬｜3박4일 심층 생태 여행","description":"프라이빗 섬과 전용 해역에서의 특별한 여정: 산호 복원, 갯벌 그루퍼 잡기, 별빛 해상 1박, 산호 성역 스노클링, 숨겨진 무인도 상륙, 지속가능 마을 산책까지 6대 체험.","duration":"3박 4일","suitable_for":"심층 생태 / 기업 연수"},
    {"title":"澎湖秘境忘忧岛｜4 天 3 夜深度生态之旅","description":"私人岛屿・独家海域的深度生态行程：亲手复育珊瑚、潮间带抓野生石斑鱼、星空海上夜泊、珊瑚秘境浮潜、隐藏版无人岛登陆与永续聚落自由行。","duration":"四天三夜","suitable_for":"生态深度 / 企业领袖 / 特殊体验"}), 506),

T("澎湖永續海島慢旅｜四天三夜・三晚不換宿",
  "低碳・在地・共生的澎湖主題遊程：三晚不換宿入住環保標章旅宿頌華私墅（節水節能、減塑備品、在地採購），以養殖廢棄蚵殼再生創作體驗海洋循環經濟，在地當令漁獲直送的島嶼一桌。20 人以上成團、可彈性分梯，適合企業 ESG 與員工旅遊包團。由行路旅行社規劃。",
  "企業 ESG / 員工旅遊 / 永續", "四天三夜（三晚不換宿）", "線上詢價",
  [{"label":"四天三夜（20 人以上成團）","value":"線上詢價"}],
  ["三晚不換宿：環保標章旅宿頌華私墅",
   "永續材料手作：養殖廢棄蚵殼再生創作",
   "在地海鮮餐廳：當令漁獲直送、縮短食物里程",
   "Day2 平台遊艇低碳跳島（將軍嶼、虎井嶼）＋離島無菜單漁獲午餐",
   "Day3 包車北環：大菓葉玄武岩、二崁古厝、跨海大橋"],
  "住宿（3 晚不換宿）、餐食、遊艇跳島、包車環島、手作體驗、保險",
  "20 人以上成團，可彈性分梯；企業 ESG／員工旅遊可包團。",
  L({"title":"Penghu Sustainable Island Slow Travel｜4D3N, One Hotel","description":"A low-carbon, local and symbiotic theme tour: three nights at an eco-labeled villa without changing hotels, upcycled oyster-shell crafts exploring the marine circular economy, and farm-to-table island dining. Min 20 guests — ideal for corporate ESG and staff trips.","duration":"4 days 3 nights","suitable_for":"Corporate ESG / Staff trips"},
    {"title":"澎湖サステナブル・アイランド スローツアー｜3泊同一宿","description":"低炭素・地域・共生をテーマにした澎湖の旅。エコラベル取得の宿に3連泊、養殖の廃棄牡蠣殻をアップサイクルする手作り体験、地元直送の島の食卓。20名以上で催行、企業ESG・社員旅行に。","duration":"3泊4日","suitable_for":"企業ESG／社員旅行"},
    {"title":"펑후 지속가능 아일랜드 슬로우 투어｜3박 한 숙소","description":"저탄소·로컬·공생을 주제로 한 펑후 여행. 친환경 인증 숙소에서 3박 연박, 폐굴껍질 업사이클 공예로 배우는 해양 순환경제, 산지직송 섬 밥상. 20인 이상 출발, 기업 ESG·워크숍에 적합.","duration":"3박 4일","suitable_for":"기업 ESG / 워크숍"},
    {"title":"澎湖永续海岛慢旅｜四天三夜・三晚不换宿","description":"低碳・在地・共生的澎湖主题游程：三晚不换宿入住环保标章旅宿，以养殖废弃蚵壳再生创作体验海洋循环经济，在地当令渔获直送。20 人以上成团，企业 ESG／员工旅游可包团。","duration":"四天三夜（三晚不换宿）","suitable_for":"企业 ESG / 员工旅游 / 永续"}), 507),

T("澎湖漫遊 4 天 3 夜｜台灣好行環島輕旅",
  "漂浮在台灣海峽上的美麗群島，用最輕鬆省錢的方式玩透澎湖：空港快線 × 台灣好行三路線觀光巴士 × 無限次搭乘公車，只要 NT$560 交通費即能暢遊環全澎湖 4 天 3 夜。走訪生活博物館與中央老街、漁市場導覽、台灣好行北環、七美望安跳島與湖島路線。由長立旅行社與長春大飯店規劃。",
  "背包客 / 自由行 / 預算友善", "四天三夜", "交通費 NT$ 560 起",
  [{"label":"台灣好行交通套票","value":"NT$ 560"},{"label":"含住宿套裝","value":"線上詢價"}],
  ["空港快線＋台灣好行三路線＋無限次公車，NT$560 玩 4 天 3 夜",
   "Day1 生活博物館、中央老街漫步",
   "Day2 漁市場導覽、台灣好行北環",
   "Day3 七美、望安走訪澎湖灣",
   "Day4 台灣好行湖島線"],
  "台灣好行三路線觀光巴士、空港快線、無限次公車搭乘",
  "住宿可另洽長春大飯店；適合想自由行又不想租車的旅客。",
  L({"title":"Penghu Roaming 4D3N｜Taiwan Tourist Shuttle Easy Trip","description":"Explore the beautiful archipelago the easy, budget way: airport express + three Taiwan Tourist Shuttle routes + unlimited local buses — just NT$560 in transport covers four days around Penghu, from the Living Museum and Old Street to the North Ring, Qimei and Wang'an.","duration":"4 days 3 nights","suitable_for":"Backpackers / Independent / Budget"},
    {"title":"澎湖漫遊 3泊4日｜台湾好行バスで巡る島旅","description":"台湾海峡に浮かぶ美しい群島を、いちばん手軽に。空港エクスプレス＋台湾好行3路線＋路線バス乗り放題、交通費NT$560で4日間の澎湖一周。生活博物館、魚市場、北環、七美・望安へ。","duration":"3泊4日","suitable_for":"バックパッカー／個人旅行"},
    {"title":"펑후 로밍 3박4일｜대만 하오싱 버스 이지 트립","description":"타이완 해협의 아름다운 군도를 가장 쉽고 알뜰하게. 공항 익스프레스+대만 하오싱 3개 노선+시내버스 무제한, 교통비 NT$560로 4일간 펑후 일주. 생활박물관, 어시장, 북환, 치메이·왕안까지.","duration":"3박 4일","suitable_for":"배낭여행 / 자유여행 / 알뜰"},
    {"title":"澎湖漫游 4 天 3 夜｜台湾好行环岛轻旅","description":"空港快线 × 台湾好行三路线观光巴士 × 无限次搭乘公车，只要 NT$560 交通费即能畅游环全澎湖 4 天 3 夜。走访生活博物馆、渔市场、台湾好行北环与七美望安。","duration":"四天三夜","suitable_for":"背包客 / 自由行 / 预算友善"}), 508),

# ── 6D5N：非四天三夜，放「官方合作特色行程」分頁 ──
T("澎湖深度旅遊 + 海鮮美食 6 天 5 夜｜Batik Air 包機直飛",
  "馬來西亞出發的獨家包機行程：Batik Air 吉隆坡（KUL）直飛馬公（MZG），六天五夜深度走訪世界級玄武岩海岸奇觀、澎湖古窯文化、絕美海島蛇頭山，品嚐豐盛海鮮美食，純玩無購物。只此一團、名額有限。由程逸商旅 Orange Leisure 規劃。",
  "海外客人 / 包機團 / 深度美食", "六天五夜", "線上詢價",
  [{"label":"六天五夜包機團","value":"線上詢價"}],
  ["Batik Air 包機直飛：KUL–MZG，去程 OD684 08:20/13:00、回程 OD685 16:10/20:30",
   "世界級玄武岩海岸奇觀",
   "澎湖古窯文化之旅",
   "絕美海島蛇頭山",
   "海鮮美食與在地文化",
   "純玩無購物、只此一團"],
  "包機來回機票、住宿、餐食、車資與導覽",
  "此為 10/22–10/27 馬來西亞出發包機團（六天五夜，非四天三夜行程）。",
  L({"title":"Penghu In-Depth & Gourmet 6D5N｜Batik Air Charter","description":"An exclusive charter itinerary from Malaysia: Batik Air direct KUL–MZG, six days exploring world-class basalt coastlines, Penghu's heritage kilns, Snake Head Mountain and abundant seafood. No shopping stops, one group only.","duration":"6 days 5 nights","suitable_for":"Overseas guests / Charter group"},
    {"title":"澎湖深度旅行＋海鮮グルメ 5泊6日｜バティックエア チャーター","description":"マレーシア発の限定チャーター。クアラルンプール（KUL）から馬公（MZG）へ直行、世界級の玄武岩海岸、古窯文化、蛇頭山、海鮮グルメを巡る6日間。ノーショッピング、1グループ限定。","duration":"5泊6日","suitable_for":"海外ゲスト／チャーター団体"},
    {"title":"펑후 심층 여행+해산물 미식 5박6일｜바틱에어 전세기","description":"말레이시아 출발 독점 전세기 일정. 쿠알라룸푸르(KUL)에서 마공(MZG) 직항, 세계급 현무암 해안, 고요 문화, 서두산과 풍성한 해산물을 즐기는 6일. 쇼핑 없음, 단 한 팀 한정.","duration":"5박 6일","suitable_for":"해외 고객 / 전세기 단체"},
    {"title":"澎湖深度旅游 + 海鲜美食 6 天 5 夜｜Batik Air 包机直飞","description":"马来西亚出发的独家包机行程：Batik Air 吉隆坡直飞马公，六天五夜深度走访世界级玄武岩海岸、澎湖古窑文化、绝美海岛蛇头山，品尝丰盛海鲜美食，纯玩无购物。","duration":"六天五夜","suitable_for":"海外客人 / 包机团 / 深度美食"}), 509, tabs=["featured"]),
]

def main():
    conn = psycopg2.connect(sys.argv[1]); cur = conn.cursor()
    added = skipped = 0
    for t in TOURS:
        cur.execute("SELECT 1 FROM tours WHERE title=%s", (t["title"],))
        if cur.fetchone():
            skipped += 1; continue
        for lang in t["i18n"].values():
            if "duration" in lang:
                lang["duration"] = lang["duration"][:30]
        cur.execute("""INSERT INTO tours
            (tabs,title,description,suitable_for,duration,price_display,prices,modal_data,i18n,
             sort_order,is_active,badge_text,badge_class,image_url)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,TRUE,%s,%s,%s)""",
            (json.dumps(t["tabs"], ensure_ascii=False), t["title"][:120], t["description"],
             t["suitable_for"][:120], t["duration"][:30], t["price_display"][:60],
             json.dumps(t["prices"], ensure_ascii=False),
             json.dumps(t["modal_data"], ensure_ascii=False),
             json.dumps(t["i18n"], ensure_ascii=False),
             t["sort_order"], "主題遊程徵選獲選行程", "award",
             f"/images/tours/t{t['sort_order']}.jpg"))
        added += 1
    # 一併補上先前公會 38 筆徽章底色（badge_class 原為空字串 → 無背景）
    cur.execute("UPDATE tours SET badge_class='guild' WHERE badge_text='2026 公會精選' AND (badge_class IS NULL OR badge_class='')")
    fixed = cur.rowcount
    conn.commit(); cur.close(); conn.close()
    print(f"added={added} skipped={skipped} guild_badge_fixed={fixed}")

if __name__ == "__main__":
    main()
