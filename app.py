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
import re
import json
import base64
import hmac
import hashlib
import random
import urllib.request
import urllib.error
import urllib.parse
from datetime import date, datetime, timedelta, timezone
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from flask import Flask, send_from_directory, request, jsonify, session, redirect
from werkzeug.security import generate_password_hash, check_password_hash
import psycopg2
import psycopg2.extras
from psycopg2.extras import Json
from dotenv import load_dotenv
from member_program import (init_member_tables, level_for_trips, levels as member_levels,
                            next_level, next_member_no, normalize_phone, points_per_trip,
                            public_member, recalculate_member, sync_trip_points, valid_email)

load_dotenv()

app = Flask(__name__, static_folder='.', static_url_path='')
# session cookie 簽章金鑰（後台帳號登入用）；優先 FLASK_SECRET_KEY，退回 ADMIN_KEY
_SECRET_KEY_FALLBACK = 'phbay-dev-secret'
app.secret_key = (os.environ.get('FLASK_SECRET_KEY') or os.environ.get('ADMIN_KEY')
                  or _SECRET_KEY_FALLBACK)
# 會員登入態（session['member_id']）與 Email OTP 的 HMAC 都繫於 secret_key。
# 若正式環境用到這個寫在原始碼裡的預設值，任何人都能偽造 cookie 以任意會員身分登入，
# 因此寧可拒絕啟動也不要靜默降級。（此情境下 ADMIN_KEY 亦未設，後台本來就是全開狀態。）
if app.secret_key == _SECRET_KEY_FALLBACK and os.environ.get('RAILWAY_ENVIRONMENT_NAME', '').strip():
    raise RuntimeError(
        '正式環境未設定 FLASK_SECRET_KEY（亦無 ADMIN_KEY），拒絕以預設金鑰啟動。'
        '請先到 Railway 設定 FLASK_SECRET_KEY。')
if not os.environ.get('FLASK_SECRET_KEY', '').strip():
    print('[警告] 未設定 FLASK_SECRET_KEY，目前沿用 ADMIN_KEY 當 session 金鑰；'
          '兩者耦合，且輪換 ADMIN_KEY 會讓全部會員登出，建議獨立設定。')
app.permanent_session_lifetime = timedelta(hours=12)

# ─── 靜態資源快取 ──────────────────────────────────────────
# CSS/JS/圖片長快取；改動 css/js 時必須同步調整各 HTML 引用的 ?v= 版本字串，
# 否則使用者會拿到快取的舊資源（版本字串統一用 ASSET_VERSION）。
ASSET_VERSION = '20260827'
_LONG_CACHE_EXT = ('.css', '.js', '.png', '.jpg', '.jpeg', '.webp', '.avif',
                   '.gif', '.svg', '.ico', '.woff', '.woff2')

# 目前站上實際會用到的外部來源。CSP 先以 Report-Only 上線：
# 瀏覽器只回報不攔截，確認一週沒有誤擋之後，把環境變數 CSP_ENFORCE 設為 1
# 即可改成強制模式。屆時 XSS 就多了一道「就算注入也送不出去」的防線。
_CSP = "; ".join([
    "default-src 'self'",
    # 站內腳本大量使用 inline，短期內無法移除，因此保留 unsafe-inline；
    # 真正的價值在於下面幾條：外部腳本與資料外傳都被限制在白名單內。
    "script-src 'self' 'unsafe-inline' https://www.googletagmanager.com "
    "https://connect.facebook.net https://cdnjs.cloudflare.com https://cdn.jsdelivr.net",
    "style-src 'self' 'unsafe-inline' https://cdnjs.cloudflare.com https://fonts.googleapis.com",
    "font-src 'self' data: https://cdnjs.cloudflare.com https://fonts.gstatic.com",
    "img-src 'self' data: blob: https:",
    "connect-src 'self' https://www.google-analytics.com https://www.googletagmanager.com "
    "https://region1.google-analytics.com",
    "frame-src 'self' https://www.facebook.com https://www.instagram.com",
    "form-action 'self'",
    "frame-ancestors 'self'",
    "base-uri 'self'",
    "object-src 'none'",
])


@app.after_request
def _set_security_headers(resp):
    header = ('Content-Security-Policy'
              if os.environ.get('CSP_ENFORCE', '').strip() == '1'
              else 'Content-Security-Policy-Report-Only')
    resp.headers.setdefault(header, _CSP)
    resp.headers.setdefault('X-Content-Type-Options', 'nosniff')
    resp.headers.setdefault('Referrer-Policy', 'strict-origin-when-cross-origin')
    return resp


@app.after_request
def _set_cache_headers(resp):
    path = request.path.lower()
    if path.startswith('/member/'):
        resp.headers['X-Robots-Tag'] = 'noindex, nofollow'
    if path.startswith('/api/'):
        return resp
    # 只有成功回應才長快取。錯誤回應（例如檔案尚未部署完成時的 404）若也標成
    # immutable，瀏覽器會把「這個檔案不存在」快取一年，之後檔案補上了也不會重抓。
    if resp.status_code >= 400:
        resp.headers['Cache-Control'] = 'no-store'
        return resp
    if path.endswith(_LONG_CACHE_EXT):
        resp.headers['Cache-Control'] = 'public, max-age=31536000, immutable'
    elif resp.mimetype == 'text/html':
        resp.headers['Cache-Control'] = 'no-cache'
    return resp


@app.errorhandler(404)
def _page_not_found(_error):
    """讓一般網頁 404 可在 GA4 統計；API 仍維持機器可讀 JSON。"""
    if request.path.startswith('/api/'):
        return jsonify(ok=False, error='not found'), 404
    path_json = json.dumps(request.path, ensure_ascii=False)
    html = f'''<!doctype html><html lang="zh-Hant"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="robots" content="noindex"><title>找不到頁面｜潮旅國際旅行社</title>
<script async src="https://www.googletagmanager.com/gtag/js?id=G-47DV1VPF9J"></script>
<script>window.dataLayer=window.dataLayer||[];function gtag(){{dataLayer.push(arguments);}}
gtag('js',new Date());gtag('config','G-47DV1VPF9J');
gtag('event','page_not_found',{{page_path:{path_json}}});</script>
<style>body{{font-family:system-ui,sans-serif;margin:0;background:#f4fbff;color:#17384d}}
main{{max-width:640px;margin:12vh auto;padding:32px;text-align:center}}a{{color:#087ca7}}</style>
</head><body><main><h1>找不到這個頁面</h1>
<p>網址可能已變更，請回首頁繼續查看澎湖行程。</p><p><a href="/">回潮旅首頁</a></p>
</main></body></html>'''
    return html, 404

_db_initialized = False

# ─── 資料庫連線 ────────────────────────────────────────────
def get_db():
    url = os.environ.get('DATABASE_URL', '')
    if not url:
        raise RuntimeError('DATABASE_URL 未設定')
    if url.startswith('postgres://'):
        url = url.replace('postgres://', 'postgresql://', 1)
    return psycopg2.connect(url, cursor_factory=psycopg2.extras.RealDictCursor, connect_timeout=5)


# ─── 管理員驗證（金鑰＝owner；帳號登入依角色分權）──────────────
ADMIN_ROLES = {'owner': '管理者（全部權限）', 'orders': '訂位人員（訂單）', 'editor': '小編（文章）'}


def _legacy_key_ok():
    key = (request.args.get('key')
           or request.headers.get('X-Admin-Key')
           or (request.get_json(force=True, silent=True) or {}).get('_key', ''))
    admin_key = os.environ.get('ADMIN_KEY', '')
    return bool(admin_key) and key == admin_key


def current_admin():
    """回傳目前操作者 {id, username, name, role}；金鑰視為 owner。未登入回 None。"""
    if _legacy_key_ok():
        return {'id': 0, 'username': '(admin-key)', 'name': '管理金鑰', 'role': 'owner'}
    u = session.get('au')
    if isinstance(u, dict) and u.get('role') in ADMIN_ROLES:
        return u
    # 未設 ADMIN_KEY 的開發環境維持全開（與舊行為一致）。
    # 但正式環境絕不能走這條路——那等於整個後台對所有人開放。
    if (not os.environ.get('ADMIN_KEY', '')
            and not os.environ.get('RAILWAY_ENVIRONMENT_NAME', '').strip()):
        return {'id': 0, 'username': '(dev)', 'name': '開發模式', 'role': 'owner'}
    return None


def is_admin():
    """owner 專用檢查（金鑰或 owner 帳號）。訂單/文章端點請用 has_role()。"""
    u = current_admin()
    return bool(u and u['role'] == 'owner')


def has_role(role):
    """角色檢查：owner 永遠通過，否則需完全符合指定角色。"""
    u = current_admin()
    return bool(u and (u['role'] == 'owner' or u['role'] == role))


def _client_ip():
    xff = request.headers.get('X-Forwarded-For', '')
    return (xff.split(',')[0].strip() if xff else request.remote_addr) or ''


