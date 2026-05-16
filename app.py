"""
潮旅國際旅行社 - Flask 後端
GET  /            → 首頁
GET  /admin       → 管理後台
POST /api/contact → 儲存諮詢
GET  /api/contacts          → 查詢諮詢（需 ADMIN_KEY）
GET  /api/tours             → 取得所有啟用行程（公開）
GET  /api/admin/tours       → 取得所有行程含停用（需 ADMIN_KEY）
POST /api/admin/tours       → 新增行程
PUT  /api/admin/tours/<id>  → 修改行程
DELETE /api/admin/tours/<id>→ 刪除行程
"""

import os
import json
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from flask import Flask, send_from_directory, request, jsonify
import psycopg2
import psycopg2.extras
from psycopg2.extras import Json
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__, static_folder='.', static_url_path='')

_db_initialized = False

# ─── 資料庫連線 ────────────────────────────────────────────
def get_db():
    url = os.environ.get('DATABASE_URL', '')
    if not url:
        raise RuntimeError('DATABASE_URL 未設定')
    if url.startswith('postgres://'):
        url = url.replace('postgres://', 'postgresql://', 1)
    return psycopg2.connect(url, cursor_factory=psycopg2.extras.RealDictCursor)


# ─── 管理員驗證 ────────────────────────────────────────────
def is_admin():
    key = (request.args.get('key')
           or request.headers.get('X-Admin-Key')
           or (request.get_json(force=True, silent=True) or {}).get('_key', ''))
    admin_key = os.environ.get('ADMIN_KEY', '')
    return (not admin_key) or (key == admin_key)


# ─── 資料表初始化 ──────────────────────────────────────────
def init_db():
    conn = get_db()
    cur = conn.cursor()

    # contacts 資料表
    cur.execute("""
        CREATE TABLE IF NOT EXISTS contacts (
            id              SERIAL PRIMARY KEY,
            name            VARCHAR(100) NOT NULL,
            phone           VARCHAR(50)  NOT NULL,
            travel_date     DATE,
            travel_date_end DATE,
            people          VARCHAR(20),
            budget          VARCHAR(30),
            transport       VARCHAR(20),
            departure_city  VARCHAR(50),
            tour_interest   VARCHAR(100),
            notes           TEXT,
            created_at      TIMESTAMP DEFAULT NOW()
        )
    """)

    # tours 資料表
    cur.execute("""
        CREATE TABLE IF NOT EXISTS tours (
            id           SERIAL PRIMARY KEY,
            tabs         JSONB    NOT NULL DEFAULT '["featured"]',
            badge_text   VARCHAR(40),
            badge_class  VARCHAR(40),
            image_url    TEXT,
            title        VARCHAR(120) NOT NULL,
            description  TEXT,
            suitable_for VARCHAR(120),
            duration     VARCHAR(30),
            price_display VARCHAR(60),
            is_hero      BOOLEAN  DEFAULT FALSE,
            prices       JSONB    DEFAULT '[]',
            modal_data   JSONB    DEFAULT '{}',
            sort_order   INT      DEFAULT 0,
            is_active    BOOLEAN  DEFAULT TRUE,
            created_at   TIMESTAMP DEFAULT NOW(),
            updated_at   TIMESTAMP DEFAULT NOW()
        )
    """)
    conn.commit()

    # 若 tours 資料表是空的，寫入預設行程
    cur.execute("SELECT COUNT(*) AS n FROM tours")
    if cur.fetchone()['n'] == 0:
        _seed_tours(conn, cur)

    cur.close()
    conn.close()
    print('[DB] 資料表已就緒')


