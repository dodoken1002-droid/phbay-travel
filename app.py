"""
潮旅國際旅行社 - Flask 後端
功能：
  GET  /            → 回傳 index.html
  POST /api/contact → 儲存諮詢表單至 PostgreSQL
  GET  /api/contacts → 查詢所有諮詢（管理用，可加密碼保護）
"""

import os
from datetime import datetime
from flask import Flask, send_from_directory, request, jsonify
import psycopg2
import psycopg2.extras
from dotenv import load_dotenv

# 載入 .env 設定（本機開發用；Railway 會直接注入環境變數）
load_dotenv()

app = Flask(__name__, static_folder='.', static_url_path='')

# ─── 資料庫連線 ───────────────────────────────────────────
# 標記：資料表是否已初始化（避免每次 request 都重複建立）
_db_initialized = False
def get_db():
    """取得 PostgreSQL 連線。Railway 會提供 DATABASE_URL 環境變數。"""
    database_url = os.environ.get('DATABASE_URL')
    if not database_url:
        raise RuntimeError('DATABASE_URL 環境變數未設定')
    # Railway 的 DATABASE_URL 有時以 postgres:// 開頭，需改為 postgresql://
    if database_url.startswith('postgres://'):
        database_url = database_url.replace('postgres://', 'postgresql://', 1)
    return psycopg2.connect(database_url, cursor_factory=psycopg2.extras.RealDictCursor)


def init_db():
    """應用啟動時自動建立資料表（若尚未存在）。"""
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS contacts (
            id           SERIAL PRIMARY KEY,
            name         VARCHAR(100) NOT NULL,
            phone        VARCHAR(50)  NOT NULL,
            travel_date  DATE,
            people       VARCHAR(20),
            tour_interest VARCHAR(100),
            notes        TEXT,
            created_at   TIMESTAMP DEFAULT NOW()
        )
    """)
    conn.commit()
    cur.close()
    conn.close()
    print('[DB] contacts 資料表已就緒')


# gunicorn 啟動時也會執行此區塊（模組層級），確保資料表存在
# 即使 DATABASE_URL 尚未注入也不中斷服務，等第一次 request 再重試
try:
    with app.app_context():
        init_db()
except Exception as _e:
    print(f'[警告] 啟動時無法初始化 DB，將於首次請求重試：{_e}')


# 每次 request 前確保資料表存在（DATABASE_URL 延遲注入時的保險）
@app.before_request
def ensure_db():
    global _db_initialized
    if not _db_initialized:
        try:
            init_db()
            _db_initialized = True
        except Exception as e:
            print(f'[DB INIT] {e}')


# ─── 靜態頁面路由 ──────────────────────────────────────────
@app.route('/')
def index():
    """回傳首頁 HTML。"""
    return send_from_directory('.', 'index.html')


# ─── API：儲存聯絡表單 ──────────────────────────────────────
@app.route('/api/contact', methods=['POST'])
def submit_contact():
    """
    接收 JSON，驗證必填欄位後寫入 PostgreSQL。
    回傳 { "ok": true } 或 { "ok": false, "error": "..." }
    """
    # force=True：即使 Content-Type 不完全符合也強制解析 JSON
    data = request.get_json(force=True, silent=True) or {}

    # 必填欄位驗證
    required = ['name', 'phone', 'travel_date', 'people']
    missing = [f for f in required if not data.get(f)]
    if missing:
        return jsonify(ok=False, error=f'缺少必填欄位：{", ".join(missing)}'), 400

    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO contacts (name, phone, travel_date, people, tour_interest, notes)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING id, created_at
        """, (
            data['name'],
            data['phone'],
            data['travel_date'],
            data['people'],
            data.get('tour_interest', ''),
            data.get('notes', ''),
        ))
        row = cur.fetchone()
        conn.commit()
        cur.close()
        conn.close()
        return jsonify(ok=True, id=row['id'], created_at=str(row['created_at']))
    except Exception as e:
        print(f'[DB ERROR] {e}')
        return jsonify(ok=False, error='伺服器錯誤，請稍後再試'), 500


# ─── API：查詢所有諮詢（管理用） ────────────────────────────
@app.route('/api/contacts', methods=['GET'])
def list_contacts():
    """
    查詢所有諮詢紀錄（依時間倒序）。
    簡易保護：需帶 ?key=<ADMIN_KEY> 查詢參數。
    ADMIN_KEY 在 Railway 環境變數中設定。
    """
    admin_key = os.environ.get('ADMIN_KEY', '')
    if admin_key and request.args.get('key') != admin_key:
        return jsonify(ok=False, error='未授權'), 401

    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute("SELECT * FROM contacts ORDER BY created_at DESC LIMIT 200")
        rows = cur.fetchall()
        cur.close()
        conn.close()
        # 將日期/時間轉為字串
        result = []
        for row in rows:
            r = dict(row)
            if r.get('travel_date'):
                r['travel_date'] = str(r['travel_date'])
            if r.get('created_at'):
                r['created_at'] = str(r['created_at'])
            result.append(r)
        return jsonify(ok=True, contacts=result)
    except Exception as e:
        print(f'[DB ERROR] {e}')
        return jsonify(ok=False, error='伺服器錯誤'), 500


# ─── 啟動 ──────────────────────────────────────────────────
if __name__ == '__main__':
    try:
        init_db()
    except Exception as e:
        print(f'[警告] 無法連線資料庫，跳過初始化：{e}')

    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=os.environ.get('FLASK_DEBUG', '0') == '1')