def write_audit(cur, action, category='', scope='', record_count=0, pax_count=0, detail=''):
    """寫一筆個資稽核紀錄（操作者身分由伺服器端 session 決定，不信任前端）。
    傳入既有 cursor，與呼叫端同一交易一起 commit。"""
    u = current_admin() or {}
    cur.execute("""
        INSERT INTO audit_logs (username, display_name, role, action, category, scope,
                                record_count, pax_count, detail, ip)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
    """, (u.get('username', ''), u.get('name', ''), u.get('role', ''), action, category, scope,
          int(record_count or 0), int(pax_count or 0), detail, _client_ip()))


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
            slot_id         INT,
            is_waitlist     BOOLEAN DEFAULT FALSE,
            notes           TEXT,
            created_at      TIMESTAMP DEFAULT NOW()
        )
    """)
    # 舊資料庫補欄位（不影響已有欄位）
    # ⚠️ 這份清單必須涵蓋 CREATE TABLE 裡「初版之後才加入」的每一個欄位。
    # CREATE TABLE IF NOT EXISTS 不會修改已存在的表，漏列的欄位在正式站永遠不會被建立，
    # 之後 INSERT 就會整筆失敗。（2026-08-26 事故：travel_date_end／budget／transport／
    # departure_city 漏列，導致線上諮詢表單自 7/19 起每一筆送出都失敗。）
    for col, defn in [
        ('slot_id',     'INT'),
        ('is_waitlist', 'BOOLEAN DEFAULT FALSE'),
        ('travel_date_end', 'DATE'),
        ('budget',          'VARCHAR(30)'),
        ('transport',       'VARCHAR(20)'),
        ('departure_city',  'VARCHAR(50)'),
        # 澎湖百旅會員計畫：蒐集回訪次數與會員狀態（皆選填）
        ('visit_count',   'VARCHAR(20)'),
        ('member_status', 'VARCHAR(30)'),
        ('member_no',     'VARCHAR(40)'),
        # P1 轉換漏斗：客服可追蹤諮詢 → 聯繫 → 成交／未成交
        ('lead_status',      "VARCHAR(30) DEFAULT 'new'"),
        ('contacted_at',     'TIMESTAMP'),
        ('converted_at',     'TIMESTAMP'),
        ('conversion_value', 'NUMERIC(12,2)'),
        ('utm',              "JSONB DEFAULT '{}'"),
    ]:
        try:
            cur.execute(f"ALTER TABLE contacts ADD COLUMN IF NOT EXISTS {col} {defn}")
        except Exception:
            conn.rollback()

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
            i18n         JSONB    DEFAULT '{}',
            sort_order   INT      DEFAULT 0,
            is_active    BOOLEAN  DEFAULT TRUE,
            created_at   TIMESTAMP DEFAULT NOW(),
            updated_at   TIMESTAMP DEFAULT NOW()
        )
    """)
    # 舊資料庫補 i18n 欄位
    try:
        cur.execute("ALTER TABLE tours ADD COLUMN IF NOT EXISTS i18n JSONB DEFAULT '{}'")
    except Exception:
        conn.rollback()
    # tour_slots 資料表
    cur.execute("""
        CREATE TABLE IF NOT EXISTS tour_slots (
            id           SERIAL PRIMARY KEY,
            tour_id      INT  NOT NULL,
            date_label   VARCHAR(120) NOT NULL,
            capacity     INT  NOT NULL DEFAULT 20,
            booked       INT  NOT NULL DEFAULT 0,
            waitlist_cap INT  NOT NULL DEFAULT 5,
            waitlisted   INT  NOT NULL DEFAULT 0,
            is_active    BOOLEAN DEFAULT TRUE,
            created_at   TIMESTAMP DEFAULT NOW()
        )
    """)


    # neihai preorder 資料表（小城故事・內海巡禮）
    cur.execute("""
        CREATE TABLE IF NOT EXISTS neihai_sailings (
            id            SERIAL PRIMARY KEY,
            sailing_date  DATE NOT NULL,
            sailing_time  VARCHAR(5) NOT NULL,
            capacity      INT NOT NULL DEFAULT 13,
            min_people    INT NOT NULL DEFAULT 6,
            is_active     BOOLEAN DEFAULT TRUE,
            notes         TEXT,
            created_at    TIMESTAMP DEFAULT NOW(),
            updated_at    TIMESTAMP DEFAULT NOW(),
            UNIQUE (sailing_date, sailing_time)
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS neihai_preorders (
            id              SERIAL PRIMARY KEY,
            booking_ref     VARCHAR(40) UNIQUE,
            sailing_id      INT NOT NULL REFERENCES neihai_sailings(id) ON DELETE CASCADE,
            agency_name     VARCHAR(120),
            contact_name    VARCHAR(100) NOT NULL,
            contact_phone   VARCHAR(50) NOT NULL,
            passenger_count INT NOT NULL,
            status          VARCHAR(30) NOT NULL DEFAULT 'pending_departure',
            notes           TEXT,
            created_at      TIMESTAMP DEFAULT NOW(),
            updated_at      TIMESTAMP DEFAULT NOW()
        )
    """)
    # 訂位確認信用：代表人 Email（選填）
    cur.execute("ALTER TABLE neihai_preorders ADD COLUMN IF NOT EXISTS contact_email VARCHAR(200)")
    cur.execute("ALTER TABLE neihai_preorders ADD COLUMN IF NOT EXISTS utm JSONB DEFAULT '{}'")
    # 行程結束後可封存（後台預設隱藏）
    cur.execute("ALTER TABLE neihai_preorders ADD COLUMN IF NOT EXISTS archived BOOLEAN DEFAULT FALSE")
    cur.execute("""
        CREATE TABLE IF NOT EXISTS neihai_passengers (
            id              SERIAL PRIMARY KEY,
            preorder_id     INT NOT NULL REFERENCES neihai_preorders(id) ON DELETE CASCADE,
            name            VARCHAR(100) NOT NULL,
            national_id     VARCHAR(30) NOT NULL,
            birth_date      DATE NOT NULL,
            phone           VARCHAR(50) NOT NULL,
            created_at      TIMESTAMP DEFAULT NOW()
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS neihai_preorder_logs (
            id           SERIAL PRIMARY KEY,
            preorder_id  INT NOT NULL REFERENCES neihai_preorders(id) ON DELETE CASCADE,
            summary      TEXT NOT NULL,
            changed_at   TIMESTAMP DEFAULT NOW()
        )
    """)

    # 後台使用者帳號（分權限：owner/orders/editor）
    cur.execute("""
        CREATE TABLE IF NOT EXISTS admin_users (
            id            SERIAL PRIMARY KEY,
            username      VARCHAR(50) UNIQUE NOT NULL,
            password_hash VARCHAR(300) NOT NULL,
            display_name  VARCHAR(100),
            role          VARCHAR(20) NOT NULL DEFAULT 'orders',
            is_active     BOOLEAN DEFAULT TRUE,
            created_at    TIMESTAMP DEFAULT NOW(),
            last_login    TIMESTAMP
        )
    """)

    # 個資稽核紀錄（誰在何時匯出/匯入/檢視含個資的名單）
    cur.execute("""
        CREATE TABLE IF NOT EXISTS audit_logs (
            id           SERIAL PRIMARY KEY,
            username     VARCHAR(80),
            display_name VARCHAR(120),
            role         VARCHAR(20),
            action       VARCHAR(30) NOT NULL,
            category     VARCHAR(40),
            scope        VARCHAR(160),
            record_count INT DEFAULT 0,
            pax_count    INT DEFAULT 0,
            detail       TEXT,
            ip           VARCHAR(60),
            created_at   TIMESTAMP DEFAULT NOW()
        )
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_audit_created ON audit_logs (created_at DESC)")

    # 澎湖百旅會員、旅次、點數與一次性登入／LINE 綁定碼
    # 以 SAVEPOINT 隔離：這段若失敗，後面的 qigui_daily_quota 等資料表仍須照常建立，
    # 否則一個新功能的建表錯誤會連帶拖垮整個 init_db。
    cur.execute("SAVEPOINT member_tables")
    try:
        init_member_tables(cur)
        cur.execute("RELEASE SAVEPOINT member_tables")
    except Exception as _member_exc:
        cur.execute("ROLLBACK TO SAVEPOINT member_tables")
        cur.execute("RELEASE SAVEPOINT member_tables")
        print(f'[DB INIT] 會員資料表初始化失敗（其餘資料表不受影響）：{_member_exc}')

    # 乞龜擲筊活動：每日禮物庫存（旅展現場限定，實體禮物有限，需硬性上限避免超發）
    cur.execute("""
        CREATE TABLE IF NOT EXISTS qigui_daily_quota (
            quota_date   DATE PRIMARY KEY,
            daily_limit  INT NOT NULL DEFAULT 125,
            given_out    INT NOT NULL DEFAULT 0
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS qigui_wins (
            id           SERIAL PRIMARY KEY,
            win_code     VARCHAR(20) UNIQUE NOT NULL,
            quota_date   DATE NOT NULL,
            claimed      BOOLEAN DEFAULT FALSE,
            claimed_at   TIMESTAMP,
            ip           VARCHAR(60),
            created_at   TIMESTAMP DEFAULT NOW()
        )
    """)

    # LINE 官方帳號互動用戶（webhook 記錄，用於取得 userId 與對照訂單）
    cur.execute("""
        CREATE TABLE IF NOT EXISTS line_users (
            user_id        VARCHAR(64) PRIMARY KEY,
            display_name   VARCHAR(120),
            last_message   TEXT,
            message_count  INT DEFAULT 0,
            first_seen     TIMESTAMP DEFAULT NOW(),
            last_seen      TIMESTAMP DEFAULT NOW()
        )
    """)

    # 通用預購系統資料表（音樂節等新行程；內海仍走既有 neihai_* 表）
    cur.execute("""
        CREATE TABLE IF NOT EXISTS preorder_products (
            id            SERIAL PRIMARY KEY,
            slug          VARCHAR(50) UNIQUE NOT NULL,
            name          VARCHAR(150) NOT NULL,
            description   TEXT DEFAULT '',
            slot_type     VARCHAR(10) NOT NULL DEFAULT 'daily',
            times         VARCHAR(200) DEFAULT '',
            duration_days INT NOT NULL DEFAULT 1,
            capacity      INT,
            min_people    INT NOT NULL DEFAULT 2,
            max_party     INT NOT NULL DEFAULT 13,
            date_start    DATE,
            date_end      DATE,
            badges        VARCHAR(300) DEFAULT '',
            is_active     BOOLEAN DEFAULT TRUE,
            created_at    TIMESTAMP DEFAULT NOW(),
            updated_at    TIMESTAMP DEFAULT NOW()
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS preorder_orders (
            id              SERIAL PRIMARY KEY,
            booking_ref     VARCHAR(40) UNIQUE,
            product_id      INT NOT NULL REFERENCES preorder_products(id) ON DELETE CASCADE,
            departure_date  DATE NOT NULL,
            departure_time  VARCHAR(5) DEFAULT '',
            agency_name     VARCHAR(120),
            contact_name    VARCHAR(100) NOT NULL,
            contact_phone   VARCHAR(50) NOT NULL,
            passenger_count INT NOT NULL,
            status          VARCHAR(30) NOT NULL DEFAULT 'pending_departure',
            notes           TEXT,
            created_at      TIMESTAMP DEFAULT NOW(),
            updated_at      TIMESTAMP DEFAULT NOW()
        )
    """)
    # 澎湖百旅會員：是否可認列為潮旅旅次。潮旅自營行程為 TRUE；
    # 若日後把代售產品加進 preorder_products，務必設為 FALSE，避免代售行程灌水會員等級。
    cur.execute("ALTER TABLE preorder_products ADD COLUMN IF NOT EXISTS counts_as_trip BOOLEAN NOT NULL DEFAULT TRUE")
    cur.execute("ALTER TABLE preorder_orders ADD COLUMN IF NOT EXISTS contact_email VARCHAR(200)")
    cur.execute("ALTER TABLE preorder_orders ADD COLUMN IF NOT EXISTS utm JSONB DEFAULT '{}'")
    cur.execute("ALTER TABLE preorder_orders ADD COLUMN IF NOT EXISTS archived BOOLEAN DEFAULT FALSE")
    cur.execute("""
        CREATE TABLE IF NOT EXISTS preorder_passengers (
            id              SERIAL PRIMARY KEY,
            order_id        INT NOT NULL REFERENCES preorder_orders(id) ON DELETE CASCADE,
            name            VARCHAR(100) NOT NULL,
            national_id     VARCHAR(30) NOT NULL,
            birth_date      DATE NOT NULL,
            phone           VARCHAR(50) NOT NULL,
            created_at      TIMESTAMP DEFAULT NOW()
        )
    """)
    # 通用預購訂單修改紀錄（與內海一致）
    cur.execute("""
        CREATE TABLE IF NOT EXISTS preorder_order_logs (
            id           SERIAL PRIMARY KEY,
            order_id     INT NOT NULL REFERENCES preorder_orders(id) ON DELETE CASCADE,
            summary      TEXT NOT NULL,
            changed_at   TIMESTAMP DEFAULT NOW()
        )
    """)
    # 種子商品：2026 追風音樂節主題行程（已存在則不動，後台/DB 可再調整）
    cur.execute("""
        INSERT INTO preorder_products
            (slug, name, description, slot_type, duration_days, capacity,
             min_people, max_party, date_start, date_end, badges)
        VALUES
            ('festival', '2026 澎湖追風音樂燈光節主題行程',
             '三天兩夜套裝行程，搭配澎湖追風音樂燈光節（觀音亭園區，燈光展演 9/12–10/11）。選擇出發日後，回程日自動為第三天。行程細節與報價由專人與您確認。',
             'daily', 3, 5, 2, 5, DATE '2026-09-12', DATE '2026-10-09',
             '兩人成行,每梯最多 5 人,三天兩夜,音樂節官方合作旅行社')
        ON CONFLICT (slug) DO NOTHING
    """)

    # posts 部落格資料表
    cur.execute("""
        CREATE TABLE IF NOT EXISTS posts (
            id           SERIAL PRIMARY KEY,
            slug         VARCHAR(180) UNIQUE NOT NULL,
            title        VARCHAR(200) NOT NULL,
            summary      TEXT,
            content      TEXT,
            cover_image  TEXT,
            tags         VARCHAR(200),
            author       VARCHAR(80) DEFAULT '潮旅國際旅行社',
            is_published BOOLEAN DEFAULT FALSE,
            published_at TIMESTAMP,
            created_at   TIMESTAMP DEFAULT NOW(),
            updated_at   TIMESTAMP DEFAULT NOW()
        )
    """)
    # AEO 選填欄位：faq=[{q,a},…] 文末常見問題；info_box={標籤:值,…} 文章資訊盒
    cur.execute("ALTER TABLE posts ADD COLUMN IF NOT EXISTS faq JSONB")
    cur.execute("ALTER TABLE posts ADD COLUMN IF NOT EXISTS info_box JSONB")
    # 多語系翻譯：{lang:{title,summary,content,faq,info_box}}，缺欄位回退中文（zh-tw）
    cur.execute("ALTER TABLE posts ADD COLUMN IF NOT EXISTS i18n JSONB DEFAULT '{}'")
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


@app.route('/penghu-100')
@app.route('/member/dashboard')
def member_pages():
    return send_from_directory('.', 'member.html')


@app.route('/lottery/')
def lottery():
    return send_from_directory('lottery', 'index.html')


@app.route('/lottery')
def lottery_redirect():
    return redirect('/lottery/', code=308)


@app.route('/qigui/')
def qigui():
    return send_from_directory('qigui', 'index.html')


@app.route('/qigui')
def qigui_redirect():
    return redirect('/qigui/', code=308)


# ─── 乞龜擲筊活動：後端權威判定（含每日禮物庫存硬上限）───────────
QIGUI_DAILY_LIMIT = 125           # 每日禮物名額（500 份 ÷ 4 天）
QIGUI_HOLY_PROB = 0.8434           # 單次擲筊「聖筊」機率，連續3次約 60%（0.8434^3 ≈ 0.60）
                                    # 2026-07-16：70%→55%→35%→50%；2026-07-19：回到70%；2026-07-20：降至60%


def _qigui_get_or_create_quota(cur, d):
    cur.execute("SELECT * FROM qigui_daily_quota WHERE quota_date=%s FOR UPDATE", (d,))
    row = cur.fetchone()
    if not row:
        cur.execute("""INSERT INTO qigui_daily_quota (quota_date, daily_limit, given_out)
                       VALUES (%s,%s,0) RETURNING *""", (d, QIGUI_DAILY_LIMIT))
        row = cur.fetchone()
    return dict(row)


def _qigui_make_code(d):
    chars = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789'
    rand = ''.join(random.choice(chars) for _ in range(4))
    return f"龜{d.strftime('%y%m%d')}-{rand}"


@app.route('/api/qigui/throw', methods=['POST'])
def qigui_throw():
    """後端權威擲筊：機率與每日庫存都由伺服器決定，前端只負責動畫呈現。
    以 Flask session 追蹤單一訪客當日的連續聖筊數與是否已用完當日挑戰。"""
    today = _taiwan_now().date()
    today_str = str(today)
    if session.get('qigui_date') != today_str:
        session['qigui_date'] = today_str
        session['qigui_streak'] = 0
        session['qigui_played'] = False
        session['qigui_won'] = False
        session['qigui_code'] = None

    if session.get('qigui_won'):
        return jsonify(ok=True, locked=True, already_won=True, code=session.get('qigui_code'))
    if session.get('qigui_played'):
        return jsonify(ok=True, locked=True, message='今日挑戰已使用，請明日再來')

    try:
        conn = get_db(); cur = conn.cursor()
        quota = _qigui_get_or_create_quota(cur, today)
        if quota['given_out'] >= quota['daily_limit']:
            conn.commit(); cur.close(); conn.close()
            session['qigui_played'] = True
            return jsonify(ok=True, locked=True, sold_out=True,
                           message='今日禮物名額已全數送出，感謝您的參與，請明日再來挑戰！')

        holy = random.random() < QIGUI_HOLY_PROB
        if not holy:
            session['qigui_played'] = True
            session['qigui_streak'] = 0
            conn.commit(); cur.close(); conn.close()
            outcome = 'laugh' if random.random() < 0.5 else 'yin'
            return jsonify(ok=True, outcome=outcome, streak=0, won=False, locked=True)

        streak = int(session.get('qigui_streak', 0)) + 1
        session['qigui_streak'] = streak

        if streak >= 3:
            cur.execute("""UPDATE qigui_daily_quota SET given_out = given_out + 1
                           WHERE quota_date=%s AND given_out < daily_limit
                           RETURNING given_out""", (today,))
            got = cur.fetchone()
            if not got:
                # 極端情況：兩人同時擲到最後一份，晚一步的人名額被搶走
                conn.commit(); cur.close(); conn.close()
                session['qigui_played'] = True
                return jsonify(ok=True, locked=True, sold_out=True,
                               message='差一點點！今日名額剛好在您擲出的瞬間發完，請明日再來。')
            code = _qigui_make_code(today)
            cur.execute("""INSERT INTO qigui_wins (win_code, quota_date, ip)
                           VALUES (%s,%s,%s)""", (code, today, _client_ip()))
            conn.commit(); cur.close(); conn.close()
            session['qigui_played'] = True
            session['qigui_won'] = True
            session['qigui_code'] = code
            return jsonify(ok=True, outcome='holy', streak=streak, won=True, code=code, locked=True)

        conn.commit(); cur.close(); conn.close()
        return jsonify(ok=True, outcome='holy', streak=streak, won=False, locked=False)
    except Exception as e:
        return jsonify(ok=False, error=str(e)), 500


@app.route('/api/admin/qigui/status', methods=['GET'])
def admin_qigui_status():
    """乞龜活動庫存總覽（僅 owner）：各日已發放/上限、中獎與領獎統計。"""
    if not is_admin():
        return jsonify(ok=False, error='未授權'), 401
    try:
        conn = get_db(); cur = conn.cursor()
        cur.execute("SELECT * FROM qigui_daily_quota ORDER BY quota_date")
        days = []
        for r in cur.fetchall():
            r = dict(r)
            r['quota_date'] = str(r['quota_date'])
            days.append(r)
        cur.execute("SELECT COUNT(*) AS c FROM qigui_wins")
        total_wins = cur.fetchone()['c']
        cur.execute("SELECT COUNT(*) AS c FROM qigui_wins WHERE claimed=TRUE")
        total_claimed = cur.fetchone()['c']
        cur.close(); conn.close()
        total_given = sum(d['given_out'] for d in days)
        total_limit = sum(d['daily_limit'] for d in days)
        return jsonify(ok=True, days=days, total_given=total_given, total_limit=total_limit,
                       total_wins=total_wins, total_claimed=total_claimed)
    except Exception as e:
        return jsonify(ok=False, error=str(e)), 500


@app.route('/api/admin/qigui/quota', methods=['PATCH'])
def admin_qigui_quota():
    """調整指定日期的禮物名額上限（僅 owner）。用於臨時追加/調整某天的庫存，
    不影響其他日期；若該日尚未建立名額列會自動建立。"""
    if not is_admin():
        return jsonify(ok=False, error='未授權'), 401
    data = request.get_json(force=True, silent=True) or {}
    date_str = (data.get('date') or '').strip()
    try:
        d = datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        return jsonify(ok=False, error='日期格式需為 YYYY-MM-DD'), 400
    try:
        new_limit = int(data.get('daily_limit'))
    except (TypeError, ValueError):
        return jsonify(ok=False, error='請提供正確的名額數字'), 400
    if new_limit < 0:
        return jsonify(ok=False, error='名額不可為負數'), 400
    try:
        conn = get_db(); cur = conn.cursor()
        cur.execute("""
            INSERT INTO qigui_daily_quota (quota_date, daily_limit, given_out)
            VALUES (%s,%s,0)
            ON CONFLICT (quota_date) DO UPDATE SET daily_limit = EXCLUDED.daily_limit
            RETURNING *
        """, (d, new_limit))
        row = dict(cur.fetchone())
        conn.commit(); cur.close(); conn.close()
        row['quota_date'] = str(row['quota_date'])
        return jsonify(ok=True, quota=row)
    except Exception as e:
        return jsonify(ok=False, error=str(e)), 500


@app.route('/api/admin/qigui/claim', methods=['POST'])
def admin_qigui_claim():
    """後台核銷中獎憑證（現場發放實體禮物時使用，避免同一組憑證被重複兌換）。"""
    if not is_admin():
        return jsonify(ok=False, error='未授權'), 401
    data = request.get_json(force=True, silent=True) or {}
    code = (data.get('code') or '').strip().upper()
    if not code:
        return jsonify(ok=False, error='請提供憑證編號'), 400
    try:
        conn = get_db(); cur = conn.cursor()
        cur.execute("SELECT * FROM qigui_wins WHERE win_code=%s", (code,))
        row = cur.fetchone()
        if not row:
            cur.close(); conn.close()
            return jsonify(ok=False, error='查無此憑證，請確認編號'), 404
        if row['claimed']:
            cur.close(); conn.close()
            return jsonify(ok=False, error=f"此憑證已於 {row['claimed_at']} 兌換過，不可重複兌換"), 400
        cur.execute("UPDATE qigui_wins SET claimed=TRUE, claimed_at=NOW() WHERE win_code=%s", (code,))
        conn.commit(); cur.close(); conn.close()
        return jsonify(ok=True, code=code)
    except Exception as e:
        return jsonify(ok=False, error=str(e)), 500


# ─── 抽獎工具：Meta 留言名單匯入 ────────────────────────────
class MetaAPIError(Exception):
    def __init__(self, message, status=502):
        super().__init__(message)
        self.status = status


def _meta_config(platform):
    token = (os.environ.get('META_PAGE_ACCESS_TOKEN')
             or os.environ.get('META_ACCESS_TOKEN') or '').strip()
    if platform == 'facebook':
        account_id = os.environ.get('META_FB_PAGE_ID', '').strip()
    elif platform == 'instagram':
        account_id = os.environ.get('META_IG_USER_ID', '').strip()
    else:
        raise MetaAPIError('不支援的社群平台', 400)
    return token, account_id


def _meta_graph_get(object_path, params=None):
    """呼叫 Meta Graph API；權杖只存在伺服器端，不回傳給前端。"""
    if not re.fullmatch(r'[A-Za-z0-9_:/.-]+', object_path or ''):
        raise MetaAPIError('Meta 資源編號格式不正確', 400)
    token = (os.environ.get('META_PAGE_ACCESS_TOKEN')
             or os.environ.get('META_ACCESS_TOKEN') or '').strip()
    if not token:
        raise MetaAPIError('Meta API 尚未設定', 503)
    version = os.environ.get('META_GRAPH_API_VERSION', 'v25.0').strip()
    if not re.fullmatch(r'v\d+\.\d+', version):
        version = 'v25.0'
    query = dict(params or {})
    query['access_token'] = token
    url = (f'https://graph.facebook.com/{version}/{object_path.lstrip("/")}?' +
           urllib.parse.urlencode(query))
    req = urllib.request.Request(url, headers={'Accept': 'application/json'})
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            return json.loads(resp.read().decode('utf-8'))
    except urllib.error.HTTPError as exc:
        try:
            payload = json.loads(exc.read().decode('utf-8', 'replace'))
            detail = ((payload.get('error') or {}).get('message') or '')
        except Exception:
            detail = ''
        if exc.code in (401, 403):
            message = 'Meta 授權已失效或權限不足'
        elif exc.code == 429:
            message = 'Meta API 使用量已達上限，請稍後再試'
        else:
            message = detail[:180] or f'Meta API 回應錯誤（HTTP {exc.code}）'
        raise MetaAPIError(message, 502) from exc
    except (urllib.error.URLError, TimeoutError) as exc:
        raise MetaAPIError('目前無法連線至 Meta API，請稍後再試', 502) from exc
    except (ValueError, TypeError) as exc:
        raise MetaAPIError('Meta API 回傳格式異常', 502) from exc


def _meta_fetch_comments(object_id, fields, max_items=1000):
    comments = []
    after = ''
    while len(comments) < max_items:
        params = {'fields': fields, 'limit': min(100, max_items - len(comments))}
        if after:
            params['after'] = after
        payload = _meta_graph_get(f'{object_id}/comments', params)
        page = payload.get('data') or []
        comments.extend(page)
        after = (((payload.get('paging') or {}).get('cursors') or {}).get('after') or '')
        if not page or not after:
            break
    return comments[:max_items], bool(after and len(comments) >= max_items)


def _meta_datetime(value):
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace('Z', '+00:00'))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
    except (TypeError, ValueError):
        return None


def _meta_required(platform):
    token, account_id = _meta_config(platform)
    if not token or not account_id:
        missing = []
        if not token:
            missing.append('META_PAGE_ACCESS_TOKEN')
        if not account_id:
            missing.append('META_FB_PAGE_ID' if platform == 'facebook' else 'META_IG_USER_ID')
        raise MetaAPIError('Meta 連線尚未完成設定：' + '、'.join(missing), 503)
    return account_id


@app.route('/api/lottery/meta/status')
def lottery_meta_status():
    if not is_admin():
        return jsonify(ok=False, error='請先登入潮旅管理後台'), 401
    token = bool((os.environ.get('META_PAGE_ACCESS_TOKEN')
                  or os.environ.get('META_ACCESS_TOKEN') or '').strip())
    return jsonify(ok=True, configured={
        'facebook': token and bool(os.environ.get('META_FB_PAGE_ID', '').strip()),
        'instagram': token and bool(os.environ.get('META_IG_USER_ID', '').strip())
    })


@app.route('/api/lottery/meta/posts')
def lottery_meta_posts():
    if not is_admin():
        return jsonify(ok=False, error='請先登入潮旅管理後台'), 401
    platform = (request.args.get('platform') or '').strip().lower()
    try:
        account_id = _meta_required(platform)
        if platform == 'facebook':
            fields = 'id,message,created_time,permalink_url'
            payload = _meta_graph_get(f'{account_id}/posts', {'fields': fields, 'limit': 25})
            posts = [{
                'id': row.get('id', ''),
                'text': (row.get('message') or '（無文字貼文）')[:180],
                'timestamp': row.get('created_time', ''),
                'url': row.get('permalink_url', '')
            } for row in (payload.get('data') or []) if row.get('id')]
        else:
            fields = 'id,caption,media_type,permalink,timestamp'
            payload = _meta_graph_get(f'{account_id}/media', {'fields': fields, 'limit': 25})
            posts = [{
                'id': row.get('id', ''),
                'text': (row.get('caption') or f'（{row.get("media_type", "貼文")}）')[:180],
                'timestamp': row.get('timestamp', ''),
                'url': row.get('permalink', '')
            } for row in (payload.get('data') or []) if row.get('id')]
        return jsonify(ok=True, platform=platform, posts=posts)
    except MetaAPIError as exc:
        return jsonify(ok=False, error=str(exc)), exc.status


@app.route('/api/lottery/meta/comments', methods=['POST'])
def lottery_meta_comments():
    if not is_admin():
        return jsonify(ok=False, error='請先登入潮旅管理後台'), 401
    data = request.get_json(force=True, silent=True) or {}
    platform = (data.get('platform') or '').strip().lower()
    object_id = (data.get('post_id') or '').strip()
    keyword = (data.get('keyword') or '').strip()
    cutoff_raw = (data.get('cutoff') or '').strip()
    cutoff = _meta_datetime(cutoff_raw)
    if not object_id or not re.fullmatch(r'[A-Za-z0-9_:-]{3,120}', object_id):
        return jsonify(ok=False, error='請選擇有效的活動貼文'), 400
    if cutoff_raw and not cutoff:
        return jsonify(ok=False, error='活動截止時間格式不正確'), 400
    try:
        _meta_required(platform)
        fields = ('id,message,created_time,from{id,name}' if platform == 'facebook'
                  else 'id,text,timestamp,username,from{id,username}')
        comments, truncated = _meta_fetch_comments(object_id, fields)
        participants = []
        seen = set()
        excluded_keyword = 0
        excluded_author = 0
        excluded_cutoff = 0
        for comment in comments:
            text = str(comment.get('message') or comment.get('text') or '')
            comment_time = _meta_datetime(comment.get('created_time') or comment.get('timestamp'))
            if cutoff and comment_time and comment_time > cutoff:
                excluded_cutoff += 1
                continue
            if keyword and keyword.casefold() not in text.casefold():
                excluded_keyword += 1
                continue
            author = comment.get('from') or {}
            if platform == 'instagram':
                username = str(author.get('username') or comment.get('username') or '').strip().lstrip('@')
                source_id = str(author.get('id') or username).strip()
                name = f'@{username}' if username else ''
            else:
                source_id = str(author.get('id') or '').strip()
                name = str(author.get('name') or '').strip()
            if not source_id or not name:
                excluded_author += 1
                continue
            dedupe_key = f'{platform}:{source_id.casefold()}'
            if dedupe_key in seen:
                continue
            seen.add(dedupe_key)
            participants.append({
                'source': platform,
                'source_id': source_id,
                'name': name,
                'comment_id': str(comment.get('id') or ''),
                'comment': text[:240]
            })
        return jsonify(ok=True, platform=platform, participants=participants, stats={
            'comments': len(comments),
            'eligible': len(participants),
            'duplicates': max(0, len(comments) - excluded_keyword - excluded_author - excluded_cutoff - len(participants)),
            'keyword_excluded': excluded_keyword,
            'missing_author': excluded_author,
            'after_cutoff': excluded_cutoff,
            'truncated': truncated
        })
    except MetaAPIError as exc:
        return jsonify(ok=False, error=str(exc)), exc.status


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
            # 這支端點不需驗證即可讀取，例外原文會帶出主機、帳號與資料庫名稱。
            # 詳細內容留在 Railway log，對外只回一個代碼。
            print(f'[HEALTH] 資料庫連線失敗：{e}')
            db_error = 'connection_failed'
            db_status = 'error'
    release_sha = (os.environ.get('RAILWAY_GIT_COMMIT_SHA')
                   or os.environ.get('SOURCE_VERSION') or '').strip()
    return jsonify(ok=db_status == 'connected' and table_exists,
                   db_url_set=bool(db_url), db_status=db_status,
                   db_error=db_error, table_contacts=table_exists,
                   release_sha=release_sha[:40],
                   environment=os.environ.get('RAILWAY_ENVIRONMENT_NAME', '').strip())


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

        grouped = {
            # 套裝行程
            'featured': [], '2d1n': [], '3d2n': [], '4d3n': [],
            # 單一行程（依海域）
            'north-sea': [], 'east-sea': [], 'south-sea': [], 'main-island': [],
        }
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
               i18n, sort_order, is_active)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            RETURNING id
        """, (
            Json(data.get('tabs', ['featured'])),
            data.get('badge_text', ''), data.get('badge_class', ''),
            data.get('image_url', ''), data.get('title', '新行程'),
            data.get('description', ''), data.get('suitable_for', ''),
            data.get('duration', ''), data.get('price_display', ''),
            data.get('is_hero', False),
            Json(data.get('prices', [])), Json(data.get('modal_data', {})),
            Json(data.get('i18n', {})),
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
              is_hero=%s, prices=%s, modal_data=%s, i18n=COALESCE(%s, i18n),
              sort_order=%s, is_active=%s, updated_at=NOW()
            WHERE id=%s
        """, (
            Json(data.get('tabs', ['featured'])),
            data.get('badge_text', ''), data.get('badge_class', ''),
            data.get('image_url', ''), data.get('title', ''),
            data.get('description', ''), data.get('suitable_for', ''),
            data.get('duration', ''), data.get('price_display', ''),
            data.get('is_hero', False),
            Json(data.get('prices', [])), Json(data.get('modal_data', {})),
            Json(data['i18n']) if 'i18n' in data else None,
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
def _gmail_api_send(sender, recipient, msg):
    """透過 Gmail API（HTTPS）寄信，繞過 Railway 封鎖的 SMTP 埠。
    需環境變數 GMAIL_SERVICE_ACCOUNT_JSON（服務帳號金鑰 JSON 全文），且該服務帳號已於
    Google Workspace 後台完成「網域範圍委派」授權 gmail.send。sender 為被代寄的信箱。
    回傳 (ok: bool, detail: str)。"""
    raw_json = os.environ.get('GMAIL_SERVICE_ACCOUNT_JSON', '').strip()
    if not raw_json:
        return False, 'GMAIL_SERVICE_ACCOUNT_JSON 未設定'
    try:
        from google.oauth2 import service_account
        from googleapiclient.discovery import build
        info = json.loads(raw_json)
        creds = service_account.Credentials.from_service_account_info(
            info, scopes=['https://www.googleapis.com/auth/gmail.send'], subject=sender)
        gmail = build('gmail', 'v1', credentials=creds, cache_discovery=False)
        raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
        gmail.users().messages().send(userId='me', body={'raw': raw}).execute()
        return True, 'gmail-api'
    except Exception as e:
        return False, f'Gmail API 失敗：{e}'


def _deliver(sender, recipient, msg):
    """統一寄信入口：優先 Gmail API（HTTPS，繞過 SMTP 封鎖），否則退回 SMTP 多埠。
    回傳 (ok: bool, detail: str)。"""
    if os.environ.get('GMAIL_SERVICE_ACCOUNT_JSON', '').strip():
        ok, detail = _gmail_api_send(sender, recipient, msg)
        if ok:
            return True, detail
        gmail_err = detail
    else:
        gmail_err = None
    password = os.environ.get('EMAIL_PASS', '')
    if password:
        ok, detail = _smtp_send(sender, password, recipient, msg)
        if ok:
            return True, detail
        return False, (f'Gmail API →{gmail_err}；SMTP →{detail}' if gmail_err else detail)
    return False, (gmail_err or '未設定寄信方式（GMAIL_SERVICE_ACCOUNT_JSON 或 EMAIL_PASS）')


def _smtp_send(sender, password, recipient, msg):
    """寄信：依序嘗試埠。優先用 SMTP_PORT（若有設），再退到 465(SSL)、587(STARTTLS)。
    某些主機（如 Railway 對 GoDaddy 465）會逾時，改用 587 STARTTLS 通常可通。
    回傳 (ok: bool, detail: str)。"""
    host = os.environ.get('SMTP_HOST', 'smtpout.secureserver.net')
    forced = os.environ.get('SMTP_PORT')
    candidates = []
    if forced and forced.isdigit():
        candidates.append(int(forced))
    for p in (465, 587):
        if p not in candidates:
            candidates.append(p)
    errors = []
    for port in candidates:
        try:
            if port == 465:
                with smtplib.SMTP_SSL(host, port, timeout=15) as s:
                    s.login(sender, password)
                    s.sendmail(sender, recipient, msg.as_string())
            else:
                with smtplib.SMTP(host, port, timeout=15) as s:
                    s.ehlo(); s.starttls(); s.ehlo()
                    s.login(sender, password)
                    s.sendmail(sender, recipient, msg.as_string())
            return True, f'{host}:{port}'
        except Exception as e:
            errors.append(f'{host}:{port} → {e}')
    return False, ' ; '.join(errors)


# ─── LINE Messaging API 通知 ─────────────────────────────────
# 需環境變數：LINE_CHANNEL_ACCESS_TOKEN（頻道存取權杖）、LINE_CHANNEL_SECRET（webhook 驗簽）、
# LINE_OWNER_USER_ID（接收通知的老闆 userId，向官方帳號傳「綁定通知」即可由機器人回覆取得）。
# 走 HTTPS（api.line.me），不受 Railway SMTP 封鎖影響；全部失敗不影響訂單/表單儲存。

def _line_api_call(endpoint, payload):
    """POST 到 LINE Messaging API，回傳 (ok: bool, detail: str)。"""
    token = os.environ.get('LINE_CHANNEL_ACCESS_TOKEN', '').strip()
    if not token:
        return False, 'LINE_CHANNEL_ACCESS_TOKEN 未設定'
    req = urllib.request.Request(
        f'https://api.line.me/v2/bot/{endpoint}',
        data=json.dumps(payload).encode('utf-8'),
        headers={'Content-Type': 'application/json', 'Authorization': f'Bearer {token}'},
        method='POST')
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return True, f'HTTP {resp.status}'
    except urllib.error.HTTPError as e:
        try:
            detail = e.read().decode('utf-8', 'replace')[:300]
        except Exception:
            detail = ''
        return False, f'HTTP {e.code}：{detail}'
    except Exception as e:
        return False, str(e)


def send_line_notify(text):
    """推播文字訊息給老闆（LINE_OWNER_USER_ID）。未設定即跳過，失敗只記 log。"""
    owner = os.environ.get('LINE_OWNER_USER_ID', '').strip()
    if not owner or not os.environ.get('LINE_CHANNEL_ACCESS_TOKEN', '').strip():
        print('[LINE] 未設定 LINE_CHANNEL_ACCESS_TOKEN / LINE_OWNER_USER_ID，跳過 LINE 通知')
        return False, '未設定'
    ok, detail = _line_api_call('message/push', {
        'to': owner, 'messages': [{'type': 'text', 'text': text[:4900]}]})
    print(f'[LINE] 推播{"成功" if ok else "失敗"}（{detail}）')
    return ok, detail


def _line_reply(reply_token, text):
    return _line_api_call('message/reply', {
        'replyToken': reply_token, 'messages': [{'type': 'text', 'text': text[:4900]}]})


def _line_get_profile(user_id):
    """查使用者顯示名稱；失敗回空字串（例如未加好友）。"""
    token = os.environ.get('LINE_CHANNEL_ACCESS_TOKEN', '').strip()
    if not token or not user_id:
        return ''
    req = urllib.request.Request(
        f'https://api.line.me/v2/bot/profile/{user_id}',
        headers={'Authorization': f'Bearer {token}'})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return (json.loads(resp.read().decode('utf-8')) or {}).get('displayName', '')
    except Exception:
        return ''


# ─── 澎湖百旅會員：註冊、一次性登入、LINE 綁定與會員中心 ────────
def _member_code_hash(member_id, purpose, code):
    secret = str(app.secret_key).encode('utf-8')
    raw = f'{member_id}:{purpose}:{code}'.encode('utf-8')
    return hmac.new(secret, raw, hashlib.sha256).hexdigest()


def _send_member_code_email(member, code):
    sender = os.environ.get('EMAIL_USER', '').strip()
    if not sender:
        return False, 'EMAIL_USER 未設定'
    msg = MIMEMultipart()
    msg['From'] = f'潮旅國際旅行社 <{sender}>'
    msg['To'] = member['email']
    msg['Subject'] = '潮旅・澎湖百旅會員登入驗證碼'
    msg.attach(MIMEText(
        f"{member['name']} 您好：\n\n您的澎湖百旅會員登入驗證碼是：{code}\n"
        "驗證碼 10 分鐘內有效。若非本人操作，請忽略此信。\n\n潮旅國際旅行社",
        'plain', 'utf-8'))
    return _deliver(sender, member['email'], msg)


def _member_row(member_id):
    if not member_id:
        return None
    conn = get_db(); cur = conn.cursor()
    cur.execute("SELECT * FROM members WHERE id=%s AND is_active=TRUE", (member_id,))
    row = cur.fetchone(); cur.close(); conn.close()
    return row


@app.route('/api/member/register', methods=['POST'])
def member_register():
    data = request.get_json(force=True, silent=True) or {}
    name = (data.get('name') or '').strip()[:100]
    phone = (data.get('phone') or '').strip()[:30]
    normalized = normalize_phone(phone)
    email = (data.get('email') or '').strip().lower()[:200]
    if not data.get('consent'):
        return jsonify(ok=False, error='請先閱讀並同意會員個資告知事項'), 400
    if not name or len(normalized) < 8 or not valid_email(email):
        return jsonify(ok=False, error='請填寫姓名、有效手機與 Email'), 400
    birth_month = data.get('birth_month')
    try:
        birth_month = int(birth_month) if birth_month not in (None, '') else None
        if birth_month is not None and not 1 <= birth_month <= 12:
            raise ValueError
    except (TypeError, ValueError):
        return jsonify(ok=False, error='生日月份需為 1–12'), 400
    # 不論這組手機／Email 是否已經是會員，一律回相同訊息並寄出驗證碼，
    # 避免用註冊端點反查某人是不是會員（登入端點已經這樣做，兩邊必須一致）。
    # 同時註冊當下不再直接發 session：必須收得到信、輸入驗證碼才算完成，
    # 否則任何人都能拿別人的 Email 開帳號並立刻取得登入狀態。
    def _generic():
        return jsonify(ok=True, verify_required=True,
                       message='我們已寄出 10 分鐘有效的驗證碼，請至 Email 收信後輸入以完成登入')
    try:
        conn = get_db(); cur = conn.cursor()
        cur.execute("""SELECT * FROM members
                       WHERE (LOWER(email)=%s OR phone_normalized=%s) AND is_active=TRUE
                       ORDER BY (LOWER(email)=%s) DESC LIMIT 1""",
                    (email, normalized, email))
        existing = cur.fetchone()
        if existing:
            _issue_member_login_code(conn, cur, existing)
            cur.close(); conn.close()
            return _generic()
        member_id, member_no = next_member_no(cur)
        cur.execute("""
            INSERT INTO members
              (id,member_no,name,phone,phone_normalized,email,birth_month,consent_at)
            VALUES (%s,%s,%s,%s,%s,%s,%s,NOW()) RETURNING *
        """, (member_id, member_no, name, phone, normalized, email, birth_month))
        member = cur.fetchone()
        write_audit(cur, 'create', '會員', member_no, 1, 0, '前台會員註冊')
        conn.commit()
        _issue_member_login_code(conn, cur, member)
        cur.close(); conn.close()
        return _generic()
    except psycopg2.errors.UniqueViolation:
        # 併發下兩個請求同時建立同一組資料才會走到這裡；仍然不能透露結果。
        try: conn.rollback(); cur.close(); conn.close()
        except Exception: pass
        return _generic()
    except Exception as exc:
        print(f'[MEMBER REGISTER] {exc}')
        return jsonify(ok=False, error='註冊失敗，請稍後再試'), 500


def _issue_member_login_code(conn, cur, member):
    """發一組 10 分鐘有效的登入碼，並寄到「會員檔案上的」Email。

    刻意不寄到請求輸入的信箱：否則只要知道別人的手機或 Email，
    就能把對方的登入碼寄到自己信箱。每小時上限 5 次。
    """
    cur.execute("""SELECT COUNT(*) AS n FROM member_auth_codes
                   WHERE member_id=%s AND purpose='login'
                     AND created_at > NOW() - INTERVAL '1 hour'""", (member['id'],))
    if int(cur.fetchone()['n'] or 0) >= 5:
        return False
    code = f'{random.SystemRandom().randrange(100000, 1000000)}'
    cur.execute("""
        INSERT INTO member_auth_codes (member_id,purpose,code_hash,expires_at)
        VALUES (%s,'login',%s,NOW()+INTERVAL '10 minutes')
    """, (member['id'], _member_code_hash(member['id'], 'login', code)))
    conn.commit()
    ok, detail = _send_member_code_email(member, code)
    if not ok:
        print(f'[MEMBER LOGIN EMAIL] {detail}')
    return True


@app.route('/api/member/login/request', methods=['POST'])
def member_login_request():
    data = request.get_json(force=True, silent=True) or {}
    email = (data.get('email') or '').strip().lower()
    # 不論帳號是否存在都回相同訊息，避免枚舉會員 Email。
    try:
        conn = get_db(); cur = conn.cursor()
        cur.execute("SELECT * FROM members WHERE LOWER(email)=%s AND is_active=TRUE", (email,))
        member = cur.fetchone()
        if member:
            _issue_member_login_code(conn, cur, member)
        cur.close(); conn.close()
    except Exception as exc:
        print(f'[MEMBER LOGIN REQUEST] {exc}')
    return jsonify(ok=True, message='如果此 Email 已加入，我們已寄出 10 分鐘有效的驗證碼')


@app.route('/api/member/login/verify', methods=['POST'])
def member_login_verify():
    data = request.get_json(force=True, silent=True) or {}
    email = (data.get('email') or '').strip().lower()
    code = re.sub(r'\D', '', str(data.get('code') or ''))[:6]
    if len(code) != 6:
        return jsonify(ok=False, error='驗證碼格式錯誤'), 400
    try:
        conn = get_db(); cur = conn.cursor()
        cur.execute("SELECT * FROM members WHERE LOWER(email)=%s AND is_active=TRUE", (email,))
        member = cur.fetchone()
        if not member:
            cur.close(); conn.close()
            return jsonify(ok=False, error='驗證碼錯誤或已過期'), 401
        cur.execute("""
            SELECT * FROM member_auth_codes WHERE member_id=%s AND purpose='login'
              AND used_at IS NULL AND expires_at>NOW() AND attempts<5
            ORDER BY created_at DESC LIMIT 1 FOR UPDATE
        """, (member['id'],))
        token = cur.fetchone()
        if not token or not hmac.compare_digest(
                token['code_hash'], _member_code_hash(member['id'], 'login', code)):
            if token:
                cur.execute("UPDATE member_auth_codes SET attempts=attempts+1 WHERE id=%s", (token['id'],))
                conn.commit()
            cur.close(); conn.close()
            return jsonify(ok=False, error='驗證碼錯誤或已過期'), 401
        cur.execute("UPDATE member_auth_codes SET used_at=NOW() WHERE id=%s", (token['id'],))
        conn.commit(); cur.close(); conn.close()
        session['member_id'] = member['id']
        return jsonify(ok=True, member=public_member(member))
    except Exception as exc:
        print(f'[MEMBER LOGIN VERIFY] {exc}')
        return jsonify(ok=False, error='登入失敗'), 500


@app.route('/api/member/logout', methods=['POST'])
def member_logout():
    session.pop('member_id', None)
    return jsonify(ok=True)


@app.route('/api/member/me')
def member_me():
    member_id = session.get('member_id')
    if not member_id:
        return jsonify(ok=False, error='尚未登入'), 401
    try:
        conn = get_db(); cur = conn.cursor()
        cur.execute("SELECT * FROM members WHERE id=%s AND is_active=TRUE", (member_id,))
        member = cur.fetchone()
        if not member:
            cur.close(); conn.close()
            return jsonify(ok=False, error='尚未登入'), 401
        cur.execute("""SELECT id,tour_name,tour_category,departure_date,status,counts_trip,
                              points_awarded,notes FROM member_trips WHERE member_id=%s
                       ORDER BY departure_date DESC NULLS LAST,id DESC LIMIT 100""", (member_id,))
        trips = []
        for row in cur.fetchall():
            row = dict(row)
            if row.get('departure_date'): row['departure_date'] = str(row['departure_date'])
            trips.append(row)
        cur.execute("""SELECT delta,source,redemption,created_at FROM member_points
                       WHERE member_id=%s ORDER BY created_at DESC LIMIT 100""", (member_id,))
        points = []
        for row in cur.fetchall():
            row = dict(row); row['created_at'] = str(row.get('created_at') or '')
            points.append(row)
        past_names = [row['tour_name'] for row in trips]
        cur.execute("""SELECT id,title,description,image_url,price_display FROM tours
                       WHERE is_active=TRUE AND NOT (title=ANY(%s))
                       ORDER BY is_hero DESC,sort_order,id LIMIT 3""", (past_names or [''],))
        recommendations = [dict(row) for row in cur.fetchall()]
        cur.close(); conn.close()
        return jsonify(ok=True, member=public_member(member), trips=trips, points=points,
                       recommendations=recommendations, points_per_trip=points_per_trip(),
                       levels=[{'trips': t, 'name': n} for t, n in member_levels()])
    except Exception as exc:
        print(f'[MEMBER ME] {exc}')
        return jsonify(ok=False, error='讀取會員資料失敗'), 500


@app.route('/api/member/line-bind-code', methods=['POST'])
def member_line_bind_code():
    member = _member_row(session.get('member_id'))
    if not member:
        return jsonify(ok=False, error='尚未登入'), 401
    try:
        code = f'{random.SystemRandom().randrange(100000, 1000000)}'
        conn = get_db(); cur = conn.cursor()
        cur.execute("""INSERT INTO member_auth_codes (member_id,purpose,code_hash,expires_at)
                       VALUES (%s,'line_bind',%s,NOW()+INTERVAL '10 minutes')""",
                    (member['id'], _member_code_hash(member['id'], 'line_bind', code)))
        conn.commit(); cur.close(); conn.close()
        return jsonify(ok=True, code=code, expires_minutes=10,
                       instruction=f'請到潮旅官方 LINE 傳送：綁定會員 {code}')
    except Exception:
        return jsonify(ok=False, error='無法建立綁定碼'), 500


def _sync_completed_order_trip(cur, source_type, source_ref, phone, tour_name,
                               departure_date, order_status, counts_trip=True):
    """依訂單狀態同步會員旅次；只有 completed 且 counts_trip 為真才計入累積旅次。

    整段以 SAVEPOINT 包住：會員同步是附加功能，任何失敗都只記 log，
    絕不能讓「改訂單狀態」這個核心訂位作業失敗（2026-07 諮詢表單事故的教訓）。
    注意 ON CONFLICT 不覆寫 counts_trip，客服在後台的人工判定優先於自動同步。

    回傳 dict：{'member_id':…, 'notify':(line_user_id, 文字) 或 None}。
    LINE 推播刻意不在這裡發送——那是十幾秒的網路呼叫，放在交易裡會一直佔著
    訂單的列鎖。改由呼叫端在 commit 之後再送。"""
    if not source_ref:
        return None
    normalized = normalize_phone(phone)
    if not normalized:
        return None
    cur.execute("SAVEPOINT member_trip_sync")
    try:
        cur.execute("""SELECT id,name,line_user_id,trip_count FROM members
                       WHERE phone_normalized=%s AND is_active=TRUE""", (normalized,))
        member = cur.fetchone()
        if not member:
            cur.execute("RELEASE SAVEPOINT member_trip_sync")
            return None
        # 這筆訂單先前若已同步過，記下原本掛在誰身上、原本什麼狀態。
        # 訂單聯絡電話改綁另一位會員時，旅次必須跟著搬，否則兩邊的累積旅次都會失準。
        cur.execute("""SELECT id,member_id,status FROM member_trips
                       WHERE source_type=%s AND source_ref=%s FOR UPDATE""",
                    (source_type, source_ref))
        previous = cur.fetchone()
        previous_member_id = previous['member_id'] if previous else None
        previous_status = previous['status'] if previous else None
        before_level = level_for_trips(member['trip_count'])
        trip_status = ('completed' if order_status == 'completed' else
                       'cancelled' if order_status == 'cancelled' else 'planned')
        cur.execute("""
            INSERT INTO member_trips
              (member_id,source_type,source_ref,tour_name,departure_date,status,counts_trip,notes)
            VALUES (%s,%s,%s,%s,%s,%s,%s,'由訂單狀態自動同步')
            ON CONFLICT (source_type,source_ref) DO UPDATE SET
              member_id=EXCLUDED.member_id,
              status=EXCLUDED.status,tour_name=EXCLUDED.tour_name,
              departure_date=EXCLUDED.departure_date,updated_at=NOW()
            RETURNING id
        """, (member['id'], source_type, source_ref, tour_name, departure_date,
              trip_status, bool(counts_trip)))
        trip_id = cur.fetchone()['id']
        moved = previous_member_id is not None and previous_member_id != member['id']
        if moved:
            # 點數帳本要跟著旅次走，否則 sync_trip_points 會誤以為已經給過點，
            # 新會員拿不到、舊會員也退不掉。
            cur.execute("UPDATE member_points SET member_id=%s WHERE trip_id=%s",
                        (member['id'], trip_id))
        # 認列狀態變動後同步點數帳本（冪等），再由帳本重算餘額與旅次數
        sync_trip_points(cur, trip_id)
        trips, _points = recalculate_member(cur, member['id'])
        if moved:
            recalculate_member(cur, previous_member_id)
        notify = None
        if (member['line_user_id'] and trip_status == 'completed'
                and previous_status != 'completed' and bool(counts_trip)):
            after_level = level_for_trips(trips)
            text = (f"{member['name']} 您好，旅程「{tour_name}」已完成認列，"
                    f"目前累積 {trips} 次澎湖旅程。")
            if after_level != before_level:
                text += f"\n恭喜升等為「{after_level}」！"
            notify = (member['line_user_id'], text)
        cur.execute("RELEASE SAVEPOINT member_trip_sync")
        return {'member_id': member['id'], 'notify': notify, 'moved_from': previous_member_id if moved else None}
    except Exception as exc:
        cur.execute("ROLLBACK TO SAVEPOINT member_trip_sync")
        cur.execute("RELEASE SAVEPOINT member_trip_sync")
        print(f'[MEMBER TRIP SYNC] {source_type}/{source_ref} 同步失敗，訂單更新不受影響：{exc}')
        return None


@app.route('/api/admin/members', methods=['GET', 'POST'])
def admin_members():
    if not has_role('orders'):
        return jsonify(ok=False, error='未授權'), 401
    if request.method == 'GET':
        query = (request.args.get('q') or '').strip()
        try:
            conn = get_db(); cur = conn.cursor()
            like = f'%{query}%'
            cur.execute("""SELECT * FROM members WHERE
                           (%s='' OR member_no ILIKE %s OR name ILIKE %s OR phone ILIKE %s OR email ILIKE %s)
                           ORDER BY joined_at DESC LIMIT 300""", (query, like, like, like, like))
            members = []
            for row in cur.fetchall():
                public = public_member(row)
                public.update({'phone': row['phone'], 'notes': row.get('notes') or '',
                               'is_active': bool(row.get('is_active'))})
                members.append(public)
            cur.close(); conn.close()
            return jsonify(ok=True, members=members)
        except Exception as exc:
            print(f'[ADMIN_MEMBERS] {exc}')
        return jsonify(ok=False, error='會員資料讀取或建立失敗'), 500
    data = request.get_json(force=True, silent=True) or {}
    name = (data.get('name') or '').strip()[:100]
    phone = (data.get('phone') or '').strip()[:30]
    normalized = normalize_phone(phone)
    email = (data.get('email') or '').strip().lower()[:200]
    if not name or len(normalized) < 8 or not valid_email(email):
        return jsonify(ok=False, error='姓名、手機、Email 格式不完整'), 400
    try:
        conn = get_db(); cur = conn.cursor(); member_id, member_no = next_member_no(cur)
        cur.execute("""INSERT INTO members
          (id,member_no,name,phone,phone_normalized,email,birth_month,notes,consent_at)
          VALUES (%s,%s,%s,%s,%s,%s,%s,%s,NOW()) RETURNING *""",
                    (member_id, member_no, name, phone, normalized, email,
                     data.get('birth_month') or None, (data.get('notes') or '')[:1000]))
        member = cur.fetchone()
        write_audit(cur, 'create', '會員', member_no, 1, 0, '後台建立會員')
        conn.commit(); cur.close(); conn.close()
        return jsonify(ok=True, member=public_member(member)), 201
    except psycopg2.errors.UniqueViolation:
        try: conn.rollback(); cur.close(); conn.close()
        except Exception: pass
        return jsonify(ok=False, error='手機或 Email 已存在'), 409
    except Exception as exc:
        print(f'[ADMIN_MEMBERS] {exc}')
        return jsonify(ok=False, error='會員資料讀取或建立失敗'), 500


@app.route('/api/admin/members/<int:member_id>')
def admin_member_detail(member_id):
    if not has_role('orders'):
        return jsonify(ok=False, error='未授權'), 401
    try:
        conn = get_db(); cur = conn.cursor()
        cur.execute("SELECT * FROM members WHERE id=%s", (member_id,)); member = cur.fetchone()
        if not member:
            cur.close(); conn.close(); return jsonify(ok=False, error='找不到會員'), 404
        cur.execute("SELECT * FROM member_trips WHERE member_id=%s ORDER BY departure_date DESC NULLS LAST,id DESC",
                    (member_id,))
        trips = []
        for row in cur.fetchall():
            row = dict(row)
            for key in ('departure_date', 'created_at', 'updated_at'):
                if row.get(key): row[key] = str(row[key])
            trips.append(row)
        cur.execute("SELECT * FROM member_points WHERE member_id=%s ORDER BY created_at DESC", (member_id,))
        points = []
        for row in cur.fetchall():
            row = dict(row); row['created_at'] = str(row.get('created_at') or '')
            points.append(row)
        detail = public_member(member)
        detail.update({'phone': member['phone'], 'notes': member.get('notes') or '',
                       'is_active': bool(member.get('is_active'))})
        cur.close(); conn.close()
        return jsonify(ok=True, member=detail, trips=trips, points=points)
    except Exception as exc:
        print(f'[ADMIN_MEMBER_DETAIL] {exc}')
        return jsonify(ok=False, error='讀取會員明細失敗'), 500


@app.route('/api/admin/members/<int:member_id>/trips', methods=['POST'])
def admin_member_add_trip(member_id):
    if not has_role('orders'):
        return jsonify(ok=False, error='未授權'), 401
    data = request.get_json(force=True, silent=True) or {}
    tour_name = (data.get('tour_name') or '').strip()[:180]
    status = (data.get('status') or 'planned').strip()
    if not tour_name or status not in {'planned', 'completed', 'cancelled'}:
        return jsonify(ok=False, error='行程名稱或狀態錯誤'), 400
    try:
        conn = get_db(); cur = conn.cursor()
        cur.execute("SELECT member_no FROM members WHERE id=%s FOR UPDATE", (member_id,))
        member = cur.fetchone()
        if not member:
            cur.close(); conn.close(); return jsonify(ok=False, error='找不到會員'), 404
        cur.execute("""INSERT INTO member_trips
          (member_id,source_type,source_ref,tour_name,tour_category,departure_date,status,counts_trip,notes)
          VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id""",
                    (member_id, (data.get('source_type') or 'manual')[:30],
                     (data.get('source_ref') or None), tour_name,
                     (data.get('tour_category') or '')[:60], data.get('departure_date') or None,
                     status, bool(data.get('counts_trip', True)), (data.get('notes') or '')[:1000]))
        trip_id = cur.fetchone()['id']
        sync_trip_points(cur, trip_id)
        trips, points = recalculate_member(cur, member_id)
        write_audit(cur, 'create', '會員旅次', member['member_no'], 1, 0, tour_name)
        conn.commit(); cur.close(); conn.close()
        return jsonify(ok=True, trip_id=trip_id, trip_count=trips, points_balance=points)
    except psycopg2.errors.UniqueViolation:
        try: conn.rollback(); cur.close(); conn.close()
        except Exception: pass
        return jsonify(ok=False, error='此來源訂單已認列'), 409
    except Exception as exc:
        print(f'[ADMIN_MEMBER_ADD_TRIP] {exc}')
        return jsonify(ok=False, error='新增旅次失敗'), 500


@app.route('/api/admin/member-trips/<int:trip_id>', methods=['PATCH'])
def admin_member_update_trip(trip_id):
    if not has_role('orders'):
        return jsonify(ok=False, error='未授權'), 401
    data = request.get_json(force=True, silent=True) or {}
    status = (data.get('status') or '').strip()
    if status not in {'planned', 'completed', 'cancelled'}:
        return jsonify(ok=False, error='旅次狀態錯誤'), 400
    try:
        conn = get_db(); cur = conn.cursor()
        cur.execute("""SELECT t.*,m.member_no,m.name,m.line_user_id,m.trip_count
                       FROM member_trips t JOIN members m ON m.id=t.member_id
                       WHERE t.id=%s FOR UPDATE OF t,m""", (trip_id,))
        trip = cur.fetchone()
        if not trip:
            cur.close(); conn.close(); return jsonify(ok=False, error='找不到旅次'), 404
        before_level = level_for_trips(trip['trip_count'])
        cur.execute("""UPDATE member_trips SET status=%s,counts_trip=%s,notes=%s,updated_at=NOW()
                       WHERE id=%s""", (status, bool(data.get('counts_trip', trip['counts_trip'])),
                                        (data.get('notes', trip['notes']) or '')[:1000], trip_id))
        sync_trip_points(cur, trip_id)
        trips, points = recalculate_member(cur, trip['member_id'])
        after_level = level_for_trips(trips)
        write_audit(cur, 'update', '會員旅次', trip['member_no'], 1, 0,
                    f"{trip['status']} → {status}; {trip['tour_name']}")
        conn.commit(); cur.close(); conn.close()
        if trip.get('line_user_id') and status == 'completed' and trip['status'] != 'completed':
            message = f"{trip['name']} 您好，旅程「{trip['tour_name']}」已完成認列，目前累積 {trips} 次澎湖旅程。"
            if after_level != before_level:
                message += f"\n恭喜升等為「{after_level}」！"
            _line_api_call('message/push', {'to': trip['line_user_id'],
                                            'messages': [{'type': 'text', 'text': message}]})
        return jsonify(ok=True, trip_count=trips, points_balance=points, level=after_level)
    except Exception as exc:
        print(f'[ADMIN_MEMBER_UPDATE_TRIP] {exc}')
        return jsonify(ok=False, error='更新旅次失敗'), 500


@app.route('/api/admin/members/<int:member_id>/points', methods=['POST'])
def admin_member_adjust_points(member_id):
    if not has_role('orders'):
        return jsonify(ok=False, error='未授權'), 401
    data = request.get_json(force=True, silent=True) or {}
    try:
        delta = int(data.get('delta'))
    except (TypeError, ValueError):
        return jsonify(ok=False, error='點數增減必須是整數'), 400
    source = (data.get('source') or '').strip()[:100]
    if not delta or not source:
        return jsonify(ok=False, error='請填寫點數與來源'), 400
    try:
        conn = get_db(); cur = conn.cursor()
        cur.execute("SELECT member_no,points_balance FROM members WHERE id=%s FOR UPDATE", (member_id,))
        member = cur.fetchone()
        if not member:
            cur.close(); conn.close(); return jsonify(ok=False, error='找不到會員'), 404
        if int(member['points_balance'] or 0) + delta < 0:
            cur.close(); conn.close(); return jsonify(ok=False, error='點數餘額不可為負數'), 400
        cur.execute("""INSERT INTO member_points (member_id,delta,source,redemption)
                       VALUES (%s,%s,%s,%s)""", (member_id, delta, source,
                                                   (data.get('redemption') or '')[:500]))
        trips, points = recalculate_member(cur, member_id)
        write_audit(cur, 'update', '會員點數', member['member_no'], 1, 0, f'{delta:+d} {source}')
        conn.commit(); cur.close(); conn.close()
        return jsonify(ok=True, points_balance=points)
    except Exception as exc:
        print(f'[ADMIN_MEMBER_ADJUST_POINTS] {exc}')
        return jsonify(ok=False, error='調整點數失敗'), 500


@app.route('/api/admin/members/merge', methods=['POST'])
def admin_member_merge():
    if not is_admin():
        return jsonify(ok=False, error='僅管理者可合併會員'), 401
    data = request.get_json(force=True, silent=True) or {}
    try:
        source_id, target_id = int(data.get('source_id')), int(data.get('target_id'))
        if source_id == target_id: raise ValueError
    except (TypeError, ValueError):
        return jsonify(ok=False, error='來源與目標會員不正確'), 400
    try:
        conn = get_db(); cur = conn.cursor()
        # 一律依 id 由小到大鎖定。若不固定順序，兩個 source/target 剛好相反的
        # 合併同時進來就可能互相等待而 deadlock。
        first, second = sorted((source_id, target_id))
        cur.execute("SELECT id,member_no,line_user_id FROM members WHERE id=%s FOR UPDATE", (first,))
        rows = {row['id']: row for row in cur.fetchall()}
        cur.execute("SELECT id,member_no,line_user_id FROM members WHERE id=%s FOR UPDATE", (second,))
        rows.update({row['id']: row for row in cur.fetchall()})
        if len(rows) != 2:
            cur.close(); conn.close(); return jsonify(ok=False, error='找不到來源或目標會員'), 404
        cur.execute("UPDATE member_trips SET member_id=%s WHERE member_id=%s", (target_id, source_id))
        cur.execute("UPDATE member_points SET member_id=%s WHERE member_id=%s", (target_id, source_id))
        if not rows[target_id].get('line_user_id') and rows[source_id].get('line_user_id'):
            cur.execute("UPDATE members SET line_user_id=%s WHERE id=%s",
                        (rows[source_id]['line_user_id'], target_id))
        cur.execute("DELETE FROM members WHERE id=%s", (source_id,))
        recalculate_member(cur, target_id)
        write_audit(cur, 'merge', '會員', rows[target_id]['member_no'], 2, 0,
                    f"合併來源 {rows[source_id]['member_no']}")
        conn.commit(); cur.close(); conn.close()
        return jsonify(ok=True, target_id=target_id)
    except psycopg2.errors.UniqueViolation:
        try: conn.rollback(); cur.close(); conn.close()
        except Exception: pass
        return jsonify(ok=False, error='來源資料與目標已有相同訂單，請先人工處理重複旅次'), 409
    except Exception as exc:
        print(f'[ADMIN_MEMBER_MERGE] {exc}')
        return jsonify(ok=False, error='合併會員失敗'), 500


@app.route('/api/admin/members/export.csv')
def admin_members_export():
    # 整份會員個資（姓名、手機、Email）一次帶走，風險等級與「合併會員」相同，
    # 因此同樣限 owner；訂位人員仍可在後台逐筆查詢。
    if not is_admin():
        return jsonify(ok=False, error='僅管理者可匯出會員名單'), 401
    try:
        import csv, io
        conn = get_db(); cur = conn.cursor()
        cur.execute("SELECT * FROM members ORDER BY joined_at DESC"); rows = cur.fetchall()
        output = io.StringIO(); output.write('\ufeff'); writer = csv.writer(output)
        writer.writerow(['會員編號','姓名','手機','Email','生日月份','等級','累積旅次','點數餘額','LINE綁定','加入時間','備註'])
        for row in rows:
            writer.writerow([row['member_no'],row['name'],row['phone'],row['email'],row.get('birth_month') or '',
                             level_for_trips(row['trip_count']),row['trip_count'],row['points_balance'],
                             '是' if row.get('line_user_id') else '否',str(row['joined_at']),row.get('notes') or ''])
        write_audit(cur, 'export', '會員名單', '全部', len(rows), 0, 'CSV 匯出')
        conn.commit(); cur.close(); conn.close()
        return app.response_class(output.getvalue(), mimetype='text/csv', headers={
            'Content-Disposition': 'attachment; filename=phbay-members.csv'})
    except Exception as exc:
        print(f'[ADMIN_MEMBERS_EXPORT] {exc}')
        return jsonify(ok=False, error='匯出會員名單失敗'), 500


def send_contact_email(data):
    sender    = os.environ.get('EMAIL_USER', '')
    recipient = 'dodoken1002@phbay.net'

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
選擇梯次：{data.get('slot_label', '（未選擇）')}
候補狀態：{'候補' if data.get('is_waitlist') else '正團'}
備註：{data.get('notes', '（未填）')}

請盡快與客戶聯繫。
"""
    if sender and (os.environ.get('GMAIL_SERVICE_ACCOUNT_JSON', '').strip() or os.environ.get('EMAIL_PASS', '')):
        msg = MIMEMultipart()
        msg['From']    = f'潮旅國際旅行社 <{sender}>'
        msg['To']      = recipient
        msg['Subject'] = f'【新諮詢】{data.get("name", "")} — {data.get("travel_date", "")} ~ {data.get("travel_date_end", "")}'
        msg.attach(MIMEText(body, 'plain', 'utf-8'))
        ok, detail = _deliver(sender, recipient, msg)
        if ok:
            print(f'[EMAIL] 通知信已寄出（{detail}）→ {recipient}')
        else:
            print(f'[EMAIL] 寄信失敗（不影響表單儲存）：{detail}')
    else:
        print('[EMAIL] 未設定寄信方式（EMAIL_USER + GMAIL_SERVICE_ACCOUNT_JSON 或 EMAIL_PASS），跳過寄信')

    try:
        send_line_notify(body)
    except Exception as _e:
        print(f'[LINE] 諮詢通知呼叫失敗（不影響表單儲存）：{_e}')


def send_preorder_email(info):
    """行程預購新訂單通知（內海巡禮／音樂節等預購共用）：email＋LINE 推播。
    任一通知失敗都不影響訂單建立。
    為保護個資，通知內容不含完整身分證字號，完整資料請至後台 /admin 檢視。"""
    sender    = os.environ.get('EMAIL_USER', '')
    recipient = os.environ.get('PREORDER_NOTIFY_EMAIL', 'dodoken1002@phbay.net')

    status_map = {'confirmed_departure': '已達成行門檻（可成行）', 'pending_departure': '待成團',
                  'confirmed': '人工確認', 'cancelled': '已取消'}
    when = f"{info.get('date', '')} {info.get('time', '')}".strip()
    names = '\n'.join(f"  {i}. {n}" for i, n in enumerate(info.get('passenger_names', []), 1)) or '  （無）'
    product = info.get('product', '預購行程')
    body = f"""潮旅國際旅行社 — 新預購通知

行程：{product}
訂單編號：{info.get('booking_ref', '')}
出發班次：{when}
預購人數：{info.get('passenger_count', '')} 人
訂單狀態：{status_map.get(info.get('status', ''), info.get('status', ''))}
業者/代號：{info.get('agency_name') or '（未填，可能為一般消費者）'}
主要聯絡：{info.get('contact_name', '')}｜{info.get('contact_phone', '')}
備註：{info.get('notes') or '（未填）'}

乘客名單：
{names}

※ 身分證字號等完整資料請至後台 /admin 檢視。
請盡快與客戶確認出發資訊。
"""
    if sender and (os.environ.get('GMAIL_SERVICE_ACCOUNT_JSON', '').strip() or os.environ.get('EMAIL_PASS', '')):
        msg = MIMEMultipart()
        msg['From']    = f'潮旅國際旅行社 <{sender}>'
        msg['To']      = recipient
        msg['Subject'] = f'【新預購】{product}｜{when}｜{info.get("passenger_count", "")}人｜{info.get("booking_ref", "")}'
        msg.attach(MIMEText(body, 'plain', 'utf-8'))
        ok, detail = _deliver(sender, recipient, msg)
        if ok:
            print(f'[EMAIL] 預購通知信已寄出（{detail}）→ {recipient}')
        else:
            print(f'[EMAIL] 預購通知寄信失敗（不影響訂單）：{detail}')
    else:
        print('[EMAIL] 未設定寄信方式（EMAIL_USER + GMAIL_SERVICE_ACCOUNT_JSON 或 EMAIL_PASS），跳過預購通知')

    try:
        send_line_notify(body)
    except Exception as _e:
        print(f'[LINE] 預購通知呼叫失敗（不影響訂單）：{_e}')


EMAIL_RE = re.compile(r'^[^@\s]+@[^@\s]+\.[^@\s]+$')


def send_customer_confirmation_email(info):
    """寄「訂位確認信」給客人（代表人 Email，選填有填才寄）。
    內容為客人視角：訂單編號、行程、班次、人數、成團狀態與聯絡方式；
    不含身分證等個資。寄信失敗不影響訂單。"""
    recipient = (info.get('contact_email') or '').strip()
    sender = os.environ.get('EMAIL_USER', '')
    if not recipient or not EMAIL_RE.match(recipient):
        return
    if not sender or not (os.environ.get('GMAIL_SERVICE_ACCOUNT_JSON', '').strip() or os.environ.get('EMAIL_PASS', '')):
        print('[EMAIL] 未設定寄信方式，跳過客人確認信')
        return

    when = f"{info.get('date', '')} {info.get('time', '')}".strip()
    product = info.get('product', '預購行程')
    if info.get('status') == 'confirmed_departure':
        status_line = '本班次已達成行門檻，確定出發！我們將於出發前與您聯繫確認細節。'
    else:
        status_line = '本班次尚在湊團中（6 人成行），成團後我們會第一時間通知您；若最終未成團，將協助您改期或全額退還已付款項。'
    body = f"""{info.get('contact_name', '')} 您好：

感謝您預購「{product}」，以下是您的訂位資訊，請留存核對：

──────────────────────
訂位代號：{info.get('booking_ref', '')}
行　　程：{product}
出發班次：{when}
預購人數：{info.get('passenger_count', '')} 人
業者/代號：{info.get('agency_name') or '—'}
備　　註：{info.get('notes') or '—'}
──────────────────────

{status_line}

【重要】請加入潮旅官方 LINE（ID：@phbay2018，https://line.me/R/ti/p/@phbay2018），
並傳送您的訂位代號 {info.get('booking_ref', '')}，方便我們即時通知出發資訊與天候異動。

如資料有誤或需修改，請透過 LINE 或電話 06-9271288 與我們聯繫（週一至週五 08:30–17:30）。

潮旅國際旅行社
交觀乙第1864號｜品保澎字第0188號
澎湖縣馬公市民權路13號2樓
官網：https://www.phbay.info
"""
    msg = MIMEMultipart()
    msg['From'] = f'潮旅國際旅行社 <{sender}>'
    msg['To'] = recipient
    msg['Subject'] = f'【訂位確認】{product}｜{when}｜訂位代號 {info.get("booking_ref", "")}'
    msg.attach(MIMEText(body, 'plain', 'utf-8'))
    ok, detail = _deliver(sender, recipient, msg)
    print(f'[EMAIL] 客人確認信{"已寄出" if ok else "寄送失敗（不影響訂單）"}（{detail}）→ {recipient}')


# ─── 梯次名額 API（公開）─────────────────────────────────────
@app.route('/api/slots', methods=['GET'])
def get_slots():
    """取得所有啟用梯次（可帶 ?tour_id=X 過濾）。"""
    try:
        conn = get_db()
        cur = conn.cursor()
        tour_id = request.args.get('tour_id')
        if tour_id:
            cur.execute(
                "SELECT * FROM tour_slots WHERE is_active=TRUE AND tour_id=%s ORDER BY id",
                (tour_id,))
        else:
            cur.execute("SELECT * FROM tour_slots WHERE is_active=TRUE ORDER BY tour_id, id")
        rows = [dict(r) for r in cur.fetchall()]
        cur.close(); conn.close()
        for r in rows:
            r['created_at'] = str(r.get('created_at', ''))
            r['remaining']  = max(0, r['capacity'] - r['booked'])
            r['wl_remaining'] = max(0, r['waitlist_cap'] - r['waitlisted'])
            r['status'] = (
                'full_wl_full' if r['remaining'] == 0 and r['wl_remaining'] == 0
                else 'waitlist'  if r['remaining'] == 0
                else 'low'       if r['remaining'] <= 3
                else 'available'
            )
        return jsonify(ok=True, slots=rows)
    except Exception as e:
        return jsonify(ok=False, error=str(e)), 500



# ─── 小城故事・內海巡禮預購 API ─────────────────────────────
NEIHAI_BASE_TIMES = ("09:00", "11:00")
NEIHAI_THIRD_TIME = "16:30"                      # 2026-07-06 起每日加開第三時段
NEIHAI_THIRD_TIME_START = date(2026, 7, 6)
NEIHAI_FIREWORKS_TIME = "20:30"                  # 花火專船：2026 年 7、8 月每週二


def _neihai_times_for_date(d):
    """回傳指定日期可預購的出航時段（依日期動態決定）。"""
    times = list(NEIHAI_BASE_TIMES)
    if d >= NEIHAI_THIRD_TIME_START:
        times.append(NEIHAI_THIRD_TIME)
    if d.year == 2026 and d.month in (7, 8) and d.weekday() == 1:  # 週二
        times.append(NEIHAI_FIREWORKS_TIME)
    return times


def _neihai_time_label(t):
    return f"{t} 花火專船" if t == NEIHAI_FIREWORKS_TIME else t


NEIHAI_DEFAULT_CAPACITY = 13
NEIHAI_MIN_PEOPLE = 6
NEIHAI_VALID_STATUSES = {
    "pending_departure",
    "confirmed_departure",
    "confirmed",
    "completed",
    "cancelled",
}


@app.route('/neihai-preorder')
def neihai_preorder_page():
    return send_from_directory('.', 'neihai-preorder.html')


def _parse_month(value):
    value = (value or date.today().strftime("%Y-%m")).strip()
    try:
        start = datetime.strptime(value, "%Y-%m").date().replace(day=1)
    except ValueError:
        raise ValueError("月份格式需為 YYYY-MM")
    if start.month == 12:
        end = start.replace(year=start.year + 1, month=1)
    else:
        end = start.replace(month=start.month + 1)
    return start, end


# ─── 中央氣象署潮汐預報（F-A0021-001）───
CWA_API_KEY = os.environ.get('CWA_API_KEY', '')
TIDE_LOCATIONS = ("澎湖縣馬公市", "澎湖縣湖西鄉", "澎湖縣白沙鄉",
                  "澎湖縣西嶼鄉", "澎湖縣望安鄉", "澎湖縣七美鄉")
TIDE_CACHE_TTL = 6 * 3600  # 潮汐預報更新頻率低，快取 6 小時
_tide_cache = {}  # location -> {'at': epoch, 'data': {...}}


def _fetch_cwa_tides(location):
    """呼叫氣象署 API 取單一鄉市未來一個月潮汐預報，整理成精簡格式。"""
    import urllib.request
    import urllib.parse
    import time as _time
    import ssl
    cached = _tide_cache.get(location)
    if cached and _time.time() - cached['at'] < TIDE_CACHE_TTL:
        return cached['data']
    qs = urllib.parse.urlencode({'Authorization': CWA_API_KEY, 'LocationName': location})
    url = f'https://opendata.cwa.gov.tw/api/v1/rest/datastore/F-A0021-001?{qs}'
    # 氣象署部分節點的憑證缺 SKI 欄位，Python 3.13 預設的嚴格檢查會拒絕；
    # 保留完整鏈驗證與主機名檢查，僅關閉 VERIFY_X509_STRICT。
    ctx = ssl.create_default_context()
    ctx.verify_flags &= ~ssl.VERIFY_X509_STRICT
    with urllib.request.urlopen(url, timeout=15, context=ctx) as resp:
        raw = json.load(resp)
    if not raw.get('success') or not raw.get('records', {}).get('TideForecasts'):
        raise RuntimeError('氣象署回應異常')
    loc = raw['records']['TideForecasts'][0]['Location']
    days = []
    # 氣象署回傳的 Daily 不保證依日期排序，需自行排序再取用
    for d in sorted(loc['TimePeriods']['Daily'], key=lambda x: x.get('Date') or ''):
        days.append({
            'date': d.get('Date'),
            'lunar': d.get('LunarDate'),
            'range': d.get('TideRange'),  # 大潮/中潮/小潮
            'tides': [{
                'time': t.get('DateTime'),
                'type': t.get('Tide'),  # 滿潮/乾潮
                'height_cm': t.get('TideHeights', {}).get('AboveTWVD'),
            } for t in (d.get('Time') or [])],
        })
    data = {'location': loc['LocationName'], 'days': days}
    _tide_cache[location] = {'at': _time.time(), 'data': data}
    return data


@app.route('/api/tides')
def api_tides():
    location = (request.args.get('location') or TIDE_LOCATIONS[0]).strip()
    if location not in TIDE_LOCATIONS:
        return jsonify(ok=False, error='地點僅限澎湖縣各鄉市'), 400
    if not CWA_API_KEY:
        return jsonify(ok=False, error='潮汐服務尚未設定'), 503
    try:
        data = _fetch_cwa_tides(location)
        return jsonify(ok=True, source='中央氣象署', **data)
    except Exception:
        # 若氣象署暫時故障，回傳過期快取聊勝於無
        stale = _tide_cache.get(location)
        if stale:
            return jsonify(ok=True, source='中央氣象署', stale=True, **stale['data'])
        return jsonify(ok=False, error='暫時無法取得潮汐資料，請稍後再試'), 502


@app.route('/tides')
def tides_page():
    return send_from_directory('.', 'tides.html')


def _taiwan_now():
    """台灣當前時間（UTC+8，台灣無夏令時間；主機時區可能是 UTC，不能用本地時間）。"""
    return datetime.utcnow() + timedelta(hours=8)


def _sailing_departed(sailing_date, sailing_time, now=None):
    """判斷船班（日期＋HH:MM 時段）是否已過出航時間。"""
    now = now or _taiwan_now()
    hh, mm = sailing_time.split(':')
    dep = datetime(sailing_date.year, sailing_date.month, sailing_date.day, int(hh), int(mm))
    return dep <= now


def _parse_sailing_date(value):
    try:
        return datetime.strptime((value or "").strip(), "%Y-%m-%d").date()
    except ValueError:
        raise ValueError("出航日期格式需為 YYYY-MM-DD")


def _normalize_neihai_time(value, sailing_date=None):
    value = (value or "").strip()
    # 先抽出 HH:MM（容許「20:30 花火專船」「20:30🎆」等帶字尾寫法）
    mt = re.search(r'(\d{1,2}):(\d{2})', value)
    if mt:
        value = f"{int(mt.group(1)):02d}:{mt.group(2)}"
    else:
        aliases = {"9:00": "09:00", "9": "09:00", "09": "09:00", "11": "11:00",
                   "16": "16:30", "1630": "16:30", "20": "20:30", "2030": "20:30"}
        value = aliases.get(value, value)
    allowed = (_neihai_times_for_date(sailing_date) if sailing_date
               else list(NEIHAI_BASE_TIMES) + [NEIHAI_THIRD_TIME, NEIHAI_FIREWORKS_TIME])
    if value not in allowed:
        raise ValueError("此日期可預購時段：" + "、".join(allowed))
    return value


def _sailing_status(booked, capacity, min_people, is_active=True):
    booked = int(booked or 0)
    capacity = int(capacity or NEIHAI_DEFAULT_CAPACITY)
    min_people = int(min_people or NEIHAI_MIN_PEOPLE)
    remaining = max(0, capacity - booked)
    if not is_active:
        return "closed", "已關閉", remaining, max(0, min_people - booked)
    if remaining <= 0:
        return "full", "已額滿", 0, 0
    if booked >= min_people:
        return "guaranteed", f"已達 {booked} 人，可發船", remaining, 0
    needed = max(0, min_people - booked)
    return "forming", f"待成團，還差 {needed} 人", remaining, needed


def _neihai_month_availability(start, end):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        SELECT
          s.id, s.sailing_date, s.sailing_time, s.capacity, s.min_people, s.is_active, s.notes,
          COALESCE(SUM(CASE WHEN p.status <> 'cancelled' THEN p.passenger_count ELSE 0 END), 0) AS booked
        FROM neihai_sailings s
        LEFT JOIN neihai_preorders p ON p.sailing_id = s.id
        WHERE s.sailing_date >= %s AND s.sailing_date < %s
        GROUP BY s.id
    """, (start, end))
    rows = cur.fetchall()
    cur.close(); conn.close()

    overrides = {}
    for r in rows:
        key = (str(r["sailing_date"]), r["sailing_time"])
        overrides[key] = dict(r)

    items = []
    now = _taiwan_now()
    d = start
    while d < end:
        for sailing_time in _neihai_times_for_date(d):
            # 已過出航時間的班次不再回傳，避免旅客誤選過期日期／時段
            if _sailing_departed(d, sailing_time, now):
                continue
            key = (str(d), sailing_time)
            row = overrides.get(key, {})
            capacity = int(row.get("capacity") or NEIHAI_DEFAULT_CAPACITY)
            min_people = int(row.get("min_people") or NEIHAI_MIN_PEOPLE)
            booked = int(row.get("booked") or 0)
            is_active = row.get("is_active", True)
            code, label, remaining, needed = _sailing_status(booked, capacity, min_people, is_active)
            items.append({
                "id": row.get("id"),
                "date": str(d),
                "time": sailing_time,
                "time_label": _neihai_time_label(sailing_time),
                "capacity": capacity,
                "min_people": min_people,
                "booked": booked,
                "remaining": remaining,
                "needed_to_go": needed,
                "status": code,
                "status_label": label,
                "is_active": bool(is_active),
                "notes": row.get("notes") or "",
            })
        d += timedelta(days=1)
    return items


@app.route('/api/neihai/sailings', methods=['GET'])
def neihai_sailings():
    try:
        start, end = _parse_month(request.args.get("month"))
        return jsonify(
            ok=True,
            month=start.strftime("%Y-%m"),
            product="小城故事・內海巡禮",
            capacity=NEIHAI_DEFAULT_CAPACITY,
            min_people=NEIHAI_MIN_PEOPLE,
            sailings=_neihai_month_availability(start, end),
        )
    except ValueError as e:
        return jsonify(ok=False, error=str(e)), 400
    except Exception as e:
        return jsonify(ok=False, error=str(e)), 500


@app.route('/api/neihai/preorders', methods=['POST'])
def create_neihai_preorder():
    data = request.get_json(force=True, silent=True) or {}
    try:
        sailing_date = _parse_sailing_date(data.get("sailing_date"))
        sailing_time = _normalize_neihai_time(data.get("sailing_time"), sailing_date)
    except ValueError as e:
        return jsonify(ok=False, error=str(e)), 400
    if _sailing_departed(sailing_date, sailing_time):
        return jsonify(ok=False, error="此船班已過出航時間，請重新整理頁面選擇其他日期"), 400

    passengers = data.get("passengers") or []
    if not isinstance(passengers, list) or not (1 <= len(passengers) <= NEIHAI_DEFAULT_CAPACITY):
        return jsonify(ok=False, error="乘客人數需為 1 至 13 人"), 400

    clean_passengers = []
    for idx, p in enumerate(passengers, start=1):
        name = (p.get("name") or "").strip()
        national_id = (p.get("national_id") or "").strip().upper()
        phone = (p.get("phone") or "").strip()
        birth = (p.get("birth_date") or "").strip()
        # 電話僅第 1 位（代表人）必填，其餘乘客選填
        if not all([name, national_id, birth]):
            return jsonify(ok=False, error=f"第 {idx} 位乘客資料未填完整"), 400
        if idx == 1 and not phone:
            return jsonify(ok=False, error="第 1 位乘客為代表人，請填寫聯絡電話"), 400
        try:
            birth_date = datetime.strptime(birth, "%Y-%m-%d").date()
        except ValueError:
            return jsonify(ok=False, error=f"第 {idx} 位乘客生日格式需為 YYYY-MM-DD"), 400
        clean_passengers.append({
            "name": name,
            "national_id": national_id,
            "birth_date": birth_date,
            "phone": phone,
        })

    contact_name = clean_passengers[0]["name"]
    contact_phone = (data.get("contact_phone") or clean_passengers[0]["phone"]).strip()
    contact_email = (data.get("contact_email") or "").strip()
    if contact_email and not EMAIL_RE.match(contact_email):
        return jsonify(ok=False, error="Email 格式不正確，請確認後再送出（或留空）"), 400
    agency_name = (data.get("agency_name") or "").strip()
    notes = (data.get("notes") or "").strip()

    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO neihai_sailings (sailing_date, sailing_time, capacity, min_people)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (sailing_date, sailing_time) DO NOTHING
        """, (sailing_date, sailing_time, NEIHAI_DEFAULT_CAPACITY, NEIHAI_MIN_PEOPLE))
        cur.execute("""
            SELECT * FROM neihai_sailings
            WHERE sailing_date=%s AND sailing_time=%s
            FOR UPDATE
        """, (sailing_date, sailing_time))
        sailing = cur.fetchone()
        if not sailing or not sailing["is_active"]:
            conn.rollback(); cur.close(); conn.close()
            return jsonify(ok=False, error="此船班目前未開放預購"), 400

        cur.execute("""
            SELECT COALESCE(SUM(passenger_count), 0) AS booked
            FROM neihai_preorders
            WHERE sailing_id=%s AND status <> 'cancelled'
        """, (sailing["id"],))
        booked = int(cur.fetchone()["booked"] or 0)
        passenger_count = len(clean_passengers)
        capacity = int(sailing["capacity"] or NEIHAI_DEFAULT_CAPACITY)
        if booked + passenger_count > capacity:
            conn.rollback(); cur.close(); conn.close()
            return jsonify(ok=False, error=f"此船班剩餘 {max(0, capacity - booked)} 位，不足以容納本次預購人數"), 400

        status = "confirmed_departure" if booked + passenger_count >= int(sailing["min_people"]) else "pending_departure"
        cur.execute("""
            INSERT INTO neihai_preorders
              (sailing_id, agency_name, contact_name, contact_phone, contact_email,
               passenger_count, status, notes, utm)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
            RETURNING id, created_at
        """, (sailing["id"], agency_name, contact_name, contact_phone, contact_email,
              passenger_count, status, notes,
              Json({k: str(v)[:200] for k, v in (data.get('utm') or {}).items()
                    if k.startswith('utm_') or k in ('landing_page', 'referrer')})))
        order = cur.fetchone()
        booking_ref = f"NH{sailing_date.strftime('%Y%m%d')}{sailing_time.replace(':', '')}-{int(order['id']):04d}"
        cur.execute("UPDATE neihai_preorders SET booking_ref=%s WHERE id=%s", (booking_ref, order["id"]))
        for p in clean_passengers:
            cur.execute("""
                INSERT INTO neihai_passengers (preorder_id, name, national_id, birth_date, phone)
                VALUES (%s,%s,%s,%s,%s)
            """, (order["id"], p["name"], p["national_id"], p["birth_date"], p["phone"]))

        conn.commit(); cur.close(); conn.close()

        try:
            send_preorder_email({
                'product': '小城故事・內海巡禮',
                'booking_ref': booking_ref,
                'date': str(sailing_date), 'time': sailing_time,
                'passenger_count': passenger_count, 'status': status,
                'agency_name': agency_name, 'contact_name': contact_name,
                'contact_phone': contact_phone, 'notes': notes,
                'passenger_names': [p['name'] for p in clean_passengers],
            })
        except Exception as _e:
            print(f'[EMAIL] 內海預購通知呼叫失敗（不影響訂單）：{_e}')

        try:
            send_customer_confirmation_email({
                'product': '小城故事・內海巡禮',
                'booking_ref': booking_ref,
                'date': str(sailing_date), 'time': sailing_time,
                'passenger_count': passenger_count, 'status': status,
                'agency_name': agency_name, 'contact_name': contact_name,
                'contact_email': contact_email, 'notes': notes,
            })
        except Exception as _e:
            print(f'[EMAIL] 內海客人確認信呼叫失敗（不影響訂單）：{_e}')

        code, label, remaining, needed = _sailing_status(booked + passenger_count, capacity, sailing["min_people"], True)
        return jsonify(
            ok=True,
            id=order["id"],
            booking_ref=booking_ref,
            created_at=str(order["created_at"]),
            sailing_date=str(sailing_date),
            sailing_time=sailing_time,
            passenger_count=passenger_count,
            sailing_status=code,
            sailing_status_label=label,
            remaining=remaining,
            needed_to_go=needed,
            message="預購已送出，已達發船門檻" if code == "guaranteed" else f"預購已送出，尚差 {needed} 人成行",
        )
    except Exception as e:
        return jsonify(ok=False, error=f"伺服器錯誤：{e}"), 500


@app.route('/api/admin/neihai/preorders', methods=['GET'])
def admin_neihai_preorders():
    if not has_role('orders'):
        return jsonify(ok=False, error='未授權'), 401
    try:
        start, end = _parse_month(request.args.get("month"))
        conn = get_db()
        cur = conn.cursor()
        cur.execute("""
            SELECT p.*, s.sailing_date, s.sailing_time, s.capacity, s.min_people
            FROM neihai_preorders p
            JOIN neihai_sailings s ON s.id = p.sailing_id
            WHERE s.sailing_date >= %s AND s.sailing_date < %s
            ORDER BY s.sailing_date, s.sailing_time, p.created_at
        """, (start, end))
        orders = [dict(r) for r in cur.fetchall()]
        ids = [o["id"] for o in orders]
        passengers_by_order = {i: [] for i in ids}
        if ids:
            cur.execute("""
                SELECT * FROM neihai_passengers
                WHERE preorder_id = ANY(%s)
                ORDER BY preorder_id, id
            """, (ids,))
            for r in cur.fetchall():
                r = dict(r)
                r["birth_date"] = str(r["birth_date"])
                if r.get("created_at"):
                    r["created_at"] = str(r["created_at"])
                passengers_by_order[r["preorder_id"]].append(r)
        logs_by_order = {i: [] for i in ids}
        if ids:
            cur.execute("""
                SELECT preorder_id, summary, changed_at FROM neihai_preorder_logs
                WHERE preorder_id = ANY(%s)
                ORDER BY preorder_id, changed_at DESC
            """, (ids,))
            for r in cur.fetchall():
                r = dict(r)
                logs_by_order[r["preorder_id"]].append(
                    {"summary": r["summary"], "changed_at": str(r["changed_at"])})
        cur.close(); conn.close()

        for o in orders:
            for k in ("sailing_date", "created_at", "updated_at"):
                if o.get(k): o[k] = str(o[k])
            o["passengers"] = passengers_by_order.get(o["id"], [])
            o["logs"] = logs_by_order.get(o["id"], [])

        availability = _neihai_month_availability(start, end)
        return jsonify(ok=True, month=start.strftime("%Y-%m"), orders=orders, sailings=availability)
    except ValueError as e:
        return jsonify(ok=False, error=str(e)), 400
    except Exception as e:
        return jsonify(ok=False, error=str(e)), 500


NEIHAI_STATUS_LABELS = {
    "pending_departure": "待成團", "confirmed_departure": "已達發船門檻",
    "confirmed": "人工確認", "completed": "旅程完成", "cancelled": "已取消",
}


@app.route('/api/admin/neihai/preorders/<int:order_id>', methods=['PATCH'])
def admin_update_neihai_preorder(order_id):
    """更新內海預購訂單：可改狀態、聯絡/業者/備註、以及各乘客資料；
    所有實際變更會寫入 neihai_preorder_logs 留下修改紀錄。"""
    if not has_role('orders'):
        return jsonify(ok=False, error='未授權'), 401
    data = request.get_json(force=True, silent=True) or {}
    try:
        conn = get_db(); cur = conn.cursor()
        cur.execute("SELECT * FROM neihai_preorders WHERE id=%s", (order_id,))
        order = cur.fetchone()
        if not order:
            cur.close(); conn.close()
            return jsonify(ok=False, error="找不到訂單"), 404
        order = dict(order)

        changes = []
        set_parts, params = [], []

        if "status" in data:
            new_status = (data.get("status") or "").strip()
            if new_status not in NEIHAI_VALID_STATUSES:
                cur.close(); conn.close()
                return jsonify(ok=False, error="狀態不正確"), 400
            if new_status != order["status"]:
                changes.append(f"狀態：{NEIHAI_STATUS_LABELS.get(order['status'], order['status'])}"
                               f" → {NEIHAI_STATUS_LABELS.get(new_status, new_status)}")
                set_parts.append("status=%s"); params.append(new_status)

        for field, label in (("agency_name", "業者"), ("contact_name", "主要聯絡姓名"),
                             ("contact_phone", "聯絡電話"), ("contact_email", "Email"),
                             ("notes", "備註")):
            if field in data:
                new_val = (data.get(field) or "").strip()
                old_val = order.get(field) or ""
                if field in ("contact_name", "contact_phone") and not new_val:
                    cur.close(); conn.close()
                    return jsonify(ok=False, error=f"{label}不可空白"), 400
                if new_val != old_val:
                    changes.append(f"{label}：{old_val or '（空）'} → {new_val or '（空）'}")
                    set_parts.append(f"{field}=%s"); params.append(new_val)

        if "archived" in data:
            new_arch = bool(data.get("archived"))
            if new_arch != bool(order.get("archived")):
                changes.append("封存訂單" if new_arch else "取消封存")
                set_parts.append("archived=%s"); params.append(new_arch)

        # 改出航日期/時段：搬移到另一個船班（必要時自動建立船班列）
        if data.get("sailing_date") or data.get("sailing_time"):
            cur.execute("SELECT sailing_date, sailing_time FROM neihai_sailings WHERE id=%s",
                        (order["sailing_id"],))
            cur_sail = cur.fetchone()
            old_d, old_t = str(cur_sail["sailing_date"]), cur_sail["sailing_time"]
            try:
                new_d = _parse_sailing_date(data.get("sailing_date") or old_d)
                new_t = _normalize_neihai_time(data.get("sailing_time") or old_t, new_d)
            except ValueError as e:
                cur.close(); conn.close()
                return jsonify(ok=False, error=str(e)), 400
            if (str(new_d), new_t) != (old_d, old_t):
                cur.execute("""
                    INSERT INTO neihai_sailings (sailing_date, sailing_time, capacity, min_people)
                    VALUES (%s,%s,%s,%s) ON CONFLICT (sailing_date, sailing_time) DO NOTHING
                """, (new_d, new_t, NEIHAI_DEFAULT_CAPACITY, NEIHAI_MIN_PEOPLE))
                cur.execute("SELECT id FROM neihai_sailings WHERE sailing_date=%s AND sailing_time=%s",
                            (new_d, new_t))
                changes.append(f"班次：{old_d} {old_t} → {new_d} {new_t}")
                set_parts.append("sailing_id=%s"); params.append(cur.fetchone()["id"])

        if set_parts:
            set_parts.append("updated_at=NOW()")
            cur.execute(f"UPDATE neihai_preorders SET {', '.join(set_parts)} WHERE id=%s",
                        tuple(params) + (order_id,))

        passengers = data.get("passengers")
        if isinstance(passengers, list):
            cur.execute("SELECT * FROM neihai_passengers WHERE preorder_id=%s", (order_id,))
            existing = {r["id"]: dict(r) for r in cur.fetchall()}
            for i, p in enumerate(passengers, 1):
                cur_p = existing.get(p.get("id"))
                if not cur_p:
                    continue
                pset, pparams = [], []
                for f, label in (("name", "姓名"), ("national_id", "身分證字號"),
                                 ("birth_date", "生日"), ("phone", "電話")):
                    if f not in p:
                        continue
                    new_v = str(p.get(f) or "").strip()
                    if f == "national_id":
                        new_v = new_v.upper()
                    if f == "birth_date":
                        try:
                            new_v = str(datetime.strptime(new_v, "%Y-%m-%d").date())
                        except ValueError:
                            cur.close(); conn.close()
                            return jsonify(ok=False, error=f"第 {i} 位乘客生日格式需為 YYYY-MM-DD"), 400
                    elif not new_v:
                        cur.close(); conn.close()
                        return jsonify(ok=False, error=f"第 {i} 位乘客{label}不可空白"), 400
                    old_v = str(cur_p.get(f) or "")
                    if new_v != old_v:
                        changes.append(f"乘客「{cur_p['name']}」{label}：{old_v} → {new_v}")
                        pset.append(f"{f}=%s"); pparams.append(new_v)
                if pset:
                    cur.execute(f"UPDATE neihai_passengers SET {', '.join(pset)} WHERE id=%s",
                                tuple(pparams) + (cur_p["id"],))

        if changes:
            cur.execute("INSERT INTO neihai_preorder_logs (preorder_id, summary) VALUES (%s,%s)",
                        (order_id, "；".join(changes)))
        member_sync = None
        if 'status' in data:
            cur.execute("""SELECT o.booking_ref,o.contact_phone,o.status,s.sailing_date
                           FROM neihai_preorders o JOIN neihai_sailings s ON s.id=o.sailing_id
                           WHERE o.id=%s""", (order_id,))
            synced = cur.fetchone()
            if synced:  # JOIN 失配（例如航次已刪）時不可讓訂單更新整筆失敗
                member_sync = _sync_completed_order_trip(
                    cur, 'neihai_order', synced['booking_ref'],
                    synced['contact_phone'], '小城故事・內海巡禮',
                    synced['sailing_date'], synced['status'],
                    counts_trip=True)  # 內海巡禮為潮旅自營
        conn.commit(); cur.close(); conn.close()
        # LINE 升等通知在 commit 之後才送：網路呼叫不該佔著訂單的列鎖，
        # 失敗也絕不能回頭影響已經寫進去的訂單狀態。
        if member_sync and member_sync.get('notify'):
            _line_api_call('message/push', {'to': member_sync['notify'][0],
                                            'messages': [{'type': 'text',
                                                          'text': member_sync['notify'][1]}]})
        return jsonify(ok=True, changed=len(changes),
                       summary=("；".join(changes) if changes else "無變更"))
    except Exception as e:
        return jsonify(ok=False, error=str(e)), 500


@app.route('/api/admin/neihai/preorders/<int:order_id>', methods=['DELETE'])
def admin_delete_neihai_preorder(order_id):
    """刪除內海預購訂單（乘客與修改紀錄隨 CASCADE 一併刪除）。"""
    if not has_role('orders'):
        return jsonify(ok=False, error='未授權'), 401
    try:
        conn = get_db(); cur = conn.cursor()
        cur.execute("SELECT booking_ref FROM neihai_preorders WHERE id=%s", (order_id,))
        row = cur.fetchone()
        if not row:
            cur.close(); conn.close()
            return jsonify(ok=False, error='找不到訂單'), 404
        cur.execute("DELETE FROM neihai_preorders WHERE id=%s", (order_id,))
        conn.commit(); cur.close(); conn.close()
        return jsonify(ok=True, booking_ref=row['booking_ref'])
    except Exception as e:
        return jsonify(ok=False, error=str(e)), 500


IMPORT_STATUS_LABELS = {v: k for k, v in NEIHAI_STATUS_LABELS.items()}  # 中文標籤→代碼


def _import_clean_passengers(raw_passengers):
    """匯入用乘客清洗：姓名/身分證/生日必填，電話選填。回傳 (clean, err)。"""
    clean = []
    for idx, p in enumerate(raw_passengers or [], start=1):
        name = (p.get('name') or '').strip()
        national_id = (p.get('national_id') or '').strip().upper()
        birth = (p.get('birth_date') or '').strip()
        phone = (p.get('phone') or '').strip()
        if not all([name, national_id, birth]):
            return None, f'第 {idx} 位乘客缺姓名/身分證/生日'
        try:
            birth_date = datetime.strptime(birth, '%Y-%m-%d').date()
        except ValueError:
            return None, f'第 {idx} 位乘客生日格式需為 YYYY-MM-DD（{birth}）'
        clean.append({'name': name, 'national_id': national_id,
                      'birth_date': birth_date, 'phone': phone})
    if not clean:
        return None, '沒有乘客資料'
    return clean, None


@app.route('/api/admin/neihai/sailings', methods=['PATCH'])
def admin_toggle_neihai_sailing():
    """後台開啟/關閉單一船班的預購（upsert neihai_sailings.is_active）。
    關閉後前台該時段顯示「已關閉」且無法送出預購；已存在的訂單不受影響。"""
    if not has_role('orders'):
        return jsonify(ok=False, error='未授權'), 401
    data = request.get_json(force=True, silent=True) or {}
    try:
        sailing_date = _parse_sailing_date(data.get('sailing_date'))
        sailing_time = _normalize_neihai_time(data.get('sailing_time'), sailing_date)
    except ValueError as e:
        return jsonify(ok=False, error=str(e)), 400
    is_active = bool(data.get('is_active'))
    try:
        conn = get_db(); cur = conn.cursor()
        cur.execute("""
            INSERT INTO neihai_sailings (sailing_date, sailing_time, capacity, min_people, is_active)
            VALUES (%s,%s,%s,%s,%s)
            ON CONFLICT (sailing_date, sailing_time) DO UPDATE SET is_active = EXCLUDED.is_active
        """, (sailing_date, sailing_time, NEIHAI_DEFAULT_CAPACITY, NEIHAI_MIN_PEOPLE, is_active))
        conn.commit(); cur.close(); conn.close()
        return jsonify(ok=True, sailing_date=str(sailing_date), sailing_time=sailing_time,
                       is_active=is_active)
    except Exception as e:
        return jsonify(ok=False, error=str(e)), 500


@app.route('/api/admin/neihai/import', methods=['POST'])
def admin_neihai_import():
    """後台批次匯入內海預購訂單（CSV 格式與匯出相同，前端解析後送 JSON）。
    - booking_ref 已存在的訂單直接略過（可安全重複匯入）
    - 不做已出航/額滿阻擋（後台資料視為權威，超過容量僅回警告）
    - 不寄 email / LINE 通知"""
    if not has_role('orders'):
        return jsonify(ok=False, error='未授權'), 401
    data = request.get_json(force=True, silent=True) or {}
    orders = data.get('orders') or []
    overwrite = (data.get('mode') or '').strip() == 'overwrite'
    if not isinstance(orders, list) or not orders:
        return jsonify(ok=False, error='沒有可匯入的訂單'), 400
    created, updated, skipped, errors, warnings = [], [], [], [], []
    try:
        conn = get_db(); cur = conn.cursor()
        for i, o in enumerate(orders, start=1):
            try:
                sailing_date = _parse_sailing_date(o.get('sailing_date'))
                sailing_time = _normalize_neihai_time(o.get('sailing_time'), sailing_date)
            except ValueError as e:
                errors.append(f'第 {i} 筆：{e}'); continue
            clean, err = _import_clean_passengers(o.get('passengers'))
            if err:
                errors.append(f'第 {i} 筆：{err}'); continue
            # 依編號判斷既有訂單：覆蓋模式→更新，否則→略過
            ref = (o.get('booking_ref') or '').strip()
            existing_id = None
            if ref:
                cur.execute("SELECT id FROM neihai_preorders WHERE booking_ref=%s", (ref,))
                row = cur.fetchone()
                if row:
                    if not overwrite:
                        skipped.append(ref); continue
                    existing_id = row['id']
            # 確保目標船班存在
            cur.execute("""
                INSERT INTO neihai_sailings (sailing_date, sailing_time, capacity, min_people)
                VALUES (%s,%s,%s,%s) ON CONFLICT (sailing_date, sailing_time) DO NOTHING
            """, (sailing_date, sailing_time, NEIHAI_DEFAULT_CAPACITY, NEIHAI_MIN_PEOPLE))
            cur.execute("SELECT * FROM neihai_sailings WHERE sailing_date=%s AND sailing_time=%s FOR UPDATE",
                        (sailing_date, sailing_time))
            sailing = cur.fetchone()
            # 已訂人數（覆蓋時排除自己，避免重複計算）
            cur.execute("""
                SELECT COALESCE(SUM(passenger_count), 0) AS booked FROM neihai_preorders
                WHERE sailing_id=%s AND status <> 'cancelled' AND id <> %s
            """, (sailing['id'], existing_id or 0))
            booked = int(cur.fetchone()['booked'] or 0)
            capacity = int(sailing['capacity'] or NEIHAI_DEFAULT_CAPACITY)
            status = IMPORT_STATUS_LABELS.get((o.get('status') or '').strip()) or (
                'confirmed_departure' if booked + len(clean) >= int(sailing['min_people'])
                else 'pending_departure')
            if status != 'cancelled' and booked + len(clean) > capacity:
                warnings.append(f'{sailing_date} {sailing_time} 匯入後共 {booked + len(clean)} 人，超過上限 {capacity}')
            agency = (o.get('agency_name') or '').strip()
            cname = (o.get('contact_name') or '').strip() or clean[0]['name']
            cphone = (o.get('contact_phone') or '').strip() or clean[0]['phone']
            cemail = (o.get('contact_email') or '').strip()
            notes = (o.get('notes') or '').strip()
            if existing_id:
                # 覆蓋更新既有訂單：換船班、換資料、整批換乘客
                cur.execute("""
                    UPDATE neihai_preorders SET sailing_id=%s, agency_name=%s, contact_name=%s,
                        contact_phone=%s, contact_email=%s, passenger_count=%s, status=%s,
                        notes=%s, updated_at=NOW() WHERE id=%s
                """, (sailing['id'], agency, cname, cphone, cemail, len(clean), status, notes, existing_id))
                cur.execute("DELETE FROM neihai_passengers WHERE preorder_id=%s", (existing_id,))
                for p in clean:
                    cur.execute("""INSERT INTO neihai_passengers (preorder_id, name, national_id, birth_date, phone)
                                   VALUES (%s,%s,%s,%s,%s)""",
                                (existing_id, p['name'], p['national_id'], p['birth_date'], p['phone']))
                cur.execute("INSERT INTO neihai_preorder_logs (preorder_id, summary) VALUES (%s,%s)",
                            (existing_id, '後台匯入覆蓋更新'))
                updated.append(ref)
            else:
                cur.execute("""
                    INSERT INTO neihai_preorders
                      (sailing_id, agency_name, contact_name, contact_phone, contact_email,
                       passenger_count, status, notes)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id
                """, (sailing['id'], agency, cname, cphone, cemail, len(clean), status, notes))
                oid = cur.fetchone()['id']
                new_ref = ref or f"NH{sailing_date.strftime('%Y%m%d')}{sailing_time.replace(':', '')}-{int(oid):04d}"
                cur.execute("UPDATE neihai_preorders SET booking_ref=%s WHERE id=%s", (new_ref, oid))
                for p in clean:
                    cur.execute("""INSERT INTO neihai_passengers (preorder_id, name, national_id, birth_date, phone)
                                   VALUES (%s,%s,%s,%s,%s)""",
                                (oid, p['name'], p['national_id'], p['birth_date'], p['phone']))
                cur.execute("INSERT INTO neihai_preorder_logs (preorder_id, summary) VALUES (%s,%s)",
                            (oid, '後台匯入建立'))
                created.append(new_ref)
        if created or updated:
            pax = sum(len(o.get('passengers') or []) for o in orders)
            write_audit(cur, 'import', category='內海預購',
                        scope=f'新增{len(created)}／覆蓋{len(updated)}',
                        record_count=len(created) + len(updated), pax_count=pax,
                        detail=('覆蓋模式' if overwrite else '一般匯入'))
        conn.commit(); cur.close(); conn.close()
        return jsonify(ok=True, created=created, updated=updated, skipped=skipped,
                       errors=errors, warnings=warnings)
    except Exception as e:
        return jsonify(ok=False, error=str(e)), 500


# ─── 後台帳號登入與使用者管理 ─────────────────────────────
@app.route('/api/admin/login', methods=['POST'])
def admin_login():
    data = request.get_json(force=True, silent=True) or {}
    username = (data.get('username') or '').strip().lower()
    password = data.get('password') or ''
    if not username or not password:
        return jsonify(ok=False, error='請輸入帳號與密碼'), 400
    try:
        conn = get_db(); cur = conn.cursor()
        cur.execute("SELECT * FROM admin_users WHERE LOWER(username)=%s", (username,))
        u = cur.fetchone()
        if not u or not u['is_active'] or not check_password_hash(u['password_hash'], password):
            cur.close(); conn.close()
            return jsonify(ok=False, error='帳號或密碼錯誤，或帳號已停用'), 401
        cur.execute("UPDATE admin_users SET last_login=NOW() WHERE id=%s", (u['id'],))
        conn.commit(); cur.close(); conn.close()
        session.permanent = True
        session['au'] = {'id': u['id'], 'username': u['username'],
                         'name': u['display_name'] or u['username'], 'role': u['role']}
        return jsonify(ok=True, user=session['au'], role_label=ADMIN_ROLES.get(u['role'], u['role']))
    except Exception as e:
        return jsonify(ok=False, error=str(e)), 500


@app.route('/api/admin/logout', methods=['POST'])
def admin_logout():
    session.pop('au', None)
    return jsonify(ok=True)


@app.route('/api/admin/me', methods=['GET'])
def admin_me():
    u = current_admin()
    if not u:
        return jsonify(ok=False, error='未登入'), 401
    return jsonify(ok=True, user=u, role_label=ADMIN_ROLES.get(u['role'], u['role']))


@app.route('/api/admin/users', methods=['GET', 'POST'])
def admin_users():
    """使用者管理（僅 owner）。GET 列表；POST 建立 {username,password,display_name,role}。"""
    if not is_admin():
        return jsonify(ok=False, error='未授權'), 401
    try:
        conn = get_db(); cur = conn.cursor()
        if request.method == 'GET':
            cur.execute("""SELECT id, username, display_name, role, is_active, created_at, last_login
                           FROM admin_users ORDER BY id""")
            users = []
            for r in cur.fetchall():
                r = dict(r)
                for k in ('created_at', 'last_login'):
                    if r.get(k): r[k] = str(r[k])
                r['role_label'] = ADMIN_ROLES.get(r['role'], r['role'])
                users.append(r)
            cur.close(); conn.close()
            return jsonify(ok=True, users=users, roles=ADMIN_ROLES)
        data = request.get_json(force=True, silent=True) or {}
        username = (data.get('username') or '').strip().lower()
        password = data.get('password') or ''
        role = (data.get('role') or 'orders').strip()
        if not re.match(r'^[a-z0-9_.-]{3,30}$', username):
            cur.close(); conn.close()
            return jsonify(ok=False, error='帳號需為 3–30 字英數（可含 . _ -）'), 400
        if len(password) < 8:
            cur.close(); conn.close()
            return jsonify(ok=False, error='密碼至少 8 碼'), 400
        if role not in ADMIN_ROLES:
            cur.close(); conn.close()
            return jsonify(ok=False, error='角色不正確'), 400
        cur.execute("SELECT 1 FROM admin_users WHERE LOWER(username)=%s", (username,))
        if cur.fetchone():
            cur.close(); conn.close()
            return jsonify(ok=False, error='帳號已存在'), 400
        cur.execute("""INSERT INTO admin_users (username, password_hash, display_name, role)
                       VALUES (%s,%s,%s,%s) RETURNING id""",
                    (username, generate_password_hash(password),
                     (data.get('display_name') or '').strip() or username, role))
        uid = cur.fetchone()['id']
        conn.commit(); cur.close(); conn.close()
        return jsonify(ok=True, id=uid)
    except Exception as e:
        return jsonify(ok=False, error=str(e)), 500


@app.route('/api/admin/users/<int:uid>', methods=['PATCH'])
def admin_update_user(uid):
    """更新使用者（僅 owner）：role / is_active / display_name / password（重設）。"""
    if not is_admin():
        return jsonify(ok=False, error='未授權'), 401
    data = request.get_json(force=True, silent=True) or {}
    sets, params = [], []
    if 'role' in data:
        if data['role'] not in ADMIN_ROLES:
            return jsonify(ok=False, error='角色不正確'), 400
        sets.append('role=%s'); params.append(data['role'])
    if 'is_active' in data:
        sets.append('is_active=%s'); params.append(bool(data['is_active']))
    if 'display_name' in data:
        sets.append('display_name=%s'); params.append((data['display_name'] or '').strip())
    if data.get('password'):
        if len(data['password']) < 8:
            return jsonify(ok=False, error='密碼至少 8 碼'), 400
        sets.append('password_hash=%s'); params.append(generate_password_hash(data['password']))
    if not sets:
        return jsonify(ok=False, error='沒有可更新的欄位'), 400
    try:
        conn = get_db(); cur = conn.cursor()
        cur.execute(f"UPDATE admin_users SET {', '.join(sets)} WHERE id=%s", tuple(params) + (uid,))
        conn.commit(); cur.close(); conn.close()
        return jsonify(ok=True)
    except Exception as e:
        return jsonify(ok=False, error=str(e)), 500


AUDIT_ACTION_LABELS = {'export': '匯出', 'import': '匯入', 'view_full_id': '顯示完整身分證'}


@app.route('/api/admin/audit', methods=['POST'])
def admin_record_audit():
    """記錄一筆個資稽核事件（前端匯出時呼叫；操作者身分以 session 為準）。"""
    u = current_admin()
    if not u:
        return jsonify(ok=False, error='未授權'), 401
    data = request.get_json(force=True, silent=True) or {}
    action = (data.get('action') or '').strip()
    if action not in AUDIT_ACTION_LABELS:
        return jsonify(ok=False, error='動作不正確'), 400
    try:
        conn = get_db(); cur = conn.cursor()
        write_audit(cur, action,
                    category=(data.get('category') or '').strip()[:40],
                    scope=(data.get('scope') or '').strip()[:160],
                    record_count=data.get('record_count') or 0,
                    pax_count=data.get('pax_count') or 0,
                    detail=(data.get('detail') or '').strip()[:500])
        conn.commit(); cur.close(); conn.close()
        return jsonify(ok=True)
    except Exception as e:
        return jsonify(ok=False, error=str(e)), 500


@app.route('/api/admin/audit', methods=['GET'])
def admin_list_audit():
    """個資稽核紀錄清單（僅 owner）。可用 ?action= / ?days= 過濾。"""
    if not is_admin():
        return jsonify(ok=False, error='未授權'), 401
    try:
        action = (request.args.get('action') or '').strip()
        days = request.args.get('days')
        where, params = [], []
        if action in AUDIT_ACTION_LABELS:
            where.append('action=%s'); params.append(action)
        if days and str(days).isdigit():
            where.append("created_at >= NOW() - INTERVAL '%s days'" % int(days))
        sql = 'SELECT * FROM audit_logs'
        if where:
            sql += ' WHERE ' + ' AND '.join(where)
        sql += ' ORDER BY created_at DESC LIMIT 500'
        conn = get_db(); cur = conn.cursor()
        cur.execute(sql, tuple(params))
        rows = []
        for r in cur.fetchall():
            r = dict(r)
            r['created_at'] = str(r['created_at'])
            r['action_label'] = AUDIT_ACTION_LABELS.get(r['action'], r['action'])
            rows.append(r)
        cur.close(); conn.close()
        return jsonify(ok=True, logs=rows, action_labels=AUDIT_ACTION_LABELS)
    except Exception as e:
        return jsonify(ok=False, error=str(e)), 500


@app.route('/api/admin/email-test', methods=['GET', 'POST'])
def admin_email_test():
    """診斷用：實際嘗試寄一封測試信，回傳成功或真實 SMTP 錯誤訊息。"""
    if not is_admin():
        return jsonify(ok=False, error='未授權'), 401
    sender = os.environ.get('EMAIL_USER', '')
    recipient = os.environ.get('PREORDER_NOTIFY_EMAIL', 'dodoken1002@phbay.net')
    has_gmail = bool(os.environ.get('GMAIL_SERVICE_ACCOUNT_JSON', '').strip())
    has_smtp = bool(os.environ.get('EMAIL_PASS', ''))
    if not sender or not (has_gmail or has_smtp):
        return jsonify(ok=False, configured=False,
                       error='未設定寄信方式：需 EMAIL_USER，且至少一種管道 GMAIL_SERVICE_ACCOUNT_JSON（建議，走 HTTPS）或 EMAIL_PASS（SMTP，Railway 會擋）。')
    msg = MIMEMultipart()
    msg['From'] = f'潮旅國際旅行社 <{sender}>'
    msg['To'] = recipient
    msg['Subject'] = '【測試】潮旅預購通知信設定測試'
    msg.attach(MIMEText('這是一封測試信。收到代表預購通知 email 設定正常，'
                        '日後有新預購訂單會自動寄到此信箱。', 'plain', 'utf-8'))
    ok, detail = _deliver(sender, recipient, msg)
    if ok:
        return jsonify(ok=True, configured=True, sent_to=recipient, via=detail,
                       message=f'測試信已透過 {detail} 寄出至 {recipient}，請查收。')
    return jsonify(ok=False, configured=True, error=f'各埠皆寄信失敗：{detail}')


# ─── LINE Messaging API：webhook 與診斷 ─────────────────────
LINE_BIND_KEYWORDS = {'綁定通知', '綁定', '我的id', 'id', 'userid', 'myid'}


def _try_bind_member_line(user_id, text):
    match = re.search(r'綁定會員\s*([0-9]{6})', text or '')
    if not match:
        return None
    code = match.group(1)
    try:
        conn = get_db(); cur = conn.cursor()
        cur.execute("""
            SELECT c.*,m.member_no,m.name FROM member_auth_codes c
            JOIN members m ON m.id=c.member_id
            WHERE c.purpose='line_bind' AND c.used_at IS NULL AND c.expires_at>NOW()
              AND c.attempts<5 AND m.is_active=TRUE
            ORDER BY c.created_at DESC LIMIT 100 FOR UPDATE OF c
        """)
        matched = None
        for token in cur.fetchall():
            if hmac.compare_digest(token['code_hash'],
                                   _member_code_hash(token['member_id'], 'line_bind', code)):
                matched = token; break
        if not matched:
            cur.close(); conn.close()
            return '綁定碼錯誤或已過期，請回會員中心重新取得。'
        cur.execute("UPDATE members SET line_user_id=%s,updated_at=NOW() WHERE id=%s",
                    (user_id, matched['member_id']))
        cur.execute("UPDATE member_auth_codes SET used_at=NOW() WHERE id=%s", (matched['id'],))
        conn.commit(); cur.close(); conn.close()
        return f"綁定完成！{matched['name']} 您好，會員編號 {matched['member_no']}。之後旅次認列與升等會由這裡通知您。"
    except psycopg2.errors.UniqueViolation:
        try: conn.rollback(); cur.close(); conn.close()
        except Exception: pass
        return '這個 LINE 帳號已綁定其他會員，請聯絡潮旅客服協助。'
    except Exception as exc:
        print(f'[MEMBER LINE BIND] {exc}')
        return '綁定暫時失敗，請稍後再試或聯絡潮旅客服。'


def _member_line_command(user_id, text):
    command = (text or '').strip().replace(' ', '')
    commands = {'會員', '我的等級', '我的旅次', '我的點數', '旅行護照', '下一趟推薦', '專屬優惠'}
    if command not in commands:
        return None
    try:
        conn = get_db(); cur = conn.cursor()
        cur.execute("SELECT * FROM members WHERE line_user_id=%s AND is_active=TRUE", (user_id,))
        member = cur.fetchone()
        if not member:
            cur.close(); conn.close()
            return '尚未綁定澎湖百旅會員。請先登入會員中心取得 6 位數綁定碼，再傳送「綁定會員 123456」。'
        if command in {'會員', '我的等級'}:
            nxt = next_level(member['trip_count'])
            detail = f"目前等級：{level_for_trips(member['trip_count'])}\n累積旅次：{member['trip_count']} 次\n點數：{member['points_balance']} 點"
            if nxt: detail += f"\n距「{nxt['name']}」還差 {nxt['remaining']} 次"
        elif command in {'我的旅次', '旅行護照'}:
            cur.execute("""SELECT tour_name,departure_date,status FROM member_trips
                           WHERE member_id=%s ORDER BY departure_date DESC NULLS LAST LIMIT 8""",
                        (member['id'],))
            rows = cur.fetchall()
            detail = '最近旅次：\n' + ('\n'.join(f"・{r['departure_date'] or '日期未定'} {r['tour_name']}（{r['status']}）" for r in rows) if rows else '尚無已登錄旅次')
        elif command == '我的點數':
            detail = f"目前點數餘額：{member['points_balance']} 點\n點數用途依潮旅當期公告。"
        elif command == '下一趟推薦':
            cur.execute("SELECT title FROM tours WHERE is_active=TRUE ORDER BY is_hero DESC,sort_order LIMIT 3")
            detail = '為你推薦：\n' + '\n'.join(f"・{r['title']}" for r in cur.fetchall()) + '\nhttps://www.phbay.info/#contact'
        else:
            detail = '目前可用優惠依潮旅官方最新公告；系統不會顯示尚未定案的折抵承諾。'
        cur.close(); conn.close()
        return f"{member['name']} 您好｜{member['member_no']}\n{detail}\n\n可輸入：我的等級／我的旅次／我的點數／下一趟推薦"
    except Exception as exc:
        print(f'[MEMBER LINE COMMAND] {exc}')
        return '會員資料暫時無法讀取，請稍後再試。'


@app.route('/api/line/webhook', methods=['POST'])
def line_webhook():
    """LINE 官方帳號 webhook：驗簽後記錄互動用戶；
    傳「綁定通知」的用戶會收到自己的 userId（供設定 LINE_OWNER_USER_ID）。"""
    secret = os.environ.get('LINE_CHANNEL_SECRET', '').strip()
    if not secret:
        return jsonify(ok=False, error='LINE_CHANNEL_SECRET 未設定'), 503
    body = request.get_data()
    signature = request.headers.get('X-Line-Signature', '')
    expected = base64.b64encode(hmac.new(secret.encode('utf-8'), body, hashlib.sha256).digest()).decode()
    if not hmac.compare_digest(signature, expected):
        return jsonify(ok=False, error='簽章驗證失敗'), 403

    try:
        events = (json.loads(body.decode('utf-8')) or {}).get('events', [])
    except Exception:
        events = []
    for ev in events:
        try:
            user_id = ((ev.get('source') or {}).get('userId') or '').strip()
            if not user_id:
                continue
            etype = ev.get('type')
            text = ''
            if etype == 'message' and (ev.get('message') or {}).get('type') == 'text':
                text = ((ev.get('message') or {}).get('text') or '').strip()
            display_name = _line_get_profile(user_id)
            conn = get_db(); cur = conn.cursor()
            cur.execute("""
                INSERT INTO line_users (user_id, display_name, last_message, message_count)
                VALUES (%s, %s, %s, 1)
                ON CONFLICT (user_id) DO UPDATE SET
                  display_name = COALESCE(NULLIF(EXCLUDED.display_name, ''), line_users.display_name),
                  last_message = CASE WHEN EXCLUDED.last_message <> '' THEN EXCLUDED.last_message ELSE line_users.last_message END,
                  message_count = line_users.message_count + 1,
                  last_seen = NOW()
            """, (user_id, display_name, text))
            conn.commit(); cur.close(); conn.close()
            member_reply = _try_bind_member_line(user_id, text) if text else None
            if not member_reply and text:
                member_reply = _member_line_command(user_id, text)
            if member_reply and ev.get('replyToken'):
                _line_reply(ev['replyToken'], member_reply)
            elif text and text.lower().replace(' ', '') in LINE_BIND_KEYWORDS and ev.get('replyToken'):
                _line_reply(ev['replyToken'],
                            f'您的 LINE userId 是：\n{user_id}\n\n'
                            '（此代碼供潮旅系統設定通知使用，一般旅客不需理會）')
        except Exception as e:
            print(f'[LINE] webhook 事件處理失敗（略過）：{e}')
    return 'OK', 200


@app.route('/api/admin/line-test', methods=['GET', 'POST'])
def admin_line_test():
    """診斷 LINE 通知設定：檢查環境變數並實際推播一則測試訊息給老闆。"""
    if not is_admin():
        return jsonify(ok=False, error='未授權'), 401
    has_token = bool(os.environ.get('LINE_CHANNEL_ACCESS_TOKEN', '').strip())
    has_secret = bool(os.environ.get('LINE_CHANNEL_SECRET', '').strip())
    owner = os.environ.get('LINE_OWNER_USER_ID', '').strip()
    if not has_token or not owner:
        return jsonify(ok=False, configured=False,
                       has_token=has_token, has_secret=has_secret, has_owner=bool(owner),
                       error='需設定 LINE_CHANNEL_ACCESS_TOKEN 與 LINE_OWNER_USER_ID'
                             '（webhook 另需 LINE_CHANNEL_SECRET）。')
    ok, detail = send_line_notify('【測試】潮旅 LINE 通知設定成功！日後新預購訂單與諮詢會即時推播到這裡。')
    if ok:
        return jsonify(ok=True, configured=True, has_secret=has_secret, via='line-messaging-api',
                       message='測試訊息已推播，請查看您的 LINE。')
    return jsonify(ok=False, configured=True, has_secret=has_secret, error=f'推播失敗：{detail}')


@app.route('/api/admin/line-users', methods=['GET'])
def admin_line_users():
    """列出曾與官方帳號互動的用戶（webhook 記錄），供查 userId 與對照訂單。"""
    if not is_admin():
        return jsonify(ok=False, error='未授權'), 401
    try:
        conn = get_db(); cur = conn.cursor()
        cur.execute("SELECT * FROM line_users ORDER BY last_seen DESC LIMIT 200")
        users = []
        for r in cur.fetchall():
            r = dict(r)
            for k in ('first_seen', 'last_seen'):
                if r.get(k): r[k] = str(r[k])
            users.append(r)
        cur.close(); conn.close()
        return jsonify(ok=True, users=users)
    except Exception as e:
        return jsonify(ok=False, error=str(e)), 500


# ─── Gemini AI 輔助（部落格草稿／諮詢回覆建議／診斷個人化）───
from gemini_helper import gemini_generate, gemini_available, resolve_model, list_models

@app.route('/api/admin/gemini-test', methods=['GET', 'POST'])
def admin_gemini_test():
    """診斷 Gemini 設定：檢查金鑰、回報自動選用的模型並實際打一次 API。"""
    if not is_admin():
        return jsonify(ok=False, error='未授權'), 401
    if not gemini_available():
        return jsonify(ok=False, configured=False, error='GEMINI_API_KEY 未設定')
    try:
        model = resolve_model()
        text = gemini_generate('請只回覆兩個字：正常', temperature=0)
        return jsonify(ok=True, configured=True, model=model,
                       reply=(text or '').strip()[:50])
    except Exception as e:
        models = []
        try:
            models = list_models()[:20]
        except Exception:
            pass
        return jsonify(ok=False, configured=True, error=str(e),
                       available_models=models), 502


@app.route('/api/admin/gemini/blog-draft', methods=['POST'])
def admin_gemini_blog_draft():
    """後台文章編輯器「AI 產生草稿」：給主題，回整篇草稿欄位。"""
    if not has_role('editor'):
        return jsonify(ok=False, error='未授權'), 401
    d = request.get_json(force=True, silent=True) or {}
    topic = (d.get('topic') or '').strip()[:120]
    notes = (d.get('notes') or '').strip()[:300]
    if not topic:
        return jsonify(ok=False, error='請先輸入文章主題'), 400
    prompt = f"""你是澎湖在地旅行社「潮旅國際旅行社」的部落格編輯，為官網 https://www.phbay.info/blog 寫文章草稿。

文章主題：{topic}
{('補充要求：' + notes) if notes else ''}

寫作規範（務必遵守）：
1. 繁體中文（台灣用語），親切、在地、實用，不浮誇。全文約 900–1300 字。
2. content 為 HTML：只用 <h2> <h3> <p> <strong> <ul> <li> <a> 標籤；2–4 個 <h2> 段落。
3. summary 寫成 2–3 句「先講結論」式摘要（會顯示在文章開頭的結論框），不要釣魚式開頭。
4. 內文自然放入 1 個相關主題攻略頁連結（美食主題連 /penghu-food-guide、親子連 /penghu-family-travel、行程景點連 /penghu-3days-itinerary、音樂節連 /penghu-2026-festival-guide），
   以及文末 1 句 CTA 引導加官方 LINE @phbay2018 或造訪 https://www.phbay.info/。
5. 絕對不可捏造：具體店名、地址、價格、營業時間、船班時刻、活動細節。不確定的就用通稱（例如「馬公市區的老字號店家」）。
6. tags 為 4–6 個逗號分隔標籤，第一個必須是「澎湖美食」「澎湖景點」或「澎湖旅遊」其中之一。
7. slug 為小寫英數與連字號（不含日期），例如 penghu-xxx-guide。
8. faq 為 3–5 題文末常見問題（q 是使用者真的會搜尋的問題、a 為 2–4 句回答）。

請回傳 JSON 物件，鍵為：title, slug, summary, content, tags, faq（faq 為 [{{"q":"...","a":"..."}}] 陣列）。"""
    try:
        draft = gemini_generate(prompt, json_mode=True, timeout=90)
        if not isinstance(draft, dict) or not draft.get('title'):
            return jsonify(ok=False, error='AI 回傳格式異常，請再試一次'), 502
        return jsonify(ok=True, draft={
            'title': str(draft.get('title', ''))[:200],
            'slug': re.sub(r'[^a-z0-9-]', '', str(draft.get('slug', '')).lower())[:120],
            'summary': str(draft.get('summary', ''))[:500],
            'content': str(draft.get('content', '')),
            'tags': str(draft.get('tags', ''))[:200],
            'faq': draft.get('faq') if isinstance(draft.get('faq'), list) else [],
        })
    except Exception as e:
        return jsonify(ok=False, error=str(e)), 502


@app.route('/api/admin/gemini/reply-suggest', methods=['POST'])
def admin_gemini_reply_suggest():
    """諮詢紀錄「AI 建議回覆」：依旅客表單內容草擬 LINE 回覆。"""
    if not has_role('orders'):
        return jsonify(ok=False, error='未授權'), 401
    d = request.get_json(force=True, silent=True) or {}
    c = d.get('contact') or {}
    fields = []
    for label, key in (('姓名', 'name'), ('旅遊日期', 'travel_date'), ('回程日', 'travel_date_end'),
                       ('人數', 'people'), ('交通方式', 'transport'), ('出發地', 'departure_city'),
                       ('預算', 'budget'), ('有興趣的行程', 'tour_interest'), ('備註', 'notes')):
        v = str(c.get(key) or '').strip()[:120]
        if v:
            fields.append(f'{label}：{v}')
    if not fields:
        return jsonify(ok=False, error='缺少旅客資料'), 400
    prompt = f"""你是澎湖在地旅行社「潮旅國際旅行社」的訂位人員，要用 LINE 回覆一位剛送出線上諮詢的旅客。

旅客資料：
{chr(10).join(fields)}

請草擬一則 LINE 回覆訊息（純文字，不用 markdown）：
1. 繁體中文（台灣用語），親切專業，150–250 字。
2. 開頭稱呼旅客姓名，感謝諮詢；針對旅客的日期、人數、預算與需求給 1–2 個具體的安排方向建議。
3. 結尾提出 1 個推進問題（例如確認日期彈性或想玩的重點），並附上聯絡資訊：電話 06-9271288（週一至週五 08:30–17:30）。
4. 絕對不可承諾或編造：具體價格、名額、船班、優惠。價格一律說「依日期與住宿等級專人報價」。
5. 署名「潮旅國際旅行社」。"""
    try:
        reply = gemini_generate(prompt, timeout=60)
        return jsonify(ok=True, reply=(reply or '').strip()[:1500])
    except Exception as e:
        return jsonify(ok=False, error=str(e)), 502


# 行程診斷個人化說明：公開端點 → 需節流（記憶體內簡易限流，每 IP 10 分鐘 5 次）
_QUIZ_AI_HITS = {}

def _quiz_ai_rate_ok(ip):
    import time as _t
    now = _t.time()
    hits = [t for t in _QUIZ_AI_HITS.get(ip, []) if now - t < 600]
    if len(hits) >= 5:
        _QUIZ_AI_HITS[ip] = hits
        return False
    hits.append(now)
    _QUIZ_AI_HITS[ip] = hits
    if len(_QUIZ_AI_HITS) > 5000:  # 防記憶體無限成長
        _QUIZ_AI_HITS.clear()
    return True

_QUIZ_AI_RESULTS = {'neihai': '內海慢遊', 'festival': '追風音樂節', 'family': '親子海島',
                    'island': '望安七美跳島', 'tides': '潮汐秘境'}

@app.route('/api/quiz-ai', methods=['POST'])
def quiz_ai_note():
    """行程診斷結果的個人化補充說明（失敗時前端靜默略過，不影響原結果）。"""
    if not gemini_available():
        return jsonify(ok=False, error='未設定'), 200
    if not _quiz_ai_rate_ok(_client_ip()):
        return jsonify(ok=False, error='rate limited'), 200
    d = request.get_json(force=True, silent=True) or {}
    result = str(d.get('result') or '')
    if result not in _QUIZ_AI_RESULTS:
        return jsonify(ok=False, error='bad result'), 200
    answers = d.get('answers') or []
    lines = []
    for a in answers[:6]:
        q = str((a or {}).get('q') or '').strip()[:60]
        v = str((a or {}).get('a') or '').strip()[:60]
        if q and v:
            lines.append(f'{q}：{v}')
    prompt = f"""你是澎湖在地旅行社「潮旅國際旅行社」的行程顧問。旅客剛完成 30 秒行程診斷，
測出的旅遊類型是「{_QUIZ_AI_RESULTS[result]}」路線。

旅客的作答：
{chr(10).join(lines) if lines else '（無詳細作答）'}

請用繁體中文寫 2–3 句（80 字內）給這位旅客的個人化建議，依作答中的月份、同行對象、
天數與預算，說明這條路線對他最值得注意的 1–2 個安排重點。口吻親切像在地朋友。
不可提及具體價格、名額或店名；不用打招呼與署名，直接講重點。"""
    try:
        text = gemini_generate(prompt, timeout=25, temperature=0.8)
        return jsonify(ok=True, text=(text or '').strip()[:300])
    except Exception:
        return jsonify(ok=False, error='ai unavailable'), 200


# ─── 通用預購系統（音樂節等；每個行程一筆 preorder_products）───
PREORDER_VALID_STATUSES = {'pending_departure', 'confirmed_departure', 'confirmed', 'completed', 'cancelled'}


def _get_product(slug, cur):
    cur.execute("SELECT * FROM preorder_products WHERE slug=%s AND is_active=TRUE", (slug,))
    return cur.fetchone()


def _product_public(p):
    return {
        'slug': p['slug'], 'name': p['name'], 'description': p.get('description') or '',
        'slot_type': p['slot_type'],
        'times': [t.strip() for t in (p.get('times') or '').split(',') if t.strip()],
        'duration_days': int(p['duration_days'] or 1),
        'capacity': p['capacity'],  # None = 不設上限
        'min_people': int(p['min_people'] or 2),
        'max_party': int(p['max_party'] or 13),
        'date_start': str(p['date_start'] or ''), 'date_end': str(p['date_end'] or ''),
        'badges': [b.strip() for b in (p.get('badges') or '').split(',') if b.strip()],
    }


def _preorder_slot_status(booked, capacity, min_people):
    """通用場次狀態；capacity=None 表示不設上限。"""
    booked = int(booked or 0)
    min_people = int(min_people or 2)
    if capacity is not None and booked >= int(capacity):
        return 'full', '已額滿', 0
    remaining = (int(capacity) - booked) if capacity is not None else None
    if booked >= min_people:
        return 'guaranteed', f'已達 {booked} 人，確定成行', remaining
    return 'forming', f'待成團，還差 {min_people - booked} 人', remaining


def _preorder_availability(product, start, end):
    """回傳 product 在 [start, end) 內、未過期的可預購場次。"""
    conn = get_db(); cur = conn.cursor()
    cur.execute("""
        SELECT departure_date, departure_time,
               COALESCE(SUM(CASE WHEN status <> 'cancelled' THEN passenger_count ELSE 0 END), 0) AS booked
        FROM preorder_orders
        WHERE product_id=%s AND departure_date >= %s AND departure_date < %s
        GROUP BY departure_date, departure_time
    """, (product['id'], start, end))
    booked_map = {(str(r['departure_date']), r['departure_time'] or ''): int(r['booked'])
                  for r in cur.fetchall()}
    cur.close(); conn.close()

    today = _taiwan_now().date()
    lo = max(start, product['date_start'] or start)
    hi = min(end - timedelta(days=1), product['date_end'] or (end - timedelta(days=1)))
    times = [t.strip() for t in (product.get('times') or '').split(',') if t.strip()] \
        if product['slot_type'] == 'times' else ['']
    duration = int(product['duration_days'] or 1)

    items = []
    d = lo
    now = _taiwan_now()
    while d <= hi:
        for tm in times:
            if tm:  # 每日多時段：已過出航時間的不列
                if _sailing_departed(d, tm, now):
                    continue
            elif d < today:  # 套裝行程：過去日期不列
                continue
            booked = booked_map.get((str(d), tm), 0)
            code, label, remaining = _preorder_slot_status(booked, product['capacity'], product['min_people'])
            item = {
                'date': str(d), 'time': tm, 'booked': booked,
                'remaining': remaining, 'status': code, 'status_label': label,
            }
            if duration > 1:
                item['return_date'] = str(d + timedelta(days=duration - 1))
            items.append(item)
        d += timedelta(days=1)
    return items


@app.route('/api/preorder/<slug>')
def api_preorder_product(slug):
    try:
        conn = get_db(); cur = conn.cursor()
        p = _get_product(slug, cur)
        cur.close(); conn.close()
        if not p:
            return jsonify(ok=False, error='找不到此預購行程'), 404
        return jsonify(ok=True, product=_product_public(p))
    except Exception as e:
        return jsonify(ok=False, error=str(e)), 500


@app.route('/api/preorder/<slug>/slots')
def api_preorder_slots(slug):
    try:
        conn = get_db(); cur = conn.cursor()
        p = _get_product(slug, cur)
        cur.close(); conn.close()
        if not p:
            return jsonify(ok=False, error='找不到此預購行程'), 404
        start, end = _parse_month(request.args.get('month'))
        return jsonify(ok=True, month=start.strftime('%Y-%m'),
                       product=_product_public(p),
                       slots=_preorder_availability(p, start, end))
    except ValueError as e:
        return jsonify(ok=False, error=str(e)), 400
    except Exception as e:
        return jsonify(ok=False, error=str(e)), 500


@app.route('/api/preorder/<slug>/orders', methods=['POST'])
def api_preorder_create(slug):
    data = request.get_json(force=True, silent=True) or {}
    try:
        conn = get_db(); cur = conn.cursor()
        p = _get_product(slug, cur)
        if not p:
            cur.close(); conn.close()
            return jsonify(ok=False, error='找不到此預購行程'), 404

        try:
            dep_date = _parse_sailing_date(data.get('departure_date'))
        except ValueError as e:
            cur.close(); conn.close()
            return jsonify(ok=False, error=str(e)), 400
        dep_time = (data.get('departure_time') or '').strip()

        # 日期／時段驗證
        if p['date_start'] and dep_date < p['date_start'] or p['date_end'] and dep_date > p['date_end']:
            cur.close(); conn.close()
            return jsonify(ok=False, error='出發日不在開放預購範圍內'), 400
        if p['slot_type'] == 'times':
            valid_times = [t.strip() for t in (p.get('times') or '').split(',') if t.strip()]
            if dep_time not in valid_times:
                cur.close(); conn.close()
                return jsonify(ok=False, error='出發時間不正確'), 400
            if _sailing_departed(dep_date, dep_time):
                cur.close(); conn.close()
                return jsonify(ok=False, error='此場次已過出發時間，請重新選擇'), 400
        else:
            dep_time = ''
            if dep_date < _taiwan_now().date():
                cur.close(); conn.close()
                return jsonify(ok=False, error='出發日已過，請重新選擇'), 400

        # 乘客驗證（同內海格式）
        passengers = data.get('passengers') or []
        max_party = int(p['max_party'] or 13)
        if not isinstance(passengers, list) or not (1 <= len(passengers) <= max_party):
            cur.close(); conn.close()
            return jsonify(ok=False, error=f'乘客人數需為 1 至 {max_party} 人'), 400
        clean = []
        for idx, ps in enumerate(passengers, start=1):
            name = (ps.get('name') or '').strip()
            national_id = (ps.get('national_id') or '').strip().upper()
            phone = (ps.get('phone') or '').strip()
            birth = (ps.get('birth_date') or '').strip()
            # 電話僅第 1 位（代表人）必填，其餘旅客選填
            if not all([name, national_id, birth]):
                cur.close(); conn.close()
                return jsonify(ok=False, error=f'第 {idx} 位旅客資料未填完整'), 400
            if idx == 1 and not phone:
                cur.close(); conn.close()
                return jsonify(ok=False, error='第 1 位旅客為代表人，請填寫聯絡電話'), 400
            try:
                birth_date = datetime.strptime(birth, '%Y-%m-%d').date()
            except ValueError:
                cur.close(); conn.close()
                return jsonify(ok=False, error=f'第 {idx} 位旅客生日格式需為 YYYY-MM-DD'), 400
            clean.append({'name': name, 'national_id': national_id,
                          'birth_date': birth_date, 'phone': phone})

        contact_name = clean[0]['name']
        contact_phone = (data.get('contact_phone') or clean[0]['phone']).strip()
        contact_email = (data.get('contact_email') or '').strip()
        if contact_email and not EMAIL_RE.match(contact_email):
            cur.close(); conn.close()
            return jsonify(ok=False, error='Email 格式不正確，請確認後再送出（或留空）'), 400
        agency_name = (data.get('agency_name') or '').strip()
        notes = (data.get('notes') or '').strip()

        # 同場次交易鎖（避免有名額上限的行程超賣）
        lock_key = abs(hash((p['id'], str(dep_date), dep_time))) % (2 ** 31)
        cur.execute('SELECT pg_advisory_xact_lock(%s)', (lock_key,))
        cur.execute("""
            SELECT COALESCE(SUM(passenger_count), 0) AS booked FROM preorder_orders
            WHERE product_id=%s AND departure_date=%s AND departure_time=%s AND status <> 'cancelled'
        """, (p['id'], dep_date, dep_time))
        booked = int(cur.fetchone()['booked'] or 0)
        if p['capacity'] is not None and booked + len(clean) > int(p['capacity']):
            conn.rollback(); cur.close(); conn.close()
            return jsonify(ok=False, error=f'此場次剩餘 {max(0, int(p["capacity"]) - booked)} 位，不足以容納本次人數'), 400

        status = 'confirmed_departure' if booked + len(clean) >= int(p['min_people']) else 'pending_departure'
        cur.execute("""
            INSERT INTO preorder_orders
              (product_id, departure_date, departure_time, agency_name,
               contact_name, contact_phone, contact_email, passenger_count, status, notes, utm)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            RETURNING id, created_at
        """, (p['id'], dep_date, dep_time, agency_name, contact_name,
              contact_phone, contact_email, len(clean), status, notes,
              Json({k: str(v)[:200] for k, v in (data.get('utm') or {}).items()
                    if k.startswith('utm_') or k in ('landing_page', 'referrer')})))
        order = cur.fetchone()
        booking_ref = f"{slug[:6].upper()}{dep_date.strftime('%Y%m%d')}-{int(order['id']):04d}"
        cur.execute('UPDATE preorder_orders SET booking_ref=%s WHERE id=%s', (booking_ref, order['id']))
        for ps in clean:
            cur.execute("""
                INSERT INTO preorder_passengers (order_id, name, national_id, birth_date, phone)
                VALUES (%s,%s,%s,%s,%s)
            """, (order['id'], ps['name'], ps['national_id'], ps['birth_date'], ps['phone']))
        conn.commit(); cur.close(); conn.close()

        try:
            send_preorder_email({
                'product': p.get('name') or slug,
                'booking_ref': booking_ref,
                'date': str(dep_date), 'time': dep_time,
                'passenger_count': len(clean), 'status': status,
                'agency_name': agency_name, 'contact_name': contact_name,
                'contact_phone': contact_phone, 'notes': notes,
                'passenger_names': [ps['name'] for ps in clean],
            })
        except Exception as _e:
            print(f'[EMAIL] 預購通知呼叫失敗（不影響訂單）：{_e}')

        try:
            send_customer_confirmation_email({
                'product': p.get('name') or slug,
                'booking_ref': booking_ref,
                'date': str(dep_date), 'time': dep_time,
                'passenger_count': len(clean), 'status': status,
                'agency_name': agency_name, 'contact_name': contact_name,
                'contact_email': contact_email, 'notes': notes,
            })
        except Exception as _e:
            print(f'[EMAIL] 客人確認信呼叫失敗（不影響訂單）：{_e}')

        code, label, remaining = _preorder_slot_status(booked + len(clean), p['capacity'], p['min_people'])
        return jsonify(
            ok=True, id=order['id'], booking_ref=booking_ref,
            created_at=str(order['created_at']),
            departure_date=str(dep_date), departure_time=dep_time,
            passenger_count=len(clean),
            slot_status=code, slot_status_label=label, remaining=remaining,
            message='預購已送出，已確定成行' if code in ('guaranteed', 'full')
                    else f'預購已送出，尚差 {int(p["min_people"]) - booked - len(clean)} 人成行',
        )
    except Exception as e:
        return jsonify(ok=False, error=f'伺服器錯誤：{e}'), 500


@app.route('/api/admin/preorder/products', methods=['GET'])
def admin_preorder_products():
    """預購商品的旅次認列政策清單。

    規劃書載明：代售產品不得認列為潮旅旅次，否則會員等級會灌水。
    這支同時回報「目前已認列幾筆」，讓管理者在切換政策前先看到影響範圍。
    """
    if not has_role('orders'):
        return jsonify(ok=False, error='未授權'), 401
    try:
        conn = get_db(); cur = conn.cursor()
        cur.execute("""
            SELECT p.id, p.slug, p.name, p.is_active, p.counts_as_trip,
                   (SELECT COUNT(*) FROM preorder_orders o
                     WHERE o.product_id=p.id AND o.status='completed') AS completed_orders,
                   (SELECT COUNT(*) FROM member_trips t
                     WHERE t.source_type='preorder_order' AND t.status='completed'
                       AND t.counts_trip=TRUE
                       AND t.source_ref IN (SELECT o2.booking_ref FROM preorder_orders o2
                                             WHERE o2.product_id=p.id)) AS counted_trips
            FROM preorder_products p
            ORDER BY p.is_active DESC, p.id
        """)
        products = [dict(row) for row in cur.fetchall()]
        cur.close(); conn.close()
        return jsonify(ok=True, products=products, points_per_trip=points_per_trip())
    except Exception as exc:
        print(f'[PREORDER PRODUCTS] {exc}')
        return jsonify(ok=False, error='讀取預購商品失敗'), 500


@app.route('/api/admin/preorder/products/<int:product_id>/counts-as-trip', methods=['PATCH'])
def admin_preorder_product_trip_policy(product_id):
    """切換單一預購商品可否認列為潮旅旅次。

    這是商業政策而非日常訂位作業，因此限 owner。預設一併校正該商品既有的旅次，
    否則設錯之後只能人工逐筆改——這正是規劃書要求「先界定哪些行程可認列」的原因。
    點數帳本走 sync_trip_points 的差額沖銷，不會竄改歷史紀錄。
    """
    if not is_admin():
        return jsonify(ok=False, error='僅管理者可調整旅次認列政策'), 401
    data = request.get_json(force=True, silent=True) or {}
    if 'counts_as_trip' not in data:
        return jsonify(ok=False, error='缺少 counts_as_trip'), 400
    counts = bool(data.get('counts_as_trip'))
    apply_existing = bool(data.get('apply_to_existing', True))
    conn = None
    try:
        conn = get_db(); cur = conn.cursor()
        cur.execute("""UPDATE preorder_products SET counts_as_trip=%s, updated_at=NOW()
                       WHERE id=%s RETURNING slug,name""", (counts, product_id))
        product = cur.fetchone()
        if not product:
            conn.rollback(); cur.close(); conn.close()
            return jsonify(ok=False, error='找不到預購商品'), 404
        affected_members = set()
        affected_trips = 0
        if apply_existing:
            cur.execute("""SELECT id, member_id FROM member_trips
                           WHERE source_type='preorder_order' AND counts_trip <> %s
                             AND source_ref IN (SELECT booking_ref FROM preorder_orders
                                                 WHERE product_id=%s)
                           FOR UPDATE""", (counts, product_id))
            rows = cur.fetchall()
            for row in rows:
                cur.execute("UPDATE member_trips SET counts_trip=%s, updated_at=NOW() WHERE id=%s",
                            (counts, row['id']))
                sync_trip_points(cur, row['id'])
                affected_members.add(row['member_id'])
            affected_trips = len(rows)
            for member_id in affected_members:
                recalculate_member(cur, member_id)
        write_audit(cur, 'update', '旅次認列政策', product['slug'], affected_trips, 0,
                    f"{product['name']}：{'可認列' if counts else '不認列'}"
                    f"；校正既有旅次 {affected_trips} 筆／{len(affected_members)} 位會員")
        conn.commit(); cur.close(); conn.close()
        return jsonify(ok=True, counts_as_trip=counts, affected_trips=affected_trips,
                       affected_members=len(affected_members))
    except Exception as exc:
        try:
            if conn: conn.rollback(); conn.close()
        except Exception:
            pass
        print(f'[PREORDER TRIP POLICY] {exc}')
        return jsonify(ok=False, error='更新旅次認列政策失敗'), 500


@app.route('/api/admin/preorder/orders', methods=['GET'])
def admin_preorder_orders():
    if not has_role('orders'):
        return jsonify(ok=False, error='未授權'), 401
    try:
        start, end = _parse_month(request.args.get('month'))
        slug = (request.args.get('product') or '').strip()
        conn = get_db(); cur = conn.cursor()
        params = [start, end]
        where = 'o.departure_date >= %s AND o.departure_date < %s'
        if slug:
            where += ' AND pr.slug = %s'
            params.append(slug)
        cur.execute(f"""
            SELECT o.*, pr.slug AS product_slug, pr.name AS product_name,
                   pr.duration_days, pr.min_people, pr.capacity
            FROM preorder_orders o JOIN preorder_products pr ON pr.id = o.product_id
            WHERE {where}
            ORDER BY o.departure_date, o.departure_time, o.created_at
        """, params)
        orders = [dict(r) for r in cur.fetchall()]
        ids = [o['id'] for o in orders]
        passengers_by_order = {i: [] for i in ids}
        logs_by_order = {i: [] for i in ids}
        if ids:
            cur.execute('SELECT * FROM preorder_passengers WHERE order_id = ANY(%s) ORDER BY order_id, id', (ids,))
            for r in cur.fetchall():
                r = dict(r)
                r['birth_date'] = str(r['birth_date'])
                if r.get('created_at'): r['created_at'] = str(r['created_at'])
                passengers_by_order[r['order_id']].append(r)
            cur.execute("""SELECT order_id, summary, changed_at FROM preorder_order_logs
                           WHERE order_id = ANY(%s) ORDER BY order_id, changed_at DESC""", (ids,))
            for r in cur.fetchall():
                logs_by_order[r['order_id']].append({'summary': r['summary'], 'changed_at': str(r['changed_at'])})
        cur.execute('SELECT slug, name FROM preorder_products WHERE is_active=TRUE ORDER BY id')
        products = [dict(r) for r in cur.fetchall()]
        cur.close(); conn.close()
        for o in orders:
            for k in ('departure_date', 'created_at', 'updated_at'):
                if o.get(k): o[k] = str(o[k])
            o['passengers'] = passengers_by_order.get(o['id'], [])
            o['logs'] = logs_by_order.get(o['id'], [])
        return jsonify(ok=True, month=start.strftime('%Y-%m'), orders=orders, products=products)
    except ValueError as e:
        return jsonify(ok=False, error=str(e)), 400
    except Exception as e:
        return jsonify(ok=False, error=str(e)), 500


@app.route('/api/admin/preorder/orders/<int:order_id>', methods=['PATCH'])
def admin_update_preorder(order_id):
    """更新通用預購訂單：狀態、封存、聯絡/業者/備註、出發日期時間、乘客資料。"""
    if not has_role('orders'):
        return jsonify(ok=False, error='未授權'), 401
    data = request.get_json(force=True, silent=True) or {}
    try:
        conn = get_db(); cur = conn.cursor()
        cur.execute("SELECT * FROM preorder_orders WHERE id=%s", (order_id,))
        order = cur.fetchone()
        if not order:
            cur.close(); conn.close()
            return jsonify(ok=False, error='找不到訂單'), 404
        order = dict(order)
        set_parts, params, changes = [], [], []
        FLABEL = {'agency_name': '業者', 'contact_name': '主要聯絡姓名', 'contact_phone': '聯絡電話',
                  'contact_email': 'Email', 'notes': '備註'}

        if 'status' in data:
            status = (data.get('status') or '').strip()
            if status not in PREORDER_VALID_STATUSES:
                cur.close(); conn.close()
                return jsonify(ok=False, error='狀態不正確'), 400
            if status != order['status']:
                changes.append(f"狀態：{NEIHAI_STATUS_LABELS.get(order['status'], order['status'])}"
                               f" → {NEIHAI_STATUS_LABELS.get(status, status)}")
                set_parts.append('status=%s'); params.append(status)

        if 'archived' in data:
            new_arch = bool(data.get('archived'))
            if new_arch != bool(order.get('archived')):
                changes.append('封存訂單' if new_arch else '取消封存')
                set_parts.append('archived=%s'); params.append(new_arch)

        for field in ('agency_name', 'contact_name', 'contact_phone', 'contact_email', 'notes'):
            if field in data:
                v = (data.get(field) or '').strip()
                if field in ('contact_name', 'contact_phone') and not v:
                    cur.close(); conn.close()
                    return jsonify(ok=False, error='聯絡姓名與電話不可空白'), 400
                if v != (order.get(field) or ''):
                    changes.append(f"{FLABEL[field]}：{order.get(field) or '（空）'} → {v or '（空）'}")
                    set_parts.append(f'{field}=%s'); params.append(v)

        if data.get('departure_date'):
            try:
                dep = datetime.strptime(str(data['departure_date']).strip(), '%Y-%m-%d').date()
            except ValueError:
                cur.close(); conn.close()
                return jsonify(ok=False, error='出發日期格式需為 YYYY-MM-DD'), 400
            if str(dep) != str(order.get('departure_date')):
                changes.append(f"出發日期：{order.get('departure_date')} → {dep}")
                set_parts.append('departure_date=%s'); params.append(dep)
        if 'departure_time' in data:
            nt = (data.get('departure_time') or '').strip()
            if nt != (order.get('departure_time') or ''):
                changes.append(f"出發時間：{order.get('departure_time') or '（空）'} → {nt or '（空）'}")
                set_parts.append('departure_time=%s'); params.append(nt)

        if set_parts:
            set_parts.append('updated_at=NOW()')
            cur.execute(f"UPDATE preorder_orders SET {', '.join(set_parts)} WHERE id=%s",
                        tuple(params) + (order_id,))

        passengers = data.get('passengers')
        if isinstance(passengers, list):
            cur.execute("SELECT * FROM preorder_passengers WHERE order_id=%s", (order_id,))
            existing = {r['id']: dict(r) for r in cur.fetchall()}
            for i, p in enumerate(passengers, 1):
                cur_p = existing.get(p.get('id'))
                if not cur_p:
                    continue
                pset, pparams = [], []
                for f in ('name', 'national_id', 'birth_date', 'phone'):
                    if f not in p:
                        continue
                    v = str(p.get(f) or '').strip()
                    if f == 'national_id':
                        v = v.upper()
                    if f == 'birth_date':
                        try:
                            v = str(datetime.strptime(v, '%Y-%m-%d').date())
                        except ValueError:
                            cur.close(); conn.close()
                            return jsonify(ok=False, error=f'第 {i} 位旅客生日格式需為 YYYY-MM-DD'), 400
                    elif f in ('name', 'national_id') and not v:
                        cur.close(); conn.close()
                        return jsonify(ok=False, error=f'第 {i} 位旅客姓名/身分證不可空白'), 400
                    if v != str(cur_p.get(f) or ''):
                        plabel = {'name': '姓名', 'national_id': '身分證字號', 'birth_date': '生日', 'phone': '電話'}[f]
                        changes.append(f"旅客「{cur_p['name']}」{plabel}：{cur_p.get(f) or ''} → {v}")
                        pset.append(f'{f}=%s'); pparams.append(v)
                if pset:
                    cur.execute(f"UPDATE preorder_passengers SET {', '.join(pset)} WHERE id=%s",
                                tuple(pparams) + (cur_p['id'],))

        if changes:
            cur.execute("INSERT INTO preorder_order_logs (order_id, summary) VALUES (%s,%s)",
                        (order_id, "；".join(changes)))
        member_sync = None
        if 'status' in data:
            cur.execute("""SELECT o.booking_ref,o.contact_phone,o.departure_date,o.status,
                                  p.name,p.counts_as_trip
                           FROM preorder_orders o JOIN preorder_products p ON p.id=o.product_id
                           WHERE o.id=%s""", (order_id,))
            synced = cur.fetchone()
            if synced:  # JOIN 失配時不可讓訂單更新整筆失敗
                member_sync = _sync_completed_order_trip(
                    cur, 'preorder_order', synced['booking_ref'],
                    synced['contact_phone'], synced['name'],
                    synced['departure_date'], synced['status'],
                    counts_trip=bool(synced.get('counts_as_trip', True)))
        conn.commit(); cur.close(); conn.close()
        # LINE 升等通知在 commit 之後才送：網路呼叫不該佔著訂單的列鎖，
        # 失敗也絕不能回頭影響已經寫進去的訂單狀態。
        if member_sync and member_sync.get('notify'):
            _line_api_call('message/push', {'to': member_sync['notify'][0],
                                            'messages': [{'type': 'text',
                                                          'text': member_sync['notify'][1]}]})
        return jsonify(ok=True)
    except Exception as e:
        return jsonify(ok=False, error=str(e)), 500


@app.route('/api/admin/preorder/orders/<int:order_id>', methods=['DELETE'])
def admin_delete_preorder(order_id):
    """刪除通用預購訂單（旅客隨 CASCADE 一併刪除）。"""
    if not has_role('orders'):
        return jsonify(ok=False, error='未授權'), 401
    try:
        conn = get_db(); cur = conn.cursor()
        cur.execute("SELECT booking_ref FROM preorder_orders WHERE id=%s", (order_id,))
        row = cur.fetchone()
        if not row:
            cur.close(); conn.close()
            return jsonify(ok=False, error='找不到訂單'), 404
        cur.execute("DELETE FROM preorder_orders WHERE id=%s", (order_id,))
        conn.commit(); cur.close(); conn.close()
        return jsonify(ok=True, booking_ref=row['booking_ref'])
    except Exception as e:
        return jsonify(ok=False, error=str(e)), 500


@app.route('/api/admin/preorder/import', methods=['POST'])
def admin_preorder_import():
    """後台批次匯入通用行程預購訂單（CSV 與匯出同格式；行程以名稱或 slug 對應）。
    規則同內海匯入：booking_ref 重複略過、超額僅警告、不發通知。"""
    if not has_role('orders'):
        return jsonify(ok=False, error='未授權'), 401
    data = request.get_json(force=True, silent=True) or {}
    orders = data.get('orders') or []
    overwrite = (data.get('mode') or '').strip() == 'overwrite'
    if not isinstance(orders, list) or not orders:
        return jsonify(ok=False, error='沒有可匯入的訂單'), 400
    created, updated, skipped, errors, warnings = [], [], [], [], []
    try:
        conn = get_db(); cur = conn.cursor()
        cur.execute("SELECT * FROM preorder_products")
        products = cur.fetchall()
        by_key = {}
        for p in products:
            by_key[p['slug'].strip().lower()] = p
            by_key[p['name'].strip()] = p
        for i, o in enumerate(orders, start=1):
            pkey = (o.get('product') or '').strip()
            prod = by_key.get(pkey) or by_key.get(pkey.lower())
            if not prod:
                errors.append(f'第 {i} 筆：找不到行程「{pkey}」'); continue
            try:
                dep_date = datetime.strptime((o.get('departure_date') or '').strip(), '%Y-%m-%d').date()
            except ValueError:
                errors.append(f'第 {i} 筆：出發日期格式需為 YYYY-MM-DD'); continue
            dep_time = (o.get('departure_time') or '').strip()
            clean, err = _import_clean_passengers(o.get('passengers'))
            if err:
                errors.append(f'第 {i} 筆：{err}'); continue
            ref = (o.get('booking_ref') or '').strip()
            existing_id = None
            if ref:
                cur.execute("SELECT id FROM preorder_orders WHERE booking_ref=%s", (ref,))
                row = cur.fetchone()
                if row:
                    if not overwrite:
                        skipped.append(ref); continue
                    existing_id = row['id']
            cur.execute("""
                SELECT COALESCE(SUM(passenger_count), 0) AS booked FROM preorder_orders
                WHERE product_id=%s AND departure_date=%s AND departure_time=%s
                  AND status <> 'cancelled' AND id <> %s
            """, (prod['id'], dep_date, dep_time, existing_id or 0))
            booked = int(cur.fetchone()['booked'] or 0)
            status = IMPORT_STATUS_LABELS.get((o.get('status') or '').strip()) or (
                'confirmed_departure' if booked + len(clean) >= int(prod['min_people'] or 2)
                else 'pending_departure')
            if status != 'cancelled' and prod['capacity'] is not None and booked + len(clean) > int(prod['capacity']):
                warnings.append(f"{prod['name']} {dep_date} {dep_time} 匯入後共 {booked + len(clean)} 人，超過上限 {prod['capacity']}")
            agency = (o.get('agency_name') or '').strip()
            cname = (o.get('contact_name') or '').strip() or clean[0]['name']
            cphone = (o.get('contact_phone') or '').strip() or clean[0]['phone']
            cemail = (o.get('contact_email') or '').strip()
            notes = (o.get('notes') or '').strip()
            if existing_id:
                cur.execute("""
                    UPDATE preorder_orders SET product_id=%s, departure_date=%s, departure_time=%s,
                        agency_name=%s, contact_name=%s, contact_phone=%s, contact_email=%s,
                        passenger_count=%s, status=%s, notes=%s, updated_at=NOW() WHERE id=%s
                """, (prod['id'], dep_date, dep_time, agency, cname, cphone, cemail,
                      len(clean), status, notes, existing_id))
                cur.execute("DELETE FROM preorder_passengers WHERE order_id=%s", (existing_id,))
                for ps in clean:
                    cur.execute("""INSERT INTO preorder_passengers (order_id, name, national_id, birth_date, phone)
                                   VALUES (%s,%s,%s,%s,%s)""",
                                (existing_id, ps['name'], ps['national_id'], ps['birth_date'], ps['phone']))
                cur.execute("INSERT INTO preorder_order_logs (order_id, summary) VALUES (%s,%s)",
                            (existing_id, '後台匯入覆蓋更新'))
                updated.append(ref)
            else:
                cur.execute("""
                    INSERT INTO preorder_orders
                      (product_id, departure_date, departure_time, agency_name,
                       contact_name, contact_phone, contact_email, passenger_count, status, notes)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id
                """, (prod['id'], dep_date, dep_time, agency, cname, cphone, cemail,
                      len(clean), status, notes))
                oid = cur.fetchone()['id']
                new_ref = ref or f"{prod['slug'][:6].upper()}{dep_date.strftime('%Y%m%d')}-{int(oid):04d}"
                cur.execute("UPDATE preorder_orders SET booking_ref=%s WHERE id=%s", (new_ref, oid))
                for ps in clean:
                    cur.execute("""INSERT INTO preorder_passengers (order_id, name, national_id, birth_date, phone)
                                   VALUES (%s,%s,%s,%s,%s)""",
                                (oid, ps['name'], ps['national_id'], ps['birth_date'], ps['phone']))
                cur.execute("INSERT INTO preorder_order_logs (order_id, summary) VALUES (%s,%s)",
                            (oid, '後台匯入建立'))
                created.append(new_ref)
        if created or updated:
            pax = sum(len(o.get('passengers') or []) for o in orders)
            write_audit(cur, 'import', category='行程預購',
                        scope=f'新增{len(created)}／覆蓋{len(updated)}',
                        record_count=len(created) + len(updated), pax_count=pax,
                        detail=('覆蓋模式' if overwrite else '一般匯入'))
        conn.commit(); cur.close(); conn.close()
        return jsonify(ok=True, created=created, updated=updated, skipped=skipped,
                       errors=errors, warnings=warnings)
    except Exception as e:
        return jsonify(ok=False, error=str(e)), 500


# 追風音樂節 FAQ：同一份資料同時供「可見 HTML」與「FAQPage 結構化資料」使用，
# 兩者文字務必逐字一致（Google 要求 structured data 與頁面可見內容相符）。
FESTIVAL_FAQ = [
    ("2026 追風音樂節主題行程幾人成行？",
     "兩人即可成行，每一梯次最多 5 人，屬於小團形式。實際出發日期可於預購頁選擇，"
     "潮旅國際旅行社會由專人與您確認名額與行程細節。"),
    ("三天兩夜行程怎麼安排？包含哪些內容？",
     "這是三天兩夜的主題套裝，主軸圍繞 2026 澎湖追風音樂燈光節（觀音亭園區，燈光展演 9/12–10/11），"
     "並搭配澎湖在地玩法。選擇出發日後，回程日自動為第三天；詳細行程內容與報價會由潮旅專人"
     "依您的需求與出發日與您確認。"),
    ("追風音樂節主題行程適合親子嗎？",
     "適合。行程採兩人成行、每梯最多 5 人的小團形式，步調可依同行者調整。若有長輩或孩童同行，"
     "建議在預購時先告知，潮旅會協助安排較適合的節奏與注意事項。"),
    ("沒有交通工具可以參加嗎？",
     "可以。相關接送與交通安排屬於行程細節之一，請在預購時，或透過 LINE @phbay2018、"
     "電話 06-9271288 告知，潮旅專人會與您一併確認。"),
]


def _preorder_seo_section(slug):
    """festival 專頁的伺服器渲染可見內容（介紹＋FAQ），讓爬蟲/AI 不必等 JS 就能取得重點文字。"""
    if slug != 'festival':
        return ''
    faq_html = ''.join(
        f'<details class="preorder-faq-item"><summary>{_html.escape(q)}</summary>'
        f'<p>{_html.escape(a)}</p></details>'
        for q, a in FESTIVAL_FAQ
    )
    return (
        '<section class="preorder-main preorder-seo">'
        '<div class="panel">'
        '<h2>2026 澎湖追風音樂燈光節主題行程</h2>'
        '<p>潮旅國際旅行社為 2026 澎湖追風音樂燈光節官方合作旅行社，推出三天兩夜主題套裝行程。'
        '行程主軸圍繞觀音亭園區的音樂燈光展演（展演期間 9/12–10/11），並搭配澎湖在地玩法，'
        '採兩人成行、每梯最多 5 人的小團形式。於上方選擇出發日期後，回程日自動為第三天，'
        '詳細行程內容與報價由潮旅專人與您確認。</p>'
        '<ul class="preorder-seo-points">'
        '<li><strong>活動：</strong>2026 澎湖追風音樂燈光節（觀音亭園區，燈光展演 9/12–10/11）</li>'
        '<li><strong>行程：</strong>三天兩夜主題套裝，選擇出發日後回程日為第三天</li>'
        '<li><strong>成行：</strong>兩人成行，每梯最多 5 人的小團</li>'
        '<li><strong>適合對象：</strong>情侶、朋友、親子與想看音樂節的澎湖自由行旅客</li>'
        '<li><strong>安排方式：</strong>行程細節、交通接送與報價由潮旅專人確認</li>'
        '</ul>'
        '<p class="preorder-seo-cta">想先了解玩法，可參考 <a href="/blog">澎湖旅遊部落格</a>；'
        '或透過 LINE @phbay2018、電話 06-9271288 與潮旅聯繫。</p>'
        '</div>'
        '<div class="panel">'
        '<h2>常見問題</h2>'
        f'{faq_html}'
        '</div>'
        '</section>'
    )


def _preorder_seo_data(slug, product=None):
    """通用預購頁的伺服器端 SEO；避免 /preorder/<slug> 只呈現通用標題。"""
    product = product or {}
    name = product.get('name') or ('2026 澎湖追風音樂燈光節主題行程' if slug == 'festival' else '潮旅行程預購')
    desc = product.get('description') or '選擇出發日期、填寫旅客資料即可完成預購，潮旅國際旅行社將由專人與您確認行程細節。'
    canonical = f'{SITE}/preorder/{slug}'
    image = f'{SITE}/images/festival-poster.jpg'
    if slug == 'festival':
        title = '2026 澎湖追風音樂燈光節主題行程預購｜三天兩夜套裝｜潮旅國際旅行社'
        desc = '2026 澎湖追風音樂燈光節主題行程預購，三天兩夜套裝安排，兩人成行，搭配觀音亭園區燈光展演與澎湖在地玩法，由潮旅國際旅行社專人確認。'
        keywords = ['澎湖追風音樂燈光節', '澎湖音樂節行程', '澎湖三天兩夜', '澎湖音樂節套裝', '潮旅國際旅行社']
    else:
        title = f'{name}預購訂位｜潮旅國際旅行社'
        keywords = ['澎湖行程預購', name, '潮旅國際旅行社']
    graph = [
        {
            '@context': 'https://schema.org',
            '@type': 'TouristTrip',
            '@id': f'{canonical}#trip',
            'name': name,
            'description': desc,
            'url': canonical,
            'image': image,
            'touristType': ['親子旅客', '情侶旅客', '朋友團體', '澎湖自由行旅客'],
            'provider': {
                '@type': 'TravelAgency',
                'name': '潮旅國際旅行社',
                'url': SITE,
                'telephone': '+886-6-9271288',
                'identifier': [
                    {'@type': 'PropertyValue', 'name': '統一編號', 'value': '60305305'},
                    {'@type': 'PropertyValue', 'name': '旅行社證號', 'value': '交觀乙第1864號'}
                ]
            },
            'offers': {
                '@type': 'Offer',
                'url': canonical,
                'priceCurrency': 'TWD',
                'availability': 'https://schema.org/InStock'
            },
            'keywords': ', '.join(keywords)
        },
        _breadcrumb_ld([('首頁', f'{SITE}/'), ('預購行程', canonical), (name, canonical)])
    ]
    if slug == 'festival':
        graph.append({
            '@context': 'https://schema.org',
            '@type': 'Event',
            '@id': f'{canonical}#event',
            'name': '2026 澎湖追風音樂燈光節',
            'description': '2026 澎湖追風音樂燈光節主題行程，搭配澎湖三天兩夜旅遊安排與專人預購服務。',
            'startDate': '2026-09-12',
            'endDate': '2026-10-11',
            'eventAttendanceMode': 'https://schema.org/OfflineEventAttendanceMode',
            'eventStatus': 'https://schema.org/EventScheduled',
            'image': image,
            'url': canonical,
            'location': {
                '@type': 'Place',
                'name': '澎湖觀音亭園區',
                'address': {
                    '@type': 'PostalAddress',
                    'addressRegion': '澎湖縣',
                    'addressLocality': '馬公市',
                    'addressCountry': 'TW'
                }
            },
            'organizer': {'@type': 'TravelAgency', 'name': '潮旅國際旅行社', 'url': SITE}
        })
        graph.append({
            '@context': 'https://schema.org',
            '@type': 'FAQPage',
            '@id': f'{canonical}#faq',
            'mainEntity': [
                {'@type': 'Question', 'name': q,
                 'acceptedAnswer': {'@type': 'Answer', 'text': a}}
                for q, a in FESTIVAL_FAQ
            ]
        })
    return {'title': title, 'description': desc, 'canonical': canonical, 'image': image, 'graph': graph}


def _render_preorder_template(slug, product=None):
    html_doc = open(os.path.join(app.root_path, 'preorder.html'), encoding='utf-8-sig').read()
    seo = _preorder_seo_data(slug, product)
    safe_title = _html.escape(seo['title'])
    safe_desc = _html.escape(seo['description'])
    safe_canonical = _html.escape(seo['canonical'])
    safe_image = _html.escape(seo['image'])
    head_extra = (
        f'<meta name="description" content="{safe_desc}" />\n'
        f'  <link rel="canonical" href="{safe_canonical}" />\n'
        f'  <meta property="og:type" content="website" />\n'
        f'  <meta property="og:site_name" content="潮旅國際旅行社" />\n'
        f'  <meta property="og:title" content="{safe_title}" />\n'
        f'  <meta property="og:description" content="{safe_desc}" />\n'
        f'  <meta property="og:url" content="{safe_canonical}" />\n'
        f'  <meta property="og:image" content="{safe_image}" />\n'
        f'  <meta property="og:locale" content="zh_TW" />\n'
        f'  <meta name="twitter:card" content="summary_large_image" />\n'
        f'  <meta name="twitter:title" content="{safe_title}" />\n'
        f'  <meta name="twitter:description" content="{safe_desc}" />\n'
        f'  <meta name="twitter:image" content="{safe_image}" />\n'
        f'  <script type="application/ld+json">{json.dumps(seo["graph"], ensure_ascii=False)}</script>'
    )
    html_doc = re.sub(r'<title>.*?</title>', f'<title>{safe_title}</title>', html_doc, count=1, flags=re.S | re.I)
    html_doc = re.sub(
        r'<meta name="description" content=".*?"\s*/>',
        head_extra,
        html_doc,
        count=1,
        flags=re.S | re.I
    )
    html_doc = html_doc.replace('<!--PREORDER_SEO_SECTION-->', _preorder_seo_section(slug))
    return html_doc


@app.route('/preorder/<slug>')
def preorder_page(slug):
    # 通用預購頁：同一模板，前端依 slug 讀取行程設定；後端先補 SEO/社群預覽/結構化資料。
    product = None
    try:
        conn = get_db(); cur = conn.cursor()
        product = _get_product(slug, cur)
        cur.close(); conn.close()
    except Exception as e:
        print(f'[SEO] 預購頁商品讀取失敗，改用 fallback：{e}')
    return _render_preorder_template(slug, product)


# ─── 梯次名額 CRUD（管理員）────────────────────────────────────
@app.route('/api/admin/slots', methods=['GET'])
def admin_get_slots():
    if not is_admin(): return jsonify(ok=False, error='未授權'), 401
    try:
        conn = get_db(); cur = conn.cursor()
        cur.execute("SELECT * FROM tour_slots ORDER BY tour_id, id")
        rows = [dict(r) for r in cur.fetchall()]
        cur.close(); conn.close()
        for r in rows:
            r['created_at'] = str(r.get('created_at', ''))
            r['remaining']  = max(0, r['capacity'] - r['booked'])
            r['wl_remaining'] = max(0, r['waitlist_cap'] - r['waitlisted'])
        return jsonify(ok=True, slots=rows)
    except Exception as e:
        return jsonify(ok=False, error=str(e)), 500


@app.route('/api/admin/slots', methods=['POST'])
def admin_create_slot():
    if not is_admin(): return jsonify(ok=False, error='未授權'), 401
    data = request.get_json(force=True, silent=True) or {}
    try:
        conn = get_db(); cur = conn.cursor()
        cur.execute("""
            INSERT INTO tour_slots
              (tour_id, date_label, capacity, booked, waitlist_cap, waitlisted, is_active)
            VALUES (%s,%s,%s,%s,%s,%s,%s) RETURNING id
        """, (data['tour_id'], data['date_label'],
              data.get('capacity', 20), data.get('booked', 0),
              data.get('waitlist_cap', 5), data.get('waitlisted', 0),
              data.get('is_active', True)))
        new_id = cur.fetchone()['id']
        conn.commit(); cur.close(); conn.close()
        return jsonify(ok=True, id=new_id)
    except Exception as e:
        return jsonify(ok=False, error=str(e)), 500


@app.route('/api/admin/slots/<int:slot_id>', methods=['PUT'])
def admin_update_slot(slot_id):
    if not is_admin(): return jsonify(ok=False, error='未授權'), 401
    data = request.get_json(force=True, silent=True) or {}
    try:
        conn = get_db(); cur = conn.cursor()
        cur.execute("""
            UPDATE tour_slots SET
              date_label=%s, capacity=%s, booked=%s,
              waitlist_cap=%s, waitlisted=%s, is_active=%s
            WHERE id=%s
        """, (data.get('date_label', ''), data.get('capacity', 20),
              data.get('booked', 0), data.get('waitlist_cap', 5),
              data.get('waitlisted', 0), data.get('is_active', True),
              slot_id))
        conn.commit(); cur.close(); conn.close()
        return jsonify(ok=True)
    except Exception as e:
        return jsonify(ok=False, error=str(e)), 500


@app.route('/api/admin/slots/<int:slot_id>', methods=['DELETE'])
def admin_delete_slot(slot_id):
    if not is_admin(): return jsonify(ok=False, error='未授權'), 401
    try:
        conn = get_db(); cur = conn.cursor()
        cur.execute("DELETE FROM tour_slots WHERE id=%s", (slot_id,))
        conn.commit(); cur.close(); conn.close()
        return jsonify(ok=True)
    except Exception as e:
        return jsonify(ok=False, error=str(e)), 500


# ═══════════════════════════════════════════════════════════
#   部落格（SEO：文章由伺服器渲染，每篇獨立網址可被收錄）
# ═══════════════════════════════════════════════════════════
import html as _html
from datetime import datetime as _dt

SITE = 'https://www.phbay.info'
REVIEWS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'content', 'reviews.json')

def load_reviews():
    """讀取真實旅客評價（content/reviews.json）；過濾不完整或無效評分的項目。"""
    try:
        with open(REVIEWS_FILE, encoding='utf-8') as f:
            data = json.load(f)
    except Exception:
        return []
    out = []
    for r in (data.get('reviews') or []):
        try:
            rating = float(r.get('rating'))
        except (TypeError, ValueError):
            continue
        if not (1 <= rating <= 5):
            continue
        author = str(r.get('author') or '').strip()
        body = str(r.get('body') or '').strip()
        if not author or not body:
            continue
        out.append({
            'author': author,
            'rating': rating,
            'date': str(r.get('date') or '')[:10],
            'tour': str(r.get('tour') or '').strip(),
            'body': body,
            'source': str(r.get('source') or '').strip(),
        })
    return out

def _breadcrumb_ld(trail):
    """trail: [(name, url), ...] → BreadcrumbList JSON-LD dict。"""
    return {
        "@context": "https://schema.org", "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": i + 1, "name": name, "item": url}
            for i, (name, url) in enumerate(trail)
        ],
    }