def _seed_tours(conn, cur):
    """寫入預設行程資料（首次部署時執行）。"""
    default_tours = [
        # ── 1. 2026 跟著海龜漫旅 ──────────────────────────────
        {
            'tabs': ['featured', '4d3n'],
            'badge_text': '2026 主打',
            'badge_class': 'badge-2026',
            'image_url': 'https://images.unsplash.com/photo-1583212292454-1fe6229603b7?w=600&q=80',
            'title': '🐢 跟著海龜漫旅',
            'description': '今年夏天，把自己交給海。4天3夜望安深度 × 海島體驗 × 永續旅遊，兩人成行說走就走！',
            'suitable_for': '兩人成行 / 親子 / 情侶',
            'duration': '4天3夜',
            'price_display': 'NT$ 6,999 起',
            'is_hero': True,
            'prices': [
                {'label': '✈ 松山出發', 'value': 'NT$ 9,999 起 / 人'},
                {'label': '✈ 台中出發', 'value': 'NT$ 8,999 起 / 人'},
                {'label': '✈ 高雄出發', 'value': 'NT$ 7,999 起 / 人'},
                {'label': '🚢 嘉義搭船', 'value': 'NT$ 6,999 起 / 人'},
            ],
            'modal_data': {
                'header_class': 'modal-header--turtle',
                'year': '2026',
                'subtitle': '今年夏天，把自己交給海。',
                'tag': '4天3夜 × 望安深度 × 海島體驗 × 永續旅遊',
                'dates': ['6/12（五）－ 6/15（一）', '6/26（五）－ 6/29（一）',
                          '7/10（五）－ 7/13（一）', '7/24（五）－ 7/27（一）'],
                'highlights': [
                    '🐢 走進海龜的家，綠蠵龜保育中心導覽',
                    '🤿 浮潛 × 珊瑚礁生態探索',
                    '🏡 望安花宅深度走讀 × 黑糖糕 DIY',
                    '🌙 夜間照海（依潮汐調整，備案：天台山觀星）',
                    '🍽 在地風味 × 山海味餐食體驗',
                ],
                'days': [
                    {'label': 'DAY 1', 'title': '抵達澎湖 × 海島開場',
                     'items': ['抵達澎湖', '市區觀光（觀音亭 / 海邊景點）', '自由活動 × 晚餐自理']},
                    {'label': 'DAY 2', 'title': '望安深度探索',
                     'items': ['搭船前往望安', '綠蠵龜保育中心導覽', '山海味午餐',
                               '珊瑚礁介紹 × 浮潛體驗', '在地風味晚餐',
                               '夜間照海（依潮汐調整，如無法前往則改天台山觀星）']},
                    {'label': 'DAY 3', 'title': '慢島生活體驗',
                     'items': ['晨間海島漫遊（早餐自理）', '花宅走讀 × 黑糖糕 DIY',
                               '午餐（自理）', '小禮遇', '返回澎湖本島']},
                    {'label': 'DAY 4', 'title': '經典澎湖一次收',
                     'items': ['澎湖跨海大橋', '經典景點巡禮', '返程']},
                ],
                'notice': '名額有限，熱門行程盡早預定！兩人成行即可出發，好友、親子、情侶說走就走。',
            },
            'sort_order': 0,
        },
        # ── 2. 澎湖經典三日遊 ─────────────────────────────────
        {
            'tabs': ['featured', '3d2n'],
            'badge_text': '最受歡迎',
            'badge_class': 'popular',
            'image_url': 'https://images.unsplash.com/photo-1507525428034-b723cf961d3e?w=600&q=80',
            'title': '澎湖經典三日遊',
            'description': '走訪北寮奎壁山、跨海大橋、七美雙心石滬，感受澎湖最具代表性的自然與人文風景。',
            'suitable_for': '親子 / 情侶 / 家庭',
            'duration': '3天2夜',
            'price_display': 'NT$ 8,800 起 / 人',
            'is_hero': False,
            'prices': [],
            'modal_data': {
                'tag': '3天2夜｜NT$ 8,800 起',
                'highlights': [
                    'Day 1：馬公市區散策、天后宮、觀音亭夕陽',
                    'Day 2：奎壁山摩西分海、跨海大橋、吉貝島浮潛',
                    'Day 3：七美雙心石滬、南海秘境，返回馬公',
                ],
                'includes': '住宿2晚（雙人房）、每日早餐、景點門票、專業導遊、接送服務',
                'notes': '機票/船票需自行購買，行程依天候調整，導遊保有微調權利',
            },
            'sort_order': 1,
        },
        # ── 3. 親子海島體驗行程 ───────────────────────────────
        {
            'tabs': ['featured', '3d2n'],
            'badge_text': '親子首選',
            'badge_class': 'family',
            'image_url': 'https://images.unsplash.com/photo-1519046904884-53103b34b206?w=600&q=80',
            'title': '親子海島體驗行程',
            'description': '專為家庭設計，包含潮間帶生態導覽、DIY貝殼彩繪、淺水浮潛等，讓孩子與海洋親密接觸。',
            'suitable_for': '親子家庭 / 小孩友善',
            'duration': '3天2夜',
            'price_display': 'NT$ 9,500 起 / 人',
            'is_hero': False,
            'prices': [],
            'modal_data': {
                'tag': '3天2夜｜NT$ 9,500 起',
                'highlights': [
                    'Day 1：潮間帶生態導覽、夜間螢火蟲生態觀察',
                    'Day 2：淺水浮潛體驗、DIY貝殼彩繪工作坊',
                    'Day 3：海灘淨灘活動、海洋小故事講座',
                ],
                'includes': '住宿2晚（家庭房）、每日早餐、專業兒童安全裝備、親子導遊',
                'notes': '建議小孩年齡 4歲以上，均有專業救生員隨行保護',
            },
            'sort_order': 2,
        },
        # ── 4. 望安永續生態旅行 ───────────────────────────────
        {
            'tabs': ['featured', '4d3n'],
            'badge_text': '生態特色',
            'badge_class': 'eco',
            'image_url': 'https://images.unsplash.com/photo-1500375592092-40eb2168fd21?w=600&q=80',
            'title': '望安永續生態旅行',
            'description': '前往望安島探索綠蠵龜產卵保護區、花宅聚落古厝文化，深入感受離島純樸的生命力。',
            'suitable_for': '自然愛好者 / 生態旅遊',
            'duration': '4天3夜',
            'price_display': 'NT$ 12,800 起 / 人',
            'is_hero': False,
            'prices': [],
            'modal_data': {
                'tag': '4天3夜｜NT$ 12,800 起',
                'highlights': [
                    'Day 1：澎湖本島精華景點',
                    'Day 2：搭船前往望安島，花宅聚落古厝文化導覽',
                    'Day 3：綠蠵龜產卵保護區解說、手工藝工坊體驗',
                    'Day 4：返回馬公，自由活動後搭船/飛機離島',
                ],
                'includes': '住宿3晚、每日早餐、望安船票、專業生態導遊、保育捐款',
                'notes': '此行程每位旅客均捐出部分費用支持望安綠蠵龜保育計畫',
            },
            'sort_order': 3,
        },
        # ── 5. SUP × 浮潛 × 海洋體驗 ────────────────────────
        {
            'tabs': ['featured', '2d1n'],
            'badge_text': '冒險首選',
            'badge_class': 'adventure',
            'image_url': 'https://images.unsplash.com/photo-1506953823976-52e1fdc0149a?w=600&q=80',
            'title': 'SUP × 浮潛 × 海洋體驗',
            'description': '站上SUP立槳衝浪板，探索清澈珊瑚礁，浮潛看魚群，用最直接的方式與澎湖海洋相遇。',
            'suitable_for': '年輕族群 / 運動愛好者',
            'duration': '2天1夜',
            'price_display': 'NT$ 5,800 起 / 人',
            'is_hero': False,
            'prices': [],
            'modal_data': {
                'tag': '2天1夜｜NT$ 5,800 起',
                'highlights': [
                    'Day 1：SUP立槳衝浪板體驗（含教練指導）、夕陽海灘BBQ',
                    'Day 2：珊瑚礁浮潛、水上摩托車體驗、返程',
                ],
                'includes': '住宿1晚、早餐、SUP裝備租借、浮潛裝備、救生衣、專業教練',
                'notes': '建議具備基本游泳能力，不會游泳者需穿著救生衣全程配合',
            },
            'sort_order': 4,
        },
        # ── 6. 澎湖日出快閃之旅 ──────────────────────────────
        {
            'tabs': ['2d1n'],
            'badge_text': '',
            'badge_class': '',
            'image_url': 'https://images.unsplash.com/photo-1507525428034-b723cf961d3e?w=600&q=80',
            'title': '澎湖日出快閃之旅',
            'description': '搭早班船出發，抵達澎湖後直奔秘境沙灘，看星空日出，隔日輕鬆返台。',
            'suitable_for': '情侶 / 朋友揪團',
            'duration': '2天1夜',
            'price_display': 'NT$ 4,500 起 / 人',
            'is_hero': False,
            'prices': [],
            'modal_data': {
                'tag': '2天1夜｜NT$ 4,500 起',
                'highlights': ['秘境沙灘星空觀賞', '日出體驗', '輕鬆快閃返台'],
                'notes': '詳情請透過 LINE 諮詢',
            },
            'sort_order': 5,
        },
        # ── 7. 澎湖深度探索之旅 ──────────────────────────────
        {
            'tabs': ['4d3n'],
            'badge_text': '',
            'badge_class': '',
            'image_url': 'https://images.unsplash.com/photo-1507525428034-b723cf961d3e?w=600&q=80',
            'title': '澎湖深度探索之旅',
            'description': '從本島到離島，北海玄武岩、南海七美，再加入夜釣體驗，把澎湖玩透透。',
            'suitable_for': '深度旅遊愛好者',
            'duration': '4天3夜',
            'price_display': 'NT$ 14,500 起 / 人',
            'is_hero': False,
            'prices': [],
            'modal_data': {
                'tag': '4天3夜｜NT$ 14,500 起',
                'highlights': ['北海玄武岩地質巡禮', '南海七美雙心石滬', '夜釣體驗'],
                'notes': '詳情請透過 LINE 諮詢',
            },
            'sort_order': 6,
        },
    ]

    for t in default_tours:
        cur.execute("""
            INSERT INTO tours
              (tabs, badge_text, badge_class, image_url, title, description,
               suitable_for, duration, price_display, is_hero, prices, modal_data,
               sort_order, is_active)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,TRUE)
        """, (
            Json(t['tabs']), t['badge_text'], t['badge_class'],
            t['image_url'], t['title'], t['description'],
            t['suitable_for'], t['duration'], t['price_display'],
            t['is_hero'], Json(t['prices']), Json(t['modal_data']),
            t['sort_order'],
        ))
    conn.commit()
    print(f'[DB] 已寫入 {len(default_tours)} 筆預設行程')


