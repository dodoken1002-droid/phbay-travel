# -*- coding: utf-8 -*-
"""行程獨立頁面：/tours（總覽，可依天數或海域篩選）與 /tours/<id>（單一行程）。

資料全部來自 tours 資料表（後台 /admin 維護），本模組只負責渲染，不新增任何
價格、日期或行程細節；欄位沒填的區塊就不顯示。app.py 負責查資料庫與共用外殼。
所有資料庫文字一律跳脫後輸出。
"""

import html as _html
import json
import re
from copy import deepcopy
from datetime import date, datetime, timedelta, timezone
from urllib.parse import urlencode

SITE = 'https://www.phbay.info'
LINE_URL = 'https://line.me/R/ti/p/@phbay2018'
TAIPEI = timezone(timedelta(hours=8))

# 分頁鍵與首頁行程區塊一致（script.js TAB_KEYS、app.py get_tours() 分組）
PACKAGE_TABS = ('featured', '2d1n', '3d2n', '4d3n')
SEA_TABS = ('north-sea', 'east-sea', 'south-sea', 'main-island')
TAB_LABELS = {
    'featured': '官方合作特色行程', '2d1n': '兩天一夜', '3d2n': '三天兩夜', '4d3n': '四天三夜',
    'north-sea': '北海海域', 'east-sea': '東海海域', 'south-sea': '南海海域', 'main-island': '本島海域',
}
# 篩選器：group 鍵對應多個分頁
FILTER_GROUPS = {'package': PACKAGE_TABS, 'single': SEA_TABS}
FILTER_LABELS = {'package': '全部套裝行程', 'single': '全部單日行程'}

SUPPORTED_LANGS = ('zh-tw', 'en', 'ja', 'ko', 'zh-cn')
TRANSLATION_LANGS = SUPPORTED_LANGS[1:]