def _post_public(r):
    r = dict(r)
    for k in ('created_at', 'updated_at', 'published_at'):
        if r.get(k): r[k] = str(r[k])
    return r

# ── 公開 API ──
@app.route('/api/posts', methods=['GET'])
def get_posts():
    try:
        conn = get_db(); cur = conn.cursor()
        cur.execute("""SELECT id,slug,title,summary,cover_image,tags,author,published_at
                       FROM posts WHERE is_published=TRUE
                       ORDER BY COALESCE(published_at, created_at) DESC""")
        rows = [_post_public(r) for r in cur.fetchall()]
        cur.close(); conn.close()
        return jsonify(ok=True, posts=rows)
    except Exception as e:
        return jsonify(ok=False, error=str(e)), 500

@app.route('/api/posts/<slug>', methods=['GET'])
def get_post(slug):
    try:
        conn = get_db(); cur = conn.cursor()
        cur.execute("SELECT * FROM posts WHERE slug=%s AND is_published=TRUE", (slug,))
        row = cur.fetchone(); cur.close(); conn.close()
        if not row: return jsonify(ok=False, error='not found'), 404
        return jsonify(ok=True, post=_post_public(row))
    except Exception as e:
        return jsonify(ok=False, error=str(e)), 500

# ── 管理員 CRUD ──
@app.route('/api/admin/posts', methods=['GET'])
def admin_get_posts():
    if not has_role('editor'): return jsonify(ok=False, error='未授權'), 401
    try:
        conn = get_db(); cur = conn.cursor()
        cur.execute("SELECT * FROM posts ORDER BY COALESCE(published_at, created_at) DESC")
        rows = [_post_public(r) for r in cur.fetchall()]
        cur.close(); conn.close()
        return jsonify(ok=True, posts=rows)
    except Exception as e:
        return jsonify(ok=False, error=str(e)), 500

