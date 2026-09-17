# -*- coding: utf-8 -*-
"""行程獨立頁面：/tours（總覽，可依天數或海域篩選）與 /tours/<id>（單一行程）。

資料全部來自 tours 資料表（後台 /admin 維護），本模組只負責渲染，不新增任何
價格、日期或行程細節；欄位沒填的區塊就不顯示。app.py 負責查資料庫與共用外殼。
所有資料庫文字一律跳脫後輸出。
"""

import html as _html
import json
import re
from datetime import date, datetime, timedelta, timezone

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


def tour_url(tour):
    return f'/tours/{int(tour["id"])}'


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


def _placeholder():
    return ('<div class="img-placeholder" aria-hidden="true"><i class="fas fa-water"></i>'
            '<span>潮旅國際旅行社</span></div>')


def _image_html(tour, eager=False):
    src = _safe_image(tour.get('image_url'))
    if not src:
        return _placeholder()
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


def guide_links(tour):
    """站內主題攻略頁（pillar_pages.py）；相關文章不多的行程也有延伸閱讀。"""
    tabs = _tabs(tour)
    text = _tour_text(tour)
    links = []
    if any(t in PACKAGE_TABS for t in tabs):
        links.append(('/penghu-3days-itinerary', '澎湖三天兩夜行程規劃'))
    if '親子' in text:
        links.append(('/penghu-family-travel', '澎湖親子旅遊攻略'))
    if any(w in text for w in ('音樂節', '燈光節')):  # 不用「追風」：別家的風浪板行程也叫追風派對
        links.append(('/penghu-2026-festival-guide', '2026 澎湖追風音樂燈光節攻略'))
    links.append(('/penghu-itinerary-recommendations', '澎湖行程推薦比較'))
    return links[:3]


def sibling_tours(tour, tours, limit=3):
    tab = primary_tab(tour)
    if not tab:
        return []
    return [t for t in tours if t['id'] != tour['id'] and tab in _tabs(t)][:limit]


def _price_text(tour):
    return str(tour.get('price_display') or '').strip()