# gunicorn 啟動時初始化（模組層級）
try:
    with app.app_context():
        init_db()
except Exception as _e:
    print(f'[警告] 啟動時無法初始化 DB：{_e}')


@app.before_request
def ensure_db():
    global _db_initialized
    if not _db_initialized:
        try:
            init_db()
            _db_initialized = True
        except Exception as e:
            print(f'[DB INIT] {e}')


# ─── 靜態頁面 ──────────────────────────────────────────────
@app.route('/')
def index():
    return send_from_directory('.', 'index.html')


@app.route('/admin')
def admin():
    return send_from_directory('.', 'admin.html')


# ─── 健康檢查 ──────────────────────────────────────────────
@app.route('/api/health')
def health():
    db_url = os.environ.get('DATABASE_URL', '')
    db_status = 'not_set'
    db_error = None
    table_exists = False
    if db_url:
        db_status = 'url_found'
        try:
            conn = get_db()
            cur = conn.cursor()
            cur.execute("SELECT to_regclass('public.contacts') AS t")
            row = cur.fetchone()
            table_exists = row['t'] is not None
            cur.close()
            conn.close()
            db_status = 'connected'
        except Exception as e:
            db_error = str(e)
            db_status = 'error'
    return jsonify(ok=True, db_url_set=bool(db_url),
                   db_url_prefix=db_url[:25] + '...' if db_url else '',
                   db_status=db_status, db_error=db_error,
                   table_contacts=table_exists)