@app.route('/api/admin/posts', methods=['POST'])
def admin_create_post():
    if not has_role('editor'): return jsonify(ok=False, error='未授權'), 401
    d = request.get_json(force=True, silent=True) or {}
    try:
        pub = bool(d.get('is_published'))
        faq = d.get('faq') if isinstance(d.get('faq'), list) else None
        conn = get_db(); cur = conn.cursor()
        cur.execute("""INSERT INTO posts (slug,title,summary,content,cover_image,tags,author,is_published,published_at,faq)
                       VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id""",
                    (d.get('slug','').strip(), d.get('title','未命名'), d.get('summary',''),
                     d.get('content',''), d.get('cover_image',''), d.get('tags',''),
                     d.get('author','潮旅國際旅行社'), pub, _dt.now() if pub else None,
                     Json(faq) if faq else None))
        nid = cur.fetchone()['id']; conn.commit(); cur.close(); conn.close()
        return jsonify(ok=True, id=nid)
    except Exception as e:
        return jsonify(ok=False, error=str(e)), 500

@app.route('/api/admin/posts/<int:pid>', methods=['PUT'])
def admin_update_post(pid):
    if not has_role('editor'): return jsonify(ok=False, error='未授權'), 401
    d = request.get_json(force=True, silent=True) or {}
    try:
        conn = get_db(); cur = conn.cursor()
        # 首次發布才寫入 published_at
        cur.execute("SELECT is_published, published_at FROM posts WHERE id=%s", (pid,))
        old = cur.fetchone() or {}
        pub = bool(d.get('is_published'))
        pub_at = old.get('published_at')
        if pub and not pub_at: pub_at = _dt.now()
        if not pub: pub_at = old.get('published_at')
        cur.execute("""UPDATE posts SET slug=%s,title=%s,summary=%s,content=%s,cover_image=%s,
                       tags=%s,author=%s,is_published=%s,published_at=%s,updated_at=NOW() WHERE id=%s""",
                    (d.get('slug','').strip(), d.get('title',''), d.get('summary',''),
                     d.get('content',''), d.get('cover_image',''), d.get('tags',''),
                     d.get('author','潮旅國際旅行社'), pub, pub_at, pid))
        # faq 僅在有傳（list）時更新，否則保留原值（AI 草稿帶入用）
        if isinstance(d.get('faq'), list):
            cur.execute("UPDATE posts SET faq=%s WHERE id=%s",
                        (Json(d['faq']) if d['faq'] else None, pid))
        conn.commit(); cur.close(); conn.close()
        return jsonify(ok=True)
    except Exception as e:
        return jsonify(ok=False, error=str(e)), 500

