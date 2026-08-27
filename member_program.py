"""澎湖百旅會員制度的資料表、等級與輸入正規化。"""

from __future__ import annotations

import json
import os
import re
from datetime import datetime


DEFAULT_LEVELS = [
    (1, "初見澎湖"), (2, "澎湖熟旅人"), (5, "澎湖知己"),
    (10, "澎湖旅家"), (20, "澎湖守護者"), (100, "百澎傳奇"),
]


def levels():
    """門檻可由 MEMBER_LEVELS_JSON 覆寫，避免商業規則寫死。"""
    raw = os.environ.get("MEMBER_LEVELS_JSON", "").strip()
    if raw:
        try:
            parsed = [(int(row["trips"]), str(row["name"])[:40]) for row in json.loads(raw)]
            if parsed and all(trips > 0 for trips, _ in parsed):
                return sorted(parsed)
        except Exception:
            pass
    return DEFAULT_LEVELS


def level_for_trips(trip_count):
    trip_count = max(0, int(trip_count or 0))
    current = "準會員"
    for threshold, name in levels():
        if trip_count >= threshold:
            current = name
    return current


def next_level(trip_count):
    trip_count = max(0, int(trip_count or 0))
    for threshold, name in levels():
        if trip_count < threshold:
            return {"name": name, "threshold": threshold,
                    "remaining": threshold - trip_count}
    return None


def normalize_phone(value):
    digits = re.sub(r"\D", "", value or "")
    if digits.startswith("886"):
        digits = "0" + digits[3:]
    return digits[:20]