# ─── 公開行程 API ──────────────────────────────────────────
@app.route('/api/tours', methods=['GET'])
def get_tours():
    """回傳所有啟用行程，依 tab 分組。"""
    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute("SELECT * FROM tours WHERE is_active=TRUE ORDER BY sort_order, id")
        rows = cur.fetchall()
        cur.close(); conn.close()

        grouped = {'featured': [], '2d1n': [], '3d2n': [], '4d3n': []}
        for r in rows:
            r = dict(r)
            r['created_at'] = str(r.get('created_at', ''))
            r['updated_at'] = str(r.get('updated_at', ''))
            for tab in (r.get('tabs') or ['featured']):
                if tab in grouped:
                    grouped[tab].append(r)
        return jsonify(ok=True, tours=grouped)
    except Exception as e:
        return jsonify(ok=False, error=str(e)), 500


# ─── 管理員行程 CRUD ────────────────────────────────────────
@app.route('/api/admin/tours', methods=['GET'])
def admin_get_tours():
    if not is_admin():
        return jsonify(ok=False, error='未授權'), 401
    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute("SELECT * FROM tours ORDER BY sort_order, id")
        rows = [dict(r) for r in cur.fetchall()]
        cur.close(); conn.close()
        for r in rows:
            r['created_at'] = str(r.get('created_at', ''))
            r['updated_at'] = str(r.get('updated_at', ''))
        return jsonify(ok=True, tours=rows)
    except Exception as e:
        return jsonify(ok=False, error=str(e)), 500