# Server-rendered tour pages use the same i18n keys stored by the existing admin
# editor.  Missing content falls back field-by-field to Traditional Chinese.
_UI = {
    'zh-tw': {
        'brand': '潮旅國際旅行社', 'home': '首頁', 'overview': '行程總覽',
        'all': '全部', 'all_tours': '全部行程', 'package_by_days': '套裝・依天數',
        'single_by_area': '單日・依海域', 'filters': '行程篩選', 'count': '共 {n} 個行程',
        'empty': '這個分類目前沒有上架中的行程，', 'see_all': '看全部行程',
        'index_heading': '澎湖行程總覽', 'package_heading': '澎湖套裝行程',
        'single_heading': '澎湖單日行程', 'north_heading': '澎湖北海一日遊行程',
        'east_heading': '澎湖東海一日遊行程', 'south_heading': '澎湖南海一日遊行程',
        'main_heading': '澎湖本島海上活動與一日遊', 'dynamic_heading': '澎湖{label}行程',
        'lead': '潮旅國際旅行社整理的澎湖行程：套裝行程依天數分類，單日跳島與海上活動依海域分類。點進每個行程可看行程安排、費用包含、注意事項與適合對象；想確認出發日與名額，歡迎 LINE 或線上諮詢。',
        'index_cta': '不確定哪個行程適合？告訴我們天數、同行者與想玩的海域，在地人幫你排。',
        'index_meta': '含套裝行程（兩天一夜到四天三夜）與北海、東海、南海、本島一日遊，可看行程安排、費用包含與注意事項。',
        'days': '天數', 'suitable': '適合', 'price': '價格', 'category': '分類',
        'book': '前往預購訂位', 'ask': '詢問這個行程', 'line': 'LINE 諮詢',
        'fee': '費用', 'dates': '出發日期', 'availability': '實際名額與是否成團以報名確認為準。',
        'past_dates': '本行程公告的梯次都已出發。想詢問下一梯或包團日期，請',
        'online': '線上諮詢', 'or_line': '或 LINE 聯絡我們。', 'daily': '每日行程',
        'highlights': '行程亮點', 'content': '行程內容', 'includes': '費用包含',
        'who': '適合誰', 'notes': '注意事項', 'photos': '行程照片與海報',
        'photo_alt': '行程照片 {n}', 'tide_title': '出發前查潮汐', 'tide_link': '澎湖潮汐查詢',
        'tide_related': '這個行程的活動時間跟潮汐有關（例如潮間帶、浮潛），實際報到時間會依當天潮汐調整。出發前可先查退潮時段。',
        'tide_general': '澎湖海上與海邊行程都會受潮汐、風浪影響。排行程前先看看出發日的漲退潮時間，玩得更順。',
        'agency': '主辦單位', 'partner': '合作夥伴', 'license': '證號', 'provider': '行程提供單位',
        'assist': '潮旅國際旅行社可協助諮詢與報名。', 'related': '相關文章與攻略',
        'related_guide': '延伸攻略', 'other': '其他行程', 'see_all_arrow': '看全部 →',
        'detail_cta': '想確認出發日、名額或客製調整？留下需求，專人回覆。',
        'cta_heading': '想把行程交給在地人排？', 'form': '線上諮詢表單',
        'tab_featured': '官方合作特色行程', 'tab_2d1n': '兩天一夜', 'tab_3d2n': '三天兩夜',
        'tab_4d3n': '四天三夜', 'tab_north-sea': '北海海域', 'tab_east-sea': '東海海域',
        'tab_south-sea': '南海海域', 'tab_main-island': '本島海域',
        'filter_package': '全部套裝行程', 'filter_single': '全部單日行程',
    },
    'en': {
        'brand': 'PH Bay Travel', 'home': 'Home', 'overview': 'Tours', 'all': 'All',
        'all_tours': 'All tours', 'package_by_days': 'Packages by duration',
        'single_by_area': 'Day tours by area', 'filters': 'Tour filters', 'count': '{n} tours',
        'empty': 'No active tours are available in this category. ', 'see_all': 'View all tours',
        'index_heading': 'Penghu Tours', 'package_heading': 'Penghu Package Tours',
        'single_heading': 'Penghu Day Tours', 'north_heading': 'Penghu North Sea Day Tours',
        'east_heading': 'Penghu East Sea Day Tours', 'south_heading': 'Penghu South Sea Day Tours',
        'main_heading': 'Penghu Main Island Activities & Day Tours', 'dynamic_heading': 'Penghu {label} Tours',
        'lead': 'Browse Penghu packages by duration and island-hopping or water activities by area. Open a tour to see its itinerary, inclusions, notes and who it suits. Contact us on LINE or online to confirm dates and availability.',
        'index_cta': 'Not sure which tour fits? Tell our local team your trip length, companions and preferred area.',
        'index_meta': 'Browse 2-day to 4-day packages and North Sea, East Sea, South Sea and main-island day tours, with itineraries, inclusions and important notes.',
        'days': 'Duration', 'suitable': 'Best for', 'price': 'Price', 'category': 'Category',
        'book': 'Book now', 'ask': 'Ask about this tour', 'line': 'Chat on LINE', 'fee': 'Prices',
        'dates': 'Departure dates', 'availability': 'Availability and minimum group size are confirmed when you book.',
        'past_dates': 'All listed departures have passed. For the next departure or a private group, ',
        'online': 'contact us online', 'or_line': ' or message us on LINE.', 'daily': 'Daily itinerary',
        'highlights': 'Highlights', 'content': 'Tour itinerary', 'includes': 'Included', 'who': 'Who it suits',
        'notes': 'Important notes', 'photos': 'Photos & posters', 'photo_alt': 'tour photo {n}',
        'tide_title': 'Check tides before departure', 'tide_link': 'Penghu tide forecast',
        'tide_related': 'This activity depends on tides. Check-in time may be adjusted for the day’s conditions; please check the low-tide period before departure.',
        'tide_general': 'Penghu sea and coastal tours can be affected by tides, wind and waves. Check the tide forecast when planning your day.',
        'agency': 'Operator', 'partner': 'Partner', 'license': 'Licence', 'provider': 'Tour provider',
        'assist': 'PH Bay Travel can assist with enquiries and bookings.', 'related': 'Related articles & guides',
        'related_guide': 'Travel guide', 'other': 'Other tours', 'see_all_arrow': 'View all →',
        'detail_cta': 'Want to confirm dates, availability or customise the trip? Send us your request.',
        'cta_heading': 'Let a local expert plan your trip', 'form': 'Online enquiry',
        'tab_featured': 'Official featured tours', 'tab_2d1n': '2 days / 1 night', 'tab_3d2n': '3 days / 2 nights',
        'tab_4d3n': '4 days / 3 nights', 'tab_north-sea': 'North Sea', 'tab_east-sea': 'East Sea',
        'tab_south-sea': 'South Sea', 'tab_main-island': 'Main Island',
        'filter_package': 'All packages', 'filter_single': 'All day tours',
    },
    'ja': {
        'brand': '潮旅国際旅行社', 'home': 'ホーム', 'overview': 'ツアー一覧', 'all': 'すべて',
        'all_tours': 'すべてのツアー', 'package_by_days': '日数別パッケージ', 'single_by_area': '海域別日帰りツアー',
        'filters': 'ツアー絞り込み', 'count': '{n}件のツアー', 'empty': 'このカテゴリーには現在販売中のツアーがありません。',
        'see_all': 'すべてのツアーを見る', 'index_heading': '澎湖ツアー一覧', 'package_heading': '澎湖パッケージツアー',
        'single_heading': '澎湖日帰りツアー', 'north_heading': '澎湖北海日帰りツアー', 'east_heading': '澎湖東海日帰りツアー',
        'south_heading': '澎湖南海日帰りツアー', 'main_heading': '澎湖本島アクティビティ・日帰りツアー',
        'dynamic_heading': '澎湖{label}ツアー', 'lead': '日数別のパッケージと、海域別の離島・マリンアクティビティをご覧いただけます。各ページで日程、料金に含まれるもの、注意事項、対象者を確認できます。',
        'index_cta': 'どのツアーが合うか迷ったら、日数・同行者・希望エリアを現地スタッフにお知らせください。',
        'index_meta': '2日間から4日間のパッケージ、北海・東海・南海・本島の日帰りツアーをご案内します。',
        'days': '日数', 'suitable': 'おすすめ', 'price': '料金', 'category': 'カテゴリー', 'book': '予約へ進む',
        'ask': 'このツアーについて問い合わせる', 'line': 'LINEで相談', 'fee': '料金', 'dates': '出発日',
        'availability': '空席と催行可否は予約確認時にご案内します。', 'past_dates': '掲載の出発日は終了しました。次回または団体旅行は',
        'online': 'オンラインでお問い合わせ', 'or_line': 'またはLINEでご連絡ください。', 'daily': '日程表',
        'highlights': 'ツアーの見どころ', 'content': 'ツアー内容', 'includes': '料金に含まれるもの', 'who': 'おすすめの方',
        'notes': '注意事項', 'photos': '写真・ポスター', 'photo_alt': 'ツアー写真 {n}',
        'tide_title': '出発前に潮汐を確認', 'tide_link': '澎湖の潮汐情報',
        'tide_related': 'このアクティビティは潮汐の影響を受けます。当日の潮位により集合時間が変更される場合があります。',
        'tide_general': '澎湖の海上・海辺のツアーは潮汐、風、波の影響を受けます。事前に潮汐をご確認ください。',
        'agency': '主催者', 'partner': 'パートナー', 'license': '登録番号', 'provider': 'ツアー提供者',
        'assist': '潮旅国際旅行社がご相談・予約をお手伝いします。', 'related': '関連記事・ガイド',
        'related_guide': '関連ガイド', 'other': 'その他のツアー', 'see_all_arrow': 'すべて見る →',
        'detail_cta': '出発日、空席、カスタマイズについてお気軽にお問い合わせください。',
        'cta_heading': '現地スタッフに旅程を相談', 'form': 'オンライン相談',
        'tab_featured': '公式おすすめツアー', 'tab_2d1n': '2日1泊', 'tab_3d2n': '3日2泊', 'tab_4d3n': '4日3泊',
        'tab_north-sea': '北海エリア', 'tab_east-sea': '東海エリア', 'tab_south-sea': '南海エリア', 'tab_main-island': '本島エリア',
        'filter_package': 'すべてのパッケージ', 'filter_single': 'すべての日帰りツアー',
    },
    'ko': {
        'brand': 'PH Bay Travel', 'home': '홈', 'overview': '투어 목록', 'all': '전체', 'all_tours': '전체 투어',
        'package_by_days': '기간별 패키지', 'single_by_area': '해역별 당일 투어', 'filters': '투어 필터',
        'count': '투어 {n}개', 'empty': '현재 이 카테고리에 판매 중인 투어가 없습니다. ', 'see_all': '전체 투어 보기',
        'index_heading': '펑후 투어', 'package_heading': '펑후 패키지 투어', 'single_heading': '펑후 당일 투어',
        'north_heading': '펑후 북해 당일 투어', 'east_heading': '펑후 동해 당일 투어', 'south_heading': '펑후 남해 당일 투어',
        'main_heading': '펑후 본섬 액티비티 및 당일 투어', 'dynamic_heading': '펑후 {label} 투어',
        'lead': '기간별 패키지와 해역별 섬 투어 및 해양 액티비티를 확인하세요. 각 투어에서 일정, 포함 사항, 주의 사항과 추천 대상을 볼 수 있습니다.',
        'index_cta': '어떤 투어가 맞는지 고민되면 여행 기간, 동행자와 희망 지역을 현지 팀에 알려 주세요.',
        'index_meta': '2~4일 패키지와 북해·동해·남해·본섬 당일 투어의 일정, 포함 사항과 주의 사항을 확인하세요.',
        'days': '기간', 'suitable': '추천 대상', 'price': '가격', 'category': '카테고리', 'book': '예약하기',
        'ask': '이 투어 문의하기', 'line': 'LINE 문의', 'fee': '요금', 'dates': '출발일',
        'availability': '잔여석과 출발 여부는 예약 확인 시 안내됩니다.', 'past_dates': '게시된 출발 일정이 모두 종료되었습니다. 다음 일정 또는 단체 여행은 ',
        'online': '온라인 문의', 'or_line': ' 또는 LINE으로 문의해 주세요.', 'daily': '일별 일정',
        'highlights': '투어 하이라이트', 'content': '투어 일정', 'includes': '포함 사항', 'who': '추천 대상',
        'notes': '주의 사항', 'photos': '사진 및 포스터', 'photo_alt': '투어 사진 {n}',
        'tide_title': '출발 전 조석 확인', 'tide_link': '펑후 조석 정보',
        'tide_related': '이 활동은 조석의 영향을 받으며 당일 상황에 따라 집결 시간이 변경될 수 있습니다.',
        'tide_general': '펑후의 해상 및 해변 투어는 조석, 바람과 파도의 영향을 받습니다. 출발 전 조석을 확인하세요.',
        'agency': '주최사', 'partner': '파트너', 'license': '등록 번호', 'provider': '투어 제공처',
        'assist': 'PH Bay Travel에서 상담과 예약을 도와드립니다.', 'related': '관련 글 및 가이드',
        'related_guide': '관련 가이드', 'other': '다른 투어', 'see_all_arrow': '전체 보기 →',
        'detail_cta': '출발일, 잔여석 또는 맞춤 일정은 문의를 남겨 주세요.', 'cta_heading': '현지 전문가에게 일정 맡기기',
        'form': '온라인 문의', 'tab_featured': '공식 추천 투어', 'tab_2d1n': '2일 1박', 'tab_3d2n': '3일 2박',
        'tab_4d3n': '4일 3박', 'tab_north-sea': '북해', 'tab_east-sea': '동해', 'tab_south-sea': '남해',
        'tab_main-island': '본섬', 'filter_package': '전체 패키지', 'filter_single': '전체 당일 투어',
    },
    'zh-cn': {
        'brand': '潮旅国际旅行社', 'home': '首页', 'overview': '行程总览', 'all': '全部', 'all_tours': '全部行程',
        'package_by_days': '套装・按天数', 'single_by_area': '单日・按海域', 'filters': '行程筛选', 'count': '共 {n} 个行程',
        'empty': '这个分类目前没有上架中的行程，', 'see_all': '查看全部行程', 'index_heading': '澎湖行程总览',
        'package_heading': '澎湖套装行程', 'single_heading': '澎湖单日行程', 'north_heading': '澎湖北海一日游行程',
        'east_heading': '澎湖东海一日游行程', 'south_heading': '澎湖南海一日游行程',
        'main_heading': '澎湖本岛海上活动与一日游', 'dynamic_heading': '澎湖{label}行程',
        'lead': '潮旅国际旅行社整理的澎湖行程：套装行程按天数分类，单日跳岛与海上活动按海域分类。进入行程可查看安排、费用包含、注意事项与适合对象。',
        'index_cta': '不确定哪个行程适合？告诉我们天数、同行者与想玩的海域，由当地人帮你安排。',
        'index_meta': '包含两天一夜到四天三夜套装，以及北海、东海、南海、本岛一日游，可查看行程安排、费用包含与注意事项。',
        'days': '天数', 'suitable': '适合', 'price': '价格', 'category': '分类', 'book': '前往预购订位',
        'ask': '咨询这个行程', 'line': 'LINE 咨询', 'fee': '费用', 'dates': '出发日期',
        'availability': '实际名额与是否成团以报名确认为准。', 'past_dates': '本行程公告的班次都已出发。想咨询下一班或包团日期，请',
        'online': '在线咨询', 'or_line': '或通过 LINE 联系我们。', 'daily': '每日行程', 'highlights': '行程亮点',
        'content': '行程内容', 'includes': '费用包含', 'who': '适合谁', 'notes': '注意事项', 'photos': '行程照片与海报',
        'photo_alt': '行程照片 {n}', 'tide_title': '出发前查询潮汐', 'tide_link': '澎湖潮汐查询',
        'tide_related': '这个活动时间与潮汐有关，实际报到时间会依当天潮汐调整。出发前可先查询退潮时段。',
        'tide_general': '澎湖海上与海边行程会受潮汐、风浪影响，安排行程前可先查看涨退潮时间。',
        'agency': '主办单位', 'partner': '合作伙伴', 'license': '证号', 'provider': '行程提供单位',
        'assist': '潮旅国际旅行社可协助咨询与报名。', 'related': '相关文章与攻略', 'related_guide': '延伸攻略',
        'other': '其他行程', 'see_all_arrow': '查看全部 →', 'detail_cta': '想确认出发日、名额或客制调整？留下需求，专人回复。',
        'cta_heading': '想把行程交给当地人安排？', 'form': '在线咨询表单',
        'tab_featured': '官方合作特色行程', 'tab_2d1n': '两天一夜', 'tab_3d2n': '三天两夜', 'tab_4d3n': '四天三夜',
        'tab_north-sea': '北海海域', 'tab_east-sea': '东海海域', 'tab_south-sea': '南海海域', 'tab_main-island': '本岛海域',
        'filter_package': '全部套装行程', 'filter_single': '全部单日行程',
    },
}


