# -*- coding: utf-8 -*-
"""Pillar pages（主題攻略頁）內容與渲染。

四頁：/penghu-3days-itinerary、/penghu-family-travel、/penghu-food-guide、
/penghu-2026-festival-guide。內容集中本模組，app.py 只負責路由與共用外殼。
事實來源限既有站內內容（llms.txt 快答、已發布文章、官方活動資訊），
勿新增未經確認的價格、名額、時刻或活動細節。
"""

import html as _html
import json

SITE = 'https://www.phbay.info'

# 共用樣式（inline 注入 head，不動 style.css、免升 ?v= 版本）
PILLAR_STYLE = (
    '<style>'
    '.pp-wrap{max-width:920px;margin:0 auto;padding:36px 20px 60px}'
    '.pp-wrap h1{font-size:clamp(1.6rem,4vw,2.2rem);color:var(--blue-dark);font-weight:800;line-height:1.35;margin-bottom:10px}'
    '.pp-kicker{color:var(--blue-main);font-weight:800;letter-spacing:.08em;font-size:.85rem;margin-bottom:8px}'
    '.pp-intro{color:var(--text-mid);line-height:1.9;font-size:1.02rem;margin-bottom:18px}'
    '.pp-cta-row{display:flex;flex-wrap:wrap;gap:10px;margin:14px 0 30px}'
    '.pp-wrap h2{font-size:1.4rem;color:var(--blue-dark);font-weight:800;margin:34px 0 14px}'
    '.pp-wrap h3{font-size:1.12rem;color:var(--blue-main);font-weight:700;margin:20px 0 8px}'
    '.pp-wrap p{line-height:1.9;color:var(--text-dark);margin-bottom:14px}'
    '.pp-wrap ul{margin:0 0 16px 22px;line-height:1.9;color:var(--text-dark)}'
    '.pp-wrap a{color:var(--blue-main);text-decoration:underline}'
    '.pp-conclusion{background:var(--blue-pale);border-left:4px solid var(--blue-main);border-radius:10px;padding:18px 22px;margin:0 0 8px}'
    '.pp-conclusion p{margin:0;line-height:1.9}'
    '.pp-table-scroll{overflow-x:auto;margin-bottom:8px}'
    '.pp-table{width:100%;border-collapse:collapse;font-size:.95rem;min-width:520px}'
    '.pp-table th{background:var(--blue-pale);color:var(--blue-dark);font-weight:800;text-align:left;padding:10px 14px;white-space:nowrap}'
    '.pp-table td{border-bottom:1px solid #eef2f5;padding:10px 14px;line-height:1.7;color:var(--text-dark)}'
    '.pp-cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:16px;margin-bottom:8px}'
    '.pp-card{background:#fff;border:1px solid #e6edf3;border-radius:14px;padding:18px 20px;box-shadow:0 2px 10px rgba(0,0,0,.05)}'
    '.pp-card h3{margin:0 0 8px}'
    '.pp-card .pp-tag{display:inline-block;background:var(--blue-pale);color:var(--blue-main);font-size:.78rem;font-weight:800;padding:2px 10px;border-radius:20px;margin-bottom:8px}'
    '.pp-card p{font-size:.95rem;margin-bottom:0;color:var(--text-mid)}'
    '.pp-links{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:10px 22px;margin-bottom:8px}'
    '.pp-links a{display:block;padding:9px 0;border-bottom:1px dashed #dfe8ef;text-decoration:none;color:var(--blue-dark);font-weight:600}'
    '.pp-links a:hover{color:var(--blue-main)}'
    '.pp-faq details{background:#fff;border:1px solid #e6edf3;border-radius:12px;margin-bottom:10px;padding:0 18px}'
    '.pp-faq summary{cursor:pointer;font-weight:700;color:var(--blue-dark);padding:14px 0;list-style-position:inside}'
    '.pp-faq details[open] summary{border-bottom:1px solid #eef2f5}'
    '.pp-faq details p{padding:12px 0 16px;color:var(--text-mid);line-height:1.9;margin:0}'
    '.pp-bottom-cta{margin-top:40px;background:var(--blue-pale);border-radius:16px;padding:28px;text-align:center}'
    '.pp-bottom-cta h2{margin:0 0 8px}'
    '.pp-bottom-cta p{color:var(--text-mid)}'
    '.pp-bottom-cta a.btn{margin:4px}'
    '</style>'
)

_LINE_URL = 'https://line.me/R/ti/p/@phbay2018'


def _cta_row(extra=''):
    return ('<div class="pp-cta-row">'
            f'<a href="{_LINE_URL}" target="_blank" rel="noopener noreferrer" class="btn btn-primary"><i class="fab fa-line"></i> LINE 諮詢 @phbay2018</a>'
            '<a href="/#tours" class="btn btn-outline" style="color:var(--blue-main);border-color:var(--blue-main)"><i class="fas fa-map-marked-alt"></i> 看推薦行程</a>'
            f'{extra}</div>')


def _bottom_cta(lead):
    return ('<div class="pp-bottom-cta"><h2>想把行程交給在地人排？</h2>'
            f'<p>{lead}</p>'
            f'<a href="{_LINE_URL}" target="_blank" rel="noopener noreferrer" class="btn btn-primary"><i class="fab fa-line"></i> LINE @phbay2018</a> '
            '<a href="tel:06-9271288" class="btn btn-outline" style="color:var(--blue-main);border-color:var(--blue-main)"><i class="fas fa-phone"></i> 電話 06-9271288</a> '
            '<a href="/#contact" class="btn btn-outline" style="color:var(--blue-main);border-color:var(--blue-main)"><i class="fas fa-comment-dots"></i> 線上諮詢表單</a> '
            '<a href="/#quiz" class="btn btn-outline" style="color:var(--blue-main);border-color:var(--blue-main)"><i class="fas fa-compass"></i> 30 秒行程診斷</a>'
            '</div>')