@app.route('/api/admin/posts/<int:pid>', methods=['DELETE'])
def admin_delete_post(pid):
    if not has_role('editor'): return jsonify(ok=False, error='未授權'), 401
    try:
        conn = get_db(); cur = conn.cursor()
        cur.execute("DELETE FROM posts WHERE id=%s", (pid,))
        conn.commit(); cur.close(); conn.close()
        return jsonify(ok=True)
    except Exception as e:
        return jsonify(ok=False, error=str(e)), 500

# ── 伺服器渲染：共用外殼 ──
# ─── 部落格多語系 ─────────────────────────────────────────
BLOG_LANGS = ('en', 'ja', 'ko', 'zh-cn')  # zh-tw 為預設，不列入
BLOG_HTML_LANG = {'zh-tw': 'zh-TW', 'en': 'en', 'ja': 'ja', 'ko': 'ko', 'zh-cn': 'zh-Hans'}
BLOG_OG_LOCALE = {'zh-tw': 'zh_TW', 'en': 'en_US', 'ja': 'ja_JP', 'ko': 'ko_KR', 'zh-cn': 'zh_CN'}
BLOG_HREFLANG = {'zh-tw': 'zh-Hant', 'en': 'en', 'ja': 'ja', 'ko': 'ko', 'zh-cn': 'zh-Hans'}
BLOG_LANG_NAME = {'zh-tw': '中文', 'en': 'English', 'ja': '日本語', 'ko': '한국어', 'zh-cn': '简体中文'}
# 文章頁固定介面字串（依語言）
BLOG_UI = {
    'zh-tw': {'back': '← 回部落格', 'tldr': '先講結論', 'faq': '常見問題',
              'cta_h': '想規劃澎湖行程？', 'consult': '線上諮詢', 'neihai': '內海巡禮預購',
              'festival': '音樂節行程預購', 'quiz': '30 秒測你的澎湖玩法', 'pillar': '延伸攻略：'},
    'en': {'back': '← Back to blog', 'tldr': 'In short', 'faq': 'FAQ',
           'cta_h': 'Planning a Penghu trip?', 'consult': 'Enquire online', 'neihai': 'Inner-Sea Cruise pre-order',
           'festival': 'Music Festival pre-order', 'quiz': 'Find your Penghu style (30s)', 'pillar': 'Related guide: '},
    'ja': {'back': '← ブログに戻る', 'tldr': '結論から', 'faq': 'よくある質問',
           'cta_h': '澎湖旅行を計画しませんか？', 'consult': 'オンライン相談', 'neihai': '内海クルーズ予約',
           'festival': '音楽祭ツアー予約', 'quiz': '30秒であなたの澎湖旅診断', 'pillar': '関連ガイド：'},
    'ko': {'back': '← 블로그로', 'tldr': '요약', 'faq': '자주 묻는 질문',
           'cta_h': '펑후 여행을 계획 중이신가요?', 'consult': '온라인 문의', 'neihai': '내해 크루즈 예약',
           'festival': '뮤직 페스티벌 예약', 'quiz': '30초 펑후 여행 진단', 'pillar': '관련 가이드: '},
    'zh-cn': {'back': '← 回博客', 'tldr': '先讲结论', 'faq': '常见问题',
              'cta_h': '想规划澎湖行程？', 'consult': '在线咨询', 'neihai': '内海巡礼预购',
              'festival': '音乐节行程预购', 'quiz': '30 秒测你的澎湖玩法', 'pillar': '延伸攻略：'},
}