def normalize_lang(lang):
    lang = str(lang or '').strip().lower()
    return lang if lang in SUPPORTED_LANGS else 'zh-tw'


def _ui(lang):
    return _UI[normalize_lang(lang)]


def tab_label(key, lang='zh-tw'):
    return _ui(lang).get(f'tab_{key}', TAB_LABELS.get(key, key))


def filter_label(key, lang='zh-tw'):
    return _ui(lang).get(f'filter_{key}', FILTER_LABELS.get(key, key))


def localized_tour(tour, lang='zh-tw'):
    """Return a copy localized from tours.i18n, with per-field Chinese fallback."""
    lang = normalize_lang(lang)
    out = deepcopy(dict(tour))
    if lang == 'zh-tw':
        return out
    translations = tour.get('i18n') if isinstance(tour.get('i18n'), dict) else {}
    tr = translations.get(lang) if isinstance(translations.get(lang), dict) else {}
    for key in ('title', 'badge_text', 'description', 'suitable_for', 'duration', 'price_display'):
        if str(tr.get(key) or '').strip():
            out[key] = tr[key]
    base_md = deepcopy(_modal(tour))
    tr_md = tr.get('modal_data') if isinstance(tr.get('modal_data'), dict) else {}
    for key in ('subtitle', 'includes', 'notice', 'notes'):
        if str(tr_md.get(key) or '').strip():
            base_md[key] = tr_md[key]
    for key in ('highlights', 'dates', 'days'):
        if isinstance(tr_md.get(key), list) and tr_md[key]:
            base_md[key] = deepcopy(tr_md[key])
    out['modal_data'] = base_md
    if isinstance(tr.get('prices'), list) and tr['prices']:
        out['prices'] = deepcopy(tr['prices'])
    return out