def _tour_card(tour):
    tags = ''.join(f'<span class="tp-tag">{_e(TAB_LABELS[t])}</span>' for t in _tabs(tour))
    badge = f'<span class="tp-badge">{_e(tour["badge_text"])}</span>' if tour.get('badge_text') else ''
    meta = []
    if tour.get('duration'):
        meta.append(f'<span><i class="fas fa-clock"></i>{_e(tour["duration"])}</span>')
    if tour.get('suitable_for'):
        meta.append(f'<span><i class="fas fa-users"></i>{_e(tour["suitable_for"])}</span>')
    price = f'<div class="tp-price">{_e(_price_text(tour))}</div>' if _price_text(tour) else ''
    return (f'<a class="tp-card" href="{tour_url(tour)}">'
            f'<div class="tp-card-img">{_image_html(tour)}{badge}</div>'
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


def _chip(key, label, selected, count):
    href = f'/tours?type={key}' if key else '/tours'
    cls = 'tp-chip active' if key == selected else 'tp-chip'
    current = ' aria-current="page"' if key == selected else ''
    return f'<a class="{cls}" href="{href}"{current}>{_e(label)} <small>({count})</small></a>'


def render_tours_index(tours, selected=''):
    """回傳 (title, description, canonical, body, head_extra)。"""
    selected = normalize_filter(selected)
    shown = filter_tours(tours, selected)

    def row(label, keys, group):
        chips = _chip(group, FILTER_LABELS[group], selected, len(filter_tours(tours, group)))
        for k in keys:
            n = len(filter_tours(tours, k))
            if n:
                chips += _chip(k, TAB_LABELS[k], selected, n)
        return f'<div class="tp-filter-row"><span class="tp-filter-label">{label}</span>{chips}</div>'

    filters = ('<nav class="tp-filters" aria-label="行程篩選">'
               f'<div class="tp-filter-row"><span class="tp-filter-label">全部</span>{_chip("", "全部行程", selected, len(tours))}</div>'
               + row('套裝・依天數', PACKAGE_TABS, 'package')
               + row('單日・依海域', SEA_TABS, 'single')
               + '</nav>')

    label = TAB_LABELS.get(selected) or FILTER_LABELS.get(selected) or ''
    heading = {
        '': '澎湖行程總覽', 'package': '澎湖套裝行程', 'single': '澎湖單日行程',
        'north-sea': '澎湖北海一日遊行程', 'east-sea': '澎湖東海一日遊行程',
        'south-sea': '澎湖南海一日遊行程', 'main-island': '澎湖本島海上活動與一日遊',
    }.get(selected) or f'澎湖{label}行程'
    lead = ('潮旅國際旅行社整理的澎湖行程：套裝行程依天數分類，單日跳島與海上活動依海域分類。'
            '點進每個行程可看行程安排、費用包含、注意事項與適合對象；想確認出發日與名額，歡迎 LINE 或線上諮詢。')
    grid = (f'<div class="tp-grid">{"".join(_tour_card(t) for t in shown)}</div>' if shown
            else '<p class="tp-empty">這個分類目前沒有上架中的行程，<a href="/tours">看全部行程</a>。</p>')
    body = (f'<div class="tp-wrap"><div class="tp-crumb"><a href="/">首頁</a> › '
            + (f'<a href="/tours">行程總覽</a> › {_e(label)}' if label else '行程總覽')
            + f'</div><h1>{_e(heading)}</h1><p class="tp-lead">{lead}</p>{filters}'
            f'<p class="tp-count">共 {len(shown)} 個行程</p>{grid}'
            + _bottom_cta('不確定哪個行程適合？告訴我們天數、同行者與想玩的海域，在地人幫你排。')
            + '</div>')

    canonical = f'{SITE}/tours' + (f'?type={selected}' if selected else '')
    title = f'{heading}｜潮旅國際旅行社'
    desc = (f'潮旅國際旅行社{label}行程共 {len(shown)} 個，' if label else f'潮旅國際旅行社澎湖行程總覽共 {len(shown)} 個，') \
        + '含套裝行程（兩天一夜到四天三夜）與北海、東海、南海、本島一日遊，可看行程安排、費用包含與注意事項。'
    crumbs = [('首頁', f'{SITE}/'), ('行程總覽', f'{SITE}/tours')]
    if label:
        crumbs.append((label, canonical))
    item_list = {
        "@context": "https://schema.org", "@type": "ItemList", "name": heading,
        "itemListElement": [
            {"@type": "ListItem", "position": i + 1, "url": f'{SITE}{tour_url(t)}', "name": str(t.get('title') or '')}
            for i, t in enumerate(shown)
        ],
    }
    head_extra = TOUR_STYLE + _ld(item_list) + _ld(_breadcrumb(crumbs))
    return title, desc, canonical, body, head_extra


def _bottom_cta(lead, contact_href='/#contact'):
    return ('<div class="tp-bottom"><h2>想把行程交給在地人排？</h2>'
            f'<p>{_e(lead)}</p>'
            f'<a href="{LINE_URL}" target="_blank" rel="noopener noreferrer" class="btn btn-primary"><i class="fab fa-line"></i> LINE @phbay2018</a> '
            f'<a href="{contact_href}" class="btn btn-outline" {_OUTLINE}><i class="fas fa-comment-dots"></i> 線上諮詢表單</a> '
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


def render_tour_page(tour, posts=(), siblings=(), today=None):
    """回傳 (title, description, canonical, body, head_extra, og_image)。"""
    md = _modal(tour)
    title = str(tour.get('title') or '')
    tid = int(tour['id'])
    canonical = f'{SITE}/tours/{tid}'
    contact_href = f'/?tour_id={tid}#contact'
    tab = primary_tab(tour)
    booking = booking_link(tour)

    # ── 開頭：照片＋重點資訊＋行動按鈕 ──
    facts = []
    if tour.get('duration'):
        facts.append(('天數', tour['duration']))
    if tour.get('suitable_for'):
        facts.append(('適合', tour['suitable_for']))
    if _price_text(tour):
        facts.append(('價格', _price_text(tour)))
    if _tabs(tour):
        facts.append(('分類', '、'.join(TAB_LABELS[t] for t in _tabs(tour))))
    facts_html = ('<ul class="tp-facts">' + ''.join(f'<li><strong>{_e(k)}</strong><span>{_e(v)}</span></li>' for k, v in facts)
                  + '</ul>') if facts else ''
    cta = '<div class="tp-cta">'
    if booking:
        cta += f'<a href="{booking}" class="btn btn-primary"><i class="fas fa-ticket"></i> 前往預購訂位</a>'
    cta += (f'<a href="{contact_href}" class="btn {"btn-outline" if booking else "btn-primary"}" {_OUTLINE if booking else ""}>'
            '<i class="fas fa-comment-dots"></i> 詢問這個行程</a>'
            f'<a href="{LINE_URL}" target="_blank" rel="noopener noreferrer" class="btn btn-outline" {_OUTLINE}><i class="fab fa-line"></i> LINE 諮詢</a>'
            '</div>')
    badge = f'<span class="tp-tag">{_e(tour["badge_text"])}</span>' if tour.get('badge_text') else ''
    subtitle = f'<p class="tp-subtitle">{_e(md["subtitle"])}</p>' if md.get('subtitle') else ''
    crumb = '<div class="tp-crumb"><a href="/">首頁</a> › <a href="/tours">行程總覽</a>'
    if tab:
        crumb += f' › <a href="/tours?type={tab}">{_e(TAB_LABELS[tab])}</a>'
    crumb += '</div>'
    hero = (f'{crumb}<div class="tp-hero"><div class="tp-hero-img">{_image_html(tour, eager=True)}</div>'
            f'<div>{badge}<h1>{_e(title)}</h1>{subtitle}<p class="tp-lead">{_e(tour.get("description"))}</p>'
            f'{facts_html}{cta}</div></div>')

    # ── 主要內容 ──
    main = ''
    prices = [p for p in (tour.get('prices') or []) if isinstance(p, dict)]
    if prices:
        rows = ''.join(f'<tr><td>{_e(p.get("label", p.get("from")))}</td><td>{_e(p.get("value", p.get("price")))}</td></tr>'
                       for p in prices)
        main += _section('fa-tag', '費用', f'<table class="tp-price-table">{rows}</table>')

    raw_dates = [d for d in (md.get('dates') or []) if str(d or '').strip()]
    dates = upcoming_dates(raw_dates, today)
    if dates:
        chips = ''.join(f'<span class="tp-date">{_e(d)}</span>' for d in dates)
        main += _section('fa-calendar-alt', '出發日期', f'<div class="tp-dates">{chips}</div>'
                         '<p style="margin-top:10px;font-size:.9rem;color:var(--text-light)">實際名額與是否成團以報名確認為準。</p>')
    elif raw_dates:
        main += _section('fa-calendar-alt', '出發日期',
                         f'<p>本行程公告的梯次都已出發。想詢問下一梯或包團日期，請<a href="{contact_href}">線上諮詢</a>或 LINE 聯絡我們。</p>')

    days = [d for d in (md.get('days') or []) if isinstance(d, dict)]
    highlights = [h for h in (md.get('highlights') or []) if str(h or '').strip()]
    if days:
        blocks = ''
        for i, d in enumerate(days):
            items = ''.join(f'<li>{_e(x)}</li>' for x in (d.get('items') or []) if str(x or '').strip())
            blocks += (f'<div class="tp-day"><span class="tp-day-label">{_e(d.get("label") or f"DAY {i + 1}")}</span>'
                       f'<h3>{_e(d.get("title"))}</h3>' + (f'<ul class="tp-list">{items}</ul>' if items else '') + '</div>')
        main += _section('fa-route', '每日行程', blocks)
        if highlights:
            main += _section('fa-star', '行程亮點', '<ul class="tp-list">' + ''.join(f'<li>{_e(h)}</li>' for h in highlights) + '</ul>')
    elif highlights:
        main += _section('fa-route', '行程內容', '<ul class="tp-list">' + ''.join(f'<li>{_e(h)}</li>' for h in highlights) + '</ul>')

    if md.get('includes'):
        main += _section('fa-circle-check', '費用包含', _paragraphs(md['includes']))
    if tour.get('suitable_for'):
        main += _section('fa-users', '適合誰', f'<p>{_e(tour["suitable_for"])}</p>')
    notices = _paragraphs(md.get('notice')) + _paragraphs(md.get('notes'))
    if notices:
        main += _section('fa-triangle-exclamation', '注意事項', f'<div class="tp-notice">{notices}</div>')

    photos = [s for s in (_safe_image(p) for p in (md.get('posters') or [])) if s]
    if photos:
        thumbs = ''.join(f'<a href="{_e(p)}" target="_blank" rel="noopener noreferrer">'
                         f'<img src="{_e(p)}" alt="{_e(title)}｜行程照片 {i + 1}" loading="lazy" decoding="async"/></a>'
                         for i, p in enumerate(photos))
        main += _section('fa-images', '行程照片與海報', f'<div class="tp-gallery">{thumbs}</div>')

    # ── 側欄：潮汐、主辦單位、相關文章、同類行程 ──
    side = ''
    tide_related = any(w in _tour_text(tour) for w in _TIDE_WORDS)
    tide_text = ('這個行程的活動時間跟潮汐有關（例如潮間帶、浮潛），實際報到時間會依當天潮汐調整。出發前可先查退潮時段。'
                 if tide_related else
                 '澎湖海上與海邊行程都會受潮汐、風浪影響。排行程前先看看出發日的漲退潮時間，玩得更順。')
    side += (f'<div class="tp-box tp-tide"><h3><i class="fas fa-water"></i> 出發前查潮汐</h3><p>{tide_text}</p>'
             f'<a href="/tides" class="btn btn-outline" {_OUTLINE}>澎湖潮汐查詢</a></div>')

    c = md.get('contact') if isinstance(md.get('contact'), dict) else {}
    c_rows = ''
    for key, label in (('agency', '主辦單位'), ('partner', '合作夥伴'), ('license', '證號')):
        if c.get(key):
            c_rows += f'<tr><td>{label}</td><td>{_e(c[key])}</td></tr>'
    if c_rows:
        side += (f'<div class="tp-box"><h3>行程提供單位</h3><table class="tp-contact">{c_rows}</table>'
                 '<p style="margin:10px 0 0">潮旅國際旅行社可協助諮詢與報名。</p></div>')

    links = ''.join(f'<a href="/blog/{_e(p["slug"])}">{_e(p.get("title"))}</a>' for p in posts)
    links += ''.join(f'<a href="{href}">{_e(name)}<small>延伸攻略</small></a>' for href, name in guide_links(tour))
    side += f'<div class="tp-box"><h3>相關文章與攻略</h3><div class="tp-links">{links}</div></div>'
    if siblings:
        links = ''.join(f'<a href="{tour_url(s)}">{_e(s.get("title"))}'
                        + (f'<small>{_e(s.get("duration"))}{"｜" + _e(_price_text(s)) if _price_text(s) else ""}</small>' if s.get('duration') or _price_text(s) else '')
                        + '</a>' for s in siblings)
        more = f'/tours?type={tab}' if tab else '/tours'
        side += (f'<div class="tp-box"><h3>{_e(TAB_LABELS.get(tab, ""))}其他行程</h3><div class="tp-links">{links}</div>'
                 f'<p style="margin:10px 0 0"><a href="{more}" style="color:var(--blue-main)">看全部 →</a></p></div>')

    body = (f'<div class="tp-wrap">{hero}<div class="tp-body"><div>{main}</div><aside class="tp-side">{side}</aside></div>'
            + _bottom_cta('想確認出發日、名額或客製調整？留下需求，專人回覆。', contact_href)
            + '</div>')

    image = _safe_image(tour.get('image_url')) or (photos[0] if photos else '')
    og_image = (SITE + image if image.startswith('/') else image) or None
    desc = str(tour.get('description') or '').strip()
    extra = '｜'.join(x for x in (str(tour.get('duration') or ''), _price_text(tour)) if x)
    meta_desc = (f'{title}：{desc}' + (f'（{extra}）' if extra else ''))[:155]

    trip = {
        "@context": "https://schema.org", "@type": "TouristTrip", "name": title,
        "description": desc or title, "url": canonical,
        "provider": {"@type": "TravelAgency", "@id": f"{SITE}/#organization", "name": "潮旅國際旅行社", "url": f"{SITE}/"},
    }
    if og_image:
        trip["image"] = og_image
    if tour.get('suitable_for'):
        trip["touristType"] = str(tour['suitable_for'])
    if days:
        trip["itinerary"] = {"@type": "ItemList", "itemListElement": [
            {"@type": "ListItem", "position": i + 1, "name": ' '.join(x for x in (str(d.get('label') or ''), str(d.get('title') or '')) if x)}
            for i, d in enumerate(days)]}
    crumbs = [('首頁', f'{SITE}/'), ('行程總覽', f'{SITE}/tours')]
    if tab:
        crumbs.append((TAB_LABELS[tab], f'{SITE}/tours?type={tab}'))
    crumbs.append((title, canonical))
    head_extra = TOUR_STYLE + _ld(trip) + _ld(_breadcrumb(crumbs))
    return f'{title}｜澎湖行程 - 潮旅國際旅行社', meta_desc, canonical, body, head_extra, og_image