def _req_lang():
    """讀取 ?lang=，僅接受支援語言，否則回傳預設 zh-tw。"""
    l = (request.args.get('lang') or '').strip().lower()
    return l if l in BLOG_LANGS else 'zh-tw'


def _localize_post(p, lang):
    """回傳指定語言的欄位；缺哪個欄位就回退中文（逐欄位）。"""
    out = dict(p)
    if lang in BLOG_LANGS:
        tr = p.get('i18n') if isinstance(p.get('i18n'), dict) else {}
        tr = tr.get(lang) if isinstance(tr, dict) else None
        tr = tr if isinstance(tr, dict) else {}
        for k in ('title', 'summary', 'content'):
            if str(tr.get(k) or '').strip():
                out[k] = tr[k]
        if isinstance(tr.get('faq'), list) and tr['faq']:
            out['faq'] = tr['faq']
        if isinstance(tr.get('info_box'), dict) and tr['info_box']:
            out['info_box'] = tr['info_box']
    return out


def _post_avail_langs(p):
    """該文章實際有翻譯（至少有標題或內文）的語言清單。"""
    tr = p.get('i18n') if isinstance(p.get('i18n'), dict) else {}
    return [l for l in BLOG_LANGS
            if isinstance(tr.get(l), dict) and (str(tr[l].get('title') or '').strip()
                                                or str(tr[l].get('content') or '').strip())]