def available_languages(tour):
    """Languages with meaningful translated tour content for detail hreflang."""
    translations = tour.get('i18n') if isinstance(tour.get('i18n'), dict) else {}
    available = []
    for lang in TRANSLATION_LANGS:
        tr = translations.get(lang)
        if not isinstance(tr, dict):
            continue
        md = tr.get('modal_data') if isinstance(tr.get('modal_data'), dict) else {}
        if any(str(tr.get(k) or '').strip() for k in ('title', 'description')) or any(
                bool(md.get(k)) for k in ('highlights', 'days', 'includes', 'notes')):
            available.append(lang)
    return available

# 相關文章比對用詞：行程文字裡出現的地名／活動，拿去對文章標題、標籤、摘要
# 不收「追風」：音樂燈光節與別家的風浪板「追風派對」都用這個詞，會配到錯的文章
_KEYWORDS = (
    '望安', '七美', '吉貝', '目斗嶼', '員貝', '鳥嶼', '東吉', '西吉', '東嶼坪', '西嶼坪',
    '南方四島', '藍洞', '桶盤', '虎井', '忘憂島', '龍蝦', '險礁', '澎澎灘', '小門', '鯨魚洞',
    '西嶼', '白沙', '湖西', '風櫃', '山水', '隘門', '內海', '跨海大橋', '二崁', '花宅', '天台山',
    '綠蠵龜', '海龜', '潮間帶', '浮潛', '潛水', 'SUP', '獨木舟', '風帆', '風浪板', '夜釣', '小管',
    '花火', '音樂節', '燈光節', '石斑', '摩西分海', '薰衣草', '燕鷗', '玄武岩', '海洋牧場',
    '牡蠣', '露營', '親子', '海鮮',
)
_TAB_KEYWORDS = {
    'north-sea': ('北海', '吉貝', '目斗嶼', '險礁', '北環'),
    'east-sea': ('東海', '員貝', '鳥嶼', '澎澎灘'),
    'south-sea': ('南海', '七美', '望安', '南方四島', '藍洞'),
    'main-island': ('馬公', '內海'),
}
# 太通用的詞只在標題／標籤命中時算 1 分，避免「海鮮」「親子」把不相干的文章帶進來
_GENERIC_KEYWORDS = frozenset(('親子', '海鮮', '潮間帶', '浮潛', '潛水', '玄武岩', '跨海大橋', 'SUP', '獨木舟', '露營'))
_MIN_RELATED_SCORE = 3

# 行程文字出現這些詞 → 行程時間受潮汐影響，潮汐提醒改成強調版
_TIDE_WORDS = ('潮間帶', '潮汐', '退潮', '摩西分海', '照海', '夜探', '抓魚', '浮潛', '石滬')

TOUR_STYLE = (
    '<style>'
    '.tp-wrap{max-width:1080px;margin:0 auto;padding:32px 20px 60px}'
    '.tp-wrap h1{font-size:clamp(1.6rem,4vw,2.2rem);color:var(--blue-dark);font-weight:800;line-height:1.35;margin:6px 0 10px}'
    '.tp-crumb{font-size:.86rem;color:var(--text-light);margin-bottom:10px}'
    '.tp-crumb a{color:var(--blue-main)}'
    '.tp-lead{color:var(--text-mid);line-height:1.9;max-width:760px}'
    '.tp-filters{margin:22px 0 8px}'
    '.tp-filter-row{display:flex;flex-wrap:wrap;align-items:center;gap:8px;margin-bottom:10px}'
    '.tp-filter-label{font-weight:800;color:var(--blue-dark);font-size:.9rem;min-width:104px}'
    '.tp-chip{display:inline-block;padding:6px 14px;border-radius:20px;background:var(--blue-pale);color:var(--blue-main);font-size:.88rem;font-weight:600;text-decoration:none}'
    '.tp-chip:hover{background:#d9ecf8}'
    '.tp-chip.active{background:var(--blue-main);color:#fff}'
    '.tp-count{color:var(--text-light);font-size:.9rem;margin:6px 0 18px}'
    '.tp-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(290px,1fr));gap:22px}'
    '.tp-card{display:flex;flex-direction:column;background:#fff;border:1px solid #e6edf3;border-radius:16px;overflow:hidden;box-shadow:0 2px 10px rgba(0,0,0,.05);text-decoration:none;color:inherit;transition:.2s}'
    '.tp-card:hover{transform:translateY(-3px);box-shadow:var(--shadow-hover)}'
    '.tp-card-img{position:relative;height:190px;overflow:hidden;background:var(--blue-pale)}'
    '.tp-card-img img{width:100%;height:100%;object-fit:cover}'
    '.tp-badge{position:absolute;top:12px;left:12px;background:rgba(11,94,158,.92);color:#fff;font-size:.74rem;font-weight:700;padding:3px 10px;border-radius:20px;max-width:calc(100% - 24px)}'
    '.tp-card-body{padding:16px 18px 18px;display:flex;flex-direction:column;gap:8px;flex:1}'
    '.tp-card-body h2{font-size:1.08rem;color:var(--blue-dark);line-height:1.45;margin:0}'
    '.tp-card-body p{color:var(--text-mid);font-size:.9rem;line-height:1.65;margin:0}'
    '.tp-meta{display:flex;flex-wrap:wrap;gap:6px 14px;font-size:.84rem;color:var(--text-mid)}'
    '.tp-meta i{color:var(--blue-main);margin-right:4px}'
    '.tp-price{margin-top:auto;padding-top:6px;font-weight:800;color:#c0392b}'
    '.tp-tags{display:flex;flex-wrap:wrap;gap:6px}'
    '.tp-tag{background:var(--blue-pale);color:var(--blue-main);font-size:.74rem;padding:2px 9px;border-radius:20px}'
    '.tp-hero{display:grid;grid-template-columns:1.1fr 1fr;gap:32px;align-items:start;margin:8px 0 10px}'
    '.tp-hero-img{border-radius:16px;overflow:hidden;background:var(--blue-pale);aspect-ratio:4/3}'
    '.tp-hero-img img{width:100%;height:100%;object-fit:cover}'
    '.tp-hero-img .img-placeholder{height:100%}'
    '.tp-subtitle{color:var(--blue-main);font-weight:700;margin-bottom:8px}'
    '.tp-facts{list-style:none;margin:16px 0;padding:0;border:1px solid #e6edf3;border-radius:12px;background:#fff}'
    '.tp-facts li{display:flex;gap:14px;padding:10px 16px;border-bottom:1px solid #f0f4f7;line-height:1.6}'
    '.tp-facts li:last-child{border-bottom:none}'
    '.tp-facts strong{flex:0 0 72px;color:var(--blue-dark)}'
    '.tp-cta{display:flex;flex-wrap:wrap;gap:10px;margin-top:6px}'
    '.tp-body{display:grid;grid-template-columns:minmax(0,1fr) 320px;gap:32px;margin-top:26px}'
    '.tp-section{margin-bottom:30px}'
    '.tp-section h2{font-size:1.3rem;color:var(--blue-dark);font-weight:800;margin:0 0 12px;display:flex;align-items:center;gap:8px}'
    '.tp-section h2 i{color:var(--blue-main);font-size:1.05rem}'
    '.tp-section p{line-height:1.9;color:var(--text-dark);margin:0 0 10px}'
    '.tp-list{margin:0;padding-left:22px;line-height:1.9;color:var(--text-dark)}'
    '.tp-day{border-left:3px solid var(--blue-main);padding:4px 0 4px 18px;margin-bottom:18px}'
    '.tp-day-label{display:inline-block;background:var(--blue-main);color:#fff;font-size:.78rem;font-weight:800;padding:2px 10px;border-radius:20px;margin-bottom:6px}'
    '.tp-day h3{font-size:1.08rem;color:var(--blue-dark);margin:0 0 6px}'
    '.tp-price-table{width:100%;border-collapse:collapse;background:#fff;border:1px solid #e6edf3;border-radius:12px;overflow:hidden}'
    '.tp-price-table td{padding:10px 14px;border-bottom:1px solid #f0f4f7}'
    '.tp-price-table td:last-child{text-align:right;font-weight:800;color:#c0392b;white-space:nowrap}'
    '.tp-dates{display:flex;flex-wrap:wrap;gap:8px}'
    '.tp-date{background:#fff7df;border:1px solid #f0d99a;color:#8a6212;border-radius:20px;padding:4px 12px;font-size:.88rem}'
    '.tp-notice{background:#fff8ec;border-left:4px solid #e0a53a;border-radius:10px;padding:14px 18px}'
    '.tp-notice p:last-child{margin-bottom:0}'
    '.tp-gallery{display:grid;grid-template-columns:repeat(auto-fill,minmax(180px,1fr));gap:12px}'
    '.tp-gallery a{display:block;border-radius:10px;overflow:hidden;border:1px solid #e6edf3;background:#fff}'
    '.tp-gallery img{width:100%;display:block}'
    '.tp-side .tp-box{background:#fff;border:1px solid #e6edf3;border-radius:14px;padding:18px 20px;margin-bottom:18px}'
    '.tp-side h3{font-size:1.02rem;color:var(--blue-dark);margin:0 0 10px}'
    '.tp-side p{font-size:.92rem;line-height:1.75;color:var(--text-mid);margin:0 0 10px}'
    '.tp-tide{background:linear-gradient(135deg,#e8f6fc,#f3fbff)!important;border-color:#cfe8f5!important}'
    '.tp-contact td{padding:5px 0;vertical-align:top;font-size:.9rem;line-height:1.6}'
    '.tp-contact td:first-child{color:var(--text-light);white-space:nowrap;padding-right:12px}'
    '.tp-links a{display:block;padding:10px 0;border-bottom:1px dashed #dfe8ef;text-decoration:none;color:var(--blue-dark);font-weight:600;line-height:1.5}'
    '.tp-links a:last-child{border-bottom:none}'
    '.tp-links a:hover{color:var(--blue-main)}'
    '.tp-links small{display:block;font-weight:400;color:var(--text-light);margin-top:2px}'
    '.tp-bottom{margin-top:36px;background:var(--blue-pale);border-radius:16px;padding:26px;text-align:center}'
    '.tp-bottom h2{color:var(--blue-dark);margin:0 0 8px;font-size:1.3rem}'
    '.tp-bottom p{color:var(--text-mid);margin-bottom:12px}'
    '.tp-bottom .btn{margin:4px}'
    '.tp-empty{padding:40px;text-align:center;color:var(--text-mid)}'
    '@media (max-width:860px){.tp-hero,.tp-body{grid-template-columns:1fr}.tp-hero{gap:18px}}'
    '</style>'
)