@app.route('/api/admin/tours', methods=['POST'])
def admin_create_tour():
    if not is_admin():
        return jsonify(ok=False, error='未授權'), 401
    data = request.get_json(force=True, silent=True) or {}
    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO tours
              (tabs, badge_text, badge_class, image_url, title, description,
               suitable_for, duration, price_display, is_hero, prices, modal_data,
               sort_order, is_active)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            RETURNING id
        """, (
            Json(data.get('tabs', ['featured'])),
            data.get('badge_text', ''), data.get('badge_class', ''),
            data.get('image_url', ''), data.get('title', '新行程'),
            data.get('description', ''), data.get('suitable_for', ''),
            data.get('duration', ''), data.get('price_display', ''),
            data.get('is_hero', False),
            Json(data.get('prices', [])), Json(data.get('modal_data', {})),
            data.get('sort_order', 99), data.get('is_active', True),
        ))
        new_id = cur.fetchone()['id']
        conn.commit(); cur.close(); conn.close()
        return jsonify(ok=True, id=new_id)
    except Exception as e:
        return jsonify(ok=False, error=str(e)), 500


@app.route('/api/admin/tours/<int:tour_id>', methods=['PUT'])
def admin_update_tour(tour_id):
    if not is_admin():
        return jsonify(ok=False, error='未授權'), 401
    data = request.get_json(force=True, silent=True) or {}
    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute("""
            UPDATE tours SET
              tabs=%s, badge_text=%s, badge_class=%s, image_url=%s, title=%s,
              description=%s, suitable_for=%s, duration=%s, price_display=%s,
              is_hero=%s, prices=%s, modal_data=%s, sort_order=%s, is_active=%s,
              updated_at=NOW()
            WHERE id=%s
        """, (
            Json(data.get('tabs', ['featured'])),
            data.get('badge_text', ''), data.get('badge_class', ''),
            data.get('image_url', ''), data.get('title', ''),
            data.get('description', ''), data.get('suitable_for', ''),
            data.get('duration', ''), data.get('price_display', ''),
            data.get('is_hero', False),
            Json(data.get('prices', [])), Json(data.get('modal_data', {})),
            data.get('sort_order', 0), data.get('is_active', True),
            tour_id,
        ))
        conn.commit(); cur.close(); conn.close()
        return jsonify(ok=True)
    except Exception as e:
        return jsonify(ok=False, error=str(e)), 500


@app.route('/api/admin/tours/<int:tour_id>', methods=['DELETE'])
def admin_delete_tour(tour_id):
    if not is_admin():
        return jsonify(ok=False, error='未授權'), 401
    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute("DELETE FROM tours WHERE id=%s", (tour_id,))
        conn.commit(); cur.close(); conn.close()
        return jsonify(ok=True)
    except Exception as e:
        return jsonify(ok=False, error=str(e)), 500


# ─── 寄送諮詢通知信 ────────────────────────────────────────
def send_contact_email(data):
    sender    = os.environ.get('EMAIL_USER', '')
    password  = os.environ.get('EMAIL_PASS', '')
    smtp_host = os.environ.get('SMTP_HOST', 'smtpout.secureserver.net')
    smtp_port = int(os.environ.get('SMTP_PORT', '465'))
    recipient = 'dodoken1002@phbay.net'
    if not sender or not password:
        print('[EMAIL] 未設定 EMAIL_USER / EMAIL_PASS，跳過寄信')
        return

    body = f"""潮旅國際旅行社 — 新諮詢通知