def _blog_hreflang(path_no_lang, avail):
    """產生 hreflang 交替連結：中文（含 x-default）＋各已翻譯語言。"""
    from urllib.parse import urlencode
    links = [f'<link rel="alternate" hreflang="zh-Hant" href="{SITE}{path_no_lang}"/>',
             f'<link rel="alternate" hreflang="x-default" href="{SITE}{path_no_lang}"/>']
    for l in avail:
        sep = '&' if '?' in path_no_lang else '?'
        links.append(f'<link rel="alternate" hreflang="{BLOG_HREFLANG[l]}" href="{SITE}{path_no_lang}{sep}lang={l}"/>')
    return ''.join(links)


def _render_blog(title, desc, canonical, body, head_extra='', image=None, lang='zh-tw', alt_links=''):
    img = image or f'{SITE}/images/festival-poster.jpg'
    nav = '''<div class="top-banner"><div class="banner-static"><span>潮旅國際旅行社</span><span class="banner-sep">｜</span><span>2026 澎湖追風音樂燈光節 官方合作旅行社</span><span class="banner-sep">｜</span><span>電話：06-9271288</span></div></div>
<nav class="navbar" id="navbar"><div class="nav-container"><a href="/" class="nav-logo"><i class="fas fa-water"></i> 潮旅國際旅行社</a><button class="nav-toggle" id="nav-toggle" aria-label="選單"><span></span><span></span><span></span></button><ul class="nav-links" id="nav-links"><li><a href="/">首頁</a></li><li><a href="/#tours">行程介紹</a></li><li class="nav-item has-submenu"><a href="/neihai-preorder.html">預購行程 <i class="fas fa-chevron-down nav-caret"></i></a><ul class="nav-submenu"><li><a href="/neihai-preorder.html">小城故事內海巡禮</a></li><li><a href="/preorder/festival">追風音樂節</a></li></ul></li><li class="nav-item has-submenu"><a href="/blog">旅遊大小事 <i class="fas fa-chevron-down nav-caret"></i></a><ul class="nav-submenu"><li><a href="/tides">潮汐查詢系統</a></li><li><a href="/blog">旅遊文章分享</a></li><li><a href="/reviews">旅客評價</a></li></ul></li><li class="nav-item has-submenu"><a href="/#about">關於我們 <i class="fas fa-chevron-down nav-caret"></i></a><ul class="nav-submenu"><li><a href="/#contact">聯絡資訊</a></li></ul></li></ul></div></nav>'''
    footer = '''<footer class="footer"><div class="container"><div class="footer-bottom"><p>© 2026 潮旅國際旅行社 All Rights Reserved.｜<a href="/" style="color:inherit">官網</a>｜<a href="/blog" style="color:inherit">部落格</a>｜<a href="/reviews" style="color:inherit">旅客評價</a></p></div></div></footer>
<script>(function(){var t=document.getElementById('nav-toggle'),l=document.getElementById('nav-links');if(t)t.addEventListener('click',function(){l.classList.toggle('open')});var lb=document.getElementById('lang-btn'),lm=document.getElementById('lang-menu');if(lb)lb.addEventListener('click',function(e){e.stopPropagation();lm.classList.toggle('open')});document.addEventListener('click',function(){if(lm)lm.classList.remove('open')});})();</script>'''
    # 部落格頁語言切換鈕（只在 /blog 路徑顯示；連到同頁 ?lang=，保留 tag/page）
    if request.path.startswith('/blog'):
        from urllib.parse import urlencode
        _other = {k: v for k, v in request.args.items() if k != 'lang'}
        _menu = ''
        for _code in ('zh-tw',) + BLOG_LANGS:
            _a = dict(_other)
            if _code != 'zh-tw':
                _a['lang'] = _code
            _qs = ('?' + urlencode(_a)) if _a else ''
            _menu += f'<li><a href="{request.path}{_qs}">{BLOG_LANG_NAME[_code]}</a></li>'
        _ls = (f'<li class="lang-switch"><button class="lang-btn" id="lang-btn" aria-label="Language">🌐 '
               f'<span id="lang-current">{BLOG_LANG_NAME.get(lang, "中文")}</span> '
               f'<i class="fas fa-chevron-down" style="font-size:.7em"></i></button>'
               f'<ul class="lang-menu" id="lang-menu">{_menu}</ul></li>')
        nav = nav.replace('</ul></div></nav>', _ls + '</ul></div></nav>')
    return (f'<!DOCTYPE html><html lang="{BLOG_HTML_LANG.get(lang, "zh-TW")}"><head>'
        '<meta charset="UTF-8"/><meta name="viewport" content="width=device-width, initial-scale=1.0"/>'
        '<script async src="https://www.googletagmanager.com/gtag/js?id=G-47DV1VPF9J"></script>'
        '<script>window.dataLayer=window.dataLayer||[];function gtag(){dataLayer.push(arguments);}gtag("js",new Date());gtag("config","G-47DV1VPF9J");</script>'
        '<script>!function(f,b,e,v,n,t,s){if(f.fbq)return;n=f.fbq=function(){n.callMethod?n.callMethod.apply(n,arguments):n.queue.push(arguments)};if(!f._fbq)f._fbq=n;n.push=n;n.loaded=!0;n.version="2.0";n.queue=[];t=b.createElement(e);t.async=!0;t.src=v;s=b.getElementsByTagName(e)[0];s.parentNode.insertBefore(t,s)}(window,document,"script","https://connect.facebook.net/en_US/fbevents.js");fbq("init","25643845041980148");fbq("track","PageView");</script>'
        '<noscript><img height="1" width="1" style="display:none" src="https://www.facebook.com/tr?id=25643845041980148&ev=PageView&noscript=1"/></noscript>'
        f'<title>{_html.escape(title)}</title>'
        f'<meta name="description" content="{_html.escape(desc)}"/>'
        f'<link rel="canonical" href="{canonical}"/>{alt_links}'
        f'<meta property="og:type" content="article"/><meta property="og:title" content="{_html.escape(title)}"/>'
        f'<meta property="og:description" content="{_html.escape(desc)}"/><meta property="og:url" content="{canonical}"/>'
        f'<meta property="og:site_name" content="潮旅國際旅行社"/><meta property="og:locale" content="{BLOG_OG_LOCALE.get(lang, "zh_TW")}"/>'
        f'<meta property="og:image" content="{_html.escape(img)}"/>'
        '<meta name="twitter:card" content="summary_large_image"/>'
        f'<meta name="twitter:title" content="{_html.escape(title)}"/>'
        f'<meta name="twitter:description" content="{_html.escape(desc)}"/>'
        f'<meta name="twitter:image" content="{_html.escape(img)}"/>'
        '<link rel="icon" href="data:image/svg+xml,%3Csvg%20xmlns=\'http://www.w3.org/2000/svg\'%20viewBox=\'0%200%20100%20100\'%3E%3Crect%20width=\'100\'%20height=\'100\'%20rx=\'22\'%20fill=\'%231a6b9e\'/%3E%3Ctext%20x=\'50\'%20y=\'73\'%20font-size=\'62\'%20text-anchor=\'middle\'%20fill=\'white\'%20font-family=\'sans-serif\'%3E潮%3C/text%3E%3C/svg%3E"/>'
        '<link rel="preconnect" href="https://cdnjs.cloudflare.com" crossorigin/>'
        f'<link rel="stylesheet" href="/style.css?v={ASSET_VERSION}"/>'
        '<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.0/css/all.min.css" media="print" onload="this.media=\'all\'"/>'
        '<noscript><link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.0/css/all.min.css"/></noscript>'
        '<style>.blog-wrap{max-width:820px;margin:0 auto;padding:36px 20px 60px}.blog-wrap h1{font-size:clamp(1.5rem,4vw,2.1rem);color:var(--blue-dark);font-weight:800;line-height:1.35;margin-bottom:12px}.blog-meta{color:var(--text-light);font-size:.9rem;margin-bottom:20px}.blog-cover{width:100%;border-radius:14px;margin-bottom:24px}.blog-body{font-size:1.04rem;line-height:1.9;color:var(--text-dark)}.blog-body h2{font-size:1.4rem;color:var(--blue-dark);margin:28px 0 12px;font-weight:800}.blog-body h3{font-size:1.15rem;color:var(--blue-main);margin:22px 0 10px;font-weight:700}.blog-body p{margin-bottom:16px}.blog-body img{max-width:100%;border-radius:10px;margin:12px 0}.blog-body ul,.blog-body ol{margin:0 0 16px 22px}.blog-body li{margin-bottom:6px}.blog-body a{color:var(--blue-main);text-decoration:underline}.post-card{display:block;background:var(--white);border:1px solid #e6edf3;border-radius:14px;overflow:hidden;transition:.2s;box-shadow:0 2px 10px rgba(0,0,0,.05)}.post-card:hover{transform:translateY(-3px);box-shadow:var(--shadow-hover)}.post-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:20px;margin-top:28px}.post-card img{width:100%;height:170px;object-fit:cover}.post-card-body{padding:16px 18px}.post-card-body h2{font-size:1.1rem;color:var(--blue-dark);margin-bottom:8px;line-height:1.4}.post-card-body p{color:var(--text-mid);font-size:.9rem;line-height:1.6}.post-tags{margin-top:10px}.post-tag{display:inline-block;background:var(--blue-pale);color:var(--blue-main);font-size:.74rem;padding:2px 9px;border-radius:20px;margin:2px 4px 2px 0}.blog-cta{margin-top:40px;background:var(--blue-pale);border-radius:16px;padding:28px;text-align:center}.blog-cta a{margin:4px}.blog-back{display:inline-block;margin-bottom:18px;color:var(--blue-main);font-weight:600}.rv-summary{display:flex;align-items:baseline;gap:12px;flex-wrap:wrap;margin:8px 0 24px;padding:16px 20px;background:var(--blue-pale);border-radius:14px}.rv-avg{font-size:2.2rem;font-weight:800;color:var(--blue-dark);line-height:1}.rv-avg-stars{color:#f5a623;font-size:1.2rem;letter-spacing:2px}.rv-count{color:var(--text-mid);font-size:.95rem}.rv-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:18px;margin-top:8px}.rv-card{background:var(--white);border:1px solid #e6edf3;border-radius:14px;padding:18px 20px;box-shadow:0 2px 10px rgba(0,0,0,.05)}.rv-stars{color:#f5a623;letter-spacing:2px;font-size:1.05rem}.rv-num{color:var(--text-mid);font-size:.85rem;margin-left:8px;letter-spacing:0}.rv-body{margin:10px 0 14px;line-height:1.8;color:var(--text-dark)}.rv-meta{color:var(--text-light);font-size:.86rem;border-top:1px solid #eef2f5;padding-top:10px}.blog-cats{display:flex;flex-wrap:wrap;gap:8px;margin:4px 0 8px}.blog-cats .post-tag{margin:0;font-size:.82rem;padding:5px 12px;cursor:pointer}.blog-cats .post-tag.active{background:var(--blue-main);color:#fff}.blog-pager{display:flex;align-items:center;justify-content:center;gap:16px;margin-top:36px}.pager-btn{display:inline-block;padding:9px 18px;border-radius:24px;background:var(--blue-pale);color:var(--blue-main);font-weight:600;text-decoration:none}.pager-btn:hover{background:var(--blue-main);color:#fff}.pager-btn.disabled{opacity:.4;pointer-events:none}.pager-info{color:var(--text-mid);font-size:.9rem}'
        '.post-tldr{background:var(--blue-pale);border-left:4px solid var(--blue-main);border-radius:10px;padding:16px 20px;margin:0 0 18px}.post-tldr-label{display:inline-block;font-weight:800;color:var(--blue-dark);font-size:.85rem;background:#fff;border-radius:20px;padding:2px 12px;margin-bottom:8px}.post-tldr p{margin:6px 0 0;line-height:1.8;color:var(--text-dark)}'
        '.post-infobox{border:1px solid #e6edf3;border-radius:12px;padding:6px 18px;margin:0 0 20px;background:#fff}.post-info-row{display:flex;gap:14px;padding:9px 0;border-bottom:1px solid #f0f4f7;font-size:.95rem}.post-info-row:last-child{border-bottom:none}.post-info-k{flex:0 0 auto;min-width:96px;font-weight:700;color:var(--blue-dark)}.post-info-v{color:var(--text-mid);line-height:1.7}'
        '.post-faq{margin-top:36px}.post-faq h2{font-size:1.4rem;color:var(--blue-dark);font-weight:800;margin-bottom:14px}.post-faq details{background:#fff;border:1px solid #e6edf3;border-radius:12px;margin-bottom:10px;padding:0 18px}.post-faq summary{cursor:pointer;font-weight:700;color:var(--blue-dark);padding:14px 0;list-style-position:inside}.post-faq details[open] summary{border-bottom:1px solid #eef2f5}.post-faq details p{padding:12px 0 16px;color:var(--text-mid);line-height:1.8}</style>'
        f'{head_extra}</head><body>{nav}<main>{body}</main>{footer}'
        '<a href="https://wa.me/886912151788" class="wa-float" target="_blank" rel="noopener noreferrer" aria-label="WhatsApp 諮詢" title="WhatsApp 諮詢"><i class="fab fa-whatsapp"></i></a>'
        '</body></html>')