_OUTLINE = 'style="color:var(--blue-main);border-color:var(--blue-main)"'


def _e(value):
    return _html.escape(str(value or ''))


def today_taipei():
    return datetime.now(TAIPEI).date()


def _url(path, lang='zh-tw', **params):
    params = {k: v for k, v in params.items() if v not in (None, '')}
    lang = normalize_lang(lang)
    if lang != 'zh-tw':
        params['lang'] = lang
    return path + (('?' + urlencode(params)) if params else '')


def tour_url(tour, lang='zh-tw'):
    return _url(f'/tours/{int(tour["id"])}', lang)


def _safe_image(url):
    """只放站內路徑或 https 圖片；其他（含 javascript:、http:）一律不輸出。"""
    url = str(url or '').strip()
    if url.startswith('/') and not url.startswith('//'):
        return url
    if url.startswith('https://'):
        return url
    return ''


def _modal(tour):
    md = tour.get('modal_data')
    return md if isinstance(md, dict) else {}


def _tabs(tour):
    tabs = tour.get('tabs')
    return [t for t in tabs if t in TAB_LABELS] if isinstance(tabs, list) else []


def primary_tab(tour):
    """麵包屑與「同類行程」用：優先海域／天數，其次才是「官方合作」。"""
    tabs = _tabs(tour)
    for t in tabs:
        if t != 'featured':
            return t
    return tabs[0] if tabs else None


def _placeholder(lang='zh-tw'):
    return ('<div class="img-placeholder" aria-hidden="true"><i class="fas fa-water"></i>'
            f'<span>{_e(_ui(lang)["brand"])}</span></div>')


def _image_html(tour, eager=False, lang='zh-tw'):
    src = _safe_image(tour.get('image_url'))
    if not src:
        return _placeholder(lang)
    loading = '' if eager else ' loading="lazy"'
    return f'<img src="{_e(src)}" alt="{_e(tour.get("title"))}"{loading} decoding="async"/>'


def booking_link(tour):
    """有對應預購產品才給預購連結。

    只認 tours.preorder_slug 與「小城故事」本身；不能用標題關鍵字（例如「追風」）
    去猜，別家旅行社的主題遊程標題裡也會出現同樣的字。
    """
    slug = str(tour.get('preorder_slug') or '').strip()
    if slug and re.fullmatch(r'[a-z0-9-]+', slug):
        return f'/preorder/{slug}'
    if str(tour.get('title') or '').startswith('小城故事'):
        return '/neihai-preorder.html'
    return None


def upcoming_dates(dates, today=None):
    """出發日期字串（例「6/12（五）－ 6/15（一）」）只保留還沒出發的。

    日期欄位沒有年份：比今天早但在半年內的視為已過；早超過半年的視為明年。
    開頭解析不出月/日的字串照原樣保留（例「每週六出發」）。
    """
    today = today or today_taipei()
    kept = []
    for raw in dates or []:
        text = str(raw or '').strip()
        if not text:
            continue
        m = re.match(r'^(\d{1,2})\s*/\s*(\d{1,2})', text)
        if m:
            try:
                d = date(today.year, int(m.group(1)), int(m.group(2)))
            except ValueError:
                kept.append(text)
                continue
            if d < today and (today - d).days <= 183:
                continue
        kept.append(text)
    return kept


def _tour_text(tour):
    md = _modal(tour)
    parts = [tour.get('title'), tour.get('description'), tour.get('suitable_for'),
             md.get('subtitle'), md.get('includes'), ' '.join(map(str, md.get('highlights') or []))]
    for d in md.get('days') or []:
        if isinstance(d, dict):
            parts += [d.get('title'), ' '.join(map(str, d.get('items') or []))]
    return ' '.join(str(p) for p in parts if p)