def valid_email(value):
    return bool(re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", (value or "").strip()))


def public_member(row):
    row = dict(row)
    trips = int(row.get("trip_count") or 0)
    return {
        "id": row.get("id"), "member_no": row.get("member_no"),
        "name": row.get("name"), "email": row.get("email"),
        "phone_masked": ("***" + (row.get("phone") or "")[-4:]) if row.get("phone") else "",
        "birth_month": row.get("birth_month"), "joined_at": str(row.get("joined_at") or ""),
        "level": level_for_trips(trips), "trip_count": trips,
        "points_balance": int(row.get("points_balance") or 0),
        "next_level": next_level(trips), "line_bound": bool(row.get("line_user_id")),
    }


def init_member_tables(cur):
    cur.execute("""
        CREATE TABLE IF NOT EXISTS members (
            id SERIAL PRIMARY KEY,
            member_no VARCHAR(30) UNIQUE,
            name VARCHAR(100) NOT NULL,
            phone VARCHAR(30) NOT NULL,
            phone_normalized VARCHAR(30) NOT NULL UNIQUE,
            email VARCHAR(200) NOT NULL,
            line_user_id VARCHAR(64) UNIQUE,
            birth_month SMALLINT CHECK (birth_month BETWEEN 1 AND 12),
            trip_count INT NOT NULL DEFAULT 0,
            points_balance INT NOT NULL DEFAULT 0,
            notes TEXT DEFAULT '',
            consent_at TIMESTAMP NOT NULL,
            joined_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW(),
            is_active BOOLEAN DEFAULT TRUE
        )
    """)
    cur.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_members_email_lower ON members (LOWER(email))")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_members_phone ON members (phone_normalized)")
    cur.execute("""
        CREATE TABLE IF NOT EXISTS member_trips (
            id SERIAL PRIMARY KEY,
            member_id INT NOT NULL REFERENCES members(id) ON DELETE CASCADE,
            source_type VARCHAR(30) DEFAULT 'manual',
            source_ref VARCHAR(80),
            tour_name VARCHAR(180) NOT NULL,
            tour_category VARCHAR(60) DEFAULT '',
            departure_date DATE,
            status VARCHAR(30) NOT NULL DEFAULT 'planned',
            counts_trip BOOLEAN NOT NULL DEFAULT TRUE,
            points_awarded INT NOT NULL DEFAULT 0,
            notes TEXT DEFAULT '',
            created_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW(),
            UNIQUE (source_type, source_ref)
        )
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_member_trips_member ON member_trips (member_id, departure_date DESC)")
    cur.execute("""
        CREATE TABLE IF NOT EXISTS member_points (
            id SERIAL PRIMARY KEY,
            member_id INT NOT NULL REFERENCES members(id) ON DELETE CASCADE,
            trip_id INT REFERENCES member_trips(id) ON DELETE SET NULL,
            delta INT NOT NULL,
            source VARCHAR(100) NOT NULL,
            redemption TEXT DEFAULT '',
            created_at TIMESTAMP DEFAULT NOW()
        )
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_member_points_member ON member_points (member_id, created_at DESC)")
    cur.execute("""
        CREATE TABLE IF NOT EXISTS member_auth_codes (
            id SERIAL PRIMARY KEY,
            member_id INT NOT NULL REFERENCES members(id) ON DELETE CASCADE,
            purpose VARCHAR(30) NOT NULL,
            code_hash VARCHAR(128) NOT NULL,
            expires_at TIMESTAMP NOT NULL,
            used_at TIMESTAMP,
            attempts INT NOT NULL DEFAULT 0,
            created_at TIMESTAMP DEFAULT NOW()
        )
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_member_codes_active ON member_auth_codes (purpose, expires_at DESC)")
    _migrate_member_columns(cur)


# CREATE TABLE IF NOT EXISTS 不會修改「已經存在」的資料表，因此日後每新增一個欄位，
# 都必須同時在這份清單補一行，否則正式站只會拿到舊結構，而 INSERT 會整筆失敗。
# 2026-07 的 contacts 表就是漏了這份清單，線上諮詢整整一個月每一筆送出都失敗且無人察覺。
MEMBER_COLUMN_MIGRATIONS = [
    # ('members', 'referrer_member_no', 'VARCHAR(40)'),   ← 之後新增欄位請照這個格式往下加
]


def _migrate_member_columns(cur):
    for table, col, defn in MEMBER_COLUMN_MIGRATIONS:
        cur.execute(f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS {col} {defn}")


def recalculate_member(cur, member_id):
    cur.execute("""
        SELECT COUNT(*) AS trips FROM member_trips
        WHERE member_id=%s AND status='completed' AND counts_trip=TRUE
    """, (member_id,))
    trips = int(cur.fetchone()["trips"] or 0)
    cur.execute("SELECT COALESCE(SUM(delta),0) AS points FROM member_points WHERE member_id=%s",
                (member_id,))
    points = int(cur.fetchone()["points"] or 0)
    cur.execute("UPDATE members SET trip_count=%s, points_balance=%s, updated_at=NOW() WHERE id=%s",
                (trips, points, member_id))
    return trips, points


DEFAULT_POINTS_PER_TRIP = 100


def points_per_trip():
    """每完成一趟可計入的旅次給多少點；可由 MEMBER_POINTS_PER_TRIP 覆寫。"""
    try:
        value = int(os.environ.get("MEMBER_POINTS_PER_TRIP", "").strip()
                    or DEFAULT_POINTS_PER_TRIP)
    except ValueError:
        value = DEFAULT_POINTS_PER_TRIP
    return max(0, value)


def sync_trip_points(cur, trip_id):
    """依旅次目前狀態調整點數帳本，並把結果回寫 member_trips.points_awarded。

    冪等設計：先算「這趟應得幾點」，再與帳本上已針對這趟給過的點數相比，
    只補差額。因此重複執行不會重複給點；旅次被改成取消或改為不計入時，
    差額為負，會自動產生一筆沖銷紀錄，而不是偷偷把歷史紀錄改掉。
    回傳這趟旅次最終的應得點數。
    """
    cur.execute("""SELECT id,member_id,tour_name,status,counts_trip
                   FROM member_trips WHERE id=%s FOR UPDATE""", (trip_id,))
    trip = cur.fetchone()
    if not trip:
        return 0
    entitled = points_per_trip() if (trip["status"] == "completed" and trip["counts_trip"]) else 0
    cur.execute("SELECT COALESCE(SUM(delta),0) AS awarded FROM member_points WHERE trip_id=%s",
                (trip_id,))
    awarded = int(cur.fetchone()["awarded"] or 0)
    diff = entitled - awarded
    if diff:
        label = "完成旅次" if diff > 0 else "旅次取消沖銷"
        cur.execute("""INSERT INTO member_points (member_id,trip_id,delta,source)
                       VALUES (%s,%s,%s,%s)""",
                    (trip["member_id"], trip_id, diff,
                     f'{label}：{(trip["tour_name"] or "")}'[:100]))
    cur.execute("UPDATE member_trips SET points_awarded=%s,updated_at=NOW() WHERE id=%s",
                (entitled, trip_id))
    return entitled


def next_member_no(cur):
    year = datetime.now().year
    prefix = os.environ.get("MEMBER_NO_PREFIX", "PH").strip().upper()[:6] or "PH"
    cur.execute("SELECT nextval('members_id_seq') AS id")
    reserved_id = int(cur.fetchone()["id"])
    return reserved_id, f"{prefix}-{year}-{reserved_id:05d}"