@app.route('/blog')
def blog_index():
    try:
        conn = get_db(); cur = conn.cursor()
        cur.execute("""SELECT slug,title,summary,cover_image,tags,published_at,i18n FROM posts
                       WHERE is_published=TRUE ORDER BY COALESCE(published_at,created_at) DESC""")
        posts = cur.fetchall(); cur.close(); conn.close()
    except Exception:
        posts = []
    lang = _req_lang()
    _langp = f'lang={lang}' if lang != 'zh-tw' else ''
    all_posts = list(posts)
    sel = (request.args.get('tag') or '').strip()
    if sel:
        posts = [p for p in posts
                 if sel in [t.strip() for t in (p.get('tags') or '').split(',')]]

    # 分頁：部落格首頁只顯示一頁，避免全部文章塞在同一頁（HTML 過大）
    PER_PAGE = 15
    try:
        page = int(request.args.get('page', 1))
    except (TypeError, ValueError):
        page = 1
    total = len(posts)
    pages = max(1, (total + PER_PAGE - 1) // PER_PAGE)
    page = min(max(page, 1), pages)
    offset = (page - 1) * PER_PAGE
    page_posts = posts[offset:offset + PER_PAGE]

    def _blog_url(n):
        parts = []
        if sel:
            parts.append(f'tag={sel}')
        if n > 1:
            parts.append(f'page={n}')
        if _langp:
            parts.append(_langp)
        return '/blog' + ('?' + '&'.join(parts) if parts else '')

    _langq = f'?lang={lang}' if lang != 'zh-tw' else ''
    _tagq = f'&lang={lang}' if lang != 'zh-tw' else ''
    cards = ''
    for p in page_posts:
        lp = _localize_post(p, lang)
        img = f'<img src="{_html.escape(lp["cover_image"])}" alt="{_html.escape(lp["title"])}" loading="lazy"/>' if lp.get('cover_image') else ''
        tags = ''.join(f'<a class="post-tag" href="/blog?tag={_html.escape(t.strip())}{_tagq}">{_html.escape(t.strip())}</a>' for t in (lp.get('tags') or '').split(',') if t.strip())
        cards += (f'<a class="post-card" href="/blog/{_html.escape(lp["slug"])}{_langq}">{img}'
                  f'<div class="post-card-body"><h2>{_html.escape(lp["title"])}</h2>'
                  f'<p>{_html.escape((lp.get("summary") or "")[:80])}</p>'
                  f'<div class="post-tags">{tags}</div></div></a>')
    if not cards:
        cards = '<p style="color:#888;text-align:center;padding:40px">部落格文章準備中，敬請期待！</p>'

    # 分類入口：依實際文章 tag 出現頻率取前 8，保證點進去不是空分類
    from collections import Counter
    freq = Counter()
    for p in all_posts:
        for t in (p.get('tags') or '').split(','):
            t = t.strip()
            if t:
                freq[t] += 1
    cat_links = ''.join(
        f'<a class="post-tag{" active" if t == sel else ""}" href="/blog?tag={_html.escape(t)}{_tagq}">{_html.escape(t)}</a>'
        for t, _c in freq.most_common(8))
    cat_bar = f'<div class="blog-cats">{cat_links}</div>' if cat_links else ''

    page_suffix = f'（第 {page} 頁）' if page > 1 else ''
    if sel:
        heading = f'{_html.escape(sel)}｜澎湖旅遊部落格'
        sub = f'分類：{_html.escape(sel)}　<a class="blog-back" style="margin:0" href="/blog">← 看全部文章</a>'
        title = f'{sel}｜澎湖旅遊部落格{page_suffix} - 潮旅國際旅行社'
        desc = f'潮旅國際旅行社部落格「{sel}」分類：澎湖旅遊相關文章與分享。'
        trail = [("首頁", f"{SITE}/"), ("部落格", f"{SITE}/blog"), (sel, f'{SITE}/blog?tag={sel}')]
    else:
        heading = '澎湖旅遊部落格'
        sub = '在地旅行社分享澎湖玩法、攻略與故事'
        title = f'澎湖旅遊部落格｜攻略、玩法、在地故事{page_suffix} - 潮旅國際旅行社'
        desc = '潮旅國際旅行社的澎湖旅遊部落格：行程攻略、景點玩法、美食推薦、跳島與音樂節在地分享。'
        trail = [("首頁", f"{SITE}/"), ("部落格", f"{SITE}/blog")]
    canonical = f'{SITE}{_blog_url(page)}'

    if pages > 1:
        prev_btn = (f'<a class="pager-btn" href="{_blog_url(page - 1)}">← 上一頁</a>'
                    if page > 1 else '<span class="pager-btn disabled">← 上一頁</span>')
        next_btn = (f'<a class="pager-btn" href="{_blog_url(page + 1)}">下一頁 →</a>'
                    if page < pages else '<span class="pager-btn disabled">下一頁 →</span>')
        pager = f'<nav class="blog-pager">{prev_btn}<span class="pager-info">第 {page} / {pages} 頁</span>{next_btn}</nav>'
    else:
        pager = ''

    body = (f'<div class="blog-wrap"><h1>{heading}</h1>'
            f'<p class="blog-meta">{sub}</p>'
            f'{cat_bar}'
            f'<div class="post-grid">{cards}</div>'
            f'{pager}</div>')

    item_list = {
        "@context": "https://schema.org", "@type": "ItemList",
        "itemListElement": [
            {"@type": "ListItem", "position": offset + i + 1,
             "url": f'{SITE}/blog/{p["slug"]}{_langq}', "name": _localize_post(p, lang)["title"]}
            for i, p in enumerate(page_posts)
        ]
    }
    rel_links = ''
    if page > 1:
        rel_links += f'<link rel="prev" href="{SITE}{_blog_url(page - 1)}"/>'
    if page < pages:
        rel_links += f'<link rel="next" href="{SITE}{_blog_url(page + 1)}"/>'
    # 列表頁可用任何語言呈現，hreflang 列出全部語言（去掉 lang 參數的乾淨路徑）
    _pnl_parts = []
    if sel:
        _pnl_parts.append(f'tag={sel}')
    if page > 1:
        _pnl_parts.append(f'page={page}')
    _path_no_lang = '/blog' + ('?' + '&'.join(_pnl_parts) if _pnl_parts else '')
    alt_links = _blog_hreflang(_path_no_lang, list(BLOG_LANGS))
    head_extra = (rel_links
                  + '<script type="application/ld+json">' + json.dumps(_breadcrumb_ld(trail), ensure_ascii=False) + '</script>'
                  + '<script type="application/ld+json">' + json.dumps(item_list, ensure_ascii=False) + '</script>')
    return _render_blog(title, desc, canonical, body, head_extra, lang=lang, alt_links=alt_links)

def _pillar_link_for_tags(tags):
    """依文章 tag 自動對應主題攻略頁（pillar page）內鏈；對不到回 None。"""
    t = tags or ''
    if '音樂節' in t or '追風' in t:
        return ('/penghu-2026-festival-guide', '2026 澎湖追風音樂燈光節攻略')
    if '親子' in t:
        return ('/penghu-family-travel', '澎湖親子旅遊攻略')
    if any(k in t for k in ('美食', '小吃', '伴手禮', '海鮮', '早餐')):
        return ('/penghu-food-guide', '澎湖美食地圖')
    if any(k in t for k in ('景點', '行程', '自由行', '跳島', '慢旅')):
        return ('/penghu-3days-itinerary', '澎湖三天兩夜行程規劃')
    return None

@app.route('/blog/<slug>')
def blog_post(slug):
    try:
        conn = get_db(); cur = conn.cursor()
        cur.execute("SELECT * FROM posts WHERE slug=%s AND is_published=TRUE", (slug,))
        p = cur.fetchone(); cur.close(); conn.close()
    except Exception:
        p = None
    if not p:
        return _render_blog('找不到文章 - 潮旅國際旅行社', '找不到這篇文章。', f'{SITE}/blog',
                            '<div class="blog-wrap"><a class="blog-back" href="/blog">← 回部落格</a><h1>找不到這篇文章</h1><p>它可能已被移除或尚未發布。</p></div>',
                            '<meta name="robots" content="noindex">'
                            '<script>gtag("event","page_not_found",{page_path:location.pathname});</script>'), 404
    lang = _req_lang()
    avail = _post_avail_langs(p)
    alt_links = _blog_hreflang(f'/blog/{slug}', avail)
    p = _localize_post(p, lang)          # 逐欄位翻譯，缺者回退中文
    desc = (p.get('summary') or _html.unescape(re.sub('<[^>]+>', '', p.get('content') or ''))[:140])
    pub = str(p.get('published_at') or p.get('created_at') or '')[:10]
    cover = f'<img class="blog-cover" src="{_html.escape(p["cover_image"])}" alt="{_html.escape(p["title"])}"/>' if p.get('cover_image') else ''
    tags = ''.join(f'<span class="post-tag">{_html.escape(t.strip())}</span>' for t in (p.get('tags') or '').split(',') if t.strip())
    canonical = f'{SITE}/blog/{slug}' + (f'?lang={lang}' if lang != 'zh-tw' else '')
    ld = {
        "@context": "https://schema.org", "@type": "Article",
        "headline": p['title'], "description": desc,
        "datePublished": str(p.get('published_at') or p.get('created_at') or ''),
        "dateModified": str(p.get('updated_at') or ''),
        "author": {"@type": "Organization", "name": p.get('author') or '潮旅國際旅行社'},
        "publisher": {"@type": "Organization", "name": "潮旅國際旅行社",
                      "logo": {"@type": "ImageObject", "url": f"{SITE}/images/festival-poster.jpg"}},
        "mainEntityOfPage": canonical, "url": canonical,
        "inLanguage": BLOG_HTML_LANG.get(lang, "zh-TW")
    }
    imgs = []
    if p.get('cover_image'):
        imgs.append(p['cover_image'])
    for m in re.findall(r'<img[^>]+src="([^"]+)"', p.get('content') or ''):
        if m not in imgs:
            imgs.append(m)
    if imgs:
        ld['image'] = imgs
    breadcrumb = _breadcrumb_ld([("首頁", f"{SITE}/"), ("部落格", f"{SITE}/blog"),
                                 (p['title'], canonical)])
    head_extra = ('<script type="application/ld+json">' + json.dumps(ld, ensure_ascii=False) + '</script>'
                  '<script type="application/ld+json">' + json.dumps(breadcrumb, ensure_ascii=False) + '</script>')

    ui = BLOG_UI.get(lang, BLOG_UI['zh-tw'])
    # 先講結論（AEO）：用 summary 產生，所有文章都有
    tldr = ''
    if p.get('summary'):
        tldr = (f'<div class="post-tldr"><span class="post-tldr-label">{ui["tldr"]}</span>'
                f'<p>{_html.escape(p["summary"])}</p></div>')

    # 資訊盒（選填欄位 info_box：{標籤:值}）
    infobox = ''
    if isinstance(p.get('info_box'), dict) and p['info_box']:
        rows = ''.join(f'<div class="post-info-row"><span class="post-info-k">{_html.escape(str(k))}</span>'
                       f'<span class="post-info-v">{_html.escape(str(v))}</span></div>'
                       for k, v in p['info_box'].items())
        infobox = f'<div class="post-infobox">{rows}</div>'

    # 文末 FAQ（選填欄位 faq：[{q,a}]）＋ FAQPage schema
    faq_html = ''
    faq_items = p.get('faq') if isinstance(p.get('faq'), list) else []
    faq_items = [x for x in faq_items if isinstance(x, dict) and x.get('q') and x.get('a')]
    if faq_items:
        qa = ''.join(f'<details><summary>{_html.escape(str(x["q"]))}</summary>'
                     f'<p>{_html.escape(str(x["a"]))}</p></details>' for x in faq_items)
        faq_html = f'<section class="post-faq"><h2>{ui["faq"]}</h2>{qa}</section>'
        faq_ld = {"@context": "https://schema.org", "@type": "FAQPage",
                  "mainEntity": [{"@type": "Question", "name": str(x["q"]),
                                  "acceptedAnswer": {"@type": "Answer", "text": str(x["a"])}}
                                 for x in faq_items]}
        head_extra += '<script type="application/ld+json">' + json.dumps(faq_ld, ensure_ascii=False) + '</script>'

    # 主題攻略頁內鏈（依 tag 自動對應）
    pillar_html = ''
    pl = _pillar_link_for_tags(p.get('tags'))
    if pl:
        pillar_html = (f'<p style="margin-top:28px;padding:14px 18px;background:var(--blue-pale);border-radius:12px">'
                       f'<strong>{ui["pillar"]}</strong><a href="{pl[0]}">{pl[1]}</a></p>')
    _langq = f'?lang={lang}' if lang != 'zh-tw' else ''

    body = (f'<article class="blog-wrap"><a class="blog-back" href="/blog{_langq}">{ui["back"]}</a>'
            f'<h1>{_html.escape(p["title"])}</h1>'
            f'<div class="blog-meta">{pub}｜{_html.escape(p.get("author") or "潮旅國際旅行社")}　{tags}</div>'
            f'{tldr}{infobox}'
            f'{cover}<div class="blog-body">{p.get("content") or ""}</div>{faq_html}{pillar_html}'
            f'<div class="blog-cta"><h3 style="color:var(--blue-dark);margin-bottom:10px">{ui["cta_h"]}</h3>'
            f'<a href="/#contact" class="btn btn-primary"><i class="fas fa-comment-dots"></i> {ui["consult"]}</a> '
            f'<a href="/neihai-preorder.html" class="btn btn-outline" style="color:var(--blue-main);border-color:var(--blue-main)"><i class="fas fa-ship"></i> {ui["neihai"]}</a> '
            f'<a href="/preorder/festival" class="btn btn-outline" style="color:var(--blue-main);border-color:var(--blue-main)"><i class="fas fa-music"></i> {ui["festival"]}</a> '
            f'<a href="/#quiz" class="btn btn-outline" style="color:var(--blue-main);border-color:var(--blue-main)"><i class="fas fa-compass"></i> {ui["quiz"]}</a>'
            f'</div></article>')
    return _render_blog(f'{p["title"]} - 潮旅國際旅行社部落格', desc, canonical, body, head_extra,
                        image=(imgs[0] if imgs else None), lang=lang, alt_links=alt_links)

# ── 旅客評價（遊客心得）──
# ── Pillar pages（主題攻略頁，內容在 pillar_pages.py）──
from pillar_pages import PILLAR_PAGES

_PILLAR_OG_IMAGE = {
    'penghu-3days-itinerary': f'{SITE}/images/summer-festival-hero-2026.jpg',
    'penghu-family-travel': f'{SITE}/images/neihai-cruise-hero-2026.jpg',
    'penghu-food-guide': f'{SITE}/images/penghu-small-squid-and-bigfin-reef-squid.jpg',
    'penghu-2026-festival-guide': f'{SITE}/images/festival-poster.jpg',
}

@app.route('/penghu-3days-itinerary')
@app.route('/penghu-family-travel')
@app.route('/penghu-food-guide')
@app.route('/penghu-2026-festival-guide')
def pillar_page():
    slug = request.path.strip('/')
    p = PILLAR_PAGES[slug]
    return _render_blog(p['title'], p['desc'], p['canonical'], p['body'],
                        p['head_extra'], image=_PILLAR_OG_IMAGE.get(slug))

@app.route('/reviews')
def reviews_page():
    items = load_reviews()
    canonical = f'{SITE}/reviews'
    if items:
        avg = round(sum(r['rating'] for r in items) / len(items), 1)
        cards = ''
        for r in items:
            stars = '★' * int(round(r['rating'])) + '☆' * (5 - int(round(r['rating'])))
            meta = '　'.join(x for x in (r['date'], r['tour'], (f'來源：{r["source"]}' if r['source'] else '')) if x)
            cards += (f'<div class="rv-card"><div class="rv-stars">{stars}'
                      f'<span class="rv-num">{r["rating"]:g}</span></div>'
                      f'<p class="rv-body">{_html.escape(r["body"])}</p>'
                      f'<div class="rv-meta"><strong>{_html.escape(r["author"])}</strong>'
                      f'{("　" + _html.escape(meta)) if meta else ""}</div></div>')
        intro = (f'<div class="rv-summary"><span class="rv-avg">{avg:g}</span>'
                 f'<span class="rv-avg-stars">{"★" * int(round(avg))}{"☆" * (5 - int(round(avg)))}</span>'
                 f'<span class="rv-count">{len(items)} 則真實旅客評價</span></div>')
        body = (f'<div class="blog-wrap"><h1>旅客評價</h1>'
                f'<p class="blog-meta">真實旅客在潮旅國際旅行社的澎湖旅程心得</p>'
                f'{intro}<div class="rv-grid">{cards}</div>'
                f'<div class="blog-cta"><h3 style="color:var(--blue-dark);margin-bottom:10px">想擁有同樣的澎湖體驗？</h3>'
                f'<a href="/#contact" class="btn btn-primary"><i class="fas fa-comment-dots"></i> 線上諮詢</a> '
                f'<a href="/#tours" class="btn btn-outline" style="color:var(--blue-main);border-color:var(--blue-main)"><i class="fas fa-map-marked-alt"></i> 看推薦行程</a>'
                f'</div></div>')
    else:
        body = ('<div class="blog-wrap"><h1>旅客評價</h1>'
                '<p class="blog-meta">真實旅客在潮旅國際旅行社的澎湖旅程心得</p>'
                '<p style="color:#888;text-align:center;padding:40px">旅客評價整理中，敬請期待！'
                '<br/>跟過潮旅行程嗎？歡迎透過 <a href="/#contact" style="color:var(--blue-main)">線上諮詢</a> '
                '或 LINE @phbay2018 分享你的心得。</p></div>')

    graph = []
    if items:
        avg = round(sum(r['rating'] for r in items) / len(items), 1)
        reviews_ld = []
        for r in items:
            rv = {
                "@type": "Review",
                "author": {"@type": "Person", "name": r['author']},
                "reviewRating": {"@type": "Rating", "ratingValue": r['rating'],
                                 "bestRating": 5, "worstRating": 1},
                "reviewBody": r['body'],
            }
            if r['date']:
                rv["datePublished"] = r['date']
            if r['tour']:
                rv["name"] = r['tour']
            reviews_ld.append(rv)
        graph.append({
            "@context": "https://schema.org", "@type": "TravelAgency",
            "@id": f"{SITE}/#organization", "name": "潮旅國際旅行社",
            "url": f"{SITE}/",
            "aggregateRating": {"@type": "AggregateRating", "ratingValue": avg,
                                "reviewCount": len(items), "bestRating": 5, "worstRating": 1},
            "review": reviews_ld,
        })
    graph.append(_breadcrumb_ld([("首頁", f"{SITE}/"), ("旅客評價", canonical)]))
    head_extra = ''.join('<script type="application/ld+json">' + json.dumps(g, ensure_ascii=False) + '</script>' for g in graph)
    return _render_blog('旅客評價｜真實澎湖旅程心得 - 潮旅國際旅行社',
                        '潮旅國際旅行社真實旅客評價：望安綠蠵龜生態、親子海島、跳島與音樂節行程的旅程心得與推薦。',
                        canonical, body, head_extra)

# ── 動態 sitemap（含部落格文章）──
@app.route('/sitemap.xml')
def dynamic_sitemap():
    urls = [(f'{SITE}/', '1.0', 'weekly'), (f'{SITE}/faq.html', '0.8', 'monthly'),
            (f'{SITE}/blog', '0.7', 'weekly'), (f'{SITE}/reviews', '0.7', 'weekly'),
            (f'{SITE}/tides', '0.7', 'daily'),
            (f'{SITE}/neihai-preorder.html', '0.8', 'weekly'),
            (f'{SITE}/penghu-3days-itinerary', '0.8', 'monthly'),
            (f'{SITE}/penghu-family-travel', '0.8', 'monthly'),
            (f'{SITE}/penghu-food-guide', '0.8', 'monthly'),
            (f'{SITE}/penghu-100', '0.8', 'monthly'),
            (f'{SITE}/penghu-2026-festival-guide', '0.8', 'weekly')]
    try:
        conn = get_db(); cur = conn.cursor()
        cur.execute("SELECT slug, COALESCE(updated_at,published_at,created_at) AS m FROM posts WHERE is_published=TRUE")
        for r in cur.fetchall():
            urls.append((f'{SITE}/blog/{r["slug"]}', '0.6', 'monthly', str(r['m'])[:10]))
        cur.execute("SELECT slug FROM preorder_products WHERE is_active=TRUE")
        for r in cur.fetchall():
            urls.append((f'{SITE}/preorder/{r["slug"]}', '0.8', 'weekly'))
        cur.close(); conn.close()
    except Exception:
        pass
    items = ''
    for u in urls:
        lastmod = f'<lastmod>{u[3]}</lastmod>' if len(u) > 3 else ''
        items += f'<url><loc>{u[0]}</loc><changefreq>{u[2]}</changefreq><priority>{u[1]}</priority>{lastmod}</url>'
    xml = f'<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{items}</urlset>'
    return app.response_class(xml, mimetype='application/xml')


# ─── 諮詢表單 ──────────────────────────────────────────────
@app.route('/api/contact', methods=['POST'])
def submit_contact():
    data = request.get_json(force=True, silent=True) or {}
    required = ['name', 'phone', 'travel_date', 'travel_date_end', 'people', 'transport']
    missing = [f for f in required if not data.get(f)]
    if missing:
        return jsonify(ok=False, error=f'缺少必填欄位：{", ".join(missing)}'), 400

    slot_id    = data.get('slot_id')
    is_waitlist = False
    slot_label  = ''

    try:
        conn = get_db()
        cur  = conn.cursor()

        # ── 若有選梯次，鎖定並扣名額 ──────────────────────────
        if slot_id:
            cur.execute(
                "SELECT * FROM tour_slots WHERE id=%s AND is_active=TRUE FOR UPDATE",
                (slot_id,))
            slot = cur.fetchone()
            if not slot:
                conn.rollback(); cur.close(); conn.close()
                return jsonify(ok=False, error='此梯次不存在或已關閉'), 400

            slot_label = slot['date_label']
            remaining  = slot['capacity']     - slot['booked']
            wl_remain  = slot['waitlist_cap'] - slot['waitlisted']

            if remaining > 0:
                cur.execute(
                    "UPDATE tour_slots SET booked=booked+1 WHERE id=%s", (slot_id,))
                is_waitlist = False
            elif wl_remain > 0:
                cur.execute(
                    "UPDATE tour_slots SET waitlisted=waitlisted+1 WHERE id=%s", (slot_id,))
                is_waitlist = True
            else:
                conn.rollback(); cur.close(); conn.close()
                return jsonify(ok=False, error='此梯次名額與候補名額均已額滿'), 400

        # ── 寫入諮詢資料 ────────────────────────────────────────
        cur.execute("""
            INSERT INTO contacts
              (name,phone,travel_date,travel_date_end,people,budget,transport,
               departure_city,tour_interest,slot_id,is_waitlist,notes,
               visit_count,member_status,member_no,utm)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id, created_at
        """, (data['name'], data['phone'], data['travel_date'], data['travel_date_end'],
              data['people'], data.get('budget',''), data['transport'],
              data.get('departure_city',''), data.get('tour_interest',''),
              slot_id, is_waitlist, data.get('notes',''),
              (data.get('visit_count') or '')[:20],
              (data.get('member_status') or '')[:30],
              (data.get('member_no') or '')[:40],
              Json({k: str(v)[:200] for k, v in (data.get('utm') or {}).items()
                    if k in ('utm_source', 'utm_medium', 'utm_campaign', 'utm_content',
                             'utm_term', 'landing_page', 'referrer')})))
        row = cur.fetchone()
        conn.commit(); cur.close(); conn.close()

        data['slot_label']  = slot_label
        data['is_waitlist'] = is_waitlist
        send_contact_email(data)
        return jsonify(ok=True, id=row['id'], created_at=str(row['created_at']),
                       is_waitlist=is_waitlist,
                       message='已登記候補，我們將優先通知您' if is_waitlist else '報名成功')
    except Exception as e:
        # 一定要留下 log：這裡曾因例外被靜默吞掉，導致諮詢表單壞了一個月才被發現。
        import traceback
        print(f'[CONTACT ERROR] {type(e).__name__}: {e}')
        traceback.print_exc()
        return jsonify(ok=False, error='伺服器錯誤，請稍後再試'), 500


@app.route('/api/quiz-lead', methods=['POST'])
def submit_quiz_lead():
    """行程診斷「領取行程建議表」名單：僅需姓名＋聯絡方式，
    寫入 contacts 表（tour_interest＝診斷結果），並寄通知信給店家。"""
    data = request.get_json(force=True, silent=True) or {}
    name = (data.get('name') or '').strip()
    phone = (data.get('phone') or '').strip()
    if not name or not phone:
        return jsonify(ok=False, error='請填寫姓名與聯絡電話／LINE'), 400
    month = (data.get('month') or '').strip()
    result_type = (data.get('result_type') or '').strip()
    result_name = (data.get('result_name') or '').strip()
    people = (data.get('people') or '').strip()
    notes = f"【行程診斷名單】結果：{result_type or '—'}｜想玩：{result_name or '—'}" \
            f"｜預計月份：{month or '未填'}｜人數：{people or '未填'}"
    try:
        conn = get_db(); cur = conn.cursor()
        cur.execute("""
            INSERT INTO contacts (name, phone, tour_interest, notes)
            VALUES (%s,%s,%s,%s) RETURNING id, created_at
        """, (name, phone, result_name or result_type, notes))
        row = cur.fetchone()
        conn.commit(); cur.close(); conn.close()
        try:
            send_contact_email({
                'name': name, 'phone': phone, 'travel_date': f'{month or "未定"}（診斷名單）',
                'travel_date_end': '', 'people': people or '—', 'budget': '—',
                'transport': '—', 'departure_city': '—',
                'tour_interest': result_name or result_type, 'slot_label': '（行程診斷領取建議表）',
                'is_waitlist': False, 'notes': notes,
            })
        except Exception as _e:
            print(f'[EMAIL] 診斷名單通知呼叫失敗（不影響）：{_e}')
        return jsonify(ok=True, id=row['id'])
    except Exception:
        return jsonify(ok=False, error='伺服器錯誤，請稍後再試'), 500


@app.route('/api/contacts', methods=['GET'])
def list_contacts():
    if not has_role('orders'):
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
            if r.get('contacted_at'): r['contacted_at'] = str(r['contacted_at'])
            if r.get('converted_at'): r['converted_at'] = str(r['converted_at'])
            if r.get('conversion_value') is not None:
                r['conversion_value'] = float(r['conversion_value'])
            result.append(r)
        return jsonify(ok=True, contacts=result)
    except Exception as e:
        return jsonify(ok=False, error='伺服器錯誤'), 500


LEAD_STATUSES = {'new', 'contacted', 'qualified', 'converted', 'lost'}


@app.route('/api/admin/contacts/<int:contact_id>', methods=['PATCH'])
def update_contact_funnel(contact_id):
    """更新諮詢漏斗狀態；時間戳由伺服器依狀態維護。"""
    if not has_role('orders'):
        return jsonify(ok=False, error='未授權'), 401
    data = request.get_json(force=True, silent=True) or {}
    status = (data.get('lead_status') or '').strip()
    if status not in LEAD_STATUSES:
        return jsonify(ok=False, error='無效的諮詢狀態'), 400
    raw_value = data.get('conversion_value')
    try:
        value = None if raw_value in (None, '') else max(0, float(raw_value))
    except (TypeError, ValueError):
        return jsonify(ok=False, error='成交金額格式錯誤'), 400
    try:
        conn = get_db(); cur = conn.cursor()
        cur.execute("SELECT id, lead_status FROM contacts WHERE id=%s FOR UPDATE", (contact_id,))
        previous = cur.fetchone()
        if not previous:
            cur.close(); conn.close()
            return jsonify(ok=False, error='找不到諮詢紀錄'), 404
        cur.execute("""
            UPDATE contacts SET lead_status=%s,
              contacted_at=CASE WHEN %s IN ('contacted','qualified','converted')
                                THEN COALESCE(contacted_at,NOW()) ELSE contacted_at END,
              converted_at=CASE WHEN %s='converted' THEN COALESCE(converted_at,NOW())
                                WHEN %s<>'converted' THEN NULL ELSE converted_at END,
              conversion_value=CASE WHEN %s='converted' THEN %s ELSE NULL END
            WHERE id=%s
        """, (status, status, status, status, status, value, contact_id))
        write_audit(cur, 'update', '諮詢漏斗', str(contact_id), 1, 0,
                    f"{previous['lead_status'] or 'new'} → {status}; value={value or 0}")
        conn.commit(); cur.close(); conn.close()
        return jsonify(ok=True, id=contact_id, lead_status=status,
                       conversion_value=value)
    except Exception as exc:
        print(f'[CONTACT FUNNEL] {exc}')
        return jsonify(ok=False, error='伺服器錯誤'), 500


@app.route('/api/admin/conversion-summary', methods=['GET'])
def conversion_summary():
    """最近 30 天諮詢漏斗，供後台與營運報告使用。"""
    if not has_role('orders'):
        return jsonify(ok=False, error='未授權'), 401
    try:
        conn = get_db(); cur = conn.cursor()
        cur.execute("""
            SELECT COALESCE(lead_status,'new') AS status, COUNT(*) AS count,
                   COALESCE(SUM(conversion_value),0) AS value
            FROM contacts WHERE created_at >= NOW() - INTERVAL '30 days'
            GROUP BY COALESCE(lead_status,'new')
        """)
        rows = {r['status']: {'count': r['count'], 'value': float(r['value'])}
                for r in cur.fetchall()}
        cur.execute("""
            SELECT COALESCE(utm->>'utm_source','(direct)') AS source, COUNT(*) AS count
            FROM contacts WHERE created_at >= NOW() - INTERVAL '30 days'
            GROUP BY 1 ORDER BY 2 DESC LIMIT 10
        """)
        sources = [dict(r) for r in cur.fetchall()]
        cur.close(); conn.close()
        total = sum(row['count'] for row in rows.values())
        converted = rows.get('converted', {}).get('count', 0)
        return jsonify(ok=True, days=30, total=total, stages=rows, sources=sources,
                       conversion_rate=(converted / total if total else 0))
    except Exception as exc:
        print(f'[CONVERSION SUMMARY] {exc}')
        return jsonify(ok=False, error='讀取轉換摘要失敗'), 500


# ─── 啟動 ──────────────────────────────────────────────────
if __name__ == '__main__':
    try:
        init_db()
    except Exception as e:
        print(f'[警告] 本機無 DB，跳過初始化：{e}')
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=os.environ.get('FLASK_DEBUG','0')=='1')