def related_posts(tour, posts, limit=4):
    """依行程文字裡的地名／活動詞，挑標題或標籤最相關的文章。"""
    text = _tour_text(tour)
    words = [w for w in _KEYWORDS if w in text]
    tab_words = [w for t in _tabs(tour) for w in _TAB_KEYWORDS.get(t, ())]
    scored = []
    for i, p in enumerate(posts):
        title = str(p.get('title') or '')
        tags = str(p.get('tags') or '')
        summary = str(p.get('summary') or '')
        score = 0
        for w in words:
            if w in _GENERIC_KEYWORDS:
                score += (w in title) + (w in tags)
            else:
                score += 3 * (w in title) + 2 * (w in tags) + (w in summary)
        for w in tab_words:
            score += (w in title) + (w in tags)
        if score >= _MIN_RELATED_SCORE:
            scored.append((-score, i, p))  # posts 已依發布時間新→舊排序，i 當同分排序
    scored.sort(key=lambda x: (x[0], x[1]))
    return [p for _, _, p in scored[:limit]]


_GUIDE_LABELS = {
    'zh-tw': ('澎湖三天兩夜行程規劃', '澎湖親子旅遊攻略', '2026 澎湖追風音樂燈光節攻略', '澎湖行程推薦比較'),
    'en': ('Penghu 3-day itinerary', 'Penghu family travel guide', '2026 Penghu Music & Light Festival guide', 'Compare Penghu itineraries'),
    'ja': ('澎湖3日間モデルコース', '澎湖ファミリー旅行ガイド', '2026澎湖音楽・ライトフェスティバルガイド', '澎湖ツアー比較'),
    'ko': ('펑후 3일 여행 일정', '펑후 가족 여행 가이드', '2026 펑후 음악·빛 축제 가이드', '펑후 여행 일정 비교'),
    'zh-cn': ('澎湖三天两夜行程规划', '澎湖亲子旅游攻略', '2026 澎湖追风音乐灯光节攻略', '澎湖行程推荐比较'),
}


def guide_links(tour, lang='zh-tw'):
    """站內主題攻略頁（pillar_pages.py）；相關文章不多的行程也有延伸閱讀。"""
    labels = _GUIDE_LABELS[normalize_lang(lang)]
    tabs = _tabs(tour)
    text = _tour_text(tour)
    links = []
    if any(t in PACKAGE_TABS for t in tabs):
        links.append(('/penghu-3days-itinerary', labels[0]))
    if '親子' in text:
        links.append(('/penghu-family-travel', labels[1]))
    if any(w in text for w in ('音樂節', '燈光節')):  # 不用「追風」：別家的風浪板行程也叫追風派對
        links.append(('/penghu-2026-festival-guide', labels[2]))
    links.append(('/penghu-itinerary-recommendations', labels[3]))
    return links[:3]


def sibling_tours(tour, tours, limit=3):
    tab = primary_tab(tour)
    if not tab:
        return []
    return [t for t in tours if t['id'] != tour['id'] and tab in _tabs(t)][:limit]


def _price_text(tour):
    return str(tour.get('price_display') or '').strip()


def _tour_card(tour, lang='zh-tw'):
    tags = ''.join(f'<span class="tp-tag">{_e(tab_label(t, lang))}</span>' for t in _tabs(tour))
    badge = f'<span class="tp-badge">{_e(tour["badge_text"])}</span>' if tour.get('badge_text') else ''
    meta = []
    if tour.get('duration'):
        meta.append(f'<span><i class="fas fa-clock"></i>{_e(tour["duration"])}</span>')
    if tour.get('suitable_for'):
        meta.append(f'<span><i class="fas fa-users"></i>{_e(tour["suitable_for"])}</span>')
    price = f'<div class="tp-price">{_e(_price_text(tour))}</div>' if _price_text(tour) else ''
    return (f'<a class="tp-card" href="{tour_url(tour, lang)}">'
            f'<div class="tp-card-img">{_image_html(tour, lang=lang)}{badge}</div>'
            f'<div class="tp-card-body"><h2>{_e(tour.get("title"))}</h2>'
            f'<p>{_e(tour.get("description"))}</p>'
            f'<div class="tp-meta">{"".join(meta)}</div>'
            f'<div class="tp-tags">{tags}</div>{price}</div></a>')


def filter_tours(tours, selected):
    if selected in FILTER_GROUPS:
        keys = FILTER_GROUPS[selected]
        return [t for t in tours if any(k in _tabs(t) for k in keys)]
    if selected in TAB_LABELS:
        return [t for t in tours if selected in _tabs(t)]
    return list(tours)


def normalize_filter(value):
    value = str(value or '').strip()
    return value if value in TAB_LABELS or value in FILTER_GROUPS else ''


def _chip(key, label, selected, count, lang='zh-tw'):
    href = _url('/tours', lang, type=key)
    cls = 'tp-chip active' if key == selected else 'tp-chip'
    current = ' aria-current="page"' if key == selected else ''
    return f'<a class="{cls}" href="{href}"{current}>{_e(label)} <small>({count})</small></a>'