def _decision_table(rows):
    body = ''.join(f'<tr><th>{_html.escape(k)}</th><td>{v}</td></tr>' for k, v in rows)
    return f'<div class="pp-table-scroll"><table class="pp-table">{body}</table></div>'


def _plan_cards(plans):
    cards = ''.join(
        f'<div class="pp-card"><span class="pp-tag">{_html.escape(tag)}</span>'
        f'<h3>{_html.escape(title)}</h3><p>{desc}</p></div>'
        for tag, title, desc in plans)
    return f'<div class="pp-cards">{cards}</div>'


def _article_links(items):
    links = ''.join(f'<a href="/blog/{slug}">{_html.escape(text)}</a>' for slug, text in items)
    return f'<div class="pp-links">{links}</div>'


def _faq_html(faq):
    qa = ''.join(f'<details><summary>{_html.escape(q)}</summary><p>{_html.escape(a)}</p></details>'
                 for q, a in faq)
    return f'<section class="pp-faq"><h2>常見問題</h2>{qa}</section>'


def _faq_ld(faq):
    return {"@context": "https://schema.org", "@type": "FAQPage",
            "mainEntity": [{"@type": "Question", "name": q,
                            "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in faq]}


def _breadcrumb_ld(trail):
    return {"@context": "https://schema.org", "@type": "BreadcrumbList",
            "itemListElement": [{"@type": "ListItem", "position": i + 1,
                                 "name": name, "item": url}
                                for i, (name, url) in enumerate(trail)]}


def _webpage_ld(slug, title, desc):
    return {"@context": "https://schema.org", "@type": "WebPage",
            "name": title, "description": desc, "url": f"{SITE}/{slug}",
            "inLanguage": "zh-TW", "dateModified": "2026-07-19",
            "publisher": {"@type": "Organization", "name": "潮旅國際旅行社",
                          "url": f"{SITE}/"}}


# ═══════════════════════ 1. 三天兩夜 ═══════════════════════

def _page_3days():
    slug = 'penghu-3days-itinerary'
    title = '澎湖三天兩夜行程規劃｜第一次來澎湖怎麼排｜潮旅國際旅行社'
    desc = ('第一次來澎湖三天兩夜怎麼排？在地旅行社整理本島、北環、跳島的取捨原則、'
            '親子與長輩的節奏建議、季節與預算怎麼抓，附範例動線與常見問題。')
    conclusion = ('第一次來澎湖，三天兩夜建議以馬公本島、北環與一個跳島或海上體驗為主，'
                  '不要把南海、北海、望安、七美全部塞進同一趟。4–9 月天氣最穩定，'
                  '玩水黃金期是 6–8 月。若同行有小孩或長輩，行程節奏比景點數量更重要；'
                  '想省去排程與訂船的功夫，可以直接找在地旅行社把交通、住宿與行程一次排好。')
    table = _decision_table([
        ('適合誰', '第一次來澎湖、想一次看到海景與離島的旅人'),
        ('建議天數', '3 天 2 夜最熱門；4 天 3 夜更從容'),
        ('適合季節', '4–9 月；玩水以 6–8 月最佳'),
        ('預算感', '套裝行程（含交通、住宿、行程）約 NT$6,000 起／人，依出發地、季節、住宿等級調整，以報價為準'),
        ('推薦玩法', '北環一日＋馬公市區半日＋跳島或海上體驗一日'),
        ('可搭配頁面', '<a href="/#quiz">30 秒行程診斷</a>、<a href="/neihai-preorder.html">內海巡禮船遊預購</a>、<a href="/tides">潮汐查詢</a>'),
    ])
    personas = (
        '<h3>第一次來澎湖</h3><p>把北環（跨海大橋、通梁古榕、西嶼）排成完整一天，市區留半天逛'
        '天后宮與中央老街，另一天交給跳島或海上體驗，就是最不容易出錯的骨架。</p>'
        '<h3>親子家庭</h3><p>一天最多排三個點，把潮間帶、船遊這類體驗放在孩子精神好的上午；'
        '細節可看 <a href="/penghu-family-travel">澎湖親子旅遊攻略</a>。</p>'
        '<h3>情侶／朋友</h3><p>把傍晚留給西嶼的燈塔與海景，晚上回馬公吃海鮮、逛老街；'
        '夏天可加夜釣小管。</p>'
        '<h3>長輩同行</h3><p>選飛機進出（航程約 35–50 分鐘）、行程避免長時間曝曬與趕船班，'
        '船遊選內海航線較平穩。</p>'
        '<h3>不想太趕的人</h3><p>直接放棄「全部都要」，選一個海域玩深；望安、七美各自都值得一整天。</p>'
    )
    plans = _plan_cards([
        ('輕鬆型', '本島慢遊＋內海船遊',
         '北環一天慢慢開、市區老街半天，加一段<a href="/neihai-preorder.html">小城故事・內海巡禮</a>船遊，不趕船班也有海上行程。'),
        ('經典型', '北環＋市區＋跳島',
         'Day1 北環動線、Day2 跳島（七美或吉貝擇一）、Day3 市區與伴手禮，是最多人選的三天兩夜骨架。'),
        ('深度型', '望安或七美整日',
         '把一整天留給望安（綠蠵龜、花宅古厝）或七美（雙心石滬），配合<a href="/tides">潮汐</a>安排潮間帶，玩法更深。'),
    ])
    days = (
        '<h2>範例動線：三天兩夜怎麼走</h2>'
        '<h3>Day 1｜北環一日</h3>'
        '<p>通梁古榕 → 跨海大橋 → 小門鯨魚洞 → 大菓葉柱狀玄武岩 → 二崁聚落 → 西嶼西臺，'
        '傍晚收在漁翁島燈塔看海。逆時針或順時針都可以，重點是別把北環拆成兩個半天。</p>'
        '<h3>Day 2｜跳島或海上體驗</h3>'
        '<p>七美雙心石滬、望安綠蠵龜擇一整日；不想搭長程船班，可改內海巡禮＋奎壁山潮間帶'
        '（出發前先查<a href="/tides">潮汐</a>）。</p>'
        '<h3>Day 3｜馬公市區半日</h3>'
        '<p>澎湖天后宮與中央老街散步、採買伴手禮後前往機場。若遇雨，'
        '澎湖生活博物館是市區最穩的備案。</p>'
    )
    links = _article_links([
        ('2026-06-24-penghu-great-bridge-north-ring-guide', '澎湖跨海大橋不只拍照：北環最有風聲的停留點'),
        ('2026-07-08-penghu-tongliang-banyan-north-ring-guide', '通梁古榕怎麼玩：把北環放慢的一站綠蔭'),
        ('2026-07-06-penghu-xiaomen-whale-cave-geology-guide', '小門鯨魚洞散步指南'),
        ('2026-07-13-daguoye-basalt-columns-guide', '大菓葉柱狀玄武岩怎麼看'),
        ('2026-06-30-penghu-erkan-chen-house-walk-guide', '二崁聚落慢走指南'),
        ('2026-07-01-yuwengdao-lighthouse-siyu-guide', '漁翁島燈塔散步指南：把西嶼海角留給傍晚'),
        ('2026-06-22-kueibishan-tidal-walk-guide', '奎壁山潮間帶怎麼玩'),
        ('2026-06-29-penghu-tianhou-temple-magang-walk-guide', '澎湖天后宮與馬公老街半日散步'),
        ('2026-07-15-penghu-living-museum-rainy-day-guide', '澎湖雨天備案：生活博物館散步指南'),
        ('2026-07-16-penghu-airport-bus-budget-meme-guide', '澎湖自由行交通與省錢動線'),
    ])
    faq = [
        ('澎湖三天兩夜夠玩嗎？',
         '夠玩，但要取捨。三天兩夜適合「本島＋一個跳島或海上體驗」的組合；想把望安、七美、吉貝都走完，建議直接排四天三夜，不然每天都在趕船班。'),
        ('第一次來澎湖，三天兩夜怎麼排最順？',
         '常見骨架是：第一天北環一日（跨海大橋、通梁古榕、西嶼一帶）、第二天跳島或海上體驗、第三天馬公市區與伴手禮。景點之間車程短，重點是同一天的點盡量排在同一個方向。'),
        ('澎湖幾月去最好？',
         '4–9 月天氣最穩定、海水溫暖，玩水黃金期是 6–8 月。冬天（11–2 月）東北季風強、體感偏冷，多數水上活動停駛，屬於非旺季。'),
        ('三天兩夜預算大概多少？',
         '潮旅套裝行程（含交通、住宿、行程）約 NT$6,000 起／人，實際依出發地、季節與住宿等級調整，以報價為準。自由行則主要看機票與住宿的季節價差。'),
        ('帶小孩或長輩，三天兩夜要注意什麼？',
         '節奏比景點數量重要：一天最多三個點、避免中午長時間曝曬、船程選短的。搭飛機進出（約 35–50 分鐘）比搭船輕鬆，暈船體質務必先備暈船藥。'),
        ('望安、七美、吉貝怎麼選？',
         '想看綠蠵龜與古厝聚落選望安，想看雙心石滬選七美，想玩水上活動選吉貝。三個都想去的話，三天兩夜塞不下，建議挑一個玩整天。'),
        ('什麼情況適合找旅行社排？',
         '人數多（家族、員工旅遊）、帶長輩小孩、或不想自己訂船班與住宿時，交給在地旅行社最省心。潮旅由在地嚮導規劃，兩人即可成行，可以先用 LINE @phbay2018 免費諮詢。'),
    ]
    body = (
        '<div class="pp-wrap">'
        '<div class="pp-kicker">澎湖行程規劃</div>'
        '<h1>澎湖三天兩夜行程規劃｜第一次來澎湖怎麼排</h1>'
        '<p class="pp-intro">三天兩夜是澎湖最熱門的玩法，但南海北海、望安七美不可能一次走完。'
        '這頁由澎湖在地旅行社整理：怎麼取捨海域、怎麼配天數與季節、預算怎麼抓，'
        '並附上可以直接照走的範例動線。</p>'
        + _cta_row()
        + '<section class="pp-conclusion"><h2 style="margin:0 0 10px">先講結論</h2><p>'
        + conclusion + '</p></section>'
        + '<h2>快速決策表</h2>' + table
        + '<h2>依同行對象怎麼排</h2>' + personas
        + '<h2>三種玩法組合</h2>' + plans
        + days
        + '<h2>延伸閱讀：把每一站看得更細</h2>' + links
        + _faq_html(faq)
        + _bottom_cta('把想去的點傳給我們，在地嚮導幫你排成順路又不趕的三天兩夜。')
        + '</div>')
    trip_ld = {
        "@context": "https://schema.org", "@type": "TouristTrip",
        "name": "澎湖三天兩夜行程規劃",
        "description": "馬公本島、北環與跳島的三天兩夜行程建議，由澎湖在地旅行社潮旅國際整理。",
        "url": f"{SITE}/{slug}",
        "touristType": ["第一次到澎湖的旅客", "親子家庭", "情侶朋友", "長輩同行"],
        "itinerary": {"@type": "ItemList", "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "Day 1 北環一日：跨海大橋、通梁古榕、西嶼"},
            {"@type": "ListItem", "position": 2, "name": "Day 2 跳島或海上體驗：七美、望安或內海巡禮"},
            {"@type": "ListItem", "position": 3, "name": "Day 3 馬公市區：天后宮、中央老街與伴手禮"},
        ]},
        "provider": {"@type": "TravelAgency", "name": "潮旅國際旅行社", "url": f"{SITE}/"},
    }
    return dict(slug=slug, title=title, desc=desc, body=body,
                extra_ld=[trip_ld], faq=faq, breadcrumb_name='澎湖三天兩夜行程規劃')


# ═══════════════════════ 2. 親子 ═══════════════════════

def _page_family():
    slug = 'penghu-family-travel'
    title = '澎湖親子旅遊攻略｜適合小孩的海島、生態與輕鬆行程｜潮旅國際旅行社'
    desc = ('澎湖適合帶小孩嗎？在地旅行社整理親子行程怎麼排：潮間帶、DIY、淺水浮潛、'
            '內海船遊的搭配方式，太熱或下雨的備案，以及不同年齡層的注意事項。')
    conclusion = ('澎湖很適合親子旅遊：飛機航程約 35–50 分鐘不易暈、景點之間車程短，'
                  '潮間帶、DIY、淺水浮潛與夜釣小管都是孩子容易上手的體驗。'
                  '排行程的原則是「一天最多三個點、體驗放上午、午後留彈性」，'
                  '夏天記得把正中午留在室內或海上，別硬曬。')
    table = _decision_table([
        ('適合誰', '帶學齡前到國小孩子的家庭、三代同堂出遊'),
        ('建議天數', '3 天 2 夜起；三代同堂建議 4 天 3 夜'),
        ('適合季節', '4–9 月；6–8 月玩水最好但要防曬'),
        ('預算感', '套裝行程約 NT$6,000 起／人，兒童依年齡與內容另計，以報價為準'),
        ('推薦玩法', '潮間帶生態＋內海船遊＋DIY，搭配一天輕鬆北環'),
        ('可搭配頁面', '<a href="/penghu-3days-itinerary">三天兩夜行程規劃</a>、<a href="/neihai-preorder.html">內海巡禮船遊</a>、<a href="/tides">潮汐查詢</a>'),
    ])
    personas = (
        '<h3>學齡前（0–6 歲）</h3><p>以「玩沙、看魚、搭船」為主：淺灘玩水、內海船遊航程短又平穩，'
        '午睡時間留在住宿點，晚上不排行程。</p>'
        '<h3>國小孩子</h3><p>潮間帶生態、DIY 與淺水浮潛接受度最高；夜釣小管是很多孩子整趟最記得的行程。'
        '出發前先查<a href="/tides">潮汐</a>，退潮時段才能玩潮間帶。</p>'
        '<h3>三代同堂</h3><p>長輩與小孩的節奏其實很像：避免長船程與曝曬、一天三個點以內。'
        '北環開車動線（通梁古榕、西嶼西臺）對全家都友善。</p>'
    )
    plans = _plan_cards([
        ('輕鬆型', '市區＋內海船遊',
         '住馬公市區，白天<a href="/neihai-preorder.html">內海巡禮</a>船遊＋老街散步，行程鬆、移動少，適合第一次帶幼兒。'),
        ('經典型', '潮間帶＋北環',
         '一天潮間帶生態＋DIY，一天北環親子動線（通梁古榕、西嶼西臺、鯨魚洞），晚上加夜釣小管。'),
        ('深度型', '生態慢旅',
         '加一天望安，看綠蠵龜保育與花宅古厝，用慢節奏讓孩子真的認識海島。'),
    ])
    tips = (
        '<h2>太熱、下雨怎麼辦</h2>'
        '<p>夏天正中午避免戶外行程，把體驗排在上午與傍晚；遇到下雨，'
        '澎湖生活博物館是市區最好的親子備案，DIY 課程也多半在室內。'
        '風大的日子船班可能調整，行程保留彈性、出發前確認即可。</p>'
        '<h2>親子行程常見的踩雷點</h2>'
        '<ul><li>一天塞五個點：孩子體力撐不住，大人也累。</li>'
        '<li>忽略潮汐：潮間帶與摩西分海都要看<a href="/tides">潮汐時間</a>，不是隨到隨玩。</li>'
        '<li>長程船班連著排：暈船一次，後面行程全毀，離島挑一個就好。</li>'
        '<li>只排大人想看的景點：穿插玩水、DIY 這類孩子主場的活動，全家都開心。</li></ul>'
    )
    links = _article_links([
        ('2026-06-22-kueibishan-tidal-walk-guide', '奎壁山潮間帶怎麼玩：不只等分海'),
        ('2026-07-08-penghu-tongliang-banyan-north-ring-guide', '通梁古榕：北環路線的親子綠蔭站'),
        ('2026-07-14-xiyu-western-fort-guide', '西嶼西臺：好走好逛的海防古堡'),
        ('2026-07-15-penghu-living-museum-rainy-day-guide', '澎湖生活博物館：雨天親子備案'),
        ('2026-06-22-wangan-slow-travel-guide', '望安慢旅：綠蠵龜與花宅古厝'),
        ('2026-07-06-penghu-xiaomen-whale-cave-geology-guide', '小門鯨魚洞：把玄武岩講成故事給孩子聽'),
        ('2026-06-21-penghu-cactus-dessert-guide', '仙人掌甜點：孩子最愛的澎湖限定冰品'),
    ])
    faq = [
        ('小孩幾歲適合去澎湖？',
         '各年齡都可以，差別在玩法。學齡前以玩沙、短程船遊為主；國小以上就能玩潮間帶、淺水浮潛與夜釣小管。飛機航程約 35–50 分鐘，比長途開車輕鬆得多。'),
        ('澎湖哪些活動適合親子？',
         '潮間帶生態、DIY 體驗、淺水浮潛、內海船遊與夜釣小管最受歡迎，皆有教練或導覽帶領。水上活動配安全裝備，不會游泳的大人小孩都能參加。'),
        ('帶小孩去澎湖，行程怎麼排比較不累？',
         '一天最多三個點，體驗類排上午、午後留彈性，晚上除了夜釣小管以外少排行程。景點間車程多在 30 分鐘內，善用這點把同方向的點排在同一天。'),
        ('夏天會不會太熱？下雨怎麼辦？',
         '6–8 月很曬，正中午建議留在室內、海上或住宿點，戶外行程放上午與傍晚。下雨可改澎湖生活博物館、室內 DIY；風大時船班可能調整，保留行程彈性即可。'),
        ('親子去澎湖要玩幾天？',
         '3 天 2 夜是低標，能玩到潮間帶＋一段船遊＋北環；帶幼兒或三代同堂建議 4 天 3 夜，每天行程更鬆。'),
        ('內海巡禮適合帶小孩搭嗎？',
         '適合。內海航線平穩、航程短，6 人成行、最多 13 人的小船不擁擠，時段固定好安排。詳情與訂位見內海巡禮預購頁。'),
        ('親子行程可以請旅行社客製嗎？',
         '可以。潮旅主打親子友善行程，會依孩子年齡調整節奏與內容，兩人即可成行；用 LINE @phbay2018 說明孩子年齡與天數，就能拿到建議行程。'),
    ]
    body = (
        '<div class="pp-wrap">'
        '<div class="pp-kicker">澎湖親子旅遊</div>'
        '<h1>澎湖親子旅遊攻略｜適合小孩的海島、生態與輕鬆行程</h1>'
        '<p class="pp-intro">澎湖是對小孩非常友善的海島：航程短、車程短、體驗多。'
        '這頁整理不同年齡層的玩法、太熱與下雨的備案、以及親子行程最常見的踩雷點，'
        '照著排就能玩得輕鬆。</p>'
        + _cta_row()
        + '<section class="pp-conclusion"><h2 style="margin:0 0 10px">先講結論</h2><p>'
        + conclusion + '</p></section>'
        + '<h2>快速決策表</h2>' + table
        + '<h2>依孩子年齡怎麼玩</h2>' + personas
        + '<h2>三種親子玩法組合</h2>' + plans
        + tips
        + '<h2>延伸閱讀</h2>' + links
        + _faq_html(faq)
        + _bottom_cta('告訴我們孩子的年齡與想玩的天數，幫你排一趟大人小孩都盡興的澎湖。')
        + '</div>')
    trip_ld = {
        "@context": "https://schema.org", "@type": "TouristTrip",
        "name": "澎湖親子旅遊攻略",
        "description": "潮間帶、DIY、淺水浮潛與內海船遊的澎湖親子行程建議，由在地旅行社潮旅國際整理。",
        "url": f"{SITE}/{slug}",
        "touristType": ["親子家庭", "三代同堂"],
        "provider": {"@type": "TravelAgency", "name": "潮旅國際旅行社", "url": f"{SITE}/"},
    }
    return dict(slug=slug, title=title, desc=desc, body=body,
                extra_ld=[trip_ld], faq=faq, breadcrumb_name='澎湖親子旅遊攻略')


# ═══════════════════════ 3. 美食 ═══════════════════════

_FOOD_SECTIONS = [
    ('早餐與早午餐', [
        ('2026-06-20-penghu-breakfast-ordering-guide', '澎湖早餐怎麼選：魚湯、鹹粥到燒餅'),
        ('2026-07-18-penghu-fresh-fish-noodle-soup-guide', '澎湖鮮魚麵線：不趕路的清湯早午餐'),
    ]),
    ('小吃與午後點心', [
        ('2026-07-03-penghu-oyster-fritter-eating-guide', '蚵嗲與海味炸物：下午嘴饞的在地節奏'),
        ('2026-07-12-penghu-fried-wahoo-soup-guide', '土魠魚羹與炸土魠魚：酥香午餐'),
        ('2026-07-11-penghu-seaweed-fish-ball-soup-guide', '海菜魚丸湯：一碗海風'),
        ('2026-07-05-penghu-siwei-noodles-guide', '西衛麵線：曬進海風的手作滋味'),
    ]),
    ('海鮮與家常味', [
        ('2026-06-27-penghu-seafood-ordering-guide', '澎湖海鮮怎麼點：石斑、牡蠣到海菜'),
        ('2026-06-19-penghu-small-squid-tasting-guide', '澎湖小管怎麼吃：清燙、炭烤到小管麵線'),
        ('2026-07-17-penghu-seaweed-vermicelli-guide', '紫菜炒冬粉：潮間帶香氣上桌'),
        ('2026-06-26-penghu-pumpkin-rice-noodles-guide', '金瓜米粉：一盤看懂海島家常'),
    ]),
    ('甜點與飲品', [
        ('2026-06-21-penghu-cactus-dessert-guide', '仙人掌甜點：冰品、果醬到伴手禮'),
        ('2026-06-28-penghu-fongru-tea-summer-guide', '風茹茶：夏天海島的清爽飲品'),
    ]),
    ('伴手禮', [
        ('2026-07-10-penghu-brown-sugar-cake-guide', '黑糖糕怎麼買才不踩雷'),
        ('2026-06-26-penghu-salty-biscuit-souvenir-guide', '澎湖鹹餅：酥香伴手禮選味指南'),
        ('2026-07-04-penghu-cuttlefish-ball-guide', '花枝丸：從伴手禮到熱湯小點'),
    ]),
]


def _page_food():
    slug = 'penghu-food-guide'
    title = '澎湖美食地圖｜早餐、小吃、海鮮與在地家常味｜潮旅國際旅行社'
    desc = ('澎湖必吃有哪些？在地旅行社把早餐、小吃、海鮮、甜點與伴手禮整理成一張美食地圖，'
            '教你按時段排進行程，不用為了排隊犧牲旅行節奏。')
    conclusion = ('澎湖美食的精華是「海味＋家常」：早餐吃魚湯鹹粥，午後吃蚵嗲、土魠魚羹這類小吃，'
                  '晚餐留給現流海鮮，伴手禮帶黑糖糕、鹹餅與花枝丸。'
                  '排法上建議「跟著行程順路吃」而不是特地跨區排隊——'
                  '馬公市區集中了大多數選擇，北環與離島則把胃口留給在地小店。')
    table = _decision_table([
        ('必吃清單', '小管／小卷、仙人掌冰、黑糖糕、現流海鮮、花生酥、鹹餅'),
        ('早餐', '魚湯、鹹粥、燒餅；睡晚了就改鮮魚麵線當早午餐'),
        ('午後點心', '蚵嗲、炸粿、仙人掌冰、風茹茶'),
        ('晚餐', '現流海鮮（石斑、牡蠣、小管）、金瓜米粉、紫菜炒冬粉'),
        ('伴手禮', '黑糖糕、鹹餅、花枝丸、仙人掌果醬、花生酥'),
        ('可搭配頁面', '<a href="/penghu-3days-itinerary">三天兩夜行程規劃</a>、<a href="/#quiz">30 秒行程診斷</a>'),
    ])
    how = (
        '<h2>怎麼把美食排進行程</h2>'
        '<p>澎湖的餐期很「在地」：許多小吃店下午就收、海鮮餐廳晚餐時段最熱門。'
        '建議把美食當成行程的補給站——北環那天早餐在市區吃飽再出發，'
        '回程順路帶伴手禮；跳島日在碼頭附近解決午餐；晚餐才是正式的海鮮主場。</p>'
        '<p>熱門名店排隊人多時，別為了一份小吃犧牲一個景點：'
        '同類型的在地小店往往一樣好吃，我們的文章裡都有「怎麼點、何時去」的建議。</p>'
    )
    sections_html = ''
    for sec_title, items in _FOOD_SECTIONS:
        sections_html += f'<h3>{_html.escape(sec_title)}</h3>' + _article_links(items)
    faq = [
        ('澎湖必吃美食有哪些？',
         '最具代表性的是小管／小卷、仙人掌冰、黑糖糕、現流海鮮、花生酥與鹹餅。海鮮以當日現流為賣點，仙人掌與風茹茶則是澎湖限定的風味。'),
        ('澎湖早餐吃什麼？',
         '在地早餐以魚湯、鹹粥、燒餅為主，起得晚可以改吃鮮魚麵線當早午餐。多數早餐店集中在馬公市區，出發北環或跳島前先吃飽最順。'),
        ('澎湖海鮮怎麼點才內行？',
         '先問當日現流是什麼，再決定做法：石斑清蒸、牡蠣鮮烤、小管清燙或做小管麵線。人少就單點兩三道配家常菜，比硬上大桌合菜實在。'),
        ('伴手禮買什麼？何時買？',
         '黑糖糕、鹹餅、花枝丸、仙人掌果醬與花生酥最經典。建議回程前一天在馬公市區採買，黑糖糕保存期限短，別第一天就買。'),
        ('澎湖美食要排隊嗎？怎麼避開人潮？',
         '旺季熱門店會排隊，但同類型的在地小店品質往往不輸名店。錯開正餐尖峰、跟著行程順路吃，不要特地跨區排隊，旅行節奏比打卡重要。'),
        ('吃素或不吃海鮮有選擇嗎？',
         '有，金瓜米粉、紫菜炒冬粉等家常料理多數店家可調整內容，早餐的燒餅豆漿也單純。訂餐廳時先講需求，或請旅行社在行程裡先安排好。'),
        ('可以請旅行社把美食排進行程嗎？',
         '可以。潮旅的行程由在地嚮導規劃，會把餐期、順路與店家營業時間一起考慮進去，兩人即可成行；用 LINE @phbay2018 告訴我們想吃什麼即可。'),
    ]
    body = (
        '<div class="pp-wrap">'
        '<div class="pp-kicker">澎湖美食</div>'
        '<h1>澎湖美食地圖｜早餐、小吃、海鮮與在地家常味</h1>'
        '<p class="pp-intro">從清晨的魚湯鹹粥到晚上的現流海鮮，澎湖的味道跟著海走。'
        '這頁把我們寫過的美食文章整理成一張地圖：按時段吃、順路吃，'
        '不用為了排隊犧牲行程。</p>'
        + _cta_row()
        + '<section class="pp-conclusion"><h2 style="margin:0 0 10px">先講結論</h2><p>'
        + conclusion + '</p></section>'
        + '<h2>快速決策表</h2>' + table
        + how
        + '<h2>美食文章總整理</h2>' + sections_html
        + _faq_html(faq)
        + _bottom_cta('想吃什麼直接說，在地嚮導幫你把餐期與行程排在同一條順路上。')
        + '</div>')
    item_ld = {
        "@context": "https://schema.org", "@type": "ItemList",
        "name": "澎湖美食地圖：文章總整理",
        "url": f"{SITE}/{slug}",
        "itemListElement": [
            {"@type": "ListItem", "position": i + 1, "name": text,
             "url": f"{SITE}/blog/{s}"}
            for i, (s, text) in enumerate(
                [it for _t, items in _FOOD_SECTIONS for it in items])
        ],
    }
    return dict(slug=slug, title=title, desc=desc, body=body,
                extra_ld=[item_ld], faq=faq, breadcrumb_name='澎湖美食地圖')


# ═══════════════════════ 4. 音樂節 ═══════════════════════

def _page_festival():
    slug = 'penghu-2026-festival-guide'
    title = '2026 澎湖追風音樂燈光節攻略｜日期、交通、住宿與行程安排｜潮旅國際旅行社'
    desc = ('2026 澎湖追風音樂燈光節在觀音亭園區，燈光展演 9/12–10/11。'
            '官方合作旅行社整理：白天行程怎麼排、住宿怎麼選、交通怎麼銜接，'
            '以及三天兩夜主題行程預購資訊。')
    conclusion = ('2026 澎湖追風音樂燈光節在馬公的觀音亭園區舉行，燈光展演 9/12–10/11，'
                  '藝人展演集中在 9/12、9/13、9/19、9/26、10/3。'
                  '最順的玩法是「白天玩澎湖、傍晚回觀音亭」：住宿選馬公市區走路就能到會場，'
                  '白天排北環或市區行程，晚上看展演。潮旅是官方合作旅行社，'
                  '有搭配活動的三天兩夜主題行程可線上預購。')
    table = _decision_table([
        ('活動地點', '澎湖觀音亭園區（馬公市區，近市中心）'),
        ('燈光展演', '2026/9/12 – 10/11'),
        ('藝人展演', '2026/9/12、9/13、9/19、9/26、10/3'),
        ('住宿建議', '馬公市區優先，步行即可往返會場，看完展演不用開夜車'),
        ('交通建議', '9–10 月為活動檔期，機票與住宿建議提早訂；藝人展演日人潮較多'),
        ('主題行程', '<a href="/preorder/festival">三天兩夜主題行程預購</a>（花路追風之旅、追風海龜療癒行，兩人成行）'),
    ])
    day_plan = (
        '<h2>晚上看展演，白天怎麼排</h2>'
        '<h3>白天：把澎湖玩起來</h3>'
        '<p>觀音亭就在馬公市區，白天完全可以正常跑行程：北環一日（跨海大橋、通梁古榕、'
        '西嶼、大菓葉）或市區半日（天后宮、中央老街）都能在傍晚前回到會場。'
        '詳細動線可參考<a href="/penghu-3days-itinerary">澎湖三天兩夜行程規劃</a>。</p>'
        '<h3>傍晚：提早到觀音亭</h3>'
        '<p>觀音亭本身就是看夕陽的熱門地點，建議傍晚提早到，先看夕陽再接晚上的燈光展演；'
        '藝人展演日人潮較多，晚餐可提早或改外帶。</p>'
        '<h3>雨備與彈性</h3>'
        '<p>9–10 月偶有風雨，白天行程保留彈性，市區的'
        '<a href="/blog/2026-07-15-penghu-living-museum-rainy-day-guide">澎湖生活博物館</a>是最近的雨天備案；'
        '活動當日資訊以主辦單位公告為準。</p>'
        '<h2>住宿與交通怎麼銜接</h2>'
        '<ul><li><strong>住宿：</strong>優先選馬公市區，走路往返觀音亭最省事；'
        '活動檔期住宿較熱門，確定日期就先訂。</li>'
        '<li><strong>機票：</strong>9–10 月週末與藝人展演日需求高，建議提早開票；'
        '出發地與航班選擇可參考<a href="/blog/2026-07-16-penghu-airport-bus-budget-meme-guide">澎湖交通動線整理</a>。</li>'
        '<li><strong>租車／接駁：</strong>白天行程用租車或包車，晚上回市區後步行即可，'
        '不用擔心會場周邊停車。</li></ul>'
        '<h2>誰適合直接預購主題行程</h2>'
        '<p>不想自己搶住宿、排動線的人。潮旅是 2026 澎湖追風音樂燈光節官方合作旅行社，'
        '主題行程（花路追風之旅、追風海龜療癒行）把機加酒、白天行程與看展演的節奏一次排好，'
        '兩人成行，可直接在<a href="/preorder/festival">預購頁</a>下訂，專人會與你確認細節。</p>'
    )
    links = _article_links([
        ('2026-06-29-penghu-tianhou-temple-magang-walk-guide', '天后宮與中央老街：會場附近的半日散步'),
        ('2026-06-24-penghu-great-bridge-north-ring-guide', '跨海大橋北環動線：白天行程首選'),
        ('2026-07-01-yuwengdao-lighthouse-siyu-guide', '漁翁島燈塔：把西嶼海角留給傍晚'),
        ('2026-07-15-penghu-living-museum-rainy-day-guide', '生活博物館：市區雨天備案'),
        ('2026-07-16-penghu-airport-bus-budget-meme-guide', '澎湖交通與省錢動線整理'),
        ('2026-07-07-penghu-fenggui-cave-sound-guide', '風櫃洞：澎南半日的海蝕洞'),
    ])
    faq = [
        ('2026 澎湖追風音樂燈光節的日期與地點？',
         '地點在馬公的澎湖觀音亭園區。燈光展演從 2026 年 9 月 12 日到 10 月 11 日，藝人展演日為 9/12、9/13、9/19、9/26 與 10/3。當日細節以主辦單位公告為準。'),
        ('看音樂節，白天可以排行程嗎？',
         '可以，而且建議這樣排。觀音亭在馬公市區，白天跑北環或市區行程都來得及在傍晚回到會場，等於白天玩澎湖、晚上看展演，一趟旅行兩種玩法。'),
        ('住宿要選哪一區？',
         '首選馬公市區：步行就能往返觀音亭，看完晚上的展演不用開夜車回住宿點。活動檔期住宿需求高，確定日期後建議盡早預訂。'),
        ('機票和交通要注意什麼？',
         '9–10 月的週末與藝人展演日航班需求高，機票建議提早開票。島上移動以租車或包車最方便，晚上會場周邊人多，住市區就能步行前往。'),
        ('潮旅的音樂節主題行程是什麼？',
         '潮旅是 2026 澎湖追風音樂燈光節官方合作旅行社，推出三天兩夜主題行程（花路追風之旅、追風海龜療癒行），把住宿、白天行程與看展演的節奏一次排好，兩人成行，可在預購頁線上下訂。'),
        ('主題行程適合誰？',
         '適合不想自己搶住宿、排動線的人，以及想順便把澎湖玩完整的旅客。預購後專人會與你確認日期與細節，再完成後續安排。'),
        ('怎麼諮詢或預訂？',
         '線上預購走 /preorder/festival 預購頁；想先問問題可加官方 LINE @phbay2018 或電話 06-9271288（週一至週五 08:30–17:30）。'),
    ]
    body = (
        '<div class="pp-wrap">'
        '<div class="pp-kicker">2026 澎湖追風音樂燈光節</div>'
        '<h1>2026 澎湖追風音樂燈光節攻略｜日期、交通、住宿與行程安排</h1>'
        '<p class="pp-intro">追風音樂燈光節是澎湖 9–10 月的重頭戲：觀音亭園區的燈光展演加上'
        '多場藝人演出。這頁由官方合作旅行社整理白天行程、住宿與交通的安排方式，'
        '讓你晚上看展演、白天把澎湖玩完整。</p>'
        + _cta_row('<a href="/preorder/festival" class="btn btn-outline" style="color:var(--blue-main);border-color:var(--blue-main)"><i class="fas fa-music"></i> 主題行程預購</a>')
        + '<section class="pp-conclusion"><h2 style="margin:0 0 10px">先講結論</h2><p>'
        + conclusion + '</p></section>'
        + '<h2>活動速覽</h2>' + table
        + day_plan
        + '<h2>延伸閱讀：把白天行程排好</h2>' + links
        + _faq_html(faq)
        + _bottom_cta('想邊看音樂節邊玩澎湖？把日期傳給我們，官方合作旅行社幫你排到好。')
        + '</div>')
    event_ld = {
        "@context": "https://schema.org", "@type": "Event",
        "name": "2026 澎湖追風音樂燈光節",
        "startDate": "2026-09-12", "endDate": "2026-10-11",
        "eventAttendanceMode": "https://schema.org/OfflineEventAttendanceMode",
        "eventStatus": "https://schema.org/EventScheduled",
        "location": {"@type": "Place", "name": "澎湖觀音亭園區",
                     "address": {"@type": "PostalAddress", "addressLocality": "馬公市",
                                 "addressRegion": "澎湖縣", "addressCountry": "TW"}},
        "description": "2026 澎湖追風音樂燈光節：觀音亭園區燈光展演 9/12–10/11，藝人展演 9/12、9/13、9/19、9/26、10/3。",
    }
    trip_ld = {
        "@context": "https://schema.org", "@type": "TouristTrip",
        "name": "2026 澎湖追風音樂燈光節主題行程",
        "description": "官方合作旅行社潮旅國際的三天兩夜音樂節主題行程：白天玩澎湖、晚上看展演。",
        "url": f"{SITE}/preorder/festival",
        "provider": {"@type": "TravelAgency", "name": "潮旅國際旅行社", "url": f"{SITE}/"},
    }
    return dict(slug=slug, title=title, desc=desc, body=body,
                extra_ld=[event_ld, trip_ld], faq=faq,
                breadcrumb_name='2026 澎湖追風音樂燈光節攻略')


def _build_pages():
    pages = {}
    for builder in (_page_3days, _page_family, _page_food, _page_festival):
        p = builder()
        slug = p['slug']
        trail = [("首頁", f"{SITE}/"), (p['breadcrumb_name'], f"{SITE}/{slug}")]
        ld_blocks = ([_webpage_ld(slug, p['title'], p['desc']),
                      _breadcrumb_ld(trail), _faq_ld(p['faq'])] + p['extra_ld'])
        head_extra = PILLAR_STYLE + ''.join(
            '<script type="application/ld+json">' + json.dumps(d, ensure_ascii=False) + '</script>'
            for d in ld_blocks)
        pages[slug] = dict(title=p['title'], desc=p['desc'],
                           canonical=f'{SITE}/{slug}', body=p['body'],
                           head_extra=head_extra)
    return pages


PILLAR_PAGES = _build_pages()
