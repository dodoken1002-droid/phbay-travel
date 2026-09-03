"""Pre-deploy schema migration runner：所有 DDL 只在這裡執行一次。

為什麼要獨立成一支：gunicorn 每個 worker 都會 import app，模組層級的
init_db() 因此被平行執行。全新資料庫上兩個 worker 同時建表會有一方拿到
duplicate 錯誤，而 init_db() 對會員資料表是 fail-open（app.py 的
SAVEPOINT member_tables），結果是 schema 只建到一半卻沒有人發現——
最嚴重的情況是 members.merged_into_member_id 沒建起來，之後每一個
會員 API 都會在 _member_row() 上 500，而首頁看起來完全正常。

因為 init_db() 會吞掉會員資料表的錯誤，「有跑完」不等於「有建好」，
所以這裡在 init_db() 之後必須真的回查 information_schema 驗證。

驗證失敗時以非零 exit code 結束：Railway 的 start command 是 && 串接，
migrate 失敗就不會啟動 gunicorn，該次部署判定失敗並保留前一版繼續服務，
而不是讓半套 schema 上線。
"""

import os
import sys

# 先擋掉 import app 時的模組層級初始化，避免在這裡重複跑一次 DDL。
os.environ["SKIP_SCHEMA_INIT"] = "1"

from app import app, get_db, init_db  # noqa: E402


REQUIRED_TABLES = (
    "members", "member_auth_codes", "member_trips", "member_points",
    "member_identities", "member_consents", "point_wallet", "point_transactions",
    "member_verification_challenges", "order_claims", "member_merge_requests",
)

# 這些欄位是 app.py 熱路徑直接引用的；缺一個就是全站會員功能 500。
REQUIRED_COLUMNS = (
    ("members", "merged_into_member_id"),
)


def verify_schema():
    """回查實際 schema，列出所有缺少的資料表與欄位。"""
    missing = []
    conn = get_db(); cur = conn.cursor()
    try:
        cur.execute("""SELECT table_name FROM information_schema.tables
                       WHERE table_schema='public' AND table_name = ANY(%s)""",
                    (list(REQUIRED_TABLES),))
        present = {row["table_name"] for row in cur.fetchall()}
        missing += [f"table {t}" for t in REQUIRED_TABLES if t not in present]

        for table, column in REQUIRED_COLUMNS:
            cur.execute("""SELECT 1 FROM information_schema.columns
                           WHERE table_schema='public' AND table_name=%s
                             AND column_name=%s""", (table, column))
            if not cur.fetchone():
                missing.append(f"column {table}.{column}")
    finally:
        cur.close(); conn.close()
    return missing


def main():
    try:
        with app.app_context():
            init_db()
    except Exception as exc:
        print(f"[MIGRATE] init_db 失敗：{exc}", file=sys.stderr)
        return 1

    try:
        missing = verify_schema()
    except Exception as exc:
        print(f"[MIGRATE] 無法驗證 schema：{exc}", file=sys.stderr)
        return 1

    if missing:
        for item in missing:
            print(f"[MIGRATE] 缺少 {item}", file=sys.stderr)
        print("[MIGRATE] schema 不完整，中止部署", file=sys.stderr)
        return 1

    print("[MIGRATE] schema 初始化與驗證完成")
    return 0


if __name__ == "__main__":
    sys.exit(main())