def render_tours_index(tours, selected='', lang='zh-tw'):
    """回傳 (title, description, canonical, body, head_extra)。"""
    lang = normalize_lang(lang)
    ui = _ui(lang)
    tours = [localized_tour(t, lang) for t in tours]
    selected = normalize_filter(selected)
    shown = filter_tours(tours, selected)

    def row(label, keys, group):
        chips = _chip(group, filter_label(group, lang), selected, len(filter_tours(tours, group)), lang)
        for k in keys:
            n = len(filter_tours(tours, k))
            if n:
                chips += _chip(k, tab_label(k, lang), selected, n, lang)
        return f'<div class="tp-filter-row"><span class="tp-filter-label">{label}</span>{chips}</div>'

    filters = (f'<nav class="tp-filters" aria-label="{_e(ui["filters"])}">'
               f'<div class="tp-filter-row"><span class="tp-filter-label">{_e(ui["all"])}</span>{_chip("", ui["all_tours"], selected, len(tours), lang)}</div>'
               + row(ui['package_by_days'], PACKAGE_TABS, 'package')
               + row(ui['single_by_area'], SEA_TABS, 'single')
               + '</nav>')

    label = (tab_label(selected, lang) if selected in TAB_LABELS else filter_label(selected, lang) if selected in FILTER_LABELS else '')
    heading = {
        '': ui['index_heading'], 'package': ui['package_heading'], 'single': ui['single_heading'],
        'north-sea': ui['north_heading'], 'east-sea': ui['east_heading'],
        'south-sea': ui['south_heading'], 'main-island': ui['main_heading'],
    }.get(selected) or ui['dynamic_heading'].format(label=label)
    grid = (f'<div class="tp-grid">{"".join(_tour_card(t, lang) for t in shown)}</div>' if shown
            else f'<p class="tp-empty">{_e(ui["empty"])}<a href="{_url("/tours", lang)}">{_e(ui["see_all"])}</a>。</p>')
    tours_href = _url('/tours', lang)
    body = (f'<div class="tp-wrap"><div class="tp-crumb"><a href="{_url("/", lang)}">{_e(ui["home"])}</a> › '
            + (f'<a href="{tours_href}">{_e(ui["overview"])}</a> › {_e(label)}' if label else _e(ui['overview']))
            + f'</div><h1>{_e(heading)}</h1><p class="tp-lead">{_e(ui["lead"])}</p>{filters}'
            f'<p class="tp-count">{_e(ui["count"].format(n=len(shown)))}</p>{grid}'
            + _bottom_cta(ui['index_cta'], lang=lang)
            + '</div>')

    canonical = f'{SITE}{_url("/tours", lang, type=selected)}'
    title = f'{heading}｜{ui["brand"]}'
    if lang == 'en':
        desc = f'{heading}: {len(shown)} tours. {ui["index_meta"]}'
    else:
        desc = f'{heading}，{len(shown)}。{ui["index_meta"]}'
    crumbs = [(ui['home'], f'{SITE}{_url("/", lang)}'), (ui['overview'], f'{SITE}{tours_href}')]
    if label:
        crumbs.append((label, canonical))
    item_list = {
        "@context": "https://schema.org", "@type": "ItemList", "name": heading,
        "itemListElement": [
            {"@type": "ListItem", "position": i + 1, "url": f'{SITE}{tour_url(t, lang)}', "name": str(t.get('title') or '')}
            for i, t in enumerate(shown)
        ],
    }
    head_extra = TOUR_STYLE + _ld(item_list) + _ld(_breadcrumb(crumbs))
    return title, desc, canonical, body, head_extra


def _bottom_cta(lead, contact_href='/#contact', lang='zh-tw'):
    ui = _ui(lang)
    return (f'<div class="tp-bottom"><h2>{_e(ui["cta_heading"])}</h2>'
            f'<p>{_e(lead)}</p>'
            f'<a href="{LINE_URL}" target="_blank" rel="noopener noreferrer" class="btn btn-primary"><i class="fab fa-line"></i> LINE @phbay2018</a> '
            f'<a href="{contact_href}" class="btn btn-outline" {_OUTLINE}><i class="fas fa-comment-dots"></i> {_e(ui["form"])}</a> '
            f'<a href="tel:06-9271288" class="btn btn-outline" {_OUTLINE}><i class="fas fa-phone"></i> 06-9271288</a>'
            '</div>')


def _ld(obj):
    return '<script type="application/ld+json">' + json.dumps(obj, ensure_ascii=False).replace('</', '<\\/') + '</script>'


def _breadcrumb(trail):
    return {
        "@context": "https://schema.org", "@type": "BreadcrumbList",
        "itemListElement": [{"@type": "ListItem", "position": i + 1, "name": n, "item": u}
                            for i, (n, u) in enumerate(trail)],
    }


def _section(icon, title, inner):
    return f'<section class="tp-section"><h2><i class="fas {icon}"></i> {_e(title)}</h2>{inner}</section>'


def _paragraphs(text):
    parts = [p.strip() for p in re.split(r'\n+', str(text or '')) if p.strip()]
    return ''.join(f'<p>{_e(p)}</p>' for p in parts)