姓名：{data.get('name', '')}
電話：{data.get('phone', '')}
出發日：{data.get('travel_date', '')}
回程日：{data.get('travel_date_end', '')}
旅遊人數：{data.get('people', '')} 人
每人預算：{data.get('budget', '（未填）')}
交通方式：{data.get('transport', '（未填）')}
出發地：{data.get('departure_city', '（未填）')}
感興趣行程：{data.get('tour_interest', '（未填）')}
備註：{data.get('notes', '（未填）')}

請盡快與客戶聯繫。
"""
    msg = MIMEMultipart()
    msg['From']    = f'潮旅國際旅行社 <{sender}>'
    msg['To']      = recipient
    msg['Subject'] = f'【新諮詢】{data.get("name", "")} — {data.get("travel_date", "")} ~ {data.get("travel_date_end", "")}'
    msg.attach(MIMEText(body, 'plain', 'utf-8'))

    try:
        with smtplib.SMTP_SSL(smtp_host, smtp_port, timeout=10) as server:
            server.login(sender, password)
            server.sendmail(sender, recipient, msg.as_string())
        print(f'[EMAIL] 通知信已寄出至 {recipient}')
    except Exception as e:
        print(f'[EMAIL] 寄信失敗（不影響表單儲存）：{e}')


# ─── 諮詢表單 ──────────────────────────────────────────────
@app.route('/api/contact', methods=['POST'])
def submit_contact():
    data = request.get_json(force=True, silent=True) or {}
    required = ['name', 'phone', 'travel_date', 'travel_date_end', 'people', 'transport']
    missing = [f for f in required if not data.get(f)]
    if missing:
        return jsonify(ok=False, error=f'缺少必填欄位：{", ".join(missing)}'), 400
    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO contacts
              (name,phone,travel_date,travel_date_end,people,budget,transport,departure_city,tour_interest,notes)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id, created_at
        """, (data['name'], data['phone'], data['travel_date'], data['travel_date_end'],
              data['people'], data.get('budget',''), data['transport'],
              data.get('departure_city',''), data.get('tour_interest',''), data.get('notes','')))
        row = cur.fetchone()
        conn.commit(); cur.close(); conn.close()
        send_contact_email(data)   # 寄通知信（失敗不影響回傳）
        return jsonify(ok=True, id=row['id'], created_at=str(row['created_at']))
    except Exception as e:
        return jsonify(ok=False, error='伺服器錯誤，請稍後再試'), 500


@app.route('/api/contacts', methods=['GET'])
def list_contacts():
    if not is_admin():
        return jsonify(ok=False, error='未授權'), 401
    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute("SELECT * FROM contacts ORDER BY created_at DESC LIMIT 200")
        rows = cur.fetchall()
        cur.close(); conn.close()
        result = []
        for r in rows:
            r = dict(r)
            if r.get('travel_date'):     r['travel_date']     = str(r['travel_date'])
            if r.get('travel_date_end'): r['travel_date_end'] = str(r['travel_date_end'])
            if r.get('created_at'): r['created_at'] = str(r['created_at'])
            result.append(r)
        return jsonify(ok=True, contacts=result)
    except Exception as e:
        return jsonify(ok=False, error='伺服器錯誤'), 500


# ─── 啟動 ──────────────────────────────────────────────────
if __name__ == '__main__':
    try:
        init_db()
    except Exception as e:
        print(f'[警告] 本機無 DB，跳過初始化：{e}')
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=os.environ.get('FLASK_DEBUG','0')=='1')