def render_tour_page(tour, posts=(), siblings=(), today=None, lang='zh-tw'):
    """回傳 (title, description, canonical, body, head_extra, og_image)。"""
    lang = normalize_lang(lang)
    ui = _ui(lang)
    source_tour = tour
    tour = localized_tour(tour, lang)
    siblings = [localized_tour(s, lang) for s in siblings]
    md = _modal(tour)
    title = str(tour.get('title') or '')
    tid = int(tour['id'])
    canonical = f'{SITE}{tour_url(tour, lang)}'
    contact_href = _url('/', lang, tour_id=tid) + '#contact'
    tab = primary_tab(tour)
    # Booking mapping is based on the canonical Chinese record/preorder_slug;
    # translated titles must not break the existing Neihai special case.
    booking = booking_link(source_tour)
    if booking and lang != 'zh-tw':
        booking = _url(booking, lang)

    # ── 開頭：照片＋重點資訊＋行動按鈕 ──
    facts = []
    if tour.get('duration'):
        facts.append((ui['days'], tour['duration']))
    if tour.get('suitable_for'):
        facts.append((ui['suitable'], tour['suitable_for']))
    if _price_text(tour):
        facts.append((ui['price'], _price_text(tour)))
    if _tabs(tour):
        facts.append((ui['category'], '、'.join(tab_label(t, lang) for t in _tabs(tour))))
    facts_html = ('<ul class="tp-facts">' + ''.join(f'<li><strong>{_e(k)}</strong><span>{_e(v)}</span></li>' for k, v in facts)
                  + '</ul>') if facts else ''
    cta = '<div class="tp-cta">'
    if booking:
        cta += f'<a href="{booking}" class="btn btn-primary"><i class="fas fa-ticket"></i> {_e(ui["book"])}</a>'
    cta += (f'<a href="{contact_href}" class="btn {"btn-outline" if booking else "btn-primary"}" {_OUTLINE if booking else ""}>'
            f'<i class="fas fa-comment-dots"></i> {_e(ui["ask"])}</a>'
            f'<a href="{LINE_URL}" target="_blank" rel="noopener noreferrer" class="btn btn-outline" {_OUTLINE}><i class="fab fa-line"></i> {_e(ui["line"])}</a>'
            '</div>')
    badge = f'<span class="tp-tag">{_e(tour["badge_text"])}</span>' if tour.get('badge_text') else ''
    subtitle = f'<p class="tp-subtitle">{_e(md["subtitle"])}</p>' if md.get('subtitle') else ''
    crumb = f'<div class="tp-crumb"><a href="{_url("/", lang)}">{_e(ui["home"])}</a> › <a href="{_url("/tours", lang)}">{_e(ui["overview"])}</a>'
    if tab:
        crumb += f' › <a href="{_url("/tours", lang, type=tab)}">{_e(tab_label(tab, lang))}</a>'
    crumb += '</div>'
    hero = (f'{crumb}<div class="tp-hero"><div class="tp-hero-img">{_image_html(tour, eager=True, lang=lang)}</div>'
            f'<div>{badge}<h1>{_e(title)}</h1>{subtitle}<p class="tp-lead">{_e(tour.get("description"))}</p>'
            f'{facts_html}{cta}</div></div>')

    # ── 主要內容 ──
    main = ''
    prices = [p for p in (tour.get('prices') or []) if isinstance(p, dict)]
    if prices:
        rows = ''.join(f'<tr><td>{_e(p.get("label", p.get("from")))}</td><td>{_e(p.get("value", p.get("price")))}</td></tr>'
                       for p in prices)
        main += _section('fa-tag', ui['fee'], f'<table class="tp-price-table">{rows}</table>')

    raw_dates = [d for d in (md.get('dates') or []) if str(d or '').strip()]
    dates = upcoming_dates(raw_dates, today)
    if dates:
        chips = ''.join(f'<span class="tp-date">{_e(d)}</span>' for d in dates)
        main += _section('fa-calendar-alt', ui['dates'], f'<div class="tp-dates">{chips}</div>'
                         f'<p style="margin-top:10px;font-size:.9rem;color:var(--text-light)">{_e(ui["availability"])}</p>')
    elif raw_dates:
        main += _section('fa-calendar-alt', ui['dates'],
                         f'<p>{_e(ui["past_dates"])}<a href="{contact_href}">{_e(ui["online"])}</a>{_e(ui["or_line"])}</p>')

    days = [d for d in (md.get('days') or []) if isinstance(d, dict)]
    highlights = [h for h in (md.get('highlights') or []) if str(h or '').strip()]
    if days:
        blocks = ''
        for i, d in enumerate(days):
            items = ''.join(f'<li>{_e(x)}</li>' for x in (d.get('items') or []) if str(x or '').strip())
            blocks += (f'<div class="tp-day"><span class="tp-day-label">{_e(d.get("label") or f"DAY {i + 1}")}</span>'
                       f'<h3>{_e(d.get("title"))}</h3>' + (f'<ul class="tp-list">{items}</ul>' if items else '') + '</div>')
        main += _section('fa-route', ui['daily'], blocks)
        if highlights:
            main += _section('fa-star', ui['highlights'], '<ul class="tp-list">' + ''.join(f'<li>{_e(h)}</li>' for h in highlights) + '</ul>')
    elif highlights:
        main += _section('fa-route', ui['content'], '<ul class="tp-list">' + ''.join(f'<li>{_e(h)}</li>' for h in highlights) + '</ul>')

    if md.get('includes'):
        main += _section('fa-circle-check', ui['includes'], _paragraphs(md['includes']))
    if tour.get('suitable_for'):
        main += _section('fa-users', ui['who'], f'<p>{_e(tour["suitable_for"])}</p>')
    notices = _paragraphs(md.get('notice')) + _paragraphs(md.get('notes'))
    if notices:
        main += _section('fa-triangle-exclamation', ui['notes'], f'<div class="tp-notice">{notices}</div>')

    photos = [s for s in (_safe_image(p) for p in (md.get('posters') or [])) if s]
    if photos:
        thumbs = ''.join(f'<a href="{_e(p)}" target="_blank" rel="noopener noreferrer">'
                         f'<img src="{_e(p)}" alt="{_e(title)}｜{_e(ui["photo_alt"].format(n=i + 1))}" loading="lazy" decoding="async"/></a>'
                         for i, p in enumerate(photos))
        main += _section('fa-images', ui['photos'], f'<div class="tp-gallery">{thumbs}</div>')

    # ── 側欄：潮汐、主辦單位、相關文章、同類行程 ──
    side = ''
    tide_related = any(w in _tour_text(source_tour) for w in _TIDE_WORDS)
    tide_text = ui['tide_related'] if tide_related else ui['tide_general']
    side += (f'<div class="tp-box tp-tide"><h3><i class="fas fa-water"></i> {_e(ui["tide_title"])}</h3><p>{_e(tide_text)}</p>'
             f'<a href="{_url("/tides", lang)}" class="btn btn-outline" {_OUTLINE}>{_e(ui["tide_link"])}</a></div>')

    c = md.get('contact') if isinstance(md.get('contact'), dict) else {}
    c_rows = ''
    for key, label in (('agency', ui['agency']), ('partner', ui['partner']), ('license', ui['license'])):
        if c.get(key):
            c_rows += f'<tr><td>{label}</td><td>{_e(c[key])}</td></tr>'
    if c_rows:
        side += (f'<div class="tp-box"><h3>{_e(ui["provider"])}</h3><table class="tp-contact">{c_rows}</table>'
                 f'<p style="margin:10px 0 0">{_e(ui["assist"])}</p></div>')

    links = ''.join(f'<a href="{_url("/blog/" + str(p["slug"]), lang)}">{_e(p.get("title"))}</a>' for p in posts)
    links += ''.join(f'<a href="{_url(href, lang)}">{_e(name)}<small>{_e(ui["related_guide"])}</small></a>' for href, name in guide_links(source_tour, lang))
    side += f'<div class="tp-box"><h3>{_e(ui["related"])}</h3><div class="tp-links">{links}</div></div>'
    if siblings:
        links = ''.join(f'<a href="{tour_url(s, lang)}">{_e(s.get("title"))}'
                        + (f'<small>{_e(s.get("duration"))}{"｜" + _e(_price_text(s)) if _price_text(s) else ""}</small>' if s.get('duration') or _price_text(s) else '')
                        + '</a>' for s in siblings)
        more = _url('/tours', lang, type=tab)
        side += (f'<div class="tp-box"><h3>{_e(tab_label(tab, lang) if tab else "")} {_e(ui["other"])}</h3><div class="tp-links">{links}</div>'
                 f'<p style="margin:10px 0 0"><a href="{more}" style="color:var(--blue-main)">{_e(ui["see_all_arrow"])}</a></p></div>')

    body = (f'<div class="tp-wrap">{hero}<div class="tp-body"><div>{main}</div><aside class="tp-side">{side}</aside></div>'
            + _bottom_cta(ui['detail_cta'], contact_href, lang)
            + '</div>')

    image = _safe_image(tour.get('image_url')) or (photos[0] if photos else '')
    og_image = (SITE + image if image.startswith('/') else image) or None
    desc = str(tour.get('description') or '').strip()
    extra = '｜'.join(x for x in (str(tour.get('duration') or ''), _price_text(tour)) if x)
    meta_desc = (f'{title}：{desc}' + (f'（{extra}）' if extra else ''))[:155]

    trip = {
        "@context": "https://schema.org", "@type": "TouristTrip", "name": title,
        "description": desc or title, "url": canonical,
        "provider": {"@type": "TravelAgency", "@id": f"{SITE}/#organization", "name": ui['brand'], "url": f"{SITE}/"},
    }
    if og_image:
        trip["image"] = og_image
    if tour.get('suitable_for'):
        trip["touristType"] = str(tour['suitable_for'])
    if days:
        trip["itinerary"] = {"@type": "ItemList", "itemListElement": [
            {"@type": "ListItem", "position": i + 1, "name": ' '.join(x for x in (str(d.get('label') or ''), str(d.get('title') or '')) if x)}
            for i, d in enumerate(days)]}
    crumbs = [(ui['home'], f'{SITE}{_url("/", lang)}'), (ui['overview'], f'{SITE}{_url("/tours", lang)}')]
    if tab:
        crumbs.append((tab_label(tab, lang), f'{SITE}{_url("/tours", lang, type=tab)}'))
    crumbs.append((title, canonical))
    head_extra = TOUR_STYLE + _ld(trip) + _ld(_breadcrumb(crumbs))
    return f'{title}｜{ui["overview"]} - {ui["brand"]}', meta_desc, canonical, body, head_extra, og_image
